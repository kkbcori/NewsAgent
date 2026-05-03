/* NewsAgent viewer.js - loaded via <script src="viewer.js"> */

var NEWS=[], HYPE=[], VIDS=[], BRAIN=[], INV=[];
var activeCat='usa', activeFmt='all', searchQ='';

var CAT_MAP={usa:'usa',world:'world',india:'india',telugu:'telugu',telugu_film:'film'};
var CAT_META={
  usa:  {lbl:'USA',           icon:'🇺🇸', tcls:'t-usa'},
  world:{lbl:'International', icon:'🌍',  tcls:'t-world'},
  india:{lbl:'India',         icon:'🇮🇳', tcls:'t-india'},
  telugu:{lbl:'Telugu',       icon:'🎙️', tcls:'t-telugu'},
  film: {lbl:'Telugu Film',   icon:'🎬',  tcls:'t-film'},
  hype: {lbl:'Hypocrisy',     icon:'🎭',  tcls:''},
  brain:{lbl:'Between Lines', icon:'🧠',  tcls:''},
  inv:  {lbl:'Inventions',    icon:'🔬',  tcls:''}
};
var HCAT_CLR={
  usa:'var(--c-usa)', world:'var(--c-world)', india:'var(--c-india)',
  telugu:'var(--c-telugu)', telugu_film:'var(--c-film)'
};
var FMT_LBL={
  rewrite:'Rewrite', hot_take:'Hot Take', thread:'Thread', poll:'Poll',
  deep_read:'Deep Read', mainstream:'Mainstream',
  alternative:'Alternative', cui_bono:'Cui Bono'
};

function esc(s) {
  return String(s||'')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function cp(text, btn) {
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
    '<button class="cp-btn" data-t="' + esc(text) +
    '" onclick="cp(this.dataset.t,this)">Copy</button></div>' +
    '<div class="char-c ' + cls + '">' + n + '/280</div>';
}

function bThread(tweets) {
  if (!tweets || !tweets.length) return '<div class="none-msg">Not generated</div>';
  var n = tweets.length, rows = '', all = '';
  for (var i = 0; i < tweets.length; i++) {
    rows += '<div class="thread-tw"><div class="thread-n">' + (i+1) + '/' + n + '</div>' +
      esc(tweets[i]) +
      '<button class="tcp" data-t="' + esc(tweets[i]) +
      '" onclick="cp(this.dataset.t,this)">Copy</button></div>';
    all += (i+1) + '/' + n + ' ' + tweets[i] + '\n\n';
  }
  return '<div class="thread-list">' + rows + '</div>' +
    '<button class="cp-all" data-t="' + esc(all) +
    '" onclick="cp(this.dataset.t,this)">Copy Thread</button>';
}

function bPoll(d) {
  if (!d) return '<div class="none-msg">Not generated</div>';
  var opts = '';
  for (var i = 0; i < (d.options||[]).length; i++) {
    opts += '<div class="poll-opt">' + esc(d.options[i]) + '</div>';
  }
  return '<div class="poll-tw">' + esc(d.tweet) +
    '<button class="cp-btn" data-t="' + esc(d.tweet) +
    '" onclick="cp(this.dataset.t,this)">Copy</button></div>' +
    '<div class="poll-opts">' + opts + '</div>' +
    '<div class="poll-note">Create poll on X manually</div>';
}

function bIntel(text, type, label) {
  if (!text) return '';
  return '<div class="intel-block ib-' + type + '">' +
    '<div class="intel-label">' + label + '</div>' + esc(text) +
    '<button class="cp-btn" data-t="' + esc(text) +
    '" onclick="cp(this.dataset.t,this)">Copy</button></div>';
}

function buildCard(item, uid) {
  var dk   = CAT_MAP[item.category] || item.category;
  var meta = CAT_META[dk] || CAT_META.usa;
  var c    = item.content || {};
  var allF = ['rewrite','hot_take','thread','poll','deep_read','mainstream','alternative','cui_bono'];
  var fmts = activeFmt === 'all' ? allF : [activeFmt];

  var imgHtml = '';
  if (item.image_url) {
    imgHtml = '<div class="nc-img-wrap">' +
      '<img src="' + esc(item.image_url) + '" loading="lazy" onerror="imgErr(this)" alt=""/>' +
      '<div class="img-overlay">' +
      '<a class="img-btn" href="' + esc(item.image_url) + '" target="_blank">Image</a>' +
      (item.youtube_id
        ? '<a class="img-btn" href="https://www.youtube.com/watch?v=' +
          esc(item.youtube_id) + '" target="_blank">Video</a>' : '') +
      '</div>' +
      (item.youtube_id ? '<div class="yt-badge">YT</div>' : '') +
      '</div>';
  }

  var tabs = '', panels = '';
  for (var i = 0; i < fmts.length; i++) {
    var f   = fmts[i];
    var act = i === 0 ? ' active' : '';
    tabs += '<button class="ftab' + act + '" data-uid="' + uid +
      '" data-fmt="' + f + '" onclick="swTab(this)">' + (FMT_LBL[f]||f) + '</button>';

    var inner;
    if      (f === 'thread')      inner = bThread(c.thread);
    else if (f === 'poll')        inner = bPoll(c.poll);
    else if (f === 'mainstream')  inner = bIntel(c.mainstream,  'mainstream',  'Official Narrative');
    else if (f === 'alternative') inner = bIntel(c.alternative, 'alternative', 'Alternative Angle');
    else if (f === 'cui_bono')    inner = bIntel(c.cui_bono,    'cui_bono',    'Cui Bono');
    else if (f === 'deep_read')   inner = bIntel(c.deep_read,   'deep_read',   'Between the Lines');
    else                          inner = bSimple(c[f]);

    panels += '<div class="panel' + act + '" data-uid="' + uid +
      '" data-fmt="' + f + '">' + inner + '</div>';
  }

  return '<div class="news-card" data-title="' + esc((item.original_title||'').toLowerCase()) + '">' +
    imgHtml +
    '<div class="nc-head">' +
      '<span class="src-tag ' + meta.tcls + '">' + meta.lbl + '</span>' +
      '<div class="nc-src">' + esc(item.source_name||'') + '</div>' +
    '</div>' +
    '<div class="nc-orig">' +
      '<div class="nc-ttl"><a href="' + esc(item.source_url) + '" target="_blank">' +
        esc(item.original_title) + '</a></div>' +
      (item.original_summary
        ? '<button class="tog" onclick="togSum(this)">show summary</button>' +
          '<div class="nc-sum">' + esc(item.original_summary) + '</div>' : '') +
    '</div>' +
    '<div class="nc-tabs">' + tabs + '</div>' +
    '<div class="nc-panels">' + panels + '</div>' +
    '</div>';
}

function buildHypeCard(h) {
  var col    = HCAT_CLR[h.category] || 'var(--c-hype)';
  var catLbl = (h.category||'').replace('_',' ').toUpperCase();
  return '<div class="hype-card">' +
    '<div class="hype-tw">' + esc(h.tweet) +
      '<button class="cp-btn" data-t="' + esc(h.tweet) +
      '" onclick="cp(this.dataset.t,this)">Copy</button>' +
    '</div>' +
    '<div class="hype-based"><b>Based on:</b> ' + esc(h.based_on||'') +
      (h.category ? '<span class="hcat" style="background:' + col + '22;color:' + col + '">' +
        catLbl + '</span>' : '') +
    '</div></div>';
}

function buildBrainCard(b) {
  var icons = {connection:'🔗',timing:'⏳',silence:'🔇',contradiction:'⚠️',pattern:'📈'};
  var icon  = icons[b.type] || '🧠';
  return '<div class="brain-card">' +
    '<div class="brain-type">' + icon + ' ' + (b.type||'').replace('_',' ').toUpperCase() + '</div>' +
    '<div class="brain-tw">' + esc(b.tweet) +
      '<button class="cp-btn" data-t="' + esc(b.tweet) +
      '" onclick="cp(this.dataset.t,this)">Copy</button>' +
    '</div>' +
    (b.angle ? '<div class="brain-angle">' + esc(b.angle) + '</div>' : '') +
    '</div>';
}

function buildInvCard(inv) {
  var tw = inv.tweet || {};
  var th = '';
  if (tw.rewrite)  th += '<div><div class="inv-tweet-lbl">Plain Explanation</div>' + bSimple(tw.rewrite)  + '</div>';
  if (tw.hot_take) th += '<div><div class="inv-tweet-lbl">Mind Blown</div>'        + bSimple(tw.hot_take) + '</div>';
  if (!th) th = '<div class="none-msg">Tweet not generated</div>';
  return '<div class="inv-card">' +
    '<div class="inv-source">' + esc(inv.source||'') + '</div>' +
    '<div class="inv-title"><a href="' + esc(inv.link||'#') + '" target="_blank">' +
      esc(inv.title) + '</a></div>' +
    '<div class="inv-tweets">' + th + '</div>' +
    '</div>';
}

function buildVideoCard(vid) {
  var tw = vid.tweet_content || {};
  var th = '';
  if (tw.rewrite)  th += '<div><div class="vc-tweet-lbl">Rewrite</div>'  + bSimple(tw.rewrite)  + '</div>';
  if (tw.hot_take) th += '<div><div class="vc-tweet-lbl">Hot Take</div>' + bSimple(tw.hot_take) + '</div>';
  if (!th) th = '<div class="none-msg">No tweet</div>';
  return '<div class="video-card">' +
    '<div class="vc-thumb">' +
      '<img src="' + esc(vid.thumbnail) + '" loading="lazy" onerror="imgErr(this)" alt=""/>' +
      '<a class="vc-play" href="' + esc(vid.url) + '" target="_blank">' +
        '<div class="vc-play-icon">&#9654;</div>' +
      '</a>' +
    '</div>' +
    '<div class="vc-body">' +
      '<div class="vc-channel">&#9654; ' + esc(vid.channel) + '</div>' +
      '<div class="vc-title"><a href="' + esc(vid.url) + '" target="_blank">' +
        esc(vid.title) + '</a></div>' +
      '<div class="vc-tweets">' + th + '</div>' +
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

  var cats = [
    {dk:'usa',    ncId:'nc-usa',    secId:'sec-usa',    meta:CAT_META.usa},
    {dk:'world',  ncId:'nc-world',  secId:'sec-world',  meta:CAT_META.world},
    {dk:'india',  ncId:'nc-india',  secId:'sec-india',  meta:CAT_META.india},
    {dk:'telugu', ncId:'nc-telugu', secId:'sec-telugu', meta:CAT_META.telugu},
    {dk:'film',   ncId:'nc-film',   secId:'sec-film',   meta:CAT_META.film}
  ];

  for (var k = 0; k < cats.length; k++) {
    var cat   = cats[k];
    var ncEl  = document.getElementById(cat.ncId);
    var secEl = document.getElementById(cat.secId);
    var its   = (groups[cat.dk]||[]).filter(function(it) {
      return !searchQ || (it.original_title||'').toLowerCase().indexOf(searchQ) >= 0;
    });
    var vs = (vidGroups[cat.dk]||[]).filter(function(v) {
      return !searchQ || (v.title||'').toLowerCase().indexOf(searchQ) >= 0;
    });

    if (ncEl) ncEl.textContent = its.length + vs.length;
    if (!secEl) continue;

    var nh = '';
    if (its.length) {
      for (var m = 0; m < its.length; m++) nh += buildCard(its[m], cat.dk + '_' + m);
    } else {
      nh = '<div class="empty" style="padding:30px">No items<small>Try different filters</small></div>';
    }
    var vh = '';
    if (vs.length) {
      vh = '<div class="subsec-lbl">Videos &mdash; ' + vs.length + '</div>';
      for (var p = 0; p < vs.length; p++) vh += buildVideoCard(vs[p]);
    }

    secEl.innerHTML =
      '<div class="sec-head">' +
        '<span class="sec-icon">' + cat.meta.icon + '</span>' +
        '<span class="sec-title">' + cat.meta.lbl + '</span>' +
        '<span class="sec-count">' + its.length + ' news &middot; ' + vs.length + ' videos</span>' +
      '</div>' + nh + vh;
  }

  // Brain
  var brainEl  = document.getElementById('nc-brain');
  var brainSec = document.getElementById('sec-brain');
  var bItems   = BRAIN.filter(function(b) {
    return !searchQ || (b.tweet||'').toLowerCase().indexOf(searchQ) >= 0;
  });
  if (brainEl) brainEl.textContent = bItems.length;
  if (brainSec) {
    var bh = bItems.length
      ? bItems.map(buildBrainCard).join('')
      : '<div class="empty">No observations</div>';
    brainSec.innerHTML =
      '<div class="sec-head"><span class="sec-icon">🧠</span>' +
      '<span class="sec-title">Between the Lines</span>' +
      '<span class="sec-count">' + bItems.length + ' observations</span></div>' + bh;
  }

  // Hypocrisy
  var hEl    = document.getElementById('nc-hype');
  var hSec   = document.getElementById('sec-hype');
  var hItems = HYPE.filter(function(h) {
    return !searchQ || ((h.tweet||'') + (h.based_on||'')).toLowerCase().indexOf(searchQ) >= 0;
  });
  if (hEl) hEl.textContent = hItems.length;
  if (hSec) {
    var hh = hItems.length
      ? hItems.map(buildHypeCard).join('')
      : '<div class="empty">No hypocrisy found</div>';
    hSec.innerHTML =
      '<div class="sec-head"><span class="sec-icon">🎭</span>' +
      '<span class="sec-title">Hypocrisy Watch</span>' +
      '<span class="sec-count">' + hItems.length + ' tweets</span></div>' + hh;
  }

  // Inventions
  var invEl   = document.getElementById('nc-inv');
  var invSec  = document.getElementById('sec-inv');
  var invItems = INV.filter(function(v) {
    return !searchQ || (v.title||'').toLowerCase().indexOf(searchQ) >= 0;
  });
  if (invEl) invEl.textContent = invItems.length;
  if (invSec) {
    var ivh = invItems.length
      ? invItems.map(buildInvCard).join('')
      : '<div class="empty">No inventions</div>';
    invSec.innerHTML =
      '<div class="sec-head"><span class="sec-icon">🔬</span>' +
      '<span class="sec-title">Inventions &amp; Breakthroughs</span>' +
      '<span class="sec-count">' + invItems.length + '</span></div>' + ivh;
  }
}

function showCat(cat, btn) {
  activeCat = cat;
  var bs = document.querySelectorAll('.nav-btn');
  for (var i = 0; i < bs.length; i++) bs[i].classList.remove('active');
  btn.classList.add('active');
  var ss = document.querySelectorAll('.cat-sec');
  for (var j = 0; j < ss.length; j++) ss[j].style.display = 'none';
  var sec = document.getElementById('sec-' + cat);
  if (sec) sec.style.display = 'block';
  var pills = document.getElementById('fmt-pills');
  if (pills) pills.style.display =
    (cat === 'brain' || cat === 'hype' || cat === 'inv') ? 'none' : 'flex';
}

function setFmt(fmt, btn) {
  activeFmt = fmt;
  var ps = document.querySelectorAll('.fpill');
  for (var i = 0; i < ps.length; i++) ps[i].classList.remove('active');
  btn.classList.add('active');
  renderAll();
}

function doSearch(q) { searchQ = q.toLowerCase().trim(); renderAll(); }

function swTab(btn) {
  var uid  = btn.dataset.uid;
  var fmt  = btn.dataset.fmt;
  var card = btn.closest('.news-card');
  if (!card) return;
  var ts = card.querySelectorAll('.ftab');
  for (var i = 0; i < ts.length; i++) ts[i].classList.remove('active');
  var ps = card.querySelectorAll('.panel');
  for (var j = 0; j < ps.length; j++) ps[j].classList.remove('active');
  btn.classList.add('active');
  var t = card.querySelector('.panel[data-uid="' + uid + '"][data-fmt="' + fmt + '"]');
  if (t) t.classList.add('active');
}

function togSum(btn) {
  var s = btn.nextElementSibling;
  if (!s) return;
  s.style.display = s.style.display === 'block' ? 'none' : 'block';
  btn.textContent = s.style.display === 'block' ? 'hide summary' : 'show summary';
}

function loadData() {
  var loadEl = document.getElementById('main-loading');
  fetch('data.json?t=' + Date.now())
    .then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function(d) {
      NEWS  = d.news          || [];
      HYPE  = d.hypocrisy     || [];
      VIDS  = d.videos        || [];
      BRAIN = d.between_lines || [];
      INV   = d.inventions    || [];
      if (loadEl) loadEl.style.display = 'none';
      renderAll();
    })
    .catch(function(err) {
      console.error('Failed to load data.json:', err);
      if (loadEl) loadEl.innerHTML =
        '<div class="empty">Failed to load data<small>' + err.message + '</small></div>';
    });
}

loadData();
