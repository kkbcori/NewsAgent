"""
viewer.py — Generates docs/index.html.
Uses string .replace() instead of f-strings to avoid Python/JS curly-brace conflicts.
All JavaScript uses var instead of const/let to avoid any template issues.
Data is stored in <script type="application/json"> tags — 100% safe from injection.
"""

import json
from datetime import datetime


def _safe_json(data):
    s = json.dumps(data, ensure_ascii=True)
    s = s.replace("</script>", r"<\/script>")
    s = s.replace("`",         r"\u0060")
    s = s.replace("$",         r"\u0024")
    return s


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>NewsAgent &middot; __DATE__</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
:root {
  --bg:#0d0f12; --surface:#13161b; --border:#1f2430; --border-hi:#2e3547;
  --text:#e2e6f0; --muted:#5a6070; --accent:#f0c040;
  --c-usa:#4f8ef7; --c-world:#3ec97e; --c-india:#f06040;
  --c-telugu:#c060f0; --c-film:#f0c040; --c-hype:#e05252;
  --font-d:'Playfair Display',serif;
  --font-m:'IBM Plex Mono',monospace;
  --font-b:'IBM Plex Sans',sans-serif;
}
*,*::before,*::after { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--text); font-family:var(--font-b); font-size:14px; line-height:1.6; }
header { border-bottom:1px solid var(--border); background:var(--surface); padding:0 24px; display:flex; align-items:center; gap:16px; height:60px; position:sticky; top:0; z-index:200; }
.logo { font-family:var(--font-d); font-size:21px; font-weight:900; color:var(--accent); }
.logo span { color:var(--text); font-weight:700; }
.hdate { font-family:var(--font-m); font-size:11px; color:var(--muted); }
.hstats { display:flex; gap:16px; margin-left:auto; }
.hstat { font-family:var(--font-m); font-size:11px; color:var(--muted); }
.hstat b { color:var(--text); }
.shell { display:flex; max-width:1300px; margin:0 auto; }
.sidenav { width:200px; min-width:200px; border-right:1px solid var(--border); padding:20px 0; position:sticky; top:60px; height:calc(100vh - 60px); overflow-y:auto; background:var(--surface); }
.nav-lbl { font-family:var(--font-m); font-size:9px; text-transform:uppercase; letter-spacing:1.5px; color:var(--muted); padding:0 16px; margin-bottom:6px; }
.nav-btn { display:flex; align-items:center; gap:8px; width:100%; background:none; border:none; border-radius:8px; padding:8px 12px; color:var(--muted); font-family:var(--font-b); font-size:13px; font-weight:500; cursor:pointer; transition:all .15s; text-align:left; }
.nav-btn:hover { background:var(--border); color:var(--text); }
.nav-btn.active { font-weight:600; }
.nav-btn.active.n-usa   { background:rgba(79,142,247,.12);  color:var(--c-usa); }
.nav-btn.active.n-world { background:rgba(62,201,126,.12);  color:var(--c-world); }
.nav-btn.active.n-india { background:rgba(240,96,64,.12);   color:var(--c-india); }
.nav-btn.active.n-tel   { background:rgba(192,96,240,.12);  color:var(--c-telugu); }
.nav-btn.active.n-film  { background:rgba(240,192,64,.12);  color:var(--c-film); }
.nav-btn.active.n-hype  { background:rgba(224,82,82,.12);   color:var(--c-hype); }
.nav-cnt { margin-left:auto; background:var(--border); border-radius:10px; font-family:var(--font-m); font-size:10px; padding:1px 7px; color:var(--muted); }
.nav-btn.active .nav-cnt { background:rgba(255,255,255,.1); color:currentColor; }
.nav-div { height:1px; background:var(--border); margin:10px 12px; }
.main { flex:1; padding:24px 24px 80px; min-width:0; }
.topbar { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-bottom:20px; }
.search-box { background:var(--surface); border:1px solid var(--border-hi); border-radius:8px; color:var(--text); font-family:var(--font-b); font-size:13px; padding:7px 14px; outline:none; width:240px; }
.search-box:focus { border-color:var(--accent); }
.search-box::placeholder { color:var(--muted); }
.fmt-pills { display:flex; gap:5px; flex-wrap:wrap; margin-left:auto; align-items:center; }
.fmt-lbl { font-family:var(--font-m); font-size:10px; color:var(--muted); }
.fpill { background:transparent; border:1px solid var(--border-hi); color:var(--muted); border-radius:20px; padding:5px 13px; font-family:var(--font-m); font-size:11px; cursor:pointer; transition:all .15s; }
.fpill:hover { border-color:var(--accent); color:var(--accent); }
.fpill.active { background:var(--accent); border-color:var(--accent); color:#0d0f12; font-weight:600; }
.sec-head { display:flex; align-items:center; gap:12px; margin-bottom:18px; padding-bottom:14px; border-bottom:2px solid var(--border); }
.sec-icon { font-size:22px; }
.sec-title { font-family:var(--font-d); font-size:24px; font-weight:900; }
.sec-count { font-family:var(--font-m); font-size:12px; color:var(--muted); }
.sec-usa    .sec-title { color:var(--c-usa); }
.sec-world  .sec-title { color:var(--c-world); }
.sec-india  .sec-title { color:var(--c-india); }
.sec-telugu .sec-title { color:var(--c-telugu); }
.sec-film   .sec-title { color:var(--c-film); }
.sec-hype   .sec-title { color:var(--c-hype); }
.subsec-lbl { font-family:var(--font-m); font-size:10px; text-transform:uppercase; letter-spacing:1.5px; color:var(--muted); margin:24px 0 12px; display:flex; align-items:center; gap:10px; }
.subsec-lbl::after { content:''; flex:1; height:1px; background:var(--border); }
.news-card { background:var(--surface); border:1px solid var(--border); border-radius:12px; margin-bottom:16px; overflow:hidden; animation:fi .2s ease; }
.news-card:hover { border-color:var(--border-hi); }
@keyframes fi { from { opacity:0; transform:translateY(5px); } to { opacity:1; } }
.nc-img-wrap { position:relative; background:var(--border); overflow:hidden; max-height:220px; }
.nc-img-wrap img { width:100%; display:block; object-fit:cover; max-height:220px; }
.img-overlay { position:absolute; top:8px; right:8px; display:flex; gap:6px; }
.img-btn { background:rgba(13,15,18,.75); border:1px solid rgba(255,255,255,.12); backdrop-filter:blur(6px); border-radius:6px; color:var(--text); font-family:var(--font-m); font-size:10px; padding:4px 10px; cursor:pointer; text-decoration:none; transition:all .15s; }
.img-btn:hover { background:rgba(240,192,64,.9); color:#0d0f12; }
.yt-badge { position:absolute; bottom:8px; left:8px; background:#ff0000; color:#fff; border-radius:5px; font-family:var(--font-m); font-size:10px; font-weight:600; padding:3px 8px; }
.nc-head { display:flex; align-items:flex-start; gap:8px; padding:11px 15px 9px; border-bottom:1px solid var(--border); }
.src-tag { font-family:var(--font-m); font-size:10px; font-weight:500; padding:2px 8px; border-radius:4px; text-transform:uppercase; letter-spacing:.5px; }
.t-usa    { background:rgba(79,142,247,.15);  color:var(--c-usa); }
.t-world  { background:rgba(62,201,126,.15);  color:var(--c-world); }
.t-india  { background:rgba(240,96,64,.15);   color:var(--c-india); }
.t-telugu { background:rgba(192,96,240,.15);  color:var(--c-telugu); }
.t-film   { background:rgba(240,192,64,.15);  color:var(--c-film); }
.nc-src { font-family:var(--font-m); font-size:10px; color:var(--muted); margin-left:auto; white-space:nowrap; }
.nc-orig { padding:10px 15px; border-bottom:1px solid var(--border); }
.nc-ttl { font-family:var(--font-d); font-size:15px; font-weight:700; line-height:1.35; }
.nc-ttl a { color:var(--text); text-decoration:none; }
.nc-ttl a:hover { color:var(--accent); }
.nc-sum { color:var(--muted); font-size:12px; margin-top:5px; display:none; }
.tog { background:none; border:none; color:var(--muted); font-family:var(--font-m); font-size:10px; cursor:pointer; text-decoration:underline; padding:2px 0; }
.tog:hover { color:var(--accent); }
.nc-tabs { display:flex; border-bottom:1px solid var(--border); padding:0 15px; }
.ftab { background:none; border:none; border-bottom:2px solid transparent; color:var(--muted); font-family:var(--font-m); font-size:11px; padding:7px 10px; cursor:pointer; transition:all .15s; margin-bottom:-1px; }
.ftab:hover { color:var(--text); }
.ftab.active { color:var(--accent); border-bottom-color:var(--accent); }
.nc-panels { padding:12px 15px 15px; }
.panel { display:none; }
.panel.active { display:block; }
.tweet-box { background:var(--bg); border:1px solid var(--border-hi); border-radius:8px; padding:11px 80px 11px 13px; font-size:14px; line-height:1.65; position:relative; white-space:pre-wrap; word-break:break-word; }
.cp-btn { position:absolute; top:9px; right:9px; background:var(--surface); border:1px solid var(--border-hi); border-radius:6px; color:var(--muted); font-family:var(--font-m); font-size:10px; padding:4px 9px; cursor:pointer; transition:all .15s; white-space:nowrap; }
.cp-btn:hover { background:var(--accent); color:#0d0f12; border-color:var(--accent); }
.cp-btn.ok { background:#3ec97e; color:#0d0f12; }
.char-c { font-family:var(--font-m); font-size:10px; color:var(--muted); margin-top:4px; text-align:right; }
.char-c.warn { color:#e08a30; }
.char-c.over { color:var(--c-hype); }
.thread-list { display:flex; flex-direction:column; gap:7px; }
.thread-tw { background:var(--bg); border:1px solid var(--border-hi); border-radius:8px; padding:9px 50px 9px 13px; position:relative; font-size:14px; line-height:1.65; }
.thread-n { font-family:var(--font-m); font-size:10px; color:var(--c-usa); margin-bottom:3px; }
.tcp { position:absolute; top:9px; right:9px; background:var(--surface); border:1px solid var(--border-hi); border-radius:6px; color:var(--muted); font-family:var(--font-m); font-size:10px; padding:3px 8px; cursor:pointer; transition:all .15s; }
.tcp:hover { background:var(--c-usa); color:#fff; }
.tcp.ok { background:#3ec97e; color:#0d0f12; }
.cp-all { margin-top:9px; background:transparent; border:1px solid var(--c-usa); border-radius:6px; color:var(--c-usa); font-family:var(--font-m); font-size:11px; padding:6px 14px; cursor:pointer; width:100%; transition:all .15s; }
.cp-all:hover { background:var(--c-usa); color:#fff; }
.poll-tw { background:var(--bg); border:1px solid var(--border-hi); border-radius:8px; padding:11px 50px 11px 13px; position:relative; font-size:14px; line-height:1.65; margin-bottom:9px; }
.poll-opts { display:grid; grid-template-columns:1fr 1fr; gap:6px; }
.poll-opt { background:var(--bg); border:1px solid var(--border-hi); border-radius:6px; padding:6px 11px; font-family:var(--font-m); font-size:11px; color:var(--c-usa); }
.poll-note { font-family:var(--font-m); font-size:10px; color:var(--muted); margin-top:7px; }
.video-card { background:var(--surface); border:1px solid var(--border); border-radius:12px; margin-bottom:14px; display:flex; overflow:hidden; }
.video-card:hover { border-color:var(--border-hi); }
.vc-thumb { position:relative; width:200px; min-width:200px; background:var(--border); }
.vc-thumb img { width:100%; height:100%; object-fit:cover; display:block; }
.vc-play { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; background:rgba(0,0,0,.3); opacity:0; transition:opacity .2s; text-decoration:none; }
.video-card:hover .vc-play { opacity:1; }
.vc-play-icon { width:42px; height:42px; background:#ff0000; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#fff; font-size:18px; }
.vc-trending { position:absolute; top:6px; left:6px; background:#ff0000; color:#fff; border-radius:4px; font-family:var(--font-m); font-size:9px; font-weight:600; padding:2px 6px; }
.vc-body { flex:1; padding:13px 15px; min-width:0; }
.vc-channel { font-family:var(--font-m); font-size:10px; color:var(--muted); margin-bottom:4px; }
.vc-title { font-family:var(--font-d); font-size:14px; font-weight:700; line-height:1.35; margin-bottom:10px; }
.vc-title a { color:var(--text); text-decoration:none; }
.vc-title a:hover { color:#ff0000; }
.vc-tweet-lbl { font-family:var(--font-m); font-size:9px; text-transform:uppercase; letter-spacing:1px; color:var(--muted); margin-bottom:3px; }
.vc-tweets { display:flex; flex-direction:column; gap:7px; }
.hype-card { background:var(--surface); border:1px solid rgba(224,82,82,.22); border-left:3px solid var(--c-hype); border-radius:12px; margin-bottom:13px; padding:15px; }
.hype-card:hover { border-color:rgba(224,82,82,.45); }
.hype-tw { font-size:15px; line-height:1.7; position:relative; padding-right:80px; white-space:pre-wrap; word-break:break-word; }
.hype-based { margin-top:9px; font-family:var(--font-m); font-size:11px; color:var(--muted); border-top:1px solid var(--border); padding-top:8px; }
.hype-based b { color:rgba(224,82,82,.7); }
.hcat { display:inline-block; font-family:var(--font-m); font-size:9px; padding:2px 7px; border-radius:4px; margin-right:5px; text-transform:uppercase; }
.none-msg { color:var(--muted); font-family:var(--font-m); font-size:12px; padding:6px 0; }
.empty { text-align:center; padding:60px 20px; color:var(--muted); font-family:var(--font-d); font-size:20px; }
.empty small { display:block; font-family:var(--font-b); font-size:13px; margin-top:8px; }
</style>
</head>
<body>

<header>
  <div class="logo">News<span>Agent</span></div>
  <div class="hdate">__DATE__</div>
  <div class="hstats">
    <div class="hstat">&#128240; <b>__TOTAL_NEWS__</b> news</div>
    <div class="hstat">&#128249; <b>__TOTAL_VIDS__</b> videos</div>
    <div class="hstat">&#127917; <b>__TOTAL_HYPE__</b> hypocrisy</div>
  </div>
</header>

<div class="shell">
  <nav class="sidenav">
    <div class="nav-lbl">Categories</div>
    <button class="nav-btn n-usa active" onclick="showCat('usa',   this)">&#127482;&#127480; USA           <span class="nav-cnt" id="nc-usa">0</span></button>
    <button class="nav-btn n-world"      onclick="showCat('world', this)">&#127757; International  <span class="nav-cnt" id="nc-world">0</span></button>
    <button class="nav-btn n-india"      onclick="showCat('india', this)">&#127470;&#127475; India        <span class="nav-cnt" id="nc-india">0</span></button>
    <button class="nav-btn n-tel"        onclick="showCat('telugu',this)">&#127897; Telugu         <span class="nav-cnt" id="nc-telugu">0</span></button>
    <button class="nav-btn n-film"       onclick="showCat('film',  this)">&#127909; Telugu Film    <span class="nav-cnt" id="nc-film">0</span></button>
    <div class="nav-div"></div>
    <button class="nav-btn n-hype"       onclick="showCat('hype',  this)">&#127917; Hypocrisy      <span class="nav-cnt" id="nc-hype">0</span></button>
  </nav>

  <main class="main">
    <div class="topbar">
      <input class="search-box" placeholder="Search headlines..." oninput="doSearch(this.value)"/>
      <div class="fmt-pills" id="fmt-pills">
        <span class="fmt-lbl">Format:</span>
        <button class="fpill active" onclick="setFmt('all',     this)">All</button>
        <button class="fpill"        onclick="setFmt('rewrite', this)">Rewrite</button>
        <button class="fpill"        onclick="setFmt('hot_take',this)">Hot Take</button>
        <button class="fpill"        onclick="setFmt('thread',  this)">Thread</button>
        <button class="fpill"        onclick="setFmt('poll',    this)">Poll</button>
      </div>
    </div>
    <div id="sec-usa"    class="cat-sec sec-usa"                    ></div>
    <div id="sec-world"  class="cat-sec sec-world"  style="display:none"></div>
    <div id="sec-india"  class="cat-sec sec-india"  style="display:none"></div>
    <div id="sec-telugu" class="cat-sec sec-telugu" style="display:none"></div>
    <div id="sec-film"   class="cat-sec sec-film"   style="display:none"></div>
    <div id="sec-hype"   class="cat-sec sec-hype"   style="display:none"></div>
  </main>
</div>

<script id="d-news" type="application/json">__ITEMS_JSON__</script>
<script id="d-hype" type="application/json">__HYPE_JSON__</script>
<script id="d-vids" type="application/json">__VIDS_JSON__</script>

<script>
var NEWS = JSON.parse(document.getElementById('d-news').textContent);
var HYPE = JSON.parse(document.getElementById('d-hype').textContent);
var VIDS = JSON.parse(document.getElementById('d-vids').textContent);

var activeCat = 'usa';
var activeFmt = 'all';
var searchQ   = '';

var CAT_MAP = {
  usa:'usa', world:'world', india:'india',
  telugu:'telugu', telugu_film:'film'
};
var CAT_META = {
  usa:   {lbl:'USA',            icon:'&#127482;&#127480;', tcls:'t-usa'},
  world: {lbl:'International',  icon:'&#127757;',          tcls:'t-world'},
  india: {lbl:'India',          icon:'&#127470;&#127475;', tcls:'t-india'},
  telugu:{lbl:'Telugu',         icon:'&#127897;',          tcls:'t-telugu'},
  film:  {lbl:'Telugu Film',    icon:'&#127909;',          tcls:'t-film'},
  hype:  {lbl:'Hypocrisy Watch',icon:'&#127917;',          tcls:''}
};
var HCAT_CLR = {
  usa:'var(--c-usa)', world:'var(--c-world)', india:'var(--c-india)',
  telugu:'var(--c-telugu)', telugu_film:'var(--c-film)'
};
var FMT_LBL = {rewrite:'Rewrite', hot_take:'Hot Take', thread:'Thread', poll:'Poll'};

function esc(s) {
  return String(s||'')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function copyText(text, btn) {
  navigator.clipboard.writeText(text).then(function() {
    var o = btn.textContent;
    btn.textContent = 'Copied!';
    btn.classList.add('ok');
    setTimeout(function(){ btn.textContent = o; btn.classList.remove('ok'); }, 1800);
  });
}

function imgErr(img) {
  var w = img.closest('.nc-img-wrap') || img.closest('.vc-thumb');
  if (w) w.style.display = 'none';
}

function bSimple(text) {
  if (!text) return '<div class="none-msg">Not generated</div>';
  var n = text.length;
  var cls = n > 280 ? 'over' : n > 240 ? 'warn' : '';
  return '<div class="tweet-box">' + esc(text) +
    '<button class="cp-btn" data-t="' + esc(text) + '" onclick="copyText(this.dataset.t,this)">&#128203; Copy</button>' +
    '</div><div class="char-c ' + cls + '">' + n + ' / 280</div>';
}

function bThread(tweets) {
  if (!tweets || !tweets.length) return '<div class="none-msg">Not generated</div>';
  var n = tweets.length;
  var rows = '';
  for (var i = 0; i < tweets.length; i++) {
    rows += '<div class="thread-tw"><div class="thread-n">' + (i+1) + '/' + n + '</div>' +
      esc(tweets[i]) +
      '<button class="tcp" data-t="' + esc(tweets[i]) + '" onclick="copyText(this.dataset.t,this)">Copy</button></div>';
  }
  var all = '';
  for (var j = 0; j < tweets.length; j++) { all += (j+1)+'/'+n+' '+tweets[j]+'\n\n'; }
  return '<div class="thread-list">' + rows + '</div>' +
    '<button class="cp-all" data-t="' + esc(all) + '" onclick="copyText(this.dataset.t,this)">Copy Entire Thread</button>';
}

function bPoll(d) {
  if (!d) return '<div class="none-msg">Not generated</div>';
  var opts = '';
  for (var i = 0; i < (d.options||[]).length; i++) {
    opts += '<div class="poll-opt">' + esc(d.options[i]) + '</div>';
  }
  return '<div class="poll-tw">' + esc(d.tweet) +
    '<button class="cp-btn" data-t="' + esc(d.tweet) + '" onclick="copyText(this.dataset.t,this)">Copy</button></div>' +
    '<div class="poll-opts">' + opts + '</div>' +
    '<div class="poll-note">Create poll manually on X with these 4 options</div>';
}

function buildNewsCard(item, uid) {
  var dk   = CAT_MAP[item.category] || item.category;
  var meta = CAT_META[dk] || CAT_META.usa;
  var c    = item.content || {};
  var fmts = activeFmt === 'all' ? ['rewrite','hot_take','thread','poll'] : [activeFmt];

  var imgHtml = '';
  if (item.image_url) {
    imgHtml = '<div class="nc-img-wrap">' +
      '<img src="' + esc(item.image_url) + '" loading="lazy" onerror="imgErr(this)" alt=""/>' +
      '<div class="img-overlay">' +
      '<a class="img-btn" href="' + esc(item.image_url) + '" target="_blank">View Image</a>' +
      (item.youtube_id ? '<a class="img-btn" href="https://www.youtube.com/watch?v=' + esc(item.youtube_id) + '" target="_blank">Watch Video</a>' : '') +
      '</div>' +
      (item.youtube_id ? '<div class="yt-badge">YouTube</div>' : '') +
      '</div>';
  }

  var tabs = '', panels = '';
  for (var i = 0; i < fmts.length; i++) {
    var f = fmts[i];
    var active = i === 0 ? ' active' : '';
    tabs += '<button class="ftab' + active + '" onclick="swTab(this,\'' + uid + '\',\'' + f + '\')">' + (FMT_LBL[f]||f) + '</button>';
    var inner = f==='thread' ? bThread(c.thread) : f==='poll' ? bPoll(c.poll) : bSimple(c[f]);
    panels += '<div class="panel' + active + '" data-uid="' + uid + '" data-fmt="' + f + '">' + inner + '</div>';
  }

  return '<div class="news-card" data-title="' + esc((item.original_title||'').toLowerCase()) + '">' +
    imgHtml +
    '<div class="nc-head"><span class="src-tag ' + meta.tcls + '">' + meta.lbl + '</span>' +
    '<div class="nc-src">' + esc(item.source_name||'') + '</div></div>' +
    '<div class="nc-orig"><div class="nc-ttl"><a href="' + esc(item.source_url) + '" target="_blank">' + esc(item.original_title) + '</a></div>' +
    (item.original_summary ? '<button class="tog" onclick="togSum(this)">show summary</button><div class="nc-sum">' + esc(item.original_summary) + '</div>' : '') +
    '</div>' +
    '<div class="nc-tabs">' + tabs + '</div>' +
    '<div class="nc-panels">' + panels + '</div></div>';
}

function buildVideoCard(vid) {
  var tw = vid.tweet_content || {};
  var twHtml = '';
  if (tw.rewrite)  twHtml += '<div><div class="vc-tweet-lbl">Rewrite</div>'  + bSimple(tw.rewrite)  + '</div>';
  if (tw.hot_take) twHtml += '<div><div class="vc-tweet-lbl">Hot Take</div>' + bSimple(tw.hot_take) + '</div>';
  if (!twHtml) twHtml = '<div class="none-msg">No tweet content</div>';
  return '<div class="video-card">' +
    '<div class="vc-thumb"><img src="' + esc(vid.thumbnail) + '" loading="lazy" onerror="imgErr(this)" alt=""/>' +
    '<a class="vc-play" href="' + esc(vid.url) + '" target="_blank"><div class="vc-play-icon">&#9654;</div></a>' +
    (vid.trending ? '<div class="vc-trending">TRENDING</div>' : '') + '</div>' +
    '<div class="vc-body"><div class="vc-channel">&#9654; ' + esc(vid.channel) + '</div>' +
    '<div class="vc-title"><a href="' + esc(vid.url) + '" target="_blank">' + esc(vid.title) + '</a></div>' +
    '<div class="vc-tweets">' + twHtml + '</div></div></div>';
}

function buildHypeCard(h) {
  var col = HCAT_CLR[h.category] || 'var(--c-hype)';
  var catLbl = (h.category||'').replace('_',' ').toUpperCase();
  return '<div class="hype-card"><div class="hype-tw">' + esc(h.tweet) +
    '<button class="cp-btn" data-t="' + esc(h.tweet) + '" onclick="copyText(this.dataset.t,this)">Copy</button></div>' +
    '<div class="hype-based"><b>Based on:</b> ' + esc(h.based_on||'') +
    (h.category ? '<span class="hcat" style="background:' + col + '22;color:' + col + '">' + catLbl + '</span>' : '') +
    '</div></div>';
}

function renderAll() {
  var groups    = {usa:[],world:[],india:[],telugu:[],film:[]};
  var vidGroups = {usa:[],world:[],india:[],telugu:[],film:[]};

  for (var i = 0; i < NEWS.length; i++) {
    var dk = CAT_MAP[NEWS[i].category] || NEWS[i].category;
    if (groups[dk]) groups[dk].push(NEWS[i]);
  }
  for (var j = 0; j < VIDS.length; j++) {
    var vdk = CAT_MAP[VIDS[j].category] || VIDS[j].category;
    if (vidGroups[vdk]) vidGroups[vdk].push(VIDS[j]);
  }

  var allCats = [
    {dk:'usa',    ncId:'nc-usa',    secId:'sec-usa',    meta:CAT_META.usa},
    {dk:'world',  ncId:'nc-world',  secId:'sec-world',  meta:CAT_META.world},
    {dk:'india',  ncId:'nc-india',  secId:'sec-india',  meta:CAT_META.india},
    {dk:'telugu', ncId:'nc-telugu', secId:'sec-telugu', meta:CAT_META.telugu},
    {dk:'film',   ncId:'nc-film',   secId:'sec-film',   meta:CAT_META.film}
  ];

  for (var k = 0; k < allCats.length; k++) {
    var cat    = allCats[k];
    var ncEl   = document.getElementById(cat.ncId);
    var secEl  = document.getElementById(cat.secId);
    var items  = (groups[cat.dk]||[]).filter(function(it) {
      return !searchQ || (it.original_title||'').toLowerCase().indexOf(searchQ) >= 0;
    });
    var vids   = (vidGroups[cat.dk]||[]).filter(function(v) {
      return !searchQ || (v.title||'').toLowerCase().indexOf(searchQ) >= 0;
    });

    if (ncEl) ncEl.textContent = items.length + vids.length;

    if (!secEl) continue;
    var newsHtml = '';
    if (items.length) {
      for (var m = 0; m < items.length; m++) { newsHtml += buildNewsCard(items[m], cat.dk+'_'+m); }
    } else {
      newsHtml = '<div class="empty" style="padding:30px">No items<small>Try different filters</small></div>';
    }
    var vidsHtml = '';
    if (vids.length) {
      vidsHtml = '<div class="subsec-lbl">Videos &mdash; ' + vids.length + '</div>';
      for (var p = 0; p < vids.length; p++) { vidsHtml += buildVideoCard(vids[p]); }
    }
    secEl.innerHTML =
      '<div class="sec-head"><span class="sec-icon">' + cat.meta.icon + '</span>' +
      '<span class="sec-title">' + cat.meta.lbl + '</span>' +
      '<span class="sec-count">' + items.length + ' news &middot; ' + vids.length + ' videos</span></div>' +
      newsHtml + vidsHtml;
  }

  var hEl   = document.getElementById('nc-hype');
  var hSec  = document.getElementById('sec-hype');
  var hItems = HYPE.filter(function(h) {
    return !searchQ || (h.tweet+h.based_on).toLowerCase().indexOf(searchQ) >= 0;
  });
  if (hEl) hEl.textContent = hItems.length;
  if (hSec) {
    var hHtml = '';
    if (hItems.length) {
      for (var q = 0; q < hItems.length; q++) { hHtml += buildHypeCard(hItems[q]); }
    } else {
      hHtml = '<div class="empty">No hypocrisy found<small>(Unlikely)</small></div>';
    }
    hSec.innerHTML =
      '<div class="sec-head"><span class="sec-icon">&#127917;</span>' +
      '<span class="sec-title">Hypocrisy Watch</span>' +
      '<span class="sec-count">' + hItems.length + ' tweets</span></div>' + hHtml;
  }
}

function showCat(cat, btn) {
  activeCat = cat;
  var btns = document.querySelectorAll('.nav-btn');
  for (var i = 0; i < btns.length; i++) btns[i].classList.remove('active');
  btn.classList.add('active');
  var secs = document.querySelectorAll('.cat-sec');
  for (var j = 0; j < secs.length; j++) secs[j].style.display = 'none';
  var sid = cat==='hype' ? 'sec-hype' : cat==='film' ? 'sec-film' : 'sec-'+cat;
  var sec = document.getElementById(sid);
  if (sec) sec.style.display = 'block';
  var pills = document.getElementById('fmt-pills');
  if (pills) pills.style.display = cat==='hype' ? 'none' : 'flex';
}

function setFmt(fmt, btn) {
  activeFmt = fmt;
  var pills = document.querySelectorAll('.fpill');
  for (var i = 0; i < pills.length; i++) pills[i].classList.remove('active');
  btn.classList.add('active');
  renderAll();
}

function doSearch(q) {
  searchQ = q.toLowerCase().trim();
  renderAll();
}

function swTab(btn, uid, fmt) {
  var card = btn.closest('.news-card');
  if (!card) return;
  var tabs   = card.querySelectorAll('.ftab');
  var panels = card.querySelectorAll('.panel');
  for (var i = 0; i < tabs.length;   i++) tabs[i].classList.remove('active');
  for (var j = 0; j < panels.length; j++) panels[j].classList.remove('active');
  btn.classList.add('active');
  var target = card.querySelector('.panel[data-uid="' + uid + '"][data-fmt="' + fmt + '"]');
  if (target) target.classList.add('active');
}

function togSum(btn) {
  var s = btn.nextElementSibling;
  if (!s) return;
  s.style.display = s.style.display === 'block' ? 'none' : 'block';
  btn.textContent = s.style.display === 'block' ? 'hide summary' : 'show summary';
}

renderAll();
</script>
</body>
</html>"""


def generate_viewer(items, hypocrisy, videos, output_path):
    date_str = datetime.now().strftime("%d %b %Y, %I:%M %p")

    html = HTML \
        .replace("__DATE__",       date_str, 2) \
        .replace("__TOTAL_NEWS__", str(len(items))) \
        .replace("__TOTAL_VIDS__", str(len(videos))) \
        .replace("__TOTAL_HYPE__", str(len(hypocrisy))) \
        .replace("__ITEMS_JSON__", _safe_json(items)) \
        .replace("__HYPE_JSON__",  _safe_json(hypocrisy)) \
        .replace("__VIDS_JSON__",  _safe_json(videos))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
