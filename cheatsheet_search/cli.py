"""Command-line front end for cheatsheet_search."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from cheatsheet_search.config import load_config
from cheatsheet_search.search import SearchResult, search

# Plain ANSI escapes - no dependency, and easy to gate off entirely for
# non-terminal output (see `_supports_color`).
_RESET = "\033[0m"
_DIM = "\033[2m"
_HIGHLIGHT = "\033[1;33m"  # bold yellow, distinct from dim context lines


def _relative_label(path: Path, sources: list[Path]) -> str:
    for source in sources:
        try:
            return str(path.relative_to(source))
        except ValueError:
            continue
    return str(path)


def _supports_color(stream=sys.stdout, env=None) -> bool:
    """Colors/hyperlinks are opt-out for piped or redirected output (and via
    NO_COLOR), so scripted use (`--no-open`'s existing use case) still gets
    clean plain text with no escape codes to strip."""
    if env is None:
        env = os.environ
    if "NO_COLOR" in env:
        return False
    try:
        return stream.isatty()
    except (AttributeError, ValueError):
        return False


def _hyperlink(label: str, path: Path) -> str:
    """Wrap `label` in an OSC 8 terminal hyperlink pointing at `path`.
    Terminals without OSC 8 support just render the label as plain text."""
    uri = path.resolve().as_uri()
    return f"\033]8;;{uri}\033\\{label}\033]8;;\033\\"


def _dim(text: str) -> str:
    return f"{_DIM}{text}{_RESET}"


def _highlight_matches(text: str, words: list[str]) -> str:
    """Bold+color occurrences of `words` (and their inflections, e.g. a
    typo-corrected query word like "detach" matching text "detaching") in
    `text`. Matching is a case-insensitive word-prefix match, since a
    corrected word may be a porter stem of the word actually on the line
    rather than the exact word (see `_correct_words` in search.py)."""
    terms = {w for w in words if w}
    if not terms:
        return text
    pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(t) for t in terms) + r")\w*", re.IGNORECASE
    )
    return pattern.sub(lambda m: f"{_HIGHLIGHT}{m.group(0)}{_RESET}", text)


def _file_lines(path: Path, cache: dict[Path, list[str]]) -> list[str]:
    if path not in cache:
        try:
            cache[path] = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            cache[path] = []
    return cache[path]


def _context_lines(lines: list[str], line_number: int) -> tuple[str | None, str | None]:
    """The lines immediately above/below `line_number` (1-indexed) in
    `lines`, stripped. Missing (file boundary) or blank lines are omitted
    (returned as None) rather than printed as empty context."""
    idx = line_number - 1
    above = lines[idx - 1].strip() if 0 <= idx - 1 < len(lines) else ""
    below = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
    return (above or None, below or None)


def _print_results(
    results: list[SearchResult], sources: list[Path], *, color: bool = False
) -> None:
    if not results:
        print("No matches found.")
        return
    file_cache: dict[Path, list[str]] = {}
    for i, r in enumerate(results, start=1):
        if i > 1:
            print()
        label = _relative_label(r.file_path, sources)
        if color:
            label = _hyperlink(label, r.file_path)
        heading = f" — {r.heading}" if r.heading else ""
        print(f"[{i}] {label}{heading} (line {r.line_number})")

        lines = _file_lines(r.file_path, file_cache)
        above, below = _context_lines(lines, r.line_number)
        line_text = _highlight_matches(r.line_text, r.matched_words) if color else r.line_text
        if above:
            print(f"    {_dim(above) if color else above}")
        print(f"    {line_text}")
        if below:
            print(f"    {_dim(below) if color else below}")


def _open_result(result: SearchResult) -> None:
    subprocess.run(["open", str(result.file_path)], check=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cheatsheet",
        description="Search personal cheat sheets and how-tos.",
    )
    parser.add_argument("query", help="natural-language search query")
    parser.add_argument(
        "-n", "--limit", type=int, default=5, help="max results to show (default: 5)"
    )
    parser.add_argument("--config", help="path to config.toml (overrides default lookup)")
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="don't prompt to open a result (useful for scripting)",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    results = search(args.query, config=config, limit=args.limit)
    _print_results(results, config.sources, color=_supports_color())

    if args.no_open or not results:
        return 0

    try:
        choice = input("\nOpen result number (or Enter to skip): ").strip()
    except EOFError:
        return 0
    if not choice:
        return 0
    if not choice.isdigit() or not (1 <= int(choice) <= len(results)):
        print(f"Invalid selection: {choice}", file=sys.stderr)
        return 1
    _open_result(results[int(choice) - 1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
