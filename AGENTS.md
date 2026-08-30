# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Add durable project-specific notes here as they are discovered through real work.

## This project

CLI tool (`cheatsheet`) that FTS5-searches local Markdown cheat sheets/how-tos and opens a matched
file. Stdlib-only (sqlite3 FTS5, tomllib, difflib) - no external dependencies. See `README.md` for
install/config/usage; see module docstrings in `cheatsheet_search/` for how the index and typo
correction work.

- Test: `pip install -e . pytest && pytest tests/`.
- Search logic (`cheatsheet_search/search.py:search`) is a plain importable function, kept separate
  from the argparse CLI (`cheatsheet_search/cli.py`) specifically so a future non-CLI front end
  (e.g. Alfred) can call it directly.
- Config file resolution and default path: see `cheatsheet_search/config.py` module docstring.
- Typo tolerance deliberately goes beyond a naive "OR-join + fallback only on zero total rows"
  design: it corrects any individual query word that matches nothing, comparing *porter-stemmed*
  forms (not raw spelling) via a throwaway fts5 probe table - see `_correct_words`/`_stem` in
  `search.py` for why (raw-string difflib comparison picked wrong corrections, e.g. "watching"
  over "detach" for a typo'd "detatching").
- On macOS, opening a search result opens the whole file via `open` (OS default handler), not a
  specific line - the default `.md` handler here is Obsidian, which has no line-jump via plain
  `open`. Result output shows the line number instead.
- CLI output (`cli.py:_print_results`) colors, OSC 8 hyperlinks, and dimmed context lines - all
  gated by `_supports_color` (tty + `NO_COLOR` check) so piped/scripted output stays plain. Matched-
  word highlighting (`_highlight_matches`) uses a case-insensitive *word-prefix* regex against
  `SearchResult.matched_words`, not exact string match: a typo-corrected query word may be a porter
  stem (e.g. "detach"), which won't literally appear in text like "detaches" - prefix matching is
  the cheap way to still highlight the inflected form actually on the line.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
