"""
run.py — NewsAgent with full intelligence brain.

Pipeline:
  1.  Scrape RSS + Google News feeds
  2.  Enrich with article images
  3.  Fetch trending hashtags (X/Twitter)
  4.  Fetch inventions (ArXiv, GitHub, Product Hunt, MIT Tech Review...)
  5.  Fetch alternative source coverage per story
  6.  Generate all tweet formats locally via Ollama:
        ✍️  Rewrite       — clean factual tweet
        🔥  Hot Take      — thought-provoking angle
        🧵  Thread        — 4-tweet deep dive
        📊  Poll          — engagement poll
        🧠  Deep Read     — reading between the lines (per story)
        🌐  Mainstream    — official narrative
        🕵️  Alternative   — counter-narrative / questions
        💰  Cui Bono      — who benefits
  7.  Between-the-lines pass (global cross-story intelligence)
  8.  Hypocrisy pass
  9.  Invention tweets (science/tech breakthroughs)
  10. YouTube videos (optional)
  11. Build viewer → docs/index.html → GitHub Pages
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
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    try:
        import requests
        requests.get(f"{ollama_url}/api/tags", timeout=3)
        logger.info("Ollama available — using local LLM.")
        return
    except Exception:
        pass
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key and len(groq_key) > 10:
        logger.info("Ollama unavailable — falling back to Groq API.")
        return
    logger.error(
        "No LLM available.\n"
        "  Local: Install Ollama (https://ollama.com) and pull qwen2.5:3b\n"
        "  CI:    Add GROQ_API_KEY GitHub secret as fallback"
    )
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="NewsAgent Intelligence")
    parser.add_argument("--max",              type=int, default=3)
    parser.add_argument("--category",         type=str, default=None)
    parser.add_argument("--no-browser",       action="store_true")
    parser.add_argument("--skip-hypocrisy",   action="store_true")
    parser.add_argument("--skip-media",       action="store_true")
    parser.add_argument("--skip-youtube",     action="store_true")
    parser.add_argument("--skip-trending",    action="store_true")
    parser.add_argument("--skip-inventions",  action="store_true")
    parser.add_argument("--skip-conspiracy",  action="store_true")
    parser.add_argument("--skip-brain",       action="store_true")
    parser.add_argument("--yt-max",           type=int, default=3)
    args = parser.parse_args()

    check_api()
    DOCS_DIR.mkdir(exist_ok=True)
    if not IS_CI:
        OUT_DIR.mkdir(exist_ok=True)

    from rewriter import (
        generate_all_formats,
        generate_between_lines,
        generate_hypocrisy_tweets,
        generate_invention_tweet,
        generate_video_tweet,
    )

    # ── 1. Scrape news ─────────────────────────────────────────────
    from scraper import scrape_all, NEWS_SOURCES, GOOGLE_NEWS_SOURCES

    if args.category:
        if args.category not in DISPLAY_CAT_FILTER:
            logger.error(f"Unknown category.")
            sys.exit(1)
        cats = DISPLAY_CAT_FILTER[args.category]
        import scraper as _s
        orig_rss, orig_gn = dict(_s.NEWS_SOURCES), dict(_s.GOOGLE_NEWS_SOURCES)
        _s.NEWS_SOURCES        = {k: v for k, v in orig_rss.items() if k in cats}
        _s.GOOGLE_NEWS_SOURCES = {k: v for k, v in orig_gn.items()  if k in cats}
        raw_items = scrape_all(max_per_source=args.max)
        _s.NEWS_SOURCES, _s.GOOGLE_NEWS_SOURCES = orig_rss, orig_gn
    else:
        raw_items = scrape_all(max_per_source=args.max)

    if not raw_items:
        logger.warning("No items scraped.")
        sys.exit(0)
    logger.info(f"\n📰 Scraped {len(raw_items)} news items.\n")

    # ── 2. Enrich with images ──────────────────────────────────────
    if not args.skip_media:
        from media_scraper import enrich_with_article_media
        raw_items = enrich_with_article_media(raw_items)

    # ── 3. Fetch trending hashtags ─────────────────────────────────
    all_trending: dict = {}
    if not args.skip_trending:
        logger.info("\n🔥 Fetching trending hashtags...\n")
        from trending import fetch_all_trending
        all_trending = fetch_all_trending()

    # Combined trending list (for global passes)
    combined_trending = []
    for tags in all_trending.values():
        for t in tags:
            if t not in combined_trending:
                combined_trending.append(t)
    combined_trending = combined_trending[:30]

    # ── 4. Fetch inventions ────────────────────────────────────────
    inventions = []
    if not args.skip_inventions:
        logger.info("\n🔬 Fetching breakthroughs and inventions...\n")
        from intelligence import (
            fetch_inventions, github_trending,
            get_story_keywords, fetch_alt_coverage,
        )
        inventions = fetch_inventions(max_per_source=args.max)
        inventions += github_trending()
        logger.info(f"Found {len(inventions)} breakthroughs total.")
    else:
        from intelligence import get_story_keywords, fetch_alt_coverage

    # ── 5. Generate tweet content for news ────────────────────────
    results = []
    total   = len(raw_items)

    for i, item in enumerate(raw_items, 1):
        cat           = item["category"]
        trending_tags = all_trending.get(cat, [])
        logger.info(
            f"[{i:>3}/{total}] [{cat.upper():<12}] "
            f"{item['source_name']}: {item['original_title'][:50]}..."
        )

        # Fetch alt coverage for this story (unless skip_conspiracy)
        alt_coverage = []
        if not args.skip_conspiracy:
            keywords    = get_story_keywords(item)
            alt_coverage = fetch_alt_coverage(keywords, max_items=3)

        content = generate_all_formats(
            title        = item["original_title"],
            summary      = item["original_summary"],
            category     = cat,
            source       = item["source_name"],
            trending_tags = trending_tags,
            alt_coverage  = alt_coverage,
        )

        results.append({
            "source_url":       item["source_url"],
            "original_title":   item["original_title"],
            "original_summary": item["original_summary"],
            "source_name":      item["source_name"],
            "category":         cat,
            "image_url":        item.get("image_url"),
            "youtube_id":       item.get("youtube_id"),
            "video_url":        item.get("video_url"),
            "content":          content,
        })

    logger.info(f"\n✅ Generated content for {len(results)} news items.\n")

    # ── 6. Between-the-lines global pass ──────────────────────────
    between_lines = []
    if not args.skip_brain:
        logger.info("\n🧠 Reading between the lines (global intelligence pass)...\n")
        between_lines = generate_between_lines(
            raw_items, trending_tags=combined_trending
        )

    # ── 7. Hypocrisy pass ─────────────────────────────────────────
    hypocrisy = []
    if not args.skip_hypocrisy:
        hypocrisy = generate_hypocrisy_tweets(
            raw_items, trending_tags=combined_trending
        )

    # ── 8. Invention tweets ────────────────────────────────────────
    invention_results = []
    if inventions and not args.skip_inventions:
        logger.info(f"\n🔬 Generating tweets for {len(inventions)} breakthroughs...\n")
        for inv in inventions:
            cat           = inv.get("category", "science")
            trending_tags = all_trending.get(cat, combined_trending[:10])
            tweet         = generate_invention_tweet(
                title        = inv["title"],
                summary      = inv["summary"],
                source       = inv["source"],
                category     = cat,
                trending_tags = trending_tags,
            )
            invention_results.append({**inv, "tweet": tweet})

    # ── 9. YouTube videos ─────────────────────────────────────────
    videos = []
    if not args.skip_youtube:
        from media_scraper import fetch_youtube_channels, fetch_youtube_trending
        yt_ch  = fetch_youtube_channels(max_per_channel=args.yt_max)
        yt_tr  = fetch_youtube_trending(os.getenv("YOUTUBE_API_KEY",""), 10)
        seen   = set()
        for v in yt_tr + yt_ch:
            if v["video_id"] not in seen:
                seen.add(v["video_id"])
                videos.append(v)
        logger.info(f"\n📹 {len(videos)} YouTube videos...\n")
        for idx, vid in enumerate(videos, 1):
            tags = all_trending.get(vid["category"], [])
            logger.info(f"  [YT {idx}/{len(videos)}] {vid['title'][:50]}...")
            vid["tweet_content"] = generate_video_tweet(
                vid["title"], vid["channel"], vid.get("description",""),
                vid["category"], vid["url"], trending_tags=tags,
            )

    # ── 10. Save JSON backup ───────────────────────────────────────
    if not IS_CI:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        payload = {
            "news":          results,
            "hypocrisy":     hypocrisy,
            "between_lines": between_lines,
            "inventions":    invention_results,
            "videos":        videos,
            "trending":      all_trending,
        }
        json_path = OUT_DIR / f"tweets_{ts}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 JSON saved → {json_path}")

    # ── 11. Generate viewer ────────────────────────────────────────
    from viewer import generate_viewer
    viewer_path = DOCS_DIR / "index.html"
    generate_viewer(
        results, hypocrisy, videos, str(viewer_path),
        between_lines=between_lines,
        inventions=invention_results,
    )

    if IS_CI:
        repo = os.getenv("GITHUB_REPOSITORY", "your/NewsAgent")
        user, repo_name = repo.split("/")
        logger.info(f"🌐 Live: https://{user}.github.io/{repo_name}/")
    else:
        logger.info(f"🌐 Viewer → {viewer_path}")

    if not args.no_browser and not IS_CI:
        webbrowser.open(viewer_path.resolve().as_uri())

    logger.info("\n✔ Done!\n")


if __name__ == "__main__":
    main()
