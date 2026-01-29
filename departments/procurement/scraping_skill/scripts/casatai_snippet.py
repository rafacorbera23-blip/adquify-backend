
    # Casa Tai Logic (List Selector)
    if "casatai" in page['url']:
        items = soup.select(".product-container") or soup.select(".product-miniature")
        for item in items:
            try:
                name = item.select_one(".product-name").text.strip()
                price_txt = item.select_one(".price").text.strip()
                price = float(re.search(r'(\d+[,.]\d+)', price_txt).group(1).replace(',', '.'))
                img = item.select_one("img").get('src')
                
                extracted_items.append({
                    "name": name,
                    "price": price,
                    "supplier": "Casa Tai",
                    "materials": "Consumible/Papel/Celulosa",
                    "dimensions": "Standard Packs",
                    "images": [img]
                })
            except: continue
