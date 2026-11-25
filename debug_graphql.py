"""
Debug - capture GraphQL response bodies
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import json

session_dir = "browser_session"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(session_dir),
        headless=False,
        viewport={"width": 1280, "height": 800},
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = context.new_page()

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

    # Click second attachment (the one that navigates to new thread)
    all_clickable = page.locator("div[role='button'][tabindex='0']").all()
    for i, el in enumerate(all_clickable[:8]):
        try:
            text = el.evaluate("el => (el.innerText || '').toLowerCase()")
            if 'sent an attachment' in text:
                print(f"\nClicking attachment {i+1}...")

                # Use expect_response to capture the GraphQL response
                with page.expect_response(lambda r: "graphql" in r.url and r.status == 200, timeout=10000) as response_info:
                    el.click()
                    page.wait_for_timeout(5000)

                response = response_info.value
                print(f"Response URL: {response.url}")

                # Try to get JSON body
                try:
                    body = response.json()
                    print(f"Response JSON keys: {list(body.keys()) if isinstance(body, dict) else 'not dict'}")

                    # Search for reel/post URLs in the response
                    body_str = json.dumps(body)
                    import re
                    urls = re.findall(r'https?://www\.instagram\.com/[a-zA-Z0-9/_-]+', body_str)
                    reel_urls = [u for u in urls if re.search(r'/(p|reel|tv|reels)/[A-Za-z0-9_-]+', u)]
                    if reel_urls:
                        print(f"FOUND REEL URLs in GraphQL response:")
                        for u in set(reel_urls):
                            print(f"  {u}")

                    # Save full response for inspection
                    with open(f"graphql_response_{i}.json", "w") as f:
                        json.dump(body, f, indent=2)
                    print(f"Saved full response to graphql_response_{i}.json")
                except Exception as e:
                    print(f"Could not parse JSON: {e}")

                # Go back if needed
                if '/direct/t/110818850307337/' not in page.url:
                    page.goto("https://www.instagram.com/direct/t/110818850307337/", wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
                break  # Only click one for now
        except Exception as e:
            print(f"Error: {e}")

    context.close()