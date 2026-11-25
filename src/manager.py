"""
Content manager for filtering, ranking, and organizing reels.
"""

import json
from pathlib import Path
from typing import List, Set
from .reel import Reel
from .niche_config import NicheConfig


class ContentManager:
    def __init__(self, metadata_dir: str = "output"):
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self._downloaded_ids: Set[str] = self._load_downloaded_ids()

    def _load_downloaded_ids(self) -> Set[str]:
        """Load previously downloaded reel IDs from metadata directory."""
        downloaded = set()
        if self.metadata_dir.exists():
            for f in self.metadata_dir.rglob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                        reel_id = data.get("id", "")
                        if reel_id:
                            downloaded.add(reel_id)
                except Exception:
                    continue
        return downloaded

    def is_already_downloaded(self, reel: Reel) -> bool:
        """Check if this reel has already been downloaded by ID."""
        return reel.id in self._downloaded_ids

    def filter_and_rank(self, reels: List[Reel], config: NicheConfig) -> List[Reel]:
        """
        Filters reels based on views, duration, and excluded words,
        then ranks them by engagement score.
        """
        # Filter out already-downloaded reels if configured
        if config.skip_downloaded:
            reels = [r for r in reels if not self.is_already_downloaded(r)]

        filtered = [
            r for r in reels
            if r.matches_filters(
                min_views=config.min_views,
                max_duration=config.max_duration,
                exclude_words=config.exclude_words,
                include_words=config.include_words
            )
        ]

        # Sort by virality score descending
        filtered.sort(key=lambda r: r.virality_score(), reverse=True)
        return filtered[:config.max_results]

    def save_metadata(self, reel: Reel, niche_name: str):
        """Save reel caption and metadata to local files."""
        safe_niche = niche_name.lower().replace(" ", "_")
        niche_dir = self.metadata_dir / safe_niche
        niche_dir.mkdir(parents=True, exist_ok=True)

        meta_file = niche_dir / f"{reel.id}_meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(reel.to_dict(), f, indent=2)

        caption_file = niche_dir / f"{reel.id}_caption.txt"
        with open(caption_file, "w", encoding="utf-8") as f:
            f.write(f"URL: {reel.url}\n")
            f.write(f"Author: @{reel.author}\n")
            f.write(f"Views: {reel.views:,} | Likes: {reel.likes:,} | Duration: {reel.duration}s\n")
            f.write("-" * 40 + "\n\n")
            f.write(reel.caption or "No caption provided.")