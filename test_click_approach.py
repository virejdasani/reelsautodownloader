"""
Test script using click approach to extract reels from DM thread.
Following user's suggested approach: scroll up, click 1/3 from left to open reel preview,
copy URL, press Escape, scroll down slightly, repeat.
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import time

session_dir = "browser_session"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(session_dir),
        headless=False,
        viewport={"width": 1280, "height": 800},
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = context.new_page()

    print("Navigating to thread...")
    page.goto("https://www.instagram.com/direct/t/110818850307337/", wait_until="domcontentloaded")
    page.wait_for_timeout(8000)

    if "accounts/login" in page.url:
        print("Please log in manually...")
        input("Press Enter after logging in...")
        page.goto("https://www.instagram.com/direct/t/110818850307337/", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

    # Scroll all the way up to load oldest messages
    print("Scrolling all the way up to load messages...")
    for _ in range(50):
        page.mouse.wheel(0, -3000)
        page.wait_for_timeout(300)
    page.wait_for_timeout(3000)

    collected_urls = []
    seen_urls = set()

    # Get viewport size for click positioning
    viewport = page.viewport_size
    click_x = viewport['width'] // 3  # 1/3 from left
    viewport_height = viewport['height']

    # Starting y position - somewhere in the visible area
    click_y = viewport_height // 2

    # Iteratively click to open reels
    max_iterations = 50  # Safety limit

    for iteration in range(max_iterations):
        print(f"\n--- Iteration {iteration+1}/{max_iterations} ---")

        # Click at 1/3 from left, middle of screen
        page.mouse.click(click_x, click_y)
        page.wait_for_timeout(3000)

        current_url = page.url
        print(f"URL after click: {current_url}")

        # Check if we navigated to a reel page
        clean_url = current_url.split('?')[0]
        is_reel = ('/reel/' in clean_url or '/p/' in clean_url or '/tv/' in clean_url) and clean_url not in seen_urls

        if is_reel and clean_url not in seen_urls:
            seen_urls.add(clean_url)
            collected_urls.append(clean_url)
            print(f"✓ Found reel: {clean_url}")
        else:
            print(f"  Not a new reel URL (already seen or invalid)")

        # Press Escape to go back to DM thread
        page.keyboard.press("Escape")
        page.wait_for_timeout(1500)

        # Scroll slightly down to view more messages
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(1000)

        # Check if we're still in the DM conversation
        if '/direct/t/' not in page.url:
            print("  Lost conversation, stopping.")
            break

        # Check if we've collected enough URLs
        if len(collected_urls) >= 20:
            print(f"Collected {len(collected_urls)} URLs, stopping.")
            break

    print(f"\n{'='*50}")
    print(f"Collected {len(collected_urls)} reel URLs:")
    for u in collected_urls:
        print(f"  {u}")
    print(f"{'='*50}")

    context.close()