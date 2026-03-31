# NewsAgent 🗞️📹

AI-powered news scraper that generates tweet content across **6 categories** — with images, YouTube videos, and a **Hypocrisy Watch** for sarcastic commentary.

Runs on **GitHub Actions** free cron. Results at your **GitHub Pages** URL.

---

## What's included per news item

| Feature | Detail |
|---|---|
| **Image thumbnail** | Extracted from RSS or scraped from article page (og:image) |
| **🖼️ View Image** | Opens image in new tab — right-click → Save |
| **▶ Watch Video** | If article embeds a YouTube video, direct link shown |
| **4 tweet formats** | Rewrite · Hot Take · Thread · Poll |
| **📋 Copy button** | One click copies to clipboard |

## YouTube videos section (per category)

| Source | How |
|---|---|
| **Channel RSS** | Latest videos from 20+ Telugu/India/World channels — no API key needed |
| **Trending India** | YouTube Data API v3 — optional, free, 10K units/day |

Each video gets: thumbnail preview, watch link, AI-written Rewrite + Hot Take tweet.

---

## Categories

| # | Category | News Sources | YouTube Channels |
|---|---|---|---|
| 1 | 🇺🇸 USA | AP, NPR, NBC, WaPo, Axios, Politico | NBC News, CNN, AP Archive |
| 2 | 🌍 International | BBC, Al Jazeera, Reuters, DW, Euronews, Guardian | Al Jazeera, DW News, BBC News |
| 3 | 🇮🇳 India | NDTV, TOI, The Hindu, HT, The Wire + Hindi sources | NDTV, India Today, Aaj Tak, Republic |
| 4 | 🎙️ Telugu | Sakshi, TV9, NTV, Eenadu, ABN, 10TV | TV9 Telugu, Sakshi TV, NTV, ABN, V6 |
| 5 | 🎬 Telugu Film | 123Telugu, Filmibeat, Gulte, Telugu360 | Aditya Music, T-Series Telugu, ETV Cinema |
| 6 | 🎭 Hypocrisy Watch | AI-picks irony/double standards from all above | — |

---

## GitHub Setup

### 1. Push repo
```bash
git init && git add . && git commit -m "Initial"
git remote add origin https://github.com/YOUR-USERNAME/NewsAgent.git
git push -u origin main
```

### 2. Add secrets
Settings → Secrets and variables → Actions → New repository secret:

| Secret Name | Value | Required? |
|---|---|---|
| `ANTHROPIC_API_KEY` | from console.anthropic.com | ✅ Required |
| `YOUTUBE_API_KEY` | from console.cloud.google.com | Optional |

Without `YOUTUBE_API_KEY`, YouTube channel videos (RSS-based) still work fine.

### 3. Enable GitHub Pages
Settings → Pages → Branch: `main` / Folder: `/docs` → Save

### 4. First run
Actions tab → **NewsAgent — Generate Tweets** → Run workflow → wait ~8 min

Your URL: `https://YOUR-USERNAME.github.io/NewsAgent/`

---

## Get a YouTube API key (free, optional)

1. Go to https://console.cloud.google.com
2. Create a project → Enable **YouTube Data API v3**
3. APIs & Services → Credentials → Create API Key
4. Add as `YOUTUBE_API_KEY` GitHub Secret

Free quota: 10,000 units/day. Each NewsAgent run uses 1 unit for trending.

---

## Local setup (Windows)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env    # fill in ANTHROPIC_API_KEY
python run.py             # opens docs/index.html in browser
```

Or double-click `run.bat`.

### Fast test run
```bash
python run.py --max 2 --skip-hypocrisy --yt-max 1
```

---

## CLI options

```bash
python run.py                          # Full run (all features)
python run.py --max 3                  # 3 items per source (faster)
python run.py --yt-max 2               # 2 videos per YouTube channel
python run.py --category telugu_film   # One category only
python run.py --skip-hypocrisy         # No sarcasm pass
python run.py --skip-youtube           # No YouTube videos
python run.py --skip-media             # No article image scraping
python run.py --no-browser             # Don't open browser
```

---

## Files

```
NewsAgent/
├── .github/workflows/newsagent.yml  ← GitHub Actions cron
├── docs/index.html                  ← Auto-generated, GitHub Pages
├── scraper.py                       ← RSS news fetcher
├── media_scraper.py                 ← Article images + YouTube
├── rewriter.py                      ← Claude AI tweet generator
├── viewer.py                        ← HTML viewer builder
├── run.py                           ← Main orchestrator
├── run.bat                          ← Windows launcher
├── requirements.txt
├── .env.example
└── .gitignore
```
