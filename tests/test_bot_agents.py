"""Tests for bot_agents.py"""

from rsb.prerender.bot_agents import KNOWN_BOT_UA_SUBSTRINGS, build_js_regex, is_bot


def test_googlebot_detected() -> None:
    assert is_bot("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")


def test_gptbot_detected() -> None:
    assert is_bot("Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2)")


def test_claudebot_detected() -> None:
    assert is_bot("ClaudeBot/1.0 (+https://www.anthropic.com/claude-web)")


def test_perplexitybot_detected() -> None:
    assert is_bot("Mozilla/5.0 (compatible; PerplexityBot/1.0)")


def test_human_not_detected() -> None:
    assert not is_bot(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )


def test_bot_list_not_empty() -> None:
    assert len(KNOWN_BOT_UA_SUBSTRINGS) >= 20


def test_js_regex_buildable() -> None:
    regex = build_js_regex()
    assert "|" in regex
    assert "googlebot" in regex
    assert "gptbot" in regex
