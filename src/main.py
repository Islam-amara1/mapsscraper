"""
CLI interface for Google Maps Business Scraper.
"""

import asyncio
import typer
from typing import Optional
from pathlib import Path
import subprocess
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="Google Maps Scraper",
    help="Scrape business data from Google Maps",
    add_completion=False
)
console = Console()


def display_banner():
    """Display application banner."""
    banner = """
╔═══════════════════════════════════════════════════════╗
║         🗺️  Google Maps Business Scraper  🗺️          ║
║                                                       ║
║  Scrape business data from Google Maps with ease!     ║
╚═══════════════════════════════════════════════════════╝
    """
    console.print(banner, style="cyan")


def display_summary(results: list, query: str, location: str):
    """Display a summary table of scraped results."""
    if not results:
        console.print("[yellow]No results to display[/yellow]")
        return
    
    table = Table(title=f"📊 Results: {query} in {location}", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="cyan", max_width=30)
    table.add_column("Rating", style="yellow", width=8)
    table.add_column("Reviews", style="green", width=10)
    table.add_column("Phone", style="blue", width=15)
    table.add_column("Category", style="magenta", max_width=20)
    
    for i, r in enumerate(results, 1):
        table.add_row(
            str(i),
            r.get('name', 'N/A') or 'N/A',
            f"{r.get('rating', 'N/A')}⭐" if r.get('rating') else 'N/A',
            str(r.get('reviews_count', 'N/A') or 'N/A'),
            r.get('phone', 'N/A') or 'N/A',
            r.get('category', 'N/A') or 'N/A'
        )
    
    console.print(table)


async def run_scraper(query: str, location: str, limit: int, headless: bool, no_website: bool = False) -> list:
    """Run the scraper asynchronously."""
    from src.browser import create_stealth_browser, close_browser
    from src.scraper import GoogleMapsScraper
    from src.config import settings

    # Override headless setting if specified
    if headless:
        settings.HEADLESS = True
    
    browser = None
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task(description="Starting browser...", total=None)
            browser, context, page = await create_stealth_browser()
        
        scraper = GoogleMapsScraper(browser, page)
        results = await scraper.scrape_all(query, location, limit, no_website_only=no_website)
        return results
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return []
    finally:
        if browser:
            await close_browser(browser)


def export_results(results: list, query: str, location: str, output_format: str) -> dict:
    """Export results to specified format."""
    from src.exporter import Exporter

    exporter = Exporter()
    
    if output_format == "all":
        return exporter.export_all(results, query, location)
    elif output_format == "csv":
        return {'csv': exporter.to_csv(results, query, location)}
    elif output_format == "json":
        return {'json': exporter.to_json(results, query, location)}
    elif output_format == "excel":
        return {'excel': exporter.to_excel(results, query, location)}
    else:
        console.print(f"[yellow]Unknown format '{output_format}', defaulting to CSV[/yellow]")
        return {'csv': exporter.to_csv(results, query, location)}


@app.command()
def scrape(
    query: str = typer.Argument(..., help="Search query (e.g., 'restaurants', 'coffee shops')"),
    location: str = typer.Option(..., "--location", "-l", help="Location to search in"),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum number of results"),
    output: str = typer.Option("csv", "--output", "-o", help="Output format: csv/json/excel/all"),
    headless: bool = typer.Option(False, "--headless", "-h", help="Run browser in headless mode"),
    no_website: bool = typer.Option(False, "--no-website", help="Only include businesses without a website"),
    expand: bool = typer.Option(False, "--expand", "-e", help="Fetch real neighborhoods from OSM to maximize leads"),
    crm_import: bool = typer.Option(True, "--crm-import/--no-crm-import", help="Auto-import CSV output into local CRM")
):
    """
    Scrape businesses from Google Maps.
    
    Example:
        python -m src.main scrape "restaurants" --location "Istanbul" --limit 20 --output csv
    """
    display_banner()
    
    console.print(Panel(
        f"[cyan]Query:[/cyan] {query}\n"
        f"[cyan]Location:[/cyan] {location}\n"
        f"[cyan]Limit:[/cyan] {limit}\n"
        f"[cyan]Output:[/cyan] {output}\n"
        f"[cyan]Headless:[/cyan] {headless}\n"
        f"[cyan]Filter No Website:[/cyan] {no_website}\n"
        f"[cyan]Expand Search:[/cyan] {expand}",
        title="🔍 Search Parameters"
    ))
    
    if expand:
        from src.geo import fetch_neighborhoods

        # Fetch real districts from Overpass API
        districts = asyncio.run(fetch_neighborhoods(location))
        
        if districts:
            console.print(f"[green]📂 Successfully fetched {len(districts)} real districts![/green]")
            all_results = []
            seen_names = set()
            
            for i, district in enumerate(districts, 1):
                full_loc = f"{district}, {location}"
                console.print(f"\n[bold magenta]📍 Area {i}/{len(districts)}: {district}[/bold magenta]")
                
                # We divide the total limit by number of districts, or just keep going until hit limit
                results = asyncio.run(run_scraper(query, full_loc, limit, headless, no_website))
                
                # Check results and deduplicate
                for r in results:
                    if r['name'] not in seen_names:
                        all_results.append(r)
                        seen_names.add(r['name'])
                
                if len(all_results) >= limit:
                    break
            results = all_results
        else:
            console.print("[yellow]⚠ No sub-districts found. Running standard search.[/yellow]")
            results = asyncio.run(run_scraper(query, location, limit, headless, no_website))
    else:
        # Run standard scraper
        results = asyncio.run(run_scraper(query, location, limit, headless, no_website))
    
    if results:
        # Display summary
        display_summary(results, query, location)
        
        # Export results
        console.print("\n[cyan]Exporting data...[/cyan]")
        exported = export_results(results, query, location, output)
        if crm_import:
            try:
                from src.crm_db import import_from_scraper_csv

                csv_path = exported.get("csv")
                if csv_path:
                    imported_rows = import_from_scraper_csv(csv_path)
                    if imported_rows:
                        console.print(f"[green]📋 CRM: Imported {imported_rows} lead(s).[/green]")
            except Exception as e:
                console.print(f"[yellow]CRM import skipped: {e}[/yellow]")
        
        # Final summary
        console.print(Panel(
            f"[green]✅ Successfully scraped {len(results)} businesses![/green]\n\n"
            f"[cyan]Files saved:[/cyan]\n" + 
            "\n".join([f"  • {k}: {v}" for k, v in exported.items() if v]),
            title="📋 Summary"
        ))
    else:
        console.print("[red]❌ No results found. Try a different query or location.[/red]")


@app.command()
def bulk(
    queries_file: Path = typer.Argument(..., help="Path to file with queries (format: query|location per line)"),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum results per query"),
    output: str = typer.Option("csv", "--output", "-o", help="Output format: csv/json/excel/all"),
    headless: bool = typer.Option(False, "--headless", "-h", help="Run browser in headless mode"),
    no_website: bool = typer.Option(False, "--no-website", help="Only include businesses without a website"),
    crm_import: bool = typer.Option(True, "--crm-import/--no-crm-import", help="Auto-import CSV output into local CRM")
):
    """
    Run bulk scraping from a queries file.
    
    File format (one per line):
        restaurants|Istanbul
        coffee shops|Ankara
        hotels|Izmir
    
    Example:
        python -m src.main bulk queries.txt --limit 20 --output excel
    """
    display_banner()
    
    # Read queries file
    if not queries_file.exists():
        console.print(f"[red]Error: File '{queries_file}' not found[/red]")
        raise typer.Exit(1)
    
    queries = []
    with open(queries_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and '|' in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    queries.append((parts[0].strip(), parts[1].strip()))
    
    if not queries:
        console.print("[red]Error: No valid queries found in file. Use format: query|location[/red]")
        raise typer.Exit(1)
    
    console.print(Panel(
        f"[cyan]Queries file:[/cyan] {queries_file}\n"
        f"[cyan]Total queries:[/cyan] {len(queries)}\n"
        f"[cyan]Limit per query:[/cyan] {limit}\n"
        f"[cyan]Output format:[/cyan] {output}\n"
        f"[cyan]Filter No Website:[/cyan] {no_website}",
        title="📋 Bulk Scraping Parameters"
    ))
    
    # Show queries to process
    console.print("\n[cyan]Queries to process:[/cyan]")
    for i, (q, loc) in enumerate(queries, 1):
        console.print(f"  {i}. {q} in {loc}")
    console.print()
    
    # Process each query
    all_results = []
    
    for i, (query, location) in enumerate(queries, 1):
        console.print(f"\n[bold cyan]━━━ Processing {i}/{len(queries)}: {query} in {location} ━━━[/bold cyan]\n")
        
        results = asyncio.run(run_scraper(query, location, limit, headless, no_website))
        
        if results:
            # Export results for this query
            exported = export_results(results, query, location, output)
            if crm_import:
                try:
                    from src.crm_db import import_from_scraper_csv

                    csv_path = exported.get("csv")
                    if csv_path:
                        import_from_scraper_csv(csv_path)
                except Exception:
                    pass
            all_results.append({
                'query': query,
                'location': location,
                'count': len(results),
                'files': exported
            })
            console.print(f"[green]✅ Scraped {len(results)} results for '{query}'[/green]")
        else:
            all_results.append({
                'query': query,
                'location': location,
                'count': 0,
                'files': {}
            })
            console.print(f"[yellow]⚠ No results for '{query}'[/yellow]")
    
    # Final summary table
    console.print("\n")
    summary_table = Table(title="📊 Bulk Scraping Summary", show_lines=True)
    summary_table.add_column("#", style="dim", width=4)
    summary_table.add_column("Query", style="cyan")
    summary_table.add_column("Location", style="blue")
    summary_table.add_column("Results", style="green")
    summary_table.add_column("Status", style="yellow")
    
    total_results = 0
    for i, r in enumerate(all_results, 1):
        total_results += r['count']
        status = "✅ Success" if r['count'] > 0 else "⚠ No data"
        summary_table.add_row(
            str(i),
            r['query'],
            r['location'],
            str(r['count']),
            status
        )
    
    console.print(summary_table)
    from src.config import settings
    console.print(Panel(
        f"[green]✅ Bulk scraping complete![/green]\n\n"
        f"[cyan]Total queries:[/cyan] {len(queries)}\n"
        f"[cyan]Total businesses scraped:[/cyan] {total_results}\n"
        f"[cyan]Output directory:[/cyan] {settings.OUTPUT_DIR}",
        title="🎉 Final Summary"
    ))


@app.command()
def version():
    """Show version information."""
    console.print(Panel(
        "[cyan]Google Maps Business Scraper[/cyan]\n"
        "[dim]Version: 1.0.0[/dim]\n\n"
        "[yellow]Built with:[/yellow]\n"
        "  • Playwright + Stealth\n"
        "  • Pandas\n"
        "  • Typer + Rich",
        title="ℹ️ About"
    ))


@app.command("crm")
def crm(
    port: int = typer.Option(8501, "--port", help="Streamlit server port"),
):
    """Launch the local CRM frontend (Streamlit)."""
    app_path = Path(__file__).parent.parent / "frontend" / "app.py"
    if not app_path.exists():
        console.print(f"[red]CRM app not found at {app_path}[/red]")
        raise typer.Exit(1)
    console.print(Panel(
        f"[cyan]Launching CRM:[/cyan] python -m streamlit run {app_path} --server.port {port}",
        title="📋 CRM"
    ))
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)],
        check=False,
    )


@app.command("crm-import")
def crm_import_cmd(
    force: bool = typer.Option(False, "--force", help="Reimport CSVs even if previously imported"),
):
    """Import any new scraper CSVs from data/results into the CRM."""
    from src.crm_db import import_new_results

    summary = import_new_results(force=force)
    console.print(Panel(
        f"[green]Imported files:[/green] {summary['files']}\n"
        f"[green]Imported rows:[/green] {summary['rows']}",
        title="📥 CRM Import"
    ))



if __name__ == "__main__":
    app()
