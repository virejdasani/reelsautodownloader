"""
Test script to extract reels from DOM attributes directly (data-lynx-uri or hrefs)
"""

from playwright.sync_api import sync_playwright
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

    print("Navigating to thread...")
    page.goto("https://www.instagram.com/direct/t/110818850307337/", wait_until="domcontentloaded")
    page.wait_for_timeout(8000)

    # Scroll up and down to load all messages into DOM
    print("Scrolling to load messages...")
    for _ in range(10):
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(300)
    for _ in range(20):
        page.mouse.wheel(0, -3000)
        page.wait_for_timeout(400)

    page.wait_for_timeout(3000)

    # Extract all links / lynx URIs / text from DOM
    urls = page.evaluate("""() => {
        const found = new Set();
        const regex = /https?:\\/\\/(www\\.)?instagram\\.com\\/(reel|p|tv|reels)\\/[A-Za-z0-9_-]+/g;

        // 1. All anchor tags and elements with href
        document.querySelectorAll('a').forEach(a => {
            if (a.href) found.add(a.href);
        });

        // 2. Elements with data attributes or lynx
        document.querySelectorAll('[data-lynx-uri]').forEach(el => {
            const uri = el.getAttribute('data-lynx-uri');
            if (uri) found.add(uri);
        });

        // 3. Search all innerText / innerHTML
        document.querySelectorAll('*').forEach(el => {
            const html = el.innerHTML || '';
            const matches = html.match(regex);
            if (matches) {
                matches.forEach(m => found.add(m));
            }
        });

        return Array.from(found);
    }""")

    print(f"Found {len(urls)} raw URLs:")
    for u in urls:
        clean = u.split('?')[0]
        if re.search(r'/(p|reel|tv|reels)/[A-Za-z0-9_-]+$', clean):
            print(f"  Valid Reel URL: {clean}")

    context.close()
