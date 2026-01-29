from harvester.base import BaseHarvester
import time
import random

class SklumHarvester(BaseHarvester):

    def __init__(self):
        super().__init__(supplier_code="sklum")
        self.base_url = "https://www.sklum.com/es"
        self.email = "admin@gpacontract.com"
        self.password = "ZcE*-g%35ucZ?rM"
        
        # FULL Category List
        self.categories_to_scrape = [
            ("633", "sofas"),
            ("639", "sofa-2-plazas"),
            ("640", "sofa-3-plazas"),
            ("641", "sofas-modulares-2-plazas"),
            ("642", "sofas-modulares-3-plazas"),
            ("645", "sofa-cama"),
            ("646", "chaise-longues"),
            ("543", "sillas"),
            ("544", "sillas-de-comedor"),
            ("545", "sillas-oficina"),
            ("553", "taburetes-altos"),
            ("649", "sillones"),
            ("542", "mesas"),
            ("555", "mesas-comedor"),
            ("556", "mesas-de-centro"),
            ("620", "aparadores"),
            ("623", "muebles-tv"),
            ("527", "dormitorio"),
            ("560", "camas"),
            ("561", "cabeceros"),
            ("537", "iluminacion"),
            ("566", "lamparas-de-techo"),
            ("538", "decoracion"),
            ("571", "espejos"),
            ("572", "alfombras"),
            ("526", "exterior"),
            ("578", "sofas-de-exterior"),
            ("579", "sillas-de-exterior"),
            ("580", "mesas-de-exterior")
        ]

    def login(self):
        page = self.browser_engine.get_page()
        print(f"[{self.supplier_code}] Navigating to Login...")
        
        # 1. Go to Login Page
        page.goto("https://www.sklum.com/es/iniciar-sesion", timeout=60000)
        self.browser_engine.random_sleep()
        
        # 2. Cookie Consent (Critical to click interactions)
        try:
            page.click("#onetrust-accept-btn-handler", timeout=5000)
            print("   [INFO] Cookies accepted.")
        except:
            pass

        # 3. Fill Credentials
        try:
            print(f"[{self.supplier_code}] Injecting Credentials for {self.email}...")
            page.fill("input[name='email']", self.email)
            page.fill("input[name='password']", self.password)
            
            # 4. Submit
            page.click("button[data-link-action='sign-in']", timeout=10000) # Selector guessed based on Prestashop/Sklum standard
            # Fallback invalid selector handling could be added
            
            page.wait_for_load_state('networkidle')
            print(f"[{self.supplier_code}] Login Submitted. Verifying...")
            
            # Simple check
            if "mi-cuenta" in page.url or "my-account" in page.url:
                print(f"   [SUCCESS] Logged in as {self.email}")
            else:
                print(f"   [WARNING] Login might have failed or redirect inconsistent. Current URL: {page.url}")
                
        except Exception as e:
            print(f"   [ERROR] Login failed: {e}")

    def extract_products(self):
        page = self.browser_engine.get_page()
        
        for cat_id, cat_slug in self.categories_to_scrape:
            full_url = f"{self.base_url}/{cat_id}-comprar-{cat_slug}"
            print(f"[{self.supplier_code}] Scraping Category: {cat_slug} ({full_url})")
            
            try:
                page.goto(full_url, timeout=60000)
                self.browser_engine.random_sleep()
                
                # Pagination Loop
                while True:
                    # Extract items
                    items = page.query_selector_all("article") # Generic selector, refine
                    print(f"   [PAGE] Found {len(items)} items.")
                    
                    for item in items:
                        try:
                            # Extraction Logic
                            # 1. Image
                            img_el = item.query_selector("img")
                            img_src = img_el.get_attribute("data-src") or img_el.get_attribute("src") if img_el else None
                            
                            # 2. Name & Link
                            link_el = item.query_selector("a")
                            url = link_el.get_attribute("href") if link_el else ""
                            name = item.inner_text().split("\n")[0] # Naive
                            
                            if img_el: 
                                name = img_el.get_attribute("alt") or name

                            # 3. Price
                            price_el = item.query_selector(".price") or item.query_selector("[itemprop='price']")
                            price_txt = price_el.inner_text() if price_el else "0"
                            price_val = float(price_txt.replace('€','').replace(',','.').strip()) if price_txt else 0.0

                            sku = f"SKLUM-{abs(hash(url))}"[:15]

                            self.results.append({
                                "name": name,
                                "sku_supplier": sku,
                                "cost_price": price_val,
                                "selling_price": price_val, # No margin logic yet
                                "image_url": img_src,
                                "raw_data": {"url": url, "category": cat_slug}
                            })
                            
                        except Exception as e:
                            # print(f"Error parsing item: {e}")
                            pass
                    
                    # Next Page
                    next_btn = page.query_selector("a[rel='next']")
                    if next_btn:
                        print("   [NAV] Going to next page...")
                        next_btn.click()
                        page.wait_for_load_state('networkidle')
                        self.browser_engine.random_sleep(2, 4)
                    else:
                        break
                        
            except Exception as e:
                print(f"   [ERROR] Failed category {cat_slug}: {e}")

        print(f"[{self.supplier_code}] Extracted {len(self.results)} total items.")
