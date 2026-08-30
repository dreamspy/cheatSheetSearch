"""Config loading: which folders to search.

Resolution order for the config file itself:
  1. explicit path (--config)
  2. $CHEATSHEET_SEARCH_CONFIG
  3. ~/.config/cheatsheet-search/config.toml
  4. built-in defaults (no file needed)

If ~/.config/cheatsheet-search/config.toml doesn't exist yet, a default one
is written there on first use so it's discoverable and hand-editable.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "cheatsheet-search" / "config.toml"

DEFAULT_SOURCES = [
    "~/Vaults/General vault/3.Resources/Programming/2. Cheatsheets/",
    "~/Vaults/General vault/3.Resources/Programming/3. How-tos/",
]

DEFAULT_CONFIG_TOML = """\
# cheatsheet-search config
# List every folder you want searched. Each is searched for *.md files
# only (recursively); anything else (images, etc.) is ignored.
sources = [
    "~/Vaults/General vault/3.Resources/Programming/2. Cheatsheets/",
    "~/Vaults/General vault/3.Resources/Programming/3. How-tos/",
]
"""


@dataclass
class Config:
    sources: list[Path] = field(default_factory=list)
    config_path: Path | None = None


def _expand(raw_paths: list[str]) -> list[Path]:
    return [Path(p).expanduser() for p in raw_paths]


def load_config(explicit_path: str | os.PathLike | None = None) -> Config:
    path: Path | None
    if explicit_path is not None:
        path = Path(explicit_path).expanduser()
    elif os.environ.get("CHEATSHEET_SEARCH_CONFIG"):
        path = Path(os.environ["CHEATSHEET_SEARCH_CONFIG"]).expanduser()
    elif DEFAULT_CONFIG_PATH.exists():
        path = DEFAULT_CONFIG_PATH
    else:
        DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_CONFIG_PATH.write_text(DEFAULT_CONFIG_TOML)
        path = DEFAULT_CONFIG_PATH

    with open(path, "rb") as f:
        data = tomllib.load(f)

    raw_sources = data.get("sources", DEFAULT_SOURCES)
    return Config(sources=_expand(raw_sources), config_path=path)
