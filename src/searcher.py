"""
Instagram searcher using instagrapi for public hashtag and reel discovery.
"""

from __future__ import annotations

import time
from random import uniform
from typing import List, Optional
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError

from .reel import Reel, _parse_count


class InstagramSearcher:
    """Searcher for Instagram Reels using instagrapi."""

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None, session_file: str = "instagram_session.json"):
        self.username = username
        self.password = password
        self.session_file = session_file
        self.client = Client()
        self._logged_in = False

    def authenticate(self) -> bool:
        """Authenticate or load session."""
        session_path = self.client.settings_path if hasattr(self.client, 'settings_path') else self.session_file
        try:
            if self.client.load_settings(self.session_file):
                self.client.get_timeline_feed()
                self._logged_in = True
                return True
        except Exception:
            pass

        if self.username and self.password:
            try:
                self.client.login(self.username, self.password)
                self.client.dump_settings(self.session_file)
                self._logged_in = True
                return True
            except Exception as e:
                print(f"[!] Login failed: {e}")
                return False

        # Try anonymous public browsing if login not provided
        return False

    def search_hashtag_reels(self, hashtag: str, max_amount: int = 30) -> List[Reel]:
        """Search top/recent media for a hashtag and extract Reel info."""
        clean_tag = hashtag.strip().lstrip("#")
        reels: List[Reel] = []

        try:
            # Try fetching hashtag medias
            medias = self.client.hashtag_medias_recent(clean_tag, amount=max_amount)
        except Exception as e:
            print(f"[!] Error fetching hashtag #{clean_tag}: {e}")
            return []

        for m in medias:
            # Check if it's a video or reel (media_type == 2 is video, or has video_url)
            if not getattr(m, 'video_url', None) and getattr(m, 'media_type', 0) != 2:
                continue

            media_id = str(getattr(m, 'id', ''))
            code = str(getattr(m, 'code', ''))
            url = f"https://www.instagram.com/reel/{code}/" if code else f"https://www.instagram.com/p/{media_id}/"

            caption = getattr(m, 'caption_text', '') or getattr(m, 'caption', '') or ''
            author = getattr(m, 'user', None)
            username = getattr(author, 'username', '') if author else ''

            views = _parse_count(getattr(m, 'view_count', 0) or getattr(m, 'play_count', 0) or 0)
            likes = _parse_count(getattr(m, 'like_count', 0))
            comments = _parse_count(getattr(m, 'comment_count', 0))

            reel = Reel(
                id=code or media_id,
                url=url,
                caption=caption,
                author=username,
                views=views,
                likes=likes,
                comments=comments,
                video_url=str(getattr(m, 'video_url', '') or ''),
                thumbnail_url=str(getattr(m, 'thumbnail_url', '') or ''),
            )
            reels.append(reel)
            time.sleep(uniform(0.2, 0.5))

        return reels
