"""
Debug - capture network requests when clicking attachment
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import json

session_dir = "browser_session"

captured_urls = []

def handle_response(response):
    url = response.url
    if any(keyword in url for keyword in ['graphql', 'media', 'reel', 'post', 'attachment', 'thread']):
        captured_urls.append({
            'url': url,
            'method': response.request.method,
            'status': response.status
        })

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(session_dir),
        headless=False,
        viewport={"width": 1280, "height": 800},
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = context.new_page()

    # Listen for network responses
    page.on("response", handle_response)

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

    # Click first attachment
    all_clickable = page.locator("div[role='button'][tabindex='0']").all()
    for i, el in enumerate(all_clickable[:5]):
        try:
            text = el.evaluate("el => (el.innerText || '').toLowerCase()")
            if 'sent an attachment' in text:
                print(f"\nClicking attachment {i+1}...")
                captured_urls.clear()
                el.click()
                page.wait_for_timeout(5000)

                print(f"URL after click: {page.url}")
                print(f"Captured {len(captured_urls)} relevant requests:")
                for req in captured_urls:
                    print(f"  {req['method']} {req['url']} -> {req['status']}")

                # Try to get response body for graphql requests
                for req in captured_urls:
                    if 'graphql' in req['url'] or 'media' in req['url']:
                        try:
                            # We can't easily get response body in sync API
                            pass
                        except:
                            pass

                # Go back
                page.goto("https://www.instagram.com/direct/t/110818850307337/", wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Error: {e}")

    context.close()