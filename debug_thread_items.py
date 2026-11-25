"""
Debug - query thread items/messages for media
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import json
import re

session_dir = "browser_session"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(session_dir),
        headless=False,
        viewport={"width": 1280, "height": 800},
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = context.new_page()

    graphql_responses = []

    def handle_graphql_response(response):
        if "graphql" in response.url and response.status == 200:
            graphql_responses.append(response)

    page.on("response", handle_graphql_response)

    print("Navigating to reel thread...")
    page.goto("https://www.instagram.com/direct/t/17846211855252077/", wait_until="domcontentloaded")
    page.wait_for_timeout(8000)

    if "accounts/login" in page.url:
        print("Need login...")
        for _ in range(60):
            if "accounts/login" not in page.url:
                break
            page.wait_for_timeout(1000)
        page.goto("https://www.instagram.com/direct/t/17846211855252077/", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

    print(f"Current URL: {page.url}")
    page.wait_for_timeout(3000)

    # Scroll to load messages
    for _ in range(10):
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(300)

    print(f"Captured {len(graphql_responses)} GraphQL responses during scroll")

    # Try to get JSON body for each
    for j, resp in enumerate(graphql_responses):
        try:
            body = resp.json()
            body_str = json.dumps(body)

            # Search for reel/post URLs
            urls = re.findall(r'https?://www\.instagram\.com/[a-zA-Z0-9/_-]+', body_str)
            reel_urls = [u for u in urls if re.search(r'/(p|reel|tv|reels)/[A-Za-z0-9_-]+', u)]
            if reel_urls:
                print(f"Response {j} FOUND REEL URLs:")
                for u in set(reel_urls):
                    print(f"  {u}")

            # Also search for media IDs, codes, or video info
            if any(kw in body_str.lower() for kw in ['media', 'reel', 'video', 'code', 'instagram.com/p/', 'instagram.com/reel/']):
                with open(f"thread_graphql_{j}.json", "w") as f:
                    json.dump(body, f, indent=2)
                print(f"Response {j} saved (contains media keywords)")
                if isinstance(body, dict) and 'data' in body:
                    print(f"  Data keys: {list(body['data'].keys())}")
        except Exception as e:
            print(f"Response {j} error: {e}")

    # Also try to directly query the thread items API
    print("\n=== Trying direct API call for thread items ===")
    thread_items = page.evaluate("""async () => {
        // Try to fetch thread items directly
        const threadId = "17846211855252077";
        const url = `https://www.instagram.com/api/v1/direct_v2/threads/${threadId}/`;
        try {
            const resp = await fetch(url, {
                headers: {
                    'X-IG-App-ID': '936619743392459',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'include'
            });
            const data = await resp.json();
            return {success: true, data: data, url: url};
        } catch (e) {
            return {success: false, error: e.message};
        }
    }""")

    print(f"Direct API result: {thread_items}")

    context.close()