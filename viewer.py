"""
viewer.py - Updated viewer with intelligence sections:
  News cards now show: Rewrite, Hot Take, Thread, Poll,
                       Deep Read, Mainstream, Alternative, Cui Bono
  New sections: Between the Lines, Inventions
"""

import json
from datetime import datetime


def _safe_json(data):
    s = json.dumps(data, ensure_ascii=True)
    s = s.replace("</script>", r"<\/script>")
    s = s.replace("`",         r"\u0060")
    s = s.replace("$",         r"\u0024")
    return s


def generate_viewer(
    items, hypocrisy, videos, output_path,
    between_lines=None, inventions=None,
):
    date_str       = datetime.now().strftime("%d %b %Y, %I:%M %p")
    between_lines  = between_lines  or []
    inventions     = inventions     or []

    parts = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html lang='en'>")
    parts.append("<head>")
    parts.append("<meta charset='UTF-8'/>")
    parts.append("<meta name='viewport' content='width=device-width,initial-scale=1.0'/>")
    parts.append(f"<title>NewsAgent &middot; {date_str}</title>")
    parts.append("<link href='https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap' rel='stylesheet'/>")

    css = """
:root{--bg:#0d0f12;--surface:#13161b;--border:#1f2430;--border-hi:#2e3547;
--text:#e2e6f0;--muted:#5a6070;--accent:#f0c040;
--c-usa:#4f8ef7;--c-world:#3ec97e;--c-india:#f06040;
--c-telugu:#c060f0;--c-film:#f0c040;--c-hype:#e05252;
--c-brain:#00d4ff;--c-inv:#a0ff80;--c-alt:#ff8c42;--c-cuibono:#ff4da6;
--font-d:'Playfair Display',serif;--font-m:'IBM Plex Mono',monospace;
--font-b:'IBM Plex Sans',sans-serif}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:var(--font-b);font-size:14px;line-height:1.6}
header{border-bottom:1px solid var(--border);background:var(--surface);padding:0 24px;display:flex;align-items:center;gap:16px;height:60px;position:sticky;top:0;z-index:200}
.logo{font-family:var(--font-d);font-size:21px;font-weight:900;color:var(--accent)}
.logo span{color:var(--text);font-weight:700}
.hdate{font-family:var(--font-m);font-size:11px;color:var(--muted)}
.hstats{display:flex;gap:14px;margin-left:auto;flex-wrap:wrap}
.hstat{font-family:var(--font-m);font-size:11px;color:var(--muted)}
.hstat b{color:var(--text)}
.shell{display:flex;max-width:1350px;margin:0 auto}
.sidenav{width:210px;min-width:210px;border-right:1px solid var(--border);padding:16px 0;position:sticky;top:60px;height:calc(100vh - 60px);overflow-y:auto;background:var(--surface)}
.nav-lbl{font-family:var(--font-m);font-size:9px;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);padding:0 14px;margin:10px 0 5px}
.nav-btn{display:flex;align-items:center;gap:7px;width:100%;background:none;border:none;border-radius:8px;padding:7px 12px;color:var(--muted);font-family:var(--font-b);font-size:12px;font-weight:500;cursor:pointer;transition:all .15s;text-align:left}
.nav-btn:hover{background:var(--border);color:var(--text)}
.nav-btn.active{font-weight:600}
.nav-btn.active.n-usa{background:rgba(79,142,247,.12);color:var(--c-usa)}
.nav-btn.active.n-world{background:rgba(62,201,126,.12);color:var(--c-world)}
.nav-btn.active.n-india{background:rgba(240,96,64,.12);color:var(--c-india)}
.nav-btn.active.n-tel{background:rgba(192,96,240,.12);color:var(--c-telugu)}
.nav-btn.active.n-film{background:rgba(240,192,64,.12);color:var(--c-film)}
.nav-btn.active.n-hype{background:rgba(224,82,82,.12);color:var(--c-hype)}
.nav-btn.active.n-brain{background:rgba(0,212,255,.12);color:var(--c-brain)}
.nav-btn.active.n-inv{background:rgba(160,255,128,.12);color:var(--c-inv)}
.nav-cnt{margin-left:auto;background:var(--border);border-radius:10px;font-family:var(--font-m);font-size:10px;padding:1px 6px;color:var(--muted)}
.nav-btn.active .nav-cnt{background:rgba(255,255,255,.1);color:currentColor}
.nav-div{height:1px;background:var(--border);margin:8px 12px}
.main{flex:1;padding:20px 22px 80px;min-width:0}
.topbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:18px}
.search-box{background:var(--surface);border:1px solid var(--border-hi);border-radius:8px;color:var(--text);font-family:var(--font-b);font-size:13px;padding:7px 14px;outline:none;width:220px}
.search-box:focus{border-color:var(--accent)}
.search-box::placeholder{color:var(--muted)}
.fmt-pills{display:flex;gap:4px;flex-wrap:wrap;margin-left:auto;align-items:center}
.fmt-lbl{font-family:var(--font-m);font-size:10px;color:var(--muted)}
.fpill{background:transparent;border:1px solid var(--border-hi);color:var(--muted);border-radius:20px;padding:4px 11px;font-family:var(--font-m);font-size:10px;cursor:pointer;transition:all .15s}
.fpill:hover{border-color:var(--accent);color:var(--accent)}
.fpill.active{background:var(--accent);border-color:var(--accent);color:#0d0f12;font-weight:600}
.sec-head{display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid var(--border)}
.sec-icon{font-size:20px}
.sec-title{font-family:var(--font-d);font-size:22px;font-weight:900}
.sec-count{font-family:var(--font-m);font-size:11px;color:var(--muted)}
.sec-usa .sec-title{color:var(--c-usa)}
.sec-world .sec-title{color:var(--c-world)}
.sec-india .sec-title{color:var(--c-india)}
.sec-telugu .sec-title{color:var(--c-telugu)}
.sec-film .sec-title{color:var(--c-film)}
.sec-hype .sec-title{color:var(--c-hype)}
.sec-brain .sec-title{color:var(--c-brain)}
.sec-inv .sec-title{color:var(--c-inv)}
.news-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;margin-bottom:14px;overflow:hidden}
.news-card:hover{border-color:var(--border-hi)}
.nc-img-wrap{position:relative;background:var(--border);overflow:hidden;max-height:200px}
.nc-img-wrap img{width:100%;display:block;object-fit:cover;max-height:200px}
.img-overlay{position:absolute;top:7px;right:7px;display:flex;gap:5px}
.img-btn{background:rgba(13,15,18,.8);border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(6px);border-radius:6px;color:var(--text);font-family:var(--font-m);font-size:10px;padding:3px 9px;cursor:pointer;text-decoration:none;transition:all .15s}
.img-btn:hover{background:rgba(240,192,64,.9);color:#0d0f12}
.yt-badge{position:absolute;bottom:7px;left:7px;background:#ff0000;color:#fff;border-radius:4px;font-family:var(--font-m);font-size:10px;font-weight:600;padding:2px 7px}
.nc-head{display:flex;align-items:flex-start;gap:8px;padding:10px 14px 8px;border-bottom:1px solid var(--border)}
.src-tag{font-family:var(--font-m);font-size:10px;font-weight:500;padding:2px 7px;border-radius:4px;text-transform:uppercase;letter-spacing:.4px}
.t-usa{background:rgba(79,142,247,.15);color:var(--c-usa)}
.t-world{background:rgba(62,201,126,.15);color:var(--c-world)}
.t-india{background:rgba(240,96,64,.15);color:var(--c-india)}
.t-telugu{background:rgba(192,96,240,.15);color:var(--c-telugu)}
.t-film{background:rgba(240,192,64,.15);color:var(--c-film)}
.nc-src{font-family:var(--font-m);font-size:10px;color:var(--muted);margin-left:auto;white-space:nowrap}
.nc-orig{padding:9px 14px;border-bottom:1px solid var(--border)}
.nc-ttl{font-family:var(--font-d);font-size:14px;font-weight:700;line-height:1.35}
.nc-ttl a{color:var(--text);text-decoration:none}
.nc-ttl a:hover{color:var(--accent)}
.nc-sum{color:var(--muted);font-size:12px;margin-top:4px;display:none}
.tog{background:none;border:none;color:var(--muted);font-family:var(--font-m);font-size:10px;cursor:pointer;text-decoration:underline;padding:2px 0}
.tog:hover{color:var(--accent)}
.nc-tabs{display:flex;flex-wrap:wrap;border-bottom:1px solid var(--border);padding:0 14px;gap:0}
.ftab{background:none;border:none;border-bottom:2px solid transparent;color:var(--muted);font-family:var(--font-m);font-size:10px;padding:6px 9px;cursor:pointer;transition:all .15s;margin-bottom:-1px;white-space:nowrap}
.ftab:hover{color:var(--text)}
.ftab.active{color:var(--accent);border-bottom-color:var(--accent)}
.nc-panels{padding:11px 14px 14px}
.panel{display:none}
.panel.active{display:block}
.tweet-box{background:var(--bg);border:1px solid var(--border-hi);border-radius:8px;padding:10px 80px 10px 12px;font-size:13px;line-height:1.65;position:relative;white-space:pre-wrap;word-break:break-word}
.cp-btn{position:absolute;top:8px;right:8px;background:var(--surface);border:1px solid var(--border-hi);border-radius:6px;color:var(--muted);font-family:var(--font-m);font-size:10px;padding:3px 8px;cursor:pointer;transition:all .15s;white-space:nowrap}
.cp-btn:hover{background:var(--accent);color:#0d0f12}
.cp-btn.ok{background:#3ec97e;color:#0d0f12}
.char-c{font-family:var(--font-m);font-size:10px;color:var(--muted);margin-top:3px;text-align:right}
.char-c.warn{color:#e08a30}
.char-c.over{color:var(--c-hype)}
.thread-list{display:flex;flex-direction:column;gap:6px}
.thread-tw{background:var(--bg);border:1px solid var(--border-hi);border-radius:8px;padding:8px 46px 8px 12px;position:relative;font-size:13px;line-height:1.65}
.thread-n{font-family:var(--font-m);font-size:10px;color:var(--c-usa);margin-bottom:2px}
.tcp{position:absolute;top:8px;right:8px;background:var(--surface);border:1px solid var(--border-hi);border-radius:6px;color:var(--muted);font-family:var(--font-m);font-size:10px;padding:3px 7px;cursor:pointer;transition:all .15s}
.tcp:hover{background:var(--c-usa);color:#fff}
.tcp.ok{background:#3ec97e;color:#0d0f12}
.cp-all{margin-top:8px;background:transparent;border:1px solid var(--c-usa);border-radius:6px;color:var(--c-usa);font-family:var(--font-m);font-size:10px;padding:5px 12px;cursor:pointer;width:100%;transition:all .15s}
.cp-all:hover{background:var(--c-usa);color:#fff}
.poll-tw{background:var(--bg);border:1px solid var(--border-hi);border-radius:8px;padding:10px 46px 10px 12px;position:relative;font-size:13px;line-height:1.65;margin-bottom:8px}
.poll-opts{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.poll-opt{background:var(--bg);border:1px solid var(--border-hi);border-radius:6px;padding:5px 10px;font-family:var(--font-m);font-size:11px;color:var(--c-usa)}
.poll-note{font-family:var(--font-m);font-size:10px;color:var(--muted);margin-top:6px}
/* Intelligence panels */
.intel-panel{display:flex;flex-direction:column;gap:8px}
.intel-block{border-radius:8px;padding:10px 12px;font-size:13px;line-height:1.65;position:relative;padding-right:80px}
.intel-label{font-family:var(--font-m);font-size:9px;text-transform:uppercase;letter-spacing:1px;font-weight:600;margin-bottom:5px}
.ib-mainstream{background:rgba(62,201,126,.08);border:1px solid rgba(62,201,126,.2)}
.ib-mainstream .intel-label{color:var(--c-world)}
.ib-alternative{background:rgba(255,140,66,.08);border:1px solid rgba(255,140,66,.25)}
.ib-alternative .intel-label{color:var(--c-alt)}
.ib-cui_bono{background:rgba(255,77,166,.08);border:1px solid rgba(255,77,166,.25)}
.ib-cui_bono .intel-label{color:var(--c-cuibono)}
.ib-deep_read{background:rgba(0,212,255,.08);border:1px solid rgba(0,212,255,.2)}
.ib-deep_read .intel-label{color:var(--c-brain)}
/* Hype cards */
.hype-card{background:var(--surface);border:1px solid rgba(224,82,82,.2);border-left:3px solid var(--c-hype);border-radius:12px;margin-bottom:12px;padding:14px}
.hype-card:hover{border-color:rgba(224,82,82,.4)}
.hype-tw{font-size:14px;line-height:1.7;position:relative;padding-right:76px;white-space:pre-wrap;word-break:break-word}
.hype-based{margin-top:8px;font-family:var(--font-m);font-size:10px;color:var(--muted);border-top:1px solid var(--border);padding-top:7px}
.hype-based b{color:rgba(224,82,82,.7)}
.hcat{display:inline-block;font-family:var(--font-m);font-size:9px;padding:2px 6px;border-radius:4px;margin-right:4px;text-transform:uppercase}
/* Brain cards */
.brain-card{background:var(--surface);border:1px solid rgba(0,212,255,.2);border-left:3px solid var(--c-brain);border-radius:12px;margin-bottom:12px;padding:14px}
.brain-card:hover{border-color:rgba(0,212,255,.4)}
.brain-tw{font-size:14px;line-height:1.7;position:relative;padding-right:76px;white-space:pre-wrap;word-break:break-word}
.brain-type{font-family:var(--font-m);font-size:9px;color:var(--c-brain);text-transform:uppercase;letter-spacing:.8px;margin-bottom:5px}
.brain-angle{margin-top:8px;font-family:var(--font-m);font-size:10px;color:var(--muted);border-top:1px solid var(--border);padding-top:7px;font-style:italic}
/* Invention cards */
.inv-card{background:var(--surface);border:1px solid rgba(160,255,128,.2);border-left:3px solid var(--c-inv);border-radius:12px;margin-bottom:12px;padding:14px}
.inv-card:hover{border-color:rgba(160,255,128,.4)}
.inv-source{font-family:var(--font-m);font-size:9px;color:var(--c-inv);text-transform:uppercase;letter-spacing:.8px;margin-bottom:6px}
.inv-title{font-family:var(--font-d);font-size:14px;font-weight:700;line-height:1.35;margin-bottom:10px}
.inv-title a{color:var(--text);text-decoration:none}
.inv-title a:hover{color:var(--c-inv)}
.inv-tweets{display:flex;flex-direction:column;gap:7px}
.inv-tweet-lbl{font-family:var(--font-m);font-size:9px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);margin-bottom:3px}
/* Video cards */
.video-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;margin-bottom:12px;display:flex;overflow:hidden}
.video-card:hover{border-color:var(--border-hi)}
.vc-thumb{position:relative;width:180px;min-width:180px;background:var(--border)}
.vc-thumb img{width:100%;height:100%;object-fit:cover;display:block}
.vc-play{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.3);opacity:0;transition:opacity .2s;text-decoration:none}
.video-card:hover .vc-play{opacity:1}
.vc-play-icon{width:38px;height:38px;background:#ff0000;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px}
.vc-body{flex:1;padding:12px 14px;min-width:0}
.vc-channel{font-family:var(--font-m);font-size:10px;color:var(--muted);margin-bottom:4px}
.vc-title{font-family:var(--font-d);font-size:13px;font-weight:700;line-height:1.35;margin-bottom:9px}
.vc-title a{color:var(--text);text-decoration:none}
.vc-title a:hover{color:#ff0000}
.vc-tweet-lbl{font-family:var(--font-m);font-size:9px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);margin-bottom:3px}
.vc-tweets{display:flex;flex-direction:column;gap:6px}
.none-msg{color:var(--muted);font-family:var(--font-m);font-size:11px;padding:5px 0}
.empty{text-align:center;padding:50px 20px;color:var(--muted);font-family:var(--font-d);font-size:18px}
.empty small{display:block;font-family:var(--font-b);font-size:12px;margin-top:7px}
.subsec-lbl{font-family:var(--font-m);font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);margin:20px 0 10px;display:flex;align-items:center;gap:10px}
.subsec-lbl::after{content:'';flex:1;height:1px;background:var(--border)}
"""
    parts.append(f"<style>{css}</style>")
    parts.append("</head>")
    parts.append("<body>")

    # Header
    parts.append("<header>")
    parts.append("  <div class='logo'>News<span>Agent</span></div>")
    parts.append(f"  <div class='hdate'>{date_str}</div>")
    parts.append("  <div class='hstats'>")
    parts.append(f"    <div class='hstat'>&#128240; <b>{len(items)}</b> news</div>")
    parts.append(f"    <div class='hstat'>&#128249; <b>{len(videos)}</b> videos</div>")
    parts.append(f"    <div class='hstat'>&#127917; <b>{len(hypocrisy)}</b> hypocrisy</div>")
    parts.append(f"    <div class='hstat'>&#129504; <b>{len(between_lines)}</b> brain</div>")
    parts.append(f"    <div class='hstat'>&#128300; <b>{len(inventions)}</b> inventions</div>")
    parts.append("  </div>")
    parts.append("</header>")

    # Shell
    parts.append("<div class='shell'>")

    # Sidenav
    parts.append("  <nav class='sidenav'>")
    parts.append("    <div class='nav-lbl'>News</div>")
    parts.append("    <button class='nav-btn n-usa active' onclick=\"showCat('usa',this)\">&#127482;&#127480; USA <span class='nav-cnt' id='nc-usa'>0</span></button>")
    parts.append("    <button class='nav-btn n-world' onclick=\"showCat('world',this)\">&#127757; International <span class='nav-cnt' id='nc-world'>0</span></button>")
    parts.append("    <button class='nav-btn n-india' onclick=\"showCat('india',this)\">&#127470;&#127475; India <span class='nav-cnt' id='nc-india'>0</span></button>")
    parts.append("    <button class='nav-btn n-tel' onclick=\"showCat('telugu',this)\">&#127897; Telugu <span class='nav-cnt' id='nc-telugu'>0</span></button>")
    parts.append("    <button class='nav-btn n-film' onclick=\"showCat('film',this)\">&#127909; Telugu Film <span class='nav-cnt' id='nc-film'>0</span></button>")
    parts.append("    <div class='nav-div'></div>")
    parts.append("    <div class='nav-lbl'>Intelligence</div>")
    parts.append("    <button class='nav-btn n-brain' onclick=\"showCat('brain',this)\">&#129504; Between Lines <span class='nav-cnt' id='nc-brain'>0</span></button>")
    parts.append("    <button class='nav-btn n-hype' onclick=\"showCat('hype',this)\">&#127917; Hypocrisy <span class='nav-cnt' id='nc-hype'>0</span></button>")
    parts.append("    <button class='nav-btn n-inv' onclick=\"showCat('inv',this)\">&#128300; Inventions <span class='nav-cnt' id='nc-inv'>0</span></button>")
    parts.append("  </nav>")

    # Main
    parts.append("  <main class='main'>")
    parts.append("    <div class='topbar'>")
    parts.append("      <input class='search-box' placeholder='Search...' oninput='doSearch(this.value)'/>")
    parts.append("      <div class='fmt-pills' id='fmt-pills'>")
    parts.append("        <span class='fmt-lbl'>Format:</span>")
    for fmt, label in [
        ("all","All"), ("rewrite","✍️ Rewrite"), ("hot_take","🔥 Hot Take"),
        ("thread","🧵 Thread"), ("poll","📊 Poll"),
        ("deep_read","🧠 Deep"), ("mainstream","🌐 Mainstream"),
        ("alternative","🕵️ Alt"), ("cui_bono","💰 Cui Bono"),
    ]:
        active = " active" if fmt == "all" else ""
        parts.append(f"        <button class='fpill{active}' onclick=\"setFmt('{fmt}',this)\">{label}</button>")
    parts.append("      </div>")
    parts.append("    </div>")
    for sec in ["usa","world","india","telugu","film","brain","hype","inv"]:
        display = "" if sec == "usa" else " style='display:none'"
        parts.append(f"    <div id='sec-{sec}' class='cat-sec sec-{sec}'{display}></div>")
    parts.append("  </main>")
    parts.append("</div>")

    # Data
    # Base64 encode all data — 100% injection-proof regardless of content
    import base64
    def b64(data):
        return base64.b64encode(
            json.dumps(data, ensure_ascii=True).encode()
        ).decode()

    parts.append(f"<script id='d-news'  type='text/plain'>{b64(items)}</script>")
    parts.append(f"<script id='d-hype'  type='text/plain'>{b64(hypocrisy)}</script>")
    parts.append(f"<script id='d-vids'  type='text/plain'>{b64(videos)}</script>")
    parts.append(f"<script id='d-brain' type='text/plain'>{b64(between_lines)}</script>")
    parts.append(f"<script id='d-inv'   type='text/plain'>{b64(inventions)}</script>")

    js = """
function b64decode(id) {
  try {
    var b64 = document.getElementById(id).textContent.trim();
    return JSON.parse(atob(b64));
  } catch(e) {
    console.error('Failed to decode ' + id + ':', e);
    return [];
  }
}
var NEWS  = b64decode('d-news');
var HYPE  = b64decode('d-hype');
var VIDS  = b64decode('d-vids');
var BRAIN = b64decode('d-brain');
var INV   = b64decode('d-inv');

var activeCat='usa', activeFmt='all', searchQ='';

var CAT_MAP={usa:'usa',world:'world',india:'india',telugu:'telugu',telugu_film:'film'};
var CAT_META={
  usa:  {lbl:'USA',          icon:'&#127482;&#127480;',tcls:'t-usa'},
  world:{lbl:'International',icon:'&#127757;',         tcls:'t-world'},
  india:{lbl:'India',        icon:'&#127470;&#127475;',tcls:'t-india'},
  telugu:{lbl:'Telugu',      icon:'&#127897;',         tcls:'t-telugu'},
  film: {lbl:'Telugu Film',  icon:'&#127909;',         tcls:'t-film'},
};
var HCAT_CLR={usa:'var(--c-usa)',world:'var(--c-world)',india:'var(--c-india)',telugu:'var(--c-telugu)',telugu_film:'var(--c-film)'};
var FMT_LBL={rewrite:'Rewrite',hot_take:'Hot Take',thread:'Thread',poll:'Poll',
             deep_read:'Deep Read',mainstream:'Mainstream',alternative:'Alternative',cui_bono:'Cui Bono'};
var BRAIN_TYPE_ICON={connection:'&#128279;',timing:'&#8987;',silence:'&#128263;',contradiction:'&#9888;',pattern:'&#128200;'};

function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function cp(text,btn){navigator.clipboard.writeText(text).then(function(){var o=btn.textContent;btn.textContent='Copied!';btn.classList.add('ok');setTimeout(function(){btn.textContent=o;btn.classList.remove('ok');},1800);});}
function imgErr(img){var w=img.closest('.nc-img-wrap')||img.closest('.vc-thumb');if(w)w.style.display='none';}

function bSimple(text){
  if(!text)return'<div class="none-msg">Not generated</div>';
  var n=text.length,cls=n>280?'over':n>240?'warn':'';
  return'<div class="tweet-box">'+esc(text)+'<button class="cp-btn" data-t="'+esc(text)+'" onclick="cp(this.dataset.t,this)">Copy</button></div><div class="char-c '+cls+'">'+n+' / 280</div>';
}
function bThread(tweets){
  if(!tweets||!tweets.length)return'<div class="none-msg">Not generated</div>';
  var n=tweets.length,rows='',all='';
  for(var i=0;i<tweets.length;i++){
    rows+='<div class="thread-tw"><div class="thread-n">'+(i+1)+'/'+n+'</div>'+esc(tweets[i])+'<button class="tcp" data-t="'+esc(tweets[i])+'" onclick="cp(this.dataset.t,this)">Copy</button></div>';
    all+=(i+1)+'/'+n+' '+tweets[i]+'\n\n';
  }
  return'<div class="thread-list">'+rows+'</div><button class="cp-all" data-t="'+esc(all)+'" onclick="cp(this.dataset.t,this)">Copy Entire Thread</button>';
}
function bPoll(d){
  if(!d)return'<div class="none-msg">Not generated</div>';
  var opts='';for(var i=0;i<(d.options||[]).length;i++)opts+='<div class="poll-opt">'+esc(d.options[i])+'</div>';
  return'<div class="poll-tw">'+esc(d.tweet)+'<button class="cp-btn" data-t="'+esc(d.tweet)+'" onclick="cp(this.dataset.t,this)">Copy</button></div><div class="poll-opts">'+opts+'</div><div class="poll-note">Create poll manually on X</div>';
}
function bIntel(text,type,label){
  if(!text)return'';
  return'<div class="intel-block ib-'+type+'"><div class="intel-label">'+label+'</div>'+esc(text)+'<button class="cp-btn" data-t="'+esc(text)+'" onclick="cp(this.dataset.t,this)">Copy</button></div>';
}

function buildNewsCard(item,uid){
  var dk=CAT_MAP[item.category]||item.category;
  var meta=CAT_META[dk]||CAT_META.usa;
  var c=item.content||{};
  var allFmts=['rewrite','hot_take','thread','poll','deep_read','mainstream','alternative','cui_bono'];
  var fmts=activeFmt==='all'?allFmts:[activeFmt];

  var imgHtml='';
  if(item.image_url){
    imgHtml='<div class="nc-img-wrap"><img src="'+esc(item.image_url)+'" loading="lazy" onerror="imgErr(this)" alt=""/><div class="img-overlay"><a class="img-btn" href="'+esc(item.image_url)+'" target="_blank">Image</a>'+(item.youtube_id?'<a class="img-btn" href="https://www.youtube.com/watch?v='+esc(item.youtube_id)+'" target="_blank">Video</a>':'')+'</div>'+(item.youtube_id?'<div class="yt-badge">YT</div>':'')+'</div>';
  }

  var tabs='',panels='';
  for(var i=0;i<fmts.length;i++){
    var f=fmts[i],act=i===0?' active':'';
    tabs+='<button class="ftab'+act+'" onclick="swTab(this,\''+uid+'\',\''+f+'\')">'+( FMT_LBL[f]||f)+'</button>';
    var inner;
    if(f==='thread') inner=bThread(c.thread);
    else if(f==='poll') inner=bPoll(c.poll);
    else if(f==='mainstream'||f==='alternative'||f==='cui_bono'){
      var lbl={mainstream:'🌐 Official Narrative',alternative:'🕵️ Alternative Angle',cui_bono:'💰 Cui Bono — Who Benefits?'};
      inner=bIntel(c[f],f,lbl[f]);
    }
    else if(f==='deep_read') inner=bIntel(c.deep_read,'deep_read','🧠 Reading Between the Lines');
    else inner=bSimple(c[f]);
    panels+='<div class="panel'+act+'" data-uid="'+uid+'" data-fmt="'+f+'">'+inner+'</div>';
  }

  return'<div class="news-card" data-title="'+esc((item.original_title||'').toLowerCase())+'">'+
    imgHtml+
    '<div class="nc-head"><span class="src-tag '+meta.tcls+'">'+meta.lbl+'</span><div class="nc-src">'+esc(item.source_name||'')+'</div></div>'+
    '<div class="nc-orig"><div class="nc-ttl"><a href="'+esc(item.source_url)+'" target="_blank">'+esc(item.original_title)+'</a></div>'+
    (item.original_summary?'<button class="tog" onclick="togSum(this)">show summary</button><div class="nc-sum">'+esc(item.original_summary)+'</div>':'')+
    '</div>'+
    '<div class="nc-tabs">'+tabs+'</div>'+
    '<div class="nc-panels">'+panels+'</div></div>';
}

function buildHypeCard(h){
  var col=HCAT_CLR[h.category]||'var(--c-hype)';
  var catLbl=(h.category||'').replace('_',' ').toUpperCase();
  return'<div class="hype-card"><div class="hype-tw">'+esc(h.tweet)+'<button class="cp-btn" data-t="'+esc(h.tweet)+'" onclick="cp(this.dataset.t,this)">Copy</button></div><div class="hype-based"><b>Based on:</b> '+esc(h.based_on||'')+(h.category?'<span class="hcat" style="background:'+col+'22;color:'+col+'">'+catLbl+'</span>':'')+'</div></div>';
}

function buildBrainCard(b){
  var icon=BRAIN_TYPE_ICON[b.type]||'&#129504;';
  var typeLabel=(b.type||'').replace('_',' ').toUpperCase();
  return'<div class="brain-card"><div class="brain-type">'+icon+' '+typeLabel+'</div><div class="brain-tw">'+esc(b.tweet)+'<button class="cp-btn" data-t="'+esc(b.tweet)+'" onclick="cp(this.dataset.t,this)">Copy</button></div>'+(b.angle?'<div class="brain-angle">'+esc(b.angle)+'</div>':'')+'</div>';
}

function buildInvCard(inv){
  var tw=inv.tweet||{};
  var twHtml='';
  if(tw.rewrite) twHtml+='<div><div class="inv-tweet-lbl">&#128300; Plain Explanation</div>'+bSimple(tw.rewrite)+'</div>';
  if(tw.hot_take) twHtml+='<div><div class="inv-tweet-lbl">&#129327; Mind Blown</div>'+bSimple(tw.hot_take)+'</div>';
  if(!twHtml) twHtml='<div class="none-msg">Tweet not generated</div>';
  return'<div class="inv-card"><div class="inv-source">'+esc(inv.source||'')+'</div><div class="inv-title"><a href="'+esc(inv.link||'#')+'" target="_blank">'+esc(inv.title)+'</a></div><div class="inv-tweets">'+twHtml+'</div></div>';
}

function buildVideoCard(vid){
  var tw=vid.tweet_content||{},twHtml='';
  if(tw.rewrite) twHtml+='<div><div class="vc-tweet-lbl">Rewrite</div>'+bSimple(tw.rewrite)+'</div>';
  if(tw.hot_take) twHtml+='<div><div class="vc-tweet-lbl">Hot Take</div>'+bSimple(tw.hot_take)+'</div>';
  if(!twHtml) twHtml='<div class="none-msg">No tweet content</div>';
  return'<div class="video-card"><div class="vc-thumb"><img src="'+esc(vid.thumbnail)+'" loading="lazy" onerror="imgErr(this)" alt=""/><a class="vc-play" href="'+esc(vid.url)+'" target="_blank"><div class="vc-play-icon">&#9654;</div></a></div><div class="vc-body"><div class="vc-channel">&#9654; '+esc(vid.channel)+'</div><div class="vc-title"><a href="'+esc(vid.url)+'" target="_blank">'+esc(vid.title)+'</a></div><div class="vc-tweets">'+twHtml+'</div></div></div>';
}

function renderAll(){
  var groups={usa:[],world:[],india:[],telugu:[],film:[]};
  var vidGroups={usa:[],world:[],india:[],telugu:[],film:[]};
  for(var i=0;i<NEWS.length;i++){var dk=CAT_MAP[NEWS[i].category]||NEWS[i].category;if(groups[dk])groups[dk].push(NEWS[i]);}
  for(var j=0;j<VIDS.length;j++){var vdk=CAT_MAP[VIDS[j].category]||VIDS[j].category;if(vidGroups[vdk])vidGroups[vdk].push(VIDS[j]);}

  var allCats=[
    {dk:'usa',ncId:'nc-usa',secId:'sec-usa',meta:CAT_META.usa,cls:'sec-usa'},
    {dk:'world',ncId:'nc-world',secId:'sec-world',meta:CAT_META.world,cls:'sec-world'},
    {dk:'india',ncId:'nc-india',secId:'sec-india',meta:CAT_META.india,cls:'sec-india'},
    {dk:'telugu',ncId:'nc-telugu',secId:'sec-telugu',meta:CAT_META.telugu,cls:'sec-telugu'},
    {dk:'film',ncId:'nc-film',secId:'sec-film',meta:CAT_META.film,cls:'sec-film'}
  ];

  for(var k=0;k<allCats.length;k++){
    var cat=allCats[k];
    var ncEl=document.getElementById(cat.ncId);
    var secEl=document.getElementById(cat.secId);
    var its=(groups[cat.dk]||[]).filter(function(it){return !searchQ||(it.original_title||'').toLowerCase().indexOf(searchQ)>=0;});
    var vs=(vidGroups[cat.dk]||[]).filter(function(v){return !searchQ||(v.title||'').toLowerCase().indexOf(searchQ)>=0;});
    if(ncEl) ncEl.textContent=its.length+vs.length;
    if(!secEl) continue;
    var nh='';
    if(its.length){for(var m=0;m<its.length;m++) nh+=buildNewsCard(its[m],cat.dk+'_'+m);}
    else nh='<div class="empty" style="padding:30px">No items<small>Try different filters</small></div>';
    var vh='';
    if(vs.length){vh='<div class="subsec-lbl">Videos &mdash; '+vs.length+'</div>';for(var p=0;p<vs.length;p++) vh+=buildVideoCard(vs[p]);}
    secEl.innerHTML='<div class="sec-head"><span class="sec-icon">'+cat.meta.icon+'</span><span class="sec-title">'+cat.meta.lbl+'</span><span class="sec-count">'+its.length+' news &middot; '+vs.length+' videos</span></div>'+nh+vh;
  }

  // Brain section
  var brainEl=document.getElementById('nc-brain');
  var brainSec=document.getElementById('sec-brain');
  var brainItems=BRAIN.filter(function(b){return !searchQ||(b.tweet||'').toLowerCase().indexOf(searchQ)>=0;});
  if(brainEl) brainEl.textContent=brainItems.length;
  if(brainSec){
    var bh='';
    if(brainItems.length){for(var bi=0;bi<brainItems.length;bi++) bh+=buildBrainCard(brainItems[bi]);}
    else bh='<div class="empty">No intelligence findings<small>Run without --skip-brain</small></div>';
    brainSec.innerHTML='<div class="sec-head"><span class="sec-icon">&#129504;</span><span class="sec-title">Between the Lines</span><span class="sec-count">'+brainItems.length+' observations</span></div>'+bh;
  }

  // Hypocrisy section
  var hEl=document.getElementById('nc-hype');
  var hSec=document.getElementById('sec-hype');
  var hItems=HYPE.filter(function(h){return !searchQ||(h.tweet+h.based_on).toLowerCase().indexOf(searchQ)>=0;});
  if(hEl) hEl.textContent=hItems.length;
  if(hSec){
    var hh='';
    if(hItems.length){for(var hi=0;hi<hItems.length;hi++) hh+=buildHypeCard(hItems[hi]);}
    else hh='<div class="empty">No hypocrisy found<small>(Unlikely)</small></div>';
    hSec.innerHTML='<div class="sec-head"><span class="sec-icon">&#127917;</span><span class="sec-title">Hypocrisy Watch</span><span class="sec-count">'+hItems.length+' tweets</span></div>'+hh;
  }

  // Inventions section
  var invEl=document.getElementById('nc-inv');
  var invSec=document.getElementById('sec-inv');
  var invItems=INV.filter(function(v){return !searchQ||(v.title||'').toLowerCase().indexOf(searchQ)>=0;});
  if(invEl) invEl.textContent=invItems.length;
  if(invSec){
    var ivh='';
    if(invItems.length){for(var ii=0;ii<invItems.length;ii++) ivh+=buildInvCard(invItems[ii]);}
    else ivh='<div class="empty">No inventions found<small>Run without --skip-inventions</small></div>';
    invSec.innerHTML='<div class="sec-head"><span class="sec-icon">&#128300;</span><span class="sec-title">Inventions &amp; Breakthroughs</span><span class="sec-count">'+invItems.length+' discoveries</span></div>'+ivh;
  }
}

function showCat(cat,btn){
  activeCat=cat;
  var bs=document.querySelectorAll('.nav-btn');for(var i=0;i<bs.length;i++) bs[i].classList.remove('active');
  btn.classList.add('active');
  var ss=document.querySelectorAll('.cat-sec');for(var j=0;j<ss.length;j++) ss[j].style.display='none';
  var sec=document.getElementById('sec-'+cat);if(sec) sec.style.display='block';
  var pills=document.getElementById('fmt-pills');
  if(pills) pills.style.display=(cat==='brain'||cat==='hype'||cat==='inv')?'none':'flex';
}

function setFmt(fmt,btn){
  activeFmt=fmt;
  var ps=document.querySelectorAll('.fpill');for(var i=0;i<ps.length;i++) ps[i].classList.remove('active');
  btn.classList.add('active');
  renderAll();
}

function doSearch(q){searchQ=q.toLowerCase().trim();renderAll();}

function swTab(btn,uid,fmt){
  var card=btn.closest('.news-card');if(!card)return;
  var ts=card.querySelectorAll('.ftab');for(var i=0;i<ts.length;i++) ts[i].classList.remove('active');
  var ps=card.querySelectorAll('.panel');for(var j=0;j<ps.length;j++) ps[j].classList.remove('active');
  btn.classList.add('active');
  var t=card.querySelector('.panel[data-uid="'+uid+'"][data-fmt="'+fmt+'"]');if(t) t.classList.add('active');
}

function togSum(btn){
  var s=btn.nextElementSibling;if(!s)return;
  s.style.display=s.style.display==='block'?'none':'block';
  btn.textContent=s.style.display==='block'?'hide summary':'show summary';
}

renderAll();
"""
    parts.append(f"<script>{js}</script>")
    parts.append("</body>")
    parts.append("</html>")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return output_path
