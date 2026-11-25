"""
Debug script to explore Instagram DM conversation DOM and find reel URLs.
Runs automatically without manual input - saves results to file.
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import re
import json

session_dir = "browser_session"
output_file = "debug_dm_results.json"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(session_dir),
        headless=False,  # Visible browser so session persists
        viewport={"width": 1280, "height": 800},
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = context.new_page()

    print("Navigating to DMs...")
    page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
    page.wait_for_timeout(8000)

    if "accounts/login" in page.url:
        print("Need login - waiting for manual login in browser...")
        # Wait up to 60 seconds for manual login
        for _ in range(60):
            if "accounts/login" not in page.url:
                break
            page.wait_for_timeout(1000)
        page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

    print("Inbox loaded. Looking for conversation with 'virej'...")
    page.wait_for_timeout(3000)

    # Find and click conversation automatically
    username_lower = "virej"
    username_parts = ["virej"]

    # Try direct conversation links first
    links = page.locator("a[href*='/direct/t/']").all()
    clicked = False
    for link in links:
        try:
            href = link.get_attribute("href") or ""
            text = link.inner_text().lower()
            if any(part in text for part in username_parts) or any(part in href.lower() for part in username_parts):
                print(f"Found conversation link: {href}, clicking...")
                link.click()
                page.wait_for_timeout(5000)
                clicked = True
                break
        except Exception:
            continue

    if not clicked:
        # Try JS approach
        elements = page.evaluate(f"""() => {{
            const results = [];
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            let node;
            while (node = walker.nextNode()) {{
                if (node.textContent.toLowerCase().includes('{username_lower}')) {{
                    let el = node.parentElement;
                    let depth = 0;
                    while (el && el !== document.body && depth < 10) {{
                        if (el.tagName === 'A' || el.tagName === 'BUTTON' ||
                            el.getAttribute('role') === 'button' ||
                            el.getAttribute('role') === 'listitem' ||
                            el.onclick || getComputedStyle(el).cursor === 'pointer') {{
                            results.push({{
                                tag: el.tagName,
                                text: el.innerText.substring(0, 200),
                                className: el.className,
                                href: el.href || '',
                                xpath: getXPath(el)
                            }});
                            break;
                        }}
                        el = el.parentElement;
                        depth++;
                    }}
                }}
            }}
            return results;

            function getXPath(element) {{
                if (element.id) return `//*[@id="${{element.id}}"]`;
                if (element === document.body) return '/html/body';
                let ix = 0;
                let siblings = element.parentNode.childNodes;
                for (let i = 0; i < siblings.length; i++) {{
                    let sibling = siblings[i];
                    if (sibling === element) {{
                        return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                    }}
                    if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {{
                        ix++;
                    }}
                }}
            }}
        }}""")

        for el in elements:
            if 'href' in el and '/direct/t/' in el['href']:
                page.goto(el['href'], wait_until="domcontentloaded")
                page.wait_for_timeout(5000)
                clicked = True
                break
            elif 'xpath' in el:
                try:
                    page.locator(f"xpath={el['xpath']}").first.click()
                    page.wait_for_timeout(5000)
                    clicked = True
                    break
                except Exception:
                    continue

    if not clicked:
        print("Could not find conversation automatically")
        context.close()
        exit(1)

    print("Conversation opened. Scrolling to load messages...")

    # Scroll to load messages - both down and up
    for i in range(15):
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(400)

    for i in range(30):
        page.mouse.wheel(0, -3000)
        page.wait_for_timeout(800)

    print("Exploring DOM for reel URLs...")

    results = {}

    # Method 1: All anchor tags
    print("--- Method 1: All anchor tags with instagram.com ---")
    anchors = page.locator("a[href*='instagram.com']").all()
    anchor_urls = []
    for a in anchors:
        try:
            href = a.get_attribute("href") or ""
            text = a.inner_text()[:100]
            anchor_urls.append({"href": href, "text": text})
        except:
            pass
    results["anchors"] = anchor_urls

    # Method 2: JS deep search
    print("--- Method 2: JS deep search for all URLs ---")
    found = page.evaluate("""() => {
        const urls = new Set();
        const validUrlRegex = /https?:\\/\\/(www\\.)?instagram\\.com\\/(reel|p|tv|reels)\\/[A-Za-z0-9_-]+/;

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

            for (const attr of el.attributes) {
                if (attr.value && validUrlRegex.test(attr.value.split('?')[0])) {
                    urls.add(attr.value.split('?')[0]);
                }
            }
        });

        return Array.from(urls);
    }""")
    results["js_deep_search"] = found

    # Method 3: Look for message containers
    print("--- Method 3: Message containers ---")
    messages = page.locator("div[role='log'] div, div[data-testid='conversation-thread'] div, div[role='listitem']").all()
    message_texts = []
    for i, msg in enumerate(messages[:50]):
        try:
            text = msg.inner_text()[:500]
            if 'instagram.com' in text:
                message_texts.append({"index": i, "text": text})
        except:
            pass
    results["message_containers"] = message_texts

    # Method 4: Check for shared post previews specifically
    print("--- Method 4: Shared post previews ---")
    previews = page.locator("[data-testid*='post'], [data-testid*='reel'], [data-testid*='media'], div[role='article']").all()
    preview_htmls = []
    for i, p in enumerate(previews[:20]):
        try:
            html = p.get_attribute("outerHTML")[:2000]
            preview_htmls.append({"index": i, "html": html})
        except:
            pass
    results["previews"] = preview_htmls

    # Method 5: Check all links in message area
    print("--- Method 5: All links in conversation area ---")
    conv_area = page.locator("div[role='log'], main, div[data-testid='conversation-thread']").first
    conv_links = []
    if conv_area.count() > 0:
        links_in_conv = conv_area.locator("a").all()
        for a in links_in_conv:
            try:
                href = a.get_attribute("href") or ""
                if 'instagram.com' in href:
                    conv_links.append(href)
            except:
                pass
    results["conversation_links"] = conv_links

    # Method 6: Full page HTML
    print("--- Method 6: Full page HTML ---")
    full_html = page.content()
    results["full_html_length"] = len(full_html)
    results["full_html_sample"] = full_html[:50000]

    # Save results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_file}")
    print(f"Found {len(found)} reel/post URLs via JS deep search:")
    for url in found:
        print(f"  {url}")

    context.close()