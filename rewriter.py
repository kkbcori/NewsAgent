"""
rewriter.py — Batch tweet generator (FAST version).

Speed trick: Instead of 1 LLM call per item per format (400 calls for 50 items),
we send ALL items in ONE call per format (~8 calls total).

Before: 400 calls × 5 sec = 33 minutes
After:  8 batch calls × 15 sec = ~2-3 minutes

Uses Ollama (local, free) with Groq fallback.
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

# Gemma 2 9B has 15,000 TPM (2.5x more than other Groq models at 6,000 TPM)
# llama-3.1-8b-instant has 14,400 RPD (most generous daily quota)
# We use gemma2 for batch (high token volume) and llama for single calls
GROQ_MODEL_BATCH  = "gemma2-9b-it"          # 15,000 TPM — best for large batch calls
GROQ_MODEL_SINGLE = "llama-3.1-8b-instant"  # 14,400 RPD — best for single calls

# Groq rate limit tracking (read from response headers)
_groq_tokens_remaining = 15000
_groq_reset_time       = 0.0

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM = (
    "You are a sharp, non-partisan intelligence analyst and journalist for X (Twitter). "
    "You read between lines, connect dots, ask uncomfortable questions, and expose "
    "what mainstream media misses — applying the same critical lens to ALL sides equally. "
    "You present multiple perspectives without claiming any as absolute truth. "
    "Your job is to make readers think, not tell them what to think."
)

CATEGORY_TONE = {
    "usa":         "US news. International audience. No partisan bias.",
    "world":       "International news. Global audience. No geopolitical bias.",
    "india":       "Indian news. General audience. No party bias.",
    "telugu":      "Telugu/AP/Telangana news. No TDP/YSRCP/BRS bias.",
    "telugu_film": "Tollywood news. Fan-friendly. Stick to facts.",
    "science":     "Science breakthrough. Plain language for general audience.",
    "tech":        "Technology. Make it relevant to non-technical readers.",
    "india_tech":  "India tech/science. Relevant to Indian audience.",
    "india_science":"India science. Inspiring and factual.",
}

# ══════════════════════════════════════════════════════════════════════════════
# BATCH PROMPTS — process ALL items at once
# ══════════════════════════════════════════════════════════════════════════════

BATCH_REWRITE = """\
Generate one factual tweet per news item below.

Rules for EACH tweet:
- Max 270 characters
- Facts only — no opinions, no framing
- Do NOT copy headline verbatim — rephrase it
- Add 1-2 relevant hashtags from this trending list ONLY if directly relevant: {trending}
- Put hashtags at end

Return ONLY a valid JSON array with exactly {count} strings, one per item, in order:
["tweet for item 1", "tweet for item 2", ...]

Items:
{items}"""

BATCH_HOT_TAKE = """\
Generate one thought-provoking tweet per news item below.
Each tweet reveals an angle based strictly on facts — NOT on political ideology.

Rules for EACH tweet:
- Max 270 characters
- Makes readers think "I hadn't considered that angle"
- No partisan framing. No political sides.
- Add 1-2 relevant hashtags from: {trending}

Return ONLY a valid JSON array with exactly {count} strings, in order:
["hot take for item 1", "hot take for item 2", ...]

Items:
{items}"""

BATCH_DEEP_READ = """\
For each news item below, read BETWEEN THE LINES and write one tweet revealing:
- What the headline doesn't say
- Whose voice is missing
- What unanswered question the journalist didn't ask
- What context completely changes how you read this story

Rules for EACH tweet:
- Max 270 characters
- Frame as observation or question — NOT definitive claim
- Add 1 relevant hashtag from: {trending}

Return ONLY a valid JSON array with exactly {count} strings, in order:
["deep read for item 1", "deep read for item 2", ...]

Items:
{items}"""

BATCH_THREAD = """\
For each news item below, write a 3-tweet thread.

Rules:
- Each tweet max 260 characters
- Tweet 1: factual hook (add 1-2 hashtags from {trending})
- Tweet 2: key fact or context most people miss
- Tweet 3: neutral question or implication

Return ONLY a valid JSON array with exactly {count} sub-arrays, in order:
[["t1 #Tag","t2","t3"], ["t1 #Tag","t2","t3"], ...]

Items:
{items}"""

BATCH_POLL = """\
For each news item below, write a tweet + poll.

Rules:
- Tweet: max 200 chars, ends with open question, 1-2 hashtags from {trending}
- Exactly 4 balanced poll options, each max 25 characters

Return ONLY a valid JSON array with exactly {count} objects, in order:
[{{"tweet":"tweet #Tag","options":["A","B","C","D"]}}, ...]

Items:
{items}"""

BATCH_CONSPIRACY = """\
For each news item below, write THREE angles:
1. mainstream: official narrative stated neutrally
2. alternative: counter-narrative or unanswered questions ("Some analysts argue..." / "Questions remain about...")
3. cui_bono: who benefits? ("Worth asking: who gains if X? [stakeholder] stands to...")

Rules:
- Each angle max 260 characters
- Add 1 relevant hashtag from {trending} per angle
- Apply equal scepticism to ALL political sides

Return ONLY a valid JSON array with exactly {count} objects, in order:
[{{"mainstream":"tweet","alternative":"tweet","cui_bono":"tweet"}}, ...]

Items:
{items}"""

HYPOCRISY_PROMPT = """\
Intelligence analyst identifying provable contradictions across today's news.
Apply equally to ALL parties, governments, corporations, celebrities.

Trending hashtags: {trending}

Headlines:
{headlines}

Pick 5-8 items showing clear factual contradictions. For each:
- One sharp tweet (max 270 chars), dry wit, 1 hashtag
- Do NOT start with "Oh the irony", "Hypocrisy alert:", "Hot take:"

Return ONLY valid JSON array:
[{{"tweet":"tweet #Tag","based_on":"headline(s)","category":"usa|world|india|telugu|telugu_film"}}]"""

BETWEEN_LINES_PROMPT = """\
Intelligence analyst reading today's news as a whole.

Find across ALL headlines:
- CONNECTIONS: unrelated stories that together reveal a bigger picture
- TIMING: stories published together that seem strategically timed
- SILENCE: important events conspicuously absent from coverage
- CONTRADICTIONS: same story covered with wildly different framing
- PATTERNS: recurring theme nobody is naming

Write 6-10 sharp analytical tweets (max 270 chars each).
Frame as questions or observations — not claims.
Add 1 hashtag each from: {trending}

Return ONLY valid JSON array:
[{{"tweet":"tweet #Tag","type":"connection|timing|silence|contradiction|pattern","angle":"one sentence insight"}}]

Today's headlines:
{headlines}"""

INVENTION_PROMPT = """\
Translate each research paper/invention/launch into TWO tweets for X:
1. rewrite: plain English explanation (max 270 chars) — what was found, why it matters, what it enables. Add 1-2 hashtags from {trending}.
2. hot_take: mind-blown angle (max 270 chars) — what this changes, makes possible. Add 1-2 hashtags.

Return ONLY valid JSON array with exactly {count} objects:
[{{"rewrite":"tweet #Tag","hot_take":"tweet #Tag"}}, ...]

Items:
{items}"""


# ══════════════════════════════════════════════════════════════════════════════
# LLM BACKEND
# ══════════════════════════════════════════════════════════════════════════════

def _call_ollama(prompt: str, max_tokens: int = 4000) -> str:
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
        timeout=300,  # 5 min timeout for batch calls
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _call_groq(prompt: str, max_tokens: int = 4000, batch: bool = False) -> str:
    """
    Call Groq API with smart rate limit handling.
    Reads x-ratelimit-remaining-tokens header and sleeps if near limit.
    Uses gemma2-9b-it for batch calls (15,000 TPM) and llama-3.1-8b-instant for singles.
    """
    global _groq_tokens_remaining, _groq_reset_time

    # Estimate tokens in this prompt (rough: 1 token ≈ 4 chars)
    estimated_tokens = len(prompt) // 4 + max_tokens

    # If we'd exceed remaining tokens, sleep until reset
    if _groq_tokens_remaining < estimated_tokens:
        wait = max(0, _groq_reset_time - time.time())
        if wait > 0:
            logger.info(f"Groq TPM limit approaching — waiting {wait:.1f}s for reset...")
            time.sleep(wait + 1)
        _groq_tokens_remaining = 15000  # reset estimate

    model = GROQ_MODEL_BATCH if batch else GROQ_MODEL_SINGLE

    import http.client as _http
    import urllib.request as _req
    import urllib.error

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    body = json.dumps({
        "model":       model,
        "max_tokens":  max_tokens,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": prompt},
        ],
    }).encode()

    req = _req.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=body, headers=headers, method="POST",
    )
    try:
        with _req.urlopen(req, timeout=120) as resp:
            # Read rate limit headers
            remaining = resp.getheader("x-ratelimit-remaining-tokens", "")
            reset_sec  = resp.getheader("x-ratelimit-reset-tokens",    "")
            if remaining:
                _groq_tokens_remaining = int(remaining)
            if reset_sec:
                _groq_reset_time = time.time() + float(reset_sec.replace("s",""))
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        if e.code == 429:
            # Rate limited — sleep and retry once
            retry_after = float(e.headers.get("retry-after", "60"))
            logger.warning(f"Groq 429 — sleeping {retry_after:.0f}s then retrying...")
            time.sleep(retry_after + 2)
            with _req.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"].strip()
        raise


def _call_llm(prompt: str, max_tokens: int = 4000, batch: bool = False) -> str:
    """Try Ollama first (no rate limits). Fall back to Groq with smart rate handling."""
    try:
        return _call_ollama(prompt, max_tokens)
    except Exception as e:
        if GROQ_API_KEY and len(GROQ_API_KEY) > 10:
            logger.warning(f"Ollama failed ({e}), using Groq ({GROQ_MODEL_BATCH if batch else GROQ_MODEL_SINGLE})...")
            return _call_groq(prompt, max_tokens, batch=batch)
        raise RuntimeError(f"No LLM available: {e}")


def _strip_fences(raw: str) -> str:
    """Strip markdown code fences from LLM output."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first line (```json or ```) and last line (```)
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        raw = "\n".join(inner)
    raw = raw.strip()
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()
    return raw


def _extract_json(raw: str):
    """
    Try to extract valid JSON from LLM output even if it's malformed.
    Strategy:
      1. Normal parse
      2. Find first [ or { and last ] or } and parse that substring
      3. Remove trailing commas (common LLM mistake)
    """
    import re as _re

    raw = _strip_fences(raw)

    # Try 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try 2: extract outermost array or object
    for start_char, end_char in [('[', ']'), ('{', '}')]:
        start = raw.find(start_char)
        end   = raw.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            candidate = raw[start:end+1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

    # Try 3: remove trailing commas before ] or }
    cleaned = _re.sub(r',\s*([\]\}])', r'\1', raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try 4: remove trailing commas AND fix unescaped quotes inside strings
    # Replace \" that aren't already escaped
    try:
        # Find array/object and try aggressive cleanup
        start = cleaned.find('[') if '[' in cleaned else cleaned.find('{')
        end   = cleaned.rfind(']') if ']' in cleaned else cleaned.rfind('}')
        if start != -1 and end != -1:
            chunk = cleaned[start:end+1]
            chunk = _re.sub(r',\s*([\]\}])', r'\1', chunk)
            return json.loads(chunk)
    except Exception:
        pass

    raise json.JSONDecodeError("Could not extract valid JSON", raw, 0)


def _parse_json(raw: str):
    return _extract_json(raw)


def _fmt_trending(tags: list) -> str:
    if not tags:
        return "None available"
    return ", ".join((tags or [])[:20])


def _fmt_items(items: list[dict]) -> str:
    """Format items list for batch prompts."""
    lines = []
    for i, item in enumerate(items, 1):
        tone = CATEGORY_TONE.get(item.get("category", ""), "")
        lines.append(
            f"{i}. [{item.get('category','').upper()}] {item.get('original_title','')}"
            f"\n   Summary: {item.get('original_summary','')[:200]}"
            f"\n   Source: {item.get('source_name','')}"
            + (f"\n   Context: {tone}" if tone else "")
        )
    return "\n\n".join(lines)


def _safe_list(result, expected_count: int, fallback=None) -> list:
    """Ensure result is a list of expected length, padding with fallback if needed."""
    if not isinstance(result, list):
        return [fallback] * expected_count
    while len(result) < expected_count:
        result.append(fallback)
    return result[:expected_count]


# ══════════════════════════════════════════════════════════════════════════════
# BATCH GENERATION — one call per format for ALL items
# ══════════════════════════════════════════════════════════════════════════════

# Batch size limit — split into chunks to avoid context length issues
BATCH_SIZE = 20


RETRY_PREFIX = "Your previous response had invalid JSON. Return ONLY a valid JSON array, no prose, no markdown. Fix any unescaped quotes inside strings.\n\n"


def _batch_generate(prompt_template: str, items: list[dict],
                    trending: str, fallback=None) -> list:
    """Run a batch prompt and return per-item results. Retries once on JSON failure."""
    results = []
    for start in range(0, len(items), BATCH_SIZE):
        chunk = items[start:start + BATCH_SIZE]
        prompt = prompt_template.format(
            count    = len(chunk),
            trending = trending,
            items    = _fmt_items(chunk),
        )
        chunk_results = None

        # First attempt
        try:
            raw = _call_llm(prompt, max_tokens=min(4000, len(chunk) * 200), batch=True)
            parsed = _parse_json(raw)
            chunk_results = _safe_list(parsed, len(chunk), fallback)
            logger.info(f"    Batch chunk {start//BATCH_SIZE + 1}: {len(chunk_results)} items OK")
        except Exception as e:
            logger.warning(f"    Batch chunk {start//BATCH_SIZE + 1} failed: {e} — retrying...")
            # Retry with explicit JSON repair instruction
            try:
                retry_prompt = RETRY_PREFIX + prompt
                raw = _call_llm(retry_prompt, max_tokens=min(4000, len(chunk) * 200), batch=True)
                parsed = _parse_json(raw)
                chunk_results = _safe_list(parsed, len(chunk), fallback)
                logger.info(f"    Retry succeeded: {len(chunk_results)} items")
            except Exception as e2:
                logger.warning(f"    Retry also failed: {e2} — using fallback")
                chunk_results = [fallback] * len(chunk)

        results.extend(chunk_results)
    return results


def generate_all_formats_batch(
    items: list[dict],
    trending_tags: list = None,
) -> list[dict]:
    """
    Generate ALL tweet formats for ALL items in batch mode.
    Returns list of content dicts, one per item.

    8 batch calls total instead of 8 × N individual calls.
    """
    trending = _fmt_trending(trending_tags or [])
    n = len(items)
    logger.info(f"\n[BATCH] Generating tweets for {n} items in batch mode...")

    # Initialise results
    results = [{
        "rewrite": None, "hot_take": None, "thread": None, "poll": None,
        "deep_read": None, "mainstream": None, "alternative": None, "cui_bono": None,
    } for _ in range(n)]

    # ── Rewrite ───────────────────────────────────────────────────
    logger.info("[BATCH] ✍️  Rewrite pass...")
    rewrites = _batch_generate(BATCH_REWRITE, items, trending, None)
    for i, r in enumerate(rewrites):
        if isinstance(r, str) and r.strip():
            results[i]["rewrite"] = r.strip().strip('"').strip("'")

    # ── Hot Take ──────────────────────────────────────────────────
    logger.info("[BATCH] 🔥 Hot Take pass...")
    hot_takes = _batch_generate(BATCH_HOT_TAKE, items, trending, None)
    for i, r in enumerate(hot_takes):
        if isinstance(r, str) and r.strip():
            results[i]["hot_take"] = r.strip().strip('"').strip("'")

    # ── Deep Read ─────────────────────────────────────────────────
    logger.info("[BATCH] 🧠 Deep Read pass...")
    deep_reads = _batch_generate(BATCH_DEEP_READ, items, trending, None)
    for i, r in enumerate(deep_reads):
        if isinstance(r, str) and r.strip():
            results[i]["deep_read"] = r.strip().strip('"').strip("'")

    # ── Thread ────────────────────────────────────────────────────
    logger.info("[BATCH] 🧵 Thread pass...")
    threads = _batch_generate(BATCH_THREAD, items, trending, None)
    for i, r in enumerate(threads):
        if isinstance(r, list) and r:
            results[i]["thread"] = [str(t) for t in r]

    # ── Poll ──────────────────────────────────────────────────────
    logger.info("[BATCH] 📊 Poll pass...")
    polls = _batch_generate(BATCH_POLL, items, trending, None)
    for i, r in enumerate(polls):
        if isinstance(r, dict) and "tweet" in r and len(r.get("options", [])) == 4:
            results[i]["poll"] = r

    # ── Conspiracy angles ─────────────────────────────────────────
    logger.info("[BATCH] 🕵️  Conspiracy angles pass...")
    conspiracies = _batch_generate(BATCH_CONSPIRACY, items, trending, None)
    for i, r in enumerate(conspiracies):
        if isinstance(r, dict):
            results[i]["mainstream"]  = r.get("mainstream")
            results[i]["alternative"] = r.get("alternative")
            results[i]["cui_bono"]    = r.get("cui_bono")

    logger.info(f"[BATCH] ✅ Done — all formats generated for {n} items.\n")
    return results


def generate_invention_tweets_batch(
    inventions: list[dict],
    trending_tags: list = None,
) -> list[dict]:
    """Generate rewrite + hot_take for all inventions in one batch call."""
    if not inventions:
        return []
    logger.info(f"[BATCH] 🔬 Invention tweets for {len(inventions)} items...")
    trending = _fmt_trending(trending_tags or [])
    prompt   = INVENTION_PROMPT.format(
        count   = len(inventions),
        trending= trending,
        items   = _fmt_items([{
            "category":         inv.get("category","science"),
            "original_title":   inv.get("title",""),
            "original_summary": inv.get("summary",""),
            "source_name":      inv.get("source",""),
        } for inv in inventions]),
    )
    try:
        raw     = _call_llm(prompt, max_tokens=len(inventions) * 200)
        parsed  = _parse_json(raw)
        results = _safe_list(parsed, len(inventions), {"rewrite": None, "hot_take": None})
        return results
    except Exception as e:
        logger.warning(f"[BATCH] Invention batch failed: {e}")
        return [{"rewrite": None, "hot_take": None}] * len(inventions)


def generate_video_tweet(
    title: str, channel: str, description: str,
    category: str, video_url: str, trending_tags: list = None,
) -> dict:
    """Single video tweet (videos are few, no need to batch)."""
    trending = _fmt_trending(trending_tags or [])
    tone     = CATEGORY_TONE.get(category, "")
    prompt   = f"""\
Write factual tweet content for this YouTube video.
Context: {tone}
Trending hashtags: {trending}
- rewrite: max 260 chars, include placeholder [LINK], add 1-2 hashtags
- hot_take: factual observation, max 260 chars, 1-2 hashtags
Return ONLY valid JSON: {{"rewrite":"tweet [LINK] #Tag","hot_take":"tweet #Tag"}}

Channel: {channel}
Title: {title}
Description: {description[:300]}"""
    try:
        raw  = _call_llm(prompt, max_tokens=300)
        data = _parse_json(raw)
        for key in ("rewrite", "hot_take"):
            if data.get(key):
                data[key] = str(data[key]).replace("[LINK]", video_url)
        return data
    except Exception as e:
        logger.warning(f"Video tweet failed ({title[:40]}): {e}")
        return {"rewrite": None, "hot_take": None}


def generate_between_lines(
    all_items: list[dict], trending_tags: list = None,
) -> list[dict]:
    """Global intelligence pass — reads all headlines together."""
    logger.info("[BRAIN] Reading between the lines...")
    headlines = "\n".join(
        f"[{i['category'].upper()} | {i['source_name']}] {i['original_title']}"
        + (f" — {i['original_summary'][:80]}" if i.get("original_summary") else "")
        for i in all_items
    )
    trending = _fmt_trending(trending_tags or [])
    prompt   = BETWEEN_LINES_PROMPT.format(
        headlines=headlines[:12000], trending=trending
    )
    for attempt in range(2):
        try:
            pfx = RETRY_PREFIX if attempt > 0 else ""
            raw     = _call_llm(pfx + prompt, max_tokens=3000, batch=True)
            results = _parse_json(raw)
            if isinstance(results, list):
                logger.info(f"[BRAIN] {len(results)} observations.")
                return results
        except Exception as e:
            logger.warning(f"[BRAIN] Attempt {attempt+1} failed: {e}")
    return []


def generate_hypocrisy_tweets(
    all_items: list[dict], trending_tags: list = None,
) -> list[dict]:
    """Find factual contradictions across all headlines."""
    logger.info("[HYPOCRISY] Scanning for contradictions...")
    headlines = "\n".join(
        f"[{i['category'].upper()} | {i['source_name']}] {i['original_title']}"
        + (f" — {i['original_summary'][:80]}" if i.get("original_summary") else "")
        for i in all_items
    )
    trending = _fmt_trending(trending_tags or [])
    prompt   = HYPOCRISY_PROMPT.format(
        headlines=headlines[:10000], trending=trending
    )
    for attempt in range(2):
        try:
            pfx = RETRY_PREFIX if attempt > 0 else ""
            raw     = _call_llm(pfx + prompt, max_tokens=2000, batch=True)
            results = _parse_json(raw)
            if isinstance(results, list):
                logger.info(f"[HYPOCRISY] {len(results)} tweets.")
                return results
        except Exception as e:
            logger.warning(f"[HYPOCRISY] Attempt {attempt+1} failed: {e}")
    return []


def check_ollama() -> bool:
    try:
        resp   = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        ok     = any(OLLAMA_MODEL.split(":")[0] in m for m in models)
        logger.info(f"Ollama {'ready' if ok else 'running but model missing'}: {OLLAMA_MODEL}")
        return ok
    except Exception as e:
        logger.warning(f"Ollama not available: {e}")
        return False
