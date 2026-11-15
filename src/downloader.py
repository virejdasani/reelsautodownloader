"""
Video downloader using yt-dlp.
"""

from __future__ import annotations

import re
from pathlib import Path
import yt_dlp
from .reel import Reel


def sanitize_filename(name: str) -> str:
    """Sanitize string for folder/file names."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r'\s+', "_", name).strip()
    return name[:50] or "video"


class VideoDownloader:
    def __init__(self, base_output_dir: str = "downloads", cookies_from_browser: str = None):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_from_browser = cookies_from_browser  # e.g. "chrome", "firefox", "edge"

    def download_reel(self, reel: Reel, niche_name: str) -> bool:
        """
        Downloads a reel into downloads/{niche}/{video_title}/
        containing {video_title}.mp4 and {video_title}.md
        """
        safe_niche = sanitize_filename(niche_name)
        # Use caption as the video title, fallback to reel ID
        video_title = sanitize_filename(reel.caption[:40] if reel.caption else f"reel_{reel.id}")
        video_dir = self.base_output_dir / safe_niche / video_title
        video_dir.mkdir(parents=True, exist_ok=True)

        # yt-dlp output template
        outtmpl = str(video_dir / f"{video_title}.%(ext)s")

        ydl_opts = {
            'outtmpl': outtmpl,
            'format': 'bestvideo+bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
        }

        # Pass browser cookies if specified (essential for Instagram login wall)
        if self.cookies_from_browser:
            ydl_opts['cookies_from_browser'] = self.cookies_from_browser

        success = False
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(reel.url, download=True)
                if info:
                    ext = info.get('ext', 'mp4')
                    reel.local_path = str(video_dir / f"{video_title}.{ext}")
                    reel.downloaded = True
                    success = True
        except Exception as e:
            print(f"[!] Error downloading {reel.url}: {e}")

        # Always save markdown file with caption & likes/views
        md_path = video_dir / f"{video_title}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {video_title}\n\n")
            f.write(f"- **URL:** {reel.url}\n")
            f.write(f"- **Author:** @{reel.author}\n")
            f.write(f"- **Views:** {reel.views:,}\n")
            f.write(f"- **Likes:** {reel.likes:,}\n")
            f.write(f"- **Comments:** {reel.comments:,}\n")
            f.write(f"- **Virality Score:** {reel.virality_score():.2f}\n\n")
            f.write(f"## Caption\n\n```text\n{reel.caption or 'No caption'}\n```\n")

        return success