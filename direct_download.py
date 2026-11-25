"""
Direct reel downloader - Given a reel URL, download it
"""

from src.downloader import VideoDownloader
from src.browser_scraper import InstagramBrowserScraper
from src.reel import Reel
from pathlib import Path
from rich.console import Console

console = Console()

# The reel URL the user mentioned
reel_url = "https://www.instagram.com/p/Dfu4sM9MlHC/"

console.print(f"Downloading reel: {reel_url}")

# Initialize browser scraper
scraper = InstagramBrowserScraper(headless=False, session_dir="browser_session")

# Initialize downloader
downloader = VideoDownloader(base_output_dir="downloads", cookies_from_browser="chrome")

# Extract metadata
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir="browser_session",
        headless=False,
        viewport={"width": 1280, "height": 800},
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = context.new_page()

    # Navigate to the reel
    page.goto(reel_url, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)

    if "accounts/login" in page.url:
        console.print("Need login - waiting...")
        input()
        page.goto(reel_url, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

    # Extract metadata
    author, caption, views, likes, duration = scraper._extract_reel_metadata(page, reel_url)

    console.print(f"Author: {author}")
    console.print(f"Caption: {caption[:200]}")
    console.print(f"Views: {views}")
    console.print(f"Likes: {likes}")
    console.print(f"Duration: {duration}s")

    # Create reel object
    reel = Reel(
        id=Path(reel_url).name,
        url=reel_url,
        caption=caption,
        author=author,
        views=views,
        likes=likes,
        duration=duration
    )

    # Download
    console.print(f"\nDownloading...")
    if downloader.download_reel(reel, "manual_download"):
        console.print("✅ Download successful!")
    else:
        console.print("❌ Download failed")

    context.close()