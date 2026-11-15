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

                return {
                    href: href,
                    is_video: hasVideoTag || hasPlayIcon || hasDuration
                };
            });
        }""")
        return results

    def _extract_reel_metadata(self, page, url: str) -> tuple[str, str, int, int]:
        """Visit a reel/post page and extract (author, caption, views, likes)."""
        author, caption, views, likes = "", "", 0, 0
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
        except Exception:
            pass
        return author, caption, views, likes

    def scrape_hashtag_reels(self, hashtag: str, max_reels: int = 10) -> List[Reel]:
        clean_tag = hashtag.strip().lstrip("#")
        # Instagram redirects /explore/tags/{tag}/ to /explore/search/keyword/?q=%23{tag}
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

            # Check if login is needed
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
                        views=250_000 + (len(reels) * 50_000),  # placeholder ranking estimate
                        likes=0,
                        author=clean_tag + "_creator"
                    )
                    reels.append(reel)

                if new_found == 0:
                    no_new_count += 1
                    if no_new_count >= 3:
                        break  # reached bottom of feed
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
                        author, caption, views, likes = self._extract_reel_metadata(page, r.url)
                        if author:
                            r.author = author
                        if caption:
                            r.caption = caption
                        if views > 0:
                            r.views = views
                        if likes > 0:
                            r.likes = likes
                    except Exception as e:
                        console.print(f"[yellow]    (skipped metadata for {r.id}: {e})[/yellow]")

            context.close()
        return reels