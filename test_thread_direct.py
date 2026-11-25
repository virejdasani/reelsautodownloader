"""
Test script to scrape reels from a known DM thread URL directly
"""

from src.dm_downloader import InstagramDMReelsDownloader
from src.downloader import VideoDownloader
from playwright.sync_api import sync_playwright
from pathlib import Path
import json

def main():
    thread_url = "https://www.instagram.com/direct/t/110818850307337/"
    hours = 168
    max_duration = 0

    print(f"=== Starting DM Downloader for Thread: {thread_url} ===")
    downloader = InstagramDMReelsDownloader(headless=False, session_dir="browser_session")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(downloader.session_dir),
            headless=downloader.headless,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.new_page()

        # Register GraphQL listener BEFORE navigating to thread
        print("Registering GraphQL listener...")
        graphql_responses = []

        def handle_graphql_response(response):
            if "graphql" in response.url and response.status == 200:
                graphql_responses.append(response)

        page.on("response", handle_graphql_response)

        print(f"Navigating directly to thread...")
        page.goto(thread_url, wait_until="domcontentloaded")
        page.wait_for_timeout(8000)

        if "accounts/login" in page.url:
            print("Please log in manually in the browser...")
            input("Press Enter after logging in...")
            page.goto(thread_url, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

        # Now extract using the method that will use the already-registered listener
        # But we need to trigger more GraphQL by scrolling
        print("Scrolling to load all messages...")
        for _ in range(20):
            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(300)
        for _ in range(40):
            page.mouse.wheel(0, -3000)
            page.wait_for_timeout(400)

        page.wait_for_timeout(5000)

        print(f"Captured {len(graphql_responses)} GraphQL responses")

        # DEBUG: Save all GraphQL responses for inspection
        for i, resp in enumerate(graphql_responses):
            try:
                body = resp.json()
                with open(f"debug_graphql_{i}.json", "w") as f:
                    json.dump(body, f, indent=2)
                print(f"  Saved debug_graphql_{i}.json (keys: {list(body.keys()) if isinstance(body, dict) else 'N/A'})")
                if isinstance(body, dict) and 'data' in body:
                    print(f"    data keys: {list(body['data'].keys())}")
            except Exception as e:
                print(f"  Response {i} error: {e}")

        # Now parse the captured responses
        collected_links_with_timestamps = []
        seen_urls = set()

        for resp in graphql_responses:
            try:
                body = resp.json()
                thread_data = body.get('data', {}).get('get_slide_thread_nullable', {}).get('as_ig_direct_thread', {})

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

                    target_url = xma.get('target_url', '')
                    if target_url:
                        clean_url = downloader._clean_url(target_url)
                        if downloader._is_valid_reel_url(clean_url):
                            if clean_url not in seen_urls:
                                seen_urls.add(clean_url)

                                timestamp_ms = node.get('timestamp_ms', '')
                                link_timestamp = None
                                if timestamp_ms:
                                    try:
                                        link_timestamp = datetime.fromtimestamp(int(timestamp_ms) / 1000)
                                    except:
                                        pass

                                collected_links_with_timestamps.append((clean_url, link_timestamp))
                                print(f"  ✓ Found reel URL: {clean_url}")
            except Exception as e:
                print(f"Error parsing GraphQL: {e}")
                continue

        # Also use JS fallback
        print("Running JS fallback extraction...")
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
            if url and url not in seen_urls:
                clean_url = downloader._clean_url(url)
                if downloader._is_valid_reel_url(clean_url):
                    seen_urls.add(clean_url)
                    collected_links_with_timestamps.append((clean_url, None))
                    print(f"  ✓ Found URL (JS fallback): {clean_url}")

        # Direct API call fallback
        if len(collected_links_with_timestamps) < 3:
            print("Trying direct API call...")
            thread_id = page.url.split('/direct/t/')[-1].rstrip('/')
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
                                clean_url = downloader._clean_url(url)
                                if clean_url not in seen_urls:
                                    seen_urls.add(clean_url)
                                    collected_links_with_timestamps.append((clean_url, None))
                                    print(f"  ✓ Found URL (API): {clean_url}")

        print(f"\nCollected {len(collected_links_with_timestamps)} reel URLs.")
        reels = []

        for idx, (reel_url, link_timestamp) in enumerate(collected_links_with_timestamps):
            print(f"Fetching metadata for reel {idx+1}/{len(collected_links_with_timestamps)}: {reel_url}")
            try:
                author, caption, views, likes, duration = downloader.browser_scraper._extract_reel_metadata(page, reel_url)
                reel = Reel(
                    id=reel_url.split('/')[-2],
                    url=reel_url,
                    caption=caption,
                    author=author if author else "dm_sender",
                    views=views,
                    likes=likes,
                    duration=duration
                )
                reels.append(reel)
                print(f"  ✓ Added: {reel.url} (Views: {views}, Likes: {likes}, Duration: {duration:.0f}s)")
            except Exception as e:
                print(f"  (skipped: {e})")

        context.close()

    print(f"\nFound {len(reels)} valid reels.")
    if reels:
        video_downloader = VideoDownloader()
        downloaded = video_downloader.download_reels(reels, niche="dm_reels")
        print(f"Successfully downloaded {len(downloaded)} reels.")
    else:
        print("No reels were downloaded.")

if __name__ == "__main__":
    from datetime import datetime
    main()