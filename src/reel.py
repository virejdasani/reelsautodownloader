"""
Data model for an Instagram Reel.

Represents a single reel with its metadata: views, likes, comments,
caption, hashtags, and download state.
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


def extract_hashtags(text: str) -> list[str]:
    """Extract hashtags from a caption."""
    return re.findall(r"#(\w+)", text or "")


def extract_mentions(text: str) -> list[str]:
    """Extract @mentions from a caption."""
    return re.findall(r"@(\w+)", text or "")


@dataclass
class Reel:
    """A single Instagram Reel with metadata and download state."""

    id: str
    """Unique identifier for the reel (short code / pk)."""

    url: str
    """Direct URL to the reel on Instagram."""

    caption: str = ""
    """Full caption text of the reel."""

    author: str = ""
    """Username of the uploader."""

    views: int = 0
    """View count."""

    likes: int = 0
    """Like count."""

    comments: int = 0
    """Comment count."""

    shares: int = 0
    """Share count (may not always be available)."""

    likes_count: int = 0
    """Alias for likes (kept for compatibility)."""

    thumbnail_url: str = ""
    """URL of the reel's thumbnail image."""

    video_url: str = ""
    """Direct video URL (mp4)."""

    duration: float = 0.0
    """Duration in seconds."""

    posted_at: datetime | None = None
    """When the reel was posted."""

    hashtags: list[str] = field(default_factory=list)
    """Hashtags extracted from the caption."""

    mentions: list[str] = field(default_factory=list)
    """@mentions extracted from the caption."""

    downloaded: bool = False
    """Whether the video has been downloaded."""

    local_path: str = ""
    """Local filesystem path of the downloaded video."""

    @property
    def engagement(self) -> float:
        """Engagement rate = (likes + comments) / max(views, 1)."""
        if self.views <= 0:
            return 0.0
        return (self.likes + self.comments) / self.views

    @property
    def engagement_score(self) -> float:
        """Alias for engagement."""
        return self.engagement

    def virality_score(self) -> float:
        """
        Composite virality score.

        Weighted combination of views (reach) and engagement.
        Formula: views * (1 + engagement * 10) / 1000
        This rewards both reach AND engagement.
        """
        return self.views * (1 + self.engagement * 10) / 1000

    def matches_filters(
        self,
        min_views: int = 0,
        exclude_words: list[str] | None = None,
        include_words: list[str] | None = None,
    ) -> bool:
        """Check if this reel passes the configured filters."""
        if self.views < min_views:
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
            "shares": self.shares,
            "thumbnail_url": self.thumbnail_url,
            "video_url": self.video_url,
            "duration": self.duration,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "hashtags": self.hashtags,
            "mentions": self.mentions,
            "downloaded": self.downloaded,
            "local_path": self.local_path,
            "engagement": round(self.engagement, 4),
            "virality_score": round(self.virality_score(), 2),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Reel":
        posted = data.get("posted_at")
        if isinstance(posted, str):
            try:
                posted = datetime.fromisoformat(posted)
            except ValueError:
                posted = None
        return cls(
            id=data.get("id", ""),
            url=data.get("url", ""),
            caption=data.get("caption", ""),
            author=data.get("author", ""),
            views=data.get("views", 0),
            likes=data.get("likes", 0),
            comments=data.get("comments", 0),
            shares=data.get("shares", 0),
            thumbnail_url=data.get("thumbnail_url", ""),
            video_url=data.get("video_url", ""),
            duration=data.get("duration", 0.0),
            posted_at=posted,
            hashtags=data.get("hashtags", []),
            mentions=data.get("mentions", []),
            downloaded=data.get("downloaded", False),
            local_path=data.get("local_path", ""),
        )

    def __repr__(self) -> str:
        return (
            f"Reel(id={self.id!r}, author={self.author!r}, "
            f"views={self.views}, likes={self.likes}, "
            f"engagement={self.engagement:.3f})"
        )