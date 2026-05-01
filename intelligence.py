"""
intelligence.py — The "Brain" layer of NewsAgent.

Three intelligence passes run AFTER news scraping:

1. between_the_lines(items)
   → Cross-references all headlines, finds hidden connections, timing patterns,
     narrative gaps, cui bono analysis, distraction stories

2. fetch_inventions()
   → Scrapes ArXiv (science papers), USPTO/Google Patents, Product Hunt, GitHub Trending
     for new breakthroughs and translates them to plain language

3. conspiracy_angles(items)
   → For selected stories: finds the mainstream narrative, the alternative angle,
     who benefits, what's being distracted from, media silence analysis

All free, no API keys needed.
"""

import re
import logging
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 10

STRIP_HTML = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return " ".join(STRIP_HTML.sub("", text or "").split())[:500]


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — READ BETWEEN THE LINES
# ═══════════════════════════════════════════════════════════════════════════════

BETWEEN_LINES_PROMPT = """\
You are an investigative intelligence analyst — sharp, non-partisan, fearless.

Below are today's news headlines from multiple sources. Your job is to:

1. READ BETWEEN THE LINES — find what is NOT being said:
   - Identify stories that appear on the same day that may be connected
   - Find the "timing coincidence" — what did this news distract from?
   - Who benefits from this story being published now? (Cui bono)
   - What is conspicuously ABSENT from coverage today?
   - Find contradictions between different outlets covering the same story

2. CROSS-REFERENCE — connect at least 3 pairs of seemingly unrelated stories
   that when read together reveal a bigger picture

3. NARRATIVE GAPS — identify 3 stories where the official explanation
   leaves obvious unanswered questions

For each finding, write ONE sharp tweet (max 260 chars) that:
- States the observation factually (not as conspiracy — as a question or observation)
- Is thought-provoking: "Has anyone noticed that..."
- Never makes claims — asks questions that make readers think
- Adds 1 relevant hashtag

Return ONLY a raw JSON array:
[{{
  "tweet": "tweet text #Tag",
  "type": "timing|connection|gap|silence|contradiction",
  "stories_referenced": ["headline1", "headline2"],
  "angle": "one sentence explaining the intelligence observation"
}}]

No markdown. Just valid JSON.

Today's headlines:
{headlines}"""


STORY_DEPTH_PROMPT = """\
You are an investigative journalist who digs deeper than the headline.

Analyse this single news story in depth:

STORY:
Title: {title}
Summary: {summary}
Source: {source}

Write a sharp analytical tweet (max 260 chars) that reveals ONE of:
- The hidden angle (what the headline buries in the details)
- The unanswered question the reporter didn't ask
- The context that completely changes how you read this story
- The stakeholder whose name is missing from the story
- The historical pattern this story repeats

Add 1-2 relevant trending hashtags from: {trending}

Return ONLY the tweet text. Nothing else."""


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — INVENTIONS & BREAKTHROUGHS
# ═══════════════════════════════════════════════════════════════════════════════

INVENTION_SOURCES = [
    # ArXiv — latest AI, Physics, Bio papers (free RSS)
    {"name": "ArXiv AI",      "url": "https://rss.arxiv.org/rss/cs.AI",    "cat": "science"},
    {"name": "ArXiv Physics", "url": "https://rss.arxiv.org/rss/physics",  "cat": "science"},
    {"name": "ArXiv Bio",     "url": "https://rss.arxiv.org/rss/q-bio",    "cat": "science"},
    {"name": "ArXiv Quantum", "url": "https://rss.arxiv.org/rss/quant-ph", "cat": "science"},

    # Tech launches
    {"name": "Product Hunt",  "url": "https://www.producthunt.com/feed",   "cat": "tech"},
    {"name": "Hacker News",   "url": "https://hnrss.org/frontpage",        "cat": "tech"},

    # Science news
    {"name": "MIT Tech Review","url": "https://www.technologyreview.com/feed/", "cat": "science"},
    {"name": "New Scientist",  "url": "https://www.newscientist.com/feed/home/","cat": "science"},
    {"name": "Phys.org",       "url": "https://phys.org/rss-feed/",         "cat": "science"},

    # India-specific tech/science
    {"name": "ISRO News",      "url": "https://www.isro.gov.in/rss",        "cat": "india_science"},
    {"name": "Tech2 India",    "url": "https://www.firstpost.com/tech/feed","cat": "india_tech"},
]

INVENTION_TWEET_PROMPT = """\
You are a science communicator who makes breakthroughs exciting for general audiences.

Translate this research/invention into an engaging tweet for X:

Title: {title}
Summary: {summary}
Source: {source}

Write ONE tweet (max 260 chars) that:
- Explains what was discovered/invented in plain language
- Uses an analogy if helpful ("Scientists just built X that works like Y")
- Conveys why this matters to an ordinary person
- Ends with the implication: what does this enable next?
- Adds 1-2 relevant hashtags from trending: {trending}
- Also write a "mind-blown" version as hot_take (max 260 chars)

Return ONLY valid JSON:
{{"rewrite": "plain explanation tweet", "hot_take": "mind-blown angle tweet"}}"""


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — CONSPIRACY & ALTERNATIVE ANGLES
# ═══════════════════════════════════════════════════════════════════════════════

# Alternative/independent news sources for counter-narrative
ALT_SOURCES = [
    {"name": "The Intercept",   "url": "https://theintercept.com/feed/?rss=1",    "lean": "investigative"},
    {"name": "Mint Press",      "url": "https://www.mintpressnews.com/feed/",      "lean": "alt"},
    {"name": "ZeroHedge",       "url": "https://feeds.feedburner.com/zerohedge/feed", "lean": "alt"},
    {"name": "Swarajya",        "url": "https://swarajyamag.com/feed",             "lean": "india_alt"},
    {"name": "NewsLaundry",     "url": "https://www.newslaundry.com/feed",         "lean": "india_investigative"},
    {"name": "The Wire India",  "url": "https://thewire.in/feed",                 "lean": "india_investigative"},
    {"name": "OpIndia",         "url": "https://www.opindia.com/feed/",            "lean": "india_alt"},
    {"name": "Wikileaks",       "url": "https://wikileaks.org/static/press.xml",  "lean": "leaked"},
]

CONSPIRACY_PROMPT = """\
You are a critical thinking analyst who explores alternative explanations for news events.
You present ALL angles — mainstream AND alternative — without claiming any is true.
You ask questions, not make accusations. Your goal: make readers think critically.

Story:
Title: {title}
Summary: {summary}
Source: {source} (mainstream)

Alternative sources covering this or related topics: {alt_coverage}

Write 3 tweets about this story:

1. MAINSTREAM: The official/mainstream interpretation (factual, neutral)
2. ALTERNATIVE: The alternative explanation or what mainstream media is missing
   - What questions does the official narrative leave unanswered?
   - What angle do independent/alternative sources suggest?
   - Use "Some analysts argue..." or "Questions remain about..."
3. CUI BONO: Who benefits from this story/situation?
   - Which corporations, governments, or groups gain from this outcome?
   - Follow the money/power — state it as a question

All tweets max 260 chars. Add 1 relevant hashtag each.
Present these as "three angles" — not as facts, as perspectives to consider.

Trending hashtags available: {trending}

Return ONLY valid JSON:
{{
  "mainstream": "tweet #Tag",
  "alternative": "tweet #Tag",
  "cui_bono": "tweet #Tag"
}}"""


# ═══════════════════════════════════════════════════════════════════════════════
# SCRAPING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_inventions(max_per_source: int = 3) -> list[dict]:
    """Scrape latest research papers, tech launches, and breakthroughs."""
    logger.info("[INVENTIONS] Fetching latest breakthroughs...")
    items = []
    seen  = set()

    for source in INVENTION_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            count = 0
            for entry in feed.entries[:max_per_source]:
                title   = _clean(entry.get("title", ""))
                summary = _clean(entry.get("summary", entry.get("description", "")))
                link    = entry.get("link", "")
                if not title or not link:
                    continue
                key = title.lower()[:60]
                if key in seen:
                    continue
                seen.add(key)
                items.append({
                    "title":    title,
                    "summary":  summary,
                    "link":     link,
                    "source":   source["name"],
                    "category": source["cat"],
                    "type":     "invention",
                })
                count += 1
            logger.info(f"  {source['name']}: {count} items")
        except Exception as e:
            logger.warning(f"  {source['name']} failed: {e}")

    logger.info(f"[INVENTIONS] Total: {len(items)} breakthroughs")
    return items


def fetch_alt_coverage(keywords: list[str], max_items: int = 5) -> list[dict]:
    """Fetch alternative source coverage for given keywords."""
    items = []
    seen  = set()

    for source in ALT_SOURCES[:4]:  # limit to avoid timeout
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:10]:
                title = _clean(entry.get("title", ""))
                if not title:
                    continue
                # Check if any keyword appears in title
                title_lower = title.lower()
                if any(kw.lower() in title_lower for kw in keywords):
                    key = title_lower[:60]
                    if key not in seen:
                        seen.add(key)
                        items.append({
                            "title":  title,
                            "source": source["name"],
                            "lean":   source["lean"],
                            "link":   entry.get("link", ""),
                        })
                        if len(items) >= max_items:
                            break
            if len(items) >= max_items:
                break
        except Exception:
            pass

    return items


def google_patents_trending() -> list[dict]:
    """Fetch recent patent grants from USPTO RSS (free)."""
    try:
        feed = feedparser.parse("https://patents.google.com/rss/query=language:ENGLISH&num=10")
        items = []
        for entry in feed.entries[:5]:
            title   = _clean(entry.get("title", ""))
            summary = _clean(entry.get("summary", ""))
            link    = entry.get("link", "")
            if title and link:
                items.append({
                    "title":    title,
                    "summary":  summary,
                    "link":     link,
                    "source":   "Google Patents",
                    "category": "patent",
                    "type":     "invention",
                })
        logger.info(f"  Google Patents: {len(items)} items")
        return items
    except Exception as e:
        logger.warning(f"  Google Patents failed: {e}")
        return []


def github_trending() -> list[dict]:
    """Fetch GitHub trending repos (free, no auth needed)."""
    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={
                "q":    f"created:>{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')}",
                "sort": "stars",
                "order":"desc",
                "per_page": 5,
            },
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        items = []
        for repo in resp.json().get("items", []):
            items.append({
                "title":    f"{repo['name']}: {repo.get('description','')[:100]}",
                "summary":  f"GitHub: {repo.get('stargazers_count',0)} stars. {repo.get('description','')}",
                "link":     repo["html_url"],
                "source":   "GitHub Trending",
                "category": "tech",
                "type":     "invention",
            })
        logger.info(f"  GitHub Trending: {len(items)} repos")
        return items
    except Exception as e:
        logger.warning(f"  GitHub Trending failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN INTELLIGENCE FUNCTIONS (called from rewriter.py)
# ═══════════════════════════════════════════════════════════════════════════════

def build_intelligence_context(all_items: list[dict]) -> str:
    """Build the headlines string for between-the-lines analysis."""
    return "\n".join(
        f"[{i['category'].upper()} | {i['source_name']}] {i['original_title']}"
        + (f" — {i['original_summary'][:80]}" if i.get("original_summary") else "")
        for i in all_items
    )


def get_story_keywords(item: dict) -> list[str]:
    """Extract key search terms from a news item."""
    text  = f"{item.get('original_title','')} {item.get('original_summary','')}".lower()
    words = re.findall(r'\b[a-z]{4,}\b', text)
    # Return the most distinctive words (exclude common ones)
    stopwords = {
        'that', 'this', 'with', 'from', 'they', 'have', 'will',
        'been', 'were', 'when', 'what', 'your', 'also', 'more',
        'said', 'says', 'after', 'over', 'than', 'into', 'some',
    }
    return [w for w in words if w not in stopwords][:5]
