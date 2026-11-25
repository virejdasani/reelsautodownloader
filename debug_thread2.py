"""
Debug the reel thread - deeper inspection
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

    print("Navigating directly to reel thread...")
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
    page.wait_for_timeout(5000)

    # Scroll to load content
    for _ in range(15):
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(300)

    for _ in range(10):
        page.mouse.wheel(0, -3000)
        page.wait_for_timeout(500)

    print("\n=== DEEP EXPLORING ===\n")

    # Check for all data attributes
    data_attrs = page.evaluate("""() => {
        const attrs = {};
        const all = document.querySelectorAll('*');
        all.forEach(el => {
            for (const attr of el.attributes) {
                if (attr.name.startsWith('data-')) {
                    const key = attr.name;
                    if (!attrs[key]) attrs[key] = [];
                    attrs[key].push(attr.value.substring(0, 200));
                }
            }
        });
        return attrs;
    }""")

    print(f"Data attributes found: {len(data_attrs)}")
    for key, values in list(data_attrs.items())[:30]:
        print(f"  {key}: {values[:3]}")

    # Look for React-related props or JSON data
    scripts = page.locator("script[type='application/json'], script[data-js-initial]").all()
    print(f"\nJSON scripts: {len(scripts)}")

    # Try to find the reel URL in any script
    html = page.content()

    # Search for the specific reel pattern in all scripts
    script_contents = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    print(f"\nScript tags: {len(script_contents)}")

    for i, script in enumerate(script_contents[:20]):
        if 'Dfu4sM9MlHC' in script or 'instagram.com/p/' in script or 'instagram.com/reel/' in script:
            print(f"  Script {i} contains reel reference!")
            print(f"  Preview: {script[:500]}")
            print()

    # Also check for window._sharedData or similar
    shared_data = page.evaluate("""() => {
        return window._sharedData || window.__additionalDataLoaded || null;
    }""")
    print(f"window._sharedData: {shared_data}")

    # Check for any instagram.com URLs in the entire page
    all_urls = re.findall(r'https?://[a-zA-Z0-9./_-]+\.instagram\.com/[a-zA-Z0-9/_-]+', html)
    print(f"\nAll instagram.com URLs: {len(all_urls)}")
    for u in set(all_urls)[:50]:
        print(f"  {u}")

    context.close()