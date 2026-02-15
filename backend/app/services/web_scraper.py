"""
Web scraper service using Playwright for JavaScript-heavy sites.
Handles sites like Indeed, LinkedIn that block simple HTTP requests.
"""
import asyncio

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from playwright_stealth import Stealth

from app.core.logging import get_logger

logger = get_logger(__name__)


class WebScraper:
    """
    Headless browser-based web scraper.
    Uses Playwright to fetch content from bot-protected sites.
    """

    def __init__(self):
        """Initialize web scraper."""
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None

    async def fetch_url(self, url: str, timeout: int = 30000) -> str:
        """
        Fetch URL content using multiple fallback strategies.

        Args:
            url: URL to fetch
            timeout: Timeout in milliseconds (default 30s)

        Returns:
            Extracted text content

        Raises:
            Exception: If fetching fails
        """
        logger.info(f"Fetching URL: {url}")

        # Strategy 1: Try Playwright with human-like stealth (best for bot-protected sites)
        try:
            logger.info("Attempting Playwright with human-like behavior...")
            content = await self._fetch_with_playwright(url, timeout)
            if content and len(content) > 200:
                logger.info(f"✓ Playwright fetched {len(content)} characters")
                return content
        except Exception as e:
            logger.warning(f"Playwright fetch failed: {e}")

        # Strategy 2: Try simple HTTP request (for non-protected sites)
        try:
            logger.info("Attempting simple HTTP request...")
            content = await self._fetch_with_http(url)
            if content and len(content) > 200:
                logger.info(f"✓ HTTP fetched {len(content)} characters")
                return content
        except Exception as e:
            logger.warning(f"HTTP fetch failed: {e}")

        # Strategy 3: Try Jina AI Reader API as last resort
        try:
            logger.info("Attempting Jina AI reader fallback...")
            content = await self._fetch_with_jina(url)
            if content and len(content) > 200:
                logger.info(f"✓ Jina fetched {len(content)} characters")
                return content
        except Exception as e:
            logger.warning(f"Jina fetch failed: {e}")

        raise Exception("All fetch strategies failed. The site may be blocking automated access.")

    async def _fetch_with_jina(self, url: str) -> str:
        """
        Fetch using Jina AI Reader API (free, no API key needed).

        Args:
            url: URL to fetch

        Returns:
            Extracted content
        """
        jina_url = f"https://r.jina.ai/{url}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/plain',
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(jina_url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            return response.text.strip()

    async def _fetch_with_http(self, url: str) -> str:
        """Simple HTTP fetch with good headers."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            # Extract text from HTML if needed
            if '<html' in response.text.lower():
                soup = BeautifulSoup(response.text, 'html.parser')
                for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                    element.decompose()
                return soup.get_text(separator='\n', strip=True)

            return response.text

    async def _fetch_with_playwright(self, url: str, timeout: int) -> str:
        """
        Fetch using Playwright with realistic human behavior simulation.

        Args:
            url: URL to fetch
            timeout: Timeout in milliseconds

        Returns:
            Extracted content
        """
        logger.info(f"Fetching with human-like browser behavior: {url}")

        async with async_playwright() as p:
            # Launch with more realistic settings
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-notifications',
                    '--disable-gpu',
                    '--window-size=1920,1080',
                ]
            )

            try:
                # Create context with full browser fingerprint
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York',
                    screen={'width': 1920, 'height': 1080},
                    device_scale_factor=2,
                    has_touch=False,
                    is_mobile=False,
                    permissions=['geolocation'],
                    geolocation={'latitude': 40.7128, 'longitude': -74.0060},
                    color_scheme='light',
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"macOS"',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1',
                        'DNT': '1',
                    }
                )

                # Create page with stealth techniques
                stealth_instance = Stealth(
                    navigator_languages_override=('en-US', 'en'),
                    navigator_platform_override='MacIntel',
                    navigator_user_agent_override='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                )
                page = await context.new_page()

                # Apply stealth to the page
                await stealth_instance.apply_stealth_async(page)

                # Additional anti-detection measures
                await page.add_init_script("""
                    // Remove webdriver property
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });

                    // Mock plugins
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
                                0: {type: "application/pdf", suffixes: "pdf", description: ""},
                                description: "",
                                filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                                length: 1,
                                name: "Chrome PDF Viewer"
                            }
                        ]
                    });

                    // Mock languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });

                    // Add chrome object
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                        app: {}
                    };

                    // Mock battery API
                    if (!navigator.getBattery) {
                        navigator.getBattery = () => Promise.resolve({
                            charging: true,
                            chargingTime: 0,
                            dischargingTime: Infinity,
                            level: 1,
                            addEventListener: () => {},
                            removeEventListener: () => {},
                            dispatchEvent: () => true
                        });
                    }

                    // Override permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                """)

                logger.info(f"Navigating to {url} with human-like behavior...")

                # Simulate human-like navigation
                # Step 1: Go to the referring domain first (simulate coming from Google)
                if 'indeed.com' in url.lower():
                    logger.info("Simulating referral from Google Search...")
                    await page.goto('https://www.indeed.com/', wait_until='domcontentloaded', timeout=15000)
                    await page.wait_for_timeout(1000 + int(asyncio.get_event_loop().time() * 1000) % 2000)  # Random 1-3s delay

                    # Simulate some mouse movement
                    await page.mouse.move(100, 100)
                    await page.wait_for_timeout(500)
                    await page.mouse.move(300, 400)
                    await page.wait_for_timeout(300)

                # Step 2: Navigate to the actual job page
                response = await page.goto(
                    url,
                    wait_until='domcontentloaded',
                    timeout=timeout
                )

                logger.info(f"Page loaded with status: {response.status if response else 'unknown'}")

                # Step 3: Simulate human reading behavior
                await page.wait_for_timeout(2000)  # Wait for page to settle

                # Scroll down slowly like a human reading
                for i in range(3):
                    scroll_amount = 300 + (i * 200)
                    await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
                    await page.wait_for_timeout(800 + int(asyncio.get_event_loop().time() * 500) % 400)

                # Random mouse movements
                await page.mouse.move(500, 300)
                await page.wait_for_timeout(200)
                await page.mouse.move(800, 600)
                await page.wait_for_timeout(500)

                # Wait for dynamic content
                await page.wait_for_timeout(2000)

                # Extract content based on site
                content = await self._extract_content(page, url)

                if not content or len(content) < 100:
                    raise ValueError("Extracted content too short or empty")

                logger.info(f"Successfully extracted {len(content)} characters")
                return content

            finally:
                await browser.close()

    async def _extract_content(self, page: Page, url: str) -> str:
        """
        Extract content from page based on URL.

        Args:
            page: Playwright page object
            url: URL being scraped

        Returns:
            Extracted text content
        """
        # Indeed-specific extraction
        if 'indeed.com' in url.lower():
            return await self._extract_indeed(page)

        # LinkedIn-specific extraction
        elif 'linkedin.com' in url.lower():
            return await self._extract_linkedin(page)

        # Generic extraction
        else:
            return await self._extract_generic(page)

    async def _extract_indeed(self, page: Page) -> str:
        """
        Extract job description from Indeed.

        Args:
            page: Playwright page

        Returns:
            Job description text
        """
        try:
            # Try multiple selectors
            selectors = [
                '#jobDescriptionText',
                '.jobsearch-jobDescriptionText',
                '[id*="jobDesc"]',
                '.jobsearch-JobComponent-description',
            ]

            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        text = await element.inner_text()
                        if text and len(text) > 100:
                            logger.info(f"Extracted Indeed job description using selector: {selector}")
                            return text.strip()
                except Exception:
                    continue

            # Fallback: get all text
            logger.warning("Using fallback extraction for Indeed")
            body = await page.locator('body').inner_text()
            return body.strip()

        except Exception as e:
            logger.error(f"Failed to extract Indeed content: {e}")
            raise

    async def _extract_linkedin(self, page: Page) -> str:
        """
        Extract job description from LinkedIn.

        Args:
            page: Playwright page

        Returns:
            Job description text
        """
        try:
            selectors = [
                '.show-more-less-html__markup',
                '.description__text',
                '[class*="description"]',
            ]

            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        text = await element.inner_text()
                        if text and len(text) > 100:
                            logger.info(f"Extracted LinkedIn job description using selector: {selector}")
                            return text.strip()
                except Exception:
                    continue

            # Fallback
            logger.warning("Using fallback extraction for LinkedIn")
            body = await page.locator('body').inner_text()
            return body.strip()

        except Exception as e:
            logger.error(f"Failed to extract LinkedIn content: {e}")
            raise

    async def _extract_generic(self, page: Page) -> str:
        """
        Generic content extraction.

        Args:
            page: Playwright page

        Returns:
            Page text content
        """
        try:
            # Try to find main content area
            main_selectors = ['main', 'article', '[role="main"]', '.content', '#content']

            for selector in main_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        text = await element.inner_text()
                        if text and len(text) > 100:
                            return text.strip()
                except Exception:
                    continue

            # Fallback to body
            body = await page.locator('body').inner_text()
            return body.strip()

        except Exception as e:
            logger.error(f"Failed to extract generic content: {e}")
            raise


async def fetch_url_with_browser(url: str) -> str:
    """
    Fetch URL using headless browser.

    Args:
        url: URL to fetch

    Returns:
        Extracted content

    Raises:
        Exception: If fetch fails
    """
    scraper = WebScraper()
    return await scraper.fetch_url(url)


# ── Singleton ──────────────────────────────────────────────────────────
_web_scraper: WebScraper | None = None


def get_web_scraper() -> WebScraper:
    """Return a singleton WebScraper."""
    global _web_scraper
    if _web_scraper is None:
        _web_scraper = WebScraper()
    return _web_scraper
