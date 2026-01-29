import asyncio
import re
from playwright.async_api import async_playwright
from datetime import datetime
import json
from pathlib import Path

# Paths
ENGINE_ROOT = Path(__file__).parent.parent.parent
DATA_EXPORTS = ENGINE_ROOT / "data" / "exports"
DATA_EXPORTS.mkdir(parents=True, exist_ok=True)

class GenericScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        # Stealth
        await self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.page = await self.context.new_page()

    async def stop(self):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()

    async def login(self, login_url, username, password):
        """
        Heuristic login: finds user/pass inputs and submit button.
        """
        print(f"🔐 Attempting login at {login_url}")
        try:
            await self.page.goto(login_url, timeout=60000)
            await self.page.wait_for_load_state('domcontentloaded')

            # Handle cookies if simple
            try:
                await self.page.click("button:has-text('Accept')", timeout=2000)
                await self.page.click("button:has-text('Aceptar')", timeout=2000)
            except: pass

            # Find fields
            # Username: type=email, name=user, mail, login, etc.
            user_selectors = [
                'input[type="email"]', 
                'input[name*="user"]', 
                'input[name*="mail"]', 
                'input[name*="login"]',
                'input[id*="user"]',
                'input[id*="mail"]'
            ]
            
            pass_selectors = [
                'input[type="password"]',
                'input[name*="pass"]',
                'input[id*="pass"]'
            ]

            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Login")',
                'button:has-text("Log in")',
                'button:has-text("Sign in")',
                'button:has-text("Entrar")',
                'button:has-text("Acceder")'
            ]

            # Fill User
            filled_user = False
            for sel in user_selectors:
                if await self.page.locator(sel).first.is_visible():
                    await self.page.fill(sel, username)
                    filled_user = True
                    break
            
            if not filled_user:
                print("❌ Could not find username field")
                return False

            # Fill Pass
            filled_pass = False
            for sel in pass_selectors:
                if await self.page.locator(sel).first.is_visible():
                    await self.page.fill(sel, password)
                    filled_pass = True
                    break

            if not filled_pass:
                print("❌ Could not find password field")
                return False

            # Submit
            clicked = False
            for sel in submit_selectors:
                if await self.page.locator(sel).first.is_visible():
                    await self.page.click(sel)
                    clicked = True
                    break
            
            if not clicked:
                # Try pressing Enter
                await self.page.keyboard.press('Enter')

            await self.page.wait_for_load_state('networkidle', timeout=30000)
            print("✅ Login action performed (success not guaranteed, proceeding)")
            return True

        except Exception as e:
            print(f"❌ Login Error: {e}")
            return False

    async def extract_products_heuristic(self):
        """
        Extracts products from the current page using DOM heuristics.
        Looks for containers with: Image + Link + Price.
        """
        print("🔍 Analyzing DOM for products...")
        
        # JS Heuristic
        products = await self.page.evaluate("""() => {
            const results = [];
            const debug = [];
            
            // Helper to clean price
            const getPrice = (txt) => {
                const match = txt.match(/(\\d+[\\.,]\\d+)/);
                return match ? match[0] : null;
            };

            // 1. Find all elements properly structured
            // Strategies:
            // A. Common class names
            // B. Schema.org (ItemScope) - TODO
            // C. Visual proximity (Container has Img, Link, Price-like text)

            // Let's use Strategy C (Container)
            // We iterate all '<a>' tags or '<div>' that look like cards
            
            const potentialCards = document.querySelectorAll('article, li, div[class*="product"], div[class*="item"], div[class*="card"]');
            
            potentialCards.forEach(card => {
                // Ignore huge containers
                if (card.offsetHeight > 1000 || card.offsetWidth > 600) return;
                if (card.offsetHeight < 100 || card.offsetWidth < 100) return;

                const linkEl = card.querySelector('a');
                if (!linkEl) return;
                
                const imgEl = card.querySelector('img');
                if (!imgEl) return;
                
                // Price text search in card
                const text = card.innerText;
                if (!text.match(/\\d+([.,]\\d+)?\\s*[€$£]/) && !text.match(/[€$£]\\s*\\d+/)) return; // Must have price symbol
                
                // Extract details
                const priceMatch = text.match(/(\\d+([.,]\\d+)?)\\s*[€$£]/) || text.match(/[€$£]\\s*(\\d+([.,]\\d+)?)/);
                const price = priceMatch ? priceMatch[0] : '0.00';
                
                const titleEl = card.querySelector('h1, h2, h3, h4, .title, .name, [class*="title"], [class*="name"]');
                const title = titleEl ? titleEl.innerText.trim() : (imgEl.alt || linkEl.innerText.trim());
                
                if (title && price) {
                    // Check duplications
                    const exists = results.find(r => r.url === linkEl.href);
                    if (!exists) {
                        results.push({
                            name: title,
                            price: price,
                            image: imgEl.src || imgEl.dataset.src,
                            url: linkEl.href,
                            sku: 'GEN-' + Math.random().toString(36).substr(2, 9).toUpperCase()
                        });
                    }
                }
            });
            
            return results;
        }""")
        
        print(f"📦 Found {len(products)} potential products on current page.")
        return products

    async def scrape_site(self, target_url, login_url=None, username=None, password=None, max_pages=3):
        await self.start()
        try:
            # Login if needed
            if login_url and username and password:
                await self.login(login_url, username, password)
            
            # Go to target
            print(f"🚀 Navigating to {target_url}")
            await self.page.goto(target_url, timeout=60000)
            
            all_products = []
            pages_scanned = 0
            
            while pages_scanned < max_pages:
                # Scroll for lazy loading
                for _ in range(3):
                    await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                    await asyncio.sleep(1)
                
                products = await self.extract_products_heuristic()
                all_products.extend(products)
                
                pages_scanned += 1
                
                # Try next page
                # Heuristic for next button: "Next", ">", "Siguiente", or aria-label="Next"
                next_btn = await self.page.evaluate_handle("""() => {
                    const candidates = Array.from(document.querySelectorAll('a, button'));
                    return candidates.find(el => {
                        const t = el.innerText.toLowerCase();
                        return (t.includes('next') || t.includes('siguiente') || t === '>') && el.offsetParent !== null;
                    });
                }""")
                
                if next_btn and await next_btn.is_visible():
                    print("➡️ Clicking Next Page...")
                    await next_btn.click()
                    await self.page.wait_for_load_state('networkidle', timeout=10000)
                else:
                    print("⏹ No next page found or limit reached.")
                    break

            # Remove duplicates
            unique = {p['url']: p for p in all_products}.values()
            return list(unique)

        finally:
            await self.stop()

async def run_analysis(url, user=None, password=None):
    scraper = GenericScraper(headless=False) # Show browser for "Wow" factor if local, or headless=True
    # Since server is background, headless=True is safer usually, but user might want to see. 
    # Let's stick to headless=True for stability unless specified. 
    # Actually user said "make it work well". Headless is better for stability on server.
    scraper.headless = True 
    
    # Heuristic: if credentials provided but no login_url, assume login at /login or main page redirects
    login_url = None
    if user and password:
        # Try to guess login URL or just go to base URL and hope for redirect/login button
        # Simple heuristic: navigate to base domain + /login
        base_domain = "/".join(url.split("/")[:3])
        login_url = f"{base_domain}/login" 
        # But wait, maybe the user expects us to find the login button on the home page?
        # For now, let's just visit the target_url first. If it redirects to login, we handle it there? 
        # The logic in scrape_site accepts login_url separately.
        # Let's use the provided URL as the starting point. If they provide credentials, we might need a separate "Login URL" field in UI?
        # User said "providing web page and credentials".
        # Let's assume the provided URL is the shop page. If we need to login, we usually need a specific login page.
        # I'll update the UI to ask for "Login URL" optionally, or just try to find it.
        pass

    results = await scraper.scrape_site(
        target_url=url, 
        login_url=login_url, # Might be wrong if not explicit
        username=user, 
        password=password
    )
    
    # Save CSV
    import pandas as pd
    if results:
        df = pd.DataFrame(results)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ScrapeMaster_Export_{ts}.csv"
        file_path = DATA_EXPORTS / filename
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        return {
            "success": True,
            "count": len(results),
            "file": str(file_path),
            "download_url": f"/files/exports/{filename}",
            "data": results[:50] # Preview
        }
    else:
        return {"success": False, "count": 0, "message": "No functional products found."}
