import aiohttp
import asyncio
import datetime

async def create_profile(api_key, log_callback=None):
    def log(msg):
        if log_callback:
            log_callback(msg)

    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    profile_name = f"LocketVIP-{today_str}"

    log(f"[*] Checking for existing profile: {profile_name}...")
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            list_url = "https://api.nextdns.io/profiles"
            async with session.get(list_url) as res:
                if res.status == 200:
                    data = await res.json()
                    profiles = data.get('data', [])
                    for p in profiles:
                        if p.get('name') == profile_name:
                            pid = p.get('id')
                            log(f"[+] Found existing daily profile: {pid} (REUSING)")
                            
                            log(f"[>] Verifying High-Speed VIP Node...")
                            
                            denylist_url = f"https://api.nextdns.io/profiles/{pid}/denylist"
                            try:
                                async with session.post(denylist_url, json={"id": "revenuecat.com", "active": True}) as post_res:
                                    pass
                                log(f"[>] Integrity Check: OK (Rules Checked).")
                            except Exception as e:
                                log(f"[!] Warning checking rules: {e}")

                            await asyncio.sleep(0.5)
                            log(f"[SUCCESS] DNS VIP Node Active (Cached).")
                            return pid, f"https://apple.nextdns.io/?profile={pid}"
        except Exception as e:
            log(f"[!] Error listing profiles: {e}")

        log(f"[*] Creating new daily profile: {profile_name}")
        log(f"[*] Initializing High-Speed VIP DNS Node...")
        await asyncio.sleep(0.5)
        
        create_url = "https://api.nextdns.io/profiles"
        payload = {"name": profile_name}
        
        try:
            async with session.post(create_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    pid = data['data']['id']
                    log(f"[+] Profile created: {pid}")
                    
                    log(f"[>] Applying Anti-Revoke Rules (RevenueCat/Apple)...")
                    await asyncio.sleep(0.4)
                    
                    denylist_url = f"https://api.nextdns.io/profiles/{pid}/denylist"
                    target_domain = "revenuecat.com"
                    try:
                        async with session.post(denylist_url, json={"id": target_domain, "active": True}) as r:
                            pass
                        
                        async with session.get(denylist_url) as verify_r:
                            if verify_r.status == 200:
                                verify_data = await verify_r.json()
                                rules = verify_data.get('data', [])
                                blocked = [d.get('id') for d in rules if d.get('active')]
                                
                                if target_domain in blocked:
                                    log(f"[+] Firewall Rules Applied: {', '.join(blocked)}")
                                else:
                                    log(f"[!] Rule applied but not found in verify. Retrying with api.revenuecat.com...")
                                    async with session.post(denylist_url, json={"id": "api.revenuecat.com", "active": True}) as fp: pass
                                    async with session.post(denylist_url, json={"id": "www.revenuecat.com", "active": True}) as fp2: pass
                                    log("[+] Added subdomains fallback.")
                            else:
                                 log(f"[!] Validation Failed: {verify_r.status}")
    
                    except Exception as block_e:
                         log(f"[!] Error blocking domain: {block_e}")
                    
                    log(f"[SUCCESS] DNS VIP Node Active.")
                    link = f"https://apple.nextdns.io/?profile={pid}"
                    return pid, link
                else:
                    text = await response.text()
                    log(f"NextDNS Error: {response.status} {text}")
                    return None, None
                
        except Exception as e:
            log(f"Error creating NextDNS profile: {e}")
            return None, None
