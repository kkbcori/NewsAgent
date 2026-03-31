"""
media_scraper.py — Three media enrichment systems:

1. enrich_with_article_media(items)
       Fetches og:image, og:video, embedded YouTube IDs from article pages.
       Fills gaps where RSS feeds don't carry media.

2. fetch_youtube_channels(max_per_channel)
       Pulls latest videos from popular Telugu/India YouTube channels via RSS.
       No API key needed.

3. fetch_youtube_trending(api_key, max_results)
       Fetches YouTube trending videos for India via Data API v3.
       Requires YOUTUBE_API_KEY. Falls back gracefully if not set.
"""

import re
import logging
import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT      = 6    # seconds per article page
MAX_ENRICH_ITEMS     = 60   # cap to keep CI runs under 10 min

YT_CHANNEL_RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
YT_VIDEO_URL   = "https://www.youtube.com/watch?v={video_id}"
YT_THUMB_URL   = "https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

YT_EMBED_RE  = re.compile(r'youtube\.com/embed/([A-Za-z0-9_-]{11})')
YT_WATCH_RE  = re.compile(r'[?&]v=([A-Za-z0-9_-]{11})')
YT_SHORT_RE  = re.compile(r'youtu\.be/([A-Za-z0-9_-]{11})')

# ── YouTube channel definitions ───────────────────────────────────────────────
# To find a channel ID: go to channel → About → Share → Copy Channel ID
# Or use: https://commentpicker.com/youtube-channel-id.php

YOUTUBE_CHANNELS = {
    "telugu": [
        {"name": "TV9 Telugu",        "channel_id": "UCSnCjDMQQlxR2B9psBXE3_A"},
        {"name": "Sakshi TV",         "channel_id": "UCu1bNGCcpLXHMwLmrTECkRA"},
        {"name": "NTV Telugu",        "channel_id": "UCbMCLFj6k_IrHgE7KoEpOHA"},
        {"name": "10TV News",         "channel_id": "UCKdgPiCYW8sEWiEMoOEtm2g"},
        {"name": "ABN Andhra Jyothi", "channel_id": "UCgbMJOxB5ZGhf9gHmxV1zHw"},
        {"name": "V6 News Telugu",    "channel_id": "UCckBsRNk8-9HFKKrNi13_jw"},
    ],
    "telugu_film": [
        {"name": "Aditya Music",      "channel_id": "UCoiRToAqBb8Ee4EMQKLV1bg"},
        {"name": "T-Series Telugu",   "channel_id": "UCZ1VFv5HVdFxbSaRR2PGOYQ"},
        {"name": "Goldmines Telugu",  "channel_id": "UCe36g-OKgJzGkKkKGfQmVAg"},
        {"name": "Sri Balaji Video",  "channel_id": "UCRMlx4q6GKYM_2sVEO5voEg"},
        {"name": "ETV Cinema",        "channel_id": "UCW9drKrPkM94y5_w4qAA9cQ"},
        {"name": "Suresh Productions","channel_id": "UCwViVZ6SFX6YlJGJEXVRp9g"},
    ],
    "india": [
        {"name": "NDTV",              "channel_id": "UCZFMm1mMw0F81Z37aaEzTUA"},
        {"name": "India Today",       "channel_id": "UCYPvAwZP8pZhSMW8qs7cVCw"},
        {"name": "Aaj Tak",           "channel_id": "UCt4t-jeY85JegMlZ-E5UWuQ"},
        {"name": "Republic TV",       "channel_id": "UCrBszZkXaAK9LBYTxCTRz1w"},
        {"name": "The Wire",          "channel_id": "UCV7SEP7bGi2qCUc0LGqPjew"},
    ],
    "usa": [
        {"name": "NBC News",          "channel_id": "UCeY0bbntWzzVIaj2z3QigXg"},
        {"name": "CNN",               "channel_id": "UCupvZG-5ko_eiXAupbDfxWw"},
        {"name": "AP Archive",        "channel_id": "UCujbToMRMsQYvDsKiHq7TRg"},
    ],
    "world": [
        {"name": "Al Jazeera English","channel_id": "UCNye-wNBqNL5ZzHSJj3l8Bg"},
        {"name": "DW News",           "channel_id": "UCknLrEdhRCp1aegoMqRaCZg"},
        {"name": "BBC News",          "channel_id": "UC16niRr50-MSBwiO3YDb3RA"},
    ],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _yt_id(url: str) -> str | None:
    for pattern in (YT_EMBED_RE, YT_WATCH_RE, YT_SHORT_RE):
        m = pattern.search(url or "")
        if m:
            return m.group(1)
    return None


def _yt_thumb(video_id: str) -> str:
    return YT_THUMB_URL.format(video_id=video_id)


_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsAgentBot/1.0)"}


# ── 1. Article page enrichment ────────────────────────────────────────────────

def _fetch_article_media(url: str) -> dict:
    """Extract og:image, og:video, embedded YouTube ID from an article page."""
    result = {"image_url": None, "video_url": None, "youtube_id": None}
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=_HEADERS)
        if not resp.ok:
            return result
        soup = BeautifulSoup(resp.text, "html.parser")

        # og:image
        for prop in ("og:image", "og:image:secure_url", "twitter:image"):
            tag = soup.find("meta", property=prop) or \
                  soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                result["image_url"] = tag["content"]
                break

        # og:video / YouTube embed
        for prop in ("og:video", "og:video:url", "og:video:secure_url"):
            tag = soup.find("meta", property=prop)
            if tag and tag.get("content"):
                result["video_url"] = tag["content"]
                yt = _yt_id(tag["content"])
                if yt:
                    result["youtube_id"] = yt
                break

        # YouTube iframes (if no og:video found)
        if not result["youtube_id"]:
            for iframe in soup.find_all("iframe", src=True):
                yt = _yt_id(iframe["src"])
                if yt:
                    result["youtube_id"] = yt
                    result["video_url"]  = YT_VIDEO_URL.format(video_id=yt)
                    if not result["image_url"]:
                        result["image_url"] = _yt_thumb(yt)
                    break

    except Exception as e:
        logger.debug(f"Article fetch failed ({url[:60]}): {e}")
    return result


def enrich_with_article_media(items: list[dict]) -> list[dict]:
    """
    For items missing image_url, scrape the article page to get
    og:image, og:video, and embedded YouTube IDs.
    Capped at MAX_ENRICH_ITEMS to avoid slow CI runs.
    """
    need = [i for i in items if not i.get("image_url")]
    batch = need[:MAX_ENRICH_ITEMS]
    logger.info(f"[MEDIA] Article enrichment: fetching {len(batch)} pages…")

    got_img = got_vid = 0
    for item in batch:
        media = _fetch_article_media(item["source_url"])
        if media["image_url"] and not item.get("image_url"):
            item["image_url"] = media["image_url"]
            got_img += 1
        if media["youtube_id"] and not item.get("youtube_id"):
            item["youtube_id"] = media["youtube_id"]
            item["video_url"]  = media["video_url"]
            got_vid += 1

    logger.info(f"[MEDIA] Got {got_img} images, {got_vid} YouTube embeds from articles.")
    return items


# ── 2. YouTube channel RSS (no API key) ──────────────────────────────────────

def fetch_youtube_channels(max_per_channel: int = 5) -> list[dict]:
    """
    Fetch latest videos from the hardcoded channel list via YouTube RSS.
    Returns list of video dicts ready for the viewer + tweet generation.
    """
    all_videos = []

    for display_cat, channels in YOUTUBE_CHANNELS.items():
        logger.info(f"[YT RSS] {display_cat.upper()}")
        for ch in channels:
            try:
                url  = YT_CHANNEL_RSS.format(channel_id=ch["channel_id"])
                feed = feedparser.parse(url)
                count = 0
                for entry in feed.entries[:max_per_channel]:
                    # feedparser puts the video id in yt_videoid
                    vid_id = getattr(entry, "yt_videoid", None) or \
                             _yt_id(entry.get("link", ""))
                    if not vid_id:
                        continue
                    title = (entry.get("title") or "").strip()
                    if not title:
                        continue
                    desc = ""
                    if hasattr(entry, "media_description"):
                        desc = entry.media_description or ""
                    elif entry.get("summary"):
                        desc = entry.summary or ""
                    desc = re.sub(r"<[^>]+>", "", desc).strip()[:300]

                    all_videos.append({
                        "video_id":    vid_id,
                        "title":       title,
                        "channel":     ch["name"],
                        "category":    display_cat,
                        "url":         YT_VIDEO_URL.format(video_id=vid_id),
                        "thumbnail":   _yt_thumb(vid_id),
                        "published":   entry.get("published", ""),
                        "description": desc,
                    })
                    count += 1
                logger.info(f"  {ch['name']}: {count} videos")
            except Exception as e:
                logger.warning(f"  {ch['name']} failed: {e}")

    logger.info(f"[YT RSS] Total: {len(all_videos)} channel videos")
    return all_videos


# ── 3. YouTube Data API v3 — trending India ───────────────────────────────────

def fetch_youtube_trending(api_key: str, max_results: int = 15) -> list[dict]:
    """
    Fetch YouTube trending videos for India via Data API v3.
    Falls back gracefully if no API key provided.
    """
    if not api_key or "YOUR_" in api_key:
        logger.info("[YT API] No API key — skipping trending fetch.")
        return []
    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part":       "snippet,statistics",
                "chart":      "mostPopular",
                "regionCode": "IN",
                "maxResults": max_results,
                "key":        api_key,
            },
            timeout=10,
        )
        resp.raise_for_status()
        videos = []
        for v in resp.json().get("items", []):
            vid_id = v["id"]
            snip   = v["snippet"]
            videos.append({
                "video_id":    vid_id,
                "title":       snip.get("title", ""),
                "channel":     snip.get("channelTitle", ""),
                "category":    "india",
                "url":         YT_VIDEO_URL.format(video_id=vid_id),
                "thumbnail":   snip.get("thumbnails", {})
                               .get("high", {}).get("url") or _yt_thumb(vid_id),
                "published":   snip.get("publishedAt", ""),
                "description": snip.get("description", "")[:300],
                "trending":    True,
            })
        logger.info(f"[YT API] Trending India: {len(videos)} videos")
        return videos
    except Exception as e:
        logger.warning(f"[YT API] Failed: {e}")
        return []
