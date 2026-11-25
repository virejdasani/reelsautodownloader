"""
Debug script - Explore conversation DOM AFTER opening it
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
        print("Need login - waiting...")
        for _ in range(60):
            if "accounts/login" not in page.url:
                break
            page.wait_for_timeout(1000)
        page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

    print("Inbox loaded. Clicking conversation with 'virej'...")

    # Click the virej conversation (div[role='button'][tabindex='0'] with 'virej' in text)
    conversations = page.locator("div[role='button'][tabindex='0']").all()
    for conv in conversations:
        try:
            text = conv.inner_text().lower()
            if 'virej' in text:
                print(f"Found: {text[:100]}")
                conv.click()
                page.wait_for_timeout(5000)
                break
        except:
            pass

    print(f"Current URL: {page.url}")

    if '/direct/t/' not in page.url:
        print("Failed to open conversation")
        context.close()
        exit(1)

    print("Conversation opened! Scrolling to load messages...")

    # Scroll to load all messages
    for _ in range(15):
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(400)

    for _ in range(30):
        page.mouse.wheel(0, -3000)
        page.wait_for_timeout(800)

    print("\n=== EXPLORING CONVERSATION DOM ===\n")

    # Get full page HTML
    html = page.content()

    # Search for instagram URLs
    urls = re.findall(r'https?://www\.instagram\.com/[a-zA-Z0-9/_-]+', html)
    reel_urls = [u for u in urls if re.search(r'/(p|reel|tv|reels)/[A-Za-z0-9_-]+', u)]
    print(f"Reel/Post URLs found in full HTML: {len(set(reel_urls))}")
    for u in set(reel_urls):
        print(f"  {u}")

    # Also search for just the path patterns
    paths = re.findall(r'/(p|reel|tv|reels)/[A-Za-z0-9_-]+', html)
    print(f"\nDirect path patterns in HTML: {len(set(paths))}")
    for p in set(paths):
        print(f"  {p}")

    # Check for message elements
    messages = page.locator("div[role='log'] div, div[data-testid='conversation-thread'] div").all()
    print(f"\nMessage-like elements: {len(messages)}")

    # Look at message content
    for i, msg in enumerate(messages[:30]):
        try:
            text = msg.inner_text()[:500]
            if any(kw in text.lower() for kw in ['instagram.com', 'reel', 'post', 'sent an attachment', 'shared']):
                print(f"  Message {i}: {text[:200]}")
        except:
            pass

    # Check for any clickable elements that might be shared posts
    clickable = page.locator("div[role='button'], a, button").all()
    shared_posts = []
    for el in clickable:
        try:
            text = el.inner_text().lower()
            if any(kw in text for kw in ['reel', 'post', 'attachment', 'shared', 'instagram.com/p/', 'instagram.com/reel/']):
                shared_posts.append((el, text[:200]))
        except:
            pass

    print(f"\nPotential shared post elements: {len(shared_posts)}")
    for el, text in shared_posts[:20]:
        try:
            classes = el.get_attribute("class") or ""
            tag = el.evaluate("el => el.tagName")
            print(f"  [{tag}] class: {classes[:100]}")
            print(f"      text: {text}")
        except:
            pass

    # Save full HTML for analysis
    with open("conversation_html.html", "w") as f:
        f.write(html)
    print("\nFull conversation HTML saved to conversation_html.html")

    context.close()