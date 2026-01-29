from harvester.base import BaseHarvester
import time

class DistrigalHarvester(BaseHarvester):
    def __init__(self):
        super().__init__(supplier_code="distrigal")
        self.base_url = "https://www.distrigalcatalogos.com"

    def login(self):
        page = self.browser_engine.get_page()
        print(f"[{self.supplier_code}] Navigating to login...")
        page.goto(f"{self.base_url}/login/")
        
        # Check if already logged in logic could go here
        
        print(f"[{self.supplier_code}] Injecting credentials...")
        # Note: In production, fetch these from DB or Config
        page.fill("input[name='log']", "blanca")
        page.fill("input[name='pwd']", "AlmacenBlanca30")
        page.click("input[type='submit']")
        
        page.wait_for_load_state('networkidle')
        print(f"[{self.supplier_code}] Login submitted.")

    def extract_products(self):
        page = self.browser_engine.get_page()
        print(f"[{self.supplier_code}] Starting extraction...")
        
        # Go to store (Example URL, might need adjustment)
        page.goto(f"{self.base_url}/tienda/")
        self.browser_engine.random_sleep()
        
        products = page.query_selector_all(".product")
        print(f"[{self.supplier_code}] Found {len(products)} products on current page.")

        for p in products:
            try:
                name_el = p.query_selector("h2")
                price_el = p.query_selector(".price")
                img_el = p.query_selector("img")
                
                if name_el and price_el:
                    name = name_el.inner_text()
                    price_txt = price_el.inner_text()
                    
                    # Basic cleaning
                    price_val = float(price_txt.replace('€','').replace(',','.').strip())
                    
                    # Image URL
                    img_src = img_el.get_attribute("src") if img_el else None
                    
                    item = {
                        "name": name,
                        "cost_price": price_val,
                        "sku_supplier": f"DIST-{abs(hash(name))}", # Simple fallback SKU
                        "image_url": img_src,
                        "raw_data": {"original_price_text": price_txt}
                    }
                    self.results.append(item)
            except Exception as e:
                print(f"Error parsing product: {e}")

        print(f"[{self.supplier_code}] Extracted {len(self.results)} total items.")
