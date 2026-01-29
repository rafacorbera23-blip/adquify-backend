
import asyncio
from playwright.async_api import async_playwright

async def debug_sklum():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        url = "https://www.sklum.com/es/633-comprar-sofas"
        print(f"Navigating to {url}...")
        await page.goto(url, timeout=60000)
        
        # Check title
        print(f"Page Title: {await page.title()}")
        
        # Check Cookie Banner
        cookie_btn = await page.query_selector("button:has-text('Aceptar')")
        if cookie_btn:
            print("Found cookie button. Clicking...")
            await cookie_btn.click()
        else:
            print("Cookie button not found (might be accepted or different selector).")
            
        # Check Products
        products = await page.query_selector_all(".c-product-card, .product-miniature, article")
        print(f"Initial product count: {len(products)}")
        
        if len(products) == 0:
            print("DEBUG: Dumping page content snippet...")
            content = await page.content()
            print(content[:1000])
        
        # Check Load More Button logic
        load_more_selectors = [
            '.js-next-page', 
            'a.load-more', 
            'button.load-more',
            'button[class*="load-more"]',
            '#js-product-list-bottom a'
        ]
        
        found_btn = False
        for sel in load_more_selectors:
            btn = await page.query_selector(sel)
            if btn:
                print(f"Found 'Load More' button with selector: {sel}")
                is_visible = await btn.is_visible()
                print(f"  Is visible: {is_visible}")
                found_btn = True
                
        if not found_btn:
            print("No 'Load More' button found with current selectors.")
            
            # Identify what IS there at the bottom
            print("Checking bottom of page structure...")
            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_sklum())
