import asyncio
import random
import hashlib
import json
import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, BrowserContext, Page
from sqlalchemy.orm import Session
from core.database import SessionLocal
from core.models import Product, Supplier, ProductImage

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("HarvesterAgent")

class BaseExtractor:
    def __init__(self, supplier_code: str):
        self.supplier_code = supplier_code
    
    def _generate_adq_sku(self, url: str) -> str:
        h = hashlib.md5(url.encode()).hexdigest()[:8].upper()
        return f"ADQ-{self.supplier_code[:2].upper()}-{h}"

    async def _safe_goto(self, page: Page, url: str, wait_until="domcontentloaded"):
        for attempt in range(3):
            try:
                jitter = random.uniform(0.5, 1.5)
                await asyncio.sleep(jitter)
                await page.goto(url, wait_until=wait_until, timeout=60000)
                return True
            except Exception as e:
                logger.warning(f"[{self.supplier_code}] JitterNav Attempt {attempt+1} failed for {url}: {e}")
                if attempt == 2: raise e
        return False

class KaveHomeExtractor(BaseExtractor):
    def __init__(self):
        super().__init__("kave")
        self.api_url = "https://EQ79XLPIU7-dsn.algolia.net/1/indexes/product_es_es/query"
        self.headers = {
            "X-Algolia-API-Key": "406dad47edeb9512eb92450bede6ed37",
            "X-Algolia-Application-Id": "EQ79XLPIU7",
            "Content-Type": "application/json"
        }
        self.search_terms = ["sofas", "sillas", "mesas", "dormitorio", "exterior", "iluminacion", "decoracion", "almacenaje"]

    async def extract(self, context: BrowserContext = None) -> List[Dict]:
        """Kave uses Algolia API, so we don't strictly need Playwright context here, but keeping signature consistent."""
        logger.info("🚀 Starting Kave Home Extraction (Algolia API)")
        all_products = []
        
        # We run requests in a separate thread to not block asyncio loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_extract)

    def _sync_extract(self) -> List[Dict]:
        products = []
        seen_urls = set()
        
        for term in self.search_terms:
            logger.info(f"   Searching '{term}'...")
            page = 0
            while True:
                payload = {"params": f"query={term}&hitsPerPage=100&page={page}"}
                try:
                    resp = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
                    if resp.status_code != 200: break
                    
                    data = resp.json()
                    hits = data.get('hits', [])
                    if not hits: break
                    
                    for hit in hits:
                        try:
                            link = hit.get('link', '')
                            if not link: continue
                            full_url = f"https://www.kavehome.com{link}"
                            if full_url in seen_urls: continue
                            seen_urls.add(full_url)

                            # Images
                            images = []
                            if hit.get('main_image'): images.append(hit.get('main_image'))
                            for img in hit.get('listing_images', []):
                                if isinstance(img, dict) and img.get('url'):
                                    if img.get('url') not in images: images.append(img.get('url'))

                            # Materials & Dimensions
                            mats = hit.get('materials', [])
                            materials = ", ".join(mats) if isinstance(mats, list) else str(mats)
                            dim_str = f"{hit.get('length','')}x{hit.get('width','')}x{hit.get('height','')} cm"

                            products.append({
                                'supplier': 'kave',
                                'sku_supplier': hit.get('sku', ''),
                                'name': hit.get('title', ''),
                                'price': float(hit.get('price', 0) or 0),
                                'url': full_url,
                                'category': term,
                                'description': hit.get('description', ''),
                                'images': images,
                                'material': materials,
                                'dimensions': dim_str
                            })
                        except: continue
                    
                    if page >= data.get('nbPages', 0) - 1: break
                    page += 1
                except Exception as e:
                    logger.error(f"Kave API Error: {e}")
                    break
        return products

class SklumExtractor(BaseExtractor):
    def __init__(self):
        super().__init__("sklum")
        # Extended Category List
        self.categories = [
            {"id": "633", "name": "sofas"},
            {"id": "543", "name": "sillas"},
            {"id": "544", "name": "mesas"},
            {"id": "545", "name": "armarios"},
            {"id": "546", "name": "lamparas"},
            {"id": "624", "name": "alfombras"},
            {"id": "547", "name": "decoracion"},
            {"id": "548", "name": "jardin"}
        ]

    async def extract(self, context: BrowserContext) -> List[Dict]:
        page = await context.new_page()
        all_products = []
        
        try:
            for cat in self.categories:
                logger.info(f"📂 Scraping Sklum: {cat['name']}")
                # Sklum listing pages often allow loading all via ID, but standard pagination is safer with JSON-LD
                # We will just hit the main category page. Sklum often puts all products in one long scroll or paginated.
                # Constructing URL:
                url = f"https://www.sklum.com/es/{cat['id']}-comprar-{cat['name']}"
                await self._safe_goto(page, url)
                
                # Sklum pagination handling via page number in URL if needed? 
                # Actually, simple method: Check for JSON-LD list.
                # To be massive, we need to iterate pages. URL format: /es/{id}-{name}?p={page}
                
                page_num = 1
                while True:
                    if page_num > 1:
                        p_url = f"{url}?p={page_num}"
                        await self._safe_goto(page, p_url)
                    
                    # Extract Data
                    found_on_page = 0
                    scripts = await page.query_selector_all('script[type="application/ld+json"]')
                    for s in scripts:
                        try:
                            content = await s.inner_text()
                            data = json.loads(content)
                            if data.get('@type') == 'ItemList':
                                items = data.get('itemListElement', [])
                                if not items: continue
                                
                                for item in items:
                                    p = item.get('item', {})
                                    if p and p.get('url'):
                                        all_products.append({
                                            'supplier': 'sklum',
                                            'sku_supplier': p.get('sku'),
                                            'name': p.get('name'),
                                            'price': float(p.get('offers', {}).get('price', 0) or 0),
                                            'url': p.get('url'),
                                            'category': cat['name'],
                                            'description': p.get('description', ''),
                                            'images': [p.get('image')] if p.get('image') else []
                                        })
                                        found_on_page += 1
                        except: continue
                    
                    if found_on_page == 0:
                        break # Stop if no products found (end of pagination)
                    
                    # Safety Break to avoid infinite loops in MVP if Sklum redirects to 1
                    if page_num > 50: break 
                    
                    page_num += 1
                    await asyncio.sleep(1) # Be nice
        except Exception as e:
            logger.error(f"Sklum Error: {e}")
        finally:
            await page.close()
        
        return all_products

class CasaThaiExtractor(BaseExtractor):
    def __init__(self):
        super().__init__("casathai")
        self.base_urls = [
            "https://casathai.es/es/3-muebles",
            "https://casathai.es/es/7-sillas",
            "https://casathai.es/es/15-sofas",
            "https://casathai.es/es/18-iluminacion"
        ]

    async def extract(self, context: BrowserContext) -> List[Dict]:
        page = await context.new_page()
        # Ensure we block images/fonts for speed in listing checking, but we need them for deep extraction??
        # No, for textual data we don't need them.
        
        all_products = []
        seen_urls = set()

        try:
            for base_url in self.base_urls:
                current_page = 1
                logger.info(f"📂 Scraping CasaThai: {base_url}")
                
                while True:
                    url = f"{base_url}?page={current_page}"
                    await self._safe_goto(page, url)
                    
                    try:
                        await page.wait_for_selector(".product-miniature", timeout=5000)
                    except:
                        break # End of cats

                    # Get links
                    links = await page.eval_on_selector_all(".product-miniature .product-title a", "els => els.map(e => e.href)")
                    if not links: break
                    
                    new_links = [l for l in links if l not in seen_urls]
                    if not new_links: break

                    # Deep Visit Each Product
                    for idx, p_url in enumerate(new_links):
                        seen_urls.add(p_url)
                        try:
                            # Use a separate page for details to keep main loop fast?
                            # Or just iterate. Concurrency would be better but simple loop is safer for anti-bot.
                            p_page = await context.new_page()
                            await p_page.goto(p_url, wait_until='domcontentloaded', timeout=30000)
                            
                            # Extract
                            name_el = await p_page.title()
                            name = name_el.split(" - CasaThai")[0].strip()
                            
                            price_el = await p_page.query_selector('.current-price span[itemprop="price"]')
                            price_txt = await price_el.get_attribute("content") if price_el else "0"
                            price = float(price_txt.replace(',','.')) if price_txt else 0.0

                            desc_el = await p_page.query_selector('.product-description')
                            desc = await desc_el.inner_html() if desc_el else ""

                            # Images
                            images = await p_page.eval_on_selector_all('ul.product-images li img', "imgs => imgs.map(i => i.getAttribute('data-image-large-src') || i.src)")
                            
                            all_products.append({
                                'supplier': 'casathai',
                                'sku_supplier': '',
                                'name': name,
                                'price': price,
                                'url': p_url,
                                'category': base_url.split('/')[-1],
                                'description': desc,
                                'images': images,
                                'material': '', # TODO: Extract from data sheet if needed
                                'dimensions': ''
                            })
                            await p_page.close()
                        except Exception as e:
                            logger.error(f"CasaThai Product Error {p_url}: {e}")
                            if not p_page.is_closed(): await p_page.close()
                            continue
                    
                    next_btn = await page.query_selector("a.next")
                    if not next_btn or await page.query_selector("a.next.disabled"):
                        break
                    
                    current_page += 1
        except Exception as e:
             logger.error(f"CasaThai Global Error: {e}")
        finally:
            await page.close()
        
        return all_products

class HarvesterAgent:
    def __init__(self):
        self.extractors = [
            KaveHomeExtractor(),
            SklumExtractor(),
            CasaThaiExtractor()
        ]

    async def run_mission(self):
        logger.info("🚀 Starting MASSIVE Harvester Mission")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            db: Session = SessionLocal()
            
            try:
                # Run extractors concurrently?
                # CasaThai is slow (DOM visiting). Sklum is medium. Kave is fast.
                # Let's run Kave first (fastest) to populate DB quickly, then others.
                # Actually, gather is fine.
                
                results = await asyncio.gather(
                    *[e.extract(context) for e in self.extractors],
                    return_exceptions=True
                )
                
                for i, res in enumerate(results):
                    if isinstance(res, list):
                        logger.info(f"💾 Persisting {len(res)} items from {self.extractors[i].supplier_code}")
                        self._persist_results(db, res)
                    else:
                        logger.error(f"❌ Extractor {self.extractors[i].supplier_code} failed: {res}")
                
            except Exception as e:
                logger.error(f"❌ Mission Critical Fail: {e}")
                db.rollback()
            finally:
                db.close()
                await browser.close()
                logger.info("🏁 Harvester Mission Finished")

    def _persist_results(self, db: Session, data: List[Dict]):
        if not data: return
        
        supplier_code = data[0]['supplier']
        supplier = db.query(Supplier).filter(Supplier.code == supplier_code).first()
        if not supplier:
            supplier = Supplier(code=supplier_code, name=supplier_code.capitalize())
            db.add(supplier)
            db.commit()
            db.refresh(supplier)

        for p_info in data:
            try:
                adq_sku = hashlib.md5(p_info['url'].encode()).hexdigest()[:8].upper()
                adq_sku = f"ADQ-{supplier_code[:2].upper()}-{adq_sku}"
                
                product = db.query(Product).filter(Product.sku_adquify == adq_sku).first()
                
                # Default margin if not set
                margin = supplier.margin_multiplier if supplier.margin_multiplier else 1.5

                if not product:
                    product = Product(
                        sku_adquify=adq_sku,
                        sku_supplier=p_info.get('sku_supplier') or adq_sku,
                        supplier_id=supplier.id,
                        name=p_info['name'],
                        category=p_info.get('category', 'general'),
                        cost_price=p_info['price'],
                        selling_price=p_info['price'] * margin,
                        description=p_info.get('description', ''),
                        material=p_info.get('material', ''),
                        dimensions=p_info.get('dimensions', ''),
                        status="published"
                    )
                    db.add(product)
                    db.flush() 
                    
                    # Images
                    for img_url in p_info.get('images', []):
                        if img_url:
                            img = ProductImage(product_id=product.id, url=img_url)
                            db.add(img)
                else:
                    # Update critical fields
                    product.cost_price = p_info['price']
                    product.selling_price = p_info['price'] * margin
                    product.updated_at = datetime.utcnow()
                    
            except Exception as e:
                logger.error(f"Error saving product {p_info.get('name')}: {e}")
                db.rollback()
                continue
        
        db.commit()

if __name__ == "__main__":
    agent = HarvesterAgent()
    asyncio.run(agent.run_mission())
import random
import hashlib
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, BrowserContext, Page
from sqlalchemy.orm import Session
from core.database import SessionLocal
from core.models import Product, Supplier, ProductImage

# Configure Logging (Devin Style)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("HarvesterAgent")

class BaseExtractor:
    def __init__(self, supplier_code: str):
        self.supplier_code = supplier_code
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ]

    def _generate_adq_sku(self, url: str) -> str:
        h = hashlib.md5(url.encode()).hexdigest()[:8].upper()
        return f"ADQ-{self.supplier_code[:2].upper()}-{h}"

    async def _safe_goto(self, page: Page, url: str, wait_until="domcontentloaded"):
        """Navigate with retry and jitter."""
        for attempt in range(3):
            try:
                jitter = random.uniform(0.5, 1.5)
                await asyncio.sleep(jitter)
                await page.goto(url, wait_until=wait_until, timeout=60000)
                return True
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed for {url}: {e}")
                if attempt == 2: raise e
        return False

class SklumExtractor(BaseExtractor):
    def __init__(self):
        super().__init__("sklum")
        # Just a subset for demo/unification proof
        self.categories = [
            {"id": "633", "name": "sofas"},
            {"id": "543", "name": "sillas"}
        ]

    async def extract(self, context: BrowserContext) -> List[Dict]:
        page = await context.new_page()
        all_products = []
        
        for cat in self.categories:
            logger.info(f"Scraping Sklum Category: {cat['name']}")
            url = f"https://www.sklum.com/es/{cat['id']}-comprar-{cat['name']}"
            await self._safe_goto(page, url)
            
            # Use JSON-LD for rapid collection
            scripts = await page.query_selector_all('script[type="application/ld+json"]')
            for s in scripts:
                content = await s.inner_text()
                try:
                    data = json.loads(content)
                    if data.get('@type') == 'ItemList':
                        for item in data.get('itemListElement', []):
                            p = item.get('item', {})
                            if p:
                                all_products.append({
                                    'supplier': 'sklum',
                                    'sku_supplier': p.get('sku'),
                                    'name': p.get('name'),
                                    'price': float(p.get('offers', {}).get('price', 0)),
                                    'url': p.get('url'),
                                    'category': cat['name'],
                                    'description': p.get('description', ''),
                                    'images': [p.get('image')] if p.get('image') else []
                                })
                except: continue
        await page.close()
        return all_products

class HarvesterAgent:
    def __init__(self):
        self.extractors = [
            SklumExtractor(),
            # Add Kave, CasaThai, Distrigal here
        ]

    async def run_mission(self):
        logger.info("🚀 Starting Harvester Mission")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            db: Session = SessionLocal()
            
            try:
                for extractor in self.extractors:
                    products_data = await extractor.extract(context)
                    logger.info(f"Fetched {len(products_data)} products from {extractor.supplier_code}")
                    self._persist_results(db, products_data)
                
                db.commit()
                logger.info("✅ Mission Complete. Database updated.")
            except Exception as e:
                logger.error(f"❌ Mission Failed: {e}")
                db.rollback()
            finally:
                db.close()
                await browser.close()

    def _persist_results(self, db: Session, data: List[Dict]):
        # Get or create supplier
        supplier_code = data[0]['supplier'] if data else None
        if not supplier_code: return
        
        supplier = db.query(Supplier).filter(Supplier.code == supplier_code).first()
        if not supplier:
            supplier = Supplier(code=supplier_code, name=supplier_code.capitalize())
            db.add(supplier)
            db.flush()

        for p_info in data:
            # Check if exists
            adq_sku = hashlib.md5(p_info['url'].encode()).hexdigest()[:8].upper()
            adq_sku = f"ADQ-{supplier_code[:2].upper()}-{adq_sku}"
            
            product = db.query(Product).filter(Product.sku_adquify == adq_sku).first()
            
            if not product:
                product = Product(
                    sku_adquify=adq_sku,
                    sku_supplier=p_info['sku_supplier'],
                    supplier_id=supplier.id,
                    name=p_info['name'],
                    category=p_info['category'],
                    cost_price=p_info['price'],
                    selling_price=p_info['price'] * supplier.margin_multiplier,
                    description=p_info['description'],
                    status="published"
                )
                db.add(product)
                db.flush()
                
                # Handle Images
                for img_url in p_info.get('images', []):
                    img = ProductImage(product_id=product.id, url=img_url)
                    db.add(img)
            else:
                # Update price if changed
                product.cost_price = p_info['price']
                product.selling_price = p_info['price'] * supplier.margin_multiplier
                product.updated_at = datetime.utcnow()

if __name__ == "__main__":
    agent = HarvesterAgent()
    asyncio.run(agent.run_mission())
