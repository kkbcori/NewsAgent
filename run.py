"""
run.py — Main entry point for NewsAgent.
Now uses Groq API (FREE) instead of Claude API.

Local usage:
    python run.py                      # full run, opens browser
    python run.py --max 3              # 3 items per source (faster)
    python run.py --category usa       # one category only
    python run.py --no-browser         # don't auto-open viewer
    python run.py --skip-hypocrisy     # skip hypocrisy pass
    python run.py --skip-youtube       # skip YouTube videos
    python run.py --skip-media         # skip article image enrichment

GitHub Actions: runs on cron, outputs to docs/index.html (GitHub Pages)
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


def check_api_key():
    key = os.getenv("GROQ_API_KEY", "")
    if not key or key.startswith("gsk_...") or len(key) < 10:
        logger.error("GROQ_API_KEY not set.")
        if IS_CI:
            logger.error("Add it in: Settings -> Secrets -> GROQ_API_KEY")
        else:
            logger.error("Copy .env.example -> .env and fill in your Groq key.")
            logger.error("Get a free key at: https://console.groq.com")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="NewsAgent — AI tweet generator (powered by Groq, free)")
    parser.add_argument("--max",            type=int,  default=5,    help="Max items per RSS source")
    parser.add_argument("--category",       type=str,  default=None, help="usa|world|india|telugu|telugu_film")
    parser.add_argument("--no-browser",     action="store_true",     help="Don't auto-open viewer")
    parser.add_argument("--skip-hypocrisy", action="store_true",     help="Skip hypocrisy pass")
    parser.add_argument("--skip-media",     action="store_true",     help="Skip article image enrichment")
    parser.add_argument("--skip-youtube",   action="store_true",     help="Skip YouTube videos")
    parser.add_argument("--yt-max",         type=int,  default=3,    help="Max videos per YouTube channel")
    args = parser.parse_args()

    check_api_key()
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
        _s.NEWS_SOURCES          = {k: v for k, v in orig_rss.items() if k in cats}
        _s.GOOGLE_NEWS_SOURCES   = {k: v for k, v in orig_gn.items()  if k in cats}
        raw_items = scrape_all(max_per_source=args.max)
        _s.NEWS_SOURCES          = orig_rss
        _s.GOOGLE_NEWS_SOURCES   = orig_gn
    else:
        raw_items = scrape_all(max_per_source=args.max)

    if not raw_items:
        logger.warning("No items scraped. Check internet connection.")
        sys.exit(0)

    logger.info(f"\n📰 Scraped {len(raw_items)} unique news items.\n")

    # ── 2. Enrich with article images ──────────────────────────────
    if not args.skip_media:
        from media_scraper import enrich_with_article_media
        raw_items = enrich_with_article_media(raw_items)
    else:
        logger.info("Skipping article media enrichment.")

    # ── 3. Generate tweet content ──────────────────────────────────
    from rewriter import generate_all_formats, generate_hypocrisy_tweets, generate_video_tweet

    results = []
    total   = len(raw_items)

    for i, item in enumerate(raw_items, 1):
        logger.info(f"[{i:>3}/{total}] [{item['category'].upper():<12}] "
                    f"{item['source_name']}: {item['original_title'][:50]}...")
        content = generate_all_formats(
            item["original_title"], item["original_summary"], item["category"]
        )
        results.append({
            "source_url":       item["source_url"],
            "original_title":   item["original_title"],
            "original_summary": item["original_summary"],
            "source_name":      item["source_name"],
            "category":         item["category"],
            "image_url":        item.get("image_url"),
            "youtube_id":       item.get("youtube_id"),
            "video_url":        item.get("video_url"),
            "content":          content,
        })

    logger.info(f"\n✅ Generated tweet content for {len(results)} items.\n")

    # ── 4. Hypocrisy pass ──────────────────────────────────────────
    hypocrisy = []
    if not args.skip_hypocrisy:
        hypocrisy = generate_hypocrisy_tweets(raw_items)
    else:
        logger.info("Skipping hypocrisy pass.")

    # ── 5. YouTube videos ──────────────────────────────────────────
    videos = []
    if not args.skip_youtube:
        from media_scraper import fetch_youtube_channels, fetch_youtube_trending
        yt_channel = fetch_youtube_channels(max_per_channel=args.yt_max)
        yt_trending = fetch_youtube_trending(
            os.getenv("YOUTUBE_API_KEY", ""), max_results=10
        )
        seen = set()
        for v in yt_trending + yt_channel:
            if v["video_id"] not in seen:
                seen.add(v["video_id"])
                videos.append(v)

        logger.info(f"\n📹 {len(videos)} YouTube videos. Generating tweet content...\n")
        for i, vid in enumerate(videos, 1):
            logger.info(f"  [YT {i}/{len(videos)}] {vid['channel']}: {vid['title'][:50]}...")
            vid["tweet_content"] = generate_video_tweet(
                vid["title"], vid["channel"], vid.get("description", ""),
                vid["category"], vid["url"],
            )
    else:
        logger.info("Skipping YouTube videos.")

    # ── 6. Save JSON backup (local only) ──────────────────────────
    if not IS_CI:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        json_path = OUT_DIR / f"tweets_{ts}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"news": results, "hypocrisy": hypocrisy, "videos": videos},
                      f, ensure_ascii=False, indent=2)
        logger.info(f"💾 JSON saved -> {json_path}")

    # ── 7. Generate viewer ─────────────────────────────────────────
    from viewer import generate_viewer
    viewer_path = DOCS_DIR / "index.html"
    generate_viewer(results, hypocrisy, videos, str(viewer_path))

    if IS_CI:
        repo = os.getenv("GITHUB_REPOSITORY", "your-username/NewsAgent")
        user, repo_name = repo.split("/")
        logger.info(f"🌐 Live at: https://{user}.github.io/{repo_name}/")
    else:
        logger.info(f"🌐 Viewer saved -> {viewer_path}")

    # ── 8. Open browser (local only) ──────────────────────────────
    if not args.no_browser and not IS_CI:
        webbrowser.open(viewer_path.resolve().as_uri())

    logger.info("\n✔ Done!\n")


if __name__ == "__main__":
    main()
