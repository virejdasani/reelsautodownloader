"""
Debug - capture GraphQL responses for ALL attachments
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

    print("Navigating to conversation...")
    page.goto("https://www.instagram.com/direct/t/110818850307337/", wait_until="domcontentloaded")
    page.wait_for_timeout(8000)

    if "accounts/login" in page.url:
        print("Need login...")
        for _ in range(60):
            if "accounts/login" not in page.url:
                break
            page.wait_for_timeout(1000)
        page.goto("https://www.instagram.com/direct/t/110818850307337/", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

    print(f"Current URL: {page.url}")
    page.wait_for_timeout(3000)

    # Click ALL attachments
    all_clickable = page.locator("div[role='button'][tabindex='0']").all()
    for i, el in enumerate(all_clickable[:10]):
        try:
            text = el.evaluate("el => (el.innerText || '').toLowerCase()")
            if 'sent an attachment' in text:
                print(f"\n=== Clicking attachment {i+1} ===")
                graphql_responses.clear()
                el.click()
                page.wait_for_timeout(5000)

                print(f"URL after click: {page.url}")
                print(f"Captured {len(graphql_responses)} GraphQL responses")

                # Try to get JSON body for each
                for j, resp in enumerate(graphql_responses):
                    try:
                        body = resp.json()
                        body_str = json.dumps(body)

                        # Search for reel/post URLs
                        urls = re.findall(r'https?://www\.instagram\.com/[a-zA-Z0-9/_-]+', body_str)
                        reel_urls = [u for u in urls if re.search(r'/(p|reel|tv|reels)/[A-Za-z0-9_-]+', u)]
                        if reel_urls:
                            print(f"  Response {j} FOUND REEL URLs:")
                            for u in set(reel_urls):
                                print(f"    {u}")

                        # Also search for media IDs or codes
                        if 'media' in body_str.lower() or 'reel' in body_str.lower() or 'video' in body_str.lower() or 'code' in body_str.lower():
                            with open(f"graphql_response_{i}_{j}.json", "w") as f:
                                json.dump(body, f, indent=2)
                            print(f"  Response {j} saved (contains media/reel/video/code)")
                            # Print a snippet
                            print(f"    Keys: {list(body.keys()) if isinstance(body, dict) else 'not dict'}")
                            if isinstance(body, dict) and 'data' in body:
                                print(f"    Data keys: {list(body['data'].keys())}")
                    except Exception as e:
                        print(f"  Response {j} error: {e}")

                # Go back if needed
                if '/direct/t/110818850307337/' not in page.url:
                    page.goto("https://www.instagram.com/direct/t/110818850307337/", wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Error clicking attachment {i+1}: {e}")
            # Try to get back
            try:
                if '/direct/t/110818850307337/' not in page.url:
                    page.goto("https://www.instagram.com/direct/t/110818850307337/", wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
            except:
                pass

    context.close()