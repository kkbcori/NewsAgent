"""
rewriter.py — Tweet generator using Groq API (FREE).

Groq free tier: 14,400 requests/day, 30 requests/minute
Model: llama-3.3-70b-versatile — comparable to Claude Sonnet quality
Sign up free at: https://console.groq.com

Tone: Centrist, factual, neutral — no ideological bias left or right.
"""

import json
import os
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL  = "llama-3.3-70b-versatile"

# ── System prompt — neutral, fact-first ───────────────────────────────────────
SYSTEM = (
    "You are a neutral, factual social media journalist writing for X (Twitter). "
    "You report news clearly and concisely without ideological bias. "
    "You do not favour any political party, ideology, or movement — left, right, or centre. "
    "You do not editorialize beyond what the facts in the story support. "
    "Your job is to inform, not to persuade. "
    "When writing opinion or hot takes, base them strictly on logic and facts — "
    "never on political alignment."
)

# ── Category context ──────────────────────────────────────────────────────────
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

# ── Prompts ───────────────────────────────────────────────────────────────────
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
- Return ONLY the tweet text. No quotes, no preamble, no explanation.

Title: {title}
Summary: {summary}""",

    "hot_take": """\
Write a thought-provoking tweet about this news based strictly on facts and logic.
{tone}

Rules:
- Max 260 characters
- The observation must be grounded in facts from THIS story — not in political ideology
- Makes people think "I hadn't considered that angle" — not "I agree with that side"
- Do NOT favour or attack any political party, government, or movement
- 0-1 hashtags
- Do NOT start with "Hot take:"
- Return ONLY the tweet text. No quotes, no preamble, no explanation.

Title: {title}
Summary: {summary}""",

    "thread": """\
Write a 3-5 tweet THREAD that explains this news story clearly and factually.
{tone}

Rules:
- Each tweet max 260 characters
- Tweet 1: factual hook — what happened
- Middle tweets: key facts, context, background, numbers
- Last tweet: neutral question or factual implication for the reader
- Present ALL sides of the story fairly
- Return ONLY a JSON array of strings like: ["tweet1", "tweet2", "tweet3"]
- No markdown. No explanation. Just valid JSON array.

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
- Return ONLY valid JSON like: {{"tweet": "...", "options": ["A", "B", "C", "D"]}}
- No markdown. No explanation. Just valid JSON.

Title: {title}
Summary: {summary}""",
}

VIDEO_PROMPT = """\
Write factual tweet content for this YouTube video.
{tone}

Rules:
- Rewrite: max 260 chars, factual, include the YouTube link placeholder [LINK]
- Hot take: a factual observation about the video's topic — not a partisan opinion
- Return ONLY valid JSON: {{"rewrite": "...", "hot_take": "..."}}
- No markdown. No explanation. Just valid JSON.

Channel: {channel}
Video title: {title}
Description: {description}"""

HYPOCRISY_PROMPT = """\
You are a sharp, logical analyst who identifies genuine contradictions, double standards, \
and hypocrisy in the news — applied EQUALLY to all political parties, governments, \
corporations, celebrities, and movements regardless of ideology.

Read ALL headlines below. Then:
1. Pick 6-10 items that show a clear, provable logical contradiction or double standard.
   - Must be based on VERIFIABLE FACTS from the headlines — not on ideology
   - Apply equally to left AND right, government AND opposition, rich AND poor
   - A person/institution saying one thing and doing another = valid
   - Two stories that directly contradict each other = valid
   - Pure partisan opinion = NOT valid

2. For each, write ONE sharp, logical tweet (max 260 chars):
   - Point out the factual contradiction clearly
   - Tone: dry wit, logical — not angry, not partisan
   - 0-1 hashtags
   - Do NOT start with "Oh the irony", "Hypocrisy alert:", "Hot take:"

Return ONLY a JSON array. Each element:
{{"tweet":"...","based_on":"...","category":"usa|world|india|telugu|telugu_film"}}

No markdown. No explanation. Just valid JSON array.

Headlines:
{headlines}"""


# ── Core generation helper ────────────────────────────────────────────────────
def _call_groq(prompt: str, max_tokens: int = 600) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


def _parse_json(raw: str):
    raw = raw.strip().strip("`").strip()
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()
    return json.loads(raw)


# ── Public functions ──────────────────────────────────────────────────────────
def generate_all_formats(title: str, summary: str, category: str) -> dict:
    """Generate all 4 tweet formats for a single news item."""
    tone_raw = CATEGORY_TONE.get(category, "")
    tone     = f"\nContext: {tone_raw}" if tone_raw else ""
    results  = {}

    for fmt, tmpl in PROMPTS.items():
        try:
            prompt = tmpl.format(tone=tone, title=title, summary=summary[:500])
            raw    = _call_groq(prompt)

            if fmt in ("thread", "poll"):
                parsed = _parse_json(raw)
                if fmt == "thread" and not isinstance(parsed, list):
                    raise ValueError("Expected list for thread")
                if fmt == "poll" and (
                    "tweet" not in parsed or len(parsed.get("options", [])) != 4
                ):
                    raise ValueError("Invalid poll structure")
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
        tone=tone, channel=channel,
        title=title, description=description[:300],
    )
    try:
        raw  = _call_groq(prompt, max_tokens=300)
        data = _parse_json(raw)
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
        prompt  = HYPOCRISY_PROMPT.format(headlines=headlines[:12000])
        raw     = _call_groq(prompt, max_tokens=2000)
        results = _parse_json(raw)
        if not isinstance(results, list):
            raise ValueError("Expected list")
        logger.info(f"[HYPOCRISY] Generated {len(results)} tweets.")
        return results
    except Exception as e:
        logger.error(f"[HYPOCRISY] Failed: {e}")
        return []
