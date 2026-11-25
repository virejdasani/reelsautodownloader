"""
Data model for an Instagram Reel.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _parse_count(value: Any) -> int:
    """Parse Instagram's formatted counts (e.g. '1.2M', '850K', '123') to int."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip().replace(",", "").replace(" ", "")
    if not s:
        return 0
    multipliers = {
        "K": 1_000,
        "M": 1_000_000,
        "B": 1_000_000_000,
        "T": 1_000_000_000_000,
    }
    if s[-1].upper() in multipliers:
        try:
            return int(float(s[:-1]) * multipliers[s[-1].upper()])
        except ValueError:
            return 0
    try:
        return int(s)
    except ValueError:
        return 0


@dataclass
class Reel:
    """A single Instagram Reel with metadata and download state."""

    id: str
    url: str
    caption: str = ""
    author: str = ""
    views: int = 0
    likes: int = 0
    comments: int = 0
    duration: float = 0.0 # Duration in seconds
    shares: int = 0
    thumbnail_url: str = ""
    video_url: str = ""
    posted_at: datetime | None = None
    hashtags: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    downloaded: bool = False
    local_path: str = ""

    @property
    def engagement(self) -> float:
        if self.views <= 0:
            return 0.0
        return (self.likes + self.comments) / self.views

    def virality_score(self) -> float:
        return self.views * (1 + self.engagement * 10) / 1000

    def matches_filters(
        self,
        min_views: int = 0,
        max_duration: int = 0,
        exclude_words: list[str] | None = None,
        include_words: list[str] | None = None,
    ) -> bool:
        """Check if this reel passes the configured filters."""
        if self.views < min_views:
            return False
        if max_duration > 0 and self.duration > max_duration:
            return False

        caption_lower = (self.caption or "").lower()
        for word in exclude_words or []:
            if word.lower() in caption_lower:
                return False
        if include_words:
            if not any(w.lower() in caption_lower for w in include_words):
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "caption": self.caption,
            "author": self.author,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "duration": self.duration,
            "engagement": round(self.engagement, 4),
            "virality_score": round(self.virality_score(), 2),
        }