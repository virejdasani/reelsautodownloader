# 🎬 Instagram Reels Viral Downloader for YouTube Shorts

A Python CLI tool that automates finding, ranking, and downloading the most viral Instagram Reels in any niche, optimized for reposting on YouTube Shorts.

---

## ✨ Features

- 🔍 **Hashtag & Niche Search**: Search single or multiple hashtags with **AND / OR logic** (e.g. `gta6,gameplay`).
- ⏱️ **Duration Filtering**: Filter videos strictly under your target length (e.g. `<= 15 seconds` for YouTube Shorts).
- 📈 **Virality Ranking**: Ranks reels using a composite score based on **views, likes, comments, and engagement rate**.
- 🌐 **Browser Automation**: Uses Playwright to drive Chrome, allowing persistent login sessions and bypassing API blocks.
- 📁 **Organized Downloads**: Each video is saved into its own folder containing:
  - High-quality `.mp4` video stream (via `yt-dlp`).
  - Clean `.md` markdown file with full caption, hashtags, author info, views, and likes ready to copy-paste.

---

## 🛠️ Prerequisites

- **Python 3.10+**
- **Google Chrome** installed on your system
- **ffmpeg** (for video merging via `yt-dlp`)

### macOS setup for ffmpeg (if needed):
```bash
brew install ffmpeg
```

---

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/insta-reels-bot.git
   cd insta-reels-bot
   ```

2. **Create & activate a Python virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browser binaries:**
   ```bash
   playwright install chromium
   ```

---

## 💻 Usage

### 1. Hashtag/Niche Reels Downloader (`main.py`)
Finds viral reels by hashtag search with AND/OR logic.

```bash
python3 main.py
```

**Interactive Prompts:**
1. **Niche/Keyword**: e.g., `GTA 6`, `Tech Memes`, `Gaming News`
2. **Hashtag(s)**: Single (`gta6`) or comma-separated multiple (`gta6, gameplay, gtavi`)
3. **Number of Reels**: How many top viral videos to collect (default: `10`)
4. **Minimum View Count**: Filter out low-performing videos (default: `100,000`)
5. **Max Duration (seconds)**: Filter out long videos (e.g., `15` for Shorts, `60` for longer, `0` for no limit)
6. **AND/OR Filter**: If multiple hashtags, choose whether videos must contain **ALL** hashtags (`y`) or **ANY** (`n`)

---

### 2. DM Reels Downloader (`dm_main.py`)
Downloads all reels sent to you in DMs from a specific user within the last X hours.

```bash
python3 dm_main.py
```

**Interactive Prompts:**
1. **Username**: The Instagram handle who sent the reels (e.g., `virejdasani`)
2. **Hours Back**: How many hours back to search (default: `24`)
3. **Max Duration (seconds)**: Filter out long videos (e.g., `15` for Shorts, `0` for no limit)
4. **Minimum Views**: Optional view count filter (default: `0`)

### Interactive Prompts:

1. **Niche/Keyword**: e.g., `GTA 6`, `Tech Memes`, `Gaming News`
2. **Hashtag(s)**: Enter single (`gta6`) or multiple comma-separated hashtags (`gta6, gameplay, gtavi`)
3. **Number of Reels**: How many top viral videos to collect (default: `10`)
4. **Minimum View Count**: Filter out low-performing videos (default: `100,000`)
5. **Max Duration (seconds)**: Filter out long videos (e.g., `15` for Shorts, `60` for longer, `0` for no limit)
6. **AND/OR Filter**: If multiple hashtags entered, choose whether videos must contain **ALL** hashtags (`y`) or **ANY** (`n`)

---

## 📂 Output Folder Structure

Downloaded content is organized by niche and video title:

```
downloads/
└── gta_6/
    ├── Insane_GTA6_gameplay!/
    │   ├── Insane_GTA6_gameplay!.mp4
    │   └── Insane_GTA6_gameplay!.md
    └── Top_3_things_in_latest_trailer/
        ├── Top_3_things_in_latest_trailer.mp4
        └── Top_3_things_in_latest_trailer.md
```

### Example `.md` metadata file:
```markdown
# Insane_GTA6_gameplay!

- **URL:** https://www.instagram.com/reel/C-xyz123/
- **Author:** @gamer_insider
- **Views:** 1,450,000
- **Likes:** 180,000
- **Comments:** 3,200
- **Virality Score:** 3282.00

## Caption

```text
Insane GTA 6 graphics comparison! What do you think? #gta6 #gameplay #gaming
```
```

---

## 🔑 Login & Rate Limits

- On first run, Chrome will open to Instagram. **Log in manually** in the browser window if prompted.
- Playwright saves your session in `browser_session/` so you won't need to log in again on subsequent runs.
- **Do not share or commit `browser_session/` or `cookies.txt`.** (Already covered by `.gitignore`).

---

## ⚖️ Legal & ToS Disclaimer

This project is intended for educational and authorized fair-use research purposes. Scraping Instagram violates Meta's Terms of Service. Re-uploading third-party copyright-protected content without permission can result in YouTube copyright strikes. Always transform content or obtain licensing before publishing commercially.

---

## 📄 License

MIT License