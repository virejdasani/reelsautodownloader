"""
Test script with detailed debug output for GraphQL parsing
"""

from src.dm_downloader import InstagramDMReelsDownloader
from src.downloader import VideoDownloader
from playwright.sync_api import sync_playwright
from pathlib import Path
from datetime import datetime
import json

def main():
    thread_url = "https://www.instagram.com/direct/t/110818850307337/"
    hours = 168

    print(f"=== Starting DM Downloader with Debug ===")
    downloader = InstagramDMReelsDownloader(headless=False, session_dir="browser_session")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(downloader.session_dir),
            headless=downloader.headless,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.new_page()

        # Set up GraphQL listener FIRST - before any navigation
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

        # Now scroll to load all messages
        print("Scrolling to load all messages...")
        for _ in range(20):
            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(300)
        for _ in range(40):
            page.mouse.wheel(0, -3000)
            page.wait_for_timeout(400)

        page.wait_for_timeout(5000)

        print(f"\nCaptured {len(graphql_responses)} GraphQL responses total")

        # Now parse the captured GraphQL responses
        collected_links = []
        seen_urls = set()

        for resp in graphql_responses:
            try:
                body = resp.json()
                thread_data = body.get('data', {}).get('get_slide_thread_nullable', {}).get('as_ig_direct_thread', {})

                if not thread_data or 'slide_messages' not in thread_data:
                    # Check all data keys
                    for key, val in body.get('data', {}).items():
                        if isinstance(val, dict) and 'slide_messages' in str(val):
                            thread_data = val
                            print(f"  Found slide_messages in key '{key}'")
                            break

                if thread_data and 'slide_messages' in thread_data:
                    slide_messages = thread_data.get('slide_messages', {}).get('edges', [])
                    print(f"  Found {len(slide_messages)} slide_messages edges in this response")

                    for edge in slide_messages:
                        node = edge.get('node', {})
                        content = node.get('content', {})
                        xma = content.get('xma', {})

                        # DEBUG: print the structure
                        print(f"    Node keys: {list(node.keys())}")
                        print(f"    Content keys: {list(content.keys())}")
                        print(f"    XMA keys: {list(xma.keys())}")
                        print(f"    XMA type: {xma.get('__typename', 'N/A')}")

                        target_url = xma.get('target_url', '')
                        if target_url:
                            print(f"    ✓ Found target_url: {target_url}")
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

                                    collected_links.append((clean_url, link_timestamp))
                                    print(f"    ✓✓ Added: {clean_url}")
                        else:
                            print(f"    ✗ No target_url in xma")
            except Exception as e:
                print(f"Error parsing: {e}")
                import traceback
                traceback.print_exc()
                continue

        print(f"\nCollected {len(collected_links)} reel URLs.")
        context.close()

if __name__ == "__main__":
    main()