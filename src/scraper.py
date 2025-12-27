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
            await human_delay(0.5, 1)
            
            # Wait for results container
            await self.page.wait_for_selector('div[role="feed"]', timeout=15000)
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
                
                # Scroll the feed container
                await self.page.evaluate('''
                    const feed = document.querySelector('div[role="feed"]');
                    if (feed) {
                        feed.scrollTop = feed.scrollTop + 1500;
                    }
                ''')
                
                await human_delay(0.3, 0.6)
            
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
        """Scrape a single business listing with improved selectors."""
        try:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await human_delay(0.3, 0.6)
            
            # Wait for main content
            await self.page.wait_for_selector('h1', timeout=8000)
            
            result = {
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
            
            # NAME - multiple selectors
            name_selectors = ['h1.DUwDvf', 'h1.fontHeadlineLarge', 'h1']
            for selector in name_selectors:
                try:
                    el = await self.page.query_selector(selector)
                    if el:
                        result['name'] = (await el.inner_text()).strip()
                        break
                except:
                    continue
            
            # RATING - multiple selectors
            rating_selectors = [
                'div.F7nice span:first-child',
                'span.ceNzKf', 
                'div.fontDisplayLarge',
                'span.fontDisplayLarge',
                'span.MW4etd',
                'div[jsaction*="rating"] span',
            ]
            for selector in rating_selectors:
                try:
                    el = await self.page.query_selector(selector)
                    if el:
                        text = (await el.inner_text()).strip()
                        match = re.search(r'(\d+[.,]\d+|\d+)', text)
                        if match:
                            result['rating'] = float(match.group(1).replace(',', '.'))
                            break
                except:
                    continue
            
            # REVIEWS COUNT
            reviews_selectors = [
                'div.F7nice span:last-child',
                'span.UY7F9',
                'button[jsaction*="reviews"]',
                'span[aria-label*="reviews"]',
            ]
            for selector in reviews_selectors:
                try:
                    el = await self.page.query_selector(selector)
                    if el:
                        text = (await el.inner_text()).strip()
                        # Match numbers with commas or parentheses: (1,234) or 1234
                        clean_text = text.replace('.', '').replace(',', '')
                        match = re.search(r'[\(]?([\d]+)[\)]?', clean_text)
                        if match:
                            result['reviews_count'] = int(match.group(1))
                            break
                except:
                    continue
            
            # CATEGORY
            category_selectors = [
                'button[jsaction*="category"]',
                'span.DkEaL',
                'button.DkEaL',
            ]
            for selector in category_selectors:
                try:
                    el = await self.page.query_selector(selector)
                    if el:
                        result['category'] = (await el.inner_text()).strip()
                        break
                except:
                    continue
            
            # ADDRESS - look for address button/div
            address_selectors = [
                'button[data-item-id="address"]',
                'button[data-item-id*="address"] div.fontBodyMedium',
                'div[data-item-id="address"]',
                'button[aria-label*="Address"]',
                'div.rogA2c div.fontBodyMedium',
            ]
            for selector in address_selectors:
                try:
                    el = await self.page.query_selector(selector)
                    if el:
                        text = (await el.inner_text()).strip()
                        if text and len(text) > 5:
                            result['address'] = text.replace('\n', ', ')
                            break
                except:
                    continue
            
            # PHONE
            phone_selectors = [
                'button[data-item-id*="phone:tel"]',
                'button[data-item-id*="phone"] div.fontBodyMedium',
                'button[aria-label*="Phone"]',
                'a[href^="tel:"]',
            ]
            for selector in phone_selectors:
                try:
                    el = await self.page.query_selector(selector)
                    if el:
                        text = (await el.inner_text()).strip()
                        if text:
                            result['phone'] = text.replace('\n', ' ')
                            break
                except:
                    continue
            
            # If phone still None, try href
            if not result['phone']:
                try:
                    el = await self.page.query_selector('a[href^="tel:"]')
                    if el:
                        href = await el.get_attribute('href')
                        if href:
                            result['phone'] = href.replace('tel:', '')
                except:
                    pass
            
            # WEBSITE
            website_selectors = [
                'a[data-item-id="authority"]',
                'a[data-item-id*="authority"]',
                'a[aria-label*="Website"]',
                'button[data-item-id*="website"]',
            ]
            for selector in website_selectors:
                try:
                    el = await self.page.query_selector(selector)
                    if el:
                        href = await el.get_attribute('href')
                        if href:
                            result['website'] = href
                            break
                except:
                    continue
            
            # HOURS
            hours_selectors = [
                'div[aria-label*="hours"]',
                'div[aria-label*="Hours"]',
                'button[data-item-id*="oh"]',
                'div.t39EBf',
            ]
            for selector in hours_selectors:
                try:
                    el = await self.page.query_selector(selector)
                    if el:
                        aria_label = await el.get_attribute('aria-label')
                        if aria_label:
                            result['hours'] = aria_label
                            break
                        else:
                            text = (await el.inner_text()).strip()
                            if text:
                                result['hours'] = text.replace('\n', ', ')
                                break
                except:
                    continue
            
            # Update URL to current (in case of redirects)
            result['google_maps_url'] = self.page.url
            
            return result
            
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
    
    async def scrape_all(self, query: str, location: str, limit: int = 50) -> list:
        """
        Scrape all businesses matching the search criteria.
        
        Args:
            query: Business type to search for
            location: Location to search in
            limit: Maximum number of businesses to scrape
            
        Returns:
            list: List of business data dictionaries
        """
        results = []
        
        # Search for businesses
        if not await self.search(query, location):
            return results
        
        # Scroll to load more results
        await self.scroll_results(limit)
        
        # Get listing URLs
        urls = await self.get_listing_urls()
        
        if not urls:
            console.print("[red]✗ No listings found to scrape[/red]")
            return results
        
        # Limit the URLs to scrape
        urls_to_scrape = urls[:limit]
        console.print(f"\n[cyan]📋 Scraping {len(urls_to_scrape)} businesses...[/cyan]\n")
        
        # Scrape each listing
        for i, url in enumerate(urls_to_scrape, 1):
            console.print(f"[dim]({i}/{len(urls_to_scrape)})[/dim] ", end="")
            
            data = await self.scrape_listing(url)
            
            if data.get("name"):
                rating = data.get("rating", "N/A")
                console.print(f"[green]✅ {data['name']} ({rating}⭐)[/green]")
                results.append(data)
            else:
                console.print(f"[yellow]⚠ Could not scrape listing[/yellow]")
            
            # Human delay between scrapes
            await human_delay()
        
        console.print(f"\n[green]✓ Successfully scraped {len(results)} businesses[/green]")
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
