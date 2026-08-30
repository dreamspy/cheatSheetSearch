# cheatSheetSearch

Fast local search (no AI/web fallback) over personal cheat sheets and
how-to notes, from the command line.

## Install

```sh
pip install -e .
```

This installs a `cheatsheet` command (see `[project.scripts]` in
`pyproject.toml`).

## Configure

Which folders get searched is controlled by a config file, not hardcoded
paths. On first run, if none exists yet, a default one is created at:

```
~/.config/cheatsheet-search/config.toml
```

It looks like:

```toml
sources = [
    "~/Vaults/General vault/3.Resources/Programming/2. Cheatsheets/",
    "~/Vaults/General vault/3.Resources/Programming/3. How-tos/",
]
```

Edit `sources` to point at whatever folders you want searched - each is
searched recursively for `*.md` files only (anything else, e.g. stray
images, is ignored). Config file lookup order:

1. `--config PATH` on the command line
2. `$CHEATSHEET_SEARCH_CONFIG` env var
3. `~/.config/cheatsheet-search/config.toml`

## Run

```sh
cheatsheet "what is the shortcut for detaching from tmux"
```

This prints a ranked list (top 5 by default, `-n`/`--limit` to change it)
of matching lines, each showing the source file, its section heading (if
any), and the line number:

```
[1] tmux.md — Detaching (line 12)
    `Ctrl+b d` — detach from current session
```

Search tolerates typos: any query word that matches nothing in the notes
gets corrected to its closest known word (stdlib `difflib`, compared on
stemmed forms) before the search runs, so a single misspelled word doesn't
sink an otherwise-correct multi-word query.

## Open a result

After a search, the CLI prompts:

```
Open result number (or Enter to skip):
```

Enter a result number to open its source file with the OS default handler
(`open` on macOS - e.g. Obsidian for vault notes). The result listing shows
the line number so you can jump to it manually; opening straight to a
specific line isn't supported for the default `.md` handler on this
machine (Obsidian doesn't support line-jump via a plain `open`, only
whole-file open). Pass `--no-open` to skip the prompt entirely (useful when
scripting).
