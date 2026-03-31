"""
run.py — Main entry point for NewsAgent.

Pipeline:
  1. Scrape RSS feeds  (scraper.py)
  2. Enrich with article media — og:image, og:video, YouTube embeds  (media_scraper.py)
  3. Generate tweet content via Claude  (rewriter.py)
  4. Hypocrisy pass  (rewriter.py)
  5. Fetch YouTube channel videos via RSS  (media_scraper.py)
  6. [Optional] Fetch YouTube trending India via API  (media_scraper.py)
  7. Generate tweet content for videos  (rewriter.py)
  8. Build viewer HTML → docs/index.html  (viewer.py)

Local:    opens docs/index.html in browser
GitHub:   commits docs/index.html, served by GitHub Pages
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
    "world":       ["world", "europe", "australia"],
    "india":       ["india", "hindi"],
    "telugu":      ["telugu"],
    "telugu_film": ["telugu_film"],
}


def check_api_key():
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key.startswith("sk-ant-..."):
        logger.error("❌  ANTHROPIC_API_KEY not set.")
        if IS_CI:
            logger.error("    Add it in: Settings → Secrets → ANTHROPIC_API_KEY")
        else:
            logger.error("    Copy .env.example → .env and fill in your key.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="NewsAgent — AI tweet content generator")
    parser.add_argument("--max",              type=int,  default=5,     help="Max items per RSS source")
    parser.add_argument("--category",         type=str,  default=None,  help="usa|world|india|telugu|telugu_film")
    parser.add_argument("--no-browser",       action="store_true",      help="Don't auto-open viewer")
    parser.add_argument("--skip-hypocrisy",   action="store_true",      help="Skip hypocrisy pass")
    parser.add_argument("--skip-media",       action="store_true",      help="Skip article media enrichment")
    parser.add_argument("--skip-youtube",     action="store_true",      help="Skip YouTube channel videos")
    parser.add_argument("--yt-max",           type=int,  default=3,     help="Max videos per YouTube channel")
    args = parser.parse_args()

    check_api_key()
    DOCS_DIR.mkdir(exist_ok=True)
    if not IS_CI:
        OUT_DIR.mkdir(exist_ok=True)

    # ── 1. Scrape news RSS ────────────────────────────────────────
    from scraper import scrape_all, NEWS_SOURCES

    if args.category:
        if args.category not in DISPLAY_CAT_FILTER:
            logger.error(f"Unknown category. Use: usa, world, india, telugu, telugu_film")
            sys.exit(1)
        import scraper as _s
        orig = dict(_s.NEWS_SOURCES)
        _s.NEWS_SOURCES = {k: v for k, v in orig.items()
                           if k in DISPLAY_CAT_FILTER[args.category]}
        raw_items = scrape_all(max_per_source=args.max)
        _s.NEWS_SOURCES = orig
    else:
        raw_items = scrape_all(max_per_source=args.max)

    if not raw_items:
        logger.warning("No items scraped.")
        sys.exit(0)

    logger.info(f"\n📰 Scraped {len(raw_items)} news items.\n")

    # ── 2. Enrich with article images & embedded videos ───────────
    if not args.skip_media:
        from media_scraper import enrich_with_article_media
        raw_items = enrich_with_article_media(raw_items)
    else:
        logger.info("Skipping article media enrichment.")

    # ── 3. Generate tweet content for news items ──────────────────
    from rewriter import generate_all_formats, generate_hypocrisy_tweets, generate_video_tweet

    results = []
    total   = len(raw_items)

    for i, item in enumerate(raw_items, 1):
        logger.info(f"[{i:>3}/{total}] [{item['category'].upper():<12}] "
                    f"{item['source_name']}: {item['original_title'][:50]}…")
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

    logger.info(f"\n✅ Generated tweet content for {len(results)} news items.\n")

    # ── 4. Hypocrisy pass ─────────────────────────────────────────
    hypocrisy = []
    if not args.skip_hypocrisy:
        hypocrisy = generate_hypocrisy_tweets(raw_items)
    else:
        logger.info("Skipping hypocrisy pass.")

    # ── 5. YouTube channel videos (RSS, no API key) ───────────────
    videos = []
    if not args.skip_youtube:
        from media_scraper import fetch_youtube_channels, fetch_youtube_trending

        yt_channel_videos = fetch_youtube_channels(max_per_channel=args.yt_max)

        # Optional: YouTube trending via API
        yt_api_key = os.getenv("YOUTUBE_API_KEY", "")
        yt_trending = fetch_youtube_trending(yt_api_key, max_results=10)

        # Merge (trending first, dedupe by video_id)
        seen_ids = set()
        for v in yt_trending + yt_channel_videos:
            if v["video_id"] not in seen_ids:
                seen_ids.add(v["video_id"])
                videos.append(v)

        logger.info(f"\n📹 {len(videos)} YouTube videos total. Generating tweet content…\n")

        # Generate tweet content for each video
        for i, vid in enumerate(videos, 1):
            logger.info(f"  [YT {i}/{len(videos)}] {vid['channel']}: {vid['title'][:50]}…")
            tweet_content = generate_video_tweet(
                title=vid["title"],
                channel=vid["channel"],
                description=vid.get("description", ""),
                category=vid["category"],
                video_url=vid["url"],
            )
            vid["tweet_content"] = tweet_content
    else:
        logger.info("Skipping YouTube videos.")

    # ── 6. Save JSON backup (local only) ─────────────────────────
    if not IS_CI:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        payload = {"news": results, "hypocrisy": hypocrisy, "videos": videos}
        json_path = OUT_DIR / f"tweets_{ts}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 JSON saved → {json_path}")

    # ── 7. Generate viewer ────────────────────────────────────────
    from viewer import generate_viewer
    viewer_path = DOCS_DIR / "index.html"
    generate_viewer(results, hypocrisy, videos, str(viewer_path))

    if IS_CI:
        repo = os.getenv("GITHUB_REPOSITORY", "your-username/NewsAgent")
        user, repo_name = repo.split("/")
        logger.info(f"🌐 Viewer → {viewer_path}  |  Live at: https://{user}.github.io/{repo_name}/")
    else:
        logger.info(f"🌐 Viewer saved → {viewer_path}")

    # ── 8. Open in browser (local only) ──────────────────────────
    if not args.no_browser and not IS_CI:
        webbrowser.open(viewer_path.resolve().as_uri())

    logger.info("\n✔ Done!\n")


if __name__ == "__main__":
    main()
