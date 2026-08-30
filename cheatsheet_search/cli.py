"""Command-line front end for cheatsheet_search."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from cheatsheet_search.config import load_config
from cheatsheet_search.search import SearchResult, search


def _relative_label(path: Path, sources: list[Path]) -> str:
    for source in sources:
        try:
            return str(path.relative_to(source))
        except ValueError:
            continue
    return str(path)


def _print_results(results: list[SearchResult], sources: list[Path]) -> None:
    if not results:
        print("No matches found.")
        return
    for i, r in enumerate(results, start=1):
        label = _relative_label(r.file_path, sources)
        heading = f" — {r.heading}" if r.heading else ""
        print(f"[{i}] {label}{heading} (line {r.line_number})")
        print(f"    {r.line_text}")


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
    _print_results(results, config.sources)

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
