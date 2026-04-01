"""
rewriter.py — Claude AI tweet generator.

Tone philosophy:
  - Centrist and factual — report what happened, not what to think about it
  - No ideological framing (left or right)
  - Hot takes = factual observations that surprise, not partisan opinions
  - Hypocrisy = logical contradictions backed by facts, applied equally to ALL sides
  - Never editorialize beyond what the facts support
"""

import anthropic
import json
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── System prompt — neutral, fact-first ───────────────────────────────────────
SYSTEM = (
    "You are a neutral, factual social media journalist for X (Twitter). "
    "You report news clearly and concisely without ideological bias. "
    "You do not favour any political party, ideology, or movement — left, right, or centre. "
    "You do not editorialize beyond what the facts in the story support. "
    "Your job is to inform, not to persuade. "
    "When writing opinion or hot takes, base them strictly on logic and facts — never on political alignment."
)

# ── Category context — audience only, no political framing ───────────────────
CATEGORY_TONE = {
    "usa": (
        "This is US news. Write for an international audience interested in US affairs. "
        "Do not assume the reader supports any US political party or ideology."
    ),
    "world": (
        "This is international news covering Europe, Australia, or global affairs. "
        "Write factually for a global audience. No geopolitical bias."
    ),
    "india": (
        "This is Indian news. Write factually for a general Indian audience. "
        "Do not favour or criticise any Indian political party, government, or opposition."
    ),
    "telugu": (
        "This is Telugu/AP/Telangana regional news. "
        "Write factually for a Telugu-speaking audience. "
        "Do not favour TDP, YSRCP, BRS, or any other regional party."
    ),
    "telugu_film": (
        "This is Tollywood / Telugu cinema news. "
        "Be enthusiastic and fan-friendly. Stick to facts about films, actors, and releases."
    ),
}

# ── Tweet format prompts ──────────────────────────────────────────────────────
PROMPTS = {
    "rewrite": """\
Rewrite this news as a clear, factual tweet. Report what happened — do not add opinions or framing.
{tone}

Rules:
- Max 260 characters
- Do NOT copy the original headline verbatim — rephrase it
- Stick strictly to the facts in the story
- No political opinions or ideological framing
- Max 1-2 hashtags only if they add genuine value
- No em-dashes. Write naturally.
- Return ONLY the tweet text. No quotes, no preamble.

Title: {title}
Summary: {summary}""",

    "hot_take": """\
Write a thought-provoking tweet about this news based strictly on the facts and logic of the story.
{tone}

Rules:
- Max 260 characters
- The observation must be grounded in facts from THIS story — not in political ideology
- It should make people think "I hadn't considered that angle" — not "I agree with that side"
- Do NOT favour or attack any political party, government, or movement
- Do NOT use language associated with left-wing or right-wing commentary
- 0-1 hashtags
- Do NOT start with "Hot take:"
- Return ONLY the tweet text. No quotes, no preamble.

Title: {title}
Summary: {summary}""",

    "thread": """\
Write a 3-5 tweet THREAD that explains this news story clearly and factually.
{tone}

Rules:
- Each tweet max 260 characters
- Tweet 1 = compelling factual hook — what happened
- Middle tweets = key facts, context, background, numbers
- Last tweet = a neutral question or factual implication for the reader to consider
- Present ALL sides of the story fairly — do not favour any party or ideology
- Return ONLY a raw JSON array of strings. Example: ["Hook", "Fact 2", "Conclusion"]
- No markdown. No explanation. Just valid JSON.

Title: {title}
Summary: {summary}""",

    "poll": """\
Write a neutral, fact-based tweet + poll about this news.
{tone}

Rules:
- Tweet: max 200 chars, ends with a genuinely open question
- The question must be neutral — not leading toward any answer
- Exactly 4 poll options, each max 25 characters
- Options must represent genuinely different viewpoints — balanced, not stacked
- Return ONLY raw JSON: {{"tweet": "...", "options": ["A","B","C","D"]}}

Title: {title}
Summary: {summary}""",
}

# ── Video tweet prompt ────────────────────────────────────────────────────────
VIDEO_PROMPT = """\
Write factual tweet content for this YouTube video.
{tone}

Rules:
- Report what the video is about — do not add political opinions
- Rewrite: max 260 chars, factual, include the YouTube link placeholder [LINK]
- Hot take: a factual observation about the video's topic — not a partisan opinion

Return ONLY raw JSON (no markdown):
{{
  "rewrite": "<factual tweet about the video, max 260 chars, include [LINK]>",
  "hot_take": "<fact-based observation about this video topic, max 260 chars>"
}}

Channel: {channel}
Video title: {title}
Description: {description}"""

# ── Hypocrisy prompt — equal-opportunity, fact-based ─────────────────────────
HYPOCRISY_PROMPT = """\
You are a sharp, logical analyst who identifies genuine contradictions, double standards, \
and hypocrisy in the news — applied EQUALLY to all political parties, governments, \
corporations, celebrities, and movements regardless of ideology.

Read ALL headlines below. Then:
1. Pick 6-10 items that show a clear, provable logical contradiction or double standard.
   - The hypocrisy must be based on VERIFIABLE FACTS from the headlines — not on ideology
   - Apply equally to left AND right, government AND opposition, rich AND poor
   - DO NOT consistently target one political side, party, or ideology
   - A person/institution saying one thing and doing another = valid
   - Two stories that contradict each other = valid
   - Pure opinion or partisan attacks = NOT valid

2. For each, write ONE sharp, logical tweet (max 260 chars):
   - Point out the factual contradiction clearly
   - Tone: dry wit, logical — not angry, not partisan
   - No insults or personal attacks
   - 0-1 hashtags
   - Do NOT start with "Oh the irony", "Hypocrisy alert", "Hot take:"

Return ONLY a raw JSON array. Each element:
{{"tweet":"<tweet>","based_on":"<headline(s) this is based on>","category":"<usa|world|india|telugu|telugu_film>"}}

No markdown. No explanation. Just valid JSON.

Headlines:
{headlines}"""


# ── Generator functions ───────────────────────────────────────────────────────

def generate_all_formats(title: str, summary: str, category: str) -> dict:
    """Generate all 4 tweet formats for a single news item."""
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
        for key in ("rewrite", "hot_take"):
            if key in data and data[key]:
                data[key] = data[key].replace("[LINK]", video_url)
        return data
    except Exception as e:
        logger.warning(f"    ✗ video tweet ({title[:40]}): {e}")
        return {"rewrite": None, "hot_take": None}


def generate_hypocrisy_tweets(all_items: list[dict]) -> list[dict]:
    """Scan all headlines and generate equal-opportunity hypocrisy tweets."""
    logger.info("[HYPOCRISY] Analysing all headlines for contradictions...")
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
            messages=[{"role": "user", "content": HYPOCRISY_PROMPT.format(
                headlines=headlines[:12000]
            )}],
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
