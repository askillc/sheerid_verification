"""
Locket Gold Service - RevenueCat API Integration
"""
import aiohttp
import json
import re
import time
import asyncio
import os
import base64

HEADERS = {
    'Host': 'api.revenuecat.com',
    'Authorization': 'Bearer appl_JngFETzdodyLmCREOlwTUtXdQik',
    'Content-Type': 'application/json',
    'Accept': '*/*',
    'X-Platform': 'iOS',
    'X-Platform-Version': 'Version 26.2 (Build 23C55)',
    'X-Platform-Device': 'iPhone15,3',
    'X-Platform-Flavor': 'native',
    'X-Version': '5.41.0',
    'X-Client-Version': '2.32.2',
    'X-Client-Bundle-ID': 'com.locket.Locket',
    'X-Client-Build-Version': '3',
    'X-StoreKit2-Enabled': 'true',
    'X-StoreKit-Version': '2',
    'X-Observer-Mode-Enabled': 'false',
    'X-Is-Sandbox': 'false',
    'X-Storefront': 'VNM',
    'X-Apple-Device-Identifier': '39A73C25-1E05-4350-ADA7-5CD3FE1079E8',
    'X-Preferred-Locales': 'vi_VN,en_US',
    'X-Nonce': 'w0Mlb6+AmV4WYuVv',
    'X-Is-Backgrounded': 'false',
    'X-Retry-Count': '0',
    'X-Is-Debug-Build': 'false',
    'User-Agent': 'Locket/3 CFNetwork/3860.300.31 Darwin/25.2.0',
    'Accept-Language': 'vi-VN,vi;q=0.9',
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
    'X-RevenueCat-ETag': ''
}

async def resolve_uid(username):
    """Resolve Locket username to UID"""
    url = f"https://locket.cam/{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
        "Accept": "text/html"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, allow_redirects=True, timeout=10) as res:
                html = await res.text()
                redirect_url = str(res.url)

                def extract(text):
                    if not text: return None
                    m = re.search(r'/invites/([A-Za-z0-9]{28})', text)
                    if m: return m.group(1)
                    
                    lp = re.search(r'link=([^\s"\'>]+)', text)
                    if lp:
                        try:
                            d = lp.group(1).replace('%3A', ':').replace('%2F', '/')
                            dm = re.search(r'/invites/([A-Za-z0-9]{28})', d)
                            if dm: return dm.group(1)
                        except:
                            pass
                    return None

                return extract(redirect_url) or extract(html)
        
    except Exception:
        return None

async def check_status(uid):
    """Check if user has Gold active"""
    url = f"https://api.revenuecat.com/v1/subscribers/{uid}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, timeout=10) as res:
                if 200 <= res.status < 300:
                    data = await res.json()
                    entitlements = data.get('subscriber', {}).get('entitlements', {}).get('Gold', {})
                    if entitlements:
                        expires_date = entitlements.get('expires_date')
                        return {"active": True, "expires": expires_date}
                    return {"active": False}
                return {"active": False}
    except Exception:
        return None

def decode_fetch_token(fetch_token):
    """
    Decode JWT fetch_token to extract real price, currency, and store info
    This prevents price mismatch that triggers RevenueCat fraud detection
    """
    try:
        # JWT format: header.payload.signature
        parts = fetch_token.split('.')
        if len(parts) != 3:
            print("⚠️ Invalid JWT format")
            return None
        
        # Decode payload (base64url)
        payload = parts[1]
        
        # Add padding if needed (base64 requires length % 4 == 0)
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        # Decode
        decoded_bytes = base64.urlsafe_b64decode(payload)
        data = json.loads(decoded_bytes)
        
        print(f"✅ Decoded token data: price={data.get('price')}, currency={data.get('currency')}")
        
        return {
            'price': data.get('price'),
            'currency': data.get('currency'),
            'storefront': data.get('storefront'),
            'product_id': data.get('productId')
        }
    except Exception as e:
        print(f"⚠️ Error decoding fetch_token: {e}")
        return None

async def inject_gold(uid, token_config):
    """Inject Gold subscription via RevenueCat API"""
    url = "https://api.revenuecat.com/v1/receipts"
    
    fetch_token = token_config['fetch_token']
    app_transaction = token_config['app_transaction']
    is_sandbox = token_config.get('is_sandbox', False)
    
    # CRITICAL FIX: Decode fetch_token to get REAL price/currency
    # This prevents price mismatch that triggers RevenueCat fraud detection
    decoded_data = decode_fetch_token(fetch_token)
    
    if decoded_data and decoded_data.get('price') and decoded_data.get('currency'):
        # Use REAL values from token (prevents fraud detection)
        price = str(decoded_data['price'])
        currency = decoded_data['currency']
        store_country = decoded_data.get('storefront', 'VNM')
        print(f"✅ Using decoded token values: price={price}, currency={currency}, storefront={store_country}")
    else:
        # Fallback to token_config or defaults
        price = token_config.get('price', '16.00')
        currency = token_config.get('currency', 'USD')
        store_country = token_config.get('storefront', 'VNM')
        print(f"⚠️ Using fallback values: price={price}, currency={currency}, storefront={store_country}")
    
    print(f"💰 Injecting Gold with price={price}, currency={currency}, storefront={store_country}")
    
    body = {
        "product_id": "locket_1600_1y", 
        "fetch_token": fetch_token, 
        "app_transaction": app_transaction,
        "app_user_id": uid, 
        "is_restore": True, 
        "store_country": store_country, 
        "currency": currency,
        "price": price, 
        "normal_duration": "P1Y", 
        "subscription_group_id": "21419447",
        "observer_mode": False, 
        "initiation_source": "restore", 
        "offers": [],
        "attributes": { 
            "$attConsentStatus": { "updated_at_ms": int(time.time() * 1000), "value": "notDetermined" } 
        }
    }
    
    current_headers = HEADERS.copy()
    current_headers['Content-Length'] = str(len(json.dumps(body)))
    current_headers['X-Is-Sandbox'] = str(is_sandbox).lower()

    async with aiohttp.ClientSession() as session:
        for attempt in range(5):
            try:
                async with session.post(url, headers=current_headers, json=body, timeout=15) as res:
                    status_code = res.status
                    
                    if status_code == 200:
                        # Verify activation
                        await asyncio.sleep(1)
                        status = await check_status(uid)
                        if status and status.get('active'):
                            return True, "SUCCESS"
                        else:
                            # Retry verification
                            await asyncio.sleep(2)
                            status = await check_status(uid)
                            if status and status.get('active'):
                                return True, "SUCCESS"
                            return False, "Accepted but NO Gold"
                            
                    elif status_code == 529:
                        await asyncio.sleep(2)
                        continue
                        
                    else:
                        msg = "Unknown Error"
                        try:
                            resp_json = await res.json()
                            msg = resp_json.get('message', str(status_code))
                        except:
                            msg = str(status_code)
                        return False, f"Rejected: {msg}"
                    
            except Exception as e:
                if attempt == 4:
                    return False, f"Request Error: {str(e)}"
                await asyncio.sleep(2)
            
    return False, "Timeout / Failed after retries"

def get_token_config():
    """Get token configuration from environment"""
    return {
        'fetch_token': os.environ.get('LOCKET_FETCH_TOKEN', ''),
        'app_transaction': os.environ.get('LOCKET_APP_TRANSACTION', ''),
        'is_sandbox': os.environ.get('LOCKET_IS_SANDBOX', 'false').lower() == 'true'
    }
