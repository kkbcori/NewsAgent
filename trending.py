"""
trending.py — Fetches live trending hashtags from X/Twitter for free.

Sources (no API key needed):
  - trends24.in   → USA, India, Worldwide, Telugu regions
  - getdaytrends.com → India real-time trends

Results are cached per run so we only fetch once per workflow execution.
"""

import re
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 10

# ── Scraper targets ───────────────────────────────────────────────────────────
TREND_SOURCES = {
    "usa":    "https://trends24.in/united-states/",
    "india":  "https://trends24.in/india/",
    "world":  "https://trends24.in/",
    "telugu": "https://trends24.in/india/",   # India trends cover Telugu region
}

GETDAYTRENDS_INDIA = "https://getdaytrends.com/india/"

# ── In-memory cache (per run) ─────────────────────────────────────────────────
_cache: dict[str, list[str]] = {}


def _clean_tag(text: str) -> str:
    """Normalise a trending topic to a hashtag."""
    text = text.strip()
    if not text:
        return ""
    # Remove tweet count suffixes like "1.2M tweets"
    text = re.sub(r"\s*\d[\d.,]*[KkMmBb]?\s*(tweets?|posts?)?$", "", text).strip()
    # Already a hashtag
    if text.startswith("#"):
        return text
    # Single word with no spaces → make it a hashtag
    if " " not in text:
        return f"#{text}"
    # Multi-word → CamelCase hashtag
    return "#" + "".join(w.capitalize() for w in text.split())


def _scrape_trends24(url: str, max_items: int = 30) -> list[str]:
    """Scrape trending topics from trends24.in."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        tags = []
        # trends24 structure: trend cards contain ordered lists of trends
        for ol in soup.select("ol.trend-card__list"):
            for li in ol.select("li a"):
                t = _clean_tag(li.get_text(strip=True))
                if t and t not in tags:
                    tags.append(t)
                if len(tags) >= max_items:
                    break
            if len(tags) >= max_items:
                break

        # Fallback: try alternative selectors
        if not tags:
            for a in soup.select("a[href*='/trending/']"):
                t = _clean_tag(a.get_text(strip=True))
                if t and t not in tags:
                    tags.append(t)
                if len(tags) >= max_items:
                    break

        logger.info(f"  trends24 ({url[-30:]}): {len(tags)} trends")
        return tags

    except Exception as e:
        logger.warning(f"  trends24 scrape failed ({url}): {e}")
        return []


def _scrape_getdaytrends() -> list[str]:
    """Scrape trending topics from getdaytrends.com (India)."""
    try:
        resp = requests.get(GETDAYTRENDS_INDIA, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        tags = []
        # getdaytrends structure: trend items in table rows or list items
        for el in soup.select("td.main-col a, .trend-name a, li.trend a"):
            t = _clean_tag(el.get_text(strip=True))
            if t and t not in tags:
                tags.append(t)
            if len(tags) >= 25:
                break

        # Fallback: grab any links that look like trends
        if not tags:
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                if text and (text.startswith("#") or (len(text) > 2 and len(text) < 40)):
                    t = _clean_tag(text)
                    if t and t not in tags:
                        tags.append(t)
                if len(tags) >= 25:
                    break

        logger.info(f"  getdaytrends India: {len(tags)} trends")
        return tags

    except Exception as e:
        logger.warning(f"  getdaytrends scrape failed: {e}")
        return []


def fetch_trending(category: str) -> list[str]:
    """
    Fetch trending hashtags for a given display category.
    Results are cached per run.

    Returns a list of hashtag strings like ['#ModiGovt', '#IPL2026', '#Gaza']
    """
    if category in _cache:
        return _cache[category]

    logger.info(f"[TRENDS] Fetching trending hashtags for: {category}")
    tags = []

    url = TREND_SOURCES.get(category, TREND_SOURCES["world"])
    tags.extend(_scrape_trends24(url))

    # Add India-specific trends for india/telugu/telugu_film categories
    if category in ("india", "telugu", "telugu_film"):
        india_tags = _scrape_getdaytrends()
        for t in india_tags:
            if t not in tags:
                tags.append(t)

    # Always add worldwide trends as supplement
    if category != "world":
        world_tags = _scrape_trends24(TREND_SOURCES["world"], max_items=15)
        for t in world_tags:
            if t not in tags:
                tags.append(t)

    # Deduplicate and limit
    tags = list(dict.fromkeys(tags))[:40]
    _cache[category] = tags

    logger.info(f"[TRENDS] {category}: {len(tags)} total trending hashtags")
    if tags:
        logger.info(f"[TRENDS] Top 10: {', '.join(tags[:10])}")

    return tags


def fetch_all_trending() -> dict[str, list[str]]:
    """Fetch trending hashtags for all categories at once."""
    categories = ["usa", "world", "india", "telugu", "telugu_film"]
    all_trends = {}
    for cat in categories:
        all_trends[cat] = fetch_trending(cat)
    return all_trends
