
import sys
import requests
import json
import time

def test_staging(base_url: str):
    print(f"🚀 Testing Staging Endpoint: {base_url}")
    
    # 1. Health Check
    try:
        print("Checking /health...")
        resp = requests.get(f"{base_url}/health", timeout=10)
        if resp.status_code == 200:
            print(f"✅ Health OK: {resp.json()}")
        else:
            print(f"❌ Health Failed: {resp.status_code} - {resp.text}")
            return
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    # 2. Chat Test (RAG + PDF)
    print("\nTesting /chat (RAG + PDF Generation)...")
    payload = {"message": "Busco mobiliario moderno para un hotel estilo zen"}
    
    start_time = time.time()
    try:
        resp = requests.post(f"{base_url}/chat", json=payload, timeout=60) # Higher timeout for PDF gen
        duration = time.time() - start_time
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Chat Response Received in {duration:.2f}s")
            print(f"🤖 Answer: {data.get('answer')}")
            
            pdf_url = data.get('pdf_url')
            if pdf_url:
                print(f"📄 PDF Generated: {pdf_url}")
                # Verify PDF access
                full_pdf_url = f"{base_url}{pdf_url}"
                print(f"   Verifying PDF accessibility at {full_pdf_url}...")
                pdf_resp = requests.head(full_pdf_url)
                if pdf_resp.status_code == 200:
                    print("   ✅ PDF Accessible")
                else:
                    print(f"   ❌ PDF Access Failed: {pdf_resp.status_code}")
            else:
                print("⚠️ No PDF URL in response.")
                
            products = data.get('products', [])
            print(f"📦 Found {len(products)} products.")
            if products:
                print(f"   Sample: {products[0]['name']} - {products[0]['price']} (Stock: {products[0].get('stock')})")
        else:
            print(f"❌ Chat Failed: {resp.status_code} - {resp.text}")

    except Exception as e:
        print(f"❌ Chat Request Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_staging_endpoint.py <BASE_URL>")
        print("Example: python test_staging_endpoint.py https://adquify-engine-production.up.railway.app")
    else:
        test_staging(sys.argv[1].rstrip('/'))
