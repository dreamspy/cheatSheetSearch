"""Core search logic: index the configured markdown folders and query them.

Kept as a plain importable function (`search`) separate from the CLI/argument
parsing, so other front ends (e.g. an Alfred workflow) can call the same
underlying search without going through the command line.
"""

from __future__ import annotations

import difflib
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from cheatsheet_search.config import Config, load_config

# Common English function words dropped before building the FTS query, so a
# question like "what is the shortcut for X" searches on the meaningful
# words rather than diluting the match with noise terms.
STOPWORDS = {
    "a", "an", "and", "are", "at", "be", "by", "did", "do", "does", "for",
    "from", "how", "i", "in", "is", "it", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "what", "when", "where", "which", "who",
    "why", "with", "you",
}

_WORD_RE = re.compile(r"[A-Za-z0-9_+#.-]+")

_SCHEMA = """
CREATE VIRTUAL TABLE lines USING fts5(
    content,
    heading,
    title,
    file_path UNINDEXED,
    line_number UNINDEXED,
    tokenize = 'porter unicode61'
);
"""

# Column weights for bm25(): body content matters most, then section
# heading, then the file's own title - keeps a whole-file/heading match
# from outranking an actual matching body line.
_BM25_WEIGHTS = "1.0, 0.5, 0.3"


@dataclass
class SearchResult:
    file_path: Path
    line_number: int
    heading: str
    line_text: str
    score: float


def _iter_markdown_files(sources: list[Path]):
    for source in sources:
        if not source.exists():
            continue
        yield from sorted(source.rglob("*.md"))


def _build_index(con: sqlite3.Connection, sources: list[Path]) -> int:
    con.execute(_SCHEMA)
    rows = []
    for path in _iter_markdown_files(sources):
        heading = ""
        title = path.stem
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                # A heading line updates section context for the lines that
                # follow it, but isn't indexed as a standalone searchable
                # row - as a very short "document" it would otherwise win
                # bm25 ranking over the real matching content line.
                heading = stripped.lstrip("#").strip()
                continue
            if not stripped:
                continue
            rows.append((stripped, heading, title, str(path), i))
    con.executemany(
        "INSERT INTO lines (content, heading, title, file_path, line_number) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def _query_words(query: str) -> list[str]:
    words = [w.lower() for w in _WORD_RE.findall(query)]
    meaningful = [w for w in words if w not in STOPWORDS]
    return meaningful or words


def _fts_query(words: list[str]) -> str:
    # OR-join terms: a multi-word query still matches rows containing just
    # one correctly-spelled word, which is what gives typo tolerance without
    # any fuzzy matching as long as one term in the query is spelled right.
    escaped = [f'"{w}"' for w in words if w]
    return " OR ".join(escaped)


def _run_fts(con: sqlite3.Connection, words: list[str], limit: int) -> list[SearchResult]:
    if not words:
        return []
    match_expr = _fts_query(words)
    cur = con.execute(
        f"SELECT file_path, line_number, heading, content, "
        f"bm25(lines, {_BM25_WEIGHTS}) AS score "
        "FROM lines WHERE lines MATCH ? ORDER BY score LIMIT ?",
        (match_expr, limit),
    )
    return [
        SearchResult(Path(fp), ln, heading, content, score)
        for fp, ln, heading, content, score in cur.fetchall()
    ]


def _word_matches(con: sqlite3.Connection, word: str) -> bool:
    cur = con.execute(
        'SELECT 1 FROM lines WHERE lines MATCH ? LIMIT 1', (f'"{word}"',)
    )
    return cur.fetchone() is not None


def _stemmed_vocabulary(con: sqlite3.Connection) -> set[str]:
    con.execute("CREATE VIRTUAL TABLE lines_vocab USING fts5vocab('lines', 'row')")
    return {term for (term,) in con.execute("SELECT term FROM lines_vocab")}


def _stem(con: sqlite3.Connection, word: str) -> str:
    con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _probe USING fts5(w, tokenize='porter unicode61')")
    con.execute("DELETE FROM _probe")
    con.execute("INSERT INTO _probe(w) VALUES (?)", (word,))
    con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _probe_vocab USING fts5vocab('_probe', 'row')")
    row = con.execute("SELECT term FROM _probe_vocab LIMIT 1").fetchone()
    return row[0] if row else word.lower()


def _correct_words(con: sqlite3.Connection, words: list[str]) -> list[str]:
    """Replace any query word that matches nothing with its closest known
    word from the corpus (stdlib difflib), so a single misspelled word in an
    otherwise-fine query doesn't get diluted down to only the generic words
    that happen to be spelled correctly. Words that already match anything
    (including via porter stemming, e.g. "detaching" ~ "detach") are left
    alone.

    Correction compares *stemmed* forms (via a throwaway fts5 probe table
    using the same porter tokenizer as the index), not raw spelling -
    comparing raw strings would let an unrelated same-suffix word (e.g.
    "watching") outscore the real match ("detach") just because "-ing"
    dominates a naive character-similarity ratio.
    """
    vocab_stems: set[str] | None = None
    corrected = []
    for word in words:
        if _word_matches(con, word):
            corrected.append(word)
            continue
        if vocab_stems is None:
            vocab_stems = _stemmed_vocabulary(con)
        stem = _stem(con, word)
        match = difflib.get_close_matches(stem, vocab_stems, n=1, cutoff=0.7)
        corrected.append(match[0] if match else word)
    return corrected


def search(query: str, config: Config | None = None, limit: int = 5) -> list[SearchResult]:
    """Search the configured markdown sources for `query`.

    Rebuilds a fresh in-memory SQLite FTS5 index on every call - the corpus
    is small enough (single-digit ms) that persisting/caching the index
    isn't worth the complexity.
    """
    if config is None:
        config = load_config()

    con = sqlite3.connect(":memory:")
    try:
        _build_index(con, config.sources)
        words = _query_words(query)
        words = _correct_words(con, words)
        return _run_fts(con, words, limit)
    finally:
        con.close()
