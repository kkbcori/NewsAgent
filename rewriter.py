"""
rewriter.py — Claude AI tweet generator.

generate_all_formats(title, summary, category)
    → Rewrite, Hot Take, Thread, Poll for a news item.

generate_video_tweet(title, channel, description, category)
    → Rewrite + Hot Take for a YouTube video (2 formats, not 4).

generate_hypocrisy_tweets(all_items)
    → Scans all headlines, picks ironic ones, writes sarcastic tweets.
"""

import anthropic
import json
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM = (
    "You are a sharp, witty social media content creator for X (Twitter). "
    "You write for a savvy Indian and global audience. Your tone matches the content: "
    "informative for news, enthusiastic for films, devastating for hypocrisy."
)

CATEGORY_TONE = {
    "usa": "This is US news. Write for an Indian-American or globally aware audience watching US politics.",
    "world": "This is international news (Europe, Australia, global). Write with global perspective for Indian readers.",
    "india": "This is Indian news (may include Hindi source content). Write for politically aware Indians.",
    "telugu": "This is Telugu/AP/Telangana regional news. Keep it punchy and relevant to Telugu audiences.",
    "telugu_film": "This is Tollywood / Telugu cinema news. Be enthusiastic, fan-aware, and entertaining.",
}

PROMPTS = {
    "rewrite": """\
Rewrite this news as a punchy, original tweet.{tone}

Rules:
- Max 260 characters
- Do NOT copy the original headline verbatim
- Max 2 hashtags, only if they genuinely add value
- No em-dashes. Write naturally.
- Return ONLY the tweet text. No quotes, no preamble.

Title: {title}
Summary: {summary}""",

    "hot_take": """\
Write a bold HOT TAKE tweet about this news.{tone}

Rules:
- Max 260 characters
- Lead with a strong opinion — NOT with "Hot take:"
- 1-2 hashtags max
- Edgy but factually grounded. Not harmful.
- Return ONLY the tweet text. No quotes, no preamble.

Title: {title}
Summary: {summary}""",

    "thread": """\
Write a 3-5 tweet THREAD about this news.{tone}

Rules:
- Each tweet max 260 characters
- Tweet 1 = strong hook
- Middle tweets = key facts and angles
- Last tweet = insight, question, or CTA
- Return ONLY a raw JSON array of strings. Example: ["Hook", "Fact 2", "Conclusion"]
- No markdown. No explanation. Just valid JSON.

Title: {title}
Summary: {summary}""",

    "poll": """\
Write a tweet + poll about this news to drive engagement.{tone}

Rules:
- Tweet: max 200 chars, ends with a question
- Exactly 4 poll options, each max 25 characters
- Options = real balanced choices, not jokes
- Return ONLY raw JSON: {{"tweet": "...", "options": ["A","B","C","D"]}}

Title: {title}
Summary: {summary}""",
}

VIDEO_PROMPT = """\
Write tweet content for this YouTube video.{tone}

Return ONLY raw JSON (no markdown):
{{
  "rewrite": "<punchy tweet about the video, max 260 chars, include the YouTube link placeholder [LINK]>",
  "hot_take": "<bold opinion angle on this video's topic, max 260 chars>"
}}

Channel: {channel}
Video title: {title}
Description: {description}"""

HYPOCRISY_PROMPT = """\
You are a razor-sharp satirist who exposes contradictions and double standards in news.

Read ALL headlines below. Then:
1. Pick 6-10 items with clear hypocrisy, irony, or double standards — within one story \
   or between two stories in contrast.
2. For each, write ONE devastating sarcastic tweet (max 260 chars).
   - Witty, not hateful. Punch up, not down.
   - Makes people say "damn, that's true".
   - May reference two headlines for contrast.
   - 0-1 hashtags. Don't start with "Oh the irony" or "Hypocrisy alert:".

Return ONLY a raw JSON array. Each element:
{{"tweet":"<sarcastic tweet>","based_on":"<original headline(s)>","category":"<usa|world|india|telugu|telugu_film>"}}

No markdown. No explanation. Just valid JSON.

Headlines:
{headlines}"""


def generate_all_formats(title: str, summary: str, category: str) -> dict:
    tone_raw = CATEGORY_TONE.get(category, "")
    tone     = f"\nContext: {tone_raw}" if tone_raw else ""
    results  = {}

    for fmt, tmpl in PROMPTS.items():
        try:
            prompt = tmpl.format(tone=tone, title=title, summary=summary[:500])
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=800,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip().strip("`").strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

            if fmt in ("thread", "poll"):
                parsed = json.loads(raw)
                if fmt == "thread" and not isinstance(parsed, list):
                    raise ValueError("Expected list")
                if fmt == "poll" and (
                    "tweet" not in parsed or len(parsed.get("options", [])) != 4
                ):
                    raise ValueError("Invalid poll")
                results[fmt] = parsed
            else:
                results[fmt] = raw

            logger.info(f"    ✓ {fmt}")
        except Exception as e:
            logger.warning(f"    ✗ {fmt}: {e}")
            results[fmt] = None

    return results


def generate_video_tweet(
    title: str, channel: str, description: str, category: str, video_url: str
) -> dict:
    """Generate Rewrite + Hot Take for a YouTube video."""
    tone_raw = CATEGORY_TONE.get(category, "")
    tone     = f"\nContext: {tone_raw}" if tone_raw else ""

    prompt = VIDEO_PROMPT.format(
        tone=tone,
        channel=channel,
        title=title,
        description=description[:300],
    )
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip().strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
        # Inject actual YouTube URL in place of [LINK] placeholder
        for key in ("rewrite", "hot_take"):
            if key in data and data[key]:
                data[key] = data[key].replace("[LINK]", video_url)
        return data
    except Exception as e:
        logger.warning(f"    ✗ video tweet ({title[:40]}): {e}")
        return {"rewrite": None, "hot_take": None}


def generate_hypocrisy_tweets(all_items: list[dict]) -> list[dict]:
    """Scan all headlines and generate sarcastic hypocrisy tweets."""
    logger.info("[HYPOCRISY] Analysing all headlines…")
    headlines = "\n".join(
        f"[{i['category'].upper()} | {i['source_name']}] {i['original_title']}"
        + (f" — {i['original_summary'][:100]}" if i.get("original_summary") else "")
        for i in all_items
    )
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=SYSTEM,
            messages=[{"role": "user", "content": HYPOCRISY_PROMPT.format(headlines=headlines[:12000])}],
        )
        raw = msg.content[0].text.strip().strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        results = json.loads(raw)
        if not isinstance(results, list):
            raise ValueError("Expected list")
        logger.info(f"[HYPOCRISY] Generated {len(results)} tweets.")
        return results
    except Exception as e:
        logger.error(f"[HYPOCRISY] Failed: {e}")
        return []
