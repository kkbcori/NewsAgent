"""
scraper.py — Fetches latest news from RSS feeds.

Sources:
  - Direct RSS feeds from news outlets (BBC, NDTV, Sakshi etc.)
  - Google News RSS (free, no API key, 60,000+ sources)

Google News RSS formats:
  Top stories:  https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en
  By topic:     https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-IN&gl=IN&ceid=IN:en
  By search:    https://news.google.com/rss/search?q=Andhra+Pradesh&hl=te&gl=IN&ceid=IN:te
"""

import feedparser
import re
import logging

logger = logging.getLogger(__name__)

# ── Direct RSS sources ────────────────────────────────────────────────────────
NEWS_SOURCES = {
    "usa": [
        {"name": "AP News",          "url": "https://feeds.apnews.com/rss/apf-topnews"},
        {"name": "NPR",              "url": "https://feeds.npr.org/1001/rss.xml"},
        {"name": "NBC News",         "url": "https://feeds.nbcnews.com/nbcnews/public/news"},
        {"name": "Washington Post",  "url": "https://feeds.washingtonpost.com/rss/national"},
        {"name": "Axios",            "url": "https://api.axios.com/feed/"},
        {"name": "Politico",         "url": "https://www.politico.com/rss/politicopicks.xml"},
    ],
    "world": [
        {"name": "BBC World",        "url": "http://feeds.bbci.co.uk/news/world/rss.xml"},
        {"name": "Al Jazeera",       "url": "https://www.aljazeera.com/xml/rss/all.xml"},
        {"name": "Reuters World",    "url": "https://feeds.reuters.com/reuters/worldNews"},
        {"name": "DW World",         "url": "https://rss.dw.com/rdf/rss-en-world"},
        {"name": "BBC Europe",       "url": "http://feeds.bbci.co.uk/news/world/europe/rss.xml"},
        {"name": "Euronews",         "url": "https://feeds.feedburner.com/euronews/en/news"},
        {"name": "ABC Australia",    "url": "https://www.abc.net.au/news/feed/51120/rss.xml"},
        {"name": "The Guardian AU",  "url": "https://www.theguardian.com/australia-news/rss"},
    ],
    "india": [
        {"name": "NDTV",             "url": "https://feeds.feedburner.com/ndtvnews-top-stories"},
        {"name": "Times of India",   "url": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms"},
        {"name": "The Hindu",        "url": "https://www.thehindu.com/news/national/feeder/default.rss"},
        {"name": "India Today",      "url": "https://www.indiatoday.in/rss/1206514"},
        {"name": "Hindustan Times",  "url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"},
        {"name": "The Wire",         "url": "https://thewire.in/feed"},
        {"name": "BBC Hindi",        "url": "http://feeds.bbci.co.uk/hindi/rss.xml"},
        {"name": "NDTV Hindi",       "url": "https://feeds.feedburner.com/ndtvkhabar"},
    ],
    "telugu": [
        {"name": "Sakshi",           "url": "https://www.sakshi.com/rss.xml"},
        {"name": "TV9 Telugu",       "url": "https://tv9telugu.com/feed"},
        {"name": "NTV Telugu",       "url": "https://www.ntvtelugu.com/feed"},
        {"name": "Eenadu",           "url": "https://www.eenadu.net/telugu-news/rss"},
        {"name": "ABN Telugu",       "url": "https://www.andhrajyothy.com/rss.xml"},
        {"name": "10TV News",        "url": "https://www.10tv.in/rss.xml"},
    ],
    "telugu_film": [
        {"name": "123Telugu",        "url": "https://www.123telugu.com/feed"},
        {"name": "Filmibeat Telugu", "url": "https://telugu.filmibeat.com/rss.xml"},
        {"name": "Tollywood.net",    "url": "https://www.tollywood.net/feed/"},
        {"name": "Gulte",            "url": "https://www.gulte.com/feed/"},
        {"name": "Telugu360",        "url": "https://www.telugu360.com/feed/"},
        {"name": "GreatAndhra",      "url": "https://www.greatandhra.com/feed/"},
    ],
}

# ── Google News RSS sources (free, no key) ────────────────────────────────────
# Google News RSS: completely free, updated every 15 minutes, 60,000+ sources
# Geo/language params: hl=language, gl=country, ceid=country:language

GOOGLE_NEWS_SOURCES = {
    "usa": [
        {"name": "Google News US",       "url": "https://news.google.com/rss/headlines/section/topic/NATION?hl=en-US&gl=US&ceid=US:en"},
        {"name": "Google News Politics",  "url": "https://news.google.com/rss/search?q=US+politics&hl=en-US&gl=US&ceid=US:en"},
    ],
    "world": [
        {"name": "Google News World",    "url": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en&gl=US&ceid=US:en"},
        {"name": "Google News Europe",   "url": "https://news.google.com/rss/search?q=Europe+news&hl=en&gl=GB&ceid=GB:en"},
        {"name": "Google News Australia","url": "https://news.google.com/rss/headlines/section/topic/NATION?hl=en-AU&gl=AU&ceid=AU:en"},
    ],
    "india": [
        {"name": "Google News India",    "url": "https://news.google.com/rss/headlines/section/topic/NATION?hl=en-IN&gl=IN&ceid=IN:en"},
        {"name": "Google News India 2",  "url": "https://news.google.com/rss/search?q=India&hl=en-IN&gl=IN&ceid=IN:en"},
        {"name": "Google News Hindi",    "url": "https://news.google.com/rss/headlines/section/topic/NATION?hl=hi-IN&gl=IN&ceid=IN:hi"},
    ],
    "telugu": [
        {"name": "Google News AP",       "url": "https://news.google.com/rss/search?q=Andhra+Pradesh&hl=te-IN&gl=IN&ceid=IN:te"},
        {"name": "Google News Telangana","url": "https://news.google.com/rss/search?q=Telangana&hl=te-IN&gl=IN&ceid=IN:te"},
        {"name": "Google News Telugu",   "url": "https://news.google.com/rss/headlines/section/topic/NATION?hl=te-IN&gl=IN&ceid=IN:te"},
    ],
    "telugu_film": [
        {"name": "Google News Tollywood","url": "https://news.google.com/rss/search?q=Tollywood+Telugu+movie&hl=te-IN&gl=IN&ceid=IN:te"},
        {"name": "Google News Film EN",  "url": "https://news.google.com/rss/search?q=Telugu+cinema+film&hl=en-IN&gl=IN&ceid=IN:en"},
    ],
}

# Maps raw category → display category
CATEGORY_DISPLAY_MAP = {
    "usa":         "usa",
    "world":       "world",
    "india":       "india",
    "telugu":      "telugu",
    "telugu_film": "telugu_film",
}

STRIP_HTML = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    text = STRIP_HTML.sub("", text or "")
    return " ".join(text.split())[:600]


def _image(entry) -> str | None:
    if hasattr(entry, "media_content") and entry.media_content:
        return entry.media_content[0].get("url")
    if hasattr(entry, "enclosures") and entry.enclosures:
        for e in entry.enclosures:
            if "image" in e.get("type", ""):
                return e.get("href") or e.get("url")
    return None


def scrape_feed(source: dict, raw_category: str, max_items: int) -> list[dict]:
    try:
        feed = feedparser.parse(source["url"])
        items = []
        for entry in feed.entries[:max_items]:
            title   = _clean(entry.get("title", ""))
            summary = _clean(entry.get("summary", entry.get("description", "")))
            link    = entry.get("link", "")
            if not title or not link:
                continue
            items.append({
                "source_url":       link,
                "original_title":   title,
                "original_summary": summary,
                "source_name":      source["name"],
                "raw_category":     raw_category,
                "category":         CATEGORY_DISPLAY_MAP.get(raw_category, raw_category),
                "image_url":        _image(entry),
                "youtube_id":       None,
                "video_url":        None,
            })
        logger.info(f"  {source['name']}: {len(items)} items")
        return items
    except Exception as e:
        logger.warning(f"  Failed {source['name']}: {e}")
        return []


def scrape_all(max_per_source: int = 5) -> list[dict]:
    all_items = []
    seen_titles = set()

    # Direct RSS feeds
    for raw_category, sources in NEWS_SOURCES.items():
        logger.info(f"[RSS {raw_category.upper()}]")
        for source in sources:
            items = scrape_feed(source, raw_category, max_per_source)
            for item in items:
                key = item["original_title"].lower().strip()[:80]
                if key not in seen_titles:
                    seen_titles.add(key)
                    all_items.append(item)

    # Google News RSS (deduplicated)
    for raw_category, sources in GOOGLE_NEWS_SOURCES.items():
        logger.info(f"[Google News {raw_category.upper()}]")
        for source in sources:
            items = scrape_feed(source, raw_category, max_per_source)
            for item in items:
                key = item["original_title"].lower().strip()[:80]
                if key not in seen_titles:
                    seen_titles.add(key)
                    all_items.append(item)

    logger.info(f"Total scraped: {len(all_items)} unique items")
    return all_items
