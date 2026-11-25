"""
Debug script - Click on the attachment message to reveal the reel
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
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

    print("Navigating to DMs...")
    page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
    page.wait_for_timeout(8000)

    if "accounts/login" in page.url:
        print("Need login - waiting...")
        for _ in range(60):
            if "accounts/login" not in page.url:
                break
            page.wait_for_timeout(1000)
        page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

    print("Clicking conversation with 'virej'...")
    conversations = page.locator("div[role='button'][tabindex='0']").all()
    for conv in conversations:
        try:
            text = conv.inner_text().lower()
            if 'virej' in text and 'sent an attachment' in text:
                print(f"Found: {text[:100]}")
                conv.click()
                page.wait_for_timeout(5000)
                break
        except:
            pass

    print(f"Current URL: {page.url}")

    # Scroll to load messages
    for _ in range(15):
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(400)

    for _ in range(30):
        page.mouse.wheel(0, -3000)
        page.wait_for_timeout(800)

    # Now try to find and CLICK on the attachment message itself
    # The attachment might be a clickable element that opens the reel
    print("\n=== Looking for clickable attachment elements ===")

    # Find elements containing "sent an attachment"
    attachments = page.locator("div:has-text('sent an attachment'), span:has-text('sent an attachment')").all()
    print(f"Found {len(attachments)} 'sent an attachment' elements")

    for i, att in enumerate(attachments):
        try:
            text = att.inner_text()
            print(f"  [{i}] {text[:200]}")

            # Try to click on parent clickable elements
            parent = att.locator("..").first
            parent_classes = parent.get_attribute("class") or ""
            print(f"      Parent classes: {parent_classes[:100]}")

            # Check if parent or nearby element has a link
            links_nearby = att.locator("xpath=ancestor::div[contains(@class, 'x1i10hfl')]//a").all()
            print(f"      Links in parent clickable: {len(links_nearby)}")
            for link in links_nearby:
                href = link.get_attribute("href") or ""
                print(f"        Link: {href}")
        except:
            pass

    # Try clicking the actual message bubble that says "sent an attachment"
    print("\n=== Trying to click attachment message bubbles ===")
    clickable_elements = page.locator("div[role='button'][tabindex='0']").all()
    print(f"Total clickable divs: {len(clickable_elements)}")

    for el in clickable_elements:
        try:
            text = el.inner_text().lower()
            if 'sent an attachment' in text:
                print(f"Clicking attachment message: {text[:100]}")
                el.click()
                page.wait_for_timeout(3000)

                # Check if URL changed or modal opened
                print(f"  New URL: {page.url}")

                # Check for modal or new content
                modals = page.locator("div[role='dialog'], div[aria-modal='true']").all()
                print(f"  Modals opened: {len(modals)}")

                # Go back if needed
                if '/direct/t/' not in page.url:
                    page.goto("https://www.instagram.com/direct/t/110818850307337/", wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
        except Exception as e:
            print(f"  Error: {e}")

    # Check page for reel URLs after interaction
    html = page.content()
    urls = re.findall(r'https?://www\.instagram\.com/[a-zA-Z0-9/_-]+', html)
    reel_urls = [u for u in urls if re.search(r'/(p|reel|tv|reels)/[A-Za-z0-9_-]+', u)]
    print(f"\nReel URLs after interaction: {len(set(reel_urls))}")
    for u in set(reel_urls):
        print(f"  {u}")

    context.close()