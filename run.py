"""
run.py — Main entry point for NewsAgent.

Pipeline:
  1. Scrape RSS + Google News feeds
  2. Enrich with article images
  3. Fetch live trending hashtags from X (trends24.in + getdaytrends.com)
  4. Generate all 4 tweet formats locally via Ollama (fallback: Groq)
     — trending hashtags injected into every tweet prompt
  5. Hypocrisy pass with trending hashtags
  6. YouTube videos (optional)
  7. Build viewer HTML → docs/index.html → GitHub Pages
"""

import argparse
import json
import logging
import os
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

IS_CI    = os.getenv("GITHUB_ACTIONS") == "true"
DOCS_DIR = Path("docs")
OUT_DIR  = Path("output")

DISPLAY_CAT_FILTER = {
    "usa":         ["usa"],
    "world":       ["world"],
    "india":       ["india"],
    "telugu":      ["telugu"],
    "telugu_film": ["telugu_film"],
}


def check_api():
    groq_key = os.getenv("GROQ_API_KEY", "")
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    # Try Ollama first
    try:
        import requests
        requests.get(f"{ollama_url}/api/tags", timeout=3)
        logger.info("Ollama detected — using local LLM.")
        return
    except Exception:
        pass
    # Fall back to Groq
    if groq_key and len(groq_key) > 10:
        logger.info("Ollama not available — using Groq API as fallback.")
        return
    logger.error(
        "Neither Ollama nor GROQ_API_KEY available.\n"
        "  Local: Install Ollama from https://ollama.com\n"
        "  CI:    Add GROQ_API_KEY secret as fallback"
    )
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="NewsAgent")
    parser.add_argument("--max",            type=int,  default=3)
    parser.add_argument("--category",       type=str,  default=None)
    parser.add_argument("--no-browser",     action="store_true")
    parser.add_argument("--skip-hypocrisy", action="store_true")
    parser.add_argument("--skip-media",     action="store_true")
    parser.add_argument("--skip-youtube",   action="store_true")
    parser.add_argument("--skip-trending",  action="store_true")
    parser.add_argument("--yt-max",         type=int,  default=3)
    args = parser.parse_args()

    check_api()
    DOCS_DIR.mkdir(exist_ok=True)
    if not IS_CI:
        OUT_DIR.mkdir(exist_ok=True)

    # ── 1. Scrape ──────────────────────────────────────────────────
    from scraper import scrape_all, NEWS_SOURCES, GOOGLE_NEWS_SOURCES

    if args.category:
        if args.category not in DISPLAY_CAT_FILTER:
            logger.error(f"Unknown category. Use: usa, world, india, telugu, telugu_film")
            sys.exit(1)
        cats = DISPLAY_CAT_FILTER[args.category]
        import scraper as _s
        orig_rss = dict(_s.NEWS_SOURCES)
        orig_gn  = dict(_s.GOOGLE_NEWS_SOURCES)
        _s.NEWS_SOURCES        = {k: v for k, v in orig_rss.items() if k in cats}
        _s.GOOGLE_NEWS_SOURCES = {k: v for k, v in orig_gn.items()  if k in cats}
        raw_items = scrape_all(max_per_source=args.max)
        _s.NEWS_SOURCES        = orig_rss
        _s.GOOGLE_NEWS_SOURCES = orig_gn
    else:
        raw_items = scrape_all(max_per_source=args.max)

    if not raw_items:
        logger.warning("No items scraped.")
        sys.exit(0)

    logger.info(f"\n📰 Scraped {len(raw_items)} unique news items.\n")

    # ── 2. Enrich with article images ──────────────────────────────
    if not args.skip_media:
        from media_scraper import enrich_with_article_media
        raw_items = enrich_with_article_media(raw_items)
    else:
        logger.info("Skipping article media enrichment.")

    # ── 3. Fetch trending hashtags ─────────────────────────────────
    all_trending: dict[str, list[str]] = {}
    if not args.skip_trending:
        logger.info("\n🔥 Fetching trending hashtags from X...\n")
        from trending import fetch_all_trending
        all_trending = fetch_all_trending()
    else:
        logger.info("Skipping trending hashtags.")

    # ── 4. Generate tweet content ──────────────────────────────────
    from rewriter import (
        generate_all_formats,
        generate_hypocrisy_tweets,
        generate_video_tweet,
    )

    results = []
    total   = len(raw_items)

    for i, item in enumerate(raw_items, 1):
        category = item["category"]
        trending_tags = all_trending.get(category, [])
        logger.info(
            f"[{i:>3}/{total}] [{category.upper():<12}] "
            f"{item['source_name']}: {item['original_title'][:50]}..."
        )
        content = generate_all_formats(
            item["original_title"],
            item["original_summary"],
            category,
            trending_tags=trending_tags,
        )
        results.append({
            "source_url":       item["source_url"],
            "original_title":   item["original_title"],
            "original_summary": item["original_summary"],
            "source_name":      item["source_name"],
            "category":         category,
            "image_url":        item.get("image_url"),
            "youtube_id":       item.get("youtube_id"),
            "video_url":        item.get("video_url"),
            "content":          content,
        })

    logger.info(f"\n✅ Generated tweet content for {len(results)} items.\n")

    # ── 5. Hypocrisy pass ──────────────────────────────────────────
    hypocrisy = []
    if not args.skip_hypocrisy:
        # Use combined trending tags for hypocrisy (world + india)
        combined_trending = []
        for tags in all_trending.values():
            for t in tags:
                if t not in combined_trending:
                    combined_trending.append(t)
        hypocrisy = generate_hypocrisy_tweets(
            raw_items, trending_tags=combined_trending[:30]
        )
    else:
        logger.info("Skipping hypocrisy pass.")

    # ── 6. YouTube videos ──────────────────────────────────────────
    videos = []
    if not args.skip_youtube:
        from media_scraper import fetch_youtube_channels, fetch_youtube_trending
        yt_channel  = fetch_youtube_channels(max_per_channel=args.yt_max)
        yt_trending = fetch_youtube_trending(
            os.getenv("YOUTUBE_API_KEY", ""), max_results=10
        )
        seen = set()
        for v in yt_trending + yt_channel:
            if v["video_id"] not in seen:
                seen.add(v["video_id"])
                videos.append(v)

        logger.info(f"\n📹 {len(videos)} YouTube videos. Generating tweets...\n")
        for i, vid in enumerate(videos, 1):
            trending_tags = all_trending.get(vid["category"], [])
            logger.info(
                f"  [YT {i}/{len(videos)}] {vid['channel']}: {vid['title'][:50]}..."
            )
            vid["tweet_content"] = generate_video_tweet(
                vid["title"], vid["channel"], vid.get("description", ""),
                vid["category"], vid["url"],
                trending_tags=trending_tags,
            )
    else:
        logger.info("Skipping YouTube videos.")

    # ── 7. Save JSON backup (local only) ──────────────────────────
    if not IS_CI:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        json_path = OUT_DIR / f"tweets_{ts}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {"news": results, "hypocrisy": hypocrisy, "videos": videos,
                 "trending": all_trending},
                f, ensure_ascii=False, indent=2,
            )
        logger.info(f"💾 JSON saved → {json_path}")

    # ── 8. Generate viewer ─────────────────────────────────────────
    from viewer import generate_viewer
    viewer_path = DOCS_DIR / "index.html"
    generate_viewer(results, hypocrisy, videos, str(viewer_path))

    if IS_CI:
        repo = os.getenv("GITHUB_REPOSITORY", "your-username/NewsAgent")
        user, repo_name = repo.split("/")
        logger.info(f"🌐 Live at: https://{user}.github.io/{repo_name}/")
    else:
        logger.info(f"🌐 Viewer → {viewer_path}")

    if not args.no_browser and not IS_CI:
        webbrowser.open(viewer_path.resolve().as_uri())

    logger.info("\n✔ Done!\n")


if __name__ == "__main__":
    main()
