from .base_scraper_agent import BaseScraperAgent, ScrapedProduct
from bs4 import BeautifulSoup
from typing import List

class SklumScraper(BaseScraperAgent):
    """
    Real production scraper for Sklum.
    Target: Office Chairs Category (Initial Test)
    """

    def extract_products(self, soup: BeautifulSoup) -> List[ScrapedProduct]:
        # Handle Cookie Consent via JS injection (more robust)
        if hasattr(self, 'driver'):
            try:
                # Force click MULTIPLE possible buttons
                buttons = self.driver.find_elements("xpath", "//button[contains(., 'Aceptar y cerrar')] | //button[contains(., 'Aceptar')] | //a[contains(., 'Aceptar')]")
                print(f"  🍪 Found {len(buttons)} cookie buttons.")
                for btn in buttons:
                    try:
                        self.driver.execute_script("arguments[0].click();", btn)
                        print("  🍪 Clicked a button!")
                    except: pass
                
                import time
                time.sleep(5) # Wait longer for reload
                
                # Refresh soup
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            except Exception as e:
                print(f"  ⚠️ Cookie handling warning: {e}")

        products = []
        
        # Generic "Loose" Strategy: Find any link that looks like a product
        # Look for <a> tags that contain an image and have a price nearby
        print("  Using Loose Selector Strategy...")
        candidate_links = soup.find_all("a", href=True)
        
        seen_skus = set()
        
        for link in candidate_links:
            try:
                # Must have image inside
                img_tag = link.find("img")
                if not img_tag: continue
                
                # Check ancestry for price (usually price is sibling or parent's sibling)
                # We look at the parent container
                container = link.find_parent("article") or link.find_parent("div", class_=lambda x: x and "product" in x) or link.parent
                
                if not container: continue
                
                # Try to find price in container text
                text_content = container.get_text()
                if "€" not in text_content and "," not in text_content: continue
                
                # Extraction
                name = link.get("title") or img_tag.get("alt") or "Unknown Product"
                if len(name) < 3: continue # garbage name
                
                # Price Extraction (Finding the first number pattern)
                import re
                price_match = re.search(r'(\d+[,.]\d{2})', text_content.replace("€", ""))
                price = float(price_match.group(1).replace(",", ".")) if price_match else 0.0
                
                img_url = img_tag.get("data-src") or img_tag.get("src")
                if not img_url: continue
                
                sku = f"SKL-{hash(name)}"
                if sku in seen_skus: continue
                seen_skus.add(sku)

                p = ScrapedProduct(
                    name=name,
                    price=price,
                    sku_supplier=sku,
                    description="Producto Sklum (Extracción Genérica)", 
                    images=[img_url],
                    specs={"Supplier": "Sklum", "Source": "LooseScraper"}
                )
                products.append(p)
            except Exception:
                continue
                
        return products

    def navigate_next(self, soup: BeautifulSoup) -> str:
        # Check for 'Next' button pagination
        next_btn = soup.select_one("a.next")
        if next_btn:
            return next_btn.get("href")
        return None

if __name__ == "__main__":
    # Test Run
    agent = SklumScraper("https://www.sklum.com/es/")
    try:
        # Target: Specific category "Dining Chairs" tends to be stable
        # Note: Sklum often uses /es/sillas-comedor
        page = agent.fetch_page("https://www.sklum.com/es/sillas-comedor")
        results = agent.extract_products(page)
        
        print(f"✅ Extracted {len(results)} products:")
        for p in results[:5]:
            print(f" - {p.name} (€{p.price})")
    finally:
        agent.close()

if __name__ == "__main__":
    # Test Run
    agent = SklumScraper("https://www.sklum.com/es/")
    try:
        # Target: Office Chairs (Using category ID often works better if path changes) or generic search
        page = agent.fetch_page("https://www.sklum.com/es/sillas")
        results = agent.extract_products(page)
        
        print(f"✅ Extracted {len(results)} products:")
        for p in results[:5]:
            print(f" - {p.name} (€{p.price})")
    finally:
        agent.close()
