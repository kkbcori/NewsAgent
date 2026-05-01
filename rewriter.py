"""
rewriter.py — Tweet generator using Ollama (local LLM, 100% free).

On GitHub Actions: Ollama runs locally on the runner with qwen2.5:3b
On local PC: Install Ollama from https://ollama.com, then run:
    ollama pull qwen2.5:3b

Fallback: If Ollama unavailable, uses Groq API (set GROQ_API_KEY in env/secrets)

Features:
  - All 4 formats: Rewrite, Hot Take, Thread, Poll
  - Trending hashtags from X/Twitter injected into every tweet
  - LLM picks 1-2 relevant trending tags per tweet (never forces irrelevant ones)
  - Centrist, factual, neutral tone — no ideological bias
"""

import json
import os
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── LLM backend config ────────────────────────────────────────────────────────
OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"

# ── System prompt ─────────────────────────────────────────────────────────────
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
        "This is US news. Write for an international audience. "
        "Do not assume the reader supports any US political party."
    ),
    "world": (
        "This is international news. Write factually for a global audience. "
        "No geopolitical bias."
    ),
    "india": (
        "This is Indian news. Write factually for a general Indian audience. "
        "Do not favour or criticise any Indian political party."
    ),
    "telugu": (
        "This is Telugu/AP/Telangana regional news. Write factually. "
        "Do not favour TDP, YSRCP, BRS, or any other regional party."
    ),
    "telugu_film": (
        "This is Tollywood / Telugu cinema news. "
        "Be enthusiastic and fan-friendly. Stick to facts."
    ),
}

# ── Hashtag instruction (added to every prompt) ───────────────────────────────
HASHTAG_RULE = """\

Trending hashtags on X right now: {trending}

Hashtag rules:
- Use 1-2 hashtags MAXIMUM in your tweet
- ONLY use a hashtag if it is DIRECTLY relevant to this specific news story
- You may use a trending hashtag from the list above OR create your own relevant one
- If NO trending hashtag fits this story, create 1 short relevant hashtag
- NEVER stuff irrelevant trending hashtags just for visibility
- Hashtags go at the END of the tweet"""

# ── Prompts ───────────────────────────────────────────────────────────────────
PROMPTS = {
    "rewrite": """\
Rewrite this news as a clear, factual tweet.
{tone}
{hashtag_rule}

Rules:
- Max 270 characters total (including hashtags)
- Do NOT copy the headline verbatim — rephrase it
- Stick to facts only, no opinions or framing
- Return ONLY the tweet text. Nothing else.

Title: {title}
Summary: {summary}""",

    "hot_take": """\
Write a thought-provoking tweet about this news based strictly on facts and logic.
{tone}
{hashtag_rule}

Rules:
- Max 270 characters total (including hashtags)
- Must be grounded in facts from THIS story — not ideology
- Makes people think "I hadn't considered that angle"
- Do NOT favour or attack any political party or movement
- Return ONLY the tweet text. Nothing else.

Title: {title}
Summary: {summary}""",

    "thread": """\
Write a 3-5 tweet thread explaining this news clearly and factually.
{tone}

Hashtag rules for thread:
- Add 1-2 relevant hashtags to the FIRST tweet only
- Trending hashtags available: {trending}
- Use only if directly relevant

Rules:
- Each tweet max 270 characters
- Tweet 1: factual hook with hashtags
- Middle tweets: key facts, context, numbers (no hashtags)
- Last tweet: neutral question or implication for reader
- Return ONLY a valid JSON array of strings:
  ["tweet one #HashTag", "tweet two", "tweet three"]
- No markdown, no explanation, just the JSON array.

Title: {title}
Summary: {summary}""",

    "poll": """\
Write a neutral tweet + poll about this news.
{tone}
{hashtag_rule}

Rules:
- Tweet: max 220 chars including hashtags, ends with an open question
- Question must be neutral — not leading toward any answer
- Exactly 4 poll options, each max 25 characters
- Options represent genuinely different viewpoints
- Return ONLY valid JSON:
  {{"tweet": "your tweet #Tag", "options": ["Option A", "Option B", "Option C", "Option D"]}}
- No markdown, no explanation, just the JSON.

Title: {title}
Summary: {summary}""",
}

VIDEO_PROMPT = """\
Write factual tweet content for this YouTube video.
{tone}
{hashtag_rule}

Rules:
- Rewrite: max 270 chars, factual, include placeholder [LINK] for URL, add 1-2 relevant hashtags
- Hot take: factual observation, max 270 chars, add 1-2 relevant hashtags
- Return ONLY valid JSON:
  {{"rewrite": "tweet with [LINK] #Tag", "hot_take": "observation #Tag"}}
- No markdown, no explanation, just the JSON.

Channel: {channel}
Video title: {title}
Description: {description}"""

HYPOCRISY_PROMPT = """\
You are a logical analyst identifying genuine contradictions and double standards in news.
Apply equally to ALL sides — left, right, government, opposition, any party or ideology.

Trending hashtags on X: {trending}

Headlines below. Pick 5-8 items showing clear, provable logical contradictions.
For each write ONE sharp tweet (max 270 chars):
- Point out the factual contradiction
- Dry wit, logical tone — not angry, not partisan
- Add 1 relevant hashtag if it fits (trending or your own)
- Do NOT start with "Oh the irony", "Hypocrisy alert:", "Hot take:"

Return ONLY a valid JSON array:
[{{"tweet":"tweet text #Tag","based_on":"headline(s)","category":"usa|world|india|telugu|telugu_film"}}]

No markdown, no explanation, just the JSON array.

Headlines:
{headlines}"""


# ── Backend calls ─────────────────────────────────────────────────────────────

def _call_ollama(prompt: str, max_tokens: int = 600) -> str:
    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model":   OLLAMA_MODEL,
            "stream":  False,
            "options": {"num_predict": max_tokens, "temperature": 0.7},
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user",   "content": prompt},
            ],
        },
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _call_groq(prompt: str, max_tokens: int = 600) -> str:
    from groq import Groq
    time.sleep(2)
    client = Groq(api_key=GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


def _call_llm(prompt: str, max_tokens: int = 600) -> str:
    """Try Ollama first, fall back to Groq."""
    try:
        return _call_ollama(prompt, max_tokens)
    except Exception as e:
        if GROQ_API_KEY and len(GROQ_API_KEY) > 10:
            logger.warning(f"Ollama failed ({e}), falling back to Groq...")
            return _call_groq(prompt, max_tokens)
        raise RuntimeError(
            f"Ollama unavailable ({e}) and no GROQ_API_KEY set."
        )


def _parse_json(raw: str):
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    raw = raw.strip()
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()
    return json.loads(raw)


def _fmt_trending(tags: list[str]) -> str:
    """Format trending tags for injection into prompts."""
    if not tags:
        return "None available right now"
    return ", ".join(tags[:20])  # top 20 to keep prompt size reasonable


# ── Public functions ──────────────────────────────────────────────────────────

def check_ollama() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        available = any(OLLAMA_MODEL.split(":")[0] in m for m in models)
        if available:
            logger.info(f"Ollama ready: {OLLAMA_MODEL}")
        else:
            logger.warning(f"Ollama running but {OLLAMA_MODEL} not found. Models: {models}")
        return available
    except Exception as e:
        logger.warning(f"Ollama not available: {e}")
        return False


def generate_all_formats(
    title: str,
    summary: str,
    category: str,
    trending_tags: list[str] = None,
) -> dict:
    """
    Generate all 4 tweet formats for a single news item.
    trending_tags: list of trending hashtags from X for this category.
    """
    tone_raw    = CATEGORY_TONE.get(category, "")
    tone        = f"\nContext: {tone_raw}" if tone_raw else ""
    trending    = _fmt_trending(trending_tags or [])
    hashtag_rule = HASHTAG_RULE.format(trending=trending)
    results     = {fmt: None for fmt in PROMPTS}

    for fmt, tmpl in PROMPTS.items():
        try:
            prompt = tmpl.format(
                tone=tone,
                hashtag_rule=hashtag_rule,
                trending=trending,
                title=title,
                summary=summary[:500],
            )
            raw = _call_llm(prompt)

            if fmt in ("thread", "poll"):
                parsed = _parse_json(raw)
                if fmt == "thread":
                    if not isinstance(parsed, list):
                        raise ValueError("Expected JSON array for thread")
                    parsed = [str(t) for t in parsed]
                if fmt == "poll":
                    if "tweet" not in parsed or len(parsed.get("options", [])) != 4:
                        raise ValueError("Need tweet + 4 options")
                results[fmt] = parsed
            else:
                raw = raw.strip('"').strip("'").strip()
                results[fmt] = raw

            logger.info(f"    ✓ {fmt}")
        except Exception as e:
            logger.warning(f"    ✗ {fmt}: {e}")
            results[fmt] = None

    return results


def generate_video_tweet(
    title: str,
    channel: str,
    description: str,
    category: str,
    video_url: str,
    trending_tags: list[str] = None,
) -> dict:
    """Generate Rewrite + Hot Take for a YouTube video."""
    tone_raw     = CATEGORY_TONE.get(category, "")
    tone         = f"\nContext: {tone_raw}" if tone_raw else ""
    trending     = _fmt_trending(trending_tags or [])
    hashtag_rule = HASHTAG_RULE.format(trending=trending)

    prompt = VIDEO_PROMPT.format(
        tone=tone,
        hashtag_rule=hashtag_rule,
        channel=channel,
        title=title,
        description=description[:300],
    )
    try:
        raw  = _call_llm(prompt, max_tokens=300)
        data = _parse_json(raw)
        for key in ("rewrite", "hot_take"):
            if key in data and data[key]:
                data[key] = str(data[key]).replace("[LINK]", video_url)
        return data
    except Exception as e:
        logger.warning(f"    ✗ video tweet ({title[:40]}): {e}")
        return {"rewrite": None, "hot_take": None}


def generate_hypocrisy_tweets(
    all_items: list[dict],
    trending_tags: list[str] = None,
) -> list[dict]:
    """Scan all headlines and generate equal-opportunity hypocrisy tweets."""
    logger.info("[HYPOCRISY] Analysing all headlines for contradictions...")
    headlines = "\n".join(
        f"[{i['category'].upper()} | {i['source_name']}] {i['original_title']}"
        + (f" — {i['original_summary'][:100]}" if i.get("original_summary") else "")
        for i in all_items
    )
    trending = _fmt_trending(trending_tags or [])
    try:
        prompt  = HYPOCRISY_PROMPT.format(
            headlines=headlines[:10000],
            trending=trending,
        )
        raw     = _call_llm(prompt, max_tokens=2000)
        results = _parse_json(raw)
        if not isinstance(results, list):
            raise ValueError("Expected list")
        logger.info(f"[HYPOCRISY] Generated {len(results)} tweets.")
        return results
    except Exception as e:
        logger.error(f"[HYPOCRISY] Failed: {e}")
        return []
