"""
viewer.py — Generates docs/index.html with:
  - Image thumbnails + download buttons on every news card
  - YouTube video cards (thumbnail, tweet content, watch button)
  - 6 categories including Hypocrisy Watch
"""

import json
from datetime import datetime


def generate_viewer(
    items: list[dict],
    hypocrisy: list[dict],
    videos: list[dict],
    output_path: str,
):
    date_str   = datetime.now().strftime("%d %b %Y, %I:%M %p")
    total_news = len(items)
    total_vids = len(videos)
    total_hype = len(hypocrisy)

    # items_json = json.dumps(items,     ensure_ascii=False)
    # hype_json  = json.dumps(hypocrisy, ensure_ascii=False)
    # vids_json  = json.dumps(videos,    ensure_ascii=False)

  def _safe_json(data):
    return (
        json.dumps(data, ensure_ascii=True)
        .replace('</script>', r'<\/script>')
        .replace('`', r'\u0060')
        .replace('$', r'\u0024')
    )

items_json = _safe_json(items)
hype_json  = _safe_json(hypocrisy)
vids_json  = _safe_json(videos)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>NewsAgent · {date_str}</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
:root{{
  --bg:#0d0f12;--surface:#13161b;--border:#1f2430;--border-hi:#2e3547;
  --text:#e2e6f0;--muted:#5a6070;--accent:#f0c040;
  --c-usa:#4f8ef7;--c-world:#3ec97e;--c-india:#f06040;
  --c-telugu:#c060f0;--c-film:#f0c040;--c-hype:#e05252;--c-yt:#ff0000;
  --font-d:'Playfair Display',serif;
  --font-m:'IBM Plex Mono',monospace;
  --font-b:'IBM Plex Sans',sans-serif;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--bg);color:var(--text);font-family:var(--font-b);font-size:14px;line-height:1.6;}}

header{{border-bottom:1px solid var(--border);background:var(--surface);padding:0 24px;display:flex;align-items:center;gap:16px;height:60px;position:sticky;top:0;z-index:200;}}
.logo{{font-family:var(--font-d);font-size:21px;font-weight:900;color:var(--accent);white-space:nowrap;}}
.logo span{{color:var(--text);font-weight:700;}}
.hdate{{font-family:var(--font-m);font-size:11px;color:var(--muted);}}
.hstats{{display:flex;gap:16px;margin-left:auto;}}
.hstat{{font-family:var(--font-m);font-size:11px;color:var(--muted);}}
.hstat b{{color:var(--text);}}

.shell{{display:flex;max-width:1300px;margin:0 auto;}}

/* Sidebar */
.sidenav{{width:200px;min-width:200px;border-right:1px solid var(--border);padding:20px 0;position:sticky;top:60px;height:calc(100vh - 60px);overflow-y:auto;background:var(--surface);}}
.nav-lbl{{font-family:var(--font-m);font-size:9px;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);padding:0 16px;margin-bottom:6px;}}
.nav-btn{{display:flex;align-items:center;gap:8px;width:100%;background:none;border:none;border-radius:8px;padding:8px 12px;color:var(--muted);font-family:var(--font-b);font-size:13px;font-weight:500;cursor:pointer;transition:all .15s;text-align:left;}}
.nav-btn:hover{{background:var(--border);color:var(--text);}}
.nav-btn.active{{font-weight:600;}}
.nav-btn.active.n-usa   {{background:rgba(79,142,247,.12);color:var(--c-usa);}}
.nav-btn.active.n-world {{background:rgba(62,201,126,.12);color:var(--c-world);}}
.nav-btn.active.n-india {{background:rgba(240,96,64,.12); color:var(--c-india);}}
.nav-btn.active.n-tel   {{background:rgba(192,96,240,.12);color:var(--c-telugu);}}
.nav-btn.active.n-film  {{background:rgba(240,192,64,.12);color:var(--c-film);}}
.nav-btn.active.n-hype  {{background:rgba(224,82,82,.12); color:var(--c-hype);}}
.nav-cnt{{margin-left:auto;background:var(--border);border-radius:10px;font-family:var(--font-m);font-size:10px;padding:1px 7px;color:var(--muted);}}
.nav-btn.active .nav-cnt{{background:rgba(255,255,255,.1);color:currentColor;}}
.nav-div{{height:1px;background:var(--border);margin:10px 12px;}}

/* Main */
.main{{flex:1;padding:24px 24px 80px;min-width:0;}}
.topbar{{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:20px;}}
.search-box{{background:var(--surface);border:1px solid var(--border-hi);border-radius:8px;color:var(--text);font-family:var(--font-b);font-size:13px;padding:7px 14px;outline:none;width:240px;}}
.search-box:focus{{border-color:var(--accent);}}
.search-box::placeholder{{color:var(--muted);}}
.fmt-pills{{display:flex;gap:5px;flex-wrap:wrap;margin-left:auto;align-items:center;}}
.fmt-lbl{{font-family:var(--font-m);font-size:10px;color:var(--muted);}}
.fpill{{background:transparent;border:1px solid var(--border-hi);color:var(--muted);border-radius:20px;padding:5px 13px;font-family:var(--font-m);font-size:11px;cursor:pointer;transition:all .15s;}}
.fpill:hover{{border-color:var(--accent);color:var(--accent);}}
.fpill.active{{background:var(--accent);border-color:var(--accent);color:#0d0f12;font-weight:600;}}

/* Section heading */
.sec-head{{display:flex;align-items:center;gap:12px;margin-bottom:18px;padding-bottom:14px;border-bottom:2px solid var(--border);}}
.sec-icon{{font-size:22px;}}
.sec-title{{font-family:var(--font-d);font-size:24px;font-weight:900;}}
.sec-count{{font-family:var(--font-m);font-size:12px;color:var(--muted);}}
.sec-usa   .sec-title{{color:var(--c-usa);}}
.sec-world .sec-title{{color:var(--c-world);}}
.sec-india .sec-title{{color:var(--c-india);}}
.sec-telugu .sec-title{{color:var(--c-telugu);}}
.sec-film  .sec-title{{color:var(--c-film);}}
.sec-hype  .sec-title{{color:var(--c-hype);}}
.sec-hype  .sec-head{{border-bottom-color:rgba(224,82,82,.25);}}

.subsec-lbl{{font-family:var(--font-m);font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);margin:24px 0 12px;display:flex;align-items:center;gap:10px;}}
.subsec-lbl::after{{content:'';flex:1;height:1px;background:var(--border);}}

/* ── NEWS CARD ─────────────────────────────────────────────── */
.news-card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;margin-bottom:16px;overflow:hidden;animation:fi .2s ease;}}
.news-card:hover{{border-color:var(--border-hi);}}
@keyframes fi{{from{{opacity:0;transform:translateY(5px)}}to{{opacity:1}}}}

/* Image area */
.nc-img-wrap{{position:relative;background:var(--border);overflow:hidden;max-height:220px;}}
.nc-img-wrap img{{width:100%;display:block;object-fit:cover;max-height:220px;transition:opacity .2s;}}
.nc-img-wrap img.errored{{display:none;}}
.img-overlay{{position:absolute;top:8px;right:8px;display:flex;gap:6px;}}
.img-btn{{background:rgba(13,15,18,.75);border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(6px);border-radius:6px;color:var(--text);font-family:var(--font-m);font-size:10px;padding:4px 10px;cursor:pointer;text-decoration:none;display:flex;align-items:center;gap:4px;transition:all .15s;}}
.img-btn:hover{{background:rgba(240,192,64,.9);color:#0d0f12;border-color:transparent;}}
.yt-badge{{position:absolute;bottom:8px;left:8px;background:#ff0000;color:#fff;border-radius:5px;font-family:var(--font-m);font-size:10px;font-weight:600;padding:3px 8px;letter-spacing:.3px;}}

/* Card head */
.nc-head{{display:flex;align-items:flex-start;gap:8px;padding:11px 15px 9px;border-bottom:1px solid var(--border);}}
.src-tag{{font-family:var(--font-m);font-size:10px;font-weight:500;padding:2px 8px;border-radius:4px;text-transform:uppercase;letter-spacing:.5px;}}
.t-usa   {{background:rgba(79,142,247,.15);color:var(--c-usa);}}
.t-world {{background:rgba(62,201,126,.15);color:var(--c-world);}}
.t-india {{background:rgba(240,96,64,.15); color:var(--c-india);}}
.t-telugu{{background:rgba(192,96,240,.15);color:var(--c-telugu);}}
.t-film  {{background:rgba(240,192,64,.15);color:var(--c-film);}}
.nc-src{{font-family:var(--font-m);font-size:10px;color:var(--muted);margin-left:auto;text-align:right;white-space:nowrap;}}

.nc-orig{{padding:10px 15px;border-bottom:1px solid var(--border);}}
.nc-ttl{{font-family:var(--font-d);font-size:15px;font-weight:700;line-height:1.35;}}
.nc-ttl a{{color:var(--text);text-decoration:none;}}
.nc-ttl a:hover{{color:var(--accent);}}
.nc-sum{{color:var(--muted);font-size:12px;margin-top:5px;display:none;}}
.tog{{background:none;border:none;color:var(--muted);font-family:var(--font-m);font-size:10px;cursor:pointer;text-decoration:underline;text-underline-offset:2px;padding:2px 0;}}
.tog:hover{{color:var(--accent);}}

.nc-tabs{{display:flex;border-bottom:1px solid var(--border);padding:0 15px;}}
.ftab{{background:none;border:none;border-bottom:2px solid transparent;color:var(--muted);font-family:var(--font-m);font-size:11px;padding:7px 10px;cursor:pointer;transition:all .15s;margin-bottom:-1px;}}
.ftab:hover{{color:var(--text);}}
.ftab.active{{color:var(--accent);border-bottom-color:var(--accent);}}
.nc-panels{{padding:12px 15px 15px;}}
.panel{{display:none;}}
.panel.active{{display:block;}}

/* Tweet box */
.tweet-box{{background:var(--bg);border:1px solid var(--border-hi);border-radius:8px;padding:11px 46px 11px 13px;font-size:14px;line-height:1.65;position:relative;white-space:pre-wrap;word-break:break-word;}}
.cp-btn{{position:absolute;top:9px;right:9px;background:var(--surface);border:1px solid var(--border-hi);border-radius:6px;color:var(--muted);font-family:var(--font-m);font-size:10px;padding:4px 9px;cursor:pointer;transition:all .15s;white-space:nowrap;}}
.cp-btn:hover{{background:var(--accent);color:#0d0f12;border-color:var(--accent);}}
.cp-btn.ok{{background:#3ec97e;color:#0d0f12;border-color:#3ec97e;}}
.char-c{{font-family:var(--font-m);font-size:10px;color:var(--muted);margin-top:4px;text-align:right;}}
.char-c.warn{{color:#e08a30;}}
.char-c.over{{color:var(--c-hype);}}

/* Thread */
.thread-list{{display:flex;flex-direction:column;gap:7px;}}
.thread-tw{{background:var(--bg);border:1px solid var(--border-hi);border-radius:8px;padding:9px 46px 9px 13px;position:relative;font-size:14px;line-height:1.65;}}
.thread-n{{font-family:var(--font-m);font-size:10px;color:var(--c-usa);margin-bottom:3px;}}
.tcp{{position:absolute;top:9px;right:9px;background:var(--surface);border:1px solid var(--border-hi);border-radius:6px;color:var(--muted);font-family:var(--font-m);font-size:10px;padding:3px 8px;cursor:pointer;transition:all .15s;}}
.tcp:hover{{background:var(--c-usa);color:#fff;border-color:var(--c-usa);}}
.tcp.ok{{background:#3ec97e;color:#0d0f12;border-color:#3ec97e;}}
.cp-all{{margin-top:9px;background:transparent;border:1px solid var(--c-usa);border-radius:6px;color:var(--c-usa);font-family:var(--font-m);font-size:11px;padding:6px 14px;cursor:pointer;width:100%;transition:all .15s;}}
.cp-all:hover{{background:var(--c-usa);color:#fff;}}

/* Poll */
.poll-tw{{background:var(--bg);border:1px solid var(--border-hi);border-radius:8px;padding:11px 46px 11px 13px;position:relative;font-size:14px;line-height:1.65;margin-bottom:9px;}}
.poll-opts{{display:grid;grid-template-columns:1fr 1fr;gap:6px;}}
.poll-opt{{background:var(--bg);border:1px solid var(--border-hi);border-radius:6px;padding:6px 11px;font-family:var(--font-m);font-size:11px;color:var(--c-usa);}}
.poll-note{{font-family:var(--font-m);font-size:10px;color:var(--muted);margin-top:7px;}}

/* ── VIDEO CARD ────────────────────────────────────────────── */
.video-card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;margin-bottom:14px;display:flex;gap:0;overflow:hidden;animation:fi .2s ease;}}
.video-card:hover{{border-color:var(--border-hi);}}
.vc-thumb{{position:relative;width:200px;min-width:200px;background:var(--border);overflow:hidden;}}
.vc-thumb img{{width:100%;height:100%;object-fit:cover;display:block;}}
.vc-thumb img.errored{{opacity:.3;}}
.vc-play{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.3);opacity:0;transition:opacity .2s;}}
.video-card:hover .vc-play{{opacity:1;}}
.vc-play-icon{{width:42px;height:42px;background:#ff0000;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;}}
.vc-trending{{position:absolute;top:6px;left:6px;background:#ff0000;color:#fff;border-radius:4px;font-family:var(--font-m);font-size:9px;font-weight:600;padding:2px 6px;}}
.vc-body{{flex:1;padding:13px 15px;min-width:0;}}
.vc-channel{{font-family:var(--font-m);font-size:10px;color:var(--muted);margin-bottom:4px;display:flex;align-items:center;gap:8px;}}
.vc-channel .yt-ico{{color:#ff0000;}}
.vc-title{{font-family:var(--font-d);font-size:14px;font-weight:700;line-height:1.35;margin-bottom:10px;}}
.vc-title a{{color:var(--text);text-decoration:none;}}
.vc-title a:hover{{color:#ff0000;}}
.vc-tweets{{display:flex;flex-direction:column;gap:7px;}}
.vc-tweet-lbl{{font-family:var(--font-m);font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:3px;}}
.none-msg{{color:var(--muted);font-family:var(--font-m);font-size:12px;padding:6px 0;}}

/* ── HYPOCRISY CARD ────────────────────────────────────────── */
.hype-card{{background:var(--surface);border:1px solid rgba(224,82,82,.22);border-left:3px solid var(--c-hype);border-radius:12px;margin-bottom:13px;padding:15px;animation:fi .2s ease;}}
.hype-card:hover{{border-color:rgba(224,82,82,.45);border-left-color:var(--c-hype);}}
.hype-tw{{font-size:15px;line-height:1.7;position:relative;padding-right:88px;white-space:pre-wrap;word-break:break-word;}}
.hype-based{{margin-top:9px;font-family:var(--font-m);font-size:11px;color:var(--muted);border-top:1px solid var(--border);padding-top:8px;}}
.hype-based b{{color:rgba(224,82,82,.7);}}
.hcat{{display:inline-block;font-family:var(--font-m);font-size:9px;padding:2px 7px;border-radius:4px;margin-right:5px;text-transform:uppercase;letter-spacing:.5px;}}

.empty{{text-align:center;padding:60px 20px;color:var(--muted);font-family:var(--font-d);font-size:20px;}}
.empty small{{display:block;font-family:var(--font-b);font-size:13px;margin-top:8px;}}
</style>
</head>
<body>

<header>
  <div class="logo">News<span>Agent</span></div>
  <div class="hdate">{date_str}</div>
  <div class="hstats">
    <div class="hstat">📰 <b>{total_news}</b> news</div>
    <div class="hstat">📹 <b>{total_vids}</b> videos</div>
    <div class="hstat">🎭 <b>{total_hype}</b> hypocrisy</div>
  </div>
</header>

<div class="shell">
  <nav class="sidenav">
    <div style="margin-bottom:12px;">
      <div class="nav-lbl">Categories</div>
      <button class="nav-btn n-usa    active" onclick="showCat('usa',   this)">🇺🇸 <span>USA</span>          <span class="nav-cnt" id="nc-usa">—</span></button>
      <button class="nav-btn n-world"         onclick="showCat('world', this)">🌍 <span>International</span> <span class="nav-cnt" id="nc-world">—</span></button>
      <button class="nav-btn n-india"         onclick="showCat('india', this)">🇮🇳 <span>India</span>        <span class="nav-cnt" id="nc-india">—</span></button>
      <button class="nav-btn n-tel"           onclick="showCat('telugu',this)">🎙️ <span>Telugu</span>        <span class="nav-cnt" id="nc-telugu">—</span></button>
      <button class="nav-btn n-film"          onclick="showCat('film',  this)">🎬 <span>Telugu Film</span>  <span class="nav-cnt" id="nc-film">—</span></button>
      <div class="nav-div"></div>
      <button class="nav-btn n-hype"          onclick="showCat('hype',  this)">🎭 <span>Hypocrisy</span>    <span class="nav-cnt" id="nc-hype">—</span></button>
    </div>
  </nav>

  <main class="main">
    <div class="topbar">
      <input class="search-box" placeholder="🔍 Search headlines…" oninput="doSearch(this.value)"/>
      <div class="fmt-pills" id="fmt-pills">
        <span class="fmt-lbl">Format:</span>
        <button class="fpill active" onclick="setFmt('all',this)">All</button>
        <button class="fpill" onclick="setFmt('rewrite',this)">✍️ Rewrite</button>
        <button class="fpill" onclick="setFmt('hot_take',this)">🔥 Hot Take</button>
        <button class="fpill" onclick="setFmt('thread',this)">🧵 Thread</button>
        <button class="fpill" onclick="setFmt('poll',this)">📊 Poll</button>
      </div>
    </div>

    <div id="sec-usa"    class="cat-sec sec-usa"   ></div>
    <div id="sec-world"  class="cat-sec sec-world"  style="display:none"></div>
    <div id="sec-india"  class="cat-sec sec-india"  style="display:none"></div>
    <div id="sec-telugu" class="cat-sec sec-telugu" style="display:none"></div>
    <div id="sec-film"   class="cat-sec sec-film"   style="display:none"></div>
    <div id="sec-hype"   class="cat-sec sec-hype"   style="display:none"></div>
  </main>
</div>

<script>
const NEWS  = {items_json};
const HYPE  = {hype_json};
const VIDS  = {vids_json};

const CAT_MAP  = {{usa:'usa',world:'world',india:'india',telugu:'telugu',telugu_film:'film'}};
const CAT_META = {{
  usa:   {{lbl:'USA',           icon:'🇺🇸',sec:'sec-usa',   tcls:'t-usa',   secCls:'sec-usa'}},
  world: {{lbl:'International', icon:'🌍', sec:'sec-world', tcls:'t-world', secCls:'sec-world'}},
  india: {{lbl:'India',         icon:'🇮🇳',sec:'sec-india', tcls:'t-india', secCls:'sec-india'}},
  telugu:{{lbl:'Telugu',        icon:'🎙️', sec:'sec-telugu',tcls:'t-telugu',secCls:'sec-telugu'}},
  film:  {{lbl:'Telugu Film',   icon:'🎬', sec:'sec-film',  tcls:'t-film',  secCls:'sec-film'}},
  hype:  {{lbl:'Hypocrisy Watch',icon:'🎭',sec:'sec-hype',  tcls:'',        secCls:'sec-hype'}},
}};
const HCAT_CLR = {{usa:'var(--c-usa)',world:'var(--c-world)',india:'var(--c-india)',telugu:'var(--c-telugu)',telugu_film:'var(--c-film)'}};
const FMT_LBL  = {{rewrite:'✍️ Rewrite',hot_take:'🔥 Hot Take',thread:'🧵 Thread',poll:'📊 Poll'}};

let activeCat = 'usa', activeFmt = 'all', searchQ = '';

// ── Utils ──────────────────────────────────────────────────────────────────
function e(s){{return(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}}
function cp(text,btn){{
  navigator.clipboard.writeText(text).then(()=>{{
    const o=btn.textContent;btn.textContent='✓ Copied!';btn.classList.add('ok');
    setTimeout(()=>{{btn.textContent=o;btn.classList.remove('ok');}},1800);
  }});
}}
function imgErr(img){{img.classList.add('errored');img.closest('.nc-img-wrap,.vc-thumb')?.style.setProperty('display','none');}}

// ── Tweet rendering ────────────────────────────────────────────────────────
function bSimple(text){{
  if(!text)return'<div class="none-msg">Not generated</div>';
  const n=text.length,cls=n>280?'over':n>240?'warn':'';
  return`<div class="tweet-box">${{e(text)}}<button class="cp-btn" onclick="cp(this.dataset.t,this)" data-t="${{e(text)}}">📋 Copy</button></div><div class="char-c ${{cls}}">${{n}} / 280</div>`;
}}
function bThread(tweets){{
  if(!tweets?.length)return'<div class="none-msg">Not generated</div>';
  const n=tweets.length;
  const rows=tweets.map((t,i)=>`<div class="thread-tw"><div class="thread-n">${{i+1}}/${{n}}</div>${{e(t)}}<button class="tcp" onclick="cp(this.dataset.t,this)" data-t="${{e(t)}}">📋</button></div>`).join('');
  const all=tweets.map((t,i)=>`${{i+1}}/${{n}} ${{t}}`).join('\n\n');
  return`<div class="thread-list">${{rows}}</div><button class="cp-all" onclick="cp(this.dataset.t,this)" data-t="${{e(all)}}">📋 Copy Entire Thread</button>`;
}}
function bPoll(d){{
  if(!d)return'<div class="none-msg">Not generated</div>';
  const opts=(d.options||[]).map(o=>`<div class="poll-opt">${{e(o)}}</div>`).join('');
  return`<div class="poll-tw">${{e(d.tweet)}}<button class="cp-btn" onclick="cp(this.dataset.t,this)" data-t="${{e(d.tweet)}}">📋 Copy</button></div><div class="poll-opts">${{opts}}</div><div class="poll-note">ℹ️ Create poll manually on X with these 4 options</div>`;
}}

// ── News card ──────────────────────────────────────────────────────────────
function buildNewsCard(item, uid){{
  const dk   = CAT_MAP[item.category]||item.category;
  const meta = CAT_META[dk]||CAT_META.usa;
  const c    = item.content||{{}};
  const fmts = activeFmt==='all'?['rewrite','hot_take','thread','poll']:[activeFmt];

  // Image block
  let imgHtml = '';
  if(item.image_url){{
    const hasYt = !!item.youtube_id;
    imgHtml = `<div class="nc-img-wrap">
      <img src="${{e(item.image_url)}}" alt="" loading="lazy" onerror="imgErr(this)"/>
      <div class="img-overlay">
        <a class="img-btn" href="${{e(item.image_url)}}" target="_blank" rel="noopener">🖼️ View Image</a>
        ${{hasYt?`<a class="img-btn" href="https://www.youtube.com/watch?v=${{item.youtube_id}}" target="_blank" rel="noopener">▶ Watch Video</a>`:''}}
      </div>
      ${{hasYt?'<div class="yt-badge">▶ YouTube</div>':''}}
    </div>`;
  }}

  const tabs   = fmts.map((f,i)=>`<button class="ftab${{i===0?' active':''}}" onclick="swTab(this,'${{uid}}','${{f}}')"> ${{FMT_LBL[f]}}</button>`).join('');
  const panels = fmts.map((f,i)=>{{
    const inner = f==='thread'?bThread(c.thread):f==='poll'?bPoll(c.poll):bSimple(c[f]);
    return`<div class="panel${{i===0?' active':''}}" data-uid="${{uid}}" data-fmt="${{f}}">${{inner}}</div>`;
  }}).join('');

  return`<div class="news-card" data-title="${{e(item.original_title.toLowerCase())}}">
    ${{imgHtml}}
    <div class="nc-head">
      <span class="src-tag ${{meta.tcls}}">${{meta.icon}} ${{meta.lbl}}</span>
      <div class="nc-src">${{e(item.source_name||'')}}</div>
    </div>
    <div class="nc-orig">
      <div class="nc-ttl"><a href="${{e(item.source_url)}}" target="_blank">${{e(item.original_title)}} ↗</a></div>
      ${{item.original_summary?`<button class="tog" onclick="togSum(this)">show summary ▾</button><div class="nc-sum">${{e(item.original_summary)}}</div>`:''}}
    </div>
    <div class="nc-tabs">${{tabs}}</div>
    <div class="nc-panels">${{panels}}</div>
  </div>`;
}}

// ── Video card ─────────────────────────────────────────────────────────────
function buildVideoCard(vid){{
  const tw  = vid.tweet_content||{{}};
  const rw  = tw.rewrite||null;
  const ht  = tw.hot_take||null;

  const tweetsHtml = [
    rw ? `<div><div class="vc-tweet-lbl">✍️ Rewrite</div>${{bSimple(rw)}}</div>` : '',
    ht ? `<div><div class="vc-tweet-lbl">🔥 Hot Take</div>${{bSimple(ht)}}</div>` : '',
  ].filter(Boolean).join('') || '<div class="none-msg">Tweet content generating…</div>';

  return`<div class="video-card" data-title="${{e((vid.title).toLowerCase())}}">
    <div class="vc-thumb">
      <img src="${{e(vid.thumbnail)}}" alt="" loading="lazy" onerror="imgErr(this)"/>
      <a class="vc-play" href="${{e(vid.url)}}" target="_blank" rel="noopener">
        <div class="vc-play-icon">▶</div>
      </a>
      ${{vid.trending?'<div class="vc-trending">🔥 TRENDING</div>':''}}
    </div>
    <div class="vc-body">
      <div class="vc-channel"><span class="yt-ico">▶</span>${{e(vid.channel)}}</div>
      <div class="vc-title"><a href="${{e(vid.url)}}" target="_blank">${{e(vid.title)}}</a></div>
      <div class="vc-tweets">${{tweetsHtml}}</div>
    </div>
  </div>`;
}}

// ── Hypocrisy card ─────────────────────────────────────────────────────────
function buildHypeCard(h){{
  const col = HCAT_CLR[h.category]||'var(--c-hype)';
  return`<div class="hype-card" data-title="${{e((h.tweet+h.based_on).toLowerCase())}}">
    <div class="hype-tw">${{e(h.tweet)}}<button class="cp-btn" onclick="cp(this.dataset.t,this)" data-t="${{e(h.tweet)}}">📋 Copy</button></div>
    <div class="hype-based"><b>Based on:</b> ${{e(h.based_on||'')}}
      ${{h.category?`<span class="hcat" style="background:${{col}}22;color:${{col}}">${{(h.category||'').replace('_',' ').toUpperCase()}}</span>`:''}}
    </div>
  </div>`;
}}

// ── Render ─────────────────────────────────────────────────────────────────
function renderAll(){{
  const groups = {{usa:[],world:[],india:[],telugu:[],film:[]}};
  for(const item of NEWS){{
    const dk=CAT_MAP[item.category]||item.category;
    if(groups[dk]) groups[dk].push(item);
  }}
  const vidGroups = {{usa:[],world:[],india:[],telugu:[],film:[]}};
  for(const v of VIDS){{
    const dk=CAT_MAP[v.category]||v.category;
    if(vidGroups[dk]) vidGroups[dk].push(v);
  }}

  document.getElementById('nc-usa').textContent    = groups.usa.length   + (vidGroups.usa.length?   ` +${{vidGroups.usa.length}}▶`:'');
  document.getElementById('nc-world').textContent  = groups.world.length  + (vidGroups.world.length? ` +${{vidGroups.world.length}}▶`:'');
  document.getElementById('nc-india').textContent  = groups.india.length  + (vidGroups.india.length? ` +${{vidGroups.india.length}}▶`:'');
  document.getElementById('nc-telugu').textContent = groups.telugu.length + (vidGroups.telugu.length?` +${{vidGroups.telugu.length}}▶`:'');
  document.getElementById('nc-film').textContent   = groups.film.length   + (vidGroups.film.length?  ` +${{vidGroups.film.length}}▶`:'');
  document.getElementById('nc-hype').textContent   = HYPE.length;

  const orderedCats = [['usa','usa'],['world','world'],['india','india'],['telugu','telugu'],['film','film']];
  for(const [dk,secId] of orderedCats){{
    const sec   = document.getElementById('sec-'+secId);
    const meta  = CAT_META[dk];
    const items = (groups[dk]||[]).filter(it=>!searchQ||it.original_title.toLowerCase().includes(searchQ));
    const vids  = (vidGroups[dk]||[]).filter(v=>!searchQ||v.title.toLowerCase().includes(searchQ));

    const newsHtml = items.length
      ? items.map((it,i)=>buildNewsCard(it,`${{dk}}_${{i}}`)).join('')
      : '<div class="empty" style="padding:30px">No news items match<small>Try different filters</small></div>';

    const vidsHtml = vids.length
      ? `<div class="subsec-lbl">📹 Videos — ${{vids.length}}</div>` + vids.map(buildVideoCard).join('')
      : '';

    sec.innerHTML = `<div class="sec-head">
        <span class="sec-icon">${{meta.icon}}</span>
        <span class="sec-title">${{meta.lbl}}</span>
        <span class="sec-count">${{items.length}} news · ${{vids.length}} videos</span>
      </div>${{newsHtml}}${{vidsHtml}}`;
  }}

  // Hypocrisy
  const hSec   = document.getElementById('sec-hype');
  const hItems = HYPE.filter(h=>!searchQ||(h.tweet+h.based_on).toLowerCase().includes(searchQ));
  hSec.innerHTML = `<div class="sec-head">
      <span class="sec-icon">🎭</span>
      <span class="sec-title">Hypocrisy Watch</span>
      <span class="sec-count">${{hItems.length}} tweets</span>
    </div>` + (hItems.length?hItems.map(buildHypeCard).join(''):'<div class="empty">No hypocrisy found today<small>(Unlikely, but possible)</small></div>');
}}

// ── Controls ───────────────────────────────────────────────────────────────
function showCat(cat,btn){{
  activeCat=cat;
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.cat-sec').forEach(s=>s.style.display='none');
  const sid=cat==='hype'?'sec-hype':cat==='film'?'sec-film':'sec-'+cat;
  document.getElementById(sid).style.display='block';
  document.getElementById('fmt-pills').style.display=cat==='hype'?'none':'flex';
}}
function setFmt(fmt,btn){{
  activeFmt=fmt;
  document.querySelectorAll('.fpill').forEach(p=>p.classList.remove('active'));
  btn.classList.add('active');
  renderAll();
}}
function doSearch(q){{searchQ=q.toLowerCase().trim();renderAll();}}
function swTab(btn,uid,fmt){{
  const card=btn.closest('.news-card');
  card.querySelectorAll('.ftab').forEach(t=>t.classList.remove('active'));
  card.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  btn.classList.add('active');
  card.querySelector(`.panel[data-uid="${{uid}}"][data-fmt="${{fmt}}"]`)?.classList.add('active');
}}
function togSum(btn){{
  const s=btn.nextElementSibling;
  s.style.display=s.style.display==='block'?'none':'block';
  btn.textContent=s.style.display==='block'?'hide summary ▴':'show summary ▾';
}}

renderAll();
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
