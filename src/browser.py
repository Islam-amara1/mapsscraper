"""
Stealth browser setup for Google Maps scraping.
Uses Playwright with anti-detection measures.
"""

import asyncio
import random
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# Support both old and new playwright_stealth API
try:
    from playwright_stealth import stealth_async
    USE_NEW_API = False
except ImportError:
    from playwright_stealth import Stealth
    USE_NEW_API = True

from src.config import settings, USER_AGENTS, VIEWPORTS


async def create_stealth_browser() -> tuple[Browser, BrowserContext, Page]:
    """
    Create a stealth browser with anti-detection measures.
    
    Returns:
        tuple: (browser, context, page)
    """
    playwright = await async_playwright().start()
    
    # Launch Chromium with anti-detection args
    browser = await playwright.chromium.launch(
        headless=settings.HEADLESS,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-size=1920,1080",
            "--disable-extensions",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--lang=en-US",
        ]
    )
    
    # Random viewport and user-agent
    viewport = random.choice(VIEWPORTS)
    user_agent = random.choice(USER_AGENTS)
    
    # Create context with realistic settings
    context = await browser.new_context(
        viewport=viewport,
        user_agent=user_agent,
        locale="en-US",
        timezone_id="America/New_York",
        permissions=["geolocation"],
        geolocation={"latitude": 40.7128, "longitude": -74.0060},  # New York
        color_scheme="light",
        device_scale_factor=1,
    )
    
    # Create page
    page = await context.new_page()
    
    # Block unnecessary resources for faster loading
    if settings.BLOCK_IMAGES:
        await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,webp,woff,woff2,ttf,otf}", lambda route: route.abort())
        await page.route("**/maps.googleapis.com/maps/api/js/GeoPhotoService*", lambda route: route.abort())
        await page.route("**/maps.googleapis.com/maps/vt*", lambda route: route.abort())
    
    # Apply playwright-stealth (support both old and new API)
    if USE_NEW_API:
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
    else:
        await stealth_async(page)
    
    # Add additional anti-detection scripts
    await page.add_init_script("""
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Fake plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {
                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                },
                {
                    0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                    description: "Portable Document Format",
                    filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                    length: 1,
                    name: "Chrome PDF Viewer"
                },
                {
                    0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable"},
                    description: "Native Client Executable",
                    filename: "internal-nacl-plugin",
                    length: 1,
                    name: "Native Client"
                }
            ]
        });
        
        // Fake languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'es']
        });
        
        // Fake platform
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32'
        });
        
        // Fake hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8
        });
        
        // Fake device memory
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8
        });
        
        // Override permissions query
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Fake chrome runtime
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
    """)
    
    return browser, context, page


async def human_delay(min_sec: float = None, max_sec: float = None) -> None:
    """
    Sleep for a random duration to mimic human behavior.
    
    Args:
        min_sec: Minimum seconds to wait (default from config)
        max_sec: Maximum seconds to wait (default from config)
    """
    min_sec = min_sec if min_sec is not None else settings.MIN_DELAY
    max_sec = max_sec if max_sec is not None else settings.MAX_DELAY
    
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)


async def random_scroll(page: Page) -> None:
    """
    Scroll down the page randomly to mimic human behavior.
    
    Args:
        page: Playwright page object
    """
    scroll_amount = random.randint(300, 700)
    
    await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
    await human_delay(0.5, 1.5)


async def close_browser(browser: Browser) -> None:
    """
    Safely close the browser.
    
    Args:
        browser: Playwright browser object
    """
    try:
        await browser.close()
    except Exception as e:
        print(f"Warning: Error closing browser: {e}")


if __name__ == "__main__":
    import asyncio
    
    async def test():
        browser, context, page = await create_stealth_browser()
        await page.goto("https://www.google.com/maps")
        await human_delay(3, 5)
        print("✅ Browser working!")
        await close_browser(browser)
    
    asyncio.run(test())
