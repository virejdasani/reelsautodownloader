"""
Debug the reel thread
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

    print("Navigating directly to reel thread...")
    page.goto("https://www.instagram.com/direct/t/17846211855252077/", wait_until="domcontentloaded")
    page.wait_for_timeout(5000)

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

    # Scroll to load content
    for _ in range(10):
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(300)

    print("\n=== EXPLORING THREAD DOM ===\n")

    # Look for any reel/post URLs
    found = page.evaluate("""() => {
        const validUrlRegex = /https?:\\/\\/(www\\.)?instagram\\.com\\/(reel|p|tv|reels)\\/[A-Za-z0-9_-]+/;
        const urls = new Set();

        const allElements = document.querySelectorAll('*');
        allElements.forEach(el => {
            const text = el.innerText || el.textContent || '';
            const matches = text.match(/https?:\\/\\/(www\\.)?instagram\\.com\\/(reel|p|tv|reels)\\/[a-zA-Z0-9_-]+/g);
            if (matches) {
                matches.forEach(u => {
                    const clean = u.split('?')[0];
                    if (validUrlRegex.test(clean)) urls.add(clean);
                });
            }
            if (el.href && validUrlRegex.test(el.href.split('?')[0])) {
                urls.add(el.href.split('?')[0]);
            }
        });
        return Array.from(urls);
    }""")

    print(f"Found {len(found)} reel/post URLs:")
    for url in found:
        print(f"  {url}")

    # Check all anchor tags
    print("\n--- All anchor tags ---")
    anchors = page.locator("a[href*='instagram.com']").all()
    for a in anchors:
        try:
            href = a.get_attribute("href") or ""
            text = a.inner_text()[:100]
            if '/p/' in href or '/reel/' in href or '/tv/' in href or '/reels/' in href:
                print(f"  href: {href}")
                print(f"  text: {text}")
        except:
            pass

    # Get full page HTML
    html = page.content()

    # Search for specific patterns
    urls = re.findall(r'https?://www\.instagram\.com/[a-zA-Z0-9/_-]+', html)
    reel_urls = [u for u in urls if re.search(r'/(p|reel|tv|reels)/[A-Za-z0-9_-]+', u)]
    print(f"\nReel/Post URLs in full HTML: {len(set(reel_urls))}")
    for u in set(reel_urls):
        print(f"  {u}")

    context.close()