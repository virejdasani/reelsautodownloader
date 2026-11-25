"""
Debug script - Try different approaches to open the conversation
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import re
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

    print("Navigating to DMs...")
    page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
    page.wait_for_timeout(8000)

    if "accounts/login" in page.url:
        print("Need login - waiting for manual login...")
        for _ in range(60):
            if "accounts/login" not in page.url:
                break
            page.wait_for_timeout(1000)
        page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

    print("Inbox loaded. Looking for ALL conversation links...")
    page.wait_for_timeout(3000)

    # Let's look at ALL conversation elements
    print("\n--- All conversation-like elements ---")

    # Try various selectors for conversation items
    selectors = [
        "a[href*='/direct/t/']",
        "div[role='listitem']",
        "div[data-testid='conversation-item']",
        "div[role='button'][tabindex='0']",
        "a[href*='direct/inbox']",
    ]

    for selector in selectors:
        elements = page.locator(selector).all()
        print(f"\nSelector: {selector} - Found {len(elements)} elements")
        for i, el in enumerate(elements[:5]):
            try:
                text = el.inner_text()[:200]
                href = el.get_attribute("href") or ""
                classes = el.get_attribute("class") or ""
                print(f"  [{i}] href: {href}")
                print(f"      text: {text}")
                print(f"      class: {classes[:100]}")
            except:
                pass

    # Also try to get the full conversation list area HTML
    print("\n--- Full inbox area HTML ---")
    inbox_area = page.locator("div[role='region'], main, nav").first
    if inbox_area.count() > 0:
        html = inbox_area.inner_html()[:10000]
        print(html)

    # Now try clicking the FIRST conversation that looks clickable
    print("\n--- Trying to click first conversation ---")
    all_links = page.locator("a[href*='/direct/t/']").all()
    if all_links:
        for link in all_links[:3]:
            try:
                href = link.get_attribute("href") or ""
                text = link.inner_text()[:100]
                print(f"Trying: {href} - {text}")
                link.click()
                page.wait_for_timeout(5000)

                # Check if we're now in a conversation
                new_url = page.url
                print(f"New URL: {new_url}")

                if '/direct/t/' in new_url:
                    print("SUCCESS - In conversation!")
                    break
                else:
                    print("Still in inbox, trying next...")
                    page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
            except Exception as e:
                print(f"Error: {e}")
                page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
    else:
        print("No direct/t/ links found")

    context.close()