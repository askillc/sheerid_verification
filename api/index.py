from flask import Flask, request, jsonify, send_from_directory, render_template_string
from urllib.parse import urlparse
import requests
import random
from datetime import datetime, timezone, timedelta
import time
import os
import json
import glob
import sqlite3
import unicodedata
import re
from PIL import Image, ImageDraw, ImageFont

# Vietnam timezone (UTC+7)
VIETNAM_TZ = timezone(timedelta(hours=7))

def get_vietnam_time():
    """Get current time in Vietnam timezone (UTC+7)"""
    return datetime.now(VIETNAM_TZ)

def format_vietnam_time(format_str='%d/%m/%Y %H:%M:%S'):
    """Format current Vietnam time in 24-hour format"""
    return get_vietnam_time().strftime(format_str)


def remove_vietnamese_accents(text):
    """Remove Vietnamese accents/diacritics from text for email generation"""
    if not text:
        return text
    # Normalize to NFD (decomposed form) then remove combining characters
    normalized = unicodedata.normalize('NFD', text)
    # Remove combining diacritical marks
    without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    # Handle special Vietnamese characters that don't decompose well
    replacements = {
        'đ': 'd', 'Đ': 'D',
        'ă': 'a', 'Ă': 'A',
        'â': 'a', 'Â': 'A',
        'ê': 'e', 'Ê': 'E',
        'ô': 'o', 'Ô': 'O',
        'ơ': 'o', 'Ơ': 'O',
        'ư': 'u', 'Ư': 'U',
    }
    for viet, ascii_char in replacements.items():
        without_accents = without_accents.replace(viet, ascii_char)
    return without_accents


# US State to Timezone mapping - CRITICAL for fraud prevention
STATE_TIMEZONE_MAP = {
    # Eastern Time (ET)
    "CT": "America/New_York", "DE": "America/New_York", "FL": "America/New_York",
    "GA": "America/New_York", "IN": "America/Indiana/Indianapolis", "KY": "America/New_York",
    "ME": "America/New_York", "MD": "America/New_York", "MA": "America/New_York",
    "MI": "America/Detroit", "NH": "America/New_York", "NJ": "America/New_York",
    "NY": "America/New_York", "NC": "America/New_York", "OH": "America/New_York",
    "PA": "America/New_York", "RI": "America/New_York", "SC": "America/New_York",
    "VT": "America/New_York", "VA": "America/New_York", "WV": "America/New_York",
    "DC": "America/New_York",
    # Central Time (CT)
    "AL": "America/Chicago", "AR": "America/Chicago", "IL": "America/Chicago",
    "IA": "America/Chicago", "KS": "America/Chicago", "LA": "America/Chicago",
    "MN": "America/Chicago", "MS": "America/Chicago", "MO": "America/Chicago",
    "NE": "America/Chicago", "ND": "America/Chicago", "OK": "America/Chicago",
    "SD": "America/Chicago", "TN": "America/Chicago", "TX": "America/Chicago",
    "WI": "America/Chicago",
    # Mountain Time (MT)
    "AZ": "America/Phoenix", "CO": "America/Denver", "ID": "America/Boise",
    "MT": "America/Denver", "NM": "America/Denver", "UT": "America/Denver",
    "WY": "America/Denver", "NV": "America/Los_Angeles",  # Most of NV is Pacific
    # Pacific Time (PT)
    "CA": "America/Los_Angeles", "OR": "America/Los_Angeles", "WA": "America/Los_Angeles",
    # Alaska & Hawaii
    "AK": "America/Anchorage", "HI": "Pacific/Honolulu",
}

STATE_TIMEZONE_OFFSET_MAP = {
    # Eastern Time: UTC-5 (standard) / UTC-4 (DST) -> -300 / -240 minutes
    "CT": -300, "DE": -300, "FL": -300, "GA": -300, "IN": -300, "KY": -300,
    "ME": -300, "MD": -300, "MA": -300, "MI": -300, "NH": -300, "NJ": -300,
    "NY": -300, "NC": -300, "OH": -300, "PA": -300, "RI": -300, "SC": -300,
    "VT": -300, "VA": -300, "WV": -300, "DC": -300,
    # Central Time: UTC-6 (standard) / UTC-5 (DST) -> -360 / -300 minutes
    "AL": -360, "AR": -360, "IL": -360, "IA": -360, "KS": -360, "LA": -360,
    "MN": -360, "MS": -360, "MO": -360, "NE": -360, "ND": -360, "OK": -360,
    "SD": -360, "TN": -360, "TX": -360, "WI": -360,
    # Mountain Time: UTC-7 (standard) / UTC-6 (DST) -> -420 / -360 minutes
    "AZ": -420, "CO": -420, "ID": -420, "MT": -420, "NM": -420, "UT": -420,
    "WY": -420, "NV": -480,  # Nevada follows Pacific
    # Pacific Time: UTC-8 (standard) / UTC-7 (DST) -> -480 / -420 minutes
    "CA": -480, "OR": -480, "WA": -480,
    # Alaska & Hawaii
    "AK": -540, "HI": -600,
}


def get_timezone_for_state(state: str) -> str:
    """Get timezone name for a US state - CRITICAL for fraud prevention"""
    return STATE_TIMEZONE_MAP.get(state, "America/New_York")


# Import HIGH_SCHOOLS from highschools_config.py
try:
    from highschools_config import HIGH_SCHOOLS, get_random_high_school, get_high_school_by_id
except ImportError:
    from api.highschools_config import HIGH_SCHOOLS, get_random_high_school, get_high_school_by_id

# HIGH_SCHOOLS is now imported from highschools_config.py
# Use get_random_high_school() for random selection
def get_timezone_offset_for_state(state: str) -> int:
    """Get timezone offset in minutes for a US state"""
    return STATE_TIMEZONE_OFFSET_MAP.get(state, -300)


def generate_threatmetrix_session():
    """Generate a ThreatMetrix session ID for fraud prevention bypass
    
    ThreatMetrix uses a unique session ID to track device fingerprinting.
    Format: org_id + random hex string (typically 32-40 chars)
    """
    import uuid
    import time
    
    # Generate unique session ID similar to ThreatMetrix format
    # Format: {org_prefix}-{timestamp_hex}-{random_uuid}
    timestamp_hex = hex(int(time.time() * 1000))[2:]  # Remove '0x' prefix
    random_part = uuid.uuid4().hex[:16]
    
    # ThreatMetrix session ID format (similar to real ones)
    tmx_session = f"sheerid-{timestamp_hex}-{random_part}"
    
    return tmx_session

def generate_device_fingerprint():
    """Generate a realistic randomized device fingerprint hash for anti-detection"""
    import hashlib
    import time
    
    # More realistic browser fingerprint components
    screen_resolutions = [(1920, 1080), (2560, 1440), (1366, 768), (1536, 864), (1440, 900), (1680, 1050)]
    color_depths = [24, 32]
    timezones = [-300, -360, -420, -480, -240]  # US timezones (EST, CST, MST, PST, EDT)
    
    selected_res = random.choice(screen_resolutions)
    
    # Random components to make each fingerprint unique
    components = [
        str(random.randint(1000000000, 9999999999)),  # Random session ID
        str(int(time.time() * 1000)),  # Timestamp in ms
        str(random.randint(1, 1000000)),  # Random entropy
        'Chrome',  # Always Chrome for consistency
        'Windows',  # Always Windows for US verification
        str(selected_res[0]),  # Screen width
        str(selected_res[1]),  # Screen height
        str(random.choice(color_depths)),  # Color depth
        str(random.choice(timezones)),  # Timezone offset
        str(random.randint(4, 16)),  # Hardware concurrency (CPU cores)
        str(random.choice([4, 8, 16, 32])),  # Device memory GB
        'Win32',  # Platform
        ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=32))  # Random string
    ]
    
    # Create hash from components
    combined = '|'.join(components)
    hash_obj = hashlib.sha256(combined.encode())
    
    # Return 64 hex characters (full SHA-256 like real fingerprint)
    return hash_obj.hexdigest()

# Load environment variables from .env.local for local development
try:
    from dotenv import load_dotenv
    # Try multiple env file locations
    if os.path.exists('.env.local'):
        load_dotenv('.env.local')
        print("✅ Loaded .env.local for local development")
    elif os.path.exists('../.env.local'):
        load_dotenv('../.env.local')
        print("✅ Loaded ../.env.local for local development")
    else:
        print("⚠️ No .env.local found, using system environment variables")
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment variables")
except Exception as e:
    print(f"⚠️ Could not load .env.local: {e}")

# Global set to track charged jobs to prevent double charging
CHARGED_JOBS = set()

# Global set to track notified jobs to prevent duplicate notifications
NOTIFIED_JOBS = set()

# ===== FRAUD IP TRACKING =====
# Track IPs that caused fraud detection to avoid reusing them
# This helps reduce fraud detection rate by avoiding "burned" IPs
FRAUD_IP_BLACKLIST = set()  # IPs that caused fraudRulesReject
FRAUD_IP_COOLDOWN = {}  # IP -> timestamp when it can be used again
FRAUD_IP_COUNT = {}  # IP -> count of fraud detections
FRAUD_IP_COOLDOWN_HOURS = 24  # Hours to blacklist an IP after fraud detection

def is_ip_blacklisted(ip):
    """Check if an IP is currently blacklisted due to fraud detection"""
    if not ip or ip == "unknown":
        return False
    if ip in FRAUD_IP_BLACKLIST:
        cooldown_time = FRAUD_IP_COOLDOWN.get(ip, 0)
        if time.time() < cooldown_time:
            return True
        # Cooldown expired, remove from blacklist
        FRAUD_IP_BLACKLIST.discard(ip)
        FRAUD_IP_COOLDOWN.pop(ip, None)
        FRAUD_IP_COUNT.pop(ip, None)
        print(f"🔓 IP {ip} cooldown expired, removed from blacklist")
    return False

def blacklist_fraud_ip(ip, job_id=None):
    """Add an IP to the fraud blacklist with cooldown"""
    if not ip or ip == "unknown":
        return
    
    # Increment fraud count for this IP
    FRAUD_IP_COUNT[ip] = FRAUD_IP_COUNT.get(ip, 0) + 1
    count = FRAUD_IP_COUNT[ip]
    
    # Add to blacklist with cooldown
    FRAUD_IP_BLACKLIST.add(ip)
    cooldown_hours = FRAUD_IP_COOLDOWN_HOURS * count  # Longer cooldown for repeat offenders
    FRAUD_IP_COOLDOWN[ip] = time.time() + (cooldown_hours * 3600)
    
    print(f"🚫 IP {ip} blacklisted for {cooldown_hours}h (fraud count: {count})")
    if job_id:
        print(f"   Job: {job_id}")
    
    # Also try to persist to database for cross-instance tracking
    try:
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            # Upsert fraud IP record
            supabase.table('fraud_ips').upsert({
                'ip_address': ip,
                'fraud_count': count,
                'last_fraud_at': datetime.now(VIETNAM_TZ).isoformat(),
                'cooldown_until': datetime.fromtimestamp(FRAUD_IP_COOLDOWN[ip], VIETNAM_TZ).isoformat(),
                'last_job_id': job_id
            }, on_conflict='ip_address').execute()
            print(f"💾 Saved fraud IP {ip} to database")
    except Exception as e:
        print(f"⚠️ Could not save fraud IP to database: {e}")

def get_fraud_ip_stats():
    """Get statistics about fraud IPs for admin dashboard"""
    return {
        'blacklisted_count': len(FRAUD_IP_BLACKLIST),
        'blacklisted_ips': list(FRAUD_IP_BLACKLIST),
        'fraud_counts': dict(FRAUD_IP_COUNT),
        'cooldowns': {ip: datetime.fromtimestamp(ts, VIETNAM_TZ).isoformat() 
                      for ip, ts in FRAUD_IP_COOLDOWN.items()}
    }

def load_fraud_ips_from_db():
    """Load fraud IPs from database on startup"""
    try:
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            result = supabase.table('fraud_ips').select('*').execute()
            if result.data:
                current_time = time.time()
                for record in result.data:
                    ip = record.get('ip_address')
                    cooldown_until = record.get('cooldown_until')
                    fraud_count = record.get('fraud_count', 1)
                    
                    if ip and cooldown_until:
                        # Parse cooldown time
                        try:
                            cooldown_ts = datetime.fromisoformat(cooldown_until.replace('Z', '+00:00')).timestamp()
                            if cooldown_ts > current_time:
                                FRAUD_IP_BLACKLIST.add(ip)
                                FRAUD_IP_COOLDOWN[ip] = cooldown_ts
                                FRAUD_IP_COUNT[ip] = fraud_count
                        except Exception:
                            pass
                print(f"📥 Loaded {len(FRAUD_IP_BLACKLIST)} fraud IPs from database")
    except Exception as e:
        print(f"⚠️ Could not load fraud IPs from database: {e}")

# Load fraud IPs on module import
try:
    load_fraud_ips_from_db()
except Exception:
    pass
# ===== END FRAUD IP TRACKING =====

# Queue system removed - verifications run immediately without waiting

# FAST MODE - Skip anti-detection delays for faster verification (like batch.1key.me)
# Default to False to enable anti-detection delays (avoid fraud detection)
# Can be changed via admin dashboard
FAST_MODE_DEFAULT = False

# SKIP FINGERPRINTING - Skip device fingerprinting and analytics for even faster verification
# This can reduce verification time from ~30s to ~5-10s
# WARNING: Skipping fingerprinting may trigger fraud detection!
SKIP_FINGERPRINTING = False  # Set to False to enable fingerprinting (avoid fraud detection)

# ENABLE THREATMETRIX - Send ThreatMetrix profiling request for fraud prevention bypass
# ThreatMetrix is a fraud detection system used by SheerID
# When enabled: Sends profiling request to h.online-metrix.net and adds TMX session to payload
# When disabled: Skips ThreatMetrix profiling (faster but may trigger fraud detection)
ENABLE_THREATMETRIX = False  # Disabled - using Browserless for fraud bypass instead

def get_fast_mode():
    """Get fast mode setting from database, fallback to default"""
    try:
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            result = supabase.table('bot_config').select('config_value').eq('config_key', 'fast_mode').execute()
            if result.data:
                return str(result.data[0].get('config_value', 'true')).lower() == 'true'
    except Exception as e:
        print(f"⚠️ Error getting fast_mode from DB: {e}")
    return FAST_MODE_DEFAULT

# GET IP FROM WWPROXY (Vietnam Residential Proxy)
# Fetch from WWProxy API - rotating residential IPs from Vietnam
# Using 8 keys for multi-IP rotation
WWPROXY_KEYS = [
    "UK-56dbe61a-7f22-49af-aaa7-5e79b3b8ad70",  # Key 1
    "UK-f90501c6-2742-4f1e-9cca-5af8ee17b0a1",  # Key 2
    "UK-4fc24cf8-f017-4ff6-a201-4f69c549ef77",  # Key 3
    "UK-a342fda1-ad00-4f91-a477-0c0106cceb61",  # Key 4
    "UK-e8a022e7-103f-4ac1-b2a9-eefe748f1820",  # Key 5
    "UK-9d8ffbaf-1c06-43a6-adfb-136cc160000f",  # Key 6
    "UK-1321b112-5a62-4cea-90f7-0236bc8675e0",  # Key 7 (new)
    "UK-dc5d691d-db7b-4d96-8ee2-222bce1a6c47"   # Key 8 (new)
]
_CURRENT_KEY_INDEX = 0  # Track which key to use next

# Cache IP for 60s - WWProxy IP lifetime is 20 min, min usage 60s
_CACHED_WWPROXY_IP = {}  # Store IP per key: {key: ip}
_CACHED_WWPROXY_TIME = {}  # Store time per key: {key: timestamp}
CACHE_DURATION = 60  # 60 seconds (1 minute)

def get_ip_status():
    """Get current IP status for admin - returns dict with IP and age info for both keys"""
    global _CACHED_WWPROXY_IP, _CACHED_WWPROXY_TIME
    
    current_time = time.time()
    status_list = []
    
    for i, key in enumerate(WWPROXY_KEYS):
        if key in _CACHED_WWPROXY_IP and key in _CACHED_WWPROXY_TIME:
            age_seconds = int(current_time - _CACHED_WWPROXY_TIME[key])
            age_minutes = age_seconds // 60
            remaining_seconds = CACHE_DURATION - age_seconds
            
            status_list.append({
                'key_index': i + 1,
                'ip': _CACHED_WWPROXY_IP[key],
                'age_seconds': age_seconds,
                'age_minutes': age_minutes,
                'remaining_seconds': max(0, remaining_seconds),
                'status': 'Active' if remaining_seconds > 0 else 'Expired'
            })
        else:
            status_list.append({
                'key_index': i + 1,
                'ip': None,
                'age_seconds': 0,
                'age_minutes': 0,
                'remaining_seconds': 0,
                'status': 'No IP cached'
            })
    
    return {
        'keys': status_list,
        'current_key_index': _CURRENT_KEY_INDEX + 1
    }

def force_rotate_ip():
    """Force clear IP cache for all keys to get new IPs on next request"""
    global _CACHED_WWPROXY_IP, _CACHED_WWPROXY_TIME
    
    old_ips = dict(_CACHED_WWPROXY_IP)
    _CACHED_WWPROXY_IP.clear()
    _CACHED_WWPROXY_TIME.clear()
    
    return {
        'old_ips': old_ips,
        'success': True,
        'message': 'All IP caches cleared - will fetch new IPs on next requests'
    }

def get_cached_ip(force_new_ip=False):
    """Fetch IP from WWProxy residential proxy API (Vietnam) with dual-key rotation"""
    global _CACHED_WWPROXY_IP, _CACHED_WWPROXY_TIME, _CURRENT_KEY_INDEX, WWPROXY_KEYS
    
    # Round-robin: select next key
    current_key = WWPROXY_KEYS[_CURRENT_KEY_INDEX]
    _CURRENT_KEY_INDEX = (_CURRENT_KEY_INDEX + 1) % len(WWPROXY_KEYS)  # Rotate to next key
    
    current_time = time.time()
    
    # Check if we have a cached IP for this key (less than 60s old)
    if current_key in _CACHED_WWPROXY_IP and current_key in _CACHED_WWPROXY_TIME:
        if (current_time - _CACHED_WWPROXY_TIME[current_key]) < CACHE_DURATION:
            age_seconds = int(current_time - _CACHED_WWPROXY_TIME[current_key])
            age_minutes = age_seconds // 60
            age_remaining = age_seconds % 60
            cached_ip = _CACHED_WWPROXY_IP[current_key]
            print(f"🔒 Using cached WWProxy IP (Key {_CURRENT_KEY_INDEX}): {cached_ip} (age: {age_minutes}m {age_remaining}s)")
            return cached_ip
    
    try:
        print(f"🌐 Fetching new IP from WWProxy (Key {_CURRENT_KEY_INDEX})...")
        
        # Build API URL with current key
        api_url = f"https://wwproxy.com/api/client/proxy/available?key={current_key}&provinceId=-1"
        response = requests.get(api_url, timeout=5)
        
        # Log response for debugging
        
        if response.status_code != 200:
            # Try to get error message
            try:
                error_data = response.json()
                print(f"❌ WWProxy API Error: {error_data}")
            except:
                print(f"❌ WWProxy API Error (text): {response.text[:200]}")
        
        if response.status_code == 200:
            # Try to parse JSON response
            try:
                data = response.json()
                
                # Extract IP from response (adjust based on actual API response format)
                # Common formats: {"ip": "1.2.3.4"} or {"data": {"ip": "1.2.3.4"}} or {"proxy": "1.2.3.4:port"}
                proxy_ip = None
                
                if isinstance(data, dict):
                    # WWProxy format: {"status": "OK", "data": {"ipAddress": "116.96.116.28", ...}}
                    if 'data' in data and isinstance(data['data'], dict):
                        if 'ipAddress' in data['data']:
                            proxy_ip = data['data']['ipAddress']
                        elif 'ip' in data['data']:
                            proxy_ip = data['data']['ip']
                        elif 'host' in data['data']:
                            proxy_ip = data['data']['host']
                    # Fallback formats
                    elif 'ip' in data:
                        proxy_ip = data['ip']
                    elif 'ipAddress' in data:
                        proxy_ip = data['ipAddress']
                    elif 'proxy' in data:
                        # Format: "ip:port" - extract IP only
                        proxy_ip = data['proxy'].split(':')[0]
                    elif 'host' in data:
                        proxy_ip = data['host']
                
                if proxy_ip:
                    print(f"✅ Got Vietnam residential IP from WWProxy (Key {_CURRENT_KEY_INDEX}): {proxy_ip}")
                    # Cache the IP for this key
                    _CACHED_WWPROXY_IP[current_key] = proxy_ip
                    _CACHED_WWPROXY_TIME[current_key] = current_time
                    return proxy_ip
                else:
                    print(f"⚠️ Could not extract IP from WWProxy response: {data}")
                    
            except Exception as e:
                print(f"⚠️ Failed to parse WWProxy JSON: {e}")
                # Try plain text response
                proxy_ip = response.text.strip()
                if proxy_ip and '.' in proxy_ip:
                    # Extract IP if format is "ip:port"
                    if ':' in proxy_ip:
                        proxy_ip = proxy_ip.split(':')[0]
                    print(f"✅ Got Vietnam residential IP from WWProxy (text): {proxy_ip}")
                    return proxy_ip
        
        print(f"❌ WWProxy API failed with status {response.status_code}")
        
    except Exception as e:
        print(f"❌ Error fetching from WWProxy: {e}")
    
    # Fallback: Try to use cached IP from ANY key (not Vercel IP)
    print(f"⚠️ Trying to use cached IP from other keys...")
    for key in WWPROXY_KEYS:
        if key in _CACHED_WWPROXY_IP and _CACHED_WWPROXY_IP[key]:
            cached_ip = _CACHED_WWPROXY_IP[key]
            cache_age = int(current_time - _CACHED_WWPROXY_TIME.get(key, 0))
            # Use cached IP even if expired (better than Vercel IP)
            if cache_age < 1200:  # Use if less than 20 minutes old (WWProxy IP lifetime)
                print(f"✅ Using cached WWProxy IP from another key: {cached_ip} (age: {cache_age}s)")
                return cached_ip
    
    # Try other keys that haven't been used recently
    for i, key in enumerate(WWPROXY_KEYS):
        if key == current_key:
            continue  # Skip current key that just failed
        try:
            print(f"🔄 Trying WWProxy Key {i}...")
            api_url = f"https://wwproxy.com/api/client/proxy/available?key={key}&provinceId=-1"
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and isinstance(data['data'], dict):
                    proxy_ip = data['data'].get('ipAddress') or data['data'].get('ip')
                    if proxy_ip:
                        print(f"✅ Got IP from WWProxy Key {i}: {proxy_ip}")
                        _CACHED_WWPROXY_IP[key] = proxy_ip
                        _CACHED_WWPROXY_TIME[key] = current_time
                        return proxy_ip
        except Exception as e:
            print(f"⚠️ Key {i} also failed: {e}")
            continue
    
    # Last resort: use any cached IP regardless of age
    for key in WWPROXY_KEYS:
        if key in _CACHED_WWPROXY_IP and _CACHED_WWPROXY_IP[key]:
            cached_ip = _CACHED_WWPROXY_IP[key]
            print(f"⚠️ Using old cached WWProxy IP as last resort: {cached_ip}")
            return cached_ip
    
    # Final fallback - only if no cached IP exists at all
    print(f"❌ No cached WWProxy IP available, using Vercel IP as last resort...")
    try:
        fallback_response = requests.get('https://api.ipify.org?format=text', timeout=3)
        if fallback_response.status_code == 200:
            fallback_ip = fallback_response.text.strip()
            print(f"⚠️ Using Vercel fallback IP (no WWProxy cache): {fallback_ip}")
            return fallback_ip
    except:
        pass
    
    # Final fallback
    print(f"❌ All IP services failed, using localhost")
    return "127.0.0.1"

def is_job_already_charged(job_id):
    """Check if job has already been charged using database and file lock"""
    import os
    import time
    
    # Check memory first (fast)
    if job_id in CHARGED_JOBS:
        print(f"⚠️ Job {job_id} already charged (memory check)")
        return True
    
    # Use file lock to prevent race conditions
    lock_file = f"/tmp/charge_lock_{job_id}.lock"
    try:
        # Check if lock file exists (another process is charging)
        if os.path.exists(lock_file):
            # Wait a bit and check again
            time.sleep(0.1)
            if job_id in CHARGED_JOBS:
                print(f"⚠️ Job {job_id} already charged (after lock wait)")
                return True
    except Exception as e:
        print(f"⚠️ Lock file check error: {e}")
    
    # Check database for transaction records (persistent)
    try:
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            # First check by job_id UUID in description (more precise)
            existing_tx = supabase.table('transactions').select('id').eq('type', 'verify').like('description', f'%Job {job_id}%').execute()
            if existing_tx.data:
                print(f"⚠️ Job {job_id} already charged (database check - description)")
                CHARGED_JOBS.add(job_id)  # Update memory cache
                return True
                
            # Also check for processing marker file
            marker_file = f"/tmp/processing_marker_{job_id}.lock"
            if os.path.exists(marker_file):
                print(f"⚠️ Job {job_id} already being processed (marker file check)")
                CHARGED_JOBS.add(job_id)  # Update memory cache
                return True
                
            # Also check by verification_jobs table for extra safety
            try:
                job_record = supabase.table('verification_jobs').select('id').eq('job_id', job_id).execute()
                if job_record.data:
                    verification_job_id = job_record.data[0]['id']
                    existing_tx_by_job_id = supabase.table('transactions').select('id').eq('type', 'verify').eq('job_id', verification_job_id).execute()
                    if existing_tx_by_job_id.data:
                        print(f"⚠️ Job {job_id} already charged (database check - job_id)")
                        CHARGED_JOBS.add(job_id)  # Update memory cache
                        return True
            except Exception as e:
                print(f"⚠️ Could not check by verification_jobs: {e}")
                
    except Exception as e:
        print(f"⚠️ Could not check database for job {job_id}: {e}")
    
    return False

def mark_job_as_charged(job_id):
    """Mark job as charged in memory, lock file, and database"""
    import os
    import time
    
    CHARGED_JOBS.add(job_id)
    
    # Create lock file
    try:
        lock_file = f"/tmp/charge_lock_{job_id}.lock"
        with open(lock_file, 'w') as f:
            f.write(str(time.time()))
        print(f"💰 Marked job {job_id} as charged with lock file")
    except Exception as e:
        print(f"⚠️ Could not create lock file: {e}")
    
    # Also create a database marker to prevent race conditions
    try:
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            # Create a simple file marker instead of database record
            marker_file = f"/tmp/processing_marker_{job_id}.lock"
            with open(marker_file, 'w') as f:
                f.write(f"processing_{int(time.time())}")
            print(f"💰 Created processing marker file for job {job_id}")
            print(f"💰 Created database marker for job {job_id}")
    except Exception as e:
        print(f"⚠️ Could not create database marker: {e}")
    
    print(f"💰 Marked job {job_id} as charged (memory + lock + database)")

def get_success_message_multilingual(job_id, payment_message, is_vip, cash, coins, user_lang='vi'):
    """Get multilingual success message for verification"""
    vip_text = {'vi': 'Có', 'en': 'Yes', 'zh': '是'}.get(user_lang, 'Có')
    no_vip_text = {'vi': 'Không', 'en': 'No', 'zh': '否'}.get(user_lang, 'Không')
    
    messages = {
        'vi': [
            "✅ VERIFY THÀNH CÔNG!",
            "",
            f"🆔 Job ID: `{job_id}`",
            "",
            f"💰 Thanh toán: {payment_message}",
            f"💎 VIP: {vip_text if is_vip else no_vip_text} | 💰 Cash: {cash} | 🌕 Xu: {coins}",
            "",
            "🎉 Verification thành công!"
        ],
        'en': [
            "✅ VERIFICATION SUCCESSFUL!",
            "",
            f"🆔 Job ID: `{job_id}`",
            "",
            f"💰 Payment: {payment_message}",
            f"💎 VIP: {vip_text if is_vip else no_vip_text} | 💰 Cash: {cash} | 🌕 Xu: {coins}",
            "",
            "🎉 Verification completed!"
        ],
        'zh': [
            "✅ 验证成功！",
            "",
            f"🆔 Job ID: `{job_id}`",
            "",
            f"💰 支付: {payment_message}",
            f"💎 VIP: {vip_text if is_vip else no_vip_text} | 💰 Cash: {cash} | 🌕 Xu: {coins}",
            "",
            "🎉 验证完成！"
        ]
    }
    return "\n".join(messages.get(user_lang, messages['vi']))

def send_notification_for_already_charged_job(job_id):
    """Send notification for job that was already charged"""
    try:
        from .supabase_client import get_verification_job_by_id, get_user_by_telegram_id
        from .telegram import is_notification_already_sent, mark_notification_sent
        
        # Check if notification already sent
        if is_notification_already_sent(job_id):
            print(f"⚠️ Notification already sent for job {job_id}")
            return
        
        # Get job info
        job_info = get_verification_job_by_id(job_id)
        if not job_info:
            print(f"❌ Job not found: {job_id}")
            return
        
        telegram_id = job_info.get('telegram_id')
        if not telegram_id:
            print(f"❌ No telegram_id found in job {job_id}")
            return
        
        # Get user info
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            print(f"❌ User not found for telegram_id {telegram_id}")
            return
        
        coins = user.get('coins', 0)
        cash = user.get('cash', 0)
        is_vip = user.get('is_vip', False)
        user_lang = user.get('language', 'vi')  # Get user language
        
        # Check recent transaction to determine payment method
        try:
            from .supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                from datetime import datetime, timedelta
                recent_time = (datetime.now() - timedelta(minutes=10)).isoformat()
                tx_response = supabase.table('transactions').select('*').eq('job_id', job_id).eq('type', 'verify').gte('created_at', recent_time).order('created_at', desc=True).limit(1).execute()
                
                if tx_response.data:
                    tx = tx_response.data[0]
                    if tx.get('amount', 0) == -10000:  # Cash deduction
                        payment_message = f"10 Cash (còn lại: {cash})"
                    else:  # Coins deduction
                        payment_message = f"10 xu (còn lại: {coins})"
                else:
                    payment_message = f"10 xu (còn lại: {coins})"
            else:
                payment_message = f"10 xu (còn lại: {coins})"
        except Exception as e:
            print(f"⚠️ Could not determine payment method: {e}")
            payment_message = f"10 xu (còn lại: {coins})"
        
        # Send notification
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if bot_token:
            mark_notification_sent(job_id)
            
            # Use multilingual message
            text_message = get_success_message_multilingual(job_id, payment_message, is_vip, cash, coins, user_lang)
            
            response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": str(telegram_id),
                    "text": text_message,
                    "parse_mode": "Markdown"
                },
                timeout=15
            )
            
            print(f"🔍 DEBUG: Telegram API response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                print(f"✅ Sent success notification to user {telegram_id} for already charged job")
            else:
                print(f"❌ Failed to send notification: {response.status_code} - {response.text}")
        else:
            print("❌ TELEGRAM_BOT_TOKEN not found")
            
    except Exception as e:
        print(f"⚠️ Failed to send notification for already charged job: {e}")
        import traceback
        traceback.print_exc()

def send_seller_webhook(seller_id, job_id, status, result_data):
    """Send webhook notification to seller when verification completes"""
    try:
        from .supabase_client import get_supabase_client
        from .seller_api import update_seller_job, refund_seller_credit
        
        supabase = get_supabase_client()
        if not supabase:
            print(f"❌ Cannot send seller webhook - no database connection")
            return False
        
        # Get seller info
        seller_result = supabase.table('sellers').select('webhook_url').eq('id', seller_id).execute()
        if not seller_result.data:
            print(f"❌ Seller {seller_id} not found")
            return False
        
        webhook_url = seller_result.data[0].get('webhook_url')
        
        # Update seller job status
        update_seller_job(job_id, status, result_data)
        
        # If failed, refund credit
        if status == 'failed':
            refund_seller_credit(seller_id)
            print(f"💰 Refunded credit to seller {seller_id} for failed job {job_id}")
        
        # Send webhook if URL configured
        if webhook_url:
            webhook_data = {
                'event': f'verification.{status}',
                'job_id': job_id,
                'status': status,
                'data': result_data,
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                response = requests.post(
                    webhook_url,
                    json=webhook_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                if response.status_code == 200:
                    print(f"✅ Sent webhook to seller {seller_id}: {webhook_url}")
                else:
                    print(f"⚠️ Webhook response {response.status_code} from {webhook_url}")
            except Exception as e:
                print(f"❌ Failed to send webhook to {webhook_url}: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Error in send_seller_webhook: {e}")
        return False

def process_completed_job_charging(job_id, cached_job_info=None):
    """Process charging for a completed verification job
    cached_job_info: Optional job info from update_verification_job_status to avoid re-query
    """
    print(f"💰 DEBUG: Starting charging process for job {job_id}")
    
    # Check if already charged
    if is_job_already_charged(job_id):
        print(f"⚠️ Job {job_id} already charged, skipping")
        # Still send notification if not already sent
        send_notification_for_already_charged_job(job_id)
        return False
    
    # Add timestamp to prevent rapid duplicate calls
    import time
    current_time = time.time()
    if hasattr(process_completed_job_charging, '_last_charged'):
        if current_time - process_completed_job_charging._last_charged.get(job_id, 0) < 5:
            print(f"⚠️ Job {job_id} charged too recently, skipping")
            return False
    
    if not hasattr(process_completed_job_charging, '_last_charged'):
        process_completed_job_charging._last_charged = {}
    process_completed_job_charging._last_charged[job_id] = current_time
    
    try:
        from .supabase_client import get_user_by_telegram_id, get_supabase_client, get_verification_job_by_id
        
        # OPTIMIZED: Use cached job_info if available, otherwise query
        if cached_job_info:
            job_info = cached_job_info
            print(f"⚡ Using cached job_info (skipped 1 query)")
        else:
            job_info = get_verification_job_by_id(job_id)
        
        if not job_info:
            print(f"❌ Job not found: {job_id}")
            return False
        
        telegram_id = job_info.get('telegram_id')
        if not telegram_id:
            print(f"❌ No telegram_id found in job {job_id}")
            return False
        
        # Get user info (still need this query)
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            print(f"❌ User not found for telegram_id {telegram_id}")
            return False
        
        coins = user.get('coins', 0)
        cash = user.get('cash', 0)
        is_vip = user.get('is_vip', False)
        user_lang = user.get('language', 'vi')  # Get user language for multilingual messages
        
        print(f"💰 User {telegram_id} - BEFORE charging: coins: {coins}, cash: {cash}, is_vip: {is_vip}")
        
        # Mark as charged first to prevent race conditions
        mark_job_as_charged(job_id)
        
        # VIP users get FREE student verification
        if is_vip:
            new_coins = coins
            new_cash = cash
            payment_message = "MIỄN PHÍ (VIP)"
            print(f"⭐ VIP user {telegram_id} - FREE verification!")
        # Calculate payment - Non-VIP users pay 10 xu or 10 cash
        elif coins >= 10:
            # Use xu first
            new_coins = coins - 10
            new_cash = cash
            payment_message = f"10 xu (còn lại: {new_coins} xu)"
            print(f"✅ Charged 10 xu from user {telegram_id}: {coins} -> {new_coins}")
        elif cash >= 10:
            # Use cash if not enough xu
            new_coins = coins
            new_cash = cash - 10
            payment_message = f"10 cash (còn lại: {new_cash} cash)"
            print(f"✅ Charged 10 cash from user {telegram_id}: {cash} -> {new_cash}")
        else:
            # Not enough money - this shouldn't happen as it should be checked before verification
            print(f"❌ User {telegram_id} insufficient funds: {coins} xu, {cash} cash")
            return False
        
        # Update user balance
        supabase = get_supabase_client()
        if supabase:
            from datetime import datetime
            response = supabase.table('users').update({
                'coins': new_coins,
                'cash': new_cash,
                'updated_at': datetime.now().isoformat()
            }).eq('telegram_id', str(telegram_id)).execute()
            
            if response.data:
                print(f"✅ Updated user balance for {telegram_id}")
                print(f"💰 User {telegram_id} - AFTER charging: coins: {new_coins}, cash: {new_cash}")
                
                # Create transaction record for ALL users (VIP and non-VIP)
                try:
                    if new_coins != coins or new_cash != cash:
                        transaction_data = {
                            'user_id': user.get('id'),
                            'type': 'verify_cash' if new_cash != cash else 'verify',
                            'amount': -10000 if new_cash != cash else -10000,  # -10000 VND for cash or xu
                            'coins': -10 if new_cash != cash else -10,
                            'description': f'Verify SheerID - Job {job_id}',
                            'status': 'completed',
                            'job_id': None,
                            'created_at': datetime.now().isoformat()
                        }
                        
                        supabase.table('transactions').insert(transaction_data).execute()
                        print(f"✅ Created transaction record for job {job_id} (VIP: {is_vip})")
                except Exception as e:
                    print(f"⚠️ Failed to create transaction record: {e}")
                
                # Send success notification (optimized with shorter timeout)
                try:
                    from .telegram import is_notification_already_sent, mark_notification_sent
                    
                    already_sent = is_notification_already_sent(job_id)
                    
                    if not already_sent:
                        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                        if bot_token:
                            mark_notification_sent(job_id)
                            
                            # Use multilingual message
                            text_message = get_success_message_multilingual(job_id, payment_message, is_vip, new_cash, new_coins, user_lang)
                            
                            # OPTIMIZATION: Use shorter timeout (5s instead of 15s)
                            try:
                                response = requests.post(
                                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                    json={
                                        "chat_id": str(telegram_id),
                                        "text": text_message,
                                        "parse_mode": "Markdown"
                                    },
                                    timeout=5
                                )
                                if response.status_code == 200:
                                    print(f"✅ Sent success notification to user {telegram_id}")
                            except requests.exceptions.Timeout:
                                print(f"⚠️ Telegram notification timeout (will retry later)")
                except Exception as e:
                    print(f"⚠️ Failed to send notification: {e}")
                
                return True
            else:
                print(f"❌ Failed to update user balance")
                return False
        else:
            print(f"❌ Supabase client not available")
            return False
            
    except Exception as e:
        print(f"❌ Error processing charging for job {job_id}: {e}")
        return False

# Try to import curl_cffi for better SOCKS5 support
try:
    from curl_cffi.requests import Session as CurlSession
    from curl_cffi.requests.exceptions import RequestException as CurlRequestException
    CURL_CFFI_AVAILABLE = True
    print("✅ curl_cffi loaded for SOCKS5H proxy support")
except ImportError:
    CURL_CFFI_AVAILABLE = False
    print("⚠️ curl_cffi not available, falling back to requests")

# Global curl_cffi session for connection reuse
_curl_session = None

def get_curl_session():
    """Get or create curl_cffi session with browser impersonation"""
    global _curl_session
    if _curl_session is None and CURL_CFFI_AVAILABLE:
        _curl_session = CurlSession(impersonate="chrome124")
    return _curl_session

def make_request(method, url, use_teacher_proxy=False, use_scrape_proxy=False, max_retries=3, session_id=None, country=None, **kwargs):
    """Make HTTP request with SOCKS5H rotating proxy support using curl_cffi
    
    IMPORTANT: Uses sticky session to keep same IP for entire verification flow
    
    Args:
        use_teacher_proxy: Use US proxy for teacher verification (legacy)
        use_scrape_proxy: Use ScrapeGW SOCKS5H rotating proxy (recommended)
        max_retries: Number of retries for transient errors (default 3)
        session_id: Unique session ID for sticky proxy (same IP for all requests with same session_id)
        country: Country code for geo-targeting (e.g., 'us', 'uk', 'de') - CRITICAL for fraud prevention
    """
    timeout = kwargs.pop('timeout', 30)
    
    # Build proxy URL if needed
    proxy_url = None
    if use_scrape_proxy or use_teacher_proxy:
        # SOCKS5 proxy credentials - NEW PROXY December 2024
        scrape_host = 'rp.scrapegw.com'
        scrape_port = '6060'
        scrape_pass = '4zqo673ns3fpmd1'
        scrape_user_base = 'hgave8blvs7dfox'
        
        # CRITICAL: Use sticky session to keep same IP for entire verification flow
        # Format: username-session-{session_id}-country-{code} keeps same IP for all requests
        # Session lasts ~10 minutes on ScrapeGW
        # Country targeting is CRITICAL to avoid fraud detection (IP must match university country)
        if session_id:
            # Sticky session: same IP for all requests with this session_id
            if country:
                # With country targeting (recommended for fraud prevention)
                scrape_user = f'{scrape_user_base}-session-{session_id}-country-{country.lower()}'
            else:
                scrape_user = f'{scrape_user_base}-session-{session_id}-country-us'
            if not hasattr(make_request, f'_session_logged_{session_id}'):
                country_info = f", country={country.upper()}" if country else ", country=US"
                print(f"🔒 Using STICKY session proxy: session={session_id}{country_info}")
                setattr(make_request, f'_session_logged_{session_id}', True)
        else:
            # Rotating: new IP per request (default US)
            if country:
                scrape_user = f'{scrape_user_base}-odds-5+100-country-{country.lower()}'
            else:
                scrape_user = f'{scrape_user_base}-odds-5+100-country-us'
        
        # CRITICAL: Use socks5:// for SOCKS5 proxy
        proxy_url = f"socks5://{scrape_user}:{scrape_pass}@{scrape_host}:{scrape_port}"
        
        if not hasattr(make_request, '_proxy_logged'):
            print(f"🌐 Using SOCKS5 proxy: {scrape_host}:{scrape_port}")
            make_request._proxy_logged = True
        
        # Log proxy info for each request (only non-polling or first request)
        # Skip logging for polling GET requests to reduce noise
        is_polling_request = method.lower() == 'get' and '/rest/v2/verification/' in url and '/step/' not in url
        if not is_polling_request:
            session_info = f" [session={session_id}]" if session_id else " [rotating]"
            print(f"📡 Proxy request: {method.upper()} {url[:80]}...{session_info}")
    
    # Use curl_cffi if available (better SOCKS5 support)
    if CURL_CFFI_AVAILABLE and proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                session = get_curl_session()
                method_lower = method.lower()
                if method_lower == 'get':
                    response = session.get(url, proxies=proxies, timeout=timeout, **kwargs)
                elif method_lower == 'post':
                    response = session.post(url, proxies=proxies, timeout=timeout, **kwargs)
                elif method_lower == 'delete':
                    response = session.delete(url, proxies=proxies, timeout=timeout, **kwargs)
                elif method_lower == 'put':
                    response = session.put(url, proxies=proxies, timeout=timeout, **kwargs)
                elif method_lower == 'patch':
                    response = session.patch(url, proxies=proxies, timeout=timeout, **kwargs)
                else:
                    response = session.request(method_lower, url, proxies=proxies, timeout=timeout, **kwargs)
                return response
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                # Retry on transient errors (common with rotating proxies)
                retryable = any(x in error_str for x in [
                    'timeout', 'connection', 'aborted', 'reset', 'closed', 
                    'ssl', 'tls', 'proxy', 'perform', 'curl'
                ])
                if retryable and attempt < max_retries - 1:
                    retry_delay = 1.0 * (attempt + 1)  # Exponential backoff
                    print(f"⚠️ Proxy error (attempt {attempt + 1}/{max_retries}): {str(e)[:50]}... retrying in {retry_delay}s")
                    time.sleep(retry_delay)
                    continue
                raise
        raise last_exception
    
    # Fallback to requests library
    if proxy_url:
        kwargs['proxies'] = {'http': proxy_url, 'https': proxy_url}
    kwargs['timeout'] = timeout
    
    method_lower = method.lower()
    if method_lower == 'get':
        return requests.get(url, **kwargs)
    elif method_lower == 'post':
        return requests.post(url, **kwargs)
    elif method_lower == 'delete':
        return requests.delete(url, **kwargs)
    elif method_lower == 'put':
        return requests.put(url, **kwargs)
    elif method_lower == 'patch':
        return requests.patch(url, **kwargs)
    else:
        return requests.request(method_lower, url, **kwargs)
try:
    from .supabase_client import get_user_by_telegram_id as get_user_from_supabase, add_coins_to_user as add_coins_to_user_in_supabase
    print("✅ Supabase client loaded successfully in index.py")
    SUPABASE_AVAILABLE = True
except ImportError as e:
    print(f"❌ Supabase client not found: {e}")
    print("🔄 Falling back to SQLite")
    SUPABASE_AVAILABLE = False
except Exception as e:
    print(f"❌ Error loading Supabase client: {e}")
    print("🔄 Falling back to SQLite")
    SUPABASE_AVAILABLE = False

# Fallback functions - use SQLite instead
def get_user_from_supabase(telegram_id):
    print(f"🔍 SUPABASE_AVAILABLE: {SUPABASE_AVAILABLE}")
    if SUPABASE_AVAILABLE:
        print(f"🔄 Using Supabase: Getting user: {telegram_id}")
        try:
            from .supabase_client import get_user_by_telegram_id
            user = get_user_by_telegram_id(telegram_id)
            if user:
                print(f"✅ Found user in Supabase: {user}")
                return user
            else:
                print(f"❌ User {telegram_id} not found in Supabase")
                return None
        except Exception as e:
            print(f"❌ Supabase error: {e}")
            print("🔄 Falling back to SQLite")
    else:
        print(f"❌ Supabase not available, using SQLite fallback")
    
    print(f"🔄 Fallback: Getting user from SQLite: {telegram_id}")
    # Direct SQLite query to avoid infinite loop
    try:
        conn = sqlite3.connect('/tmp/sheerid_bot.db')
        cursor = conn.cursor()
        
        # Create tables if not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                coins INTEGER DEFAULT 0,
                is_vip BOOLEAN DEFAULT 0,
                vip_expiry DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(255) UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                sheerid_url TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                student_info TEXT,
                card_filename VARCHAR(255),
                upload_result TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            user = {
                'id': user_data[0],
                'telegram_id': str(user_data[1]),
                'username': user_data[2],
                'first_name': user_data[3],
                'last_name': user_data[4],
                'coins': user_data[5],
                'is_vip': bool(user_data[6]),
                'vip_expiry': user_data[7],
                'created_at': user_data[8],
                'updated_at': user_data[9]
            }
            
            # Auto-check VIP expiry and revoke if expired
            if user['is_vip'] and user['vip_expiry']:
                try:
                    from datetime import datetime
                    expiry = datetime.fromisoformat(user['vip_expiry'].replace('Z', '+00:00')) if isinstance(user['vip_expiry'], str) else user['vip_expiry']
                    if expiry and datetime.now(expiry.tzinfo if expiry.tzinfo else None) > expiry:
                        print(f"⏰ VIP expired for user {telegram_id}, auto-revoking...")
                        conn2 = sqlite3.connect('/tmp/sheerid_bot.db')
                        cursor2 = conn2.cursor()
                        cursor2.execute('UPDATE users SET is_vip = 0, vip_expiry = NULL WHERE telegram_id = ?', (telegram_id,))
                        conn2.commit()
                        conn2.close()
                        user['is_vip'] = False
                        user['vip_expiry'] = None
                        print(f"✅ VIP revoked for user {telegram_id}")
                except Exception as vip_err:
                    print(f"⚠️ Error checking VIP expiry: {vip_err}")
            
            return user
        return None
        
    except Exception as e:
        print(f"❌ Error in fallback get_user: {e}")
        return None

def add_coins_to_user_in_supabase(telegram_id, coins, transaction_info):
    if SUPABASE_AVAILABLE:
        print(f"🔄 Using Supabase: Adding coins: {telegram_id}")
        try:
            from .supabase_client import add_coins_to_user
            return add_coins_to_user(telegram_id, coins, transaction_info)
        except Exception as e:
            print(f"❌ Supabase error: {e}")
            print("🔄 Falling back to SQLite")
    
    print(f"🔄 Fallback: Adding coins in SQLite: {telegram_id}")
    # Direct SQLite query to avoid infinite loop
    try:
        conn = sqlite3.connect('/tmp/sheerid_bot.db')
        cursor = conn.cursor()
        
        # Get current user
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            conn.close()
            return False
        
        current_coins = user_data[5]
        new_coins = current_coins + coins
        
        # Update coins
        cursor.execute('''
            UPDATE users 
            SET coins = ?, updated_at = ?
            WHERE telegram_id = ?
        ''', (new_coins, datetime.now().isoformat(), telegram_id))
        
        # Insert transaction record
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, coins, description, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_data[0], 'deposit', coins * 1000, coins, transaction_info, 'completed', datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Added {coins} coins to user {telegram_id}. New balance: {new_coins}")
        return True
        
    except Exception as e:
        print(f"❌ Error adding coins: {e}")
        return False
    
def find_user_in_telegram_database(telegram_id):
    if SUPABASE_AVAILABLE:
        print(f"🔄 Using Supabase: Finding user in Telegram database: {telegram_id}")
        try:
            from .supabase_client import find_user_in_telegram_database as supabase_find
            return supabase_find(telegram_id)
        except Exception as e:
            print(f"❌ Supabase error: {e}")
            print("🔄 Falling back to SQLite")
    
    print(f"🔄 Fallback: Finding user in Telegram database: {telegram_id}")
    # Direct file query to avoid infinite loop
    try:
        user_file = f"/tmp/user_{telegram_id}.json"
        if os.path.exists(user_file):
            with open(user_file, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
                return user_data
        return None
    except Exception as e:
        print(f"❌ Error finding user in Telegram database: {e}")
        return None

def sync_user_from_telegram_database(telegram_user):
    if SUPABASE_AVAILABLE:
        print(f"🔄 Using Supabase: Syncing user from Telegram database")
        try:
            from .supabase_client import sync_user_from_telegram_database as supabase_sync
            return supabase_sync(telegram_user)
        except Exception as e:
            print(f"❌ Supabase error: {e}")
            print("🔄 Falling back to SQLite")
    
    print(f"🔄 Fallback: Syncing user from Telegram database")
    # Direct SQLite query to avoid infinite loop
    try:
        conn = sqlite3.connect('/tmp/sheerid_bot.db')
        cursor = conn.cursor()
        
        # Create tables if not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                coins INTEGER DEFAULT 0,
                is_vip BOOLEAN DEFAULT 0,
                vip_expiry DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(255) UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                sheerid_url TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                student_info TEXT,
                card_filename VARCHAR(255),
                upload_result TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Insert or update user
        cursor.execute('''
            INSERT OR REPLACE INTO users (telegram_id, username, first_name, last_name, coins, is_vip, vip_expiry, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            telegram_user.get('telegram_id'),
            telegram_user.get('username'),
            telegram_user.get('first_name'),
            telegram_user.get('last_name'),
            telegram_user.get('coins', 0),
            telegram_user.get('is_vip', False),
            telegram_user.get('vip_expiry'),
            telegram_user.get('created_at'),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ User synced successfully from Telegram database")
        # Return user data directly instead of calling get_user_by_telegram_id
        return {
            'id': telegram_user.get('id'),
            'telegram_id': str(telegram_user.get('telegram_id')),
            'username': telegram_user.get('username'),
            'first_name': telegram_user.get('first_name'),
            'last_name': telegram_user.get('last_name'),
            'coins': telegram_user.get('coins', 0),
            'is_vip': telegram_user.get('is_vip', False),
            'vip_expiry': telegram_user.get('vip_expiry'),
            'created_at': telegram_user.get('created_at'),
            'updated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error syncing user from Telegram database: {e}")
        return None

def sync_coins_to_telegram_file(telegram_id):
    if SUPABASE_AVAILABLE:
        print(f"🔄 Using Supabase: Syncing coins to Telegram file: {telegram_id}")
        try:
            from .supabase_client import sync_coins_to_telegram_file as supabase_sync
            return supabase_sync(telegram_id)
        except Exception as e:
            print(f"❌ Supabase error: {e}")
            print("🔄 Falling back to SQLite")
    
    print(f"🔄 Fallback: Syncing coins to Telegram file: {telegram_id}")
    # Direct file update to avoid infinite loop
    try:
        # Get updated user data from SQLite directly
        conn = sqlite3.connect('/tmp/sheerid_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            print(f"❌ User not found in SQLite: {telegram_id}")
            return False
        
        # Convert tuple to dict format
        user_data = {
            'id': user[0],
            'telegram_id': str(user[1]),
            'username': user[2],
            'first_name': user[3],
            'last_name': user[4],
            'coins': user[5],
            'is_vip': bool(user[6]),
            'vip_expiry': user[7],
            'created_at': user[8],
            'updated_at': datetime.now().isoformat()
        }
        
        # Update Telegram database file
        user_file = f"/tmp/user_{telegram_id}.json"
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Coins synced to Telegram file: {user_data['coins']} xu")
        return True
        
    except Exception as e:
        print(f"❌ Error syncing coins to Telegram file: {e}")
        return False
TMP_DIR = "/tmp"
BASE_DIR = os.path.dirname(__file__)
# Use US template for US students (Dartmouth College)
GERMANY_TEMPLATE = os.path.join(BASE_DIR, "card-template-germany.png")
INDONESIA_TEMPLATE = os.path.join(BASE_DIR, "card-template-indonesia.png")
US_TEMPLATE = os.path.join(BASE_DIR, "card-template-us.png")
UK_TEMPLATE = os.path.join(BASE_DIR, "card-template-uk.png")
UK_TEMPLATE_2 = os.path.join(BASE_DIR, "card-template-uk2.png")
UK_TEMPLATE_3 = os.path.join(BASE_DIR, "card-template-uk3.png")
UK_TEMPLATE_4 = os.path.join(BASE_DIR, "card-template-uk4.png")
UK_TEMPLATE_5 = os.path.join(BASE_DIR, "card-template-uk5.png")
UK_TEMPLATE_6 = os.path.join(BASE_DIR, "card-template-uk6.png")
UK_TEMPLATE_7 = os.path.join(BASE_DIR, "card-template-uk7.png")
UK_TEMPLATE_8 = os.path.join(BASE_DIR, "card-template-uk8.png")
TEACHER_TEMPLATE = os.path.join(BASE_DIR, "card-template-teacher.png")
TEMPLATE_PATH = UK_TEMPLATE  # Use UK template globally

# University rotation configuration - Art Institute universities
# Import from universities_config.py (single source of truth)
try:
    from .universities_config import UNIVERSITIES as ART_INSTITUTE_UNIVERSITIES
    from .universities_config import get_random_university as get_random_art_institute
except ImportError:
    from universities_config import UNIVERSITIES as ART_INSTITUTE_UNIVERSITIES
    from universities_config import get_random_university as get_random_art_institute

# UNIVERSITIES dùng cho SheerID API - reference từ universities_config
UNIVERSITIES = ART_INSTITUTE_UNIVERSITIES

# Hidden universities for later use:
# US Universities:
# {"id": 1320, "idExtended": "1320", "name": "Georgia State University (Atlanta, GA)"}
# {"id": 1301, "idExtended": "1301", "name": "George Mason University (Fairfax, VA)"}
# {"id": 10279637, "idExtended": "10279637", "name": "Institute of Child Nutrition (University, MS)"}
# {"id": 3721, "idExtended": "3721", "name": "University of Vermont (Burlington, VT)"}
# {"id": 1876, "idExtended": "1876", "name": "Loyola University Chicago"}
# {"id": 1862, "idExtended": "1862", "name": "Louisiana State University"}
# {"id": 1828, "idExtended": "1828", "name": "Lone Star College System (The Woodlands, TX)"}
# {"id": 1852, "idExtended": "1852", "name": "Los Angeles Pierce College (Woodland Hills, CA)"}
# {"id": 1860, "idExtended": "1860", "name": "Louisiana Christian University (Pineville, LA)"}

def get_random_university():
    """Get a random university from the rotation list"""
    return random.choice(UNIVERSITIES)

# Predefine font paths bundled with the function (more reliable on Vercel)
DEJAVU_REG = os.path.join(BASE_DIR, "DejaVuSans.ttf")
DEJAVU_BOLD = os.path.join(BASE_DIR, "DejaVuSans-Bold.ttf")

app = Flask(__name__, static_folder='..', static_url_path='')

# Register Seller API Blueprint
try:
    from .seller_api import seller_bp
    app.register_blueprint(seller_bp)
    print("✅ Seller API Blueprint registered")
except Exception as e:
    print(f"⚠️ Could not register Seller API Blueprint: {e}")

# Register Teacher Browserless Blueprint (for fraud bypass)
try:
    from .teacher_browserless import teacher_browserless_bp
    app.register_blueprint(teacher_browserless_bp)
    print("✅ Teacher Browserless Blueprint registered")
except Exception as e:
    print(f"⚠️ Could not register Teacher Browserless Blueprint: {e}")

# Register Red Envelope Simple Blueprint (no complex dependencies)
try:
    from .red_envelope_simple import red_envelope_simple_bp
    app.register_blueprint(red_envelope_simple_bp)
    print("✅ Red Envelope Simple Blueprint registered")
except Exception as e:
    print(f"⚠️ Could not register Red Envelope Simple Blueprint: {e}")

# Register Locket Web Blueprint (web-based Locket Gold activation)
try:
    from .locket_web import locket_web_bp
    app.register_blueprint(locket_web_bp)
    print("✅ Locket Web Blueprint registered")
    
    # Also register recent-purchases as a direct route for redundancy
    from .locket_web import get_recent_purchases
    app.add_url_rule('/api/locket/recent-purchases', 'recent_purchases_direct', get_recent_purchases, methods=['GET'])
    print("✅ Recent purchases direct route registered")
except Exception as e:
    print(f"⚠️ Could not register Locket Web Blueprint: {e}")
    import traceback
    traceback.print_exc()

# Register Locket Analytics Blueprint (dashboard analytics)
try:
    from .locket_analytics import locket_analytics_bp
    app.register_blueprint(locket_analytics_bp)
    print("✅ Locket Analytics Blueprint registered")
except Exception as e:
    print(f"⚠️ Could not register Locket Analytics Blueprint: {e}")
    import traceback
    traceback.print_exc()

# Register Red Envelope Production Blueprint with Dynamic Spawn Service
try:
    from .red_envelope_production import red_envelope_prod_bp
    app.register_blueprint(red_envelope_prod_bp)
    print("✅ Red Envelope Production Blueprint registered")
    
    # Start Dynamic Spawn Service
    from .dynamic_spawn_service import start_spawn_service
    start_spawn_service()
    print("✅ Dynamic Spawn Service started")
except Exception as e:
    print(f"⚠️ Could not register Red Envelope Production or start Dynamic Spawn Service: {e}")

# Register iOS Profile Generator Blueprint
try:
    from .ios_profile_generator import ios_profile_bp
    app.register_blueprint(ios_profile_bp)
    print("✅ iOS Profile Generator Blueprint registered")
except Exception as e:
    print(f"⚠️ Could not register iOS Profile Generator Blueprint: {e}")

# Register iOS Certificate Profile Blueprint
try:
    from .ios_certificate_profile import ios_cert_profile_bp
    app.register_blueprint(ios_cert_profile_bp)
    print("✅ iOS Certificate Profile Blueprint registered")
except Exception as e:
    print(f"⚠️ Could not register iOS Certificate Profile Blueprint: {e}")

# Register Realtime Visitors Tracking Routes
try:
    from .realtime_visitors import track_visitor, get_active_visitors, get_visitor_stats
    
    @app.route('/api/track-visitor', methods=['POST'])
    def api_track_visitor():
        return track_visitor()
    
    @app.route('/api/active-visitors', methods=['GET'])
    def api_active_visitors():
        return get_active_visitors()
    
    @app.route('/api/visitor-stats', methods=['GET'])
    def api_visitor_stats():
        return get_visitor_stats()
    
    print("✅ Realtime Visitors Tracking routes registered")
except Exception as e:
    print(f"⚠️ Realtime Visitors Tracking not registered: {e}")
    import traceback
    traceback.print_exc()


def get_random_avatar():
    """Lấy avatar ngẫu nhiên từ folder face-id - hỗ trợ jpg/jpeg/png/webp; có fallback"""
    face_files = []
    patterns = ["*.jpg", "*.jpeg", "*.png", "*.webp"]
    # Prefer avatars co-located with the serverless function
    for ext in patterns:
        face_files += glob.glob(os.path.join(BASE_DIR, "face-id", ext))
    # Fallback to project root (useful on localhost)
    for ext in patterns:
        face_files += glob.glob(os.path.join("face-id", ext))
    # Additional fallback for api/face-id
    for ext in patterns:
        face_files += glob.glob(os.path.join("api", "face-id", ext))
    
    print(f"🔍 DEBUG: Found {len(face_files)} face files:")
    for i, f in enumerate(face_files[:10]):  # Show first 10 files
        print(f"  {i+1}. {f}")
    if len(face_files) > 10:
        print(f"  ... and {len(face_files) - 10} more files")
    
    if not face_files:
        # Fallback: tạo avatar đơn giản
        print("Không tìm thấy folder face-id, tạo avatar mẫu...")
        return create_fallback_avatar()
    chosen = random.choice(face_files)
    print(f"🖼️ DEBUG: Selected face file → {chosen}")
    return chosen

def create_fallback_avatar():
    """Tạo avatar mẫu đơn giản khi không có folder face-id"""
    try:
        # Tạo ảnh avatar mẫu đơn giản
        avatar = Image.new('RGB', (192, 256), (200, 200, 200))  # Màu xám
        draw = ImageDraw.Draw(avatar)
        
        # Vẽ hình tròn đơn giản
        draw.ellipse([50, 50, 142, 142], fill=(100, 150, 200))  # Màu xanh
        
        # Lưu avatar tạm vào /tmp để phù hợp serverless
        avatar_path = os.path.join(TMP_DIR, "fallback_avatar.jpg")
        avatar.save(avatar_path, 'JPEG')
        return avatar_path
    except Exception as e:
        print(f"Error creating fallback avatar: {e}")
        # Trả về None để code khác xử lý
        return None

def generate_indonesia_student_id(enrollment_year: int = None, faculty_code: str = None) -> str:
    """Generate Indonesian-style student ID: YYYYXXZZZZZ.
    - YYYY: enrollment year (default: current year)
    - XX: faculty/program code (2 digits, default: random 01-99)
    - ZZZZZ: unique sequence (5 digits)
    """
    try:
        from datetime import datetime
        year = enrollment_year if enrollment_year else datetime.now().year
        year_str = f"{int(year):04d}"
    except Exception:
        year_str = "2024"
    if not faculty_code or not str(faculty_code).isdigit():
        # import random as _rnd  # Using global import
        faculty_code = f"{random.randint(1,99):02d}"
    else:
        faculty_code = f"{int(faculty_code):02d}"
    # import random as _rnd  # Using global import
    seq = f"{random.randint(0,99999):05d}"
    return f"{year_str}{faculty_code}{seq}"

def create_teacher_card(teacher_info, avatar_path, template_path=TEMPLATE_PATH):
    """Tạo thẻ giáo viên từ template - for ChatGPT Teacher verification"""
    try:
        # Debug: template path and existence
        try:
            print(f"🎓 DEBUG: Creating teacher card with TEMPLATE_PATH={template_path} exists={os.path.exists(template_path)}")
        except Exception:
            pass
        # Mở template
        template = Image.open(template_path)
        template = template.convert('RGBA')
        
        # Tạo canvas mới
        card = Image.new('RGBA', template.size, (255, 255, 255, 0))
        card.paste(template, (0, 0))
        
        # Load avatar - có fallback
        if not avatar_path or not os.path.exists(avatar_path):
            print("Avatar không tồn tại, tạo avatar mẫu...")
            avatar_path = create_fallback_avatar()
            if not avatar_path:
                raise Exception("Không thể tạo avatar!")
        
        avatar = Image.open(avatar_path)
        # Resize avatar to fit card
        avatar = avatar.resize((1, 1), Image.Resampling.LANCZOS)
        # Paste avatar at specific position
        card.paste(avatar, (9999, 9999))
        
        # Fonts
        try:
            name_font = ImageFont.truetype("arialbd.ttf", 20)
            id_font = ImageFont.truetype("arialbd.ttf", 20)
            info_font = ImageFont.truetype("arial.ttf", 1)
        except Exception:
            try:
                if os.path.exists(DEJAVU_REG):
                    name_font = ImageFont.truetype(DEJAVU_BOLD, 20)
                    id_font = ImageFont.truetype(DEJAVU_BOLD, 20)
                    info_font = ImageFont.truetype(DEJAVU_REG, 27)
                else:
                    raise RuntimeError("No truetype fonts available")
            except Exception:
                name_font = ImageFont.load_default()
                info_font = ImageFont.load_default()
                id_font = ImageFont.load_default()
        
        draw = ImageDraw.Draw(card)
        
        # Teacher card coordinates (using UK template style)
        name_xy = (220, 165)
        id_xy = (1050, 165)
        
        # Draw teacher info - Title Case (capitalize first letter only)
        full_name = f"{teacher_info.get('name', '')}".replace(',', ' ').strip()
        if full_name:
            formatted_name = full_name.title()  # Title Case: Michelle Taylor
        else:
            first_name_val = f"{teacher_info.get('first_name', '')}".replace(',', ' ').strip()
            last_name_val = f"{teacher_info.get('last_name', '')}".replace(',', ' ').strip()
            formatted_name = f"{first_name_val} {last_name_val}".strip().title()  # Title Case: Michelle Taylor
        
        teacher_id = f"{teacher_info.get('teacher_id', teacher_info.get('student_id', '00000000'))}"
        
        draw.text(name_xy, formatted_name, fill=(0, 0, 0), font=name_font or ImageFont.load_default())
        draw.text(id_xy, teacher_id, fill=(0, 0, 0), font=id_font or ImageFont.load_default())
        
        print(f"🎓 DEBUG: Teacher card created successfully for {formatted_name}")
        return card
        
    except Exception as e:
        print(f"❌ Error creating teacher card: {e}")
        return None

def create_student_card(student_info, avatar_path, template_path=TEMPLATE_PATH):
    """Tạo thẻ sinh viên từ template"""
    try:
        # Debug: template path and existence
        try:
            print(f"DEBUG: TEMPLATE_PATH={template_path} exists={os.path.exists(template_path)}")
        except Exception:
            pass
        # Mở template
        template = Image.open(template_path)
        template = template.convert('RGBA')
        
        # Tạo canvas mới
        card = Image.new('RGBA', template.size, (255, 255, 255, 0))
        card.paste(template, (0, 0))
        
        # Load avatar - có fallback
        if not avatar_path or not os.path.exists(avatar_path):
            print("Avatar không tồn tại, tạo avatar mẫu...")
            avatar_path = create_fallback_avatar()
            if not avatar_path:
                raise Exception("Không thể tạo avatar!")
        
        avatar = Image.open(avatar_path)
        # Resize avatar to fit card - kích thước phù hợp với template
        avatar = avatar.resize((222, 289), Image.Resampling.LANCZOS)
        # Paste avatar at specific position - vị trí chính xác trên template
        card.paste(avatar, (410, 375))  # x, y coordinates - vị trí bên trái
        
        # Fonts: force Arial Regular (no bold for name and ID)
        try:
            # Use Arial Bold for name
            name_font = ImageFont.truetype("arialbd.ttf", 8)
            # Separate fonts for SURNAME and FIRSTNAME - using BOLD
            surname_font = ImageFont.truetype("arial.ttf", 8)  # SURNAME font BOLD
            firstname_font = ImageFont.truetype("arial.ttf", 8)  # FIRSTNAME font BOLD
            # Use Arial Bold for ID
            id_font = ImageFont.truetype("arialbd.ttf", 10)
            info_font = ImageFont.truetype("arial.ttf", 27)
            # Use Arial Regular for DOB (not bold)
            date_font = ImageFont.truetype("arial.ttf", 18)
            # Prefer Arial Bold for DID if available
            try:
                did_font = ImageFont.truetype("arialbd.ttf", 38)
            except Exception:
                did_font = ImageFont.truetype("arial.ttf", 38)
            # Use Arial Regular for Định danh (not bold)
            try:
                dinh_danh_font = ImageFont.truetype("arial.ttf", 38)
            except Exception:
                dinh_danh_font = ImageFont.truetype("arial.ttf", 38)
            uni_font = ImageFont.truetype("arial.ttf", 27)
        except Exception:
            try:
                # Fallback to bundled DejaVu Regular if Arial not present
                if os.path.exists(DEJAVU_REG):
                    # Use DejaVu Bold for name
                    name_font = ImageFont.truetype(DEJAVU_BOLD, 14)
                    # Separate fonts for SURNAME and FIRSTNAME - using BOLD
                    surname_font = ImageFont.truetype(DEJAVU_BOLD, 14)
                    firstname_font = ImageFont.truetype(DEJAVU_BOLD, 14)
                    # Use DejaVu Bold for ID
                    id_font = ImageFont.truetype(DEJAVU_BOLD, 10)
                    info_font = ImageFont.truetype(DEJAVU_REG, 27)
                    # Use DejaVu Regular for DOB (not bold)
                    date_font = ImageFont.truetype(DEJAVU_REG, 18)
                    # Use DejaVu Bold for DID if available
                    try:
                        did_font = ImageFont.truetype(DEJAVU_BOLD, 38)
                    except Exception:
                        did_font = ImageFont.truetype(DEJAVU_REG, 38)
                    # Use DejaVu Regular for Định danh (not bold)
                    try:
                        dinh_danh_font = ImageFont.truetype(DEJAVU_REG, 38)
                    except Exception:
                        dinh_danh_font = ImageFont.truetype(DEJAVU_REG, 38)
                    uni_font = ImageFont.truetype(DEJAVU_REG, 27)
                else:
                    raise RuntimeError("No truetype fonts available")
            except Exception:
                # Final fallback to PIL default bitmap font
                name_font = ImageFont.load_default()
                surname_font = ImageFont.load_default()
                firstname_font = ImageFont.load_default()
                info_font = ImageFont.load_default()
                id_font = ImageFont.load_default()
                date_font = ImageFont.load_default()
                did_font = ImageFont.load_default()
                dinh_danh_font = ImageFont.load_default()
                uni_font = ImageFont.load_default()
        
        draw = ImageDraw.Draw(card)
        
        # Determine coordinates by template (US vs Indonesia vs Germany)
        template_name = os.path.basename(template_path).lower()
        is_indonesia = 'indonesia' in template_name
        is_us = 'uk' in template_name
        
        if is_us:
            # US/UK template coordinates
            name_xy = (100, 200)  # Full name (fallback if not using separate surname/firstname)
            surname_xy = (340, 410)  # SURNAME position (customizable)
            firstname_xy = (147, 124)  # FIRSTNAME position (customizable) - increased spacing
            id_xy = (9999, 105)
            dob_xy = (99999, 270)
            avatar_xy = (9999, 400)
        elif is_indonesia:
            # Indonesia template coordinates
            name_xy = (773, 415)
            id_xy = (890, 850)
            dob_xy = (897, 522)
            avatar_xy = (350, 405)
        else:
            # Germany template coordinates
            name_xy = (900, 465)
            id_xy = (930, 697)
            dob_xy = (870, 584)
            avatar_xy = (408, 420)

        # Re-paste avatar at template-specific position if different
        if avatar_xy != (1000, 700):
            card.paste(template, (0, 0))
            card.paste(avatar, avatar_xy)

        # Reformat fields for Indonesia
        display_birth_date = student_info.get('birth_date')
        display_student_id = f"{student_info.get('student_id')}"
        display_did_text = None
        display_dinh_danh_text = None
        if is_us or is_indonesia:
            # Format DOB to YYYY-MM-DD
            try:
                dob_raw = str(student_info.get('birth_date', '')).replace('.', '-').replace('/', '-')
                parts = dob_raw.split('-')
                if len(parts) == 3:
                    # detect if YYYY-first (already in correct format)
                    if len(parts[0]) == 4:
                        y, m, d = parts[0], parts[1].zfill(2), parts[2].zfill(2)
                        display_birth_date = f"{y}-{m}-{d}"
                    else:
                        # assume DD-MM-YYYY, convert to YYYY-MM-DD
                        d, m, y = parts[0].zfill(2), parts[1].zfill(2), parts[2]
                        display_birth_date = f"{y}-{m}-{d}"
            except Exception:
                pass
            # Keep format for both US and templates
            try:
                # import random  # Using global import
                display_student_id = f"{random.randint(10000000, 99999999)}"  # 8 random digits (no 00 prefix)
                display_did_text = f"DID#:F00{random.randint(0, 99999):05d}".upper()
                display_dinh_danh_text = f"1001{random.randint(0, 99999):05d}"
            except Exception:
                pass

        # Draw fields (black text)
        # Use full name from student_info (Vietnamese format: HỌ TÊN ĐỆM TÊN)
        full_name = f"{student_info.get('name', '')}".replace(',', ' ').strip()
        if not full_name:
            # Fallback to first_name + last_name if name not provided
            first_name_val = f"{student_info.get('first_name', '')}".replace(',', ' ').strip()
            last_name_val = f"{student_info.get('last_name', '')}".replace(',', ' ').strip()
            full_name = f"{last_name_val} {first_name_val}".strip()
        
        if is_us:  # UK template - draw full name in one line (BOLD + Title Case)
            # Use Arial Bold for name
            try:
                name_font_bold = ImageFont.truetype("arialbd.ttf", 34)  # Arial BOLD, size 14
            except Exception:
                try:
                    if os.path.exists(DEJAVU_BOLD):
                        name_font_bold = ImageFont.truetype(DEJAVU_BOLD, 34)
                    else:
                        name_font_bold = ImageFont.truetype(DEJAVU_REG, 34)
                except Exception:
                    name_font_bold = ImageFont.load_default()
            
            # Draw full name at surname position (BOLD, Title Case)
            if surname_xy and full_name:
                formatted_fullname = full_name.title()  # Title Case: Nguyen Van Minh
                draw.text(surname_xy, formatted_fullname, fill=(0, 0, 0), font=name_font_bold)
        else:
            # Other templates - draw full name (Title Case + BOLD)
            # Use Arial Bold for name
            try:
                name_font_bold_other = ImageFont.truetype("arialbd.ttf", 14)  # Arial BOLD
            except Exception:
                try:
                    if os.path.exists(DEJAVU_BOLD):
                        name_font_bold_other = ImageFont.truetype(DEJAVU_BOLD, 14)
                    else:
                        name_font_bold_other = name_font or ImageFont.load_default()
                except Exception:
                    name_font_bold_other = name_font or ImageFont.load_default()
            
            if name_xy and full_name:
                formatted_fullname = full_name.title()  # Title Case: Nguyen Van Minh
                draw.text(name_xy, formatted_fullname, fill=(0, 0, 0), font=name_font_bold_other)
        
        # Draw Student ID (no bold)
        try:
            id_font_regular = ImageFont.truetype("arial.ttf", 10)  # Regular, not bold
        except Exception:
            try:
                if os.path.exists(DEJAVU_REG):
                    id_font_regular = ImageFont.truetype(DEJAVU_REG, 10)
                else:
                    id_font_regular = ImageFont.load_default()
            except Exception:
                id_font_regular = ImageFont.load_default()
        
        draw.text(id_xy, display_student_id, fill=(0, 0, 0), font=id_font_regular)
        # Draw DOB (Date of Birth)
        if display_birth_date and dob_xy:
            draw.text(dob_xy, str(display_birth_date), fill=(0, 0, 0), font=date_font or ImageFont.load_default())
        # Expiry date line for UK template: format DD MON YYYY, year 2028-2029, uppercase
        try:
            if is_us:  # 'is_us' flag is repurposed to detect UK template in this codebase
                # import random  # Using global import
                month_names = [
                    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"
                ]
                exp_day = random.randint(1, 28)
                exp_month = random.randint(1, 12)
                exp_year = random.randint(2028, 2029)
                expiry_text = f"{exp_day:02d} {month_names[exp_month - 1]} {exp_year}"
                # Position under the student id for UK layout
                # X là trục ngang, Y là trục dọc — CHỈNH TẠI HAI BIẾN NÀY
                expiry_x = id_xy[0] - 9999
                expiry_y = id_xy[1] + 9999
                expiry_xy = (expiry_x, expiry_y)
                # Try bold font for expiry if available
                try:
                    expiry_font = ImageFont.truetype("arialbd.ttf", 44)
                except Exception:
                    try:
                        expiry_font = ImageFont.truetype(DEJAVU_BOLD, 44)
                    except Exception:
                        expiry_font = id_font or ImageFont.load_default()
                draw.text(expiry_xy, expiry_text, fill=(0, 0, 0), font=expiry_font)
        except Exception:
            pass
        
        return card
        
    except Exception as e:
        print(f"Error creating card: {e}")
        return None

def generate_and_upload_card(verification_id: str, first_name: str, last_name: str, birth_date: str, steps: list):
    # Deprecated per request: use upload_student_card_to_sheerid directly after create_student_card
    return None


def create_transcript_image(student_info, university_info=None):
    """
    Tạo transcript image từ template HTML
    
    Args:
        student_info: dict với first_name, last_name, birth_date, student_id
        university_info: dict với university config (optional, sẽ random nếu không có)
    
    Returns:
        PIL Image object hoặc None nếu lỗi
    """
    try:
        from .transcript_generator import generate_transcript_html
        from .universities_config import get_random_university
        
        # Lấy thông tin trường
        if university_info is None:
            university_info = get_random_university()
        
        # Generate HTML
        html_content, info = generate_transcript_html(
            university=university_info,
            first_name=student_info.get('first_name'),
            last_name=student_info.get('last_name'),
            dob=student_info.get('birth_date')
        )
        
        # Render HTML to image (auto-fallback to Pillow on Vercel)
        try:
            from .transcript_generator import render_transcript_auto
            
            # Create temp file for output
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                output_path = tmp.name
            
            # Render with auto-fallback (Playwright -> Pillow)
            render_transcript_auto(html_content, info, output_path)
            
            # Load image
            transcript_img = Image.open(output_path)
            
            # Cleanup temp file
            try:
                os.unlink(output_path)
            except:
                pass
            
            print(f"✅ Created transcript for {info['first_name']} {info['last_name']} - {info['university']['name']}")
            return transcript_img, info
            
        except Exception as render_err:
            print(f"⚠️ Transcript render failed: {render_err}")
            return None, info
            
    except Exception as e:
        print(f"❌ Error creating transcript: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def upload_transcript_to_sheerid(verification_id, transcript_path, is_teacher=False, session_id=None):
    """Upload transcript lên SheerID - tương tự upload_student_card_to_sheerid"""
    try:
        with open(transcript_path, 'rb') as f:
            image_data = f.read()

        # Bước 1: Gửi metadata để lấy S3 URL
        payload = {
            "files": [{
                "fileName": os.path.basename(transcript_path),
                "fileSize": len(image_data),
                "mimeType": "image/png"
            }]
        }

        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Origin': 'https://services.sheerid.com',
            'Referer': f'https://services.sheerid.com/verify/{verification_id}',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        }

        upload_url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}/step/docUpload"
        response = make_request('post', upload_url, json=payload, headers=headers, timeout=30, use_scrape_proxy=True, session_id=session_id, country='us')

        if response.status_code != 200:
            return {"success": False, "error": f"Step 1 failed: {response.status_code} - {response.text[:200]}"}

        response_data = response.json() if response.content else {}
        
        # Check for fraud rejection in upload response
        if response_data.get('currentStep', '').lower() == 'error':
            error_ids = response_data.get('errorIds', [])
            if 'fraudRulesReject' in error_ids:
                print(f"🚫 FRAUD DETECTED during upload: {error_ids}")
                return {
                    "success": False, 
                    "error": "fraudRulesReject",
                    "errorIds": error_ids,
                    "errorDetailId": response_data.get('errorDetailId'),
                    "systemErrorMessage": response_data.get('systemErrorMessage')
                }
        
        # Bước 2: Upload file thực tế lên S3
        if 'documents' in response_data and len(response_data['documents']) > 0:
            document = response_data['documents'][0]
            if 'uploadUrl' in document:
                s3_url = document['uploadUrl']
                document_id = document.get('documentId', 'unknown')
                
                # Upload file thực tế lên S3
                s3_headers = {
                    'Content-Type': 'image/png',
                    'Content-Length': str(len(image_data))
                }
                
                s3_response = requests.put(s3_url, data=image_data, headers=s3_headers, timeout=30)
                
                if s3_response.status_code in [200, 204]:
                    print(f"✅ Transcript uploaded successfully to S3 for document {document_id}")
                    return {
                        "success": True, 
                        "message": f"Transcript đã được upload thành công (Document ID: {document_id})", 
                        "response_data": response_data,
                        "document_id": document_id
                    }
                else:
                    return {"success": False, "error": f"S3 upload failed: {s3_response.status_code} - {s3_response.text[:200]}"}
            else:
                return {"success": False, "error": "No uploadUrl in response"}
        else:
            return {"success": False, "error": "No documents in response"}

    except Exception as e:
        return {"success": False, "error": f"Transcript upload error: {str(e)}"}

def upload_student_card_to_sheerid(verification_id, card_filename, is_teacher=False, session_id=None):
    """Upload thẻ sinh viên lên SheerID - 2 bước: metadata + S3 upload"""
    try:
        with open(card_filename, 'rb') as f:
            image_data = f.read()

        # Bước 1: Gửi metadata để lấy S3 URL
        payload = {
            "files": [{
                "fileName": os.path.basename(card_filename),
                "fileSize": len(image_data),
                "mimeType": "image/jpeg"
            }]
        }

        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Origin': 'https://services.sheerid.com',
            'Referer': f'https://services.sheerid.com/verify/{verification_id}',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        }

        upload_url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}/step/docUpload"


        response = make_request('post', upload_url, json=payload, headers=headers, timeout=30, use_scrape_proxy=True, session_id=session_id, country='us')


        if response.status_code != 200:
            return {"success": False, "error": f"Step 1 failed: {response.status_code} - {response.text[:200]}"}

        response_data = response.json() if response.content else {}
        
        # Bước 2: Upload file thực tế lên S3
        if 'documents' in response_data and len(response_data['documents']) > 0:
            document = response_data['documents'][0]
            if 'uploadUrl' in document:
                s3_url = document['uploadUrl']
                document_id = document.get('documentId', 'unknown')
                
                
                # Upload file thực tế lên S3
                s3_headers = {
                    'Content-Type': 'image/jpeg',
                    'Content-Length': str(len(image_data))
                }
                
                s3_response = requests.put(s3_url, data=image_data, headers=s3_headers, timeout=30)
                
                
                if s3_response.status_code in [200, 204]:
                    print(f"✅ File uploaded successfully to S3 for document {document_id}")
                    return {
                        "success": True, 
                        "message": f"Thẻ sinh viên đã được upload thành công (Document ID: {document_id})", 
                        "response_data": response_data,
                        "document_id": document_id
                    }
                else:
                    return {"success": False, "error": f"S3 upload failed: {s3_response.status_code} - {s3_response.text[:200]}"}
            else:
                return {"success": False, "error": "No uploadUrl in response"}
        else:
            return {"success": False, "error": "No documents in response"}

    except Exception as e:
        return {"success": False, "error": f"Upload error: {str(e)}"}

def schedule_background_polling(verification_id, job_id, result_data, is_teacher=False):
    """Schedule background polling for verification that's taking too long"""
    try:
        import threading
        import time
        
        def background_poll():
            """Background polling function"""
            print(f"🔄 Starting background polling for verification {verification_id}")
            
            # Background polling: different delays for student vs teacher
            # Student: 3 seconds, 80 attempts | Teacher: 10 seconds, 24 attempts
            max_bg_attempts = 24 if is_teacher else 80
            bg_delay = 10.0 if is_teacher else 3.0
            
            for attempt in range(max_bg_attempts):
                try:
                    # Check if job is already completed before each polling attempt
                    from .supabase_client import get_verification_job_by_id
                    job_info = get_verification_job_by_id(job_id)
                    if job_info and job_info.get('status') == 'completed':
                        print(f"✅ Job {job_id} already completed - stopping background polling")
                        return
                    
                    print(f"🔄 Background polling attempt {attempt + 1}/{max_bg_attempts} for {verification_id}")
                    time.sleep(bg_delay)
                    
                    # Check verification status
                    url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}"
                    headers = {
                        'Accept': 'application/json, text/plain, */*',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Origin': 'https://services.sheerid.com',
                        'Referer': f'https://services.sheerid.com/verify/{verification_id}',
                    }
                    
                    response = make_request('get', url, headers=headers, timeout=30, use_scrape_proxy=True, country='us')
                    
                    if response.status_code == 200:
                        data = response.json()
                        current_step = data.get('currentStep', '').lower()
                        
                        print(f"🔍 Background poll result: {current_step}")
                        
                        if current_step in ['success', 'complete', 'verified']:
                            print(f"✅ Background polling SUCCESS for {verification_id}")
                            
                            # Process success - charge user and send notification
                            process_background_success(job_id, verification_id, result_data, data)
                            return
                        elif current_step in ['failed', 'error', 'rejected']:
                            print(f"❌ Background polling FAILED for {verification_id}")
                            
                            # Process failure - send notification but don't charge
                            process_background_failure(job_id, verification_id, result_data, data)
                            return
                        else:
                            print(f"⏳ Still pending: {current_step}")
                            continue
                    else:
                        print(f"❌ Background poll HTTP error: {response.status_code}")
                        continue
                        
                except Exception as e:
                    print(f"❌ Background polling error: {e}")
                    continue
            
            # If we get here, it's still pending after extended time
            print(f"⏰ Background polling timeout for {verification_id}")
            process_background_timeout(job_id, verification_id, result_data)
        
        # Start background thread
        thread = threading.Thread(target=background_poll, daemon=True)
        thread.start()
        
        print(f"✅ Background polling scheduled for {verification_id}")
        return True
        
    except Exception as e:
        print(f"❌ Error scheduling background polling: {e}")
        return False

def process_background_success(job_id, verification_id, result_data, sheerid_data):
    """Process successful verification from background polling"""
    try:
        print(f"🎉 Processing background success for job {job_id}")
        
        # Update job status to completed
        from .supabase_client import update_verification_job_status
        success = update_verification_job_status(
            job_id, 
            'completed',
            result_data.get("student_info"),
            result_data.get("card_filename"),
            result_data.get("upload_result")
        )
        
        if success:
            print(f"✅ Updated job {job_id} to completed")
            
            # Process charging (includes notification)
            charging_success = process_completed_job_charging(job_id)
            
            if charging_success:
                print(f"✅ Successfully charged job {job_id}")
            else:
                print(f"⚠️ Charging skipped for job {job_id} (already charged or VIP)")
        else:
            print(f"❌ Failed to update job {job_id} status")
            
    except Exception as e:
        print(f"❌ Error processing background success: {e}")

def process_background_failure(job_id, verification_id, result_data, sheerid_data):
    """Process failed verification from background polling"""
    try:
        print(f"❌ Processing background failure for job {job_id}")
        
        # Check if job is already completed - don't override completed status
        from .supabase_client import get_verification_job_by_id
        job_info = get_verification_job_by_id(job_id)
        if job_info and job_info.get('status') == 'completed':
            print(f"✅ Job {job_id} already completed - skipping background failure override")
            return
        
        # Update job status to failed only if not already completed
        from .supabase_client import update_verification_job_status
        update_verification_job_status(job_id, 'failed')
        
        # Send failure notification (no charging)
        send_failure_notification_for_job(job_id, "Verification failed after extended processing")
        
    except Exception as e:
        print(f"❌ Error processing background failure: {e}")

def process_background_timeout(job_id, verification_id, result_data):
    """Process timeout after extended background polling - mark as FAILED"""
    try:
        print(f"⏰ Processing background timeout for job {job_id} - marking as FAILED")
        
        # Check if job is already completed - don't override completed status
        from .supabase_client import get_verification_job_by_id
        job_info = get_verification_job_by_id(job_id)
        if job_info and job_info.get('status') == 'completed':
            print(f"✅ Job {job_id} already completed - skipping background timeout override")
            return
        
        # Update job status to FAILED (not timeout) - polling exhausted means verification failed
        from .supabase_client import update_verification_job_status
        update_verification_job_status(job_id, 'failed')
        
        # Send failure notification with timeout reason (no charging)
        send_failure_notification_for_job(job_id, "Quá thời gian verify")
        
    except Exception as e:
        print(f"❌ Error processing background timeout: {e}")

def send_failure_notification_for_job(job_id, reason):
    """Send failure notification for a job"""
    try:
        print(f"📤 send_failure_notification_for_job called for job {job_id}, reason: {reason}")
        from .supabase_client import get_verification_job_by_id, get_supabase_client
        
        job_info = get_verification_job_by_id(job_id)
        print(f"📋 Job info retrieved: {job_info}")
        if job_info:
            telegram_id = job_info.get('telegram_id')
            user_lang = 'vi'  # Default language
            
            # Fallback: get telegram_id and language from user if not in job
            user_id = job_info.get('user_id')
            if user_id:
                try:
                    client = get_supabase_client()
                    if client:
                        user_resp = client.table('users').select('telegram_id, language').eq('id', user_id).limit(1).execute()
                        if user_resp.data:
                            if not telegram_id:
                                telegram_id = user_resp.data[0].get('telegram_id')
                                print(f"📱 Telegram ID from user fallback: {telegram_id}")
                            user_lang = user_resp.data[0].get('language', 'vi')
                except Exception as e:
                    print(f"⚠️ Error getting user info: {e}")
            
            print(f"📱 Final Telegram ID: {telegram_id}, Language: {user_lang}")
            if telegram_id:
                bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                if bot_token:
                    # Determine if this is a timeout failure
                    is_timeout = 'timeout' in reason.lower() or 'polling' in reason.lower() or 'thời gian' in reason.lower()
                    current_time = format_vietnam_time()
                    
                    # Multilingual fail messages
                    if is_timeout:
                        fail_msgs = {
                            'vi': f"""❌ Verification thất bại!

🆔 Job ID: {job_id}
📋 Lý do: Quá thời gian verify, vui lòng thử lại
🕐 Thời gian: {current_time}

💰 Không bị trừ xu/cash
🔄 Bạn có thể thử lại với link mới

📞 Hỗ trợ: @meepzizhere""",
                            'en': f"""❌ Verification failed!

🆔 Job ID: {job_id}
📋 Reason: Verification timeout, please try again
🕐 Time: {current_time}

💰 No xu/cash deducted
🔄 You can try again with a new link

📞 Support: @meepzizhere""",
                            'zh': f"""❌ 验证失败！

🆔 Job ID: {job_id}
📋 原因: 验证超时，请重试
🕐 时间: {current_time}

💰 未扣除 xu/cash
🔄 您可以使用新链接重试

📞 支持: @meepzizhere"""
                        }
                    else:
                        fail_msgs = {
                            'vi': f"""❌ Verification thất bại!

🆔 Job ID: {job_id}
📋 Lý do: {reason}
🕐 Thời gian: {current_time}

💰 Không bị trừ xu/cash
🔄 Bạn có thể thử lại với link mới

📞 Hỗ trợ: @meepzizhere""",
                            'en': f"""❌ Verification failed!

🆔 Job ID: {job_id}
📋 Reason: {reason}
🕐 Time: {current_time}

💰 No xu/cash deducted
🔄 You can try again with a new link

📞 Support: @meepzizhere""",
                            'zh': f"""❌ 验证失败！

🆔 Job ID: {job_id}
📋 原因: {reason}
🕐 时间: {current_time}

💰 未扣除 xu/cash
🔄 您可以使用新链接重试

📞 支持: @meepzizhere"""
                        }
                    
                    message = fail_msgs.get(user_lang, fail_msgs['vi'])

                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    # Send as plain text - no parse_mode to avoid Markdown errors
                    data = {
                        'chat_id': telegram_id,
                        'text': message,
                    }
                    response = requests.post(url, data=data, timeout=30)
                    
                    if response.status_code == 200:
                        print(f"✅ Sent failure notification to {telegram_id}")
                    else:
                        print(f"❌ Failed to send Telegram notification: {response.status_code} - {response.text}")
                    
            else:
                print(f"❌ No telegram_id found in job_info for job {job_id}")
        else:
            print(f"❌ No job_info found for job {job_id}")
                    
    except Exception as e:
        print(f"❌ Error sending failure notification: {e}")
        import traceback
        traceback.print_exc()

def wait_for_doc_processing(verification_id: str, max_attempts: int = 100, delay: float = 3.0, is_teacher: bool = False, session_id: str = None, university_id: str = None, university_name: str = None):
    """Poll SheerID to wait for document processing before completing upload.
    Student: Uses passed delay (default 3s), 100 attempts max (300s total)
    Teacher: Uses passed delay (default 10s), uses passed max_attempts (default 20)
    FAST_MODE: 1s interval for faster response
    
    university_id/university_name: Used for fraud tracking (block after 3 consecutive DOCUMENT_LIKELY_FRAUD)
    """
    try:
        url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}"
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Origin': 'https://services.sheerid.com',
            'Referer': f'https://services.sheerid.com/verify/{verification_id}',
        }
        
        # Use passed delay parameter for both teacher and student
        actual_delay = delay
        # Don't override max_attempts - use the value passed in
        print(f"📊 Polling config: {max_attempts} attempts x {actual_delay}s = {max_attempts * actual_delay}s total (is_teacher={is_teacher})")
        
        last_current_step = ""
        has_been_pending = False  # Track if we've seen pending status (indicates upload happened)
        
        for attempt in range(max_attempts):
            # Log only every 10 attempts to reduce noise
            if attempt == 0 or (attempt + 1) % 10 == 0:
                print(f"Polling {attempt + 1}/{max_attempts}...")
            resp = make_request('get', url, headers=headers, timeout=30, use_scrape_proxy=True, session_id=session_id, country='us')
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    current_step = data.get('currentStep', '').lower()
                    last_current_step = current_step
                    # Reduced logging
                    
                    # Track if we've seen pending status
                    if current_step == 'pending':
                        has_been_pending = True
                    
                    # Check if document is processed and ready for completion
                    if current_step in ('success', 'complete', 'verified'):
                        print("✅ Verification completed successfully!")
                        
                        # Track success for university fraud tracking (reset consecutive count)
                        if university_id and not is_teacher:
                            try:
                                from .supabase_client import record_university_success
                                record_university_success(university_id, university_name)
                            except Exception as e:
                                print(f"⚠️ Failed to record university success: {e}")
                        
                        return True, data
                    elif current_step in ('docupload', 'document', 'documentupload', 'upload', 'uploaddocs', 'docs'):
                        # If we've seen pending before, check if document was rejected
                        if has_been_pending:
                            rejection_reasons = data.get('rejectionReasons', [])
                            if rejection_reasons:
                                # Document was rejected - fail immediately
                                print(f"❌ Document REJECTED: {rejection_reasons}")
                                
                                # Track DOCUMENT_LIKELY_FRAUD for university fraud tracking
                                if university_id and not is_teacher and 'DOCUMENT_LIKELY_FRAUD' in rejection_reasons:
                                    try:
                                        from .supabase_client import record_university_fraud
                                        is_blocked, consecutive = record_university_fraud(university_id, university_name)
                                        if is_blocked:
                                            print(f"🚫 University {university_id} ({university_name}) is now BLOCKED after {consecutive} consecutive frauds!")
                                    except Exception as e:
                                        print(f"⚠️ Failed to record university fraud: {e}")
                                
                                return False, {
                                    "error": f"Document rejected: {', '.join(rejection_reasons)}",
                                    "rejectionReasons": rejection_reasons,
                                    "currentStep": current_step,
                                    **data
                                }
                            else:
                                # No rejection reasons - SheerID may need more docs or still processing
                                print("Document upload step after pending - continue polling (review in progress)")
                                time.sleep(actual_delay)
                        else:
                            print("Document upload step - should not continue polling")
                            return False, {"error": "docUpload", "currentStep": current_step, **data}
                    elif current_step == 'pending':
                        # Continue polling for pending status - wait before next attempt
                        time.sleep(actual_delay)
                    elif current_step == 'error':
                        error_ids = data.get('errorIds', [])
                        error_detail = data.get('errorDetailId', '')
                        system_error = data.get('systemErrorMessage', '')
                        print(f"Verification error: {error_ids}")
                        print(f"Error detail: {error_detail}")
                        print(f"System error: {system_error}")
                        
                        # Create detailed error message
                        error_msg = f"Verification failed: {', '.join(error_ids) if error_ids else 'Unknown error'}"
                        if system_error:
                            error_msg += f" - {system_error}"
                        
                        return False, {
                            "error": error_msg,
                            "errorIds": error_ids,
                            "errorDetailId": error_detail,
                            "systemErrorMessage": system_error,
                            "currentStep": current_step
                        }
                    else:
                        time.sleep(actual_delay)
                except Exception as e:
                    print(f"Error parsing response: {e}")
                    time.sleep(actual_delay)
            else:
                # Treat transient 4xx/5xx as pending; retry after delay
                print(f"Polling failed with status {resp.status_code}")
                time.sleep(actual_delay)
        
        # Max attempts reached - return timeout
        print(f"⏰ Max polling attempts ({max_attempts}) reached - returning TIMEOUT")
        return False, {
            "currentStep": last_current_step or 'unknown', 
            "status": "timeout", 
            "reason": "timeout",
            "error": f"Verification timeout after {max_attempts} polling attempts ({max_attempts * actual_delay}s)"
        }
        
    except Exception as e:
        print(f"Error during polling: {e}")
        return False, {"error": str(e)}

def complete_doc_upload(verification_id: str, card_filename: str = None, is_teacher: bool = False, session_id: str = None):
    """Call SheerID to complete doc upload step and advance flow."""
    try:
        url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}/step/completeDocUpload"
        # Prepare payload with document data
        payload = {}
        if card_filename and os.path.exists(card_filename):
            try:
                with open(card_filename, 'rb') as f:
                    image_data = f.read()
                
                # Encode image as base64
                import base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                # Create payload with document data
                payload = {
                    "files": [{
                        "fileName": os.path.basename(card_filename),
                        "fileSize": len(image_data),
                        "mimeType": "image/jpeg",
                        "data": image_base64
                    }]
                }
                print(f"DEBUG: Sending document data - file: {os.path.basename(card_filename)}, size: {len(image_data)} bytes")
            except Exception as e:
                print(f"DEBUG: Failed to read card file: {e}")
                # Fallback to empty payload
                payload = {"files": []}
        else:
            print("DEBUG: No card file provided, sending empty payload")
            payload = {"files": []}
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Origin': 'https://services.sheerid.com',
            'Referer': f'https://services.sheerid.com/verify/{verification_id}',
            'X-Requested-With': 'XMLHttpRequest'
        }
        resp = make_request('post', url, json=payload, headers=headers, timeout=30, use_scrape_proxy=True, session_id=session_id, country='us')
        print(f"completeDocUpload status: {resp.status_code}")
        print(f"completeDocUpload body: {resp.text[:500]}")
        if resp.status_code == 200:
            try:
                return True, resp.json()
            except Exception:
                return True, {}
        return False, {"error": f"{resp.status_code} - {resp.text[:200]}"}
    except Exception as e:
        return False, {"error": str(e)}

@app.route('/')
def root():
    return send_from_directory('..', 'index.html')

@app.route('/locket')
def locket_page():
    return send_from_directory('..', 'locket.html')

@app.route('/quanly.html')
def quanly():
    return send_from_directory('..', 'quanly.html')

@app.route('/quanly.js')
def quanly_js():
    return send_from_directory('..', 'quanly.js')

@app.route('/admin.html')
def admin_page():
    return send_from_directory('..', 'admin.html')

@app.route('/admin_jobs.html')
def admin_jobs_page():
    return send_from_directory('..', 'admin_jobs.html')

@app.route('/api/teacher-queue-status', methods=['GET'])
def teacher_queue_status():
    """Get current teacher verification queue status"""
    try:
        from .telegram import get_teacher_queue_status, TEACHER_ACTIVE_JOBS, TEACHER_QUEUE
        status = get_teacher_queue_status()
        return jsonify({
            'success': True,
            'active': status['active'],
            'waiting': status['waiting'],
            'max_concurrent': status['max_concurrent'],
            'active_jobs': list(TEACHER_ACTIVE_JOBS),
            'queue_length': len(TEACHER_QUEUE)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/docs')
def api_docs():
    """API Documentation for sellers"""
    return send_from_directory('..', 'docs.html')

@app.route('/verify', methods=['POST'])
def verify():
    try:
        payload = request.get_json(silent=True) or {}
        url = (payload.get('url') or '').strip()
        if not url:
            return jsonify(success=False, error='Thiếu URL'), 400

        # Basic validation the URL looks like a SheerID verify link.
        parsed = urlparse(url)
        host_ok = 'sheerid.com' in (parsed.netloc or '')
        path_ok = '/verify' in (parsed.path or '')

        # NOTE: Original app likely called an external API. We cannot call
        # external APIs from Vercel serverless functions in production.
        # This is a placeholder that simulates success/failure based on URL.
        if not host_ok or not path_ok:
            return jsonify(success=False, error='URL không hợp lệ'), 400

        # Simulate verification
        time.sleep(2)
        return jsonify(success=True, message='Verification completed')
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

def _submit_sheerid_verification(payload: dict):
    try:
        import time as _t
        _verify_start = _t.time()
        
        url = payload.get('url')
        job_id = payload.get('job_id')  # Get job_id from payload
        
        # CRITICAL: Create sticky proxy session ID to keep same IP for entire verification
        # This prevents fraud detection due to IP mismatch between requests
        proxy_session_id = job_id or f"verify_{int(_verify_start)}"
        print(f"🔒 Proxy session ID: {proxy_session_id} (sticky IP for all requests)")
        
        steps = []
        steps.append({"t":"start","msg":"Start verification"})
        
        # Initialize response_data to avoid UnboundLocalError
        response_data = {}
        
        # Use global CHARGED_JOBS to prevent double charging
        
        # Get fast_mode setting for later use
        fast_mode = get_fast_mode()
        
        # US names database for Art Institute - expanded 200+ names for better randomization
        us_first_names = [
            # Male names - Classic & Modern
            "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
            "Thomas", "Christopher", "Charles", "Daniel", "Matthew", "Anthony", "Mark",
            "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian",
            "George", "Timothy", "Ronald", "Edward", "Jason", "Jeffrey", "Ryan", "Jacob",
            "Gary", "Nicholas", "Eric", "Jonathan", "Stephen", "Larry", "Justin", "Scott",
            "Brandon", "Benjamin", "Samuel", "Raymond", "Gregory", "Frank", "Patrick", "Peter",
            "Liam", "Noah", "Oliver", "Elijah", "Lucas", "Mason", "Logan", "Alexander",
            "Ethan", "Henry", "Sebastian", "Jack", "Aiden", "Owen", "Carter", "Jayden",
            "Wyatt", "Dylan", "Grayson", "Levi", "Isaac", "Gabriel", "Julian", "Mateo",
            "Jaxon", "Lincoln", "Theodore", "Caleb", "Asher", "Nathan", "Leo", "Isaiah",
            "Hudson", "Christian", "Hunter", "Connor", "Eli", "Ezra", "Aaron", "Landon",
            "Adrian", "Nolan", "Jeremiah", "Easton", "Elias", "Colton", "Cameron", "Carson",
            "Angel", "Maverick", "Dominic", "Greyson", "Adam", "Ian", "Austin", "Santiago",
            "Jordan", "Cooper", "Brayden", "Roman", "Evan", "Xavier", "Jose", "Jace",
            # Female names - Classic & Modern
            "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica",
            "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra", "Ashley",
            "Kimberly", "Emily", "Donna", "Michelle", "Dorothy", "Carol", "Amanda", "Melissa",
            "Deborah", "Stephanie", "Rebecca", "Sharon", "Laura", "Cynthia", "Kathleen", "Amy",
            "Angela", "Anna", "Brenda", "Pamela", "Emma", "Nicole", "Helen", "Samantha",
            "Olivia", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia", "Harper",
            "Evelyn", "Abigail", "Ella", "Scarlett", "Grace", "Chloe", "Victoria", "Riley",
            "Aria", "Lily", "Aurora", "Zoey", "Nora", "Camila", "Hannah", "Lillian",
            "Addison", "Eleanor", "Natalie", "Luna", "Savannah", "Brooklyn", "Leah", "Zoe",
            "Stella", "Hazel", "Ellie", "Paisley", "Audrey", "Skylar", "Violet", "Claire",
            "Bella", "Lucy", "Caroline", "Genesis", "Aaliyah", "Kennedy", "Kinsley", "Allison",
            "Maya", "Madelyn", "Adeline", "Alexa", "Ariana", "Elena", "Gabriella", "Naomi",
            "Alice", "Sadie", "Hailey", "Eva", "Emilia", "Autumn", "Quinn", "Piper", "Ruby"
        ]
        us_last_names = [
            # Most common US surnames - expanded
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
            "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
            "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
            "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
            "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
            "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
            "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
            "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
            "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey",
            "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson", "Watson",
            "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes",
            "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long", "Ross", "Foster",
            "Jimenez", "Powell", "Jenkins", "Perry", "Russell", "Sullivan", "Bell", "Coleman",
            "Butler", "Henderson", "Barnes", "Fisher", "Vasquez", "Simmons", "Crawford", "Porter",
            "Mason", "Shaw", "Gordon", "Wagner", "Hunter", "Romero", "Dixon", "Hunt", "Palmer"
        ]
        
        # Generate US name for Art Institute
        first_name = random.choice(us_first_names)
        last_name = random.choice(us_last_names)
        full_name = f"{first_name} {last_name}"
        print(f"👤 Generated US name: {full_name}")
        
        # Generate realistic US email - use common domains for higher success rate
        email_domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com"]
        email_patterns = [
            f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}@{random.choice(email_domains)}",
            f"{first_name.lower()}{last_name.lower()}{random.randint(1, 9999)}@{random.choice(email_domains)}",
            f"{first_name.lower()}_{last_name.lower()}{random.randint(1, 99)}@{random.choice(email_domains)}",
            f"{first_name.lower()}{random.randint(1000, 9999)}@{random.choice(email_domains)}",
        ]
        email = random.choice(email_patterns)
        print(f"📧 Generated US email: {email}")
        
        # Generate Student ID: 8-digit format (no bold)
        student_id = f"{random.randint(10000000, 99999999)}"
        
        # Generate more realistic DOB (19-22 years old) - typical university age
        # Avoid 18 (too young, might be flagged) and 23+ (less common for undergrad)
        try:
            from datetime import datetime
            # Generate DOB for university students (19-22 years old) - sweet spot
            current_year = datetime.now().year
            birth_year = random.randint(current_year - 22, current_year - 19)
            birth_month = random.randint(1, 12)
            birth_day = random.randint(1, 28)  # Safe day for all months
            birth_date = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"
        except Exception as e:
            print(f"❌ ERROR generating birth date: {e}")
            birth_date = "2003-01-01"  # Fallback
        
        # No phone number needed
        phone_number = ""
        
        # University rotation - randomly select from Art Institute universities
        try:
            selected_university = get_random_university()
            university = selected_university["name"]
            university_id = selected_university["id"]
            university_id_extended = selected_university["idExtended"]
            university_template = selected_university.get("template", UK_TEMPLATE)
            university_city = selected_university.get("city", "")
            university_state = selected_university.get("state", "")
            
            # Art Institute = US universities, always use en-US locale
            country = "US"
            locale = "en-US"
            
            print(f"🎓 Selected university: {university} (ID: {university_id})")
            print(f"📍 Location: {university_city}, {university_state}")
            print(f"🌍 Country: {country}, Locale: {locale}")
            
            # Update job with university info immediately after selection
            if job_id:
                try:
                    from .supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    if supabase:
                        supabase.table('verification_jobs').update({'university': university}).eq('job_id', job_id).execute()
                        print(f"✅ Updated job {job_id} with university: {university}")
                except Exception as ue:
                    print(f"⚠️ Failed to update job university: {ue}")
        except Exception as e:
            print(f"❌ ERROR setting university data: {e}")
            university = "The Art Institute of Michigan"
            university_id = 8976
            university_id_extended = "8976"
            university_template = UK_TEMPLATE
            university_city = "Novi"
            university_state = "MI"
            country = "US"
            locale = "en-US"
        
        # Check verification type
        verification_type = payload.get('verification_type', 'sheerid')
        is_chatgpt_teacher = (verification_type == 'chatgpt')
        is_spotify = (verification_type == 'spotify')
        
        # Use SOCKS5 proxy for all verification types
        # This provides better IP rotation and reliability
        use_scrape_proxy = True  # Always use SOCKS5 proxy for verification
        use_us_proxy = False  # Disable legacy US proxy
        
        # Get proxy IP for debug logging - USING STICKY SESSION WITH US TARGETING
        # CRITICAL: Use same session_id to get the IP that will be used for all requests
        # CRITICAL: Use US country targeting to avoid fraud detection (IP must match university country)
        proxy_ip = "unknown"
        proxy_country = "US"  # Default to US for SheerID US universities
        try:
            # HARDCODED proxy credentials - Updated Dec 2024 (MUST match make_request)
            scrape_host = 'rp.scrapegw.com'
            scrape_port = '6060'
            scrape_pass = '4zqo673ns3fpmd1'  # Same as make_request function
            # Use sticky session with proxy_session_id + country-us for US IP
            # Format: username-session-{id}-country-{code}
            scrape_user = f'hgave8blvs7dfox-session-{proxy_session_id}-country-us'
            proxy_url = f"socks5://{scrape_user}:{scrape_pass}@{scrape_host}:{scrape_port}"
            
            if CURL_CFFI_AVAILABLE:
                from curl_cffi.requests import Session as CurlSession
                with CurlSession() as session:
                    ip_response = session.get("https://api.ipify.org?format=json", 
                                              proxies={"http": proxy_url, "https": proxy_url}, 
                                              timeout=10)
                    if ip_response.status_code == 200:
                        proxy_ip = ip_response.json().get('ip', 'unknown')
                        print(f"✅ Got US sticky session IP: {proxy_ip} (session={proxy_session_id}, country=US)")
        except Exception as e:
            print(f"⚠️ Could not get proxy IP: {e}")
            # Generate a fake but valid-looking US IP as fallback (common US ranges)
            # Note: random is already imported at module level
            us_ip_ranges = [
                (8, 8),      # Google
                (13, 13),    # Xerox
                (15, 15),    # HP
                (17, 17),    # Apple
                (20, 20),    # CSC
                (32, 32),    # AT&T
                (34, 34),    # Halliburton
                (35, 35),    # Merit Network
                (38, 38),    # PSINet
                (40, 40),    # Eli Lilly
                (44, 44),    # Amateur Radio
                (45, 45),    # Interop
                (47, 47),    # Bell-Northern
                (48, 48),    # Prudential
                (50, 50),    # JC Penney
                (52, 52),    # DuPont
                (54, 54),    # Merck
                (55, 55),    # Boeing
                (56, 56),    # USPS
                (57, 57),    # SITA
            ]
            first_octet = random.choice(us_ip_ranges)[0]
            proxy_ip = f"{first_octet}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
            print(f"⚠️ Using generated US fallback IP: {proxy_ip}")
        
        host_ip = proxy_ip  # Store for payload
        print(f"🌐 Using SOCKS5 sticky session proxy - IP: {proxy_ip}")
        steps.append({"t":"ip","msg":f"SOCKS5 Rotating Proxy IP: {proxy_ip}"})
        
        # ===== CHECK IP BLACKLIST =====
        # Check if this IP has been blacklisted due to previous fraud detection
        # If blacklisted, we log it but continue (can't easily get new IP mid-session)
        if is_ip_blacklisted(proxy_ip):
            print(f"⚠️ WARNING: IP {proxy_ip} is in fraud blacklist!")
            print(f"   This IP previously caused fraud detection.")
            print(f"   Continuing anyway, but fraud detection is more likely.")
            steps.append({"t":"ip_blacklisted","msg":f"IP {proxy_ip} is blacklisted - fraud risk higher"})
        else:
            print(f"✅ IP {proxy_ip} is not blacklisted")
        # ===== END CHECK IP BLACKLIST =====
        
        # Extract verification ID and program ID from URL (support both formats)
        verification_id = None
        program_id = None  # Program ID for metadata (e.g., 67c8c14f5f17a83b745e3f82)
        
        # Format 1: /verify/67c8c14f5f17a83b745e3f82/?verificationId=68cd3607c6b1fd741c15c58b
        # or services.sheerid.com/67c8c14f5f17a83b745e3f82/?verificationId=...
        if 'verificationId=' in url:
            verification_id = url.split('verificationId=')[-1].split('&')[0]
            # Extract program_id from path (before verificationId)
            # Pattern: /67c8c14f5f17a83b745e3f82/?verificationId=
            import re
            program_match = re.search(r'/([a-f0-9]{24})/?\?verificationId=', url)
            if program_match:
                program_id = program_match.group(1)
        # Format 2: /verification/68cd310ac6b1fd741c15440d/step/...
        elif 'verification/' in url:
            verification_id = url.split('verification/')[-1].split('/')[0]
        # Format 3: /verify/67c8c14f5f17a83b745e3f82/ (extract from path)
        elif '/verify/' in url:
            parts = url.split('/verify/')
            if len(parts) > 1:
                path_part = parts[1].split('/')[0]
                if path_part and len(path_part) > 10: # Heuristic for valid ID length
                    verification_id = path_part
        
        # Default program_id if not extracted (fallback to common student program)
        if not program_id:
            program_id = '67c8c14f5f17a83b745e3f82'  # Default student verification program
        
        # Known Teacher program IDs (ChatGPT, OpenAI, etc.)
        # These are program IDs that require teacher verification
        TEACHER_PROGRAM_IDS = [
            '67c8c14f5f17a83b745e3f83',  # ChatGPT Teacher (example)
            '5f8a1b2c3d4e5f6a7b8c9d0e',  # OpenAI Teacher (example)
            # Add more teacher program IDs as discovered
        ]
        
        # Auto-detect teacher verification from program ID
        is_teacher_from_program = program_id in TEACHER_PROGRAM_IDS
        if is_teacher_from_program and not is_chatgpt_teacher:
            print(f"🎓 AUTO-DETECT: Teacher program ID detected: {program_id}")
            print(f"   Switching to teacher verification flow")
            is_chatgpt_teacher = True
            steps.append({"t":"auto_detect_teacher","msg":f"Teacher program ID: {program_id}"})
        
        print(f"URL: {url}")
        print(f"🔍 DEBUG: Extracted verification_id: {verification_id}")
        print(f"🔍 DEBUG: Extracted program_id: {program_id}")
        print(f"🔍 DEBUG: is_chatgpt_teacher: {is_chatgpt_teacher} (from_program={is_teacher_from_program})")
        steps.append({"t":"extract","msg":f"verificationId={verification_id}, programId={program_id}, isTeacher={is_chatgpt_teacher}"})
        
        if not verification_id:
            raise Exception("Không thể trích xuất verification ID từ URL")
        
        # DISABLED: PATCH locale no longer works - SheerID returns 405
        # SheerID now strictly enforces locale matching - we must use original locale
        # Attempting to change locale triggers fraud detection
        # try:
        #     print(f"🔄 Attempting to update verification locale to en-US...")
        #     patch_url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}"
        #     patch_payload = {"locale": "en-US"}
        #     ...
        # except Exception as e:
        #     print(f"⚠️ Error updating locale: {e}")
        print(f"ℹ️ PATCH locale DISABLED - SheerID now enforces locale matching (405 error)")
        print(f"ℹ️ Will use original locale from verification to avoid fraud detection")
        
        # Prepare API payload - Indonesia + carry UTM/ref for debug
        try:
            from urllib.parse import urlparse, parse_qs
            _p = urlparse(url)
            _qs = parse_qs(_p.query)
            utm_campaign = (_qs.get('utm_campaign') or [''])[0]
            utm_medium = (_qs.get('utm_medium') or [''])[0]
            utm_source = (_qs.get('utm_source') or [''])[0]
        except Exception:
            utm_campaign = utm_medium = utm_source = ''

        # Teacher flow (is_chatgpt_teacher already set above)
        if is_chatgpt_teacher:
            print(f"🎓 DEBUG: ChatGPT Teacher verification detected - using teacher flow")
            
            # Generate US teacher name and Gmail email - expanded 200+ names for better randomization
            us_first_names = [
                # Female names - Classic
                'Maria','Jennifer','Sarah','Emily','Jessica','Amanda','Ashley','Stephanie','Nicole','Elizabeth',
                'Michelle','Kimberly','Angela','Melissa','Rebecca','Laura','Christina','Katherine','Rachel','Heather',
                'Megan','Amy','Samantha','Brittany','Danielle','Tiffany','Amber','Crystal','Kelly','Lauren',
                'Courtney','Vanessa','Natalie','Lindsey','Kayla','Allison','Hannah','Alexis','Victoria','Jasmine',
                'Brooke','Chelsea','Erica','Jacqueline','Brenda','Diana','Cynthia','Patricia','Nancy','Sandra',
                'Carol','Donna','Sharon','Barbara','Susan','Dorothy','Lisa','Betty','Margaret','Karen',
                # Female names - Modern
                'Madison','Olivia','Emma','Sophia','Isabella','Ava','Mia','Abigail','Charlotte','Harper',
                'Evelyn','Amelia','Ella','Scarlett','Grace','Chloe','Camila','Penelope','Riley','Layla',
                'Zoey','Nora','Lily','Eleanor','Hazel','Violet','Aurora','Savannah','Audrey','Brooklyn',
                'Bella','Claire','Skylar','Lucy','Paisley','Anna','Caroline','Genesis','Aaliyah','Kennedy',
                # Male names - Classic
                'James','Michael','Robert','David','William','John','Christopher','Daniel','Matthew','Anthony',
                'Mark','Steven','Andrew','Paul','Joshua','Kenneth','Kevin','Brian','Timothy','Richard',
                'Thomas','Charles','Joseph','Donald','George','Edward','Ronald','Jason','Jeffrey','Ryan',
                'Jacob','Gary','Nicholas','Eric','Jonathan','Stephen','Larry','Justin','Scott','Brandon',
                'Benjamin','Samuel','Raymond','Gregory','Frank','Patrick','Peter','Henry','Douglas','Dennis',
                # Male names - Modern
                'Liam','Noah','Oliver','Elijah','Lucas','Mason','Logan','Alexander','Ethan','Sebastian',
                'Jack','Aiden','Owen','Carter','Jayden','Wyatt','Dylan','Grayson','Levi','Isaac',
                'Gabriel','Julian','Mateo','Jaxon','Lincoln','Theodore','Caleb','Asher','Nathan','Leo',
                'Isaiah','Hudson','Christian','Hunter','Connor','Eli','Ezra','Aaron','Landon','Adrian',
                'Nolan','Jeremiah','Easton','Elias','Colton','Cameron','Carson','Maverick','Dominic','Austin'
            ]
            us_last_names = [
                # Most common US surnames
                'Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Rodriguez','Martinez',
                'Hernandez','Lopez','Gonzalez','Wilson','Anderson','Thomas','Taylor','Moore','Jackson','Martin',
                'Lee','Thompson','White','Harris','Clark','Lewis','Robinson','Walker','Young','Allen',
                'King','Wright','Scott','Torres','Hill','Green','Adams','Nelson','Baker','Hall',
                'Rivera','Campbell','Mitchell','Carter','Roberts','Gomez','Phillips','Evans','Turner','Diaz',
                'Parker','Cruz','Edwards','Collins','Reyes','Stewart','Morris','Morales','Murphy','Cook',
                'Rogers','Gutierrez','Ortiz','Morgan','Cooper','Peterson','Bailey','Reed','Kelly','Howard',
                'Ramos','Kim','Cox','Ward','Richardson','Watson','Brooks','Chavez','Wood','James',
                'Bennett','Gray','Mendoza','Ruiz','Hughes','Price','Alvarez','Castillo','Sanders','Patel',
                'Myers','Long','Ross','Foster','Jimenez','Powell','Jenkins','Perry','Russell','Sullivan',
                # Additional surnames
                'Bell','Coleman','Butler','Henderson','Barnes','Gonzales','Fisher','Vasquez','Simmons','Graham',
                'Murray','Freeman','Wells','Webb','Simpson','Stevens','Tucker','Porter','Hunter','Hicks',
                'Crawford','Henry','Boyd','Mason','Moreno','Kennedy','Warren','Dixon','Burns','Gordon',
                'Shaw','Holmes','Rice','Robertson','Hunt','Black','Daniels','Palmer','Mills','Nichols',
                'Grant','Knight','Ferguson','Rose','Stone','Hawkins','Dunn','Perkins','Spencer','Lawrence'
            ]
            
            teacher_first = random.choice(us_first_names)
            teacher_last = random.choice(us_last_names)
            
            # Override names for teacher
            first_name = teacher_first
            last_name = teacher_last
            
            # Generate Gmail email for teacher
            email_prefix = f"{teacher_first.lower()}.{teacher_last.lower()}{random.randint(100,999)}"
            email = f"{email_prefix}@gmail.com"
            
            print(f"👤 DEBUG: Generated US teacher: {last_name} {first_name}")
            print(f"📧 DEBUG: Teacher email: {email}")
            
            # ChatGPT Teacher uses different organization and metadata
            # Extract organization from URL metadata if available
            try:
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                redirect_url = query_params.get('redirectUrl', [''])[0]
                print(f"🔗 DEBUG: Redirect URL: {redirect_url}")
            except Exception as e:
                print(f"⚠️ Could not parse redirect URL: {e}")
                redirect_url = "https://chatgpt.com/k12-verification"
            
            # Use US school district for ChatGPT Teacher - RANDOM from highschools_config.py
            # og-teacher-transcript.js now supports all schools in highschools_config.js
            selected_school = get_random_high_school()
            print(f"🏫 Random school selected: {selected_school['name']} ({selected_school.get('city', 'N/A')}, {selected_school.get('state', 'N/A')})")
            api_payload = {
                "firstName": first_name,  # Just first name for teacher
                "lastName": last_name,
                "birthDate": "",  # No birth date for teachers
                "email": email,
                "phoneNumber": "",
                "organization": {
                    "id": selected_school["id"],
                    "idExtended": selected_school["idExtended"],
                    "name": selected_school["name"]
                },
                "deviceFingerprintHash": generate_device_fingerprint(),
                "locale": "en-US",
                "metadata": {
                    "marketConsentValue": False,
                    "refererUrl": url,
                    "redirectUrl": redirect_url,
                    # ThreatMetrix session for fraud prevention bypass
                    "tmx_session_id": generate_threatmetrix_session(),
                    "threatMetrixSessionId": generate_threatmetrix_session(),
                    # Additional anti-fraud fields
                    "clientTimezone": random.choice(["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"]),
                    "clientTimezoneOffset": random.choice([-300, -360, -420, -480]),
                    "screenResolution": f"{random.choice([1920, 2560, 1366])}x{random.choice([1080, 1440, 768])}",
                    "colorDepth": 24,
                    "deviceMemory": random.choice([4, 8, 16]),
                    "hardwareConcurrency": random.choice([4, 8, 12, 16]),
                    "platform": "Win32",
                    "cookieEnabled": True,
                    "doNotTrack": None,
                    "flags": "{\"doc-upload-considerations\":\"default\",\"doc-upload-may24\":\"default\",\"doc-upload-redesign-use-legacy-message-keys\":false,\"docUpload-assertion-checklist\":\"default\",\"include-cvec-field-france-student\":\"not-labeled-optional\",\"org-search-overlay\":\"default\",\"org-selected-display\":\"default\"}",
                    "submissionOptIn": "By submitting the personal information above, I acknowledge that my personal information is being collected under the <a target=\"_blank\" rel=\"noopener noreferrer\" class=\"sid-privacy-policy sid-link\" href=\"https://openai.com/policies/privacy-policy/\">privacy policy</a> of the business from which I am seeking a discount, and I understand that my personal information will be shared with SheerID as a processor/third-party service provider in order for SheerID to confirm my eligibility for a special offer. <a target=\"_blank\" rel=\"noopener noreferrer\" class=\"sid-faq sid-link\" href=\"https://support.sheerid.com/en-US/68d47554aa292d20b9bec8f7/help-center\">More about SheerID.</a>"
                }
            }
            print(f"🎓 DEBUG: ChatGPT Teacher payload prepared with ThreatMetrix session")
        else:
            # Original student verification payload - University rotation with enhanced metadata
            # Generate realistic metadata for higher success rate
            screen_res = random.choice([(1920, 1080), (2560, 1440), (1366, 768), (1536, 864)])
            timezone_offset = random.choice([-300, -360, -420, -480])  # US timezones
            
            api_payload = {
                "firstName": first_name,
                "lastName": last_name,
                "birthDate": birth_date,
                "email": email,
                "deviceFingerprintHash": generate_device_fingerprint(),
                "locale": locale,
                "country": country,
                "metadata": {
                    "marketConsentValue": False,
                    "refererUrl": url,
                    "verificationId": verification_id,
                    # ThreatMetrix session for fraud prevention bypass
                    "tmx_session_id": generate_threatmetrix_session(),
                    "threatMetrixSessionId": generate_threatmetrix_session(),
                    # CRITICAL: Match timezone with university state to avoid fraud detection
                    "clientTimezone": get_timezone_for_state(university_state),
                    "clientTimezoneOffset": get_timezone_offset_for_state(university_state),
                    "screenResolution": f"{screen_res[0]}x{screen_res[1]}",
                    "colorDepth": 24,
                    "deviceMemory": random.choice([4, 8, 16]),
                    "hardwareConcurrency": random.choice([4, 8, 12, 16]),
                    "platform": "Win32",
                    "cookieEnabled": True,
                    "doNotTrack": None,
                    "flags": "{\"collect-info-step-email-first\":\"default\",\"doc-upload-considerations\":\"default\",\"doc-upload-may24\":\"default\",\"doc-upload-redesign-use-legacy-message-keys\":false,\"docUpload-assertion-checklist\":\"default\",\"font-size\":\"default\",\"include-cvec-field-france-student\":\"not-labeled-optional\"}",
                    "submissionOptIn": f"By submitting the personal information above, I acknowledge that my personal information is being collected under the privacy policy of the business from which I am seeking a discount, and I understand that my personal information will be shared with SheerID as a processor/third-party service provider in order for SheerID to confirm my eligibility for a special offer. <a target=\"_blank\" rel=\"noopener noreferrer\" class=\"sid-faq sid-link\" href=\"https://support.sheerid.com/en-US/{program_id}/help-center\">More about SheerID.</a>"
                },
                "organization": {
                    "id": university_id,
                    "idExtended": university_id_extended,
                    "name": university
                },
                "phoneNumber": "",
                "ipAddress": host_ip,
                "externalUserId": f"student_{random.randint(100000, 999999)}",
                "email2": "",
                "cvecNumber": ""
            }
        try:
            if is_chatgpt_teacher:
                print(f"DEBUG: POST collectTeacherPersonalInfo payload: {json.dumps(api_payload, ensure_ascii=False)[:800]}")
            else:
                print(f"DEBUG: POST collectStudentPersonalInfo payload: {json.dumps(api_payload, ensure_ascii=False)[:800]}")
        except Exception:
            pass
        
        # Validate required fields - birth_date not required for teacher verification
        if is_chatgpt_teacher:
            if not first_name or not last_name or not email:
                raise Exception("Thiếu thông tin bắt buộc trong payload (teacher)")
        else:
            if not first_name or not last_name or not email or not birth_date:
                raise Exception("Thiếu thông tin bắt buộc trong payload")
        
        # First try GET to check if verification exists
        get_response = None
        try:
            get_url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}"
            get_headers = {
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Origin': 'https://services.sheerid.com',
                'Referer': url
            }
            print(f"🌐 DEBUG: Trying GET to: {get_url}")
            _get_start = _t.time()
            get_response = make_request('get', get_url, headers=get_headers, timeout=30, use_scrape_proxy=use_scrape_proxy, session_id=proxy_session_id, country='us')
            print(f"📊 DEBUG: GET Response Status: {get_response.status_code} (took {_t.time()-_get_start:.2f}s)")
            print(f"📄 DEBUG: GET Response Text: {get_response.text[:500]}")
            steps.append({"t":"get","msg":f"GET verification → {get_response.status_code}"})
            
            # Parse response to check for error state BEFORE processing
            try:
                verification_status = get_response.json()
                current_step = verification_status.get('currentStep', '').lower()
                error_ids = verification_status.get('errorIds', [])
                system_error = verification_status.get('systemErrorMessage', '')
                
                # AUTO-DETECT Teacher verification from segment in GET response
                segment_from_get = verification_status.get('segment', '').lower()
                if segment_from_get == 'teacher' and not is_chatgpt_teacher:
                    print(f"🎓 AUTO-DETECT: Teacher segment detected from GET response")
                    print(f"   Switching to teacher verification flow")
                    is_chatgpt_teacher = True
                    steps.append({"t":"auto_detect_teacher_segment","msg":f"segment={segment_from_get}"})
                
                # Get locale from verification status - USE ORIGINAL LOCALE to avoid fraud detection
                original_locale = verification_status.get('locale', 'en-US')
                original_country = verification_status.get('country', '')
                print(f"🌍 Verification original locale: {original_locale}, country: {original_country}")
                
                # NOTE: We previously tried to block non-US locales, but testing shows that
                # SheerID doesn't always reject locale mismatch. The fraud detection is more
                # complex and depends on multiple factors (account history, program rules, etc.)
                # So we'll proceed with the original locale and let SheerID decide.
                
                # CRITICAL FIX: Use ORIGINAL locale from verification to avoid fraud detection
                # SheerID now detects locale mismatch and rejects with fraudRulesReject
                # If original locale is set (e.g., 'ko', 'ja', 'zh'), we MUST use it
                if original_locale and original_locale != 'null':
                    api_payload['locale'] = original_locale
                    print(f"📝 Using ORIGINAL locale: {original_locale} (to match verification)")
                else:
                    api_payload['locale'] = 'en-US'
                    print(f"📝 No original locale, defaulting to: en-US")
                
                # For country, use original if set, otherwise keep US for US universities
                if original_country and original_country != 'null':
                    api_payload['country'] = original_country
                    print(f"📝 Using ORIGINAL country: {original_country}")
                else:
                    # Keep country as US since we're using US universities
                    api_payload['country'] = 'US'
                    print(f"📝 No original country, using: US (for US university)")
                
                # Check if link is already in error state - skip processing to avoid false fail count
                if current_step == 'error' or error_ids:
                    error_msg = error_ids[0] if error_ids else system_error or 'Unknown error'
                    print(f"⚠️ Link already in error state: {error_msg}")
                    steps.append({"t":"skip","msg":f"Link already failed: {error_msg}"})
                    
                    # Map common errors to user-friendly messages
                    error_messages = {
                        'docReviewLimitExceeded': '❌ Link đã vượt quá giới hạn review. Vui lòng dùng link mới.',
                        'verificationExpired': '❌ Link đã hết hạn. Vui lòng tạo link mới.',
                        'maxAttemptsExceeded': '❌ Link đã vượt quá số lần thử. Vui lòng dùng link mới.',
                        'invalidVerification': '❌ Link không hợp lệ. Vui lòng kiểm tra lại.',
                        'noVerification': '❌ Link không tồn tại hoặc đã hết hạn. Vui lòng lấy link mới từ trang ChatGPT/Gemini.',
                    }
                    user_error = error_messages.get(error_msg, f'❌ Link đã bị lỗi: {error_msg}. Vui lòng dùng link mới.')
                    
                    # Send notification directly to user about error link
                    print(f"📤 DEBUG: Attempting to send error notification for job_id={job_id}")
                    if job_id:
                        try:
                            import requests as req_lib  # Use alias to avoid shadowing
                            from .supabase_client import get_verification_job_by_id, update_verification_job_status
                            job_info = get_verification_job_by_id(job_id)
                            print(f"📤 DEBUG: job_info found: {bool(job_info)}")
                            if job_info:
                                telegram_id = job_info.get('telegram_id')
                                user_lang = job_info.get('language', 'vi')
                                print(f"📤 DEBUG: telegram_id={telegram_id}, user_lang={user_lang}")
                                if telegram_id:
                                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                                    if bot_token:
                                        # Multilingual error link messages
                                        error_msgs = {
                                            'vi': f"⚠️ LINK BỊ LỖI\n\n🆔 Job ID: {job_id[:8]}...\n📝 Lý do: {user_error}\n\n💡 Vui lòng gửi link mới để verify.\n📖 Hướng dẫn: https://t.me/channel_sheerid_vip_bot/135\n💰 Không bị trừ xu/cash\n📞 Hỗ trợ: @meepzizhere",
                                            'en': f"⚠️ LINK ERROR\n\n🆔 Job ID: {job_id[:8]}...\n📝 Reason: {user_error}\n\n💡 Please send a new link to verify.\n📖 Guide: https://t.me/channel_sheerid_vip_bot/135\n💰 No xu/cash deducted\n📞 Support: @meepzizhere",
                                            'zh': f"⚠️ 链接错误\n\n🆔 Job ID: {job_id[:8]}...\n📝 原因: {user_error}\n\n💡 请发送新链接进行验证。\n📖 指南: https://t.me/channel_sheerid_vip_bot/135\n💰 未扣除 xu/cash\n📞 支持: @meepzizhere"
                                        }
                                        msg = error_msgs.get(user_lang, error_msgs['vi'])
                                        url_tg = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                        data_tg = {"chat_id": telegram_id, "text": msg}
                                        resp_tg = req_lib.post(url_tg, data=data_tg, timeout=30)
                                        print(f"📤 Error link notification sent to {telegram_id}: {resp_tg.status_code}")
                                        if resp_tg.status_code != 200:
                                            print(f"📤 DEBUG: Telegram response: {resp_tg.text}")
                                    else:
                                        print(f"📤 DEBUG: No bot_token found!")
                                else:
                                    print(f"📤 DEBUG: No telegram_id in job_info!")
                            else:
                                print(f"📤 DEBUG: job_info is None for job_id={job_id}")
                            # Update job status to skipped (not failed, since link was already bad)
                            update_verification_job_status(job_id, 'skipped')
                            print(f"📤 DEBUG: Updated job status to 'skipped'")
                        except Exception as e:
                            print(f"⚠️ Failed to send error link notification: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"📤 DEBUG: No job_id provided, cannot send notification")
                    
                    return {
                        "success": False,
                        "error": user_error,
                        "skip_fail_count": True,  # Flag to skip counting as failed
                        "already_failed": True,
                        "debug_info": {"steps": steps, "original_error": error_msg}
                    }
                
                # Check if link is already in pending/docUpload state with rejectionReasons (already used link)
                rejection_reasons = verification_status.get('rejectionReasons', [])
                awaiting_step = verification_status.get('awaitingStep', '').lower()
                last_response = verification_status.get('lastResponse', {})
                last_rejection = last_response.get('rejectionReasons', []) if isinstance(last_response, dict) else []
                
                # Combine rejection reasons from both places
                all_rejections = rejection_reasons + last_rejection
                
                if (current_step == 'pending' and awaiting_step == 'docupload') or all_rejections:
                    if all_rejections:
                        rejection_msg = ', '.join(all_rejections)
                        print(f"⚠️ Link already used with rejectionReasons: {rejection_msg}")
                        steps.append({"t":"skip","msg":f"Link already rejected: {rejection_msg}"})
                        
                        # Map rejection reasons to user-friendly messages
                        rejection_messages = {
                            'DOCUMENT_LIKELY_FRAUD': '❌ Link đã bị từ chối (nghi ngờ gian lận). Vui lòng dùng link mới.',
                            'DOCUMENT_UNREADABLE': '❌ Link đã bị từ chối (tài liệu không đọc được). Vui lòng dùng link mới.',
                            'DOCUMENT_EXPIRED': '❌ Link đã bị từ chối (tài liệu hết hạn). Vui lòng dùng link mới.',
                            'DOCUMENT_INVALID': '❌ Link đã bị từ chối (tài liệu không hợp lệ). Vui lòng dùng link mới.',
                        }
                        
                        # Get first matching rejection message
                        user_error = '❌ Link đã bị từ chối. Vui lòng dùng link mới.'
                        for reason in all_rejections:
                            if reason in rejection_messages:
                                user_error = rejection_messages[reason]
                                break
                        
                        # Send notification directly to user about rejected link
                        if job_id:
                            try:
                                from .supabase_client import get_verification_job_by_id, update_verification_job_status
                                job_info = get_verification_job_by_id(job_id)
                                if job_info:
                                    telegram_id = job_info.get('telegram_id')
                                    user_lang = job_info.get('language', 'vi')
                                    if telegram_id:
                                        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                                        if bot_token:
                                            # Multilingual rejected link messages
                                            reject_msgs = {
                                                'vi': f"⚠️ LINK ĐÃ BỊ TỪ CHỐI\n\n🆔 Job ID: {job_id}\n📝 Lý do: {user_error}\n\n💡 Vui lòng gửi link mới để verify.\n📖 Hướng dẫn: https://t.me/channel_sheerid_vip_bot/135\n💰 Không bị trừ xu/cash\n📞 Hỗ trợ: @meepzizhere",
                                                'en': f"⚠️ LINK REJECTED\n\n🆔 Job ID: {job_id}\n📝 Reason: Link has been rejected. Please use a new link.\n\n💡 Please send a new link to verify.\n📖 Guide: https://t.me/channel_sheerid_vip_bot/135\n💰 No xu/cash deducted\n📞 Support: @meepzizhere",
                                                'zh': f"⚠️ 链接被拒绝\n\n🆔 Job ID: {job_id}\n📝 原因: 链接已被拒绝。请使用新链接。\n\n💡 请发送新链接进行验证。\n📖 指南: https://t.me/channel_sheerid_vip_bot/135\n💰 未扣除 xu/cash\n📞 支持: @meepzizhere"
                                            }
                                            msg = reject_msgs.get(user_lang, reject_msgs['vi'])
                                            url_tg = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                            data_tg = {"chat_id": telegram_id, "text": msg}
                                            resp_tg = requests.post(url_tg, data=data_tg, timeout=30)
                                            print(f"📤 Rejected link notification sent: {resp_tg.status_code}")
                                # Update job status to skipped
                                update_verification_job_status(job_id, 'skipped')
                            except Exception as e:
                                print(f"⚠️ Failed to send rejected link notification: {e}")
                        
                        return {
                            "success": False,
                            "error": user_error,
                            "skip_fail_count": True,  # Flag to skip counting as failed
                            "already_rejected": True,
                            "rejection_reasons": all_rejections,
                            "debug_info": {"steps": steps, "rejection_reasons": all_rejections}
                        }
                    elif current_step == 'pending' and awaiting_step == 'docupload':
                        print(f"⚠️ Link already in pending/docUpload state - already used")
                        steps.append({"t":"skip","msg":"Link already in pending/docUpload state"})
                        
                        # Send notification directly to user about pending link
                        if job_id:
                            try:
                                from .supabase_client import get_verification_job_by_id, update_verification_job_status
                                job_info = get_verification_job_by_id(job_id)
                                if job_info:
                                    telegram_id = job_info.get('telegram_id')
                                    user_lang = job_info.get('language', 'vi')
                                    if telegram_id:
                                        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                                        if bot_token:
                                            # Multilingual pending link messages
                                            pending_msgs = {
                                                'vi': f"⚠️ LINK ĐÃ ĐƯỢC SỬ DỤNG\n\n🆔 Job ID: {job_id}\n📝 Lý do: Link đã được sử dụng và đang chờ xử lý.\n\n💡 Vui lòng gửi link mới để verify.\n📖 Hướng dẫn: https://t.me/channel_sheerid_vip_bot/135\n💰 Không bị trừ xu/cash\n📞 Hỗ trợ: @meepzizhere",
                                                'en': f"⚠️ LINK ALREADY USED\n\n🆔 Job ID: {job_id}\n📝 Reason: Link has been used and is pending processing.\n\n💡 Please send a new link to verify.\n📖 Guide: https://t.me/channel_sheerid_vip_bot/135\n💰 No xu/cash deducted\n📞 Support: @meepzizhere",
                                                'zh': f"⚠️ 链接已被使用\n\n🆔 Job ID: {job_id}\n📝 原因: 链接已被使用，正在等待处理。\n\n💡 请发送新链接进行验证。\n📖 指南: https://t.me/channel_sheerid_vip_bot/135\n💰 未扣除 xu/cash\n📞 支持: @meepzizhere"
                                            }
                                            msg = pending_msgs.get(user_lang, pending_msgs['vi'])
                                            url_tg = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                            data_tg = {"chat_id": telegram_id, "text": msg}
                                            resp_tg = requests.post(url_tg, data=data_tg, timeout=30)
                                            print(f"📤 Pending link notification sent: {resp_tg.status_code}")
                                # Update job status to skipped
                                update_verification_job_status(job_id, 'skipped')
                            except Exception as e:
                                print(f"⚠️ Failed to send pending link notification: {e}")
                        
                        return {
                            "success": False,
                            "error": "❌ Link đã được sử dụng và đang chờ xử lý. Vui lòng dùng link mới.",
                            "skip_fail_count": True,
                            "already_pending": True,
                            "debug_info": {"steps": steps}
                        }
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse verification status JSON")
            
            # Check if verification exists
            if get_response.status_code == 404:
                print(f"❌ Verification {verification_id} not found (404)")
                steps.append({"t":"error","msg":f"Verification {verification_id} not found"})
                return {
                    "success": False,
                    "error": f"❌ Verification ID không tồn tại: {verification_id}. Vui lòng kiểm tra lại URL và thử lại.",
                    "skip_fail_count": True,  # Don't count as failed attempt
                    "debug_info": {"steps": steps}
                }
            elif get_response.status_code != 200:
                print(f"❌ Verification check failed with status {get_response.status_code}")
                steps.append({"t":"error","msg":f"Verification check failed: {get_response.status_code}"})
                return {
                    "success": False,
                    "error": f"Failed to verify verification ID. Status: {get_response.status_code}",
                    "skip_fail_count": True,  # Don't count as failed attempt
                    "debug_info": {"steps": steps}
                }
                
        except Exception as e:
            print(f"GET request failed: {e}")
            steps.append({"t":"get","msg":f"GET failed: {str(e)}"})
            # Simplify error message for user - hide technical details
            user_error = "Xác minh thất bại 404"
            return {
                "success": False,
                "error": user_error,
                "debug_info": {"steps": steps}
            }
        
        # Device fingerprinting and analytics step (before SSO)
        # Can be skipped with SKIP_FINGERPRINTING for faster verification
        if SKIP_FINGERPRINTING:
            print(f"⚡ SKIP_FINGERPRINTING: Skipping device fingerprinting and analytics")
            steps.append({"t":"fingerprint","msg":"Skipped (SKIP_FINGERPRINTING=True)"})
            status_data = {}  # Initialize empty status_data
        else:
          try:
            print(f"DEBUG: Performing device fingerprinting and analytics...")
            steps.append({"t":"fingerprint","msg":"Starting device fingerprinting"})
            
            # Use enhanced fingerprint profiles module (70+ real device configurations)
            try:
                from .fingerprint_profiles import generate_fingerprint_data, get_fingerprint_url
                
                # Generate complete fingerprint with realistic hardware profile
                fp_result = generate_fingerprint_data(verification_id, url)
                fingerprint_data = fp_result['fingerprint_data']
                fingerprint_headers = fp_result['headers']
                user_agent = fp_result['user_agent']
                selected_chrome = fp_result['chrome_version']
                
                print(f"🎭 Enhanced fingerprint: {fp_result['profile']['name']}")
                print(f"   GPU: {fp_result['gpu'][:50]}...")
                print(f"   Screen: {fp_result['screen']}, Platform: {fp_result['platform']}")
                print(f"   Chrome/{selected_chrome}, TZ: {fp_result['timezone']}")
                print(f"   Fonts: {len(fingerprint_data.get('dtaa[]', []))} fonts")
                
                # Use correct IPQS token URL
                fingerprint_url = get_fingerprint_url()
                
            except ImportError as ie:
                print(f"⚠️ Could not import fingerprint_profiles: {ie}, using fallback")
                # Fallback to basic fingerprint if module not available
                chrome_versions = ['120', '121', '122', '123', '124', '125', '126', '127', '128', '129', '130', '131']
                selected_chrome = random.choice(chrome_versions)
                user_agent = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{selected_chrome}.0.0.0 Safari/537.36'
                
                fingerprint_data = {
                    'fast': '1',
                    'dta[]': json.dumps({"key": "transactionID", "value": verification_id}),
                    'ipqsd': str(random.randint(100000000000000000, 999999999999999999)),
                    'dtb': user_agent,
                    'dtc': 'en-US',
                    'dtg': json.dumps([1920, 1080]),
                    'dth': json.dumps([1920, 1040]),
                    'dto': 'Win32',
                    'dts': 'NVIDIA, NVIDIA GeForce RTX 3060 (0x00002503) Direct3D11 vs_5_0 ps_5_0, D3D11',
                    'dtls[]': ['en-US', 'en'],
                    'dtaa[]': ['Arial', 'Times New Roman', 'Calibri', 'Verdana', 'Georgia', 'Tahoma'],
                }
                
                fingerprint_url = "https://fn.us.fd.sheerid.com/api/*/BJOvvIiNpZnA9XHXIHVc0S4FO87k4eub6NLOfmShTU7nRqamLKTzQixwD7XETz7bvtNHmicHNx9hEtOJ9NPo3kUJBl7o1jpwcbcXeOMDJjvulAWSrRnO7WYq9gxL6xNT0xnfou5UlshUGWQ2g68qBuWajMWbxZ25JELntxaP0neiVUbephG5E79ES89qBo4uIGBDvykdJb75hpo0URvJ0Fm1j6fuEqHQBq64Mi390KC9XoQwiFxyboxQ5lSooY4p/learn/fetch"
                
                fingerprint_headers = {
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate, br, zstd',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Connection': 'keep-alive',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Host': 'fn.us.fd.sheerid.com',
                    'Origin': 'https://services.sheerid.com',
                    'Referer': url,
                    'Sec-Ch-Ua': f'"Not;A=Brand";v="99", "Google Chrome";v="{selected_chrome}", "Chromium";v="{selected_chrome}"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"Windows"',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-site',
                    'User-Agent': user_agent
                }
                
                print(f"🎭 Fallback fingerprint: Chrome/{selected_chrome}")
            
            # Anti-detection: Random delay before fingerprinting (0.5-1.5s)
            if not fast_mode:
                fp_delay = random.uniform(0.5, 1.5)
                time.sleep(fp_delay)
            
            print(f"DEBUG: Sending device fingerprinting to: {fingerprint_url}")
            _fp_start = _t.time()
            fingerprint_response = make_request('post', fingerprint_url, data=fingerprint_data, headers=fingerprint_headers, timeout=30, use_scrape_proxy=use_scrape_proxy, session_id=proxy_session_id, country='us')
            print(f"DEBUG: Fingerprinting response: {fingerprint_response.status_code} (took {_t.time()-_fp_start:.2f}s)")
            steps.append({"t":"fingerprint","msg":f"Device fingerprinting → {fingerprint_response.status_code}"})
            
            # ThreatMetrix profiling request - CRITICAL for fraud prevention bypass
            # ThreatMetrix collects device/browser fingerprint for fraud detection
            # Controlled by ENABLE_THREATMETRIX flag
            if ENABLE_THREATMETRIX:
                try:
                    tmx_session_id = generate_threatmetrix_session()
                    tmx_org_id = "sheerid"  # SheerID's ThreatMetrix org ID
                    
                    # ThreatMetrix profiling endpoint
                    tmx_url = f"https://h.online-metrix.net/fp/tags.js?org_id={tmx_org_id}&session_id={tmx_session_id}"
                    
                    tmx_headers = {
                        'Accept': '*/*',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'User-Agent': user_agent,
                        'Referer': 'https://services.sheerid.com/',
                        'Origin': 'https://services.sheerid.com',
                        'Sec-Fetch-Dest': 'script',
                        'Sec-Fetch-Mode': 'no-cors',
                        'Sec-Fetch-Site': 'cross-site'
                    }
                    
                    print(f"🔒 ThreatMetrix: Sending profiling request with session={tmx_session_id[:20]}...")
                    _tmx_start = _t.time()
                    tmx_response = make_request('get', tmx_url, headers=tmx_headers, timeout=15, use_scrape_proxy=use_scrape_proxy, session_id=proxy_session_id, country='us')
                    print(f"🔒 ThreatMetrix response: {tmx_response.status_code} (took {_t.time()-_tmx_start:.2f}s)")
                    steps.append({"t":"threatmetrix","msg":f"ThreatMetrix profiling → {tmx_response.status_code}"})
                    
                    # Store TMX session for later use in payload
                    api_payload['metadata']['tmx_session_id'] = tmx_session_id
                    api_payload['metadata']['threatMetrixSessionId'] = tmx_session_id
                    
                except Exception as tmx_error:
                    print(f"⚠️ ThreatMetrix profiling failed: {tmx_error}")
                    steps.append({"t":"threatmetrix","msg":f"Failed: {str(tmx_error)[:50]}"})
            else:
                print(f"⏭️ ThreatMetrix: DISABLED (ENABLE_THREATMETRIX=False)")
                steps.append({"t":"threatmetrix","msg":"Skipped (ENABLE_THREATMETRIX=False)"})
            
            # Anti-detection: Random delay before analytics (0.3-1.0s)
            if not fast_mode:
                analytics_delay = random.uniform(0.3, 1.0)
                time.sleep(analytics_delay)
            
            # LaunchDarkly analytics
            analytics_data = [
                {
                    "kind": "identify",
                    "context": {
                        "kind": "multi",
                        "user": {
                            "key": verification_id,
                            "segment": "student",
                            "locale": "de"
                        },
                        "program": {
                            "key": url.split('/verify/')[1].split('/')[0] if '/verify/' in url else verification_id
                        }
                    },
                    "creationDate": int(time.time() * 1000)
                },
                {
                    "kind": "summary",
                    "startDate": int(time.time() * 1000),
                    "endDate": int(time.time() * 1000) + 5,
                    "features": {}
                }
            ]
            
            analytics_url = f"https://events.launchdarkly.com/events/bulk/6530161f9ff41712a2eef741"
            analytics_headers = {
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Content-Type': 'application/json',
                'Origin': 'https://services.sheerid.com',
                'Referer': url,
                'Sec-Ch-Ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
                'X-Launchdarkly-Event-Schema': '4',
                'X-Launchdarkly-Payload-Id': f"{random.randint(10000000, 99999999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(100000000000000000, 999999999999999999)}",
                'X-Launchdarkly-User-Agent': 'JSClient/3.5.0',
                'X-Launchdarkly-Wrapper': 'react-client-sdk/3.6.1'
            }
            
            print(f"DEBUG: Sending analytics to: {analytics_url}")
            _analytics_start = _t.time()
            analytics_response = make_request('post', analytics_url, json=analytics_data, headers=analytics_headers, timeout=30, use_scrape_proxy=use_scrape_proxy, session_id=proxy_session_id, country='us')
            print(f"DEBUG: Analytics response: {analytics_response.status_code} (took {_t.time()-_analytics_start:.2f}s)")
            steps.append({"t":"analytics","msg":f"LaunchDarkly analytics → {analytics_response.status_code}"})
            
            # Check verification status again after fingerprinting
            print(f"DEBUG: Checking verification status after fingerprinting...")
            status_data = {}
            try:
                status_check_url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}"
                status_response = make_request('get', status_check_url, headers=get_headers, timeout=30, use_scrape_proxy=use_scrape_proxy, session_id=proxy_session_id, country='us')
                try:
                    status_data = status_response.json()
                except json.JSONDecodeError as e:
                    print(f"Failed to parse status response JSON: {e}")
                    status_data = {}
                print(f"DEBUG: Status after fingerprinting: {json.dumps(status_data, indent=2)}")
                steps.append({"t":"status","msg":f"Status after fingerprinting: {status_data.get('currentStep', 'unknown')}"})
                
                # Check for rejectionReasons after fingerprinting - this is where they often appear
                post_fp_rejections = status_data.get('rejectionReasons', [])
                if post_fp_rejections:
                    rejection_msg = ', '.join(post_fp_rejections)
                    print(f"⚠️ Link has rejectionReasons after fingerprinting: {rejection_msg}")
                    steps.append({"t":"skip","msg":f"Link rejected after fingerprinting: {rejection_msg}"})
                    
                    # Map rejection reasons to user-friendly messages
                    rejection_messages = {
                        'DOCUMENT_LIKELY_FRAUD': '❌ Link đã bị từ chối (nghi ngờ gian lận). Vui lòng dùng link mới.',
                        'DOCUMENT_UNREADABLE': '❌ Link đã bị từ chối (tài liệu không đọc được). Vui lòng dùng link mới.',
                        'DOCUMENT_EXPIRED': '❌ Link đã bị từ chối (tài liệu hết hạn). Vui lòng dùng link mới.',
                        'DOCUMENT_INVALID': '❌ Link đã bị từ chối (tài liệu không hợp lệ). Vui lòng dùng link mới.',
                    }
                    
                    user_error = '❌ Link đã bị từ chối. Vui lòng dùng link mới.'
                    for reason in post_fp_rejections:
                        if reason in rejection_messages:
                            user_error = rejection_messages[reason]
                            break
                    
                    return {
                        "success": False,
                        "error": user_error,
                        "skip_fail_count": True,
                        "already_rejected": True,
                        "rejection_reasons": post_fp_rejections,
                        "debug_info": {"steps": steps, "rejection_reasons": post_fp_rejections}
                    }
            except Exception as e:
                print(f"DEBUG: Status check failed: {e}")
                steps.append({"t":"status","msg":f"Status check failed: {str(e)}"})
            
            # CRITICAL: Check if verification succeeded after fingerprinting (instant approval)
            post_fp_step = status_data.get('currentStep', '') if status_data else ''
            if post_fp_step in ['success', 'complete', 'verified']:
                print(f"🎉 INSTANT SUCCESS: Verification approved after fingerprinting! Step: {post_fp_step}")
                steps.append({"t":"instant_success","msg":f"Approved after fingerprinting: {post_fp_step}"})
                
                # Update job status and return success
                if job_id:
                    try:
                        from .supabase_client import update_verification_job_status
                        update_verification_job_status(job_id, 'completed', university=university)
                        print(f"✅ Updated job {job_id} status to completed (instant approval)")
                    except Exception as ue:
                        print(f"⚠️ Failed to update job status: {ue}")
                
                return {
                    "success": True,
                    "verification_id": verification_id,
                    "status": "success",
                    "instant_approval": True,
                    "message": "Verification approved instantly after fingerprinting",
                    "debug_info": {"steps": steps}
                }
            
          except Exception as e:
            print(f"DEBUG: Device fingerprinting/analytics failed: {e}")
            steps.append({"t":"fingerprint","msg":f"Fingerprinting failed: {str(e)}"})
        
        # Determine the correct step to POST to based on currentStep
        current_step = None
        rejection_reasons = []
        try:
            # Get current step from the initial GET request
            if get_response and get_response.status_code == 200:
                try:
                    get_data = get_response.json()
                except json.JSONDecodeError as e:
                    print(f"Failed to parse GET response JSON: {e}")
                    get_data = {}
                current_step = get_data.get('currentStep')
                rejection_reasons = get_data.get('rejectionReasons', [])
                print(f"DEBUG: Current step from initial GET: {current_step}")
                if rejection_reasons:
                    print(f"DEBUG: Rejection reasons: {rejection_reasons}")
        except:
            pass
        
        # Check if verification is already completed
        print(f"🔍 DEBUG: Checking currentStep: {current_step}")
        if current_step in ["success", "complete", "verified"]:
            print(f"✅ Verification already completed: {verification_id}")
            
            if job_id:
                try:
                    from .supabase_client import get_verification_job_by_id, update_verification_job_status
                    
                    # Update job status
                    update_verification_job_status(job_id, 'completed')
                    print(f"✅ Updated job {job_id} status to completed (already successful)")
                    
                    # Send notification directly for already verified link (no charge)
                    job_info = get_verification_job_by_id(job_id)
                    if job_info:
                        telegram_id = job_info.get('telegram_id')
                        if telegram_id:
                            bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                            if bot_token:
                                msg = f"✅ LINK ĐÃ VERIFY THÀNH CÔNG TỪ TRƯỚC\n\n🆔 Job ID: {job_id}\n📝 Link này đã được xác minh thành công rồi!\n\n💰 Không tính phí vì link đã verify từ trước."
                                url_tg = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                data_tg = {"chat_id": telegram_id, "text": msg}
                                resp_tg = requests.post(url_tg, data=data_tg, timeout=30)
                                print(f"📤 Already verified notification sent: {resp_tg.status_code}")
                    
                except Exception as e:
                    print(f"❌ Error updating job status: {e}")
                
                # Mark job as already processed to prevent duplicate processing
                mark_job_as_charged(job_id)
                print(f"✅ Marked job {job_id} as already processed (already verified)")
                
                # Return success without charging (already verified)
                # Generate a dummy student_id for display
                # import random  # Using global import
                dummy_student_id = f"{random.randint(10000000, 99999999)}"  # 8 random digits
                
                return {
                    "success": True,
                    "message": "Link này đã verify thành công rồi mà :3",
                    "status": "approved", 
                    "stage": current_step,
                    "job_id": job_id,
                    "already_verified": True,
                    "student_info": {
                        "name": f"{first_name} {last_name}",
                        "first_name": first_name,
                        "last_name": last_name,
                        "birth_date": birth_date,
                        "student_id": dummy_student_id
                    }
                }
        
        # Check if verification is at docUpload step - needs manual intervention
        elif current_step.lower() == "docupload":
            print(f"📄 Verification at docUpload step: {verification_id}")
            
            # Send notification to user about docUpload step
            if job_id:
                try:
                    from .supabase_client import get_verification_job_by_id, update_verification_job_status
                    from .telegram import is_notification_already_sent, mark_notification_sent
                    
                    # Always send notification for docUpload step (user needs to know)
                    notification_already_sent = is_notification_already_sent(job_id)
                    if notification_already_sent:
                        print(f"⚠️ DocUpload notification already sent for job {job_id}, but still sending reminder")
                    
                    # Update job status to docUpload (NOT completed - user needs to take action)
                    update_verification_job_status(job_id, 'docUpload')
                    print(f"✅ Updated job {job_id} status to docUpload (user received instructions)")
                    
                    # Get user info to send notification
                    job_info = get_verification_job_by_id(job_id)
                    if job_info:
                        telegram_id = job_info.get('telegram_id')
                        user_lang = job_info.get('language', 'vi')
                        if telegram_id:
                            # Send notification about docUpload step
                            bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                            if bot_token:
                                # Check if there are rejection reasons
                                if rejection_reasons:
                                    # Document was rejected - don't send notification here, let other system handle it
                                    print(f"🔇 Document rejected, skipping notification - will be handled by other system")
                                    # Mark notification as sent to prevent duplicate
                                    mark_notification_sent(job_id)
                                    print(f"✅ Marked rejection notification as sent for job {job_id}")
                                else:
                                    # Multilingual docUpload instruction
                                    docupload_msgs = {
                                        'vi': f"""⚠️ Xác minh thất bại. Link của bạn bị Xác minh, vui lòng vào link và upload ảnh nào đó tầm 3 lần để lấy link mới.

🆔 Job ID: {job_id}
🔗 Link: {url}

💡 Hướng dẫn xử lý:
1️⃣ Vào link trên
2️⃣ Upload bậy tấm hình nào đó 3 lần 
3️⃣ Hệ thống sẽ trả form mới
4️⃣ Copy link mới và verify lại

🎯 Lưu ý: Cần upload đúng 3 lần để được form mới!
💰 Không bị trừ xu/cash
📞 Hỗ trợ: @meepzizhere""",
                                        'en': f"""⚠️ Verification failed. Your link requires document upload, please go to the link and upload any image about 3 times to get a new link.

🆔 Job ID: {job_id}
🔗 Link: {url}

💡 Instructions:
1️⃣ Go to the link above
2️⃣ Upload any random image 3 times
3️⃣ System will return a new form
4️⃣ Copy the new link and verify again

🎯 Note: Need to upload exactly 3 times to get a new form!
💰 No xu/cash deducted
📞 Support: @meepzizhere""",
                                        'zh': f"""⚠️ 验证失败。您的链接需要上传文档，请进入链接并上传任意图片约3次以获取新链接。

🆔 Job ID: {job_id}
🔗 链接: {url}

💡 操作说明:
1️⃣ 进入上面的链接
2️⃣ 上传任意图片3次
3️⃣ 系统将返回新表单
4️⃣ 复制新链接并重新验证

🎯 注意: 需要上传正好3次才能获得新表单！
💰 未扣除 xu/cash
📞 支持: @meepzizhere"""
                                    }
                                    message = docupload_msgs.get(user_lang, docupload_msgs['vi'])
                                    
                                    resp = requests.post(
                                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                        json={
                                            "chat_id": str(telegram_id),
                                            "text": message
                                        },
                                        timeout=15
                                    )
                                    if resp.status_code == 200:
                                        print(f"✅ Sent 'docUpload step' notification to user {telegram_id}")
                                    else:
                                        print(f"❌ Failed to send docUpload notification: {resp.status_code} - {resp.text}")
                                
                                # Mark notification as sent
                                mark_notification_sent(job_id)
                                print(f"✅ Marked docUpload notification as sent for job {job_id}")
                except Exception as e:
                    print(f"❌ Error sending docUpload notification: {e}")
                
                # Mark job as processed to prevent duplicate processing by polling system
                mark_job_as_charged(job_id)
                print(f"✅ Marked job {job_id} as processed (docUpload case)")
                
                # Return with appropriate message based on rejection status
                if rejection_reasons:
                    return {
                        "success": False,
                        "message": f"Document bị từ chối: {', '.join(rejection_reasons)}",
                        "status": "rejected",
                        "stage": current_step,
                        "job_id": job_id,
                        "rejection_reasons": rejection_reasons,
                        "student_info": {
                            "name": f"{first_name} {last_name}",
                            "first_name": first_name,
                            "last_name": last_name,
                            "birth_date": birth_date,
                            "student_id": "N/A"
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": "Link đang ở bước Upload proof - cần xử lý thủ công",
                        "status": "docUpload",
                        "stage": current_step,
                        "job_id": job_id,
                        "instruction": "Vào link upload bậy 3 tấm hình để được form mới",
                        "student_info": {
                            "name": f"{first_name} {last_name}",
                            "first_name": first_name,
                            "last_name": last_name,
                            "birth_date": birth_date,
                            "student_id": "N/A"
                        }
                    }
        
        # Check if verification is in pending/reviewing state
        elif current_step.lower() == "pending":
            print(f"⏳ Verification in pending/reviewing state: {verification_id}")
            
            # Send notification to user about pending state
            if job_id:
                try:
                    from .supabase_client import get_verification_job_by_id, update_verification_job_status
                    from .telegram import is_notification_already_sent, mark_notification_sent
                    
                    # Always send notification for pending step (user needs to know)
                    notification_already_sent = is_notification_already_sent(job_id)
                    if notification_already_sent:
                        print(f"⚠️ Pending notification already sent for job {job_id}, but still sending reminder")
                    
                    # Update job status to pending (NOT completed - waiting for review)
                    update_verification_job_status(job_id, 'pending')
                    print(f"✅ Updated job {job_id} status to pending (waiting for review)")
                    
                    # Get user info to send notification
                    job_info = get_verification_job_by_id(job_id)
                    if job_info:
                        telegram_id = job_info.get('telegram_id')
                        user_lang = job_info.get('language', 'vi')
                        if telegram_id:
                            # Send notification about pending state
                            bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                            if bot_token:
                                # Multilingual pending/reviewing messages
                                pending_msgs = {
                                    'vi': f"""⏳ Link của bạn đã ở trạng thái Reviewing (đang xem xét)

🆔 Job ID: {job_id}
📋 Trạng thái: Đang được review bởi SheerID
🔗 Link: {url}

💡 Hướng dẫn:
⏰ Vui lòng chờ 30 phút - 2 tiếng để lấy link mới
🔄 Hoặc vào tài khoản khác để tạo link mới

🎯 Lưu ý: 
• SheerID đang xem xét thông tin của bạn
• Không cần làm gì thêm, chỉ cần chờ
• Sau khi review xong sẽ có link mới

💰 Không bị trừ xu/cash
📞 Hỗ trợ: @meepzizhere""",
                                    'en': f"""⏳ Your link is in Reviewing status

🆔 Job ID: {job_id}
📋 Status: Being reviewed by SheerID
🔗 Link: {url}

💡 Instructions:
⏰ Please wait 30 minutes - 2 hours to get a new link
🔄 Or go to another account to create a new link

🎯 Note: 
• SheerID is reviewing your information
• No action needed, just wait
• A new link will be available after review

💰 No xu/cash deducted
📞 Support: @meepzizhere""",
                                    'zh': f"""⏳ 您的链接正在审核中

🆔 Job ID: {job_id}
📋 状态: SheerID正在审核
🔗 链接: {url}

💡 说明:
⏰ 请等待30分钟-2小时以获取新链接
🔄 或使用其他账户创建新链接

🎯 注意: 
• SheerID正在审核您的信息
• 无需任何操作，只需等待
• 审核完成后将有新链接

💰 未扣除 xu/cash
📞 支持: @meepzizhere"""
                                }
                                message = pending_msgs.get(user_lang, pending_msgs['vi'])
                                
                                resp = requests.post(
                                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                    json={
                                        "chat_id": str(telegram_id),
                                        "text": message
                                    },
                                    timeout=15
                                )
                                if resp.status_code == 200:
                                    print(f"✅ Sent 'pending/reviewing' notification to user {telegram_id}")
                                else:
                                    print(f"❌ Failed to send pending notification: {resp.status_code} - {resp.text}")
                                
                                # Mark notification as sent
                                mark_notification_sent(job_id)
                                print(f"✅ Marked pending notification as sent for job {job_id}")
                except Exception as e:
                    print(f"❌ Error sending pending notification: {e}")
                
                # Mark job as processed to prevent duplicate processing by polling system
                mark_job_as_charged(job_id)
                print(f"✅ Marked job {job_id} as processed (pending case)")
                
                # Return with pending status
                return {
                    "success": False,
                    "message": "Link đang ở trạng thái Reviewing - cần chờ xử lý",
                    "status": "pending",
                    "stage": current_step,
                    "job_id": job_id,
                    "instruction": "Chờ 30p-2h để lấy link mới hoặc dùng tài khoản khác",
                    "student_info": {
                        "name": f"{first_name} {last_name}",
                        "first_name": first_name,
                        "last_name": last_name,
                        "birth_date": birth_date,
                        "student_id": "N/A"
                    }
                }
            
        # Check if student verification link is actually a teacher link (wrong command used)
        # IMPORTANT: Skip this check if this IS a ChatGPT Teacher verification (is_chatgpt_teacher=True)
        elif current_step.lower() == "collectteacherpersonalinfo" and not is_chatgpt_teacher:
            print(f"🎓 Student verification detected Teacher link: {verification_id}")
            
            # This is a teacher verification link but user used student command
            if job_id:
                try:
                    from .supabase_client import get_verification_job_by_id, update_verification_job_status
                    from .telegram import is_notification_already_sent, mark_notification_sent
                    
                    # Check if notification already sent to prevent duplicates
                    if not is_notification_already_sent(job_id):
                        # Get user info to send notification
                        job_info = get_verification_job_by_id(job_id)
                        if job_info:
                            telegram_id = job_info.get('telegram_id')
                            user_lang = job_info.get('language', 'vi')
                            if telegram_id:
                                bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                                if bot_token:
                                    # Multilingual message
                                    if user_lang == 'en':
                                        message = f"""⚠️ Wrong command!

🆔 Job ID: {job_id}

This is a ChatGPT Teacher verification link, not a Student link.

👉 Please use /vc command to verify ChatGPT Teacher

💰 No coins/cash deducted for this attempt."""
                                    elif user_lang == 'zh':
                                        message = f"""⚠️ 命令错误！

🆔 Job ID: {job_id}

这是 ChatGPT Teacher 验证链接，不是学生链接。

👉 请使用 /vc 命令来验证 ChatGPT Teacher

💰 本次尝试不扣除 xu/cash。"""
                                    else:  # Vietnamese default
                                        message = f"""⚠️ Sai lệnh!

🆔 Job ID: {job_id}

Đây là link verify ChatGPT Teacher, không phải link Student.

👉 Hãy sử dụng lệnh /vc để verify ChatGPT Teacher

💰 Không bị trừ xu/cash cho lần thử này."""
                                    
                                    resp = requests.post(
                                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                        json={
                                            "chat_id": str(telegram_id),
                                            "text": message
                                        },
                                        timeout=15
                                    )
                                    if resp.status_code == 200:
                                        print(f"✅ Sent 'wrong command' notification to user {telegram_id}")
                                    else:
                                        print(f"❌ Failed to send wrong command notification: {resp.status_code} - {resp.text}")
                        
                        # Mark notification as sent
                        mark_notification_sent(job_id)
                        print(f"✅ Marked wrong command notification as sent for job {job_id}")
                    
                    # Update job status to skipped (not failed, not charged)
                    update_verification_job_status(job_id, 'skipped')
                    print(f"✅ Updated job {job_id} status to skipped (wrong command)")
                    
                except Exception as e:
                    print(f"❌ Error handling wrong command case: {e}")
                
                # Mark job as processed to prevent duplicate processing
                mark_job_as_charged(job_id)
                print(f"✅ Marked job {job_id} as processed (wrong command - teacher link)")
            
            return {
                "success": False,
                "message": "Sai lệnh, hãy sử dụng lệnh /vc để verify ChatGPT Teacher",
                "status": "skipped",
                "stage": current_step,
                "job_id": job_id,
                "reason": "wrong_command",
                "instruction": "Sử dụng /vc để verify ChatGPT Teacher",
                "student_info": {
                    "name": f"{first_name} {last_name}",
                    "first_name": first_name,
                    "last_name": last_name,
                    "birth_date": birth_date,
                    "student_id": "N/A"
                }
            }
        
        # Continue with normal verification flow for other currentStep values
        print(f"🔄 DEBUG: Continuing with normal flow for currentStep: {current_step}")
        
        # Prioritize the correct step based on verification type
        if is_chatgpt_teacher:
            print("🎓 DEBUG: Using collectTeacherPersonalInfo for ChatGPT Teacher")
            api_urls = [
                f"https://services.sheerid.com/rest/v2/verification/{verification_id}/step/collectTeacherPersonalInfo",
                f"https://my.sheerid.com/rest/v2/verification/{verification_id}/step/collectTeacherPersonalInfo"
            ]
        elif current_step == "collectStudentPersonalInfo":
            print("DEBUG: Prioritizing collectStudentPersonalInfo based on currentStep")
            api_urls = [
                f"https://services.sheerid.com/rest/v2/verification/{verification_id}/step/collectStudentPersonalInfo",
                f"https://my.sheerid.com/rest/v2/verification/{verification_id}/step/collectStudentPersonalInfo",
                f"https://services.sheerid.com/rest/v2/verification/{verification_id}/step/collectPersonalInfo",
                f"https://my.sheerid.com/rest/v2/verification/{verification_id}/step/collectPersonalInfo"
            ]
        else:
            print("DEBUG: Using default order (collectPersonalInfo first)")
            api_urls = [
                f"https://services.sheerid.com/rest/v2/verification/{verification_id}/step/collectPersonalInfo",
                f"https://services.sheerid.com/rest/v2/verification/{verification_id}/step/collectStudentPersonalInfo",
                f"https://my.sheerid.com/rest/v2/verification/{verification_id}/step/collectPersonalInfo",
                f"https://my.sheerid.com/rest/v2/verification/{verification_id}/step/collectStudentPersonalInfo"
            ]
        
        # Only do POST if not already at docUpload
        if current_step != "docupload" and current_step != "docUpload":
            print(f"DEBUG: API URLs to try: {api_urls}")
            
            # Generate latest Chrome version headers for higher success rate
            chrome_version = random.choice(['131', '132', '133'])
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36',
                'Origin': 'https://services.sheerid.com',
                'Referer': url,
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Ch-Ua': f'"Google Chrome";v="{chrome_version}", "Chromium";v="{chrome_version}", "Not_A Brand";v="24"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            try:
                response = None
                api_url = None
                for url_candidate in api_urls:
                    try:
                        # Anti-detection: Random delay before main POST (1-3s) - simulates form filling time
                        if not fast_mode:
                            post_delay = random.uniform(1.0, 3.0)
                            print(f"⏳ Anti-detection: Pre-POST delay {post_delay:.1f}s")
                            time.sleep(post_delay)
                        else:
                            print(f"⚡ FAST MODE: Skipping pre-POST delay")
                        
                        print(f"📤 DEBUG: Trying POST to: {url_candidate}")
                        print(f"📦 DEBUG: Payload: {api_payload}")
                        _post_start = _t.time()
                        response = make_request('post', url_candidate, json=api_payload, headers=headers, timeout=30, use_scrape_proxy=use_scrape_proxy, session_id=proxy_session_id, country='us')
                        print(f"⏱️ POST took {_t.time()-_post_start:.2f}s")
                        print(f"📊 DEBUG: Response Status: {response.status_code}")
                        print(f"📄 DEBUG: Response Text: {response.text[:500]}")
                        if response.status_code == 200:
                            api_url = url_candidate
                            print(f"✅ Success with URL: {url_candidate}")
                            steps.append({"t":"post","msg":f"Submitted personal info → 200 at {url_candidate}"})
                            break
                        else:
                            print(f"❌ Failed with URL: {url_candidate} - Status: {response.status_code}")
                            steps.append({"t":"post","msg":f"Failed {response.status_code} at {url_candidate}"})
                    except Exception as e:
                        print(f"❌ Exception with URL {url_candidate}: {e}")
                        steps.append({"t":"post","msg":f"Exception {str(e)} at {url_candidate}"})
                        continue

                if not response or response.status_code != 200:
                    return {"success": False, "error": f"All API endpoints failed. Last response: {response.status_code if response else 'No response'}", "debug_info": {"steps": steps}}
            except Exception as e:
                print(f"❌ General exception in POST loop: {e}")
                steps.append({"t":"post_error","msg":f"General POST error: {str(e)}"})
                return {"success": False, "error": f"General POST error: {str(e)}", "debug_info": {"steps": steps}}

            if not response or response.status_code != 200:
                # Even if POST fails, continue with upload if we have the data
                print(f"⚠️ POST failed but continuing with upload - Status: {response.status_code if response else 'No response'}")
                steps.append({"t":"post_failed","msg":f"POST failed but continuing: {response.status_code if response else 'No response'}"})
                # Set default response_data for upload
                response_data = {"currentStep": "docUpload"}
                # Force can_upload_doc to True
                can_upload_doc = True
                steps.append({"t":"force_upload_after_fail","msg":"Forcing upload after POST failure"})

            
        # Try to parse response as JSON for better debugging
            try:
                response_json = response.json() if response is not None and getattr(response, 'content', None) else {}
                # Normalize response_data for next steps
                if response_json is None or not isinstance(response_json, dict):
                    response_data = {"currentStep": "docUpload"}
                else:
                    response_data = response_json
            except json.JSONDecodeError as e:
                print(f"Response is not valid JSON: {e}")
                print(f"Response text (first 200 chars): {response.text[:200]}")
                steps.append({"t":"json_error","msg":f"JSON parse error: {str(e)[:100]}"})
            except Exception as e:
                print(f"Unexpected error parsing JSON: {e}")
                steps.append({"t":"json_error","msg":f"Unexpected JSON error: {str(e)[:100]}"})
            
            if response and response.status_code == 200:
                try:
                    response_data = response.json() if response.content else {}
                except json.JSONDecodeError as e:
                    print(f"Failed to parse response JSON: {e}")
                    print(f"Response text: {response.text[:500]}")
                    steps.append({"t":"json_error","msg":f"Failed to parse response JSON: {str(e)[:100]}"})
                    # Continue with upload even if JSON parse fails
                    response_data = {"currentStep": "docUpload"}
                except Exception as e:
                    print(f"Unexpected error parsing response: {e}")
                    steps.append({"t":"json_error","msg":f"Unexpected response error: {str(e)[:100]}"})
                    # Continue with upload even if parse fails
                    response_data = {"currentStep": "docUpload"}
            else:
                # If no response or failed, set default for upload
                response_data = {"currentStep": "docUpload"}
            
            # ===== FRAUD DETECTION CHECK =====
            # Check for fraud rejection BEFORE attempting transcript generation
            if response_data and isinstance(response_data, dict):
                error_ids = response_data.get('errorIds', [])
                current_step_check = (response_data.get('currentStep') or '').lower()
                segment = response_data.get('segment', '').lower()  # 'teacher' or 'student'
                
                if current_step_check == 'error' or 'fraudRulesReject' in error_ids:
                    error_detail = response_data.get('errorDetailId', 'unknown')
                    system_error = response_data.get('systemErrorMessage', 'No details')
                    verification_type_str = "Teacher" if segment == 'teacher' or is_chatgpt_teacher else "Student"
                    print(f"🚫 FRAUD DETECTION ({verification_type_str}): Request rejected by SheerID")
                    print(f"   Segment: {segment}")
                    print(f"   Error IDs: {error_ids}")
                    print(f"   Error Detail: {error_detail}")
                    print(f"   System Message: {system_error}")
                    print(f"   IP Used: {host_ip}")
                    steps.append({"t":"fraud_reject","msg":f"Fraud detection ({verification_type_str}): {error_ids}"})
                    
                    # ===== BLACKLIST FRAUD IP =====
                    # Track this IP as causing fraud detection
                    # This helps avoid reusing "burned" IPs in future verifications
                    if host_ip and host_ip != "unknown":
                        blacklist_fraud_ip(host_ip, job_id)
                        print(f"🚫 IP {host_ip} added to fraud blacklist")
                    # ===== END BLACKLIST FRAUD IP =====)
                    
                    # Send fraud detection notification to user
                    if job_id:
                        try:
                            from .supabase_client import get_verification_job_by_id, update_verification_job_status
                            job_info = get_verification_job_by_id(job_id)
                            if job_info:
                                telegram_id = job_info.get('telegram_id')
                                user_lang = job_info.get('language', 'vi')
                                if telegram_id:
                                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                                    if bot_token:
                                        # Multilingual fraud detection messages
                                        vn_time = format_vietnam_time()
                                        # Detect verification type from segment or is_chatgpt_teacher
                                        is_teacher_verify = segment == 'teacher' or is_chatgpt_teacher
                                        type_vi = "Teacher" if is_teacher_verify else "Student"
                                        type_en = "Teacher" if is_teacher_verify else "Student"
                                        type_zh = "教师" if is_teacher_verify else "学生"
                                        
                                        fraud_msgs = {
                                            'vi': f"""🚫 PHÁT HIỆN GIAN LẬN ({type_vi})!

🆔 Job ID: {job_id}
📋 Loại: {type_vi} Verification
⏰ Thời gian: {vn_time}

🔄 Giải pháp:
• Tạo link mới từ tài khoản khác
• Hoặc bật VPN US rồi tạo link mới

💰 Không bị trừ xu/cash
📞 Hỗ trợ: @meepzizhere""",
                                            'en': f"""🚫 FRAUD DETECTION ({type_en})!

🆔 Job ID: {job_id}
📋 Type: {type_en} Verification
⏰ Time: {vn_time}

🔄 Solutions:
• Create a new link from another account
• Or turn on US VPN and create a new link

💰 No xu/cash deducted
📞 Support: @meepzizhere""",
                                            'zh': f"""🚫 检测到欺诈 ({type_zh})！

🆔 Job ID: {job_id}
📋 类型: {type_zh}验证
⏰ 时间: {vn_time}

🔄 解决方案:
• 从其他账户创建新链接
• 或开启美国VPN后创建新链接

💰 未扣除 xu/cash
📞 支持: @meepzizhere"""
                                        }
                                        fraud_msg = fraud_msgs.get(user_lang, fraud_msgs['vi'])
                                        
                                        import requests as req_lib
                                        resp = req_lib.post(
                                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                            json={"chat_id": str(telegram_id), "text": fraud_msg},
                                            timeout=15
                                        )
                                        if resp.status_code == 200:
                                            print(f"✅ Fraud detection notification sent to user {telegram_id}")
                                        else:
                                            print(f"❌ Failed to send fraud notification: {resp.status_code} - {resp.text}")
                            
                            # Update job status to fraud_reject
                            update_verification_job_status(job_id, 'fraud_reject')
                            print(f"✅ Updated job {job_id} status to fraud_reject (fraud detection)")
                        except Exception as e:
                            print(f"❌ Error sending fraud notification: {e}")
                    
                    # Return failure immediately - don't waste resources on transcript
                    is_teacher_verify = segment == 'teacher' or is_chatgpt_teacher
                    return {
                        "success": False, 
                        "error": "fraudRulesReject",
                        "error_detail": error_detail,
                        "system_message": system_error,
                        "segment": segment,
                        "verification_type": "teacher" if is_teacher_verify else "student",
                        "debug_info": {"steps": steps}
                    }
            # ===== END FRAUD DETECTION CHECK =====
            
            # Always force upload regardless of response
            can_upload_doc = True
            steps.append({"t":"force_upload_always","msg":"Always forcing upload regardless of response"})
        
        # Only set default response_data if we don't have a valid response
        if can_upload_doc and (not response_data or not isinstance(response_data, dict) or not response_data.get('currentStep')):
            response_data = {"currentStep": "docUpload"}
            
            # Check for next step in response
            status = "Form submitted successfully"
            if 'currentStep' in response_data:
                if response_data['currentStep'] == 'sso':
                    status = "SSO step reached - verification in progress"
                elif response_data['currentStep'] == 'complete':
                    status = "Verification completed"
            
            # Determine if we are allowed to upload documents now
            if response_data is None or not isinstance(response_data, dict):
                response_data = {}
            current_step = (response_data.get('currentStep') or '').lower()
            can_upload_doc = current_step in ("docupload", "document", "documentupload", "upload", "uploaddocs", "docs")
            steps.append({"t":"step","msg":f"currentStep={current_step}, canUpload={can_upload_doc}"})
            
            # Always force upload regardless of step
            can_upload_doc = True
            steps.append({"t":"force_upload_all","msg":"Forcing upload for all steps"})

        # Check if we need to handle SSO (only if currentStep is actually 'sso')
        # Skip SSO for ChatGPT Teacher - go straight to docUpload
        if response_data is None:
            response_data = {}
        current_step = (response_data.get('currentStep') or '').lower()
        print(f"🔍 DEBUG: Checking SSO - currentStep = '{current_step}'")
        
        if is_chatgpt_teacher and current_step == 'sso':
            print(f"🎓 DEBUG: Skipping SSO for ChatGPT Teacher - going straight to docUpload")
            steps.append({"t":"skip_sso","msg":"Skipping SSO for ChatGPT Teacher"})
            current_step = 'docupload'
            can_upload_doc = True
        elif current_step == 'sso':
            print(f"🔐 DEBUG: Handling SSO step for verification {verification_id}")
            steps.append({"t":"sso_handling","msg":"Handling SSO step"})
            
            # Always try SSO bypass regardless of can_upload_doc
            try:
                sso_url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}/step/sso"
                sso_headers = {
                    'Accept': 'application/json, text/plain, */*',
                    'User-Agent': headers['User-Agent'],
                    'Origin': 'https://services.sheerid.com',
                    'Referer': url,
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
                # Try POST with empty payload to bypass SSO - USE PROXY!
                resp_sso = make_request('post', sso_url, json={}, headers=sso_headers, timeout=30, 
                                       use_scrape_proxy=True, session_id=proxy_session_id, country='us')
                
                # Check if request returned None
                if resp_sso is None:
                    raise Exception("SSO POST request returned None - network/proxy error")
                
                steps.append({"t":"sso_post","msg":f"status={resp_sso.status_code}"})
                if resp_sso.status_code == 200:
                    try:
                        sso_json = resp_sso.json()
                        print(f"SSO POST response: {sso_json}")
                    except Exception:
                        sso_json = {}
                    response_data.update(sso_json)
                    current_step = (sso_json.get('currentStep') or current_step).lower()
                    can_upload_doc = current_step in ("docupload", "document", "documentupload", "upload", "uploaddocs", "docs")
                    steps.append({"t":"step","msg":f"after SSO post → currentStep={current_step}, canUpload={can_upload_doc}"})
                    print(f"✅ SSO POST successful - currentStep: {current_step}")
                else:
                    # If POST fails, try DELETE as fallback - USE PROXY!
                    resp_del = make_request('delete', sso_url, headers=sso_headers, timeout=30,
                                           use_scrape_proxy=True, session_id=proxy_session_id, country='us')
                    
                    # Check if request returned None
                    if resp_del is None:
                        raise Exception("SSO DELETE request returned None - network/proxy error")
                    
                    steps.append({"t":"sso_delete_fallback","msg":f"status={resp_del.status_code}"})
                    if resp_del.status_code == 200:
                        try:
                            sso_json = resp_del.json()
                            print(f"SSO DELETE response: {sso_json}")
                        except Exception:
                            sso_json = {}
                        response_data.update(sso_json)
                        current_step = (sso_json.get('currentStep') or current_step).lower()
                        can_upload_doc = current_step in ("docupload", "document", "documentupload", "upload", "uploaddocs", "docs")
                        steps.append({"t":"step","msg":f"after SSO delete fallback → currentStep={current_step}, canUpload={can_upload_doc}"})
                        print(f"✅ SSO DELETE successful - currentStep: {current_step}")
                        # FORCE: run generate/upload now and return
                        try:
                            can_upload_doc = True
                            steps.append({"t":"transcript_gen_start","msg":"start"})
                            
                            # Generate TRANSCRIPT instead of student card for SSO bypass
                            print(f"📄 DEBUG: Force generating TRANSCRIPT for {first_name} {last_name}")
                            
                            # Import transcript generator
                            try:
                                from .transcript_generator import generate_transcript_html, render_transcript_auto
                                from .universities_config import generate_student_id as gen_transcript_student_id
                            except ImportError:
                                from transcript_generator import generate_transcript_html, render_transcript_auto
                                from universities_config import generate_student_id as gen_transcript_student_id
                            
                            # Use selected_university for transcript
                            transcript_university = selected_university
                            transcript_student_id = gen_transcript_student_id(transcript_university)
                            
                            # Convert birth_date to readable format
                            try:
                                bd_parts = birth_date.split('-')
                                months = ["January", "February", "March", "April", "May", "June",
                                          "July", "August", "September", "October", "November", "December"]
                                dob_readable = f"{months[int(bd_parts[1])-1]} {int(bd_parts[2])}, {bd_parts[0]}"
                            except:
                                dob_readable = f"January 1, 2002"
                            
                            # Generate transcript HTML
                            html_content, transcript_info = generate_transcript_html(
                                university=transcript_university,
                                first_name=first_name,
                                last_name=last_name,
                                dob=dob_readable,
                                student_id=transcript_student_id
                            )
                            
                            print(f"📄 DEBUG: Transcript generated - Student ID: {transcript_info['student_id']}")
                            
                            # Render transcript to image
                            random_suffix_force = random.randint(100000, 999999)
                            clean_last_force = remove_vietnamese_accents(last_name).replace(' ', '')
                            clean_first_force = remove_vietnamese_accents(first_name).replace(' ', '')
                            card_filename_force = f"transcript_{clean_last_force}_{clean_first_force}_{random_suffix_force}.png"
                            save_path_force = os.path.join(TMP_DIR, card_filename_force)
                            
                            render_transcript_auto(html_content, transcript_info, save_path_force)
                            print(f"✅ DEBUG: Transcript rendered to {save_path_force}")
                            steps.append({"t":"transcript_saved","msg":save_path_force})
                            
                            # Upload transcript
                            print("DEBUG: doc_upload → starting")
                            steps.append({"t":"doc_upload","msg":"starting"})
                            upload_res = upload_transcript_to_sheerid(verification_id, save_path_force, session_id=proxy_session_id)
                            steps.append({"t":"doc_upload_result","msg":str(upload_res)[:200]})
                            # Complete
                            print("DEBUG: complete_doc → starting")
                            steps.append({"t":"complete_doc","msg":"starting"})
                            okf, compf = complete_doc_upload(verification_id, save_path_force)
                            steps.append({"t":"complete_doc_result","msg":f"ok={okf}"})
                            
                            # Poll status until success/failed or timeout
                            # Teacher: 60 attempts x 10s = 600s | Student: 30 attempts x 3s = 90s
                            try:
                                steps.append({"t":"poll_start","msg":"waiting for processing"})
                                if is_chatgpt_teacher:
                                    print("🎓 Teacher verification: Starting polling 60x10s (600s total)")
                                    polling_delay = 10.0
                                    polling_attempts = 60
                                else:
                                    polling_delay = 3.0
                                    polling_attempts = 120
                                    print(f"🎓 Student verification: Starting polling {polling_attempts}x{polling_delay}s ({polling_attempts * polling_delay}s total)")
                                
                                # Pass university info for fraud tracking (student only)
                                poll_university_id = str(university_id) if not is_chatgpt_teacher else None
                                poll_university_name = university if not is_chatgpt_teacher else None
                                
                                poll_ok, poll_data = wait_for_doc_processing(
                                    verification_id, 
                                    max_attempts=polling_attempts, 
                                    delay=polling_delay, 
                                    is_teacher=is_chatgpt_teacher, 
                                    session_id=proxy_session_id,
                                    university_id=poll_university_id,
                                    university_name=poll_university_name
                                )
                                steps.append({"t":"poll_result","msg":str(poll_ok)})
                                print(f"📊 Polling result: ok={poll_ok}, step={poll_data.get('currentStep') if poll_data else 'N/A'}")
                            except Exception as _pe:
                                print(f"⚠️ Polling error: {_pe}")
                                poll_ok, poll_data = False, {"error":"poll_exception"}
                            
                            # If successful, polling is complete - charging will be handled by the main endpoint
                            if poll_ok:
                                print("🎯 SUCCESS PATH: Polling completed successfully - charging will be handled by main endpoint")
                                
                                # Return success result for polling completion
                                return {
                                    "success": True,
                                    "status": "success",
                                    "message": "Card generated and uploaded successfully",
                                    "student_info": {
                                        "name": f"{first_name} {last_name}",
                                        "first_name": first_name,
                                        "last_name": last_name,
                                        "email": email,
                                        "birth_date": birth_date,
                                        "university": university,
                                        "country": country,
                                        "student_id": transcript_info.get('student_id', transcript_student_id)
                                    },
                                    "card_filename": card_filename_force,
                                    "upload_result": upload_res,
                                    "debug_info": {"steps": steps, "poll": poll_data}
                                }
                            else:
                                # Polling timeout - return fail immediately, don't retry upload
                                poll_step = poll_data.get('currentStep', 'unknown') if poll_data else 'unknown'
                                print(f"❌ FAIL PATH: Polling timeout - step={poll_step}, returning fail immediately")
                                steps.append({"t":"poll_timeout_fail","msg":f"Polling timeout at step {poll_step}"})
                                
                                return {
                                    "success": False,
                                    "status": "failed",
                                    "message": f"Verification timeout - still at {poll_step} after polling",
                                    "error": "polling_timeout",
                                    "reason": "timeout",
                                    "response_data": poll_data,
                                    "debug_info": {"steps": steps}
                                }
                        except Exception as force_error:
                            print(f"❌ Force path error: {force_error}")
                            import traceback
                            traceback.print_exc()
                            steps.append({"t":"force_error","msg":str(force_error)[:200]})

            except Exception as e:
                steps.append({"t":"sso_post","msg":f"exception {str(e)}"})
                print(f"❌ SSO handling error: {e}")
                
                # SSO bypass failed - check if we can still proceed
                if current_step == 'sso':
                    # Still at SSO step - cannot proceed with upload
                    print(f"❌ SSO bypass failed, still at SSO step - returning noVerification")
                    steps.append({"t":"sso_failed","msg":"SSO bypass failed, cannot proceed"})
                    return {
                        "success": False,
                        "status": "failed",
                        "message": "This link requires SSO login which cannot be bypassed",
                        "error": "noVerification",
                        "reason": "sso_required",
                        "response_data": response_data,
                        "debug_info": {"steps": steps}
                    }
                else:
                    # Moved to another step - can try upload
                    can_upload_doc = True
                    steps.append({"t":"force_upload","msg":"SSO exception but moved to different step"})
            
            # Check if we're at docUpload step after SSO processing
            if current_step in ("docupload", "document", "documentupload", "upload", "uploaddocs", "docs"):
                can_upload_doc = True
                steps.append({"t":"docupload_detected","msg":"Detected docUpload step - enabling upload"})
            else:
                # Other step - try upload anyway (SSO fail already handled above)
                can_upload_doc = True
                steps.append({"t":"force_upload_other","msg":f"At step {current_step}, trying upload anyway"})

        # At this point, if we can upload doc, generate transcript and upload it
        print(f"🚀 DEBUG: Starting transcript generation check - can_upload_doc = {can_upload_doc} (elapsed: {_t.time()-_verify_start:.2f}s)")
        try:
            print(f"🔍 DEBUG: can_upload_doc = {can_upload_doc}")
            print(f"🔍 DEBUG: response_data = {response_data}")
            
            # ===== DOUBLE-CHECK FRAUD DETECTION BEFORE TRANSCRIPT =====
            # Re-check for fraud rejection before wasting resources on transcript generation
            if response_data and isinstance(response_data, dict):
                error_ids_check = response_data.get('errorIds', [])
                current_step_recheck = (response_data.get('currentStep') or '').lower()
                
                if current_step_recheck == 'error' or 'fraudRulesReject' in error_ids_check:
                    print(f"🚫 FRAUD DETECTED (pre-transcript check): Skipping transcript generation")
                    print(f"   Error IDs: {error_ids_check}")
                    steps.append({"t":"fraud_skip_transcript","msg":f"Skipping transcript due to fraud: {error_ids_check}"})
                    can_upload_doc = False  # Disable upload
            # ===== END DOUBLE-CHECK =====
            
            if can_upload_doc:
                steps.append({"t":"transcript_gen_start","msg":"Generating transcript for Art Institute"})
                
                # Teacher verification uses og-teacher-paystub.js (Satori Edge Function)
                # IMPORTANT: Must pass same name + school that was sent to SheerID to avoid MISMATCH
                if is_chatgpt_teacher:
                    print(f"🎓 DEBUG: Generating Teacher Pay Stub - calling og-teacher-paystub directly")
                    steps.append({"t":"paystub_gen_start","msg":"Calling og-teacher-paystub Edge Function"})
                    
                    random_suffix = random.randint(100000, 999999)
                    card_filename = f"paystub_teacher_{random_suffix}.png"
                    save_path = os.path.join(TMP_DIR, card_filename)
                    
                    try:
                        import requests
                        from urllib.parse import urlencode
                        
                        # Call og-teacher-paystub with SAME name + school sent to SheerID
                        # selected_school is defined earlier in teacher flow (line ~2870)
                        base_url = os.getenv("PRODUCTION_URL", "https://sheerid-verify-pro.vercel.app")
                        
                        # Build params to match SheerID submission
                        paystub_params = {
                            "firstName": first_name,
                            "lastName": last_name,
                            "school_id": selected_school.get('id'),
                            "school_name": selected_school.get('name'),
                            "t": random.randint(1000, 9999)  # Cache buster
                        }
                        paystub_url = f"{base_url}/api/og-teacher-paystub?{urlencode(paystub_params)}"
                        
                        print(f"📄 Calling og-teacher-paystub: {paystub_url}")
                        print(f"📋 Paystub params: name={first_name} {last_name}, school={selected_school.get('name')}")
                        
                        # Add bypass header if configured
                        headers = {}
                        bypass_token = os.getenv("VERCEL_AUTOMATION_BYPASS_SECRET")
                        if bypass_token:
                            headers["x-vercel-protection-bypass"] = bypass_token
                        
                        response = requests.get(paystub_url, headers=headers, timeout=60)
                        
                        if response.status_code == 200:
                            with open(save_path, 'wb') as f:
                                f.write(response.content)
                            print(f"✅ Teacher pay stub generated: {save_path} ({len(response.content)} bytes)")
                        else:
                            raise Exception(f"og-teacher-paystub returned {response.status_code}")
                            
                    except Exception as e:
                        print(f"⚠️ og-teacher-paystub failed, falling back to Pillow: {e}")
                        steps.append({"t":"paystub_satori_fallback","msg":f"og-teacher-paystub failed: {e}, using Pillow"})
                        
                        # Fallback to Pillow-based paystub_generator
                        try:
                            from paystub_generator import generate_paystub_image
                        except ImportError:
                            import sys
                            api_dir = os.path.dirname(os.path.abspath(__file__))
                            if api_dir not in sys.path:
                                sys.path.insert(0, api_dir)
                            from paystub_generator import generate_paystub_image
                        
                        generate_paystub_image(first_name, last_name, save_path)
                        print(f"✅ Pay stub generated with Pillow fallback: {save_path}")
                    
                    if not os.path.exists(save_path):
                        steps.append({"t":"paystub_error","msg":"Failed to create pay stub"})
                        raise Exception("Failed to create teacher pay stub")
                    
                    print(f"✅ DEBUG: Pay stub saved at {save_path}")
                    steps.append({"t":"paystub_saved","msg":save_path})
                else:
                    # Student verification: Generate TRANSCRIPT instead of student card
                    print(f"📄 DEBUG: Generating TRANSCRIPT for {first_name} {last_name}")
                    print(f"🎓 DEBUG: University: {university} (ID: {university_id})")
                    
                    # Import transcript generator
                    try:
                        from .transcript_generator import generate_transcript_html, render_transcript_auto
                        from .universities_config import generate_student_id as gen_transcript_student_id
                    except ImportError:
                        from transcript_generator import generate_transcript_html, render_transcript_auto
                        from universities_config import generate_student_id as gen_transcript_student_id
                    
                    # IMPORTANT: Use selected_university directly (same as SheerID API)
                    # This ensures transcript info matches what was sent to SheerID
                    transcript_university = selected_university
                    
                    # Generate transcript student ID using same university
                    transcript_student_id = gen_transcript_student_id(transcript_university)
                    
                    # Convert birth_date to readable format for transcript
                    # IMPORTANT: Use same birth_date as sent to SheerID API
                    try:
                        bd_parts = birth_date.split('-')
                        months = ["January", "February", "March", "April", "May", "June",
                                  "July", "August", "September", "October", "November", "December"]
                        dob_readable = f"{months[int(bd_parts[1])-1]} {int(bd_parts[2])}, {bd_parts[0]}"
                    except:
                        dob_readable = f"January 1, 2002"  # Fallback
                    
                    # Generate transcript HTML with SAME info as SheerID API
                    # first_name, last_name, birth_date all match what was sent to SheerID
                    print(f"📄 DEBUG: Creating transcript with SAME info as SheerID API:")
                    print(f"   - Name: {first_name} {last_name}")
                    print(f"   - DOB: {dob_readable} (from {birth_date})")
                    print(f"   - University: {transcript_university['name']} (ID: {transcript_university['id']})")
                    
                    html_content, transcript_info = generate_transcript_html(
                        university=transcript_university,
                        first_name=first_name,
                        last_name=last_name,
                        dob=dob_readable,
                        student_id=transcript_student_id
                    )
                    
                    print(f"📄 DEBUG: Transcript generated - Student ID: {transcript_info['student_id']}")
                    print(f"📄 DEBUG: Program: {transcript_info['program']}")
                    print(f"📄 DEBUG: GPA: {transcript_info['gpa']}")
                    
                    # Render transcript to image (auto-fallback to Pillow on Vercel)
                    random_suffix = random.randint(100000, 999999)
                    card_filename = f"transcript_{last_name}_{first_name}_{random_suffix}.png"
                    save_path = os.path.join(TMP_DIR, card_filename)
                    
                    # Use render_transcript_auto which handles Playwright->Pillow fallback
                    render_transcript_auto(html_content, transcript_info, save_path)
                    print(f"✅ DEBUG: Transcript rendered to {save_path}")
                    
                    steps.append({"t":"transcript_saved","msg":save_path})
                    student_id = transcript_info['student_id']

                # Upload metadata and file
                doc_type = "teacher card" if is_chatgpt_teacher else "transcript"
                steps.append({"t":"doc_upload","msg":f"Uploading {doc_type} to SheerID"})
                print(f"📤 DEBUG: Starting upload to SheerID - verification_id: {verification_id}")
                print(f"📁 DEBUG: File path: {save_path}")
                
                # Use appropriate upload function based on file type
                if save_path.endswith('.png'):
                    upload_result = upload_transcript_to_sheerid(verification_id, save_path, is_teacher=False, session_id=proxy_session_id)
                else:
                    upload_result = upload_student_card_to_sheerid(verification_id, save_path, is_teacher=is_chatgpt_teacher, session_id=proxy_session_id)
                print(f"📤 DEBUG: Upload result: {upload_result}")
                steps.append({"t":"doc_upload_result","msg":str(upload_result)[:200]})

                # Complete upload
                print(f"🏁 DEBUG: Starting complete_doc_upload")
                ok, comp = complete_doc_upload(verification_id, save_path, is_teacher=is_chatgpt_teacher, session_id=proxy_session_id)
                print(f"🏁 DEBUG: Complete upload result - ok: {ok}, comp: {comp}")
                steps.append({"t":"complete_doc","msg":f"ok={ok}"})
                try:
                    comp_step = (comp or {}).get('currentStep')
                    if comp_step and comp_step.lower() == 'pending':
                        # Continue to polling to see if it resolves; do not return immediately
                        pass
                    elif comp_step and comp_step.lower() in ('success','complete','verified'):
                        # Immediately approved by SheerID - charging will be handled by main endpoint
                        print("🎯 IMMEDIATE SUCCESS PATH: Immediate approval detected - charging will be handled by main endpoint")

                except Exception:
                    pass
                # For Teacher: Poll 60 times x 10 seconds (600s total) - longer intervals for review
                if is_chatgpt_teacher:
                    print("🎓 Teacher verification: Starting polling 60x10s (600s total)")
                    try:
                        import time as _time
                        steps.append({"t":"teacher_poll","msg":"start"})
                        # Teacher: 10s x 60 attempts (600s total) - longer intervals for review
                        polling_delay = 10.0
                        polling_attempts = 60
                        print(f"⏱️ Teacher polling: {polling_attempts} attempts x {polling_delay}s = {polling_attempts * polling_delay}s total")
                        poll_ok_once, poll_data_once = wait_for_doc_processing(
                            verification_id, 
                            max_attempts=polling_attempts, 
                            delay=polling_delay, 
                            is_teacher=True, 
                            session_id=proxy_session_id
                        )
                        steps.append({"t":"teacher_poll_result","msg":str(poll_ok_once)})
                        print(f"🎓 Teacher polling result: ok={poll_ok_once}, step={poll_data_once.get('currentStep') if poll_data_once else 'N/A'}")
                    except Exception as poll_err:
                        print(f"⚠️ Teacher polling error: {poll_err}")
                        poll_ok_once = False
                        poll_data_once = {}
                else:
                    # For Student: Poll immediately - FAST_MODE skips pre-poll wait entirely
                    try:
                        import time as _time
                        # Poll immediately (no pre-poll wait)
                        print(f"⚡ Polling immediately (no pre-poll wait)")
                        steps.append({"t":"poll_once","msg":"start"})
                        # Student: 3s x 120 attempts (360s total)
                        polling_delay = 3.0
                        polling_attempts = 120
                        
                        # Pass university info for fraud tracking (student only)
                        poll_ok_once, poll_data_once = wait_for_doc_processing(
                            verification_id, 
                            max_attempts=polling_attempts, 
                            delay=polling_delay, 
                            is_teacher=False, 
                            session_id=proxy_session_id,
                            university_id=str(university_id),
                            university_name=university
                        )
                        steps.append({"t":"poll_once_result","msg":str(poll_ok_once)})
                    except Exception:
                        pass
                # If polling ultimately failed or remained pending, return failure to user
                if not poll_ok_once:
                    # Determine appropriate Vietnamese message based on the step
                    poll_step = (poll_data_once or {}).get('currentStep', '').lower() if poll_data_once else ''
                    poll_reason = (poll_data_once or {}).get('reason', '') if poll_data_once else ''
                    
                    if poll_step == 'pending' or poll_reason == 'timeout':
                        error_message = "Quá thời gian verify, vui lòng thử lại"
                    elif poll_step in ('docupload', 'document', 'documentupload', 'upload'):
                        error_message = "Link của bạn đang ở bước upload proof, vui lòng vào link gửi ảnh bậy bạ gì đó 3 lần để về form lấy link SheerID mới"
                    else:
                        error_message = "Xác minh thất bại. Vui lòng thử lại sau"
                    
                    # Update job status to failed and send notification
                    if job_id:
                        try:
                            from .supabase_client import update_verification_job_status
                            update_verification_job_status(job_id, 'failed')
                            print(f"✅ Updated job {job_id} status to failed")
                            
                            # Send failure notification
                            send_failure_notification_for_job(job_id, error_message)
                        except Exception as e:
                            print(f"❌ Error updating job status: {e}")
                    
                    return {
                        "success": False,
                        "status": "failed",
                        "message": error_message,
                        "error": error_message,
                        "reason": poll_reason or (poll_data_once or {}).get('status') or 'timeout',
                        "response_data": poll_data_once,
                        "card_filename": card_filename,
                        "card_url": f"/student-card/{card_filename}",
                        "upload_result": upload_result,
                        "debug_info": {"steps": steps}
                    }
                
                # If poll says success, pass through as approved; otherwise default to pending                                                                  
                try:
                    final_step = str((poll_data_once or {}).get('currentStep', '')).lower()                                                                     
                    if final_step in ('success','complete','verified'):
                        print(f"✅ Verification SUCCESS! is_teacher={is_chatgpt_teacher}, job_id={job_id}")
                        
                        # Send success notification to Telegram
                        if job_id:
                            try:
                                from .supabase_client import update_verification_job_status, get_verification_job_by_id
                                
                                # Update job status to completed with university info
                                update_verification_job_status(job_id, 'completed', university=university)
                                # Notification đã được gửi ở chỗ khác rồi, không cần gửi lại
                            except Exception as notif_err:
                                pass
                        
                        return {
                            "success": True,
                            "status": "approved",
                            "message": "Verification approved",
                            "student_info": {
                                "name": f"{first_name} {last_name}",
                                "first_name": first_name,
                                "last_name": last_name,
                                "email": email,
                                "birth_date": birth_date,
                                "university": university,
                                "country": country,
                                "student_id": student_id
                            },
                            "card_filename": card_filename,
                            "card_url": f"/student-card/{card_filename}",       
                            "upload_result": upload_result,
                            "response_data": poll_data_once,
                            "debug_info": {"steps": steps}
                        }
                except Exception as success_err:
                    print(f"⚠️ Error in success handling: {success_err}")
                

        except Exception as e:
            print(f"❌ CARD FLOW ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            steps.append({"t":"fatal","msg":f"Card flow error: {str(e)[:200]}"})

        # Guard: ensure response_data is dict before any subsequent .get usage
        if response_data is None or not isinstance(response_data, dict):
            response_data = {}

            # Generate student ID for card: 8 random digits
            student_id = f"{random.randint(10000000, 99999999)}"
            
            # Tạo thông tin sinh viên cho thẻ
            # Use full_name if available, otherwise fallback to last_name + first_name
            card_name = full_name if 'full_name' in dir() and full_name else f"{last_name} {first_name}"
            student_card_info = {
                'name': card_name,
                'first_name': first_name,
                'last_name': last_name,
                'birth_date': birth_date.replace('-', '.'),
                'student_id': student_id
            }
            
            # Tạo thẻ sinh viên
            avatar_path = get_random_avatar()
            steps.append({"t":"avatar","msg":f"Avatar → {avatar_path}"})
            card = create_student_card(student_card_info, avatar_path)
            
            card_filename = None
            upload_result = None
            if card:
                # Lưu thẻ với tên file vào /tmp để phù hợp serverless
                # Generate filename with lastname_firstname_6digits format (remove spaces)
                random_suffix = random.randint(100000, 999999)
                clean_last = remove_vietnamese_accents(last_name).replace(' ', '')
                clean_first = remove_vietnamese_accents(first_name).replace(' ', '')
                card_filename = f"{clean_last}_{clean_first}_{random_suffix}.jpg"
                save_path = os.path.join(TMP_DIR, card_filename)
                # JPEG không hỗ trợ alpha; chuyển sang RGB trước khi lưu
                card_to_save = card.convert('RGB') if card.mode in ('RGBA', 'LA') else card
                card_to_save.save(save_path, 'JPEG')
                print(f"Student card created: {save_path}")
                steps.append({"t":"card","msg":f"Card saved {save_path}"})

                # Always try to upload document after creating card
                try:
                    print(f"📤 DEBUG: Starting card upload for verification {verification_id}")
                    upload_result = upload_student_card_to_sheerid(verification_id, save_path)
                    steps.append({"t":"upload","msg":str(upload_result)[:200]})
                    ok, comp = complete_doc_upload(verification_id, save_path)
                    
                    if ok and comp and isinstance(comp, dict):
                        # Check if completeDocUpload returned success (currentStep != "pending")
                        current_step_after_complete = comp.get("currentStep", "").lower()
                        print(f"Current step after completeDocUpload: {current_step_after_complete}")
                        steps.append({"t":"complete_step","msg":f"After complete: {current_step_after_complete}"})
                        
                        # Only treat as success if currentStep is actually success/complete
                        if current_step_after_complete in ["success", "complete", "verified"]:
                            response_data.update({"completeDocUpload": comp})
                            status = "completed"
                            print(f"✅ Job {job_id} completed successfully!")
                            steps.append({"t":"complete_success","msg":f"completeDocUpload returned {current_step_after_complete} - success"})
                            
                            # Job completed successfully - return success immediately
                            print(f"🎉 Job {job_id} completed successfully! Returning success to user.")
                        elif current_step_after_complete == "pending":
                            print("⏳ completeDocUpload returned pending - job is still under review")
                            steps.append({"t":"complete_pending","msg":"completeDocUpload returned pending - still under review"})
                            status = "pending"
                            
                            # Return pending status, don't charge user
                            return {
                                "success": False,
                                "status": "pending",
                                "message": "Link đang ở trạng thái Reviewing - cần chờ xử lý",
                                "student_info": {
                                    "name": f"{first_name} {last_name}",
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "email": email,
                                    "birth_date": birth_date,
                                    "university": university,
                                    "country": country,
                                    "student_id": student_id
                                },
                                "card_filename": card_filename,
                                "card_url": f"/student-card/{card_filename}",
                                "upload_result": upload_result,
                                "response_data": comp,
                                "debug_info": {"steps": steps}
                            }
                        else:
                            print(f"❌ completeDocUpload returned unexpected step: {current_step_after_complete}")
                            status = "failed"
                            
                            # Return failure status
                            return {
                                "success": False,
                                "status": "failed", 
                                "message": f"Verification failed at step: {current_step_after_complete}",
                                "student_info": {
                                    "name": f"{first_name} {last_name}",
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "email": email,
                                    "birth_date": birth_date,
                                    "university": university,
                                    "country": country,
                                    "student_id": student_id
                                },
                                "card_filename": card_filename,
                                "card_url": f"/student-card/{card_filename}",
                                "upload_result": upload_result,
                                "response_data": comp,
                                "debug_info": {"steps": steps}
                            }
                        
                        # Only process success if currentStep is actually success/complete
                        # This code should only run for the success path above
                        if current_step_after_complete in ["success", "complete", "verified"]:
                            print("🎯 DEBUG: Starting success processing - deducting coins and sending notification")
                            try:
                                import sys
                                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                                from .supabase_client import get_user_by_telegram_id, update_user_coins, get_verification_job_by_id, update_verification_job_status
                                
                                # Get job info from Supabase
                                job_info = get_verification_job_by_id(job_id)
                                if job_info:
                                    telegram_id = job_info.get('telegram_id')
                                    if not telegram_id:
                                        # Try to get from user_id if telegram_id not directly available
                                        user_id = job_info.get('user_id')
                                        if user_id:
                                            user = get_user_by_telegram_id(user_id)
                                            if user:
                                                telegram_id = user.get('telegram_id')
                                    
                                    # Update job status to completed with all data
                                    from datetime import datetime
                                    
                                    # Create student info from generated data
                                    student_info = {
                                        "first_name": first_name,
                                        "last_name": last_name,
                                        "email": email,
                                        "birth_date": birth_date,
                                        "university": university,
                                        "country": country
                                    }
                                    
                                    # Get card filename from upload result
                                    card_filename = upload_result.get('response_data', {}).get('documents', [{}])[0].get('documentId', '') if upload_result else ''
                                    
                                    result_data = {
                                        "student_info": student_info,
                                        "card_filename": card_filename,
                                        "upload_result": upload_result,
                                        "completeDocUpload": comp,
                                        "verification_id": verification_id,
                                        "completed_at": datetime.now().isoformat()
                                    }
                                    update_verification_job_status(
                                        job_id, 
                                        'completed',
                                        result_data=result_data
                                    )
                            except ImportError:
                                print("❌ Supabase client not available, but job completed successfully")
                            except Exception as e:
                                print(f"❌ Database update failed but job completed: {e}")
                        else:
                            print(f"⚠️ Skipping success processing - currentStep is '{current_step_after_complete}', not success")
                    elif ok and comp is None:
                        print("❌ completeDocUpload returned None - treating as fail")
                        steps.append({"t":"complete_fail","msg":"completeDocUpload returned None - fail"})
                        status = "failed"
                        success = False
                        
                        # Send failure notification to user via Telegram
                        try:
                            if job_id:
                                from .supabase_client import get_supabase_client, get_verification_job_by_id
                                supabase = get_supabase_client()
                                if supabase:
                                    job_data = get_verification_job_by_id(job_id)
                                    if job_data and job_data.get('user_id'):
                                        user_data = supabase.table('users').select('telegram_id, first_name, language').eq('id', job_data['user_id']).execute()
                                        if user_data.data:
                                            telegram_id = user_data.data[0].get('telegram_id')
                                            first_name = user_data.data[0].get('first_name', 'User')
                                            user_lang = user_data.data[0].get('language', 'vi')
                                            
                                            if telegram_id:
                                                bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                                                if bot_token:
                                                    current_time = format_vietnam_time()
                                                    fail_msgs = {
                                                        'vi': f"""❌ VERIFY THẤT BẠI!

👤 Chào {first_name}!
🆔 Job ID: {job_id}
❌ Trạng thái: Thất bại
⏰ Thời gian: {current_time}

🔄 Lý do: Không thể hoàn thành upload document
💡 Vui lòng thử lại sau hoặc liên hệ hỗ trợ

💰 Không bị trừ xu/cash
📞 Hỗ trợ: @meepzizhere""",
                                                        'en': f"""❌ VERIFICATION FAILED!

👤 Hello {first_name}!
🆔 Job ID: {job_id}
❌ Status: Failed
⏰ Time: {current_time}

🔄 Reason: Unable to complete document upload
💡 Please try again later or contact support

💰 No xu/cash deducted
📞 Support: @meepzizhere""",
                                                        'zh': f"""❌ 验证失败！

👤 你好 {first_name}！
🆔 Job ID: {job_id}
❌ 状态: 失败
⏰ 时间: {current_time}

🔄 原因: 无法完成文档上传
💡 请稍后重试或联系支持

💰 未扣除 xu/cash
📞 支持: @meepzizhere"""
                                                    }
                                                    failure_message = fail_msgs.get(user_lang, fail_msgs['vi'])
                                                    
                                                    # Send as plain text to avoid Markdown errors
                                                    resp = requests.post(
                                                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                                        json={
                                                            "chat_id": str(telegram_id),
                                                            "text": failure_message
                                                        },
                                                        timeout=15
                                                    )
                                                    if resp.status_code == 200:
                                                        print(f"✅ Failure notification sent to user {telegram_id}")
                                                    else:
                                                        print(f"❌ Failed to send notification: {resp.status_code} - {resp.text}")
                        except Exception as e:
                            print(f"❌ Error sending failure notification: {e}")
                            
                    elif ok and not isinstance(comp, dict):
                        print(f"❌ completeDocUpload returned invalid data type: {type(comp)} - treating as fail")
                        steps.append({"t":"complete_fail","msg":f"completeDocUpload returned invalid type: {type(comp)} - fail"})
                        status = "failed"
                        success = False
                        
                        # Send failure notification to user via Telegram
                        try:
                            if job_id:
                                from .supabase_client import get_supabase_client, get_verification_job_by_id
                                supabase = get_supabase_client()
                                if supabase:
                                    job_data = get_verification_job_by_id(job_id)
                                    if job_data and job_data.get('user_id'):
                                        user_data = supabase.table('users').select('telegram_id, first_name, language').eq('id', job_data['user_id']).execute()
                                        if user_data.data:
                                            telegram_id = user_data.data[0].get('telegram_id')
                                            first_name = user_data.data[0].get('first_name', 'User')
                                            user_lang = user_data.data[0].get('language', 'vi')
                                            
                                            if telegram_id:
                                                bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                                                if bot_token:
                                                    current_time = format_vietnam_time()
                                                    fail_msgs = {
                                                        'vi': f"""❌ VERIFY THẤT BẠI!

👤 Chào {first_name}!
🆔 Job ID: {job_id}
❌ Trạng thái: Thất bại
⏰ Thời gian: {current_time}

🔄 Lý do: Dữ liệu trả về không hợp lệ
💡 Vui lòng thử lại sau hoặc liên hệ hỗ trợ

💰 Không bị trừ xu/cash
📞 Hỗ trợ: @meepzizhere""",
                                                        'en': f"""❌ VERIFICATION FAILED!

👤 Hello {first_name}!
🆔 Job ID: {job_id}
❌ Status: Failed
⏰ Time: {current_time}

🔄 Reason: Invalid response data
💡 Please try again later or contact support

💰 No xu/cash deducted
📞 Support: @meepzizhere""",
                                                        'zh': f"""❌ 验证失败！

👤 你好 {first_name}！
🆔 Job ID: {job_id}
❌ 状态: 失败
⏰ 时间: {current_time}

🔄 原因: 返回数据无效
💡 请稍后重试或联系支持

💰 未扣除 xu/cash
📞 支持: @meepzizhere"""
                                                    }
                                                    failure_message = fail_msgs.get(user_lang, fail_msgs['vi'])
                                                    
                                                    # Send as plain text to avoid Markdown errors
                                                    resp = requests.post(
                                                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                                        json={
                                                            "chat_id": str(telegram_id),
                                                            "text": failure_message
                                                        },
                                                        timeout=15
                                                    )
                                                    if resp.status_code == 200:
                                                        print(f"✅ Failure notification sent to user {telegram_id}")
                                                    else:
                                                        print(f"❌ Failed to send notification: {resp.status_code} - {resp.text}")
                        except Exception as e:
                            print(f"❌ Error sending failure notification: {e}")
                            
                    else:
                        print("❌ Complete doc upload failed")
                        steps.append({"t":"complete","msg":"Complete failed"})
                        status = "failed"
                        success = False
                        
                        # Send failure notification to user via Telegram
                        try:
                            if job_id:
                                from .supabase_client import get_supabase_client, get_verification_job_by_id
                                supabase = get_supabase_client()
                                if supabase:
                                    job_data = get_verification_job_by_id(job_id)
                                    if job_data and job_data.get('user_id'):
                                        user_data = supabase.table('users').select('telegram_id, first_name, language').eq('id', job_data['user_id']).execute()
                                        if user_data.data:
                                            telegram_id = user_data.data[0].get('telegram_id')
                                            first_name = user_data.data[0].get('first_name', 'User')
                                            user_lang = user_data.data[0].get('language', 'vi')
                                            
                                            if telegram_id:
                                                bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                                                if bot_token:
                                                    current_time = format_vietnam_time()
                                                    fail_msgs = {
                                                        'vi': f"""❌ VERIFY THẤT BẠI!

👤 Chào {first_name}!
🆔 Job ID: {job_id}
❌ Trạng thái: Thất bại
⏰ Thời gian: {current_time}

🔄 Lý do: Không thể hoàn thành verification
💡 Vui lòng thử lại sau hoặc liên hệ hỗ trợ

💰 Không bị trừ xu/cash
📞 Hỗ trợ: @meepzizhere""",
                                                        'en': f"""❌ VERIFICATION FAILED!

👤 Hello {first_name}!
🆔 Job ID: {job_id}
❌ Status: Failed
⏰ Time: {current_time}

🔄 Reason: Unable to complete verification
💡 Please try again later or contact support

💰 No xu/cash deducted
📞 Support: @meepzizhere""",
                                                        'zh': f"""❌ 验证失败！

👤 你好 {first_name}！
🆔 Job ID: {job_id}
❌ 状态: 失败
⏰ 时间: {current_time}

🔄 原因: 无法完成验证
💡 请稍后重试或联系支持

💰 未扣除 xu/cash
📞 支持: @meepzizhere"""
                                                    }
                                                    failure_message = fail_msgs.get(user_lang, fail_msgs['vi'])
                                                    
                                                    # Send as plain text to avoid Markdown errors
                                                    resp = requests.post(
                                                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                                        json={
                                                            "chat_id": str(telegram_id),
                                                            "text": failure_message
                                                        },
                                                        timeout=15
                                                    )
                                                    if resp.status_code == 200:
                                                        print(f"✅ Failure notification sent to user {telegram_id}")
                                                    else:
                                                        print(f"❌ Failed to send notification: {resp.status_code} - {resp.text}")
                        except Exception as e:
                            print(f"❌ Error sending failure notification: {e}")
                except Exception as e:
                    print(f"Failed to upload card: {e}")
                    upload_result = {"success": False, "error": str(e)}
                    steps.append({"t":"upload","msg":f"exception {str(e)}"})
                    success = False
            
            # Determine overall success. Treat SheerID error step as failure
            overall_success = True
            error_message = None
            try:
                if response_data is None:
                    response_data = {}
                step_lower = (response_data.get("currentStep") or "").lower()
                if step_lower == "error":
                    overall_success = False
                    # Check for specific error types
                    error_ids = response_data.get("errorIds", [])
                    if "fraudRulesReject" in error_ids:
                        error_message = "Tài khoản của bạn đã xác minh quá nhiều và bị chặn. Vui lòng thử lại sau"
                    else:
                        error_message = "Xác minh thất bại. Vui lòng thử lại sau"
                elif step_lower == "docupload":
                    overall_success = False
                    error_message = "Link của bạn đang ở bước upload proof, vui lòng vào link gửi ảnh bậy bạ gì đó 3 lần để về form lấy link SheerID mới"
                elif step_lower == "pending":
                    overall_success = False
                    error_message = "Link verify của bạn đang bị Reviewing (Đang xem xét), vui lòng đợi 30p-2 tiếng để lấy link mới hoặc dùng tài khoản khác!"
            except Exception:
                pass
            
            # Ensure success is set correctly
            if 'success' not in locals():
                success = overall_success
            elif success is None:
                success = overall_success

            return {
                "success": success,
                "message": f"Verification completed successfully - {status}" if success else error_message,
                "error": error_message if not success else None,
                "student_info": {
                    "name": f"{first_name} {last_name}",
                    "email": email,
                    "birth_date": birth_date,
                    "university": university,
                    "student_id": student_id,
                    "first_name": first_name,
                    "last_name": last_name
                },
                "status": status,
                "response_data": response_data,
                # Bubble up error context (if any) so callers can map user-friendly messages
                "systemErrorMessage": response_data.get("systemErrorMessage") if response_data else None,
                "errorIds": response_data.get("errorIds") if response_data else [],
                "errorDetailId": response_data.get("errorDetailId") if response_data else None,
                "card_filename": card_filename,
                "avatar_path": avatar_path,
                "upload_result": upload_result,
                "stage": current_step,
                "can_upload_doc": can_upload_doc,
                "debug_info": {"steps": steps}
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"POST request failed: {str(e)}"
        }
    
    except Exception as e:
        print(f"❌ CRITICAL ERROR in _submit_sheerid_verification: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": f"Critical error: {str(e)}",
            "debug_info": {"steps": [{"t":"critical_error","msg":str(e)}]}
        }


@app.route('/fix-docupload', methods=['POST'])
def fix_docupload():
    """Fix stuck docUpload link by uploading blank images until error state"""
    try:
        payload = request.get_json(silent=True) or {}
        verification_id = payload.get('verification_id', '').strip()
        
        if not verification_id:
            return jsonify(success=False, error='Missing verification_id'), 400
        
        print(f"🔧 Starting fix-docupload for verification {verification_id}")
        
        # Create a simple blank image (1x1 white pixel PNG)
        import base64
        import io
        from PIL import Image
        
        # Create blank white image
        blank_img = Image.new('RGB', (100, 100), color='white')
        img_buffer = io.BytesIO()
        blank_img.save(img_buffer, format='JPEG', quality=50)
        img_buffer.seek(0)
        blank_image_data = img_buffer.read()
        
        max_attempts = 3
        attempts = 0
        final_status = 'unknown'
        
        for attempt in range(max_attempts):
            attempts += 1
            print(f"🔄 Fix attempt {attempts}/{max_attempts}")
            
            try:
                # Step 1: Check current status
                status_url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}"
                headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                status_resp = requests.get(status_url, headers=headers, timeout=30)
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    current_step = status_data.get('currentStep', '').lower()
                    print(f"📊 Current step: {current_step}")
                    
                    # If already in error state, we're done
                    if current_step in ['error', 'rejected', 'failed']:
                        final_status = current_step
                        print(f"✅ Link already in error state: {current_step}")
                        break
                    
                    # If not in docUpload, can't fix
                    if current_step not in ['docupload', 'pending', 'collectstudentpersonalinfo']:
                        final_status = current_step
                        print(f"⚠️ Link not in docUpload state: {current_step}")
                        break
                
                # Step 2: Upload blank image
                upload_url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}/step/docUpload"
                
                files = {
                    'file': ('blank.jpg', blank_image_data, 'image/jpeg')
                }
                
                upload_headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Origin': 'https://services.sheerid.com',
                    'Referer': f'https://services.sheerid.com/verify/{verification_id}'
                }
                
                upload_resp = requests.post(upload_url, files=files, headers=upload_headers, timeout=30)
                print(f"📤 Upload response: {upload_resp.status_code}")
                
                if upload_resp.status_code == 200:
                    upload_data = upload_resp.json()
                    new_step = upload_data.get('currentStep', '').lower()
                    print(f"📊 After upload step: {new_step}")
                    final_status = new_step
                    
                    # If reached error state, we're done
                    if new_step in ['error', 'rejected', 'failed']:
                        print(f"✅ Reached error state after {attempts} attempts")
                        break
                else:
                    print(f"❌ Upload failed: {upload_resp.status_code} - {upload_resp.text[:200]}")
                
                # Wait a bit before next attempt
                import time
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Error in attempt {attempts}: {e}")
                continue
        
        return jsonify(
            success=True,
            attempts=attempts,
            final_status=final_status,
            message=f"Completed {attempts} upload attempts, final status: {final_status}"
        )
        
    except Exception as e:
        print(f"❌ Error in fix-docupload: {e}")
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e)), 500


@app.route('/start-verification', methods=['POST'])
def start_verification():
    try:
        payload = request.get_json(silent=True) or {}
        url = (payload.get('url') or '').strip()
        job_id = payload.get('job_id')  # Telegram job ID or Seller job ID
        seller_id = payload.get('seller_id')  # Seller ID if from Seller API
        webhook_url = payload.get('webhook_url')  # Webhook URL for seller callback
        verification_type = payload.get('verification_type', 'sheerid')  # Default to sheerid
        from_queue = payload.get('from_queue', False)  # Flag to bypass queue check
        
        if not url:
            return jsonify(started=False, error='Thiếu URL'), 400

        # Log verification type
        if seller_id:
            print(f"🏪 Starting Seller verification for seller {seller_id}, job {job_id}")
        elif verification_type == 'chatgpt':
            print(f"🎓 Starting ChatGPT Teacher verification for job {job_id}")
        else:
            print(f"🔍 Starting SheerID verification for job {job_id}")

        # Queue system disabled - Vercel serverless doesn't maintain in-memory state
        # All verifications run immediately without queue
        # Note: If rate limiting needed, implement via database tracking instead
        
        import time as timing_module
        _start_time = timing_module.time()
        print(f"🚀 Job {job_id} starting verification at {_start_time}")

        # Submit verification via API and then upload doc
        try:
            # Add job_id and verification_type to payload for _submit_sheerid_verification
            payload['job_id'] = job_id
            payload['verification_type'] = verification_type
            result = _submit_sheerid_verification(payload)
            started_flag = bool(result.get("success"))
            
            # If this is a Telegram job, update the job status in Supabase
            if job_id:
                try:
                    import sys
                    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                    from .supabase_client import update_verification_job_status
                    
                    # Only treat as success if both success=True AND status is not pending/failed
                    result_success = result.get("success")
                    result_status = result.get("status", "").lower()
                    result_reason = result.get("reason", "").lower()
                    
                    # Check for success indicators (more flexible)
                    success_indicators = [
                        "approved", "completed", "success", "verified", 
                        "complete", "done", "finished"
                    ]
                    
                    # Check for failure indicators  
                    failure_indicators = [
                        "failed", "error", "rejected", "timeout", 
                        "pending_timeout", "cancelled"
                    ]
                    
                    # More flexible success detection
                    has_success_status = any(indicator in result_status for indicator in success_indicators)
                    has_failure_status = any(indicator in result_status for indicator in failure_indicators)
                    has_failure_reason = any(indicator in result_reason for indicator in failure_indicators)
                    
                    is_truly_successful = (
                        result_success and 
                        (has_success_status or result_status == "approved") and
                        not (has_failure_status or has_failure_reason)
                    )
                    
                    if is_truly_successful:
                        print(f"✅ Job {job_id} is truly successful - updating to completed")
                        
                        # Remove from student active jobs queue
                        try:
                            from .telegram import remove_student_from_active
                            remove_student_from_active(job_id)
                            print(f"🎓 Removed job {job_id} from student active queue")
                        except Exception as e:
                            print(f"⚠️ Failed to remove from student queue: {e}")
                        
                        # OPTIMIZED: Get job_info from update to avoid re-query in charging
                        update_result = update_verification_job_status(
                            job_id, 
                            'completed',
                            result.get("student_info"),
                            result.get("card_filename"),
                            result.get("upload_result"),
                            return_job_info=True
                        )
                        # Handle both old (bool) and new (tuple) return format
                        if isinstance(update_result, tuple):
                            success, cached_job_info = update_result
                        else:
                            success, cached_job_info = update_result, None
                        
                        if success:
                            print(f"✅ Updated job {job_id} status to completed in Supabase")
                            
                            # Process charging with cached job_info (saves 1 query)
                            print(f"💰 Processing charging for completed job {job_id}")
                            charging_success = process_completed_job_charging(job_id, cached_job_info=cached_job_info)
                            
                            if charging_success:
                                print(f"✅ Successfully charged job {job_id}")
                            else:
                                print(f"⚠️ Charging skipped for job {job_id} (already charged or VIP)")
                            
                            # Send webhook to seller if this is a seller job
                            if seller_id:
                                send_seller_webhook(seller_id, job_id, 'completed', {
                                    'verified': True,
                                    'student_info': result.get("student_info"),
                                    'card_image': result.get("card_filename")
                                })
                        else:
                            print(f"❌ Failed to update job {job_id} status in Supabase")
                    elif result_success and not has_failure_status and not has_failure_reason:
                        # Fallback: if success=True but status doesn't match expected values, still mark as completed
                        print(f"🔄 FALLBACK: Marking job {job_id} as completed (success=True, status='{result_status}')")
                        update_result = update_verification_job_status(
                            job_id, 
                            'completed',
                            result.get("student_info"),
                            result.get("card_filename"),
                            result.get("upload_result"),
                            return_job_info=True
                        )
                        if isinstance(update_result, tuple):
                            success, cached_job_info = update_result
                        else:
                            success, cached_job_info = update_result, None
                        
                        if success:
                            print(f"✅ FALLBACK: Job {job_id} updated to completed")
                            
                            # Process charging with cached job_info
                            charging_success = process_completed_job_charging(job_id, cached_job_info=cached_job_info)
                            
                            if not charging_success:
                                print(f"⚠️ FALLBACK: Charging skipped for job {job_id}")
                            
                            # Send webhook to seller if this is a seller job
                            if seller_id:
                                send_seller_webhook(seller_id, job_id, 'completed', {
                                    'verified': True,
                                    'student_info': result.get("student_info"),
                                    'card_image': result.get("card_filename")
                                })
                        else:
                            print(f"❌ FALLBACK: Failed to update job {job_id} status")
                    elif result_status in ["pending", "docUpload"]:
                        print(f"⏳ Job {job_id} is in intermediate state '{result_status}' - updating to pending")
                        success = update_verification_job_status(job_id, 'pending')
                        if success:
                            print(f"✅ Updated job {job_id} status to pending in Supabase")
                        else:
                            print(f"❌ Failed to update job {job_id} status to pending in Supabase")
                    elif result_status == "pending_background":
                        print(f"🔄 Job {job_id} is in background polling - updating to pending_background")
                        success = update_verification_job_status(job_id, 'pending_background')
                        if success:
                            print(f"✅ Updated job {job_id} status to pending_background in Supabase")
                            
                            # Send notification that verification is being processed
                            try:
                                from .supabase_client import get_verification_job_by_id
                                job_info = get_verification_job_by_id(job_id)
                                if job_info:
                                    telegram_id = job_info.get('telegram_id')
                                    user_lang = job_info.get('language', 'vi')
                                    if telegram_id:
                                        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                                        if bot_token:
                                            # Multilingual background processing messages
                                            bg_msgs = {
                                                'vi': f"""⏳ Verification đang xử lý

🆔 Job ID: {job_id}
⏳ Trạng thái: Đang xử lý trong background
⏰ Thời gian dự kiến: 3-5 phút

🔔 Bạn sẽ nhận thông báo khi có kết quả
💰 Xu/cash sẽ được trừ khi verification thành công

📞 Hỗ trợ: @meepzizhere""",
                                                'en': f"""⏳ Verification in progress

🆔 Job ID: {job_id}
⏳ Status: Processing in background
⏰ Estimated time: 3-5 minutes

🔔 You will receive a notification when results are ready
💰 Xu/cash will be deducted upon successful verification

📞 Support: @meepzizhere""",
                                                'zh': f"""⏳ 验证处理中

🆔 Job ID: {job_id}
⏳ 状态: 后台处理中
⏰ 预计时间: 3-5分钟

🔔 结果出来后您将收到通知
💰 验证成功后将扣除 xu/cash

📞 支持: @meepzizhere"""
                                            }
                                            message = bg_msgs.get(user_lang, bg_msgs['vi'])

                                            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                            data = {
                                                'chat_id': telegram_id,
                                                'text': message
                                            }
                                            resp = requests.post(url, data=data, timeout=30)
                                            if resp.status_code == 200:
                                                print(f"✅ Sent background processing notification to {telegram_id}")
                                            else:
                                                print(f"❌ Failed to send background notification: {resp.status_code} - {resp.text}")
                            except Exception as e:
                                print(f"❌ Failed to send background notification: {e}")
                        else:
                            print(f"❌ Failed to update job {job_id} status to pending_background in Supabase")
                    else:
                        # Check if job was already marked as completed - don't override
                        from .supabase_client import get_verification_job_by_id
                        current_job = get_verification_job_by_id(job_id)
                        if current_job and current_job.get('status') == 'completed':
                            print(f"✅ Job {job_id} already completed - not overriding with failed status")
                        # Check if this should skip fail count (link already failed before we tried)
                        elif result.get("skip_fail_count") or result.get("already_failed") or result.get("already_rejected") or result.get("already_pending"):
                            print(f"⏭️ Job {job_id} skipped - link was already in error/rejected/pending state, not counting as failed")
                            # Remove from queue but don't count as failed attempt
                            try:
                                from .telegram import remove_student_from_active
                                remove_student_from_active(job_id)
                            except Exception as e:
                                print(f"⚠️ Failed to remove from student queue: {e}")
                            # Update to 'skipped' status instead of 'failed'
                            update_verification_job_status(job_id, 'skipped')
                            # Send notification about invalid link
                            try:
                                job_info = get_verification_job_by_id(job_id)
                                print(f"📋 Job info for skip notification: {job_info}")
                                if job_info:
                                    telegram_id = job_info.get('telegram_id')
                                    user_lang = job_info.get('language', 'vi')
                                    print(f"📱 Telegram ID for skip notification: {telegram_id}")
                                    if telegram_id:
                                        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                                        if bot_token:
                                            error_msg = result.get("error", "Link không hợp lệ")
                                            # Multilingual invalid link messages
                                            invalid_msgs = {
                                                'vi': f"⚠️ LINK KHÔNG HỢP LỆ\n\n🆔 Job ID: {job_id}\n📝 Lý do: {error_msg}\n\n💡 Vui lòng gửi link mới để verify.\n💰 Không bị trừ xu/cash\n📞 Hỗ trợ: @meepzizhere",
                                                'en': f"⚠️ INVALID LINK\n\n🆔 Job ID: {job_id}\n📝 Reason: {error_msg}\n\n💡 Please send a new link to verify.\n💰 No xu/cash deducted\n📞 Support: @meepzizhere",
                                                'zh': f"⚠️ 链接无效\n\n🆔 Job ID: {job_id}\n📝 原因: {error_msg}\n\n💡 请发送新链接进行验证。\n💰 未扣除 xu/cash\n📞 支持: @meepzizhere"
                                            }
                                            msg = invalid_msgs.get(user_lang, invalid_msgs['vi'])
                                            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                            data = {"chat_id": telegram_id, "text": msg}
                                            resp = requests.post(url, data=data, timeout=30)
                                            print(f"📤 Skip notification sent: {resp.status_code} - {resp.text[:200]}")
                                        else:
                                            print(f"⚠️ No bot token for skip notification")
                                    else:
                                        print(f"⚠️ No telegram_id in job_info for skip notification")
                                else:
                                    print(f"⚠️ No job_info found for skip notification")
                            except Exception as e:
                                print(f"⚠️ Failed to send skip notification: {e}")
                        else:
                            # Check if this is a special status (docUpload, pending) that shouldn't be marked as failed
                            result_status = result.get("status", "")
                            if result_status in ["docUpload", "pending"]:
                                # Don't mark as failed, and don't send failure notification
                                print(f"✅ Job {job_id} has special status '{result_status}', not marking as failed")
                            else:
                                # Remove from student active jobs queue
                                try:
                                    from .telegram import remove_student_from_active
                                    remove_student_from_active(job_id)
                                    print(f"🎓 Removed failed job {job_id} from student active queue")
                                except Exception as e:
                                    print(f"⚠️ Failed to remove from student queue: {e}")
                                
                                success = update_verification_job_status(job_id, 'failed')
                                if success:
                                    print(f"✅ Updated job {job_id} status to failed in Supabase")
                                    
                                    # Send webhook to seller if this is a seller job
                                    if seller_id:
                                        error_msg = result.get("error") or result.get("message") or "Verification failed"
                                        send_seller_webhook(seller_id, job_id, 'failed', {
                                            'verified': False,
                                            'error': error_msg
                                        })
                                    
                                    # Send failure notification to user only if actually failed
                                    try:
                                        job_info = get_verification_job_by_id(job_id)
                                        if job_info:
                                            telegram_id = job_info.get('telegram_id')
                                            user_lang = job_info.get('language', 'vi')
                                            if telegram_id:
                                                bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                                                if bot_token:
                                                    # Get appropriate error message
                                                    error_message = result.get("error") or result.get("message") or "Xác minh thất bại"
                                                    current_time = format_vietnam_time()
                                                    
                                                    # Multilingual failure messages
                                                    fail_msgs = {
                                                        'vi': f"""❌ VERIFY THẤT BẠI!

🆔 Job ID: {job_id}
📝 Lý do: {error_message}
⏰ Thời gian: {current_time}

📖 Hướng dẫn: https://t.me/channel_sheerid_vip_bot/135

🔄 Nếu vẫn fail:
1️⃣ Mở link SheerID trên trình duyệt
2️⃣ Submit blank image 3 lần để lấy link mới
3️⃣ Quay lại bot verify với link mới

💰 Không bị trừ xu/cash
📞 Hỗ trợ: @meepzizhere""",
                                                        'en': f"""❌ VERIFICATION FAILED!

🆔 Job ID: {job_id}
📝 Reason: {error_message}
⏰ Time: {current_time}

📖 Guide: https://t.me/channel_sheerid_vip_bot/135

🔄 If still failing:
1️⃣ Open SheerID link in browser
2️⃣ Submit blank image 3 times to get new link
3️⃣ Return to bot and verify with new link

💰 No xu/cash deducted
📞 Support: @meepzizhere""",
                                                        'zh': f"""❌ 验证失败！

🆔 Job ID: {job_id}
📝 原因: {error_message}
⏰ 时间: {current_time}

📖 指南: https://t.me/channel_sheerid_vip_bot/135

🔄 如果仍然失败:
1️⃣ 在浏览器中打开SheerID链接
2️⃣ 提交空白图片3次以获取新链接
3️⃣ 返回机器人使用新链接验证

💰 未扣除 xu/cash
📞 支持: @meepzizhere"""
                                                    }
                                                    text_message = fail_msgs.get(user_lang, fail_msgs['vi'])
                                                    
                                                    # Send as plain text - no parse_mode to avoid Markdown errors
                                                    response = requests.post(
                                                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                                        json={
                                                            "chat_id": str(telegram_id),
                                                            "text": text_message
                                                        },
                                                        timeout=15
                                                    )
                                                    if response.status_code == 200:
                                                        print("📨 FAILURE: Notification sent to Telegram")
                                                        print("✅ Failure notification sent to user")
                                                    else:
                                                        print(f"❌ Failed to send Telegram notification: {response.status_code} - {response.text}")
                                                else:
                                                    print("❌ TELEGRAM_BOT_TOKEN not found")
                                            else:
                                                print(f"❌ No telegram_id found in job {job_id}")
                                        else:
                                            print(f"❌ Job not found: {job_id}")
                                    except Exception as e:
                                        print(f"❌ Error sending failure notification: {e}")
                                else:
                                    print(f"❌ Failed to update job {job_id} status in Supabase")
                            
                except ImportError:
                    print("❌ Supabase client not available, skipping job status update")
                except Exception as e:
                    print(f"Failed to update job status: {e}")
            
            return jsonify(
                success=result.get("success", False),
                started=started_flag,
                message=result.get("message"),
                student_info=result.get("student_info"),
                status=result.get("status"),
                response_data=result.get("response_data"),
                card_filename=result.get("card_filename"),
                upload_result=result.get("upload_result"),
                stage=result.get("stage"),
                can_upload_doc=result.get("can_upload_doc"),
                debug_info=result.get("debug_info"),
                error=result.get("error"),
                job_id=job_id
            )
        except Exception as e:
            return jsonify(started=False, error=f"Lỗi xử lý: {str(e)}", debug_info={"steps":[{"t":"exception","msg":str(e)}]})
    except Exception as exc:  # pragma: no cover
        return jsonify(started=False, error=str(exc)), 500

@app.route('/start-verification-chatgpt', methods=['POST'])
def start_verification_chatgpt():
    """Start ChatGPT Teacher verification - uses Browserless to bypass fraud detection"""
    try:
        payload = request.get_json(silent=True) or {}
        url = (payload.get('url') or '').strip()
        job_id = payload.get('job_id')
        
        if not url:
            return jsonify(started=False, error='Thiếu URL'), 400
        
        print(f"🎓 Starting ChatGPT Teacher verification for job {job_id}")
        print(f"🔗 URL: {url}")

        # ===== USE BROWSERLESS FOR TEACHER VERIFICATION =====
        # Browserless bypasses fraud detection by using real browser
        # Now with rotating API keys for better reliability
        try:
            from .browserless_client import bypass_and_get_upload_url, BROWSERLESS_API_KEYS, get_browserless_url
            import asyncio
            
            if BROWSERLESS_API_KEYS:
                print(f"🌐 Using Browserless.io for fraud bypass ({len(BROWSERLESS_API_KEYS)} keys available)...")
                
                # Run async browserless verification - school will be randomly selected
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    browserless_result = loop.run_until_complete(
                        bypass_and_get_upload_url(url)  # No school = random selection
                    )
                finally:
                    loop.close()
                
                if browserless_result.get('success'):
                    print(f"✅ Browserless bypass successful!")
                    verification_id = browserless_result.get('verification_id')
                    user_data = browserless_result.get('user_data')
                    selected_school = browserless_result.get('school')
                    print(f"   Verification ID: {verification_id}")
                    print(f"   User: {user_data['first_name']} {user_data['last_name']}")
                    print(f"   School: {selected_school}")
                    
                    # ===== CONTINUE WITH DOCUMENT UPLOAD =====
                    # Now that fraud is bypassed, we need to:
                    # 1. Generate teacher paystub using og-teacher-paystub Edge Function
                    # 2. Upload to SheerID
                    # 3. Complete doc upload
                    
                    try:
                        # Generate teacher paystub using the user data from browserless
                        first_name = user_data['first_name']
                        last_name = user_data['last_name']
                        email = user_data['email']
                        # Use school from browserless result (random school was selected)
                        school_name = browserless_result.get('school', 'Discovery Education')
                        school_id = browserless_result.get('school_id')
                        
                        print(f"📄 Generating teacher paystub for {first_name} {last_name} at {school_name}...")
                        
                        # Call og-teacher-paystub Edge Function with school_id for exact match
                        from urllib.parse import urlencode
                        base_url = os.getenv("PRODUCTION_URL", "https://sheerid-verify-pro.vercel.app")
                        
                        paystub_params = {
                            "firstName": first_name,
                            "lastName": last_name,
                            "t": random.randint(1000, 9999)  # Cache buster
                        }
                        # Use school_id if available for exact match, otherwise use school_name
                        if school_id:
                            paystub_params["school_id"] = school_id
                        else:
                            paystub_params["school_name"] = school_name
                        
                        paystub_url = f"{base_url}/api/og-teacher-paystub?{urlencode(paystub_params)}"
                        
                        print(f"📄 Calling og-teacher-paystub: {paystub_url}")
                        
                        # Add bypass header if configured
                        headers = {"User-Agent": "Mozilla/5.0"}
                        bypass_token = os.getenv("VERCEL_AUTOMATION_BYPASS_SECRET")
                        if bypass_token:
                            headers["x-vercel-protection-bypass"] = bypass_token
                        
                        paystub_response = requests.get(paystub_url, headers=headers, timeout=60)
                        
                        if paystub_response.status_code == 200:
                            paystub_image_data = paystub_response.content
                            print(f"✅ Paystub generated: {len(paystub_image_data)} bytes")
                            
                            # Save paystub to temp file
                            paystub_filename = f"paystub_{first_name}_{last_name}_{random.randint(100000, 999999)}.png"
                            paystub_path = os.path.join(TMP_DIR, paystub_filename)
                            with open(paystub_path, 'wb') as f:
                                f.write(paystub_image_data)
                            print(f"✅ Paystub saved: {paystub_path}")
                            
                            # Upload to SheerID
                            print(f"📤 Uploading paystub to SheerID...")
                            upload_result = upload_student_card_to_sheerid(
                                verification_id, 
                                paystub_path, 
                                is_teacher=True,
                                session_id=f"browserless_{job_id}"
                            )
                            
                            if upload_result.get('success'):
                                print(f"✅ Paystub uploaded successfully!")
                                
                                # Complete doc upload
                                print(f"🔄 Completing doc upload...")
                                ok, comp = complete_doc_upload(
                                    verification_id, 
                                    paystub_path, 
                                    is_teacher=True,
                                    session_id=f"browserless_{job_id}"
                                )
                                
                                if ok and comp:
                                    current_step = comp.get('currentStep', '').lower()
                                    print(f"📍 Current step after complete: {current_step}")
                                    
                                    if current_step in ['success', 'complete', 'verified']:
                                        result = {
                                            "success": True,
                                            "status": "completed",
                                            "verification_id": verification_id,
                                            "student_info": {
                                                "first_name": first_name,
                                                "last_name": last_name,
                                                "email": email,
                                                "school": school_name
                                            },
                                            "card_filename": paystub_filename,
                                            "upload_result": upload_result,
                                            "message": "Teacher verification completed successfully!"
                                        }
                                    elif current_step == 'pending':
                                        # Poll for result - 10s interval, 60 attempts (10 minutes total)
                                        print(f"⏳ Verification pending, starting polling (10s x 60)...")
                                        
                                        poll_max_attempts = 60
                                        poll_delay = 10  # seconds
                                        poll_success = False
                                        final_status = "pending"
                                        
                                        for poll_attempt in range(poll_max_attempts):
                                            time.sleep(poll_delay)
                                            print(f"🔄 Polling attempt {poll_attempt + 1}/{poll_max_attempts}...")
                                            
                                            # Check verification status
                                            try:
                                                status_url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}"
                                                status_headers = {
                                                    'Accept': 'application/json',
                                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                                                }
                                                status_resp = make_request('get', status_url, headers=status_headers, timeout=30, use_scrape_proxy=True, session_id=f"browserless_{job_id}", country='us')
                                                
                                                if status_resp.status_code == 200:
                                                    status_data = status_resp.json()
                                                    poll_step = status_data.get('currentStep', '').lower()
                                                    print(f"   Current step: {poll_step}")
                                                    
                                                    if poll_step in ['success', 'complete', 'verified']:
                                                        print(f"✅ Verification completed after {poll_attempt + 1} polls!")
                                                        poll_success = True
                                                        final_status = "completed"
                                                        break
                                                    elif 'docupload' in poll_step or poll_step == 'docupload':
                                                        # docUpload means SheerID rejected document and wants re-upload = FAIL
                                                        print(f"❌ Document rejected - returned to docUpload step - BREAKING NOW")
                                                        final_status = "failed"
                                                        break
                                                    elif poll_step == 'error' or 'reject' in poll_step or 'fail' in poll_step:
                                                        print(f"❌ Verification rejected: {poll_step} - BREAKING NOW")
                                                        final_status = "failed"
                                                        break
                                                    # Still pending, continue polling
                                            except Exception as poll_err:
                                                print(f"⚠️ Poll error: {poll_err}")
                                        
                                        if poll_success:
                                            result = {
                                                "success": True,
                                                "status": "completed",
                                                "verification_id": verification_id,
                                                "student_info": {
                                                    "first_name": first_name,
                                                    "last_name": last_name,
                                                    "email": email,
                                                    "school": school_name
                                                },
                                                "card_filename": paystub_filename,
                                                "upload_result": upload_result,
                                                "message": "Teacher verification completed successfully!"
                                            }
                                        else:
                                            result = {
                                                "success": False,
                                                "status": final_status,
                                                "verification_id": verification_id,
                                                "student_info": {
                                                    "first_name": first_name,
                                                    "last_name": last_name,
                                                    "email": email,
                                                    "school": school_name
                                                },
                                                "card_filename": paystub_filename,
                                                "message": f"Verification {final_status} after polling"
                                            }
                                    else:
                                        result = {
                                            "success": False,
                                            "status": current_step,
                                            "verification_id": verification_id,
                                            "message": f"Verification at step: {current_step}"
                                        }
                                else:
                                    result = {
                                        "success": False,
                                        "status": "failed",
                                        "error": f"Complete doc upload failed: {comp}",
                                        "verification_id": verification_id
                                    }
                            else:
                                result = {
                                    "success": False,
                                    "status": "failed",
                                    "error": f"Upload failed: {upload_result.get('error')}",
                                    "verification_id": verification_id
                                }
                        else:
                            print(f"❌ Paystub generation failed: {paystub_response.status_code}")
                            result = {
                                "success": False,
                                "status": "failed",
                                "error": f"Paystub generation failed: {paystub_response.status_code}",
                                "verification_id": verification_id
                            }
                    except Exception as doc_err:
                        print(f"❌ Document upload error: {doc_err}")
                        result = {
                            "success": False,
                            "status": "failed",
                            "error": f"Document upload error: {str(doc_err)}",
                            "verification_id": verification_id
                        }
                    
                    # ===== SEND TELEGRAM NOTIFICATION & UPDATE JOB STATUS =====
                    try:
                        from .supabase_client import get_verification_job_by_id, update_verification_job_status
                        
                        # Get job info to find telegram_id
                        job_info = get_verification_job_by_id(job_id)
                        telegram_id = job_info.get('telegram_id') if job_info else None
                        
                        if telegram_id:
                            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                            if bot_token:
                                if result.get('success'):
                                    # SUCCESS notification
                                    success_msg = f"""✅ Teacher Verification thành công!

🆔 Job ID: `{job_id}`
🎓 Trường: {result.get('student_info', {}).get('school', 'N/A')}
👤 Tên: {result.get('student_info', {}).get('first_name', '')} {result.get('student_info', {}).get('last_name', '')}

🎉 Bạn đã có thể sử dụng ưu đãi giáo viên!"""
                                    
                                    # Update job status to completed
                                    update_verification_job_status(job_id, 'completed')
                                    print(f"✅ Updated job {job_id} status to completed")
                                    
                                    # Process charging for ChatGPT Teacher (75 xu/cash)
                                    print(f"💰 Processing ChatGPT charging for job {job_id}")
                                    charging_success = process_chatgpt_job_charging(job_id)
                                    if charging_success:
                                        print(f"✅ Successfully charged ChatGPT job {job_id}")
                                    else:
                                        print(f"⚠️ Charging skipped for ChatGPT job {job_id}")
                                    
                                else:
                                    # FAIL notification
                                    fail_reason = result.get('error') or result.get('message') or 'Document rejected by SheerID'
                                    fail_msg = f"""❌ Teacher Verification thất bại!

🆔 Job ID: `{job_id}`
🔍 Lý do: {fail_reason}

💡 Vui lòng thử lại với link khác hoặc liên hệ hỗ trợ."""
                                    
                                    # Update job status to failed
                                    update_verification_job_status(job_id, 'failed')
                                    print(f"✅ Updated job {job_id} status to failed")
                                    
                                    success_msg = fail_msg  # Use same variable for sending
                                
                                # Send notification
                                import requests as tg_requests
                                tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                tg_payload = {
                                    "chat_id": telegram_id,
                                    "text": success_msg,
                                    "parse_mode": "Markdown"
                                }
                                tg_resp = tg_requests.post(tg_url, json=tg_payload, timeout=10)
                                print(f"📤 Telegram notification sent: {tg_resp.status_code}")
                            else:
                                print(f"⚠️ TELEGRAM_BOT_TOKEN not set, skipping notification")
                        else:
                            print(f"⚠️ No telegram_id found for job {job_id}, skipping notification")
                            # Still update job status even without notification
                            if result.get('success'):
                                update_verification_job_status(job_id, 'completed')
                            else:
                                update_verification_job_status(job_id, 'failed')
                    except Exception as notif_err:
                        print(f"⚠️ Error sending notification: {notif_err}")
                    
                    # Return result from browserless flow
                    return jsonify(
                        success=result.get("success", False),
                        started=True,
                        message=result.get("message"),
                        student_info=result.get("student_info"),
                        status=result.get("status"),
                        card_filename=result.get("card_filename"),
                        upload_result=result.get("upload_result"),
                        error=result.get("error"),
                        job_id=job_id,
                        verification_type='chatgpt',
                        verification_id=result.get("verification_id")
                    )
                else:
                    print(f"❌ Browserless bypass failed: {browserless_result.get('error')}")
                    
                    # Send failure notification for browserless bypass failure
                    try:
                        from .supabase_client import get_verification_job_by_id, update_verification_job_status
                        job_info = get_verification_job_by_id(job_id)
                        telegram_id = job_info.get('telegram_id') if job_info else None
                        
                        if telegram_id:
                            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                            if bot_token:
                                fail_msg = f"""❌ Teacher Verification thất bại!

🆔 Job ID: `{job_id}`
🔍 Lý do: Không thể bypass fraud detection
💡 Vui lòng thử lại sau hoặc liên hệ hỗ trợ."""
                                
                                import requests as tg_requests
                                tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                tg_payload = {"chat_id": telegram_id, "text": fail_msg, "parse_mode": "Markdown"}
                                tg_requests.post(tg_url, json=tg_payload, timeout=10)
                                
                        # Update job status to failed
                        update_verification_job_status(job_id, 'failed')
                        print(f"✅ Updated job {job_id} status to failed (browserless bypass failed)")
                    except Exception as notif_err:
                        print(f"⚠️ Error sending browserless failure notification: {notif_err}")
                    
                    # Return failure instead of fallback (old API method doesn't work well)
                    return jsonify(
                        success=False,
                        started=False,
                        error=f"Browserless bypass failed: {browserless_result.get('error')}",
                        job_id=job_id,
                        verification_type='chatgpt'
                    )
            else:
                print(f"⚠️ BROWSERLESS_API_KEY not set")
                # Send failure notification
                try:
                    from .supabase_client import get_verification_job_by_id, update_verification_job_status
                    job_info = get_verification_job_by_id(job_id)
                    telegram_id = job_info.get('telegram_id') if job_info else None
                    if telegram_id:
                        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                        if bot_token:
                            fail_msg = f"""❌ Teacher Verification thất bại!

🆔 Job ID: `{job_id}`
🔍 Lý do: Hệ thống chưa được cấu hình
💡 Vui lòng liên hệ admin."""
                            import requests as tg_requests
                            tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                            tg_requests.post(tg_url, json={"chat_id": telegram_id, "text": fail_msg, "parse_mode": "Markdown"}, timeout=10)
                    update_verification_job_status(job_id, 'failed')
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                return jsonify(success=False, started=False, error="BROWSERLESS_API_KEY not configured", job_id=job_id)
        except ImportError as ie:
            print(f"⚠️ Browserless client not available: {ie}")
            # Send failure notification
            try:
                from .supabase_client import get_verification_job_by_id, update_verification_job_status
                job_info = get_verification_job_by_id(job_id)
                telegram_id = job_info.get('telegram_id') if job_info else None
                if telegram_id:
                    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                    if bot_token:
                        fail_msg = f"""❌ Teacher Verification thất bại!

🆔 Job ID: `{job_id}`
🔍 Lý do: Module không khả dụng
💡 Vui lòng liên hệ admin."""
                        import requests as tg_requests
                        tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                        tg_requests.post(tg_url, json={"chat_id": telegram_id, "text": fail_msg, "parse_mode": "Markdown"}, timeout=10)
                update_verification_job_status(job_id, 'failed')
            except Exception as e:
                print(f"⚠️ Error: {e}")
            return jsonify(success=False, started=False, error=f"Browserless client not available: {ie}", job_id=job_id)
        except Exception as be:
            print(f"❌ Browserless error: {be}")
            # Send failure notification
            try:
                from .supabase_client import get_verification_job_by_id, update_verification_job_status
                job_info = get_verification_job_by_id(job_id)
                telegram_id = job_info.get('telegram_id') if job_info else None
                if telegram_id:
                    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                    if bot_token:
                        fail_msg = f"""❌ Teacher Verification thất bại!

🆔 Job ID: `{job_id}`
🔍 Lý do: Lỗi hệ thống - {str(be)[:50]}
💡 Vui lòng thử lại sau."""
                        import requests as tg_requests
                        tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                        tg_requests.post(tg_url, json={"chat_id": telegram_id, "text": fail_msg, "parse_mode": "Markdown"}, timeout=10)
                update_verification_job_status(job_id, 'failed')
            except Exception as e:
                print(f"⚠️ Error: {e}")
            return jsonify(success=False, started=False, error=f"Browserless error: {str(be)}", job_id=job_id)
    except Exception as exc:
        return jsonify(started=False, error=str(exc)), 500

def process_chatgpt_job_charging(job_id):
    """Process charging for ChatGPT verification job - 75 xu/cash"""
    print(f"💰 DEBUG: Starting ChatGPT charging process for job {job_id} (75 xu/cash)")
    
    # Check if already charged
    if is_job_already_charged(job_id):
        print(f"⚠️ ChatGPT job {job_id} already charged, skipping")
        return False
    
    try:
        from .supabase_client import get_verification_job_by_id, get_user_by_telegram_id, get_supabase_client
        
        job_info = get_verification_job_by_id(job_id)
        if not job_info:
            print(f"❌ ChatGPT job not found: {job_id}")
            return False
        
        telegram_id = job_info.get('telegram_id')
        if not telegram_id:
            print(f"❌ No telegram_id found in ChatGPT job {job_id}")
            return False
        
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            print(f"❌ User not found for telegram_id {telegram_id}")
            return False
        
        coins = user.get('coins', 0)
        cash = user.get('cash', 0)
        is_vip = user.get('is_vip', False)
        user_lang = user.get('language', 'vi')  # Get user language
        
        print(f"💰 User {telegram_id} - BEFORE ChatGPT charging: coins: {coins}, cash: {cash}, is_vip: {is_vip}")
        
        # Mark as charged first
        mark_job_as_charged(job_id)
        
        # ChatGPT Teacher pricing: 75 xu or 75 cash
        if coins >= 75:
            new_coins = coins - 75
            new_cash = cash
            payment_message = f"75 xu (còn lại: {new_coins} xu)"
            print(f"✅ Charged 75 xu from user {telegram_id}: {coins} -> {new_coins}")
        elif cash >= 75:
            new_coins = coins
            new_cash = cash - 75
            payment_message = f"75 cash (còn lại: {new_cash} cash)"
            print(f"✅ Charged 75 cash from user {telegram_id}: {cash} -> {new_cash}")
        else:
            print(f"❌ User {telegram_id} insufficient funds: {coins} xu, {cash} cash")
            return False
        
        # Update user balance
        supabase = get_supabase_client()
        if supabase:
            from datetime import datetime
            response = supabase.table('users').update({
                'coins': new_coins,
                'cash': new_cash,
                'updated_at': datetime.now().isoformat()
            }).eq('telegram_id', str(telegram_id)).execute()
            
            if response.data:
                print(f"✅ Updated user balance for {telegram_id}")
                print(f"💰 User {telegram_id} - AFTER ChatGPT charging: coins: {new_coins}, cash: {new_cash}")
                
                # Create transaction record
                try:
                    transaction_data = {
                        'user_id': user.get('id'),
                        'type': 'verify_chatgpt_cash' if new_cash != cash else 'verify_chatgpt',
                        'amount': -75000 if new_cash != cash else -75000,  # -75000 VND
                        'coins': -75 if new_cash != cash else -75,
                        'description': f'Verify ChatGPT Teacher - Job {job_id}',
                        'status': 'completed',
                        'job_id': None,
                        'created_at': datetime.now().isoformat()
                    }
                    
                    supabase.table('transactions').insert(transaction_data).execute()
                    print(f"✅ Created transaction record for ChatGPT job {job_id}")
                except Exception as e:
                    print(f"⚠️ Failed to create transaction record: {e}")
                
                # Send success notification
                try:
                    from .telegram import is_notification_already_sent, mark_notification_sent
                    
                    if not is_notification_already_sent(job_id):
                        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                        if bot_token:
                            mark_notification_sent(job_id)
                            
                            # Multilingual ChatGPT Teacher success message
                            vip_text = {'vi': 'Có', 'en': 'Yes', 'zh': '是'}.get(user_lang, 'Có')
                            no_vip_text = {'vi': 'Không', 'en': 'No', 'zh': '否'}.get(user_lang, 'Không')
                            
                            chatgpt_msgs = {
                                'vi': [
                                    "✅ CHATGPT TEACHER VERIFY THÀNH CÔNG!",
                                    "",
                                    f"🆔 Job ID: `{job_id}`",
                                    "� Locại: ChatGPT Teacher",
                                    "",
                                    f"💰 Thanh toán: {payment_message}",
                                    f"💎 VIP: {vip_text if is_vip else no_vip_text} | 💰 Cash: {new_cash} | 🌕 Xu: {new_coins}",
                                    "",
                                    "🎉 Verification thành công! Bạn có thể sử dụng ChatGPT Teacher ngay bây giờ."
                                ],
                                'en': [
                                    "✅ CHATGPT TEACHER VERIFICATION SUCCESSFUL!",
                                    "",
                                    f"🆔 Job ID: `{job_id}`",
                                    "🎓 Type: ChatGPT Teacher",
                                    "",
                                    f"💰 Payment: {payment_message}",
                                    f"💎 VIP: {vip_text if is_vip else no_vip_text} | 💰 Cash: {new_cash} | 🌕 Xu: {new_coins}",
                                    "",
                                    "🎉 Verification successful! You can use ChatGPT Teacher now."
                                ],
                                'zh': [
                                    "✅ CHATGPT TEACHER 验证成功！",
                                    "",
                                    f"🆔 Job ID: `{job_id}`",
                                    "🎓 类型: ChatGPT Teacher",
                                    "",
                                    f"💰 支付: {payment_message}",
                                    f"💎 VIP: {vip_text if is_vip else no_vip_text} | 💰 Cash: {new_cash} | 🌕 Xu: {new_coins}",
                                    "",
                                    "🎉 验证成功！您现在可以使用 ChatGPT Teacher。"
                                ]
                            }
                            text_message = "\n".join(chatgpt_msgs.get(user_lang, chatgpt_msgs['vi']))
                            
                            response = requests.post(
                                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                json={
                                    "chat_id": str(telegram_id),
                                    "text": text_message,
                                    "parse_mode": "Markdown"
                                },
                                timeout=15
                            )
                            
                            if response.status_code == 200:
                                print(f"✅ Sent ChatGPT success notification to user {telegram_id}")
                            else:
                                print(f"❌ Failed to send notification: {response.status_code}")
                    else:
                        print(f"⚠️ Notification already sent for ChatGPT job {job_id}")
                except Exception as e:
                    print(f"⚠️ Failed to send notification: {e}")
                
                return True
            else:
                print(f"❌ Failed to update user balance")
                return False
        else:
            print(f"❌ Supabase client not available")
            return False
            
    except Exception as e:
        print(f"❌ Error processing ChatGPT charging for job {job_id}: {e}")
        return False


# ============================================================
# STUDENT VERIFICATION WITH BROWSERLESS + PROXY
# ============================================================

@app.route('/start-verification-student-browserless', methods=['POST'])
def start_verification_student_browserless():
    """
    Start Student verification using Browserless.io with proxy
    
    Flow:
    1. Browserless fills form with random university, name, DOB (using proxy)
    2. SheerID accepts (no fraud reject)
    3. Generate transcript image with data from browserless
    4. Upload transcript to SheerID
    5. Poll for result
    
    This bypasses fraud detection by using real browser with US proxy
    """
    try:
        payload = request.get_json(silent=True) or {}
        url = (payload.get('url') or '').strip()
        job_id = payload.get('job_id')
        use_proxy = payload.get('use_proxy', True)  # Default to use proxy
        
        if not url:
            return jsonify(started=False, error='Thiếu URL'), 400
        
        print(f"🎓 Starting Student Browserless verification for job {job_id}")
        print(f"🔗 URL: {url}")
        print(f"🌐 Use proxy: {use_proxy}")

        # ===== USE BROWSERLESS FOR STUDENT VERIFICATION =====
        try:
            from .browserless_client import (
                student_bypass_and_get_data, 
                BROWSERLESS_API_KEYS, 
                get_browserless_url
            )
            import asyncio
            
            if not BROWSERLESS_API_KEYS:
                print(f"⚠️ BROWSERLESS_API_KEY not set")
                return jsonify(
                    success=False, 
                    started=False, 
                    error="BROWSERLESS_API_KEY not configured", 
                    job_id=job_id
                )
            
            print(f"🌐 Using Browserless.io for student fraud bypass ({len(BROWSERLESS_API_KEYS)} keys available)...")
            
            # Run async browserless verification
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                browserless_result = loop.run_until_complete(
                    student_bypass_and_get_data(url, use_proxy=use_proxy)
                )
            finally:
                loop.close()
            
            if browserless_result.get('success'):
                print(f"✅ Browserless student bypass successful!")
                verification_id = browserless_result.get('verification_id')
                university = browserless_result.get('university', {})
                student_data = browserless_result.get('student_data', {})
                
                first_name = student_data.get('first_name', 'John')
                last_name = student_data.get('last_name', 'Doe')
                birth_date = student_data.get('birth_date', '2002-01-01')
                email = student_data.get('email', '')
                
                print(f"   Verification ID: {verification_id}")
                print(f"   University: {university.get('name')} (ID: {university.get('id')})")
                print(f"   Student: {first_name} {last_name}")
                print(f"   DOB: {birth_date}")
                
                # ===== GENERATE TRANSCRIPT =====
                try:
                    from .transcript_generator import generate_transcript_html, render_transcript_auto
                    from .universities_config import generate_student_id as gen_transcript_student_id
                    
                    # Generate student ID
                    transcript_student_id = gen_transcript_student_id(university)
                    
                    # Convert birth_date to readable format
                    try:
                        bd_parts = birth_date.split('-')
                        months = ["January", "February", "March", "April", "May", "June",
                                  "July", "August", "September", "October", "November", "December"]
                        dob_readable = f"{months[int(bd_parts[1])-1]} {int(bd_parts[2])}, {bd_parts[0]}"
                    except:
                        dob_readable = "January 1, 2002"
                    
                    print(f"📄 Generating transcript for {first_name} {last_name} at {university.get('name')}...")
                    
                    # Generate transcript HTML
                    html_content, transcript_info = generate_transcript_html(
                        university=university,
                        first_name=first_name,
                        last_name=last_name,
                        dob=dob_readable,
                        student_id=transcript_student_id
                    )
                    
                    print(f"📄 Transcript generated - Student ID: {transcript_info['student_id']}")
                    
                    # Render transcript to image
                    random_suffix = random.randint(100000, 999999)
                    transcript_filename = f"transcript_{last_name}_{first_name}_{random_suffix}.png"
                    transcript_path = os.path.join(TMP_DIR, transcript_filename)
                    
                    render_transcript_auto(html_content, transcript_info, transcript_path)
                    print(f"✅ Transcript rendered to {transcript_path}")
                    
                    # ===== UPLOAD TO SHEERID =====
                    print(f"📤 Uploading transcript to SheerID...")
                    upload_result = upload_transcript_to_sheerid(
                        verification_id, 
                        transcript_path, 
                        is_teacher=False,
                        session_id=f"browserless_student_{job_id}"
                    )
                    
                    if upload_result.get('success'):
                        print(f"✅ Transcript uploaded successfully!")
                        
                        # Complete doc upload
                        print(f"🔄 Completing doc upload...")
                        proxy_session_id = f"browserless_student_{job_id}"
                        ok, comp = complete_doc_upload(
                            verification_id, 
                            transcript_path, 
                            is_teacher=False,
                            session_id=proxy_session_id
                        )
                        
                        current_step = (comp or {}).get('currentStep', '').lower() if comp else ''
                        print(f"📍 Current step after complete: {current_step}")
                        
                        # Poll for result using same function as normal student verification
                        # Student: 100 attempts x 3s = 300s total (5 minutes)
                        print(f"⏳ Starting polling for student verification (100 x 3s = 300s max)...")
                        poll_ok, poll_data = wait_for_doc_processing(
                            verification_id, 
                            max_attempts=100, 
                            delay=3.0, 
                            is_teacher=False, 
                            session_id=proxy_session_id,
                            university_id=str(university.get('id', '')),
                            university_name=university.get('name', '')
                        )
                        
                        # Use status transition module to determine final status
                        # Requirements: 3.2, 3.3, 3.4
                        from .status_transition import (
                            map_polling_result_to_job_status, 
                            JobStatus, 
                            get_status_string
                        )
                        
                        job_status, status_reason = map_polling_result_to_job_status(poll_ok, poll_data)
                        print(f"📊 Status transition: poll_ok={poll_ok} -> {job_status.value} ({status_reason})")
                        
                        # Build result based on job status
                        if job_status == JobStatus.COMPLETED:
                            result = {
                                "success": True,
                                "status": get_status_string(job_status),
                                "verification_id": verification_id,
                                "student_info": {
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "email": email,
                                    "university": university.get('name'),
                                    "student_id": transcript_info['student_id']
                                },
                                "card_filename": transcript_filename,
                                "upload_result": upload_result,
                                "message": "Student verification completed successfully!"
                            }
                        elif job_status == JobStatus.TIMEOUT:
                            # Handle timeout case (Requirements 3.4)
                            result = {
                                "success": False,
                                "status": get_status_string(job_status),
                                "verification_id": verification_id,
                                "student_info": {
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "university": university.get('name')
                                },
                                "card_filename": transcript_filename,
                                "error": status_reason,
                                "message": f"Verification timeout: {status_reason}"
                            }
                        else:
                            # Handle failure case (Requirements 3.3)
                            result = {
                                "success": False,
                                "status": get_status_string(job_status),
                                "verification_id": verification_id,
                                "student_info": {
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "university": university.get('name')
                                },
                                "card_filename": transcript_filename,
                                "error": status_reason,
                                "message": f"Verification failed: {status_reason}"
                            }
                    else:
                        result = {
                            "success": False,
                            "status": "failed",
                            "error": f"Upload failed: {upload_result.get('error')}",
                            "verification_id": verification_id
                        }
                        
                except Exception as transcript_err:
                    print(f"❌ Transcript generation error: {transcript_err}")
                    import traceback
                    traceback.print_exc()
                    result = {
                        "success": False,
                        "status": "failed",
                        "error": f"Transcript generation error: {str(transcript_err)}",
                        "verification_id": verification_id
                    }
                
                # ===== SEND TELEGRAM NOTIFICATION & UPDATE JOB STATUS =====
                # Use status from result to update job status correctly
                # Requirements: 3.2, 3.3, 3.4
                try:
                    from .supabase_client import get_verification_job_by_id, update_verification_job_status
                    
                    job_info = get_verification_job_by_id(job_id)
                    telegram_id = job_info.get('telegram_id') if job_info else None
                    
                    # Get the status from result (already mapped by status_transition module)
                    result_status = result.get('status', 'failed')
                    
                    if telegram_id:
                        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                        if bot_token:
                            if result.get('success'):
                                # Success case (Requirements 3.2)
                                success_msg = f"""✅ Student Verification thành công!

🆔 Job ID: `{job_id}`
🎓 Trường: {result.get('student_info', {}).get('university', 'N/A')}
👤 Tên: {first_name} {last_name}

🎉 Bạn đã có thể sử dụng ưu đãi sinh viên!"""
                                
                                update_verification_job_status(job_id, 'completed')
                                print(f"✅ Updated job {job_id} status to completed")
                                
                                # Process charging for student verification
                                print(f"💰 Processing student charging for job {job_id}")
                                charging_success = process_completed_job_charging(job_id)
                                if charging_success:
                                    print(f"✅ Successfully charged student job {job_id}")
                            elif result_status == 'timeout':
                                # Timeout case (Requirements 3.4)
                                fail_reason = result.get('error') or 'Verification timeout'
                                success_msg = f"""⏰ Student Verification timeout!

🆔 Job ID: `{job_id}`
🔍 Lý do: {fail_reason}

💡 Vui lòng thử lại sau."""
                                
                                update_verification_job_status(job_id, 'timeout')
                                print(f"✅ Updated job {job_id} status to timeout")
                            else:
                                # Failure case (Requirements 3.3)
                                fail_reason = result.get('error') or result.get('message') or 'Document rejected'
                                success_msg = f"""❌ Student Verification thất bại!

🆔 Job ID: `{job_id}`
🔍 Lý do: {fail_reason}

💡 Vui lòng thử lại với link khác."""
                                
                                update_verification_job_status(job_id, 'failed')
                                print(f"✅ Updated job {job_id} status to failed")
                            
                            # Send notification
                            import requests as tg_requests
                            tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                            tg_payload = {
                                "chat_id": telegram_id,
                                "text": success_msg,
                                "parse_mode": "Markdown"
                            }
                            tg_resp = tg_requests.post(tg_url, json=tg_payload, timeout=10)
                            print(f"📤 Telegram notification sent: {tg_resp.status_code}")
                    else:
                        # Still update job status based on result
                        if result.get('success'):
                            update_verification_job_status(job_id, 'completed')
                        elif result_status == 'timeout':
                            update_verification_job_status(job_id, 'timeout')
                        else:
                            update_verification_job_status(job_id, 'failed')
                except Exception as notif_err:
                    print(f"⚠️ Error sending notification: {notif_err}")
                
                # Return result
                return jsonify(
                    success=result.get("success", False),
                    started=True,
                    message=result.get("message"),
                    student_info=result.get("student_info"),
                    status=result.get("status"),
                    card_filename=result.get("card_filename"),
                    upload_result=result.get("upload_result"),
                    error=result.get("error"),
                    job_id=job_id,
                    verification_type='student_browserless',
                    verification_id=result.get("verification_id")
                )
            else:
                # Browserless bypass failed
                print(f"❌ Browserless student bypass failed: {browserless_result.get('error')}")
                
                try:
                    from .supabase_client import get_verification_job_by_id, update_verification_job_status
                    job_info = get_verification_job_by_id(job_id)
                    telegram_id = job_info.get('telegram_id') if job_info else None
                    
                    if telegram_id:
                        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                        if bot_token:
                            fail_msg = f"""❌ Student Verification thất bại!

🆔 Job ID: `{job_id}`
🔍 Lý do: Không thể bypass fraud detection
💡 Vui lòng thử lại sau."""
                            
                            import requests as tg_requests
                            tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                            tg_requests.post(tg_url, json={"chat_id": telegram_id, "text": fail_msg, "parse_mode": "Markdown"}, timeout=10)
                    
                    update_verification_job_status(job_id, 'failed')
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                
                return jsonify(
                    success=False,
                    started=False,
                    error=f"Browserless bypass failed: {browserless_result.get('error')}",
                    job_id=job_id,
                    verification_type='student_browserless'
                )
                
        except ImportError as ie:
            print(f"⚠️ Browserless client not available: {ie}")
            return jsonify(
                success=False, 
                started=False, 
                error=f"Browserless client not available: {ie}", 
                job_id=job_id
            )
        except Exception as be:
            print(f"❌ Browserless error: {be}")
            import traceback
            traceback.print_exc()
            return jsonify(
                success=False, 
                started=False, 
                error=f"Browserless error: {str(be)}", 
                job_id=job_id
            )
            
    except Exception as exc:
        print(f"❌ Exception in start_verification_student_browserless: {exc}")
        import traceback
        traceback.print_exc()
        return jsonify(started=False, error=str(exc)), 500


@app.route('/test-charging', methods=['GET'])
def test_charging():
    """DISABLED DUE TO SECURITY VULNERABILITY
    
    This endpoint was exposing sensitive information or allowing
    unauthorized actions without proper authentication.
    
    Disabled: 2026-03-03
    Incident: Security audit after hack incident
    """
    return jsonify({
        'error': 'This endpoint has been permanently disabled for security reasons',
        'code': 'ENDPOINT_DISABLED'
    }), 403

@app.route('/fix-charging', methods=['POST'])
def fix_charging():
    """Fix charging for specific job or all uncharged completed jobs"""
    try:
        payload = request.get_json(silent=True) or {}
        job_id = payload.get('job_id')
        
        if job_id:
            # Process specific job
            print(f"🔧 Manual charging fix for job: {job_id}")
            success = process_completed_job_charging(job_id)
            return jsonify({
                'success': success,
                'message': f'Job {job_id} charging processed successfully' if success else f'Failed to process charging for job {job_id}',
                'job_id': job_id
            })
        else:
            # Process all completed jobs from last 24 hours that weren't charged
            try:
                from .supabase_client import get_supabase_client
                from datetime import datetime, timedelta
                
                supabase = get_supabase_client()
                if not supabase:
                    return jsonify({'success': False, 'error': 'Supabase not available'})
                
                # Get completed jobs from last 24 hours
                yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
                
                completed_jobs = supabase.table('verification_jobs').select('job_id, telegram_id').eq('status', 'completed').gte('updated_at', yesterday).execute()
                
                processed = 0
                failed = 0
                skipped = 0
                
                print(f"🔧 Found {len(completed_jobs.data)} completed jobs to check")
                
                for job in completed_jobs.data:
                    job_id = job.get('job_id')
                    if job_id:
                        if not is_job_already_charged(job_id):
                            print(f"🔄 Processing uncharged job: {job_id}")
                            if process_completed_job_charging(job_id):
                                processed += 1
                                print(f"✅ Successfully processed job: {job_id}")
                            else:
                                failed += 1
                                print(f"❌ Failed to process job: {job_id}")
                        else:
                            skipped += 1
                            print(f"⚠️ Job {job_id} already charged, skipping")
                
                return jsonify({
                    'success': True,
                    'message': f'Processed {processed} jobs, {failed} failed, {skipped} skipped',
                    'processed': processed,
                    'failed': failed,
                    'skipped': skipped,
                    'total_checked': len(completed_jobs.data)
                })
                
            except Exception as e:
                print(f"❌ Error in batch processing: {e}")
                return jsonify({'success': False, 'error': str(e)})
    
    except Exception as e:
        print(f"❌ Error in fix_charging endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/test-payload', methods=['POST'])
def test_payload():
    """Test endpoint to see what payload we're sending"""
    try:
        payload = request.get_json(silent=True) or {}
        url = (payload.get('url') or '').strip()
        if not url:
            return jsonify(success=False, error='Thiếu URL'), 400

        # Generate American names - expanded list for test-payload
        first_names = [
            'James','John','Robert','Michael','David','William','Richard','Joseph','Thomas','Christopher',
            'Mary','Patricia','Jennifer','Linda','Elizabeth','Barbara','Susan','Jessica','Sarah','Karen',
            'Liam','Noah','Oliver','Elijah','Lucas','Mason','Logan','Alexander','Ethan','Henry','Sebastian',
            'Emma','Olivia','Ava','Isabella','Sophia','Mia','Charlotte','Amelia','Harper','Evelyn','Abigail',
            'Benjamin','Samuel','Daniel','Matthew','Anthony','Mark','Joshua','Andrew','Ryan','Brian','Kevin'
        ]
        last_names = [
            'Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Rodriguez','Martinez',
            'Wilson','Anderson','Taylor','Thomas','Moore','Jackson','Martin','Lee','Thompson','White',
            'Harris','Clark','Lewis','Robinson','Walker','Hall','Allen','Young','King','Wright','Scott'
        ]
        
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        middle_name = ""
        full_name = f"{first_name} {last_name}"
        # Add random number to avoid duplicate emails
        random_suffix = random.randint(1000, 9999)
        email = f"{first_name.lower()}.{last_name.lower()}{random_suffix}@students.edu"
        
        # Generate DOB (18-23 years old)
        current_year = datetime.now().year
        birth_year = random.randint(current_year - 23, current_year - 18)
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)
        birth_date = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"
        
        # Extract verification ID
        verification_id = None
        if 'verificationId=' in url:
            verification_id = url.split('verificationId=')[-1].split('&')[0]
        
        # Use university rotation for test payload
        test_university = get_random_university()
        
        test_payload = {
            "firstName": first_name,
            "lastName": last_name,
            "birthDate": birth_date,
            "email": email,
            "deviceFingerprintHash": generate_device_fingerprint(),
            "locale": "en-US",
            "country": "US",
            "metadata": {
                "marketConsentValue": False,
                "consentGiven": True,
                "termsAccepted": True,
                "source": "web",
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            "organization": {
                "id": test_university["id"],
                "idExtended": test_university["idExtended"],
                "name": test_university["name"]
            },
            "phoneNumber": "",
            "ipAddress": "127.0.0.1",
            "externalUserId": f"student_{random.randint(100000, 999999)}",
            "email2": "",
            "cvecNumber": ""
        }
        
        return jsonify(
            success=True,
            message="Test payload generated",
            student_info={
                "name": f"{first_name} {last_name}",
                "email": email,
                "birth_date": birth_date,
                "university": test_university["name"]
            },
            payload=test_payload,
            debug_info={
                "url": url,
                "verification_id": verification_id,
                "api_url": f"https://services.sheerid.com/rest/v2/verification/{verification_id}/step/collectStudentPersonalInfo" if verification_id else "UNKNOWN"
            }
        )
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/preview-card', methods=['POST'])
def preview_card():
    """Preview endpoint để xem thẻ sinh viên với thông tin random"""
    try:
        # Xóa các file preview card cũ trước khi tạo mới
        import glob
        old_preview_cards = glob.glob("preview_card_.png")
        for old_card in old_preview_cards:
            try:
                os.remove(old_card)
                print(f"Deleted old preview card: {old_card}")
            except Exception as e:
                print(f"Could not delete {old_card}: {e}")
        
        # Generate American names - expanded 100+ names
        first_names = [
            # Male names
            'James','John','Robert','Michael','David','William','Richard','Joseph','Thomas','Christopher',
            'Daniel','Matthew','Anthony','Mark','Donald','Steven','Paul','Andrew','Joshua','Kenneth',
            'Kevin','Brian','George','Timothy','Ronald','Edward','Jason','Jeffrey','Ryan','Jacob',
            'Gary','Nicholas','Eric','Jonathan','Stephen','Larry','Justin','Scott','Brandon','Benjamin',
            'Samuel','Raymond','Gregory','Frank','Alexander','Patrick','Jack','Dennis','Jerry','Tyler',
            # Female names
            'Mary','Patricia','Jennifer','Linda','Elizabeth','Barbara','Susan','Jessica','Sarah','Karen',
            'Lisa','Nancy','Betty','Margaret','Sandra','Ashley','Kimberly','Emily','Donna','Michelle',
            'Dorothy','Carol','Amanda','Melissa','Deborah','Stephanie','Rebecca','Sharon','Laura','Cynthia',
            'Kathleen','Amy','Angela','Shirley','Anna','Brenda','Pamela','Emma','Nicole','Helen',
            'Samantha','Katherine','Christine','Debra','Rachel','Carolyn','Janet','Catherine','Maria','Heather'
        ]
        last_names = [
            'Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Rodriguez','Martinez',
            'Wilson','Anderson','Taylor','Thomas','Moore','Jackson','Martin','Lee','Thompson','White',
            'Harris','Clark','Lewis','Robinson','Walker','Young','Allen','King','Wright','Scott',
            'Torres','Nguyen','Hill','Flores','Green','Adams','Nelson','Baker','Hall','Rivera',
            'Campbell','Mitchell','Carter','Roberts','Gomez','Phillips','Evans','Turner','Diaz','Parker'
        ]
        
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        full_name = f"{first_name} {last_name}"
        
        # Generate DOB (18-23 years old)
        current_year = datetime.now().year
        birth_year = random.randint(current_year - 23, current_year - 18)
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)
        birth_date = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"
        
        # Generate student ID: 8 random digits
        student_id = f"{random.randint(10000000, 99999999)}"
        
        student_data = {
            'name': full_name,
            'first_name': first_name,
            'last_name': last_name,
            'birth_date': birth_date,
            'student_id': student_id
        }
        
        first_name = student_data['first_name']
        last_name = student_data['last_name']
        birth_date = student_data['birth_date'].replace('.', '-')
        # Add random number to avoid duplicate emails
        random_suffix = random.randint(1000, 9999)
        email = f"{first_name.lower()}.{last_name.lower()}{random_suffix}@students.artinstitutes.edu"
        
        # Generate student ID for card: 7 random digits, no prefix
        student_id = student_data['student_id']
        
        # Tạo thông tin sinh viên cho thẻ
        student_card_info = {
            'name': student_data['name'],  # Full American name: FIRST LAST
            'first_name': first_name,
            'last_name': last_name,
            'birth_date': birth_date.replace('-', '.'),
            'student_id': student_id
        }
        
        # Use university rotation for preview card
        preview_university = get_random_university()
        
        # Tạo thẻ sinh viên
        avatar_path = get_random_avatar()
        card = create_student_card(student_card_info, avatar_path, template_path=preview_university["template"])
        
        card_filename = None
        if card:
            # Lưu thẻ với tên file vào /tmp
            # Generate filename with lastname_firstname_6digits format (remove spaces)
            random_suffix = random.randint(100000, 999999)
            clean_last = remove_vietnamese_accents(last_name).replace(' ', '')
            clean_first = remove_vietnamese_accents(first_name).replace(' ', '')
            card_filename = f"{clean_last}_{clean_first}_{random_suffix}.jpg"
            save_path = os.path.join(TMP_DIR, card_filename)
            # JPEG không hỗ trợ alpha; chuyển sang RGB trước khi lưu
            card_to_save = card.convert('RGB') if card.mode in ('RGBA', 'LA') else card
            card_to_save.save(save_path, 'JPEG')
            print(f"Preview card created: {save_path}")
        
        return jsonify(
            success=True,
            message="Preview card generated successfully",
            student_info={
                "name": f"{first_name} {last_name}",
                "email": email,
                "birth_date": birth_date,
                "university": preview_university["name"],
                "student_id": student_id,
                "first_name": first_name,
                "last_name": last_name
            },
            card_filename=card_filename,
            avatar_path=avatar_path
        )
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/student-card/<filename>')
def get_student_card(filename):
    try:
        return send_from_directory(TMP_DIR, filename)
    except Exception as e:
        return f"Error serving card: {e}", 404

@app.route('/cardtest')
def cardtest():
    try:
        import traceback
        # Generate Vietnamese names (no accents, Title Case)
        vn_surnames = ['Nguyen','Tran','Le','Pham','Hoang','Huynh','Phan','Vu','Vo','Dang',
                       'Bui','Do','Ho','Ngo','Duong','Ly','Truong','Dinh','Lam','Mai']
        vn_middle_names = ['Van','Thi','Minh','Hoang','Duc','Thanh','Quoc','Ngoc','Anh','Tuan',
                           'Huu','Dinh','Xuan','Hong','Kim','Phuong','Bao','Quang','Hai','Duy']
        vn_first_names = ['An','Binh','Cuong','Dung','Em','Giang','Hai','Hung','Khanh','Linh',
                          'Long','Mai','Nam','Ngoc','Phuong','Quang','Son','Tam','Tuan','Vy']
        surname = random.choice(vn_surnames)
        middle = random.choice(vn_middle_names)
        first = random.choice(vn_first_names)
        first_name = f"{middle} {first}"  # Middle + First
        last_name = surname  # Surname
        full_name = f"{surname} {middle} {first}"  # Vietnamese format: Ho Ten Dem Ten
        # DOB (18-23 years old)
        from datetime import datetime
        current_year = datetime.now().year
        birth_year = random.randint(current_year - 23, current_year - 18)
        birth_date = f"{birth_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        student_id = f"{random.randint(10000000, 99999999)}"  # 8 random digits
        student_card_info = {
            'name': full_name,  # American name: First Last
            'first_name': first_name,
            'last_name': last_name,
            'birth_date': birth_date.replace('-', '.'),
            'student_id': student_id
        }
        avatar_path = get_random_avatar()
        card = create_student_card(student_card_info, avatar_path)
        if not card:
            return "Failed to create card", 500
        filename = f"cardtest_{student_id}.jpg"
        save_path = os.path.join(TMP_DIR, filename)
        card_to_save = card.convert('RGB') if card.mode in ('RGBA','LA') else card
        card_to_save.save(save_path, 'JPEG')
        # Simple HTML preview (plain)
        import time
        img_url = f"/student-card/{filename}?v={int(time.time())}"
        html = f"""
<!DOCTYPE html>
<html lang=\"vi\"><head><meta charset=\"utf-8\"><title>Card Test</title>
<style>body{{font-family:sans-serif;padding:24px;background:#111;color:#eee}} .wrap{{max-width:980px;margin:0 auto}} img{{max-width:100%;border-radius:12px;border:2px solid #333}} .meta{{margin:12px 0 20px;opacity:.9}} a.btn{{display:inline-block;margin-top:12px;padding:10px 16px;background:#2563eb;color:#fff;border-radius:10px;text-decoration:none}}</style>
</head><body><div class=\"wrap\">
  <h2>Card Test Preview</h2>
  <div class=\"meta\">Template: <code>{os.path.basename(UK_TEMPLATE)}</code> · Name: <code>{(student_card_info.get('first_name','') + ' ' + student_card_info.get('last_name','')).strip().replace(',', ' ').lower()}</code> · DOB: <code>{student_card_info['birth_date']}</code></div>
  <img src=\"{img_url}\" alt=\"student card\" />
  <div><a class=\"btn\" href=\"/cardtest\">Generate Another</a></div>
</div></body></html>
"""
        return html
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Cardtest error: {e}")
        print(error_trace)
        return f"Error: {e}<br><pre>{error_trace}</pre>", 500

@app.route('/cardtest2')
def cardtest2():
    """Test route for teacher card generation"""
    try:
        # Generate teacher name (US style for ChatGPT Teacher) - Expanded list
        first_names = [
            # Female names
            'Sarah','Emily','Jessica','Ashley','Jennifer','Amanda','Melissa','Nicole','Stephanie','Rebecca',
            'Rachel','Laura','Michelle','Elizabeth','Amy','Kimberly','Lisa','Angela','Heather','Samantha',
            'Katherine','Christina','Lauren','Megan','Brittany','Danielle','Christine','Kelly','Victoria','Amber',
            'Mary','Patricia','Linda','Barbara','Susan','Karen','Nancy','Betty','Margaret','Sandra',
            'Dorothy','Carol','Ruth','Sharon','Deborah','Cynthia','Donna','Janet','Catherine','Virginia',
            'Pamela','Debra','Maria','Carolyn','Brenda','Anna','Emma','Olivia','Sophia','Isabella',
            'Ava','Mia','Charlotte','Abigail','Harper','Evelyn','Grace','Lily','Hannah','Madison',
            # Male names
            'Michael','Christopher','Matthew','Joshua','David','Daniel','Andrew','James','Justin','Joseph',
            'Ryan','Robert','Brian','John','William','Brandon','Kevin','Jason','Thomas','Nicholas',
            'Eric','Richard','Charles','Mark','Donald','Paul','Steven','Kenneth','George','Edward',
            'Timothy','Ronald','Anthony','Kevin','Jeffrey','Jacob','Gary','Raymond','Dennis','Jerry',
            'Frank','Scott','Stephen','Larry','Benjamin','Samuel','Patrick','Alexander','Jack','Henry',
            'Noah','Liam','Ethan','Lucas','Mason','Logan','Oliver','Elijah','Aiden','Jackson'
        ]
        
        last_names = [
            'Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Rodriguez','Martinez',
            'Hernandez','Lopez','Gonzalez','Wilson','Anderson','Thomas','Taylor','Moore','Jackson','Martin',
            'Lee','Thompson','White','Harris','Sanchez','Clark','Ramirez','Lewis','Robinson','Walker',
            'Young','Allen','King','Wright','Scott','Torres','Nguyen','Hill','Flores','Green',
            'Adams','Nelson','Baker','Hall','Rivera','Campbell','Mitchell','Carter','Roberts','Phillips',
            'Evans','Turner','Parker','Collins','Edwards','Stewart','Morris','Murphy','Cook','Rogers',
            'Morgan','Peterson','Cooper','Reed','Bailey','Bell','Gomez','Kelly','Howard','Ward',
            'Cox','Richardson','Wood','Watson','Brooks','Bennett','Gray','James','Reyes','Cruz',
            'Hughes','Price','Myers','Long','Foster','Sanders','Ross','Morales','Powell','Sullivan'
        ]
        
        first_name = random.choice(first_names)
        last_name = random.choice([l for l in last_names if l.lower() != first_name.lower()])
        
        # Teacher ID (7 random digits for teachers)
        teacher_id = f"{random.randint(1000000, 9999999)}"
        
        teacher_card_info = {
            'name': f"{last_name} {first_name}",
            'first_name': first_name,
            'last_name': last_name,
            'birth_date': '',  # No birth date for teachers
            'teacher_id': teacher_id
        }
        
        avatar_path = get_random_avatar()
        card = create_teacher_card(teacher_card_info, avatar_path, template_path=TEACHER_TEMPLATE)
        
        if not card:
            return "Failed to create teacher card", 500
        
        filename = f"teachertest_{teacher_id}.jpg"
        save_path = os.path.join(TMP_DIR, filename)
        card_to_save = card.convert('RGB') if card.mode in ('RGBA','LA') else card
        card_to_save.save(save_path, 'JPEG')
        
        # Simple HTML preview
        import time
        img_url = f"/student-card/{filename}?v={int(time.time())}"
        html = f"""
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Teacher Card Test</title>
<style>body{{font-family:sans-serif;padding:24px;background:#111;color:#eee}} .wrap{{max-width:980px;margin:0 auto}} img{{max-width:100%;border-radius:12px;border:2px solid #333}} .meta{{margin:12px 0 20px;opacity:.9;background:#1a1a1a;padding:12px;border-radius:8px}} .badge{{display:inline-block;padding:4px 8px;background:#2563eb;border-radius:4px;font-size:12px;margin-right:8px}} a.btn{{display:inline-block;margin-top:12px;padding:10px 16px;background:#2563eb;color:#fff;border-radius:10px;text-decoration:none;margin-right:8px}} a.btn:hover{{background:#1d4ed8}}</style>
</head><body><div class="wrap">
  <h2>🎓 Teacher Card Test Preview</h2>
  <div class="meta">
    <span class="badge">TEACHER</span>
    <strong>Template:</strong> <code>{os.path.basename(TEACHER_TEMPLATE)}</code> · 
    <strong>Name:</strong> <code>{teacher_card_info.get('name', '')}</code> · 
    <strong>ID:</strong> <code>{teacher_id}</code> · 
    <strong>Birth Date:</strong> <code>N/A (Teacher)</code>
  </div>
  <img src="{img_url}" alt="teacher card" />
  <div>
    <a class="btn" href="/cardtest2">🔄 Generate Another Teacher</a>
    <a class="btn" href="/cardtest" style="background:#059669">👨‍🎓 Student Card Test</a>
  </div>
</div></body></html>
"""
        return html
    except Exception as e:
        import traceback
        return f"Error: {e}<br><pre>{traceback.format_exc()}</pre>", 500

@app.route('/api/job-status')
def get_job_status():
    """Get job status for Telegram users"""
    try:
        job_id = request.args.get('job_id')
        if not job_id:
            return jsonify(success=False, error='Missing job_id parameter'), 400
        
        # Connect to database
        import sqlite3
        conn = sqlite3.connect("/tmp/sheerid_bot.db")
        cursor = conn.cursor()
        
        # Get job info
        cursor.execute('''
            SELECT j., u.telegram_id, u.username, u.first_name, u.last_name
            FROM verification_jobs j
            JOIN users u ON j.user_id = u.id
            WHERE j.job_id = ?
        ''', (job_id,))
        
        job = cursor.fetchone()
        conn.close()
        
        if not job:
            return jsonify(success=False, error='Job not found'), 404
        
        # Parse job data
        job_data = {
            'job_id': job[1],
            'user_id': job[2],
            'sheerid_url': job[3],
            'status': job[4],
            'student_info': json.loads(job[5]) if job[5] else None,
            'card_filename': job[6],
            'upload_result': json.loads(job[7]) if job[7] else None,
            'created_at': job[8],
            'completed_at': job[9],
            'user': {
                'telegram_id': job[10],
                'username': job[11],
                'first_name': job[12],
                'last_name': job[13]
            }
        }
        
        return jsonify(success=True, job=job_data)
        
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/create-payment-qr', methods=['POST'])
def create_payment_qr():
    """Create VietQR payment QR code"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['telegram_id', 'coins', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        telegram_id = data['telegram_id']
        coins = int(data['coins'])
        amount = int(data['amount'])
        
        # Validate amounts
        if coins < 10 or coins > 1000:
            return jsonify({'success': False, 'error': 'Invalid coin amount'}), 400
        
        expected_amount = coins * 1000  # 1 xu = 1000 VNĐ
        if amount != expected_amount:
            return jsonify({'success': False, 'error': 'Amount mismatch'}), 400
        
        # Generate transaction ID
        import uuid
        transaction_id = f"TXN_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        # MB Bank configuration
        bank_id = "970422"  # MB Bank
        account_number = "188299299"
        account_name = "PHAN QUOC DANG QUANG"
        description = f"SheerID Bot - {coins} xu - {transaction_id}"
        
        qr_content = f"{bank_id}|{account_number}|{account_name}|{amount}|{description}"
        
        # Store pending payment in memory (for Vercel serverless)
        # In production, you would use a proper database like PostgreSQL
        from datetime import datetime, timedelta
        now = datetime.now()
        expires_at = now + timedelta(minutes=15)  # QR expires in 15 minutes
        
        # For now, we'll simulate the database operation
        # In a real implementation, you'd store this in a database
        payment_data = {
            'transaction_id': transaction_id,
            'telegram_id': telegram_id,
            'coins': coins,
            'amount': amount,
            'qr_content': qr_content,
            'status': 'pending',
            'created_at': now.isoformat(),
            'expires_at': expires_at.isoformat()
        }
        
        # Store in a simple file-based storage (temporary solution)
        import json
        
        # Create pending_payments directory if not exists
        os.makedirs('/tmp/pending_payments', exist_ok=True)
        
        # Save payment data to file
        payment_file = f'/tmp/pending_payments/{transaction_id}.json'
        with open(payment_file, 'w') as f:
            json.dump(payment_data, f)
        
        return jsonify({
            'success': True,
            'transaction_id': transaction_id,
            'qr_content': qr_content,
            'amount': amount,
            'coins': coins,
            'expires_at': expires_at.isoformat(),
            'qr_url': f"https://img.vietqr.io/image/{bank_id}-{account_number}-compact2.jpg?amount={amount}&addInfo={description}"
        })
        
    except Exception as e:
        print(f"Create payment QR error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/process-payment', methods=['POST'])
def process_payment():
    """Process payment and add coins to user account"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['telegram_id', 'coins', 'amount', 'transaction_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        telegram_id = data['telegram_id']
        coins = int(data['coins'])
        amount = int(data['amount'])
        transaction_id = data['transaction_id']
        
        # Validate amounts
        if coins < 10 or coins > 1000:
            return jsonify({'success': False, 'error': 'Invalid coin amount'}), 400
        
        expected_amount = coins * 1000  # 1 xu = 1000 VNĐ
        if amount != expected_amount:
            return jsonify({'success': False, 'error': 'Amount mismatch'}), 400
        
        # Get user from database
        import sqlite3
        DB_PATH = '/tmp/sheerid_bot.db'
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT  FROM users WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Check if transaction already processed
        cursor.execute('''
            SELECT COUNT() FROM transactions 
            WHERE description LIKE ? AND type = 'deposit'
        ''', (f'%{transaction_id}%',))
        
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Transaction already processed'}), 400
        
        # Add coins to user account
        cursor.execute('UPDATE users SET coins = coins + ? WHERE id = ?', (coins, user[0]))
        
        # Add transaction record
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, description, job_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user[0], 'deposit', coins, f'Nạp {coins} xu - Transaction ID: {transaction_id}', None, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Send confirmation message via Telegram
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if bot_token:
            message = f"""
✅ Nạp xu thành công!

💰 Số xu nạp: {coins}
🪙 Tổng xu: {user[5] + coins}
🆔 Transaction ID: {transaction_id}

💡 Sử dụng /verify <URL> để xác minh SheerID
❓ Hỗ trợ: @meepzizhere
            """
            
            try:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                data = {
                    'chat_id': telegram_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                }
                requests.post(url, data=data, timeout=30)
            except Exception as e:
                print(f"Error sending Telegram message: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Payment processed successfully',
            'coins_added': coins,
            'new_balance': user[5] + coins
        })
        
    except Exception as e:
        print(f"Payment processing error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/sepay-webhook', methods=['POST'])
@app.route('/api/sepay-webhook', methods=['POST'])  # Alias for new webhook URL
def sepay_webhook():
    """Webhook to receive payment notifications from SePay"""
    try:
        data = request.get_json()
        
        # Log webhook data for debugging
        print(f"=== SEPAY WEBHOOK RECEIVED ===")
        print(f"Raw data: {data}")
        
        # Extract payment information from SePay webhook (official format)
        # According to https://docs.sepay.vn/lap-trinh-webhooks.html
        gateway = data.get('gateway', '')
        transaction_date = data.get('transactionDate', '')
        account_number = data.get('accountNumber', '')
        sub_account = data.get('subAccount', '')
        transfer_type = data.get('transferType', '')  # 'in' or 'out'
        transfer_amount = data.get('transferAmount', 0)
        accumulated = data.get('accumulated', 0)
        code = data.get('code', '')
        transaction_content = data.get('content', '')
        reference_number = data.get('referenceCode', '')
        body = data.get('description', '')
        
        print(f"SePay webhook details:")
        print(f"  Gateway: {gateway}")
        print(f"  Transaction Date: {transaction_date}")
        print(f"  Account Number: {account_number}")
        print(f"  Sub Account (VA): {sub_account}")
        print(f"  Transfer Type: {transfer_type}")
        print(f"  Transfer Amount: {transfer_amount}")
        print(f"  Transaction Content: {transaction_content}")
        print(f"  Code: {code}")
        print(f"  Reference Number: {reference_number}")
        
        # Validate Virtual Account
        # Sepay sends VA in 'subAccount' field, not 'accountNumber'
        expected_va = "VQRQAHGFY9482"
        if sub_account != expected_va:
            print(f"❌ Wrong Virtual Account: {sub_account} (expected: {expected_va})")
            return jsonify({'success': False, 'error': f'Wrong Virtual Account'}), 400
        
        print(f"✅ Valid Virtual Account: {sub_account}")
        
        # Only process incoming transactions
        if transfer_type != 'in':
            print(f"❌ Not an incoming transaction: {transfer_type}")
            return jsonify({'success': False, 'error': 'Not an incoming transaction'}), 400
        
        # Check if using virtual account (VQRQAHGFY9482)
        # For Virtual Account, transaction code is in 'code' field
        telegram_id = None
        
        # Extract telegram ID from transaction code (DQ + Telegram ID format)
        # Code can be in 'code' field or 'content' field
        transaction_code = code or transaction_content
        
        if not transaction_code:
            print(f"❌ No transaction code found")
            return jsonify({'success': False, 'error': 'No transaction code'}), 400
        
        # Parse DQ code
        if transaction_code.startswith('DQ'):
            telegram_id_str = transaction_code[2:]  # Remove 'DQ' prefix
        else:
            # Try to find DQ in content
            import re
            match = re.search(r'DQ(\d{10,12})', transaction_code, re.IGNORECASE)
            if match:
                telegram_id_str = match.group(1)
            else:
                print(f"❌ Invalid transaction code format: {transaction_code}")
                return jsonify({'success': False, 'error': 'Invalid transaction code format'}), 400
        
        try:
            telegram_id = int(telegram_id_str)
        except ValueError:
            print(f"❌ Invalid telegram ID: {telegram_id_str}")
            return jsonify({'success': False, 'error': 'Invalid telegram ID'}), 400
    
        print(f"👤 Processing payment for telegram ID: {telegram_id}")
        
        # Calculate coins based on amount (1 xu = 1000 VNĐ)
        coins = transfer_amount // 1000
        
        # AUTO BONUS: 10% bonus for deposits over 20,000 VND from MBBank
        bonus_applied = False
        if transfer_amount >= 20000 and 'MB' in gateway.upper():
            bonus_coins = int(coins * 0.1)  # 10% bonus
            coins += bonus_coins
            bonus_applied = True
            print(f"🎁 BONUS APPLIED: +{bonus_coins} coins (10% bonus for {transfer_amount:,} VND from {gateway})")
        
        if coins < 10 or coins > 1000:
            print(f"❌ Invalid coin amount: {coins}")
            return jsonify({'success': False, 'error': 'Invalid coin amount'}), 400
        
        # Find user by telegram_id directly from Supabase
        print(f"🔍 Attempting to get user from Supabase: {telegram_id}")
        print(f"🔍 SUPABASE_AVAILABLE in webhook: {SUPABASE_AVAILABLE}")
        user = get_user_from_supabase(str(telegram_id))
        
        if not user:
            print(f"❌ User not found with telegram_id: {telegram_id}")
            print(f"💡 Attempting to sync with Telegram bot database...")
            
            # Try to find user in Telegram bot database and sync
            try:
                # Check if user exists in Telegram bot database (file-based)
                telegram_user = find_user_in_telegram_database(str(telegram_id))
                
                if telegram_user:
                    print(f"✅ Found user in Telegram database, syncing...")
                    # Sync user from Telegram database (file) to Supabase
                    user = sync_user_from_telegram_database(telegram_user)
                else:
                    print(f"❌ User not found in Telegram database either")
                    print(f"💡 User must run /start command first to create account")
                    return jsonify({'success': False, 'error': 'User not found. Please run /start command first.'}), 404
                    
            except Exception as e:
                print(f"❌ Error syncing user: {e}")
                return jsonify({'success': False, 'error': f'Failed to sync user: {str(e)}'}), 500
        
        # Nạp vào CASH thay vì Xu
        try:
            from .supabase_client import adjust_user_cash_by_telegram_id
            new_cash = adjust_user_cash_by_telegram_id(str(telegram_id), coins, tx_type='deposit_cash', description=f'SePay: {transaction_content}')
            success = new_cash is not None
        except Exception as e:
            print(f"❌ Error adjusting CASH: {e}")
            success = False
        
        if not success:
            print(f"❌ Failed to add coins to user {telegram_id}")
            return jsonify({'success': False, 'error': 'Failed to add coins'}), 500
        
        # Get updated user data after adding cash
        updated_user = get_user_from_supabase(str(telegram_id))
        if not updated_user:
            print(f"❌ Could not get updated user data for {telegram_id}")
            return jsonify({'success': False, 'error': 'Could not get updated user data'}), 500
        
        # Send confirmation message via Telegram
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        print(f"🤖 Bot token available: {bot_token is not None}")
        
        if bot_token:
            # Get current user cash from updated user data
            current_cash = updated_user.get('cash', 0) if isinstance(updated_user, dict) else 0
            
            # Build message with bonus info if applicable
            bonus_text = ""
            if bonus_applied:
                base_coins = transfer_amount // 1000
                bonus_coins = coins - base_coins
                bonus_text = f"\n🎁 Bonus 10%: +{bonus_coins} cash (nạp trên 20k từ MBBank)"
            
            message = f"""✅ Nạp tiền thành công!

💵 Cash cộng thêm: {coins}{bonus_text}
💰 Tổng CASH: {current_cash}
💵 Số tiền: {transfer_amount:,} VNĐ
📝 Nội dung: {transaction_content}
🆔 Mã TT: {code}
⏰ Thời gian: {transaction_date}

💡 Sử dụng /verify <URL> để xác minh SheerID
❓ Hỗ trợ: @meepzizhere"""
        
            try:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                data = {
                    'chat_id': telegram_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                }
                response = requests.post(url, data=data, timeout=30)
                print(f"📱 Telegram message sent: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"❌ Error sending Telegram message: {e}")
        else:
            print("❌ TELEGRAM_BOT_TOKEN not found!")
        
        print(f"✅ Payment processed successfully for user {telegram_id}: +{coins} CASH")
        
        # Send group notification
        bonus_info = ""
        if bonus_applied:
            base_coins = transfer_amount // 1000
            bonus_coins = coins - base_coins
            bonus_info = f"\n🎁 **Bonus:** +{bonus_coins} cash (10% cho nạp trên 20k từ MBBank)"
        
        group_message = f"""🔔 **WEBHOOK** - 💰 {transfer_amount:,} VNĐ

✅ **Giao dịch thành công:**
• Cash cộng thêm: {coins}{bonus_info}
• User ID: `{telegram_id}`
• Mã TT: {code}
• Thời gian: {transaction_date}
• Nội dung: `{transaction_content}`

🤖 **Bot:** SheerID Auto Verify"""
        
        send_telegram_group_notification(group_message)
        
        return jsonify({
            'success': True, 
            'message': 'Payment processed successfully', 
            'coins_added': coins, 
            'total_coins': updated_user.get('coins', 0),
            'user_id': telegram_id,
            'code': code
        }), 200  # Return 200 status code as required by SePay

    except Exception as e:
        print(f"❌ Payment webhook error: {e}")
        import traceback
        traceback.print_exc()
        
        # Send error notification to group
        error_message = f"""🚨 **WEBHOOK ERROR**

❌ **Lỗi xử lý webhook:**
• Lỗi: `{str(e)}`
• Thời gian: {format_vietnam_time()}
• Webhook: SePay Payment

🔧 **Cần kiểm tra:**
• Logs Vercel
• Database connection
• SePay API status

🤖 **Bot:** SheerID Auto Verify"""
        
        send_telegram_group_notification(error_message)
        
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/check-payment-status/<transaction_id>', methods=['GET'])
def check_payment_status(transaction_id):
    """Check payment status for a transaction"""
    try:
        import json
        
        payment_file = f'/tmp/pending_payments/{transaction_id}.json'
        
        if not os.path.exists(payment_file):
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404
        
        with open(payment_file, 'r') as f:
            payment_data = json.load(f)
        
        return jsonify({
            'success': True,
            'status': payment_data['status'],
            'coins': payment_data['coins'],
            'amount': payment_data['amount'],
            'created_at': payment_data['created_at'],
            'expires_at': payment_data['expires_at']
        })
        
    except Exception as e:
        print(f"Check payment status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def verify_sepay_signature(signature, payload):
    """Verify SePay webhook signature"""
    try:
        import hmac
        import hashlib
        import base64
        
        # Get secret key from environment or config
        secret_key = os.getenv('SEPAY_WEBHOOK_SECRET')
        
        if not signature or not secret_key:
            return False
        
        # Create expected signature
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        print(f"Error verifying signature: {e}")
        return False

def verify_payos_signature(signature, payload):
    """Verify PayOS webhook signature"""
    try:
        import hmac
        import hashlib
        import base64
        
        # Get secret key from environment or config
        secret_key = os.getenv('PAYOS_WEBHOOK_SECRET')
        
        if not signature or not secret_key:
            return False
        
        # Create expected signature
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        print(f"Error verifying signature: {e}")
        return False

def verify_vietqr_signature(signature, payload):
    """Verify VietQR webhook signature (legacy)"""
    return verify_payos_signature(signature, payload)

def find_transaction_by_user_id(user_id, amount):
    """Find transaction by user ID and amount"""
    try:
        import json
        import glob
        
        # Search in pending payments directory
        pending_dir = '/tmp/pending_payments'
        if not os.path.exists(pending_dir):
            return None
        
        # Get all payment files
        payment_files = glob.glob(f'{pending_dir}/.json')
        
        for payment_file in payment_files:
            try:
                with open(payment_file, 'r') as f:
                    payment_data = json.load(f)
                
                # Check if user ID and amount match
                if (payment_data.get('telegram_id') == int(user_id) and 
                    payment_data.get('amount') == amount and 
                    payment_data.get('status') == 'pending'):
                    return payment_data.get('transaction_id')
                    
            except Exception as e:
                print(f"Error reading payment file {payment_file}: {e}")
                continue
        
        return None
        
    except Exception as e:
        print(f"Error finding transaction by user ID: {e}")
        return None

def get_db_connection():
    """Get database connection"""
    import sqlite3
    
    try:
        # Database path (same as Telegram bot)
        DB_PATH = '/tmp/sheerid_bot.db'
        
        # Debug: Check if database file exists
        print(f"🔍 Database path: {DB_PATH}")
        print(f"📁 Database exists: {os.path.exists(DB_PATH)}")
        
        # For Vercel serverless, try to use persistent storage
        # Check if we're in Vercel environment
        if os.environ.get('VERCEL'):
            # Use /tmp directory but with better persistence
            DB_PATH = '/tmp/sheerid_bot.db'
            print(f"🔧 Vercel environment detected, using: {DB_PATH}")
        
        # Create connection (will create database if not exists)
        conn = sqlite3.connect(DB_PATH)
        
        # Create tables if they don't exist (for Vercel serverless)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                coins INTEGER DEFAULT 0,
                is_vip BOOLEAN DEFAULT 0,
                vip_expiry DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(255) UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                sheerid_url TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                student_info TEXT,
                card_filename VARCHAR(255),
                upload_result TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type VARCHAR(50),
                amount INTEGER,
                coins INTEGER,
                description TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                job_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create bot_settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key VARCHAR(255) UNIQUE NOT NULL,
                value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        print(f"✅ Database tables created/verified")
        
        return conn
        
    except Exception as e:
        print(f"❌ Error creating database connection: {e}")
        return None

# Global user cache to persist data between function calls
USER_CACHE = {}

def get_user_by_telegram_id(telegram_id):
    """Get user by telegram_id from SQLite"""
    try:
        print(f"🔍 Getting user by telegram_id from SQLite: {telegram_id}")
        
        conn = get_db_connection()
        if not conn:
            print("❌ Cannot connect to database")
            return None
        
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("❌ Users table does not exist")
            conn.close()
            return None
        
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (str(telegram_id),))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            user = {
                'id': user_data[0],
                'telegram_id': str(user_data[1]),
                'username': user_data[2],
                'first_name': user_data[3],
                'last_name': user_data[4],
                'coins': user_data[5],
                'is_vip': bool(user_data[6]),
                'vip_expiry': user_data[7],
                'created_at': user_data[8],
                'updated_at': user_data[9]
            }
            
            # Auto-check VIP expiry and revoke if expired
            if user['is_vip'] and user['vip_expiry']:
                try:
                    from datetime import datetime
                    expiry = datetime.fromisoformat(user['vip_expiry'].replace('Z', '+00:00')) if isinstance(user['vip_expiry'], str) else user['vip_expiry']
                    if expiry and datetime.now(expiry.tzinfo if expiry.tzinfo else None) > expiry:
                        print(f"⏰ VIP expired for user {telegram_id}, auto-revoking...")
                        # Revoke VIP
                        conn2 = get_db_connection()
                        if conn2:
                            cursor2 = conn2.cursor()
                            cursor2.execute('UPDATE users SET is_vip = 0, vip_expiry = NULL WHERE telegram_id = ?', (str(telegram_id),))
                            conn2.commit()
                            conn2.close()
                            user['is_vip'] = False
                            user['vip_expiry'] = None
                            print(f"✅ VIP revoked for user {telegram_id}")
                except Exception as vip_err:
                    print(f"⚠️ Error checking VIP expiry: {vip_err}")
            
            print(f"👤 User found in SQLite: {user}")

            # Cache the data
            USER_CACHE[telegram_id] = user

            return (
                user['id'],
                user['telegram_id'],
                user['username'],
                user['first_name'],
                user['last_name'],
                user['coins'],
                user['is_vip'],
                user['vip_expiry'],
                user['created_at']
            )
        else:
            print(f"❌ User {telegram_id} not found in SQLite - User must run /start command first")
            return None

    except Exception as e:
        print(f"❌ Error getting user from SQLite: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_user_by_id(user_id):
    """Get user by ID from SQLite"""
    try:
        print(f"🔍 Getting user by ID from SQLite: {user_id}")
        
        conn = get_db_connection()
        if not conn:
            print("❌ Cannot connect to database")
            return None
        
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("❌ Users table does not exist")
            conn.close()
            return None
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (int(user_id),))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            user = {
                'id': user_data[0],
                'telegram_id': str(user_data[1]),
                'username': user_data[2],
                'first_name': user_data[3],
                'last_name': user_data[4],
                'coins': user_data[5],
                'is_vip': bool(user_data[6]),
                'vip_expiry': user_data[7],
                'created_at': user_data[8],
                'updated_at': user_data[9]
            }
            print(f"👤 User found in SQLite: {user}")

            # Cache the data
            USER_CACHE[user_id] = user

            return (
                user['id'],
                user['telegram_id'],
                user['username'],
                user['first_name'],
                user['last_name'],
                user['coins'],
                user['is_vip'],
                user['vip_expiry'],
                user['created_at']
            )
        else:
            print(f"❌ User {user_id} not found in SQLite - User must run /start command first")
            return None

    except Exception as e:
        print(f"❌ Error getting user from SQLite: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_user_from_telegram(telegram_id, username, first_name, last_name):
    """Create user from Telegram data"""
    try:
        print(f"👤 Creating new user from Telegram data: {telegram_id}")
        
        # File path for user data
        user_file = f'/tmp/user_{telegram_id}.json'
        
        # Create new user with Telegram data
        user_data = {
            'id': 1,
            'telegram_id': telegram_id,
            'username': username or 'user',
            'first_name': first_name or 'User',
            'last_name': last_name or '',
            'coins': 0,
            'is_vip': 0,
            'vip_expiry': None,
            'created_at': datetime.now().isoformat()
        }
        
        # Save user data
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ User created: {user_data}")
        return (
            user_data.get('id', 1),
            user_data.get('telegram_id', telegram_id),
            user_data.get('username', 'user'),
            user_data.get('first_name', 'User'),
            user_data.get('last_name', ''),
            user_data.get('coins', 0),
            user_data.get('is_vip', 0),
            user_data.get('vip_expiry'),
            user_data.get('created_at', '2025-09-21T00:00:00')
        )
        
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        import traceback
        traceback.print_exc()
        return None

def add_coins_to_user(telegram_id, coins, transaction_info=""):
    """Add coins to user account in SQLite"""
    try:
        print(f"💰 Adding {coins} coins to user {telegram_id}")
        
        conn = get_db_connection()
        if not conn:
            print("❌ Cannot connect to database")
            return False
        
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("❌ Users table does not exist")
            conn.close()
            return False
        
        # Get current user data
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (str(telegram_id),))
        user_data = cursor.fetchone()
        
        if not user_data:
            print(f"❌ User {telegram_id} not found in SQLite")
            conn.close()
            return False
        
        current_coins = user_data[5]  # coins column
        new_coins = current_coins + coins
        
        # Update coins in SQLite
        cursor.execute('''
            UPDATE users 
            SET coins = ?, updated_at = ?
            WHERE telegram_id = ?
        ''', (new_coins, datetime.now().isoformat(), str(telegram_id)))
        
        # Insert transaction record
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, coins, description, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_data[0], 'deposit', coins * 1000, coins, transaction_info, 'completed', datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Clear cache to force fresh data on next request
        if telegram_id in USER_CACHE:
            del USER_CACHE[telegram_id]
            print(f"🗑️ Cleared cache for user {telegram_id}")
        
        # Update cache with fresh data
        user = {
            'id': user_data[0],
            'telegram_id': str(user_data[1]),
            'username': user_data[2],
            'first_name': user_data[3],
            'last_name': user_data[4],
            'coins': new_coins,
            'is_vip': bool(user_data[6]),
            'vip_expiry': user_data[7],
            'created_at': user_data[8],
            'updated_at': datetime.now().isoformat()
        }
        USER_CACHE[telegram_id] = user
        
        print(f"✅ Added {coins} coins to user {telegram_id}. New balance: {new_coins}")
        return True
        
    except Exception as e:
        print(f"❌ Error adding coins: {e}")
        import traceback
        traceback.print_exc()
        return False

# Function already defined above, removing duplicate

# Function already defined above, removing duplicate

def send_telegram_message(chat_id, message):
    """Send message to Telegram"""
    try:
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print(f"Would send message to {chat_id}: {message}")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, data=data, timeout=30)
        print(f"Telegram message sent: {response.status_code} - {response.text}")
        return response.status_code == 200
        
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return False

def send_telegram_group_notification(message):
    """Send notification to Telegram group for webhook monitoring"""
    try:
        # Get group chat ID from environment variable or use default
        group_chat_id = os.environ.get('TELEGRAM_GROUP_CHAT_ID', '-4845312032')
        if not group_chat_id:
            print("⚠️ TELEGRAM_GROUP_CHAT_ID not set, skipping group notification")
            return False
        
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print("❌ TELEGRAM_BOT_TOKEN not found!")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': group_chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, data=data, timeout=30)
        if response.status_code == 200:
            print(f"✅ Group notification sent to: {group_chat_id}")
            return True
        else:
            print(f"❌ Failed to send group notification: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending group notification: {e}")
        return False

def find_user_in_telegram_database(telegram_id):
    """Find user in Telegram bot database by checking file-based storage"""
    try:
        print(f"🔍 Searching for user {telegram_id} in Telegram database...")
        
        # Check if user file exists in /tmp directory
        user_file = f"/tmp/user_{telegram_id}.json"
        if os.path.exists(user_file):
            with open(user_file, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
                print(f"✅ Found user in Telegram database: {user_data}")
                return user_data
        else:
            print(f"❌ User file not found: {user_file}")
            return None
            
    except Exception as e:
        print(f"❌ Error finding user in Telegram database: {e}")
        return None

def sync_user_from_telegram_database(telegram_user):
    """Sync user from Telegram database to SePay database"""
    try:
        print(f"🔄 Syncing user from Telegram database...")
        
        conn = sqlite3.connect('/tmp/sheerid_bot.db')
        cursor = conn.cursor()
        
        # Create tables if not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                coins INTEGER DEFAULT 0,
                is_vip BOOLEAN DEFAULT 0,
                vip_expiry DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(255) UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                sheerid_url TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                student_info TEXT,
                card_filename VARCHAR(255),
                upload_result TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type VARCHAR(50),
                amount INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 0,
                description TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                job_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Insert or update user with data from Telegram database
        cursor.execute('''
            INSERT OR REPLACE INTO users (telegram_id, username, first_name, last_name, coins, is_vip, vip_expiry, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            telegram_user.get('telegram_id'),
            telegram_user.get('username'),
            telegram_user.get('first_name'),
            telegram_user.get('last_name'),
            telegram_user.get('coins', 0),
            telegram_user.get('is_vip', False),
            telegram_user.get('vip_expiry'),
            telegram_user.get('created_at'),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ User synced successfully from Telegram database")
        
        # Return user data in the format expected by the rest of the code
        return get_user_by_telegram_id(str(telegram_user.get('telegram_id')))
        
    except Exception as e:
        print(f"❌ Error syncing user from Telegram database: {e}")
        return None

def sync_coins_to_telegram_file(telegram_id):
    """Sync updated coins back to Telegram database file"""
    try:
        print(f"🔄 Syncing coins to Telegram file for user {telegram_id}...")
        
        # Get updated user data from SePay database
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            print(f"❌ User not found in SePay database: {telegram_id}")
            return False
        
        # Convert tuple to dict format
        user_data = {
            'id': user[0],
            'telegram_id': str(user[1]),
            'username': user[2],
            'first_name': user[3],
            'last_name': user[4],
            'coins': user[5],
            'is_vip': bool(user[6]),
            'vip_expiry': user[7],
            'created_at': user[8],
            'updated_at': datetime.now().isoformat()
        }
        
        # Update Telegram database file
        user_file = f"/tmp/user_{telegram_id}.json"
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Coins synced to Telegram file: {user_data['coins']} xu")
        return True
        
    except Exception as e:
        print(f"❌ Error syncing coins to Telegram file: {e}")
        return False

@app.route('/check-transaction', methods=['POST'])
def check_transaction():
    """Check and process transaction manually"""
    try:
        data = request.get_json()
        
        # Get parameters
        user_id = data.get('user_id')
        amount = data.get('amount')  # VNĐ
        description = data.get('description', '')
        
        if not user_id or not amount:
            return jsonify({'success': False, 'error': 'Missing user_id or amount'}), 400
        
        # Calculate coins (1 xu = 1000 VNĐ)
        coins = amount // 1000
        
        if coins < 10 or coins > 1000:
            return jsonify({'success': False, 'error': 'Invalid amount'}), 400
        
        # Check if user exists
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Add coins to user
        success = add_coins_to_user(user_id, coins, f"Manual check: {description}")
        
        if success:
            # Send confirmation message
            message = f"""✅ Xác nhận nạp xu thủ công

💰 Số xu nạp: {coins}
🪙 Tổng xu: {user[5] + coins} xu
💵 Số tiền: {amount:,} VNĐ
📝 Mô tả: {description}
⏰ Thời gian: {format_vietnam_time('%H:%M:%S %d/%m/%Y')}

💡 Sử dụng /verify <URL> để xác minh SheerID
❓ Hỗ trợ: @meepzizhere"""
            
            send_telegram_message(user_id, message)
            
            return jsonify({
                'success': True,
                'message': 'Transaction processed successfully',
                'coins_added': coins,
                'new_balance': user[5] + coins
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to add coins'}), 500
            
    except Exception as e:
        print(f"Error checking transaction: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get-user-info/<int:user_id>', methods=['GET'])
def get_user_info(user_id):
    """Get user information"""
    try:
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': {
                'id': user[1],
                'name': user[2],
                'username': user[3],
                'coins': user[5],
                'vip': user[6],
                'joined': user[7]
            }
        })
        
    except Exception as e:
        print(f"Error getting user info: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/check-database', methods=['GET'])
def check_database():
    """DISABLED DUE TO SECURITY VULNERABILITY
    
    This endpoint was exposing sensitive information or allowing
    unauthorized actions without proper authentication.
    
    Disabled: 2026-03-03
    Incident: Security audit after hack incident
    """
    return jsonify({
        'error': 'This endpoint has been permanently disabled for security reasons',
        'code': 'ENDPOINT_DISABLED'
    }), 403

@app.route('/check-user/<telegram_id>', methods=['GET'])
def check_user(telegram_id):
    """Check specific user by telegram_id"""
    try:
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': {
                'id': user[0],
                'telegram_id': user[1],
                'username': user[2],
                'first_name': user[3],
                'last_name': user[4],
                'coins': user[5],
                'is_vip': user[6],
                'vip_expiry': user[7],
                'created_at': user[8]
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/test-group', methods=['GET'])
def test_group():
    """DISABLED DUE TO SECURITY VULNERABILITY
    
    This endpoint was exposing sensitive information or allowing
    unauthorized actions without proper authentication.
    
    Disabled: 2026-03-03
    Incident: Security audit after hack incident
    """
    return jsonify({
        'error': 'This endpoint has been permanently disabled for security reasons',
        'code': 'ENDPOINT_DISABLED'
    }), 403

@app.route('/clear-all-users', methods=['POST'])
def clear_all_users():
    """DISABLED DUE TO SECURITY VULNERABILITY
    
    This endpoint was exposing sensitive information or allowing
    unauthorized actions without proper authentication.
    
    Disabled: 2026-03-03
    Incident: Security audit after hack incident
    """
    return jsonify({
        'error': 'This endpoint has been permanently disabled for security reasons',
        'code': 'ENDPOINT_DISABLED'
    }), 403

@app.route('/daily-notification', methods=['POST'])
def trigger_daily_notification():
    """Trigger daily notification manually"""
    try:
        print("🌅 Manual daily notification triggered")
        
        # Import the function from telegram.py
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from telegram import send_daily_notification
        
        # Send daily notification
        success = send_daily_notification()
        
        if success:
            return jsonify({'success': True, 'message': 'Daily notification sent successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send daily notification'})
            
    except Exception as e:
        print(f"❌ Error in daily notification: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/cron/daily-notification', methods=['GET', 'POST'])
def cron_daily_notification():
    """Cron job endpoint for daily notification at 9 AM"""
    try:
        print("🌅 Cron daily notification triggered")
        
        # Import the function from telegram.py
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from telegram import send_daily_notification
        
        # Send daily notification
        success = send_daily_notification()
        
        if success:
            print("✅ Daily notification cron job completed successfully")
            return jsonify({'success': True, 'message': 'Daily notification sent successfully'})
        else:
            print("❌ Daily notification cron job failed")
            return jsonify({'success': False, 'message': 'Failed to send daily notification'})
            
    except Exception as e:
        print(f"❌ Error in cron daily notification: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/fix-maintenance-now', methods=['GET', 'POST'])
def fix_maintenance_now():
    """Fix maintenance configuration immediately"""
    from .fix_maintenance_now import handler
    return handler(request)


@app.route('/cron/poll-binance-deposits', methods=['GET', 'POST'])
def cron_poll_binance_deposits():
    """
    Cron job to poll Binance deposits and auto-credit users
    Should be called every 30-60 seconds
    """
    try:
        import os
        from .binance_auto_deposit import check_binance_deposits, get_deposit_addresses
        
        # Debug: Check if API credentials are available
        api_key = os.getenv('BINANCE_API_KEY', '')
        api_secret = os.getenv('BINANCE_API_SECRET', '')
        
        print(f"🔍 Polling Binance deposits...")
        print(f"   API Key: {'SET' if api_key else 'NOT SET'} ({len(api_key)} chars)")
        print(f"   API Secret: {'SET' if api_secret else 'NOT SET'} ({len(api_secret)} chars)")
        
        result = check_binance_deposits()
        
        return jsonify({
            'success': True,
            'result': result,
            'addresses': get_deposit_addresses(),
            'debug': {
                'api_key_set': bool(api_key),
                'api_secret_set': bool(api_secret)
            }
        })
        
    except Exception as e:
        print(f"❌ Error polling Binance deposits: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/cron/retention-checks', methods=['GET', 'POST'])
def cron_retention_checks():
    """
    Cron job to process scheduled retention checks
    Should be called every 15 minutes
    """
    try:
        import asyncio
        from datetime import datetime
        from .services.monitoring import MonitoringService
        
        print(f"🕐 Retention checks cron triggered at {datetime.now().isoformat()}")
        
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        service = MonitoringService()
        results = loop.run_until_complete(service.process_scheduled_checks())
        
        loop.close()
        
        # Calculate summary
        total_checks = len(results)
        gold_active = sum(1 for r in results if r.get('gold_active') is True)
        gold_lost = sum(1 for r in results if r.get('gold_lost') is True)
        errors = sum(1 for r in results if r.get('gold_active') is None)
        
        print(f"✅ Processed {total_checks} checks: {gold_active} active, {gold_lost} lost, {errors} errors")
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'checks_processed': total_checks,
            'summary': {
                'gold_active': gold_active,
                'gold_lost': gold_lost,
                'errors': errors
            },
            'results': results
        })
        
    except Exception as e:
        print(f"❌ Error in retention checks cron: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/cron/token-health-updates', methods=['GET', 'POST'])
def cron_token_health_updates():
    """
    Cron job to update token health metrics and status
    Should be called every hour
    """
    try:
        import asyncio
        from datetime import datetime
        from .services.token_health import TokenHealthService
        
        print(f"🕐 Token health update cron triggered at {datetime.now().isoformat()}")
        
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        service = TokenHealthService()
        
        # Get all tokens and their health metrics
        health_reports = loop.run_until_complete(service.get_token_health_report())
        
        if not health_reports:
            loop.close()
            return jsonify({
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'tokens_processed': 0,
                    'tokens_updated': 0,
                    'degraded_tokens': 0,
                    'failed_tokens': 0,
                    'healthy_tokens': 0
                },
                'status_changes': [],
                'health_reports': []
            })
        
        # Update token status based on retention rates
        updated_count = 0
        degraded_count = 0
        failed_count = 0
        status_changes = []
        
        for report in health_reports:
            token_id = report['id']
            current_status = report['status']
            retention_24h = report['retention_rate_24h']
            
            # Determine new status based on retention rate
            # Requirement 2.4: retention < 80% = degraded
            # Requirement 2.5: retention < 50% = failed
            new_status = None
            
            if retention_24h < 50.0:
                new_status = 'failed'
                failed_count += 1
            elif retention_24h < 80.0:
                new_status = 'degraded'
                degraded_count += 1
            elif current_status != 'healthy':
                # Token has recovered
                new_status = 'healthy'
            
            # Update status if changed
            if new_status and new_status != current_status:
                reason = f"24h retention rate: {retention_24h:.1f}%"
                success = loop.run_until_complete(service.mark_token_status(token_id, new_status, reason))
                if success:
                    updated_count += 1
                    status_changes.append({
                        'token_id': token_id,
                        'old_status': current_status,
                        'new_status': new_status,
                        'retention_24h': retention_24h,
                        'reason': reason
                    })
        
        loop.close()
        
        # Count healthy tokens
        healthy_count = len(health_reports) - degraded_count - failed_count
        
        print(f"✅ Processed {len(health_reports)} tokens: "
              f"{healthy_count} healthy, "
              f"{degraded_count} degraded, "
              f"{failed_count} failed")
        
        if updated_count > 0:
            print(f"⚠️  Updated {updated_count} token statuses")
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'tokens_processed': len(health_reports),
                'tokens_updated': updated_count,
                'degraded_tokens': degraded_count,
                'failed_tokens': failed_count,
                'healthy_tokens': healthy_count
            },
            'status_changes': status_changes,
            'health_reports': health_reports
        })
        
    except Exception as e:
        print(f"❌ Error in token health update cron: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/binance-deposit-addresses', methods=['GET'])
def get_binance_deposit_addresses():
    """Get Binance deposit addresses for display"""
    try:
        from .binance_auto_deposit import get_deposit_addresses
        addresses = get_deposit_addresses()
        return jsonify({
            'success': True,
            'addresses': addresses
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/process-pending-deposit', methods=['POST'])
def process_pending_deposit():
    """
    Manually process a pending deposit (for admin)
    Used when user forgot to include memo
    """
    try:
        data = request.get_json()
        tx_id = data.get('transaction_id')
        telegram_id = data.get('telegram_id')
        
        if not tx_id or not telegram_id:
            return jsonify({'success': False, 'error': 'Missing transaction_id or telegram_id'}), 400
        
        from .supabase_client import get_supabase_client
        client = get_supabase_client()
        if not client:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        # Get pending deposit
        deposit = client.table('binance_deposits').select('*').eq('transaction_id', tx_id).execute()
        if not deposit.data:
            return jsonify({'success': False, 'error': 'Deposit not found'}), 404
        
        deposit_data = deposit.data[0]
        if deposit_data.get('status') == 'completed':
            return jsonify({'success': False, 'error': 'Deposit already processed'}), 400
        
        # Get amount and calculate CASH
        import os
        usdt_amount = float(deposit_data.get('amount', 0))
        usdt_rate = float(os.getenv('USDT_TO_CASH_RATE', '25'))
        cash_amount = int(usdt_amount * usdt_rate)
        
        # Add cash to user
        from .binance_auto_deposit import get_auto_deposit
        auto_deposit = get_auto_deposit()
        success = auto_deposit._add_cash_to_user(telegram_id, cash_amount, tx_id, usdt_amount, 'MANUAL')
        
        if success:
            # Update deposit record
            client.table('binance_deposits').update({
                'telegram_id': str(telegram_id),
                'status': 'completed',
                'processed_at': datetime.now().isoformat()
            }).eq('transaction_id', tx_id).execute()
            
            # Notify user
            auto_deposit._notify_user(telegram_id, usdt_amount, cash_amount, tx_id, 'MANUAL')
            
            return jsonify({
                'success': True,
                'message': f'Added {cash_amount} CASH to user {telegram_id}'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to add cash'}), 500
        
    except Exception as e:
        print(f"❌ Error processing pending deposit: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

def send_success_notification_for_job(job_id):
    """Send success notification for a completed verification job - DISABLED to prevent duplicates"""
    try:
        print(f"🔇 DISABLED: send_success_notification_for_job for job {job_id} - notification handled by process_completed_job_charging")
        return True  # Return True to indicate "success" but don't actually send
        
        # DISABLED CODE BELOW - All notifications are now handled by process_completed_job_charging
        print(f"📨 Preparing success notification for job {job_id}")
        
        # Get job details from Supabase
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            print("❌ Could not get Supabase client for notification")
            return False
        
        # Get job data
        job_response = supabase.table('verification_jobs').select('*').eq('job_id', job_id).execute()
        if not job_response.data:
            print(f"❌ Job {job_id} not found for notification")
            return False
        
        job_data = job_response.data[0]
        user_id = job_data.get('user_id')
        
        if not user_id:
            print(f"❌ No user_id found for job {job_id}")
            return False
        
        # Get user data to determine VIP status and payment info
        user_response = supabase.table('users').select('*').eq('id', user_id).execute()
        if not user_response.data:
            print(f"❌ User not found for job {job_id}")
            return False
        
        user = user_response.data[0]
        telegram_id = user.get('telegram_id')
        
        if not telegram_id:
            print(f"❌ No telegram_id found for user {user_id}")
            return False
        is_vip = user.get('is_vip', False)
        coins = user.get('coins', 0)
        cash = user.get('cash', 0)
        user_lang = user.get('language', 'vi')  # Get user language
        
        # Determine payment message
        if is_vip:
            payment_message = "VIP - không trừ phí"
        else:
            # Check if cash or coins were deducted by looking at recent transactions
            try:
                from datetime import datetime, timedelta
                recent_time = (datetime.now() - timedelta(minutes=5)).isoformat()
                tx_response = supabase.table('transactions').select('*').eq('user_id', user_id).eq('type', 'verify').gte('created_at', recent_time).order('created_at', desc=True).limit(1).execute()
                
                if tx_response.data:
                    tx = tx_response.data[0]
                    if tx.get('amount', 0) == -10000:  # Cash deduction
                        payment_message = f"10 CASH (còn lại: {cash})"
                    else:  # Coins deduction
                        payment_message = f"10 xu (còn lại: {coins})"
                else:
                    payment_message = f"10 xu (còn lại: {coins})"
            except Exception as e:
                print(f"⚠️ Could not determine payment method: {e}")
                payment_message = f"10 xu (còn lại: {coins})"
        
        # Check if notification already sent (using global set)
        notification_key = f"notif_{job_id}"
        if notification_key in NOTIFIED_JOBS:
            print(f"⚠️ Notification already sent for job {job_id}")
            return True
        
        # Send notification
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print("❌ TELEGRAM_BOT_TOKEN not found")
            return False
        
        # Use multilingual message
        text_message = get_success_message_multilingual(job_id, payment_message, is_vip, cash, coins, user_lang)
        
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": str(telegram_id),
                "text": text_message,
                "parse_mode": "Markdown"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            # Mark notification as sent
            NOTIFIED_JOBS.add(notification_key)
            print(f"✅ Success notification sent to user {telegram_id} for job {job_id}")
            return True
        else:
            print(f"❌ Failed to send notification: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending success notification for job {job_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


# Register admin routes for dashboard
try:
    from .admin_routes import register_admin_routes
    register_admin_routes(app)
    print("✅ Admin routes registered successfully")
except Exception as e:
    print(f"⚠️ Failed to register admin routes: {e}")


# ============================================
# FALLBACK ROUTE FOR RECENT PURCHASES
# This ensures the route works even if blueprint fails
# ============================================
@app.route('/api/locket/recent-purchases', methods=['GET'])
def fallback_recent_purchases():
    """
    Fallback route for recent purchases if blueprint fails to load
    Returns fake purchase data for social proof
    """
    import random
    
    fake_usernames = [
        '***nhi', '***ung', '***inh', '***yen', '***thu',
        '***mai', '***lan', '***hoa', '***nga', '***han',
        '***son', '***tuan', '***long', '***nam', '***duc',
        '***kha', '***minh', '***phat', '***khoa', '***bao'
    ]
    
    packages = ['Gói 1 tháng', 'Gói 5 tháng', 'Gói 12 tháng']
    
    purchases = []
    
    for i in range(15):
        minutes_ago = random.randint(5, 180)
        hours_ago = int(minutes_ago / 60)
        
        if hours_ago < 1:
            time_display = f'{minutes_ago} phút trước'
        else:
            time_display = f'{hours_ago} giờ trước'
        
        purchases.append({
            'username': random.choice(fake_usernames),
            'package': random.choice(packages),
            'time': time_display
        })
    
    return jsonify({
        'success': True,
        'purchases': purchases
    })

print("✅ Fallback recent-purchases route registered")

# ============================================
# FALLBACK ROUTE FOR LOCKET ACTIVATION
# This ensures the route works even if blueprint fails
# ============================================
@app.route('/api/locket/activate', methods=['POST', 'OPTIONS'])
def fallback_locket_activate():
    """
    Fallback route for locket activation if blueprint fails to load
    """
    print("🔥 [FALLBACK] Activate endpoint called")
    
    # Handle OPTIONS for CORS
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response, 200
    
    try:
        # Try to import and call the actual function from locket_web
        from .locket_web import activate_locket as locket_activate_func
        print("✅ [FALLBACK] Imported activate_locket from locket_web")
        return locket_activate_func()
    except Exception as e:
        print(f"❌ [FALLBACK] Error importing from locket_web: {e}")
        import traceback
        traceback.print_exc()
        # Return error response
        response = jsonify({
            'success': False,
            'message': f'Lỗi hệ thống: {str(e)}'
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500

print("✅ Fallback locket-activate route registered")

# ============================================
# FALLBACK ROUTE FOR LOCKET CHECK
# ============================================
@app.route('/api/locket/check', methods=['POST', 'OPTIONS'])
def fallback_locket_check():
    """
    Fallback route for locket check if blueprint fails to load
    """
    print("🔥 [FALLBACK] Check endpoint called")
    
    # Handle OPTIONS for CORS
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response, 200
    
    try:
        # Try to import and call the actual function from locket_web
        from .locket_web import check_locket_username
        print("✅ [FALLBACK] Imported check_locket_username from locket_web")
        return check_locket_username()
    except Exception as e:
        print(f"❌ [FALLBACK] Error importing from locket_web: {e}")
        import traceback
        traceback.print_exc()
        # Return error response
        response = jsonify({
            'success': False,
            'message': f'Lỗi hệ thống: {str(e)}'
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500

print("✅ Fallback locket-check route registered")
