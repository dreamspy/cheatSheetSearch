from pathlib import Path

from cheatsheet_search.cli import (
    _context_lines,
    _highlight_matches,
    _hyperlink,
    _supports_color,
)


class _FakeStream:
    def __init__(self, is_tty: bool):
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty


def test_supports_color_when_tty_and_no_env_override():
    assert _supports_color(_FakeStream(True), env={}) is True


def test_supports_color_false_when_not_a_tty():
    assert _supports_color(_FakeStream(False), env={}) is False


def test_supports_color_false_when_no_color_env_set_even_on_tty():
    assert _supports_color(_FakeStream(True), env={"NO_COLOR": "1"}) is False


def test_context_lines_returns_stripped_neighbors():
    lines = ["above", "matched", "below"]
    above, below = _context_lines(lines, 2)
    assert above == "above"
    assert below == "below"


def test_context_lines_omits_missing_boundary_lines():
    lines = ["only line"]
    above, below = _context_lines(lines, 1)
    assert above is None
    assert below is None


def test_context_lines_omits_blank_neighbors():
    lines = ["", "matched", "   "]
    above, below = _context_lines(lines, 2)
    assert above is None
    assert below is None


def test_context_lines_handles_line_number_past_end_of_lines():
    assert _context_lines([], 5) == (None, None)


def test_highlight_matches_wraps_literal_word():
    result = _highlight_matches("detach from tmux", ["tmux"])
    assert "\033[1;33mtmux\033[0m" in result
    assert "detach" in result  # untouched, no escape codes around it


def test_highlight_matches_matches_inflected_form_of_corrected_stem():
    # "detach" is the porter stem search.py would substitute for a typo'd
    # query word - it should still highlight "detaches" in the line text.
    result = _highlight_matches("`Ctrl+b d` detaches from the session", ["detach"])
    assert "\033[1;33mdetaches\033[0m" in result


def test_highlight_matches_no_words_returns_text_unchanged():
    text = "plain line with no matches"
    assert _highlight_matches(text, []) == text


def test_hyperlink_wraps_label_in_osc8_escape_with_file_uri(tmp_path):
    target = tmp_path / "notes.md"
    result = _hyperlink("notes.md", target)
    assert result.startswith(f"\033]8;;{target.as_uri()}\033\\notes.md")
    assert result.endswith("\033]8;;\033\\")
