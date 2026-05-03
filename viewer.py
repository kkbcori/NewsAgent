"""
viewer.py - Generates docs/index.html, docs/viewer.js, docs/data.json

Python NEVER embeds JS or JSON into HTML - zero injection issues.
index.html loads viewer.js via <script src> and data via fetch().
"""

import json
import os
from datetime import datetime


CSS = """:root{--bg:#0d0f12;--surface:#13161b;--border:#1f2430;--border-hi:#2e3547;
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
.loading{text-align:center;padding:80px 20px;color:var(--muted);font-family:var(--font-m);font-size:13px}
.spin{display:inline-block;width:18px;height:18px;border:2px solid var(--border-hi);border-top-color:var(--accent);border-radius:50%;animation:spin .6s linear infinite;margin-right:8px;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.sec-head{display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid var(--border)}
.sec-icon{font-size:20px}.sec-title{font-family:var(--font-d);font-size:22px;font-weight:900}
.sec-count{font-family:var(--font-m);font-size:11px;color:var(--muted)}
.sec-usa .sec-title{color:var(--c-usa)}.sec-world .sec-title{color:var(--c-world)}
.sec-india .sec-title{color:var(--c-india)}.sec-telugu .sec-title{color:var(--c-telugu)}
.sec-film .sec-title{color:var(--c-film)}.sec-hype .sec-title{color:var(--c-hype)}
.sec-brain .sec-title{color:var(--c-brain)}.sec-inv .sec-title{color:var(--c-inv)}
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
.t-usa{background:rgba(79,142,247,.15);color:var(--c-usa)}.t-world{background:rgba(62,201,126,.15);color:var(--c-world)}
.t-india{background:rgba(240,96,64,.15);color:var(--c-india)}.t-telugu{background:rgba(192,96,240,.15);color:var(--c-telugu)}
.t-film{background:rgba(240,192,64,.15);color:var(--c-film)}
.nc-src{font-family:var(--font-m);font-size:10px;color:var(--muted);margin-left:auto;white-space:nowrap}
.nc-orig{padding:9px 14px;border-bottom:1px solid var(--border)}
.nc-ttl{font-family:var(--font-d);font-size:14px;font-weight:700;line-height:1.35}
.nc-ttl a{color:var(--text);text-decoration:none}.nc-ttl a:hover{color:var(--accent)}
.nc-sum{color:var(--muted);font-size:12px;margin-top:4px;display:none}
.tog{background:none;border:none;color:var(--muted);font-family:var(--font-m);font-size:10px;cursor:pointer;text-decoration:underline;padding:2px 0}
.tog:hover{color:var(--accent)}
.nc-tabs{display:flex;flex-wrap:wrap;border-bottom:1px solid var(--border);padding:0 14px}
.ftab{background:none;border:none;border-bottom:2px solid transparent;color:var(--muted);font-family:var(--font-m);font-size:10px;padding:6px 9px;cursor:pointer;transition:all .15s;margin-bottom:-1px;white-space:nowrap}
.ftab:hover{color:var(--text)}.ftab.active{color:var(--accent);border-bottom-color:var(--accent)}
.nc-panels{padding:11px 14px 14px}.panel{display:none}.panel.active{display:block}
.tweet-box{background:var(--bg);border:1px solid var(--border-hi);border-radius:8px;padding:10px 80px 10px 12px;font-size:13px;line-height:1.65;position:relative;white-space:pre-wrap;word-break:break-word}
.cp-btn{position:absolute;top:8px;right:8px;background:var(--surface);border:1px solid var(--border-hi);border-radius:6px;color:var(--muted);font-family:var(--font-m);font-size:10px;padding:3px 8px;cursor:pointer;transition:all .15s;white-space:nowrap}
.cp-btn:hover{background:var(--accent);color:#0d0f12}.cp-btn.ok{background:#3ec97e;color:#0d0f12}
.char-c{font-family:var(--font-m);font-size:10px;color:var(--muted);margin-top:3px;text-align:right}
.char-c.warn{color:#e08a30}.char-c.over{color:var(--c-hype)}
.thread-list{display:flex;flex-direction:column;gap:6px}
.thread-tw{background:var(--bg);border:1px solid var(--border-hi);border-radius:8px;padding:8px 46px 8px 12px;position:relative;font-size:13px;line-height:1.65}
.thread-n{font-family:var(--font-m);font-size:10px;color:var(--c-usa);margin-bottom:2px}
.tcp{position:absolute;top:8px;right:8px;background:var(--surface);border:1px solid var(--border-hi);border-radius:6px;color:var(--muted);font-family:var(--font-m);font-size:10px;padding:3px 7px;cursor:pointer;transition:all .15s}
.tcp:hover{background:var(--c-usa);color:#fff}.tcp.ok{background:#3ec97e;color:#0d0f12}
.cp-all{margin-top:8px;background:transparent;border:1px solid var(--c-usa);border-radius:6px;color:var(--c-usa);font-family:var(--font-m);font-size:10px;padding:5px 12px;cursor:pointer;width:100%;transition:all .15s}
.cp-all:hover{background:var(--c-usa);color:#fff}
.poll-tw{background:var(--bg);border:1px solid var(--border-hi);border-radius:8px;padding:10px 46px 10px 12px;position:relative;font-size:13px;line-height:1.65;margin-bottom:8px}
.poll-opts{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.poll-opt{background:var(--bg);border:1px solid var(--border-hi);border-radius:6px;padding:5px 10px;font-family:var(--font-m);font-size:11px;color:var(--c-usa)}
.poll-note{font-family:var(--font-m);font-size:10px;color:var(--muted);margin-top:6px}
.intel-block{border-radius:8px;padding:10px 12px;font-size:13px;line-height:1.65;position:relative;padding-right:80px;margin-bottom:6px}
.intel-label{font-family:var(--font-m);font-size:9px;text-transform:uppercase;letter-spacing:1px;font-weight:600;margin-bottom:5px}
.ib-mainstream{background:rgba(62,201,126,.08);border:1px solid rgba(62,201,126,.2)}
.ib-mainstream .intel-label{color:var(--c-world)}
.ib-alternative{background:rgba(255,140,66,.08);border:1px solid rgba(255,140,66,.25)}
.ib-alternative .intel-label{color:var(--c-alt)}
.ib-cui_bono{background:rgba(255,77,166,.08);border:1px solid rgba(255,77,166,.25)}
.ib-cui_bono .intel-label{color:var(--c-cuibono)}
.ib-deep_read{background:rgba(0,212,255,.08);border:1px solid rgba(0,212,255,.2)}
.ib-deep_read .intel-label{color:var(--c-brain)}
.hype-card{background:var(--surface);border:1px solid rgba(224,82,82,.2);border-left:3px solid var(--c-hype);border-radius:12px;margin-bottom:12px;padding:14px}
.hype-card:hover{border-color:rgba(224,82,82,.4)}
.hype-tw{font-size:14px;line-height:1.7;position:relative;padding-right:76px;white-space:pre-wrap;word-break:break-word}
.hype-based{margin-top:8px;font-family:var(--font-m);font-size:10px;color:var(--muted);border-top:1px solid var(--border);padding-top:7px}
.hype-based b{color:rgba(224,82,82,.7)}
.hcat{display:inline-block;font-family:var(--font-m);font-size:9px;padding:2px 6px;border-radius:4px;margin-right:4px;text-transform:uppercase}
.brain-card{background:var(--surface);border:1px solid rgba(0,212,255,.2);border-left:3px solid var(--c-brain);border-radius:12px;margin-bottom:12px;padding:14px}
.brain-card:hover{border-color:rgba(0,212,255,.4)}
.brain-tw{font-size:14px;line-height:1.7;position:relative;padding-right:76px;white-space:pre-wrap;word-break:break-word}
.brain-type{font-family:var(--font-m);font-size:9px;color:var(--c-brain);text-transform:uppercase;letter-spacing:.8px;margin-bottom:5px}
.brain-angle{margin-top:8px;font-family:var(--font-m);font-size:10px;color:var(--muted);border-top:1px solid var(--border);padding-top:7px;font-style:italic}
.inv-card{background:var(--surface);border:1px solid rgba(160,255,128,.2);border-left:3px solid var(--c-inv);border-radius:12px;margin-bottom:12px;padding:14px}
.inv-card:hover{border-color:rgba(160,255,128,.4)}
.inv-source{font-family:var(--font-m);font-size:9px;color:var(--c-inv);text-transform:uppercase;letter-spacing:.8px;margin-bottom:6px}
.inv-title{font-family:var(--font-d);font-size:14px;font-weight:700;line-height:1.35;margin-bottom:10px}
.inv-title a{color:var(--text);text-decoration:none}.inv-title a:hover{color:var(--c-inv)}
.inv-tweets{display:flex;flex-direction:column;gap:7px}
.inv-tweet-lbl{font-family:var(--font-m);font-size:9px;text-transform:uppercase;color:var(--muted);margin-bottom:3px}
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
.vc-title a{color:var(--text);text-decoration:none}.vc-title a:hover{color:#ff0000}
.vc-tweets{display:flex;flex-direction:column;gap:6px}
.none-msg{color:var(--muted);font-family:var(--font-m);font-size:11px;padding:5px 0}
.empty{text-align:center;padding:50px 20px;color:var(--muted);font-family:var(--font-d);font-size:18px}
.empty small{display:block;font-family:var(--font-b);font-size:12px;margin-top:7px}
.subsec-lbl{font-family:var(--font-m);font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);margin:20px 0 10px;display:flex;align-items:center;gap:10px}
.subsec-lbl::after{content:'';flex:1;height:1px;background:var(--border)}"""


def build_html(date_str, n, v, h, b, inv):
    """Build index.html as a plain string — no f-strings, no JS embedded."""
    lines = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '<meta charset="UTF-8"/>',
        '<meta name="viewport" content="width=device-width,initial-scale=1.0"/>',
        '<title>NewsAgent - ' + date_str + '</title>',
        '<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet"/>',
        '<style>' + CSS + '</style>',
        '</head>',
        '<body>',
        '<header>',
        '  <div class="logo">News<span>Agent</span></div>',
        '  <div class="hdate">' + date_str + '</div>',
        '  <div class="hstats">',
        '    <div class="hstat">&#128240; <b>' + str(n)   + '</b> news</div>',
        '    <div class="hstat">&#128249; <b>' + str(v)   + '</b> videos</div>',
        '    <div class="hstat">&#127917; <b>' + str(h)   + '</b> hypocrisy</div>',
        '    <div class="hstat">&#129504; <b>' + str(b)   + '</b> brain</div>',
        '    <div class="hstat">&#128300; <b>' + str(inv) + '</b> inventions</div>',
        '  </div>',
        '</header>',
        '<div class="shell">',
        '  <nav class="sidenav">',
        '    <div class="nav-lbl">News</div>',
        '    <button class="nav-btn n-usa active" onclick="showCat(\'usa\',this)">&#127482;&#127480; USA <span class="nav-cnt" id="nc-usa">0</span></button>',
        '    <button class="nav-btn n-world" onclick="showCat(\'world\',this)">&#127757; International <span class="nav-cnt" id="nc-world">0</span></button>',
        '    <button class="nav-btn n-india" onclick="showCat(\'india\',this)">&#127470;&#127475; India <span class="nav-cnt" id="nc-india">0</span></button>',
        '    <button class="nav-btn n-tel" onclick="showCat(\'telugu\',this)">&#127897; Telugu <span class="nav-cnt" id="nc-telugu">0</span></button>',
        '    <button class="nav-btn n-film" onclick="showCat(\'film\',this)">&#127909; Telugu Film <span class="nav-cnt" id="nc-film">0</span></button>',
        '    <div class="nav-div"></div>',
        '    <div class="nav-lbl">Intelligence</div>',
        '    <button class="nav-btn n-brain" onclick="showCat(\'brain\',this)">&#129504; Between Lines <span class="nav-cnt" id="nc-brain">0</span></button>',
        '    <button class="nav-btn n-hype" onclick="showCat(\'hype\',this)">&#127917; Hypocrisy <span class="nav-cnt" id="nc-hype">0</span></button>',
        '    <button class="nav-btn n-inv" onclick="showCat(\'inv\',this)">&#128300; Inventions <span class="nav-cnt" id="nc-inv">0</span></button>',
        '  </nav>',
        '  <main class="main">',
        '    <div class="topbar">',
        '      <input class="search-box" placeholder="Search headlines..." oninput="doSearch(this.value)"/>',
        '      <div class="fmt-pills" id="fmt-pills">',
        '        <span class="fmt-lbl">Format:</span>',
        '        <button class="fpill active" onclick="setFmt(\'all\',this)">All</button>',
        '        <button class="fpill" onclick="setFmt(\'rewrite\',this)">Rewrite</button>',
        '        <button class="fpill" onclick="setFmt(\'hot_take\',this)">Hot Take</button>',
        '        <button class="fpill" onclick="setFmt(\'thread\',this)">Thread</button>',
        '        <button class="fpill" onclick="setFmt(\'poll\',this)">Poll</button>',
        '        <button class="fpill" onclick="setFmt(\'deep_read\',this)">Deep</button>',
        '        <button class="fpill" onclick="setFmt(\'mainstream\',this)">Mainstream</button>',
        '        <button class="fpill" onclick="setFmt(\'alternative\',this)">Alt</button>',
        '        <button class="fpill" onclick="setFmt(\'cui_bono\',this)">Cui Bono</button>',
        '      </div>',
        '    </div>',
        '    <div id="main-loading" class="loading"><span class="spin"></span>Loading...</div>',
        '    <div id="sec-usa"    class="cat-sec sec-usa"                    ></div>',
        '    <div id="sec-world"  class="cat-sec sec-world"  style="display:none"></div>',
        '    <div id="sec-india"  class="cat-sec sec-india"  style="display:none"></div>',
        '    <div id="sec-telugu" class="cat-sec sec-telugu" style="display:none"></div>',
        '    <div id="sec-film"   class="cat-sec sec-film"   style="display:none"></div>',
        '    <div id="sec-brain"  class="cat-sec sec-brain"  style="display:none"></div>',
        '    <div id="sec-hype"   class="cat-sec sec-hype"   style="display:none"></div>',
        '    <div id="sec-inv"    class="cat-sec sec-inv"    style="display:none"></div>',
        '  </main>',
        '</div>',
        '<!-- JS loaded from external file - never embedded in HTML -->',
        '<script src="viewer.js"></script>',
        '</body>',
        '</html>',
    ]
    return '\n'.join(lines)


def generate_viewer(
    items, hypocrisy, videos, output_path,
    between_lines=None, inventions=None,
):
    between_lines = between_lines or []
    inventions    = inventions    or []
    date_str      = datetime.now().strftime("%d %b %Y, %I:%M %p")
    output_dir    = os.path.dirname(os.path.abspath(output_path))

    # 1. Write data.json
    data_path = os.path.join(output_dir, "data.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated":     date_str,
            "news":          items,
            "hypocrisy":     hypocrisy,
            "videos":        videos,
            "between_lines": between_lines,
            "inventions":    inventions,
        }, f, ensure_ascii=False)
    print("data.json written: " + str(len(items)) + " news, " +
          str(len(hypocrisy)) + " hype, " + str(len(between_lines)) +
          " brain, " + str(len(inventions)) + " inv")

    # 2. Write viewer.js (read from same directory as this file)
    js_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewer.js")
    js_dst = os.path.join(output_dir, "viewer.js")
    if os.path.exists(js_src):
        with open(js_src, "r", encoding="utf-8") as f:
            js_content = f.read()
        with open(js_dst, "w", encoding="utf-8") as f:
            f.write(js_content)
        print("viewer.js copied (" + str(len(js_content)) + " bytes)")
    else:
        print("WARNING: viewer.js not found at " + js_src)

    # 3. Write index.html (pure shell - no JS, no data)
    html = build_html(
        date_str,
        len(items), len(videos), len(hypocrisy),
        len(between_lines), len(inventions)
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html written (" + str(len(html)) + " bytes)")

    return output_path
