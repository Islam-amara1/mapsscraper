"""
Google Maps business scraping logic.
"""

import re
from urllib.parse import quote_plus
from playwright.async_api import Page, Browser, TimeoutError as PlaywrightTimeout
from rich.console import Console

from src.browser import human_delay, random_scroll

console = Console()


class GoogleMapsScraper:
    """Scraper for Google Maps business listings."""
    
    def __init__(self, browser: Browser, page: Page):
        """
        Initialize the scraper.
        
        Args:
            browser: Playwright browser instance
            page: Playwright page instance
        """
        self.browser = browser
        self.page = page
        self.base_url = "https://www.google.com/maps/search/"
    
    async def search(self, query: str, location: str) -> bool:
        """
        Search for businesses on Google Maps.
        
        Args:
            query: Business type to search for (e.g., "restaurants")
            location: Location to search in (e.g., "New York")
            
        Returns:
            bool: True if results were found
        """
        search_term = f"{query} in {location}"
        search_url = f"{self.base_url}{quote_plus(search_term)}"
        
        console.print(f"[cyan]🔍 Searching:[/cyan] {query} in {location}")
        
        try:
            await self.page.goto(search_url, wait_until="domcontentloaded")
            
            # Wait for results container FIRST before trying to scroll it
            await self.page.wait_for_selector('div[role="feed"]', timeout=15000)
            
            # Faster initial scroll to trigger loading
            await self.page.evaluate('''
                const feed = document.querySelector('div[role="feed"]');
                if (feed) feed.scrollTop += 3000;
            ''')
            await human_delay(0.8, 1.2)
            
            console.print("[green]✓ Results loaded[/green]")
            return True
            
        except PlaywrightTimeout:
            console.print("[red]✗ No results found or page timeout[/red]")
            return False
        except Exception as e:
            console.print(f"[red]✗ Search error: {e}[/red]")
            return False
    
    async def scroll_results(self, max_results: int = 50) -> int:
        """
        Scroll through results to load more businesses.
        
        Args:
            max_results: Maximum number of results to load
            
        Returns:
            int: Number of results loaded
        """
        console.print(f"[cyan]📜 Scrolling to load up to {max_results} results...[/cyan]")
        
        try:
            feed = await self.page.query_selector('div[role="feed"]')
            if not feed:
                console.print("[red]✗ Results container not found[/red]")
                return 0
            
            previous_count = 0
            no_change_count = 0
            
            while True:
                # Get current listing count
                listings = await self.page.query_selector_all('a[href*="/maps/place/"]')
                current_count = len(listings)
                
                console.print(f"[yellow]Loading... {current_count} businesses found[/yellow]", end="\r")
                
                # Check if we have enough results
                if current_count >= max_results:
                    console.print(f"\n[green]✓ Reached target: {current_count} businesses[/green]")
                    break
                
                # Check for "end of results" message
                end_message = await self.page.query_selector('span:has-text("You\'ve reached the end")')
                if end_message:
                    console.print(f"\n[green]✓ End of results: {current_count} businesses[/green]")
                    break
                
                # Check if no new results are loading
                if current_count == previous_count:
                    no_change_count += 1
                    if no_change_count >= 3:
                        console.print(f"\n[yellow]⚠ No more results loading: {current_count} businesses[/yellow]")
                        break
                else:
                    no_change_count = 0
                
                previous_count = current_count
                
                # More aggressive scroll to force Google to load more
                await self.page.evaluate('''
                    const feed = document.querySelector('div[role="feed"]');
                    if (feed) {
                        feed.scrollTop += 5000;
                    }
                ''')
                
                # Small hover over the list to trigger active loading
                try:
                    await self.page.hover('div[role="feed"] div[role="article"]:last-child')
                except:
                    pass
                    
                await human_delay(0.6, 1.2)
            
            return current_count
            
        except Exception as e:
            console.print(f"\n[red]✗ Scroll error: {e}[/red]")
            return 0
    
    async def get_listing_urls(self) -> list:
        """
        Extract all business listing URLs from search results.
        
        Returns:
            list: List of unique business URLs
        """
        try:
            links = await self.page.query_selector_all('a[href*="/maps/place/"]')
            
            urls = []
            for link in links:
                href = await link.get_attribute('href')
                if href and href not in urls:
                    urls.append(href)
            
            console.print(f"[green]✓ Found {len(urls)} unique business URLs[/green]")
            return urls
            
        except Exception as e:
            console.print(f"[red]✗ Error extracting URLs: {e}[/red]")
            return []
    
    async def scrape_listing(self, url: str) -> dict:
        """Scrape a single listing efficiently using unified JS extraction."""
        try:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await self.page.wait_for_selector('h1', timeout=7000)
            
            # Unified extraction (Single IPC call for maximum speed)
            data = await self.page.evaluate("""
                () => {
                    const getTxt = (sel) => {
                        const el = Array.isArray(sel) 
                            ? sel.reduce((acc, s) => acc || document.querySelector(s), null)
                            : document.querySelector(sel);
                        return el ? el.innerText.trim() : null;
                    };

                    const getAttr = (sel, attr) => {
                        const el = document.querySelector(sel);
                        return el ? el.getAttribute(attr) : null;
                    };

                    return {
                        name: getTxt(['h1.DUwDvf', 'h1.fontHeadlineLarge', 'h1']),
                        rating: getTxt(['div.F7nice span:first-child', 'span.ceNzKf', 'span.MW4etd']),
                        reviews_count: getTxt(['div.F7nice span:last-child', 'span.UY7F9', 'button[jsaction*="reviews"]']),
                        category: getTxt(['button[jsaction*="category"]', 'span.DkEaL']),
                        address: getTxt(['button[data-item-id="address"]', 'div.rogA2c div.fontBodyMedium']),
                        phone: getTxt(['button[data-item-id*="phone:tel"]', 'a[href^="tel:"]']),
                        website: getAttr('a[data-item-id="authority"]', 'href') || getAttr('a[aria-label*="Website"]', 'href'),
                        hours: getAttr('div[aria-label*="hours"]', 'aria-label') || getTxt('div.t39EBf')
                    };
                }
            """)
            
            # Post-process numeric values
            if data['rating']:
                m = re.search(r'(\d+[.,]\d+|\d+)', data['rating'])
                data['rating'] = float(m.group(1).replace(',', '.')) if m else None
            
            if data['reviews_count']:
                m = re.search(r'(\d+)', data['reviews_count'].replace(',', '').replace('.', ''))
                data['reviews_count'] = int(m.group(1)) if m else None
            
            # Post-process address, phone, hours for formatting if they exist
            if data['address']:
                data['address'] = data['address'].replace('\n', ', ')
            if data['phone']:
                data['phone'] = data['phone'].replace('\n', ' ')
                # If phone was extracted from an href, it might still be 'tel:...'
                if data['phone'].startswith('tel:'):
                    data['phone'] = data['phone'].replace('tel:', '')
            if data['hours']:
                # If hours came from innerText, it might have newlines
                if not data['hours'].startswith('Open') and not data['hours'].startswith('Closed'): # Heuristic to check if it's an aria-label or innerText
                    data['hours'] = data['hours'].replace('\n', ', ')
            
            data['google_maps_url'] = self.page.url
            return data
            
        except Exception as e:
            console.print(f"[red]✗ Error scraping listing: {e}[/red]")
            return {
                'name': None,
                'rating': None,
                'reviews_count': None,
                'category': None,
                'address': None,
                'phone': None,
                'website': None,
                'hours': None,
                'google_maps_url': url
            }
    
    async def scrape_all(self, query: str, location: str, limit: int = 50, no_website_only: bool = False) -> list:
        """
        Scrape all businesses matching the search criteria iteratively.
        """
        results = []
        processed_urls = set()
        
        search_term = f"{query} in {location}"
        search_url = f"{self.base_url}{quote_plus(search_term)}"
        self.current_search_url = search_url # Store for return navigation
        
        # Initial Search
        if not await self.search(query, location):
            return results
        
        # 1. Prepare Background Listing Page (Optimization: No more search reloads!)
        listing_page = await self.page.context.new_page()
        
        console.print(f"\n[cyan]📋 Starting High-Speed Scrape... (Target: {limit} leads)[/cyan]")
        
        total_attempts = 0
        try:
            while len(results) < limit:
                # 1. Scroll Results
                await self.scroll_results(limit * 3)
                
                # 2. Extract current URLs from sidebar
                all_urls = await self.get_listing_urls()
                new_urls = [u for u in all_urls if u not in processed_urls]
                
                if not new_urls:
                    console.print("[red]❌ Exhausted all possible results.[/red]")
                    break
                
                # 3. Process Batch
                for url in new_urls:
                    if len(results) >= limit:
                        break
                    
                    processed_urls.add(url)
                    total_attempts += 1
                    
                    # --- SIDEBAR RADAR (Optimization for No-Website Filter) ---
                    # If user only wants leads without websites, we check the sidebar button before clicking
                    if no_website_only:
                        has_website_indicator = await self.page.evaluate(f"""
                            (targetUrl) => {{
                                const slug = targetUrl.split('/place/')[1]?.split('/')[0];
                                const container = document.querySelector(`a[href*="${{slug}}"]`)?.closest('div[role="article"]');
                                if (!container) return false;
                                return !!(container.querySelector('a[aria-label*="Website"]') || 
                                         container.querySelector('button[aria-label*="Website"]'));
                            }}
                        """, url)
                        
                        if has_website_indicator:
                            continue # Skip without opening second tab!

                    # 4. Deep scrape using the SECOND TAB
                    console.print(f"[cyan]▶ [{len(results)}/{limit} leads][/cyan] Scoping: ", end="")
                    
                    original_page = self.page
                    self.page = listing_page
                    try:
                        data = await self.scrape_listing(url)
                    finally:
                        self.page = original_page
                    
                    if data.get("name"):
                        if no_website_only and data.get("website"):
                            console.print(f"[yellow]⏭ Skipped {data['name']} (Has website)[/yellow]")
                            continue
                        
                        rating = data.get("rating", "N/A")
                        console.print(f"[bold green]✅ {data['name']} ({rating}⭐)[/bold green]")
                        results.append(data)
                    else:
                        console.print(f"[red]⚠ Failed[/red]")
                        
                    await human_delay(0.1, 0.3)
        finally:
            await listing_page.close()

        console.print(f"\n[bold green]🏁 Scrape Complete! Found {len(results)} leads total.[/bold green]")
        return results


if __name__ == "__main__":
    import asyncio
    from src.browser import create_stealth_browser, close_browser
    
    async def test():
        browser, context, page = await create_stealth_browser()
        scraper = GoogleMapsScraper(browser, page)
        
        # Test search
        results = await scraper.scrape_all("coffee shops", "Manhattan, NY", limit=5)
        
        for r in results:
            print(f"\n{r['name']}")
            print(f"  Rating: {r['rating']}")
            print(f"  Address: {r['address']}")
            print(f"  Phone: {r['phone']}")
        
        await close_browser(browser)
    
    asyncio.run(test())
