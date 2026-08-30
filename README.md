# cheatSheetSearch

Fast local search (no AI/web fallback) over personal cheat sheets and
how-to notes, from the command line.

## Install

### System-wide (recommended)

Install with [pipx](https://pipx.pypa.io/) so the `cheatsheet` command is on
your `PATH` everywhere, in its own isolated environment (no dependency on
where any particular clone or checkout happens to live):

```sh
pipx install git+https://github.com/dreamspy/cheatSheetSearch.git
```

(No pipx yet? `brew install pipx`.) This is stdlib-only - no other Python
dependencies get pulled in. To upgrade after new commits land:

```sh
pipx upgrade cheatsheet-search
```

To uninstall:

```sh
pipx uninstall cheatsheet-search
```

If you keep a permanent local clone (e.g. because you're developing on it)
and want the installed command to pick up edits immediately without
reinstalling, install from that clone in editable mode instead:

```sh
git clone git@github.com:dreamspy/cheatSheetSearch.git ~/Programming/cheatSheetSearch
pipx install --editable ~/Programming/cheatSheetSearch
```

### Local / development install

From a checkout of this repo, in a virtualenv:

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/cheatsheet "..."
```

Either install method exposes a `cheatsheet` command (see `[project.scripts]`
in `pyproject.toml`).

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
any), the line number, and a line of context immediately above/below the
match where one exists:

```
[1] tmux.md — Detaching (line 12)
    ## Detaching
    `Ctrl+b d` — detach from current session

[2] tmux.md — Sessions (line 18)
    `Ctrl+b s` — list sessions to switch between
```

In a real terminal the file label (`tmux.md` above) is a clickable OSC 8
hyperlink to the source file, context lines are dimmed, and the matched
query word(s) are highlighted within the result line. Colors/hyperlinks
auto-disable when stdout isn't a terminal (piped/redirected output, or
`--no-open`'s scripting use case) or when `NO_COLOR` is set, so scripted
use always gets clean plain text.

Search tolerates typos: any query word that matches nothing in the notes
gets corrected to its closest known word (stdlib `difflib`, compared on
stemmed forms) before the search runs, so a single misspelled word doesn't
sink an otherwise-correct multi-word query. A corrected word is highlighted
via the actual (inflected) form it matches in the text, not the misspelled
query word.

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
