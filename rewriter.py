"""
rewriter.py — Tweet generator with full intelligence brain.

Formats generated per news item:
  ✍️  Rewrite      — clean factual tweet
  🔥  Hot Take     — thought-provoking angle
  🧵  Thread       — 3-5 tweet deep dive
  📊  Poll         — engagement poll
  🧠  Deep Read    — what the headline doesn't say (read between lines)
  🌐  Mainstream   — official narrative
  🕵️  Alternative  — counter-narrative / alternative angle
  💰  Cui Bono     — who benefits analysis

For inventions:
  🔬  Invention    — plain language explanation
  🤯  Mind Blown   — wow factor angle

Uses Ollama (local LLM on GitHub Actions) — 100% free, no rate limits.
Falls back to Groq if Ollama unavailable.
"""

import json
import os
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM = (
    "You are a sharp, non-partisan intelligence analyst and journalist for X (Twitter). "
    "You read between lines, connect dots, ask uncomfortable questions, and expose "
    "what mainstream media misses — applying the same critical lens to ALL sides equally. "
    "You present multiple perspectives without claiming any as absolute truth. "
    "Your job is to make readers think, not tell them what to think."
)

# ── Category context ──────────────────────────────────────────────────────────
CATEGORY_TONE = {
    "usa":         "US news. International audience. No partisan bias.",
    "world":       "International news. Global audience. No geopolitical bias.",
    "india":       "Indian news. General audience. No party bias.",
    "telugu":      "Telugu/AP/Telangana news. No TDP/YSRCP/BRS bias.",
    "telugu_film": "Tollywood news. Fan-friendly. Stick to facts.",
    "science":     "Science/tech breakthrough. Plain language for general audience.",
    "tech":        "Technology news. Make it relevant to non-technical readers.",
    "india_tech":  "India tech/science. Relevant to Indian audience.",
    "india_science":"India science/ISRO. Inspiring and factual.",
}

# ── Hashtag rule injected into every prompt ───────────────────────────────────
HASHTAG_RULE = """
Trending hashtags on X: {trending}
Use 1-2 hashtags MAX. Only if DIRECTLY relevant. Put at end of tweet."""

# ══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

PROMPTS = {

    "rewrite": """\
Rewrite this news as a clear, factual tweet. Facts only, no opinions.
Context: {tone}
{hashtag_rule}
Max 270 chars. Do not copy headline verbatim. Return ONLY the tweet text.

Title: {title}
Summary: {summary}""",

    "hot_take": """\
Write a thought-provoking tweet grounded strictly in the facts of this story.
Context: {tone}
{hashtag_rule}
Max 270 chars. Make readers think "I hadn't considered that."
No partisan opinion. Return ONLY the tweet text.

Title: {title}
Summary: {summary}""",

    "thread": """\
Write a 4-tweet thread explaining this story with depth.
Context: {tone}
Trending hashtags (use 1-2 in tweet 1 only): {trending}

- Tweet 1: Hook + 1-2 hashtags
- Tweet 2: Key fact or context most people miss
- Tweet 3: The deeper implication or pattern
- Tweet 4: Question that makes readers think

Each tweet max 270 chars. Return ONLY a valid JSON array:
["tweet1 #Tag", "tweet2", "tweet3", "tweet4"]

Title: {title}
Summary: {summary}""",

    "poll": """\
Write a neutral tweet + poll that sparks genuine debate.
Context: {tone}
{hashtag_rule}
Tweet max 220 chars, ends with open question. 4 balanced options (max 25 chars each).
Return ONLY valid JSON:
{{"tweet": "tweet #Tag", "options": ["A", "B", "C", "D"]}}

Title: {title}
Summary: {summary}""",

    "deep_read": """\
You are reading BETWEEN THE LINES of this news story.

Analyse this story for:
- What is NOT mentioned that should be?
- Whose voice/perspective is missing?
- What does the timing of this story suggest?
- What does this story distract from or enable?
- What unanswered question did the journalist not ask?

Context: {tone}
{hashtag_rule}
Write ONE sharp tweet (max 270 chars) revealing your most important observation.
Frame as a question or observation — NOT as a definitive claim.
Return ONLY the tweet text.

Title: {title}
Summary: {summary}
Source: {source}""",

}

CONSPIRACY_PROMPT = """\
You are a critical thinking analyst presenting MULTIPLE ANGLES on a news story.
You don't claim conspiracies as fact — you ask the questions mainstream media avoids.
Apply equal scepticism to ALL sides.

Story:
Title: {title}
Summary: {summary}
Source: {source}

Alternative source perspectives: {alt_coverage}
Trending hashtags: {trending}

Write 3 short tweets (max 270 chars each) presenting:
1. mainstream — the official narrative in neutral terms
2. alternative — the angle independent sources suggest OR questions the official story leaves open
   Use phrases like "Questions remain..." or "Some analysts argue..." or "What's not mentioned:"
3. cui_bono — who gains from this situation? Follow the money/power.
   Frame as: "Worth asking: who benefits if X happens? [stakeholder] stands to [gain/lose]..."

Add 1 relevant hashtag to each. Return ONLY valid JSON:
{{"mainstream":"tweet #Tag","alternative":"tweet #Tag","cui_bono":"tweet #Tag"}}"""

INVENTION_PROMPT = """\
Translate this scientific paper/invention/launch into exciting plain language for X.
Context: {tone}
Trending hashtags: {trending}

Write 2 tweets:
1. rewrite — plain English: what was discovered, why it matters, what it enables next (max 270 chars)
   Use analogy if helpful. Add 1-2 relevant hashtags.
2. hot_take — the "mind-blown" angle: what this changes, what it makes possible (max 270 chars)

Return ONLY valid JSON:
{{"rewrite":"explanation tweet #Tag","hot_take":"mind-blown tweet #Tag"}}

Title: {title}
Summary: {summary}
Source: {source}"""

BETWEEN_LINES_PROMPT = """\
You are an intelligence analyst reading today's news as a whole — not individual stories.

Look across ALL headlines below for:
1. CONNECTIONS — 2-3 seemingly unrelated stories that tell a bigger story together
2. TIMING — stories published together that seem strategically timed
3. SILENCE — important events conspicuously absent from coverage today
4. CONTRADICTIONS — outlets covering the same story with wildly different framing
5. PATTERNS — a recurring theme across multiple stories that nobody is naming

For each finding, write ONE sharp analytical tweet (max 270 chars):
- State the observation as a question or pattern — not a claim
- "Has anyone noticed that on the same day X happened, Y was also quietly..."
- "Three separate stories today all point to one thing: ..."
- "What's missing from today's coverage: [topic] — despite [reason it matters]"
- Add 1 relevant hashtag

Trending hashtags: {trending}

Return ONLY a valid JSON array (6-10 items):
[{{
  "tweet": "tweet text #Tag",
  "type": "connection|timing|silence|contradiction|pattern",
  "angle": "one sentence explaining the intelligence insight"
}}]

No markdown. Just valid JSON.

Today's headlines:
{headlines}"""

HYPOCRISY_PROMPT = """\
Intelligence analyst identifying provable contradictions across today's news.
Apply equally to ALL parties, governments, corporations, celebrities.

Trending hashtags: {trending}

Headlines:
{headlines}

Pick 5-8 items showing clear factual contradictions. For each:
- One sharp tweet (max 270 chars)
- Dry wit, logical — not angry, not partisan
- 1 relevant hashtag
- Do NOT start with "Oh the irony", "Hypocrisy alert:", "Hot take:"

Return ONLY valid JSON array:
[{{"tweet":"tweet #Tag","based_on":"headline(s)","category":"usa|world|india|telugu|telugu_film"}}]"""


# ══════════════════════════════════════════════════════════════════════════════
# LLM BACKEND
# ══════════════════════════════════════════════════════════════════════════════

def _call_ollama(prompt: str, max_tokens: int = 600) -> str:
    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model":   OLLAMA_MODEL,
            "stream":  False,
            "options": {"num_predict": max_tokens, "temperature": 0.72},
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
        temperature=0.72,
    )
    return resp.choices[0].message.content.strip()


def _call_llm(prompt: str, max_tokens: int = 600) -> str:
    try:
        return _call_ollama(prompt, max_tokens)
    except Exception as e:
        if GROQ_API_KEY and len(GROQ_API_KEY) > 10:
            logger.warning(f"Ollama failed ({e}), using Groq...")
            return _call_groq(prompt, max_tokens)
        raise RuntimeError(f"No LLM available: {e}")


def _parse_json(raw: str):
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    raw = raw.strip()
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()
    return json.loads(raw)


def _fmt_trending(tags: list) -> str:
    if not tags:
        return "None available"
    return ", ".join(tags[:20])


def _safe_call(fmt: str, prompt: str, max_tokens: int = 600):
    """Call LLM and parse result, return None on failure."""
    try:
        raw = _call_llm(prompt, max_tokens)
        if fmt in ("thread", "poll", "conspiracy", "invention",
                   "between_lines", "hypocrisy"):
            return _parse_json(raw)
        return raw.strip('"').strip("'").strip()
    except Exception as e:
        logger.warning(f"    ✗ {fmt}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC GENERATION FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def check_ollama() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        ok = any(OLLAMA_MODEL.split(":")[0] in m for m in models)
        logger.info(f"Ollama {'ready' if ok else 'running but model missing'}: {OLLAMA_MODEL}")
        return ok
    except Exception as e:
        logger.warning(f"Ollama not available: {e}")
        return False


def generate_all_formats(
    title: str,
    summary: str,
    category: str,
    source: str = "",
    trending_tags: list = None,
    alt_coverage: list = None,
) -> dict:
    """
    Generate all tweet formats for a single news item.

    Returns dict with keys:
      rewrite, hot_take, thread, poll, deep_read,
      mainstream, alternative, cui_bono
    """
    tone         = CATEGORY_TONE.get(category, "Factual, neutral.")
    trending     = _fmt_trending(trending_tags or [])
    hashtag_rule = HASHTAG_RULE.format(trending=trending)
    alt_text     = "\n".join(
        f"- {a['source']} ({a['lean']}): {a['title']}"
        for a in (alt_coverage or [])
    ) or "No alternative coverage found."

    results = {}

    # ── Standard formats ──────────────────────────────────────────
    for fmt in ("rewrite", "hot_take", "deep_read"):
        prompt = PROMPTS[fmt].format(
            tone=tone,
            hashtag_rule=hashtag_rule,
            trending=trending,
            title=title,
            summary=summary[:500],
            source=source,
        )
        results[fmt] = _safe_call(fmt, prompt)
        if results[fmt]:
            logger.info(f"    ✓ {fmt}")

    # ── Thread ────────────────────────────────────────────────────
    prompt = PROMPTS["thread"].format(
        tone=tone, trending=trending,
        title=title, summary=summary[:500],
    )
    raw = _safe_call("thread", prompt)
    if isinstance(raw, list):
        results["thread"] = [str(t) for t in raw]
        logger.info(f"    ✓ thread ({len(results['thread'])} tweets)")
    else:
        results["thread"] = None

    # ── Poll ──────────────────────────────────────────────────────
    prompt = PROMPTS["poll"].format(
        tone=tone, hashtag_rule=hashtag_rule, trending=trending,
        title=title, summary=summary[:500],
    )
    raw = _safe_call("poll", prompt)
    if isinstance(raw, dict) and "tweet" in raw and len(raw.get("options", [])) == 4:
        results["poll"] = raw
        logger.info(f"    ✓ poll")
    else:
        results["poll"] = None

    # ── Conspiracy / alternative angles ───────────────────────────
    prompt = CONSPIRACY_PROMPT.format(
        title=title, summary=summary[:500], source=source,
        alt_coverage=alt_text, trending=trending,
    )
    raw = _safe_call("conspiracy", prompt)
    if isinstance(raw, dict):
        results["mainstream"]   = raw.get("mainstream")
        results["alternative"]  = raw.get("alternative")
        results["cui_bono"]     = raw.get("cui_bono")
        logger.info(f"    ✓ conspiracy angles")
    else:
        results["mainstream"]  = None
        results["alternative"] = None
        results["cui_bono"]    = None

    return results


def generate_invention_tweet(
    title: str,
    summary: str,
    source: str,
    category: str,
    trending_tags: list = None,
) -> dict:
    """Generate plain-language + mind-blown tweets for an invention/paper."""
    tone     = CATEGORY_TONE.get(category, "Science. Plain language.")
    trending = _fmt_trending(trending_tags or [])

    prompt = INVENTION_PROMPT.format(
        tone=tone, trending=trending,
        title=title, summary=summary[:500], source=source,
    )
    raw = _safe_call("invention", prompt, max_tokens=400)
    if isinstance(raw, dict):
        logger.info(f"    ✓ invention tweet: {title[:40]}...")
        return raw
    return {"rewrite": None, "hot_take": None}


def generate_video_tweet(
    title: str,
    channel: str,
    description: str,
    category: str,
    video_url: str,
    trending_tags: list = None,
) -> dict:
    """Generate tweet content for a YouTube video."""
    tone         = CATEGORY_TONE.get(category, "")
    trending     = _fmt_trending(trending_tags or [])
    hashtag_rule = HASHTAG_RULE.format(trending=trending)

    prompt = f"""\
Write factual tweet content for this YouTube video.
Context: {tone}
{hashtag_rule}
- rewrite: max 270 chars, factual, include placeholder [LINK], add 1-2 hashtags
- hot_take: factual observation, max 270 chars, 1-2 hashtags
Return ONLY valid JSON: {{"rewrite":"tweet [LINK] #Tag","hot_take":"observation #Tag"}}

Channel: {channel}
Title: {title}
Description: {description[:300]}"""

    raw = _safe_call("invention", prompt, max_tokens=300)
    if isinstance(raw, dict):
        for key in ("rewrite", "hot_take"):
            if raw.get(key):
                raw[key] = str(raw[key]).replace("[LINK]", video_url)
        return raw
    return {"rewrite": None, "hot_take": None}


def generate_between_lines(
    all_items: list,
    trending_tags: list = None,
) -> list:
    """
    Analyse ALL headlines together for hidden connections, timing,
    silences, contradictions, and patterns.
    Returns list of {tweet, type, angle} dicts.
    """
    logger.info("[BRAIN] Reading between the lines of all headlines...")
    headlines = "\n".join(
        f"[{i['category'].upper()} | {i['source_name']}] {i['original_title']}"
        + (f" — {i['original_summary'][:80]}" if i.get("original_summary") else "")
        for i in all_items
    )
    trending = _fmt_trending(trending_tags or [])
    prompt   = BETWEEN_LINES_PROMPT.format(
        headlines=headlines[:12000],
        trending=trending,
    )
    raw = _safe_call("between_lines", prompt, max_tokens=2500)
    if isinstance(raw, list):
        logger.info(f"[BRAIN] Found {len(raw)} intelligence observations.")
        return raw
    logger.warning("[BRAIN] Between-the-lines pass failed.")
    return []


def generate_hypocrisy_tweets(
    all_items: list,
    trending_tags: list = None,
) -> list:
    """Find factual contradictions across all headlines."""
    logger.info("[HYPOCRISY] Scanning for contradictions...")
    headlines = "\n".join(
        f"[{i['category'].upper()} | {i['source_name']}] {i['original_title']}"
        + (f" — {i['original_summary'][:80]}" if i.get("original_summary") else "")
        for i in all_items
    )
    trending = _fmt_trending(trending_tags or [])
    prompt   = HYPOCRISY_PROMPT.format(
        headlines=headlines[:10000],
        trending=trending,
    )
    raw = _safe_call("hypocrisy", prompt, max_tokens=2000)
    if isinstance(raw, list):
        logger.info(f"[HYPOCRISY] Generated {len(raw)} tweets.")
        return raw
    return []
