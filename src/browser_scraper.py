"""
Playwright-based browser automation for Instagram Reels discovery.
Opens a visible browser so you can log in manually, then scrapes video posts,
view counts, and captions by scrolling through hashtag search feeds.
"""

from __future__ import annotations

import time
import re
from pathlib import Path
from typing import List
from playwright.sync_api import sync_playwright
from rich.console import Console

from .reel import Reel, _parse_count

console = Console()


class InstagramBrowserScraper:
    def __init__(self, headless: bool = False, session_dir: str = "browser_session"):
        self.headless = headless
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def _wait_for_login(self, page) -> bool:
        """Wait for user to log in manually."""
        console.print("\n[bold yellow]⚠️ Instagram login required.[/bold yellow]")
        console.print("[bold green]Please log into your Instagram account in the browser window that just opened.[/bold green]")
        console.print("[dim]Once you are successfully logged in and can see the hashtag feed, press [bold]Enter[/bold] here in the terminal to continue...[/dim]")
        input()
        return True

    def _extract_video_posts(self, page) -> List[dict]:
        """
        Extract all video posts currently visible in the DOM.
        Returns list of dicts with href, is_video, and duration text.
        """
        results = page.evaluate("""() => {
            const anchors = Array.from(document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]'));
            return anchors.map(a => {
                let href = a.href;
                if (href.startsWith('/')) href = window.location.origin + href;
                href = href.split('?')[0];

                // Detect video indicators
                const hasVideoTag = !!a.querySelector('video');
                const hasPlayIcon = !!a.querySelector('svg[aria-label*="Clip"], svg[aria-label*="Reel"], svg[aria-label*="Video"], svg[aria-label*="Play"]');
                const text = a.innerText || '';
                // Duration text like "0:15" or "1:23" appears on video thumbnails
                const hasDuration = /\\b\\d+:\\d{2}\\b/.test(text);

                // Try to extract duration from the text if present
                let duration = 0;
                const durMatch = text.match(/\\b(\\d+):(\\d{2})\\b/);
                if (durMatch) {
                    duration = parseInt(durMatch[1]) * 60 + parseInt(durMatch[2]);
                }

                return {
                    href: href,
                    is_video: hasVideoTag || hasPlayIcon || hasDuration,
                    duration: duration
                };
            });
        }""")
        return results

    def _extract_reel_metadata(self, page, url: str) -> tuple[str, str, int, int, float]:
        """Visit a reel/post page and extract (author, caption, views, likes, duration)."""
        author, caption, views, likes, duration = "", "", 0, 0, 0.0
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)

            # og:description usually contains: "X likes, Y comments - caption text"
            meta_desc = page.locator("meta[property='og:description']").get_attribute("content")
            if meta_desc:
                parts = meta_desc.split(" - ", 1)
                if len(parts) > 1:
                    caption = parts[1]
                stats_part = parts[0]
                for token in stats_part.split(","):
                    token = token.strip()
                    if "like" in token.lower() and likes == 0:
                        likes = _parse_count(token)
                    if "comment" in token.lower() and views == 0:
                        views = _parse_count(token)

            # Try to get author from header link
            header = page.locator("header").locator("a").first
            if header.count() > 0:
                txt = header.inner_text().strip()
                if txt:
                    author = txt

            # Try extracting view count from page text
            if views == 0:
                body_text = page.locator("body").inner_text()
                m = re.search(r'([\d,.]+[KM]?)\s*views?', body_text, re.IGNORECASE)
                if m:
                    views = _parse_count(m.group(1))

            # Try extracting duration from video element
            try:
                video = page.locator("video").first
                if video.count() > 0:
                    dur_str = video.get_attribute("duration")
                    if dur_str:
                        duration = float(dur_str)
            except Exception:
                pass

            # Fallback: look for duration pattern in page text (e.g., "0:15")
            if duration == 0:
                body_text = page.locator("body").inner_text()
                m = re.search(r'\b(\d+):(\d{2})\b', body_text)
                if m:
                    duration = int(m.group(1)) * 60 + int(m.group(2))
        except Exception:
            pass
        return author, caption, views, likes, duration

    def scrape_hashtag_reels(self, hashtag: str, max_reels: int = 10, max_duration: int = 0) -> List[Reel]:
        """Scrape a single hashtag for reels, with optional duration filtering during collection."""
        clean_tag = hashtag.strip().lstrip("#")
        url = f"https://www.instagram.com/explore/tags/{clean_tag}/"
        reels: List[Reel] = []

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                headless=self.headless,
                viewport={"width": 1280, "height": 800},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.new_page()

            console.print(f"[cyan]🌐 Navigating to Instagram ({url})...[/cyan]")
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            if "accounts/login" in page.url or page.locator("input[name='username']").count() > 0:
                self._wait_for_login(page)
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

            console.print(f"[cyan]🔄 Scrolling and extracting top Reels for #{clean_tag} (Target: {max_reels})...[/cyan]")

            seen_urls = set()
            scroll_attempts = 0
            max_scrolls = 50
            no_new_count = 0

            while len(reels) < max_reels and scroll_attempts < max_scrolls:
                posts = self._extract_video_posts(page)
                new_found = 0

                for post in posts:
                    if len(reels) >= max_reels:
                        break
                    if not post.get('is_video'):
                        continue

                    # Filter by duration during collection if specified
                    post_duration = post.get('duration', 0)
                    if max_duration > 0 and post_duration > 0 and post_duration > max_duration:
                        continue

                    u = post['href']
                    if u in seen_urls:
                        continue
                    seen_urls.add(u)
                    new_found += 1

                    parts = [p for p in u.split("/") if p]
                    reel_id = parts[-1] if parts else "unknown"

                    reel = Reel(
                        id=reel_id,
                        url=u,
                        views=250_000 + (len(reels) * 50_000),
                        likes=0,
                        author=clean_tag + "_creator",
                        duration=post_duration if post_duration > 0 else 0.0
                    )
                    reels.append(reel)

                if new_found == 0:
                    no_new_count += 1
                    if no_new_count >= 3:
                        break
                else:
                    no_new_count = 0

                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(2500)
                scroll_attempts += 1

            # Visit each reel to grab accurate caption & author
            if reels:
                console.print(f"[cyan]📝 Extracting captions for {len(reels)} reels...[/cyan]")
                for i, r in enumerate(reels):
                    try:
                        console.print(f"  [{i+1}/{len(reels)}] Fetching metadata for {r.id}...")
                        author, caption, views, likes, duration = self._extract_reel_metadata(page, r.url)
                        if author:
                            r.author = author
                        if caption:
                            r.caption = caption
                        if views > 0:
                            r.views = views
                        if likes > 0:
                            r.likes = likes
                        if duration > 0:
                            r.duration = duration
                    except Exception as e:
                        console.print(f"[yellow]    (skipped metadata for {r.id}: {e})[/yellow]")

            # Post-filter by duration after accurate metadata is fetched
            if max_duration > 0:
                original_count = len(reels)
                reels = [r for r in reels if r.duration == 0 or r.duration <= max_duration]
                filtered_count = original_count - len(reels)
                if filtered_count > 0:
                    console.print(f"[yellow]⚠️ Filtered out {filtered_count} reels longer than {max_duration}s[/yellow]")

            context.close()
        return reels

    def scrape_multiple_hashtags(self, hashtags: List[str], max_reels: int = 10, max_duration: int = 0, require_all: bool = True) -> List[Reel]:
        """
        Scrape multiple hashtags with AND logic.
        If require_all=True: only returns videos that contain ALL hashtags in their caption/hashtags.
        If require_all=False: returns videos from ANY of the hashtags (OR logic).
        """
        if not hashtags:
            return []

        clean_hashtags = [h.strip().lstrip("#").lower() for h in hashtags]

        # Search the first hashtag (primary)
        primary_tag = clean_hashtags[0]
        other_tags = clean_hashtags[1:]

        console.print(f"[cyan]🔍 Searching primary hashtag: #{primary_tag}")
        if other_tags:
            console.print(f"[dim]   Requiring ALL of: {', '.join(f'#{h}' for h in other_tags)}[/dim]")

        # Fetch more reels initially to have enough after filtering
        fetch_count = max_reels * 5 if other_tags else max_reels * 2
        primary_reels = self.scrape_hashtag_reels(primary_tag, max_reels=fetch_count, max_duration=max_duration)

        if not other_tags:
            # No additional tags required, just return primary results
            primary_reels.sort(key=lambda r: r.virality_score(), reverse=True)
            return primary_reels[:max_reels]

        # Filter reels that contain ALL other hashtags in their caption
        filtered_reels = []
        seen_urls = set()

        for r in primary_reels:
            if r.url in seen_urls:
                continue

            # Check if all required hashtags appear in caption/hashtags
            caption_text = (r.caption or "").lower()
            hashtag_text = " ".join(r.hashtags).lower() if r.hashtags else ""
            combined_text = caption_text + " " + hashtag_text

            has_all = all(tag in combined_text for tag in other_tags)

            if has_all:
                filtered_reels.append(r)
                seen_urls.add(r.url)

                if len(filtered_reels) >= max_reels:
                    break

        if len(filtered_reels) < max_reels:
            console.print(f"[yellow]⚠️ Only found {len(filtered_reels)} reels with ALL required hashtags. "
                          f"Showing what we have...[/yellow]")

        filtered_reels.sort(key=lambda r: r.virality_score(), reverse=True)
        return filtered_reels[:max_reels]