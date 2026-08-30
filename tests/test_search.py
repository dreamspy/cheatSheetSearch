from pathlib import Path

import pytest

from cheatsheet_search.config import Config
from cheatsheet_search.search import search


@pytest.fixture
def sample_config(tmp_path: Path) -> Config:
    cheatsheets = tmp_path / "Cheatsheets"
    howtos = tmp_path / "How-tos"
    cheatsheets.mkdir()
    howtos.mkdir()

    (cheatsheets / "tmux.md").write_text(
        "# tmux\n"
        "\n"
        "## Detaching\n"
        "\n"
        "`Ctrl+b d` detaches from the current session.\n"
        "`Ctrl+b s` lists sessions to switch between.\n"
    )
    (cheatsheets / "git.md").write_text(
        "# git\n"
        "\n"
        "## Undo\n"
        "\n"
        "`git reset --hard HEAD~1` discards the last commit entirely.\n"
    )
    (cheatsheets / "notes.png").write_bytes(b"not markdown")
    (howtos / "deploy.md").write_text(
        "# Deploy how-to\n\n## Steps\n\nRun `make deploy` from the repo root.\n"
    )

    return Config(sources=[cheatsheets, howtos])


def test_finds_exact_match(sample_config):
    results = search("what is the shortcut for detaching from tmux", config=sample_config)
    assert results
    assert "Ctrl+b d" in results[0].line_text
    assert results[0].file_path.name == "tmux.md"


def test_ignores_non_markdown_files(sample_config):
    results = search("not markdown", config=sample_config)
    assert all(r.file_path.suffix == ".md" for r in results)
    assert not results  # the .png content was never indexed


def test_typo_tolerant_multiword_query(sample_config):
    # "detaching" misspelled, "tmux" and "session" correct - OR-joined FTS
    # should still surface the right line via the correctly-spelled words.
    results = search("detaxhing tmux session", config=sample_config)
    assert results
    assert results[0].file_path.name == "tmux.md"


def test_fuzzy_fallback_when_everything_is_misspelled(sample_config):
    # every word garbled -> normal FTS returns zero rows -> fuzzy fallback
    results = search("tmxu detac", config=sample_config)
    assert results
    assert results[0].file_path.name == "tmux.md"


def test_searches_both_configured_sources(sample_config):
    files_found = set()
    for query in ["tmux", "git reset", "deploy"]:
        results = search(query, config=sample_config)
        files_found.update(r.file_path.name for r in results)
    assert {"tmux.md", "git.md", "deploy.md"} <= files_found


def test_respects_limit(sample_config):
    results = search("the", config=sample_config, limit=2)
    assert len(results) <= 2
