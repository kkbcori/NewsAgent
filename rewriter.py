"""
rewriter.py — Tweet generator using Ollama (local LLM, 100% free).

On GitHub Actions: Ollama runs locally on the runner with qwen2.5:3b
On local PC: Install Ollama from https://ollama.com, then run:
    ollama pull qwen2.5:3b

Model: qwen2.5:3b (~2GB RAM, excellent at JSON structured output)
Fallback: If Ollama is not available, falls back to Groq API (if key set)

Tone: Centrist, factual, neutral — no ideological bias left or right.
All 4 formats generated: Rewrite, Hot Take, Thread, Poll
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
OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"

# Detect which backend to use
USE_OLLAMA = True  # always try Ollama first

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
        "This is US news. Write for an international audience. "
        "Do not assume the reader supports any US political party or ideology."
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

# ── Prompts ───────────────────────────────────────────────────────────────────
PROMPTS = {
    "rewrite": """\
Rewrite this news as a clear, factual tweet.
{tone}

Rules:
- Max 260 characters total
- Do NOT copy the headline verbatim — rephrase it
- Stick to facts only, no opinions or framing
- Max 2 hashtags only if genuinely valuable
- Return ONLY the tweet text. Nothing else.

Title: {title}
Summary: {summary}""",

    "hot_take": """\
Write a thought-provoking tweet about this news based strictly on facts and logic.
{tone}

Rules:
- Max 260 characters total
- Must be grounded in facts from THIS story only — not ideology
- Makes people think "I hadn't considered that" — not "I agree with that side"
- Do NOT favour or attack any political party or movement
- Return ONLY the tweet text. Nothing else.

Title: {title}
Summary: {summary}""",

    "thread": """\
Write a 3-5 tweet thread explaining this news clearly and factually.
{tone}

Rules:
- Each tweet max 260 characters
- Tweet 1: factual hook — what happened
- Middle tweets: key facts, context, numbers
- Last tweet: neutral question or implication for reader
- Present ALL sides fairly
- Return ONLY a valid JSON array of strings, example:
  ["tweet one here", "tweet two here", "tweet three here"]
- No markdown, no explanation, just the JSON array.

Title: {title}
Summary: {summary}""",

    "poll": """\
Write a neutral tweet + poll about this news.
{tone}

Rules:
- Tweet: max 200 chars, ends with an open question
- Question must be neutral — not leading toward any answer
- Exactly 4 poll options, each max 25 characters
- Options represent genuinely different viewpoints
- Return ONLY valid JSON, exactly like this:
  {{"tweet": "your tweet here", "options": ["Option A", "Option B", "Option C", "Option D"]}}
- No markdown, no explanation, just the JSON object.

Title: {title}
Summary: {summary}""",
}

VIDEO_PROMPT = """\
Write factual tweet content for this YouTube video.
{tone}

Rules:
- Rewrite: max 260 chars, factual, include the placeholder text [LINK] for the URL
- Hot take: factual observation about the topic, max 260 chars, no partisan opinion
- Return ONLY valid JSON exactly like this:
  {{"rewrite": "tweet with [LINK]", "hot_take": "observation here"}}
- No markdown, no explanation, just the JSON.

Channel: {channel}
Video title: {title}
Description: {description}"""

HYPOCRISY_PROMPT = """\
You are a logical analyst identifying genuine contradictions and double standards in news.
Apply equally to ALL sides — left, right, government, opposition, any party or ideology.

Headlines below. Pick 5-8 items showing clear, provable logical contradictions:
- Person/institution saying one thing, doing another = valid
- Two stories directly contradicting each other = valid
- Partisan opinion without factual basis = NOT valid

For each write ONE sharp tweet (max 260 chars):
- Dry wit, logical tone — not angry, not partisan
- No hashtags needed
- Do NOT start with "Oh the irony", "Hypocrisy alert:", "Hot take:"

Return ONLY a valid JSON array, each element exactly like:
{{"tweet":"tweet text","based_on":"headline(s)","category":"usa|world|india|telugu|telugu_film"}}

No markdown, no explanation, just the JSON array.

Headlines:
{headlines}"""


# ── Backend calls ─────────────────────────────────────────────────────────────

def _call_ollama(prompt: str, max_tokens: int = 600) -> str:
    """Call local Ollama instance."""
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
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _call_groq(prompt: str, max_tokens: int = 600) -> str:
    """Fallback to Groq API if Ollama not available."""
    from groq import Groq
    time.sleep(2)  # respect 30 req/min limit
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
    """Call Ollama first, fall back to Groq if Ollama unavailable."""
    try:
        return _call_ollama(prompt, max_tokens)
    except Exception as e:
        if GROQ_API_KEY and len(GROQ_API_KEY) > 10:
            logger.warning(f"Ollama failed ({e}), falling back to Groq...")
            return _call_groq(prompt, max_tokens)
        raise RuntimeError(
            f"Ollama unavailable ({e}) and no GROQ_API_KEY set. "
            "Install Ollama locally or set GROQ_API_KEY."
        )


def _parse_json(raw: str):
    """Safely parse JSON from LLM output, stripping any markdown fences."""
    raw = raw.strip()
    # Strip markdown code fences
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    raw = raw.strip()
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()
    return json.loads(raw)


# ── Public functions ──────────────────────────────────────────────────────────

def check_ollama() -> bool:
    """Check if Ollama is running and model is available."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        available = any(OLLAMA_MODEL.split(":")[0] in m for m in models)
        if available:
            logger.info(f"Ollama ready with model: {OLLAMA_MODEL}")
        else:
            logger.warning(f"Ollama running but {OLLAMA_MODEL} not found. Models: {models}")
        return available
    except Exception as e:
        logger.warning(f"Ollama not available: {e}")
        return False


def generate_all_formats(title: str, summary: str, category: str) -> dict:
    """Generate all 4 tweet formats for a single news item."""
    tone_raw = CATEGORY_TONE.get(category, "")
    tone     = f"\nContext: {tone_raw}" if tone_raw else ""
    results  = {fmt: None for fmt in PROMPTS}

    for fmt, tmpl in PROMPTS.items():
        try:
            prompt = tmpl.format(tone=tone, title=title, summary=summary[:500])
            raw    = _call_llm(prompt)

            if fmt in ("thread", "poll"):
                parsed = _parse_json(raw)
                if fmt == "thread":
                    if not isinstance(parsed, list):
                        raise ValueError("Expected JSON array for thread")
                    # Ensure all items are strings
                    parsed = [str(t) for t in parsed]
                if fmt == "poll":
                    if "tweet" not in parsed or len(parsed.get("options", [])) != 4:
                        raise ValueError("Invalid poll: need tweet + 4 options")
                results[fmt] = parsed
            else:
                # Clean up plain text — remove surrounding quotes if model added them
                raw = raw.strip('"').strip("'").strip()
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
    prompt   = VIDEO_PROMPT.format(
        tone=tone, channel=channel,
        title=title, description=description[:300],
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


def generate_hypocrisy_tweets(all_items: list[dict]) -> list[dict]:
    """Scan all headlines and generate equal-opportunity hypocrisy tweets."""
    logger.info("[HYPOCRISY] Analysing all headlines for contradictions...")
    headlines = "\n".join(
        f"[{i['category'].upper()} | {i['source_name']}] {i['original_title']}"
        + (f" — {i['original_summary'][:100]}" if i.get("original_summary") else "")
        for i in all_items
    )
    try:
        prompt  = HYPOCRISY_PROMPT.format(headlines=headlines[:10000])
        raw     = _call_llm(prompt, max_tokens=2000)
        results = _parse_json(raw)
        if not isinstance(results, list):
            raise ValueError("Expected JSON array")
        logger.info(f"[HYPOCRISY] Generated {len(results)} tweets.")
        return results
    except Exception as e:
        logger.error(f"[HYPOCRISY] Failed: {e}")
        return []
