"""
Niche configuration for the Instagram Reels downloader bot.

Defines what niches to search for, which hashtags/keywords to use,
and ranking preferences (min views, engagement thresholds, etc.).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import yaml


@dataclass
class NicheConfig:
    """Configuration for a single content niche."""

    name: str
    """Human-readable name, e.g. 'GTA 6'."""

    keywords: list[str] = field(default_factory=list)
    """Search keywords / hashtags to query, e.g. ['gta6', 'gtavi']."""

    min_views: int = 100_000
    """Minimum view count for a reel to be considered 'viral'."""

    max_results: int = 10
    """Maximum number of reels to download per run."""

    exclude_words: list[str] = field(default_factory=list)
    """Words that disqualify a reel (e.g. ['fake', 'leak'])."""

    include_words: list[str] = field(default_factory=list)
    """If non-empty, caption must contain at least one of these."""

    sort_by: str = "views"
    """Sort key: 'views', 'likes', 'comments', 'engagement'."""

    enabled: bool = True
    """Set to False to skip this niche."""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NicheConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class BotConfig:
    """Top-level bot configuration."""

    niches: list[NicheConfig] = field(default_factory=list)
    output_dir: str = "downloads"
    metadata_dir: str = "output"
    max_concurrent_downloads: int = 3
    skip_downloaded: bool = True
    save_captions: bool = True
    save_thumbnails: bool = True
    video_format: str = "mp4"
    max_video_height: int = 1080

    @classmethod
    def from_yaml(cls, path: str | Path) -> "BotConfig":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        niches = [NicheConfig.from_dict(n) for n in data.pop("niches", [])]
        return cls(niches=niches, **{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_yaml(self, path: str | Path) -> None:
        path = Path(path)
        data: dict[str, Any] = {
            "niches": [n.to_dict() for n in self.niches],
            "output_dir": self.output_dir,
            "metadata_dir": self.metadata_dir,
            "max_concurrent_downloads": self.max_concurrent_downloads,
            "skip_downloaded": self.skip_downloaded,
            "save_captions": self.save_captions,
            "save_thumbnails": self.save_thumbnails,
            "video_format": self.video_format,
            "max_video_height": self.max_video_height,
        }
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def active_niches(self) -> list[NicheConfig]:
        return [n for n in self.niches if n.enabled]


def create_default_config(path: str | Path) -> BotConfig:
    """Create a default config with example niches."""
    config = BotConfig(
        niches=[
            NicheConfig(
                name="GTA 6",
                keywords=["gta6", "gtavi", "rockstargames"],
                min_views=500_000,
                max_results=10,
                exclude_words=["leak", "rumor", "fake"],
            ),
            NicheConfig(
                name="Gaming News",
                keywords=["gaming", "gameupdate", "esports"],
                min_views=200_000,
                max_results=8,
            ),
        ]
    )
    config.to_yaml(path)
    return config


def load_config(path: str | Path) -> BotConfig:
    """Load a BotConfig from a YAML file, creating a default if missing."""
    path = Path(path)
    if not path.exists():
        return create_default_config(path)
    return BotConfig.from_yaml(path)