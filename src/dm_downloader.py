"""
Instagram DM Reels Downloader.
Fetches shared reels from DM conversation via GraphQL API.
"""

from __future__ import annotations

import time
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple
from playwright.sync_api import sync_playwright, Page, BrowserContext
from rich.console import Console

from .reel import Reel, _parse_count
from .browser_scraper import InstagramBrowserScraper

console = Console()


class InstagramDMReelsDownloader:
    def __init__(self, headless: bool = False, session_dir: str = "browser_session"):
        self.headless = headless
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.browser_scraper = InstagramBrowserScraper(headless=headless, session_dir=session_dir)

    def _wait_for_login(self, page) -> bool:
        """Wait for user to log in manually."""
        console.print("\n[bold yellow]⚠️ Instagram login required.[/bold yellow]")
        console.print("[bold green]Please log into your Instagram account in the browser window that just opened.[/bold green]")
        console.print("[dim]Once you are successfully logged in and can see your DMs, press [bold]Enter[/bold] here in the terminal to continue...[/dim]")
        input()
        return True

    def _parse_timestamp(self, text: str) -> datetime | None:
        """Parse Instagram relative timestamps like '2h', '3d', '1w', etc."""
        text = text.strip().lower()
        now = datetime.now()

        m = re.match(r'(\d+)\s*([hdwmy])', text)
        if m:
            val = int(m.group(1))
            unit = m.group(2)
            if unit == 'h':
                return now - timedelta(hours=val)
            elif unit == 'd':
                return now - timedelta(days=val)
            elif unit == 'w':
                return now - timedelta(weeks=val)
            elif unit == 'm':
                return now - timedelta(weeks=val*4)
            elif unit == 'y':
                return now - timedelta(weeks=val*52)

        for fmt in ['%b %d, %Y', '%b %d', '%m/%d', '%Y-%m-%d']:
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    def _find_and_open_conversation(self, page, username: str) -> bool:
        """Find and click the conversation with the specified username."""
        console.print(f"[cyan]🔍 Looking for conversation with @{username}...[/cyan]")
        page.wait_for_timeout(5000)

        username_lower = username.lower()
        username_parts = [username_lower]
        username_parts.extend(username_lower.split('.'))
        username_parts.extend(username_lower.split('_'))
        username_parts = [p for p in username_parts if len(p) > 2]

        conversation_selectors = [
            "div[role='button'][tabindex='0']",
            "div[role='listitem']",
        ]

        for selector in conversation_selectors:
            try:
                elements = page.locator(selector).all()
                for el in elements:
                    try:
                        text = el.inner_text().lower()
                        if any(part in text for part in username_parts):
                            console.print(f"[green]Found conversation with @{username}, clicking...[/green]")
                            el.click()
                            page.wait_for_timeout(5000)

                            if '/direct/t/' in page.url:
                                console.print(f"[green]✓ Successfully opened conversation[/green]")
                                return True
                            else:
                                console.print(f"[yellow]Clicked but URL didn't change to conversation, trying next...[/yellow]")
                                page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
                                page.wait_for_timeout(3000)
                    except Exception:
                        continue
            except Exception:
                continue

        try:
            elements = page.evaluate(f"""() => {{
                const results = [];
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                let node;
                while (node = walker.nextNode()) {{
                    if (node.textContent.toLowerCase().includes('{username_lower}')) {{
                        let el = node.parentElement;
                        let depth = 0;
                        while (el && el !== document.body && depth < 15) {{
                            if (el.tagName === 'A' || el.tagName === 'BUTTON' ||
                                el.getAttribute('role') === 'button' ||
                                el.getAttribute('role') === 'listitem' ||
                                el.getAttribute('tabindex') === '0' ||
                                el.onclick || getComputedStyle(el).cursor === 'pointer') {{
                                results.push({{
                                    tag: el.tagName,
                                    text: el.innerText.substring(0, 300),
                                    className: el.className,
                                    href: el.href || '',
                                    role: el.getAttribute('role') || '',
                                    tabindex: el.getAttribute('tabindex') || '',
                                    xpath: getXPath(el)
                                }});
                                break;
                            }}
                            el = el.parentElement;
                            depth++;
                        }}
                    }}
                }}
                return results;

                function getXPath(element) {{
                    if (element.id) return `//*[@id="${{element.id}}"]`;
                    if (element === document.body) return '/html/body';
                    let ix = 0;
                    let siblings = element.parentNode.childNodes;
                    for (let i = 0; i < siblings.length; i++) {{
                        let sibling = siblings[i];
                        if (sibling === element) {{
                            return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                        }}
                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {{
                            ix++;
                        }}
                    }}
                }}
            }}""")

            for el in elements:
                if 'xpath' in el:
                    try:
                        console.print(f"[cyan]Trying xpath click: {el['xpath'][:100]}...[/cyan]")
                        page.locator(f"xpath={el['xpath']}").first.click()
                        page.wait_for_timeout(5000)
                        if '/direct/t/' in page.url:
                            console.print(f"[green]✓ Opened conversation via xpath[/green]")
                            return True
                    except Exception:
                        continue
                elif 'href' in el and '/direct/t/' in el['href']:
                    try:
                        page.goto(el['href'], wait_until="domcontentloaded")
                        page.wait_for_timeout(5000)
                        if '/direct/t/' in page.url:
                            return True
                    except Exception:
                        continue
        except Exception as e:
            console.print(f"[dim]JS search failed: {e}[/dim]")

        console.print(f"[red]Could not find conversation with @{username}[/red]")
        return False

    def _is_valid_reel_url(self, url: str) -> bool:
        """Check if URL is a valid reel/post URL with an ID."""
        return bool(re.search(r'/(p|reel|tv|reels)/[A-Za-z0-9_-]+/?$', url))

    def _clean_url(self, url: str) -> str:
        """Clean URL by removing query params and ensuring full domain."""
        if url.startswith("/"):
            url = f"https://www.instagram.com{url}"
        return url.split("?")[0]

    def _parse_graphql_responses(self, graphql_responses, page) -> List[Tuple[str, datetime | None]]:
        """Parse GraphQL responses for slide_messages and extract reel URLs."""
        collected_links: List[Tuple[str, datetime | None]] = []
        seen_urls = set()

        for resp in graphql_responses:
            try:
                body = resp.json()

                # Navigate to slide_messages - exact path from GraphQL response
                thread_data = body.get('data', {}).get('get_slide_thread_nullable', {}).get('as_ig_direct_thread', {})

                # Also check for other possible paths
                if not thread_data or 'slide_messages' not in thread_data:
                    for key, val in body.get('data', {}).items():
                        if isinstance(val, dict) and 'slide_messages' in str(val):
                            thread_data = val
                            break

                slide_messages = thread_data.get('slide_messages', {}).get('edges', []) if thread_data else []

                for edge in slide_messages:
                    node = edge.get('node', {})
                    content = node.get('content', {})
                    xma = content.get('xma', {})

                    # Get the reel URL from target_url - this is the key field
                    target_url = xma.get('target_url', '')
                    if not target_url:
                        # Fallback: check other fields in xma
                        target_url = xma.get('url', '')

                    if target_url:
                        clean_url = self._clean_url(target_url)
                        if self._is_valid_reel_url(clean_url):
                            if clean_url not in seen_urls:
                                seen_urls.add(clean_url)

                                # Get timestamp from message
                                timestamp_ms = node.get('timestamp_ms', '')
                                link_timestamp = None
                                if timestamp_ms:
                                    try:
                                        link_timestamp = datetime.fromtimestamp(int(timestamp_ms) / 1000)
                                    except:
                                        pass

                                collected_links.append((clean_url, link_timestamp))
                                console.print(f"[dim]    ✓ Found reel URL: {clean_url}[/dim]")
            except Exception as e:
                console.print(f"[dim]Error parsing GraphQL response: {e}[/dim]")
                continue

        return collected_links

    def download_dm_reels(self, username: str, hours: int, max_duration: int = 0) -> List[Reel]:
        """
        Navigate to DMs, find conversation with username, fetch shared reels via GraphQL, and download.
        """
        reels: List[Reel] = []

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                headless=self.headless,
                viewport={"width": 1280, "height": 800},
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.new_page()

            # Set up GraphQL listener FIRST - before any navigation
            graphql_responses = []

            def handle_graphql_response(response):
                if "graphql" in response.url and response.status == 200:
                    graphql_responses.append(response)

            page.on("response", handle_graphql_response)

            console.print(f"[cyan]🌐 Navigating to Instagram DMs...[/cyan]")
            page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            if "accounts/login" in page.url or page.locator("input[name='username']").count() > 0:
                self._wait_for_login(page)
                page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

            # Find and open the conversation
            conv_found = self._find_and_open_conversation(page, username)

            if not conv_found:
                console.print(f"[red]Could not find conversation with @{username}[/red]")
                console.print("[dim]Please make sure you have an existing DM conversation with this user.[/dim]")
                context.close()
                return []

            console.print(f"[green]✓ Opened conversation with @{username}[/green]")
            page.wait_for_timeout(2000)

            # Now scroll to load all messages - this will trigger GraphQL fetches
            console.print(f"[cyan]🔄 Loading messages and fetching shared reels...[/cyan]")
            for _ in range(20):
                page.mouse.wheel(0, 5000)
                page.wait_for_timeout(300)
            for _ in range(40):
                page.mouse.wheel(0, -3000)
                page.wait_for_timeout(400)

            page.wait_for_timeout(5000)

            console.print(f"[dim]  Captured {len(graphql_responses)} GraphQL responses[/dim]")

            # Parse the captured GraphQL responses
            collected_links_with_timestamps = self._parse_graphql_responses(graphql_responses, page)

            # Also use JS fallback
            try:
                found_via_js = page.evaluate("""() => {
                    const urls = new Set();
                    const validUrlRegex = /https?:\\/\\/(www\\.)?instagram\\.com\\/(reel|p|tv|reels)\\/[A-Za-z0-9_-]+/g;

                    document.querySelectorAll('a').forEach(a => {
                        if (a.href) urls.add(a.href);
                    });

                    document.querySelectorAll('[data-lynx-uri]').forEach(el => {
                        const uri = el.getAttribute('data-lynx-uri');
                        if (uri) urls.add(uri);
                    });

                    document.querySelectorAll('*').forEach(el => {
                        const html = el.innerHTML || '';
                        const matches = html.match(validUrlRegex);
                        if (matches) {
                            matches.forEach(m => urls.add(m));
                        }
                    });

                    return Array.from(urls);
                }""")

                for url in found_via_js:
                    if url:
                        clean_url = self._clean_url(url)
                        if self._is_valid_reel_url(clean_url):
                            collected_links_with_timestamps.append((clean_url, None))
                            console.print(f"[dim]    ✓ Found URL (JS fallback): {clean_url}[/dim]")
            except Exception as e:
                console.print(f"[dim]JS extraction error: {e}[/dim]")

            # Direct API call fallback
            if len(collected_links_with_timestamps) < 3:
                try:
                    thread_id = page.url.split('/direct/t/')[-1].rstrip('/')
                    console.print(f"[cyan]  Trying direct API call for thread: {thread_id}[/cyan]")
                    api_result = page.evaluate(f"""async () => {{
                        try {{
                            const resp = await fetch('https://www.instagram.com/api/v1/direct_v2/threads/{thread_id}/', {{
                                headers: {{
                                    'X-IG-App-ID': '936619743392459',
                                    'X-Requested-With': 'XMLHttpRequest',
                                }},
                                credentials: 'include'
                            }});
                            const data = await resp.json();
                            return {{success: true, data: data}};
                        }} catch (e) {{
                            return {{success: false, error: e.message}};
                        }}
                    }}""")

                    if api_result.get('success'):
                        data = api_result['data']
                        thread = data.get('thread', {})
                        items = thread.get('items', [])
                        for item in items:
                            if item.get('item_type') == 'media_share' or 'media' in item:
                                media = item.get('media', {})
                                if media:
                                    code = media.get('code')
                                    if code:
                                        url = f"https://www.instagram.com/reel/{code}/"
                                        clean_url = self._clean_url(url)
                                        if not any(c[0] == clean_url for c in collected_links_with_timestamps):
                                            collected_links_with_timestamps.append((clean_url, None))
                                            console.print(f"[dim]    ✓ Found URL (API): {clean_url}[/dim]")
                except Exception as e:
                    console.print(f"[dim]Direct API call failed: {e}[/dim]")

            console.print(f"[green]Collected {len(collected_links_with_timestamps)} potential reel URLs.[/green]")

            if not collected_links_with_timestamps:
                console.print("[yellow]No reel/post links found in this conversation.[/yellow]")
                context.close()
                return []

            # Filter by time window
            filtered_links = []
            for reel_url, link_timestamp in collected_links_with_timestamps:
                if link_timestamp and (datetime.now() - link_timestamp).total_seconds() / 3600 > hours:
                    console.print(f"[dim]  Skipping {reel_url} (too old: {link_timestamp}).[/dim]")
                    continue
                filtered_links.append((reel_url, link_timestamp))

            if not filtered_links:
                console.print("[yellow]No reel/post links within the time window.[/yellow]")
                context.close()
                return []

            # Process each collected link to get full metadata and apply duration filter
            for idx, (reel_url, link_timestamp) in enumerate(filtered_links):
                console.print(f"[cyan]📝 Fetching metadata for reel {idx+1}/{len(filtered_links)}...[/cyan]")
                try:
                    author, caption, views, likes, duration = self.browser_scraper._extract_reel_metadata(page, reel_url)

                    if max_duration > 0 and duration > 0 and duration > max_duration:
                        console.print(f"[yellow]    Skipping (duration {duration:.0f}s > {max_duration}s).[/yellow]")
                        continue

                    reel = Reel(
                        id=Path(reel_url).name,
                        url=reel_url,
                        caption=caption,
                        author=author if author else "dm_sender",
                        views=views,
                        likes=likes,
                        duration=duration
                    )
                    reels.append(reel)
                    console.print(f"[green]    ✓ Added: {reel.url} (Views: {views}, Likes: {likes}, Duration: {duration:.0f}s)[/green]")

                except Exception as e:
                    console.print(f"[yellow]    (skipped metadata for {reel_url}: {e})[/yellow]")

            context.close()
        return reels