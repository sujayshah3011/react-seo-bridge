"""
bot_agents.py - Versioned list of crawler and bot user-agent substrings.
"""

from __future__ import annotations


BOT_LIST_VERSION = "2025.04"

KNOWN_BOT_UA_SUBSTRINGS: list[str] = [
    "googlebot",
    "google-inspectiontool",
    "bingbot",
    "msnbot",
    "slurp",
    "duckduckbot",
    "baiduspider",
    "yandexbot",
    "sogou",
    "exabot",
    "facebot",
    "ia_archiver",
    "applebot",
    "gptbot",
    "oai-searchbot",
    "chatgpt-user",
    "claudebot",
    "anthropic-ai",
    "perplexitybot",
    "youbot",
    "amazonbot",
    "bytespider",
    "meta-externalagent",
    "semrushbot",
    "ahrefsbot",
    "mj12bot",
    "dotbot",
    "rogerbot",
    "screaming frog",
    "facebookexternalhit",
    "twitterbot",
    "linkedinbot",
    "slackbot",
    "slack-imgproxy",
    "discordbot",
    "telegrambot",
    "whatsapp",
    "iframely",
    "embedly",
    "prerender",
    "headlesschrome",
]


def build_js_regex() -> str:
    """Return a JavaScript-safe regex body for crawler detection."""

    return "|".join(KNOWN_BOT_UA_SUBSTRINGS)


def is_bot(user_agent: str) -> bool:
    """Return True when a user-agent looks like a crawler."""

    user_agent_lower = user_agent.lower()
    return any(substring in user_agent_lower for substring in KNOWN_BOT_UA_SUBSTRINGS)
