"""
Automated test script for DM Reels Downloader
"""

from src.dm_downloader import InstagramDMReelsDownloader
from src.downloader import VideoDownloader

def main():
    username = "virej"  # Try matching 'virej' in conversation
    hours = 168
    max_duration = 0

    print(f"=== Starting DM Downloader for @{username} ===")
    downloader = InstagramDMReelsDownloader(headless=False, session_dir="browser_session")
    reels = downloader.download_dm_reels(username=username, hours=hours, max_duration=max_duration)

    print(f"\nFound {len(reels)} reels to download.")
    if reels:
        video_downloader = VideoDownloader()
        downloaded_count = 0
        for reel in reels:
            # Need to pass niche_name since download_reel requires it
            if video_downloader.download_reel(reel, niche_name="dm_reels"):
                downloaded_count += 1
        print(f"Successfully downloaded {downloaded_count} reels.")
    else:
        print("No reels were found.")

if __name__ == "__main__":
    main()