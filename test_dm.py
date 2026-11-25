"""
Test script - Non-interactive DM downloader for debugging
"""

from src.dm_downloader import InstagramDMReelsDownloader
from src.downloader import VideoDownloader
from src.manager import ContentManager
from src.niche_config import NicheConfig
from src.reel import Reel
from rich.console import Console

console = Console()

def test_dm_downloader():
    username = "virej"
    hours = 24
    max_duration = 0
    min_views = 0

    console.print(f"\n[cyan]🌐 Launching browser to find reels from @{username} in the last {hours} hours...[/cyan]")

    dm_scraper = InstagramDMReelsDownloader(headless=False, session_dir="browser_session")

    try:
        reels = dm_scraper.download_dm_reels(username=username, hours=hours, max_duration=max_duration)

        if min_views > 0:
            reels = [r for r in reels if r.views >= min_views]
            console.print(f"[cyan]Filtered by min_views >= {min_views:,}: {len(reels)} reels remaining[/cyan]")

        if not reels:
            console.print("[yellow]No reels found matching your criteria.[/yellow]")
            return

        console.print(f"\n[green]Found {len(reels)} reel(s) to process.[/green]")

        # Display results table
        from rich.table import Table
        table = Table(title=f"Reels from DM with @{username}")
        table.add_column("Rank", style="dim", width=6)
        table.add_column("Author", style="magenta")
        table.add_column("Views", style="green", justify="right")
        table.add_column("Likes", style="yellow", justify="right")
        table.add_column("Dur", style="cyan", justify="right")
        table.add_column("Score", style="bold blue", justify="right")
        table.add_column("URL", style="underline cyan")

        for i, r in enumerate(reels, 1):
            table.add_row(
                str(i),
                f"@{r.author}" if r.author else "unknown",
                f"{r.views:,}",
                f"{r.likes:,}",
                f"{r.duration:.0f}s" if r.duration else "?",
                f"{r.virality_score():.1f}",
                r.url
            )
        console.print("\n")
        console.print(table)

        # Download
        downloader = VideoDownloader(base_output_dir="downloads", cookies_from_browser="chrome")
        console.print("[cyan]⬇️ Downloading videos...[/cyan]")
        success_count = 0
        for r in reels:
            console.print(f"Downloading @{r.author} ({r.url})...")
            if downloader.download_reel(r, f"dm_{username}"):
                success_count += 1
            else:
                console.print(f"[yellow]    (Note: Download failed for {r.id}. Metadata saved.)[/yellow]")

        # Save metadata
        config = NicheConfig(name=f"DM_{username}", min_views=min_views, max_duration=max_duration, max_results=len(reels))
        manager = ContentManager(metadata_dir="output")
        ranked = manager.filter_and_rank(reels, config)
        for r in ranked:
            manager.save_metadata(r, f"DM_{username}")

        console.print(f"\n[bold green]✨ Done! Processed {len(reels)} reels ({success_count} downloaded).[/bold green]")
        console.print(f"📁 Videos saved in: [cyan]downloads/dm_{username}/[/cyan]")
        console.print(f"📄 Captions & metadata saved in: [cyan]output/dm_{username}/[/cyan]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dm_downloader()