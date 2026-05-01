"""
run.py — NewsAgent with batch processing (FAST).

Key change: generate_all_formats_batch() processes ALL items at once
instead of one at a time. 400 LLM calls → 8 LLM calls.
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

IS_CI    = os.getenv("GITHUB_ACTIONS") == "true"
DOCS_DIR = Path("docs")
OUT_DIR  = Path("output")

DISPLAY_CAT_FILTER = {
    "usa":["usa"], "world":["world"], "india":["india"],
    "telugu":["telugu"], "telugu_film":["telugu_film"],
}


def check_api():
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    try:
        import requests
        requests.get(f"{ollama_url}/api/tags", timeout=3)
        logger.info("Ollama available.")
        return
    except Exception:
        pass
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key and len(groq_key) > 10:
        logger.info("Using Groq API.")
        return
    logger.error("No LLM available. Install Ollama or set GROQ_API_KEY.")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max",             type=int, default=3)
    parser.add_argument("--category",        type=str, default=None)
    parser.add_argument("--no-browser",      action="store_true")
    parser.add_argument("--skip-hypocrisy",  action="store_true")
    parser.add_argument("--skip-media",      action="store_true")
    parser.add_argument("--skip-youtube",    action="store_true")
    parser.add_argument("--skip-trending",   action="store_true")
    parser.add_argument("--skip-inventions", action="store_true")
    parser.add_argument("--skip-conspiracy", action="store_true")
    parser.add_argument("--skip-brain",      action="store_true")
    parser.add_argument("--yt-max",          type=int, default=3)
    args = parser.parse_args()

    check_api()
    DOCS_DIR.mkdir(exist_ok=True)
    if not IS_CI:
        OUT_DIR.mkdir(exist_ok=True)

    from rewriter import (
        generate_all_formats_batch,
        generate_between_lines,
        generate_hypocrisy_tweets,
        generate_invention_tweets_batch,
        generate_video_tweet,
    )

    # ── 1. Scrape ──────────────────────────────────────────────────
    from scraper import scrape_all, NEWS_SOURCES, GOOGLE_NEWS_SOURCES
    if args.category:
        cats = DISPLAY_CAT_FILTER.get(args.category)
        if not cats:
            logger.error("Unknown category.")
            sys.exit(1)
        import scraper as _s
        orig_rss, orig_gn = dict(_s.NEWS_SOURCES), dict(_s.GOOGLE_NEWS_SOURCES)
        _s.NEWS_SOURCES        = {k:v for k,v in orig_rss.items() if k in cats}
        _s.GOOGLE_NEWS_SOURCES = {k:v for k,v in orig_gn.items()  if k in cats}
        raw_items = scrape_all(max_per_source=args.max)
        _s.NEWS_SOURCES, _s.GOOGLE_NEWS_SOURCES = orig_rss, orig_gn
    else:
        raw_items = scrape_all(max_per_source=args.max)

    if not raw_items:
        logger.warning("No items scraped.")
        sys.exit(0)
    logger.info(f"\n📰 Scraped {len(raw_items)} items.\n")

    # ── 2. Enrich images ───────────────────────────────────────────
    if not args.skip_media:
        from media_scraper import enrich_with_article_media
        raw_items = enrich_with_article_media(raw_items)

    # ── 3. Trending hashtags ───────────────────────────────────────
    all_trending: dict = {}
    if not args.skip_trending:
        logger.info("\n🔥 Fetching trending hashtags...\n")
        from trending import fetch_all_trending
        all_trending = fetch_all_trending()

    combined_trending = []
    for tags in all_trending.values():
        for t in tags:
            if t not in combined_trending:
                combined_trending.append(t)
    combined_trending = combined_trending[:30]

    # ── 4. Inventions ──────────────────────────────────────────────
    inventions = []
    if not args.skip_inventions:
        logger.info("\n🔬 Fetching breakthroughs...\n")
        from intelligence import fetch_inventions, github_trending
        inventions = fetch_inventions(max_per_source=2) + github_trending()
        logger.info(f"Found {len(inventions)} breakthroughs.")

    # ── 5. Alt coverage ────────────────────────────────────────────
    alt_coverage_map: dict = {}
    if not args.skip_conspiracy:
        from intelligence import fetch_alt_coverage, get_story_keywords
        logger.info("\n🕵️  Fetching alternative source coverage...\n")
        for item in raw_items[:20]:  # limit to top 20 for speed
            kw = get_story_keywords(item)
            alts = fetch_alt_coverage(kw, max_items=2)
            if alts:
                alt_coverage_map[item["original_title"]] = alts

    # ── 6. BATCH generate all tweet formats ───────────────────────
    logger.info(f"\n🚀 Batch generating tweets for {len(raw_items)} items...\n")

    # Group by category so trending tags are relevant
    from collections import defaultdict
    by_cat = defaultdict(list)
    for item in raw_items:
        by_cat[item["category"]].append(item)

    # Process each category as a batch
    item_content_map: dict = {}
    for cat, cat_items in by_cat.items():
        trending_tags = all_trending.get(cat, combined_trending[:15])
        logger.info(f"\n[BATCH] Category: {cat.upper()} ({len(cat_items)} items)")
        contents = generate_all_formats_batch(cat_items, trending_tags=trending_tags)
        for item, content in zip(cat_items, contents):
            item_content_map[item["original_title"]] = content

    # ── 7. Assemble results ────────────────────────────────────────
    results = []
    for item in raw_items:
        content = item_content_map.get(item["original_title"], {})
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

    logger.info(f"\n✅ Generated content for {len(results)} items.\n")

    # ── 8. Between-the-lines global pass ──────────────────────────
    between_lines = []
    if not args.skip_brain:
        logger.info("\n🧠 Between-the-lines global pass...\n")
        between_lines = generate_between_lines(raw_items, trending_tags=combined_trending)

    # ── 9. Hypocrisy pass ─────────────────────────────────────────
    hypocrisy = []
    if not args.skip_hypocrisy:
        hypocrisy = generate_hypocrisy_tweets(raw_items, trending_tags=combined_trending)

    # ── 10. Invention tweets ───────────────────────────────────────
    invention_results = []
    if inventions and not args.skip_inventions:
        logger.info(f"\n🔬 Generating invention tweets (batch)...\n")
        inv_tweets = generate_invention_tweets_batch(inventions, trending_tags=combined_trending)
        for inv, tweet in zip(inventions, inv_tweets):
            invention_results.append({**inv, "tweet": tweet})

    # ── 11. YouTube videos ─────────────────────────────────────────
    videos = []
    if not args.skip_youtube:
        from media_scraper import fetch_youtube_channels, fetch_youtube_trending
        yt  = fetch_youtube_channels(max_per_channel=args.yt_max)
        yt += fetch_youtube_trending(os.getenv("YOUTUBE_API_KEY",""), 10)
        seen = set()
        for v in yt:
            if v["video_id"] not in seen:
                seen.add(v["video_id"])
                videos.append(v)
        for idx, vid in enumerate(videos, 1):
            logger.info(f"  [YT {idx}/{len(videos)}] {vid['title'][:50]}...")
            vid["tweet_content"] = generate_video_tweet(
                vid["title"], vid["channel"], vid.get("description",""),
                vid["category"], vid["url"],
                trending_tags=all_trending.get(vid["category"], []),
            )

    # ── 12. Save JSON backup ───────────────────────────────────────
    if not IS_CI:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        with open(OUT_DIR / f"tweets_{ts}.json", "w", encoding="utf-8") as f:
            json.dump({
                "news":results, "hypocrisy":hypocrisy,
                "between_lines":between_lines, "inventions":invention_results,
                "videos":videos, "trending":all_trending,
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 JSON saved.")

    # ── 13. Generate viewer ────────────────────────────────────────
    from viewer import generate_viewer
    viewer_path = DOCS_DIR / "index.html"
    generate_viewer(results, hypocrisy, videos, str(viewer_path),
                    between_lines=between_lines, inventions=invention_results)

    if IS_CI:
        repo = os.getenv("GITHUB_REPOSITORY","your/NewsAgent")
        u, r = repo.split("/")
        logger.info(f"🌐 Live: https://{u}.github.io/{r}/")
    else:
        logger.info(f"🌐 Viewer → {viewer_path}")

    if not args.no_browser and not IS_CI:
        webbrowser.open(viewer_path.resolve().as_uri())

    logger.info("\n✔ Done!\n")


if __name__ == "__main__":
    main()
