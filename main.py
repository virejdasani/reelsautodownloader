"""
Interactive CLI for Instagram Reels Viral Downloader Bot (Browser-Controlled).
"""

from __future__ import annotations

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, Confirm

from src.downloader import VideoDownloader
from src.manager import ContentManager
from src.browser_scraper import InstagramBrowserScraper
from src.niche_config import NicheConfig
from src.reel import Reel

console = Console()


def main():
    console.clear()
    console.print("[bold cyan]╔══════════════════════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║        Instagram Reels Viral Downloader for Shorts       ║[/bold cyan]")
    console.print("[bold cyan]╚══════════════════════════════════════════════════════════╝[/bold cyan]\n")

    # 1. Ask for niche / keyword
    niche_name = Prompt.ask("[bold yellow]Enter your niche or keyword[/bold yellow] (e.g., [cyan]GTA 6[/cyan], [cyan]Gaming News[/cyan], [cyan]Tech[/cyan])", default="GTA 6")

    # 2. Ask for hashtags (comma-separated for multiple)
    default_hashtag = niche_name.lower().replace(" ", "")
    hashtags_input = Prompt.ask(f"[bold yellow]Enter hashtag(s) to search[/bold yellow] (comma-separated for multiple, e.g. 'gta6,gameplay')", default=default_hashtag)
    hashtags = [h.strip().lstrip("#") for h in hashtags_input.split(",") if h.strip()]

    # 3. Ask how many top viral reels to find
    top_n = IntPrompt.ask("[bold yellow]How many top viral reels to find?[/bold yellow]", default=10)

    # 4. Ask for minimum views filter
    min_views = IntPrompt.ask("[bold yellow]Minimum view count filter[/bold yellow]", default=100000)

    # 5. Ask for max video duration filter (for YouTube Shorts compatibility)
    max_duration = IntPrompt.ask("[bold yellow]Max video duration in seconds[/bold yellow] (e.g., [cyan]15[/cyan] for Shorts, [cyan]60[/cyan] for longer, [cyan]0[/cyan] for no limit)", default=15)

    # 6. Ask for AND/OR logic when multiple hashtags
    require_all = True
    if len(hashtags) > 1:
        require_all = Confirm.ask(
            f"[bold yellow]Require videos to have ALL {len(hashtags)} hashtags?[/bold yellow] "
            f"([cyan]y[/cyan]=AND / [cyan]n[/cyan]=OR)",
            default=True
        )

    console.print(f"\n[cyan]🌐 Launching browser to search top Reels for: [/cyan][bold green]{', '.join(f'#{h}' for h in hashtags)}[/bold green]...")
    console.print("[dim]A Chrome browser window will open. If prompted, log into Instagram manually.[/dim]")

    # Initialize browser scraper
    scraper = InstagramBrowserScraper(headless=False)

    try:
        if len(hashtags) == 1:
            raw_reels = scraper.scrape_hashtag_reels(hashtags[0], max_reels=top_n * 2, max_duration=max_duration)
        else:
            raw_reels = scraper.scrape_multiple_hashtags(hashtags, max_reels=top_n * 2, max_duration=max_duration, require_all=require_all)
    except Exception as e:
        console.print(f"[bold red]Browser scraping error:[/bold red] {e}")
        raw_reels = []

    # If scraping returned 0, ask if user wants demo data
    if not raw_reels:
        console.print("[yellow][!] No reels retrieved from the browser feed.[/yellow]")
        use_demo = Confirm.ask("Would you like to load sample demo reels to test the metadata pipeline?", default=True)
        if use_demo:
            raw_reels = [
                Reel(
                    id="gta6_demo_1",
                    url="https://www.instagram.com/reel/C-demo1/",
                    caption=f"Insane {niche_name} gameplay! #{hashtags[0]} #gaming",
                    author="gamer_insider",
                    views=1_450_000,
                    likes=180_000,
                    comments=3_200,
                    duration=14,
                ),
                Reel(
                    id="gta6_demo_2",
                    url="https://www.instagram.com/reel/C-demo2/",
                    caption=f"Top 3 things in latest trailer! #{hashtags[0]}",
                    author="game_central",
                    views=920_000,
                    likes=95_000,
                    comments=1_400,
                    duration=12,
                ),
            ]
        else:
            console.print("[red]Exiting. Try again later or log in with a burner account.[/red]")
            return

    # Filter and rank (double-check duration filter)
    manager = ContentManager(metadata_dir="output")
    config = NicheConfig(name=niche_name, min_views=min_views, max_duration=max_duration, max_results=top_n)
    ranked = manager.filter_and_rank(raw_reels, config)

    if not ranked:
        console.print(f"[red]No reels met the minimum view threshold of {min_views:,} views.[/red]")
        return

    # Display results table
    hashtag_display = ", ".join(f"#{h}" for h in hashtags)
    table = Table(title=f"Top {len(ranked)} Viral Reels for '{niche_name}' ({hashtag_display})")
    table.add_column("Rank", style="dim", width=6)
    table.add_column("Author", style="magenta")
    table.add_column("Views", style="green", justify="right")
    table.add_column("Likes", style="yellow", justify="right")
    table.add_column("Dur", style="cyan", justify="right")
    table.add_column("Score", style="bold blue", justify="right")
    table.add_column("URL", style="underline cyan")

    for i, r in enumerate(ranked, 1):
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

    # Save master metadata index
    console.print(f"\n[cyan]💾 Saving captions and metadata to [bold]output/{niche_name.lower().replace(' ', '_')}/[/bold]...[/cyan]")
    for r in ranked:
        manager.save_metadata(r, niche_name)

    # Ask to download videos
    should_download = Confirm.ask(f"\n[bold yellow]Do you want to download these {len(ranked)} video(s) for YouTube Shorts?[/bold yellow]", default=True)

    if should_download:
        downloader = VideoDownloader(base_output_dir="downloads", cookies_from_browser="chrome")
        console.print("[cyan]⬇️ Downloading videos...[/cyan]")
        success_count = 0
        for r in ranked:
            console.print(f"Downloading @{r.author} ({r.url})...")
            if downloader.download_reel(r, niche_name):
                success_count += 1
            else:
                console.print(f"[yellow]  (Note: Direct video stream download skipped/failed for {r.id}. Metadata & caption saved successfully)[/yellow]")

        console.print(f"\n[bold green]✨ Done! Successfully processed {len(ranked)} reels.[/bold green]")
        console.print(f"📁 Videos saved in: [cyan]downloads/{niche_name.lower().replace(' ', '_')}/[/cyan]")
        console.print(f"📄 Captions & metadata saved in: [cyan]output/{niche_name.lower().replace(' ', '_')}/[/cyan]")
    else:
        console.print(f"\n[bold green]✨ Captions and metadata saved successfully![/bold green]")
        console.print(f"📄 Saved in: [cyan]output/{niche_name.lower().replace(' ', '_')}/[/cyan]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")