"""
Browserless.io client for SheerID verification
Connects to cloud browser to bypass fraud detection
"""
import os
import random
import asyncio
from playwright.async_api import async_playwright

# Browserless.io config - Multiple API keys for rotation
BROWSERLESS_API_KEYS = [
    os.environ.get('BROWSERLESS_API_KEY', ''),
    os.environ.get('BROWSERLESS_API_KEY_2', ''),
    os.environ.get('BROWSERLESS_API_KEY_3', ''),
    os.environ.get('BROWSERLESS_API_KEY_4', ''),
    os.environ.get('BROWSERLESS_API_KEY_5', ''),
    os.environ.get('BROWSERLESS_API_KEY_6', ''),
]
# Filter out empty keys
BROWSERLESS_API_KEYS = [k for k in BROWSERLESS_API_KEYS if k]

# Track current key index for round-robin rotation
_current_key_index = 0

def get_browserless_url():
    """Get Browserless URL with rotating API key (round-robin)"""
    global _current_key_index
    
    if not BROWSERLESS_API_KEYS:
        print("⚠️ No Browserless API keys configured!")
        return None
    
    # Get current key and rotate to next
    api_key = BROWSERLESS_API_KEYS[_current_key_index]
    key_num = _current_key_index + 1
    
    # Rotate to next key (round-robin)
    _current_key_index = (_current_key_index + 1) % len(BROWSERLESS_API_KEYS)
    
    print(f"🔑 Using Browserless API key #{key_num}/{len(BROWSERLESS_API_KEYS)}")
    
    # Production endpoint with stealth mode
    return f"wss://production-sfo.browserless.io?token={api_key}&stealth"

def get_random_browserless_url():
    """Get Browserless URL with random API key selection"""
    if not BROWSERLESS_API_KEYS:
        print("⚠️ No Browserless API keys configured!")
        return None
    
    api_key = random.choice(BROWSERLESS_API_KEYS)
    key_index = BROWSERLESS_API_KEYS.index(api_key) + 1
    
    print(f"🔑 Using random Browserless API key #{key_index}/{len(BROWSERLESS_API_KEYS)}")
    
    return f"wss://production-sfo.browserless.io?token={api_key}&stealth"

# Legacy single key support (fallback)
BROWSERLESS_API_KEY = os.environ.get('BROWSERLESS_API_KEY', '')
BROWSERLESS_URL = f"wss://production-sfo.browserless.io?token={BROWSERLESS_API_KEY}&stealth"

# Test data - US names
FIRST_NAMES = ["Sarah", "Michael", "Jennifer", "David", "Amanda", "Robert", "Emily", "James", "Jessica", "Christopher", "Ashley", "Matthew", "Stephanie", "Andrew", "Nicole"]
LAST_NAMES = ["Smith", "Williams", "Brown", "Davis", "Wilson", "Johnson", "Miller", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson"]
EMAIL_DOMAINS = ["outlook.com", "yahoo.com", "hotmail.com", "icloud.com", "gmail.com"]

# High Schools for random selection - must match highschools_config.js
HIGH_SCHOOLS = [
    {"id": 11455510, "name": "Discovery Education", "city": "Springfield", "state": "VA"},
    {"id": 4508226, "name": "De La Salle High School", "city": "Concord", "state": "CA"},
    {"id": 4669179, "name": "De Paul Catholic High School", "city": "Wayne", "state": "NJ"},
    {"id": 225592, "name": "De Soto High School", "city": "De Soto", "state": "KS"},
    {"id": 3997849, "name": "De Pere High", "city": "De Pere", "state": "WI"},
    {"id": 4000803, "name": "De Anza High", "city": "Richmond", "state": "CA"},
    {"id": 4508228, "name": "De Smet Jesuit High School", "city": "St. Louis", "state": "MO"},
    {"id": 3994116, "name": "Clearview Regional High School", "city": "Mullica Hill", "state": "NJ"},
    {"id": 177729, "name": "Mullins High School", "city": "Mullins", "state": "SC"},
    {"id": 4012207, "name": "Mullins High", "city": "Mullins", "state": "SC"},
]


def get_random_school():
    """Get a random school from the list"""
    return random.choice(HIGH_SCHOOLS)


def generate_random_data():
    """Generate random user data for verification"""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    email_domain = random.choice(EMAIL_DOMAINS)
    email = f"{first_name.lower()}.{last_name.lower()}.{random.randint(100, 999)}@{email_domain}"
    return {
        "first_name": first_name,
        "last_name": last_name,
        "email": email
    }



async def verify_with_browserless(verification_url: str, school_name: str = None):
    """
    Run SheerID verification using Browserless.io cloud browser
    
    Args:
        verification_url: SheerID verification URL
        school_name: School to search for (if None, random school is selected)
        
    Returns:
        dict with success status and details
    """
    if not BROWSERLESS_API_KEY:
        return {"success": False, "error": "BROWSERLESS_API_KEY not configured"}
    
    # Select random school if not provided
    if school_name is None:
        selected_school = get_random_school()
        school_name = selected_school["name"]
        school_id = selected_school["id"]
    else:
        # Find school by name or use first match
        selected_school = next((s for s in HIGH_SCHOOLS if school_name.lower() in s["name"].lower()), HIGH_SCHOOLS[0])
        school_id = selected_school["id"]
    
    user_data = generate_random_data()
    result = {
        "success": False,
        "user_data": user_data,
        "school": school_name,
        "school_id": school_id,
        "error": None,
        "step": None
    }
    
    print(f"🎓 Selected school: {school_name} (ID: {school_id})")
    
    async with async_playwright() as p:
        browser = None
        try:
            # Get rotating Browserless URL
            browserless_url = get_browserless_url()
            if not browserless_url:
                return {"success": False, "error": "No Browserless API keys configured"}
            
            print(f"🔗 Connecting to Browserless.io...")
            # Connect to Browserless.io cloud browser with timeout
            browser = await p.chromium.connect_over_cdp(
                browserless_url,
                timeout=60000
            )
            print(f"✅ Connected to cloud browser")
            
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
            )
            
            page = await context.new_page()
            page.set_default_timeout(60000)  # 60s timeout for all operations
            
            # Remove webdriver detection
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
            """)
            
            # Navigate to verification page
            print(f"📄 Loading verification page...")
            await page.goto(verification_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # Wait for JS to load
            print(f"✅ Page loaded")
            
            # Wait for form to be ready
            print(f"⏳ Waiting for form...")
            await page.wait_for_selector('#sid-teacher-school, input[name="organization"]', timeout=30000)
            print(f"✅ Form ready")
            
            # Fill School first - FAST mode to avoid timeout
            print(f"📝 Filling school: {school_name}...")
            school_input = page.locator('#sid-teacher-school')
            await school_input.click()
            # Type first few characters of school name for autocomplete
            search_term = school_name[:15] if len(school_name) > 15 else school_name
            await school_input.fill(search_term)
            await asyncio.sleep(1.5)  # Wait for autocomplete
            
            # Select from dropdown
            try:
                option = page.locator('[role="option"], [role="listbox"] li').first
                await option.click()
            except:
                await school_input.press("ArrowDown")
                await school_input.press("Enter")
            
            await asyncio.sleep(0.5)
            print(f"✅ School selected")
            
            # Fill First Name - FAST
            print(f"📝 Filling name and email...")
            first_input = page.locator('#sid-first-name')
            await first_input.fill(user_data["first_name"])
            
            # Fill Last Name - FAST
            last_input = page.locator('#sid-last-name')
            await last_input.fill(user_data["last_name"])
            
            # Fill Email - FAST
            email_input = page.locator('#sid-email')
            await email_input.fill(user_data["email"])
            
            await asyncio.sleep(0.5)
            print(f"✅ Form filled")
            
            # Click Submit
            print(f"🚀 Submitting...")
            submit_btn = page.locator('button[type="submit"]').first
            await submit_btn.click()
            
            # Wait for response and page navigation
            await asyncio.sleep(5)
            
            # Check result
            page_content = await page.content()
            page_url = page.url
            
            print(f"📍 Current URL: {page_url}")
            
            if "docUpload" in page_content or "upload" in page_url.lower() or "document" in page_content.lower():
                result["success"] = True
                result["step"] = "docUpload"
                result["current_url"] = page_url
                
                # Extract verificationId from URL or page
                import re
                vid_match = re.search(r'verificationId=([a-f0-9]+)', page_url)
                if vid_match:
                    result["verification_id"] = vid_match.group(1)
                else:
                    # Try to find in page content
                    vid_match = re.search(r'"verificationId"\s*:\s*"([a-f0-9]+)"', page_content)
                    if vid_match:
                        result["verification_id"] = vid_match.group(1)
                
                print(f"✅ Bypass successful! VerificationId: {result.get('verification_id')}")
                
            elif "fraud" in page_content.lower() or "unable to verify" in page_content.lower():
                result["error"] = "fraudRulesReject"
                result["step"] = "rejected"
            else:
                result["step"] = "unknown"
                result["error"] = "Unknown result"
                result["current_url"] = page_url
            
            if browser:
                await browser.close()
            
        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Error: {e}")
            if browser:
                try:
                    await browser.close()
                except:
                    pass
    
    return result


def verify_sync(verification_url: str, school_name: str = None):
    """Synchronous wrapper for verify_with_browserless"""
    return asyncio.run(verify_with_browserless(verification_url, school_name))


async def bypass_and_get_upload_url(verification_url: str, school_name: str = None):
    """
    Bypass fraud detection and return the docUpload URL for Vercel to continue
    
    Flow:
    1. Browserless fills form and submits (random school if not provided)
    2. SheerID accepts (no fraud reject)
    3. Returns verification_id for Vercel to upload document via API
    
    Args:
        verification_url: Initial SheerID verification URL
        school_name: School name to fill (if None, random school is selected)
        
    Returns:
        dict with:
        - success: bool
        - verification_id: str (for API upload)
        - user_data: dict (name, email used)
        - school: str (school name used)
        - school_id: int (school ID for paystub)
        - error: str if failed
    """
    result = await verify_with_browserless(verification_url, school_name)
    
    if result["success"] and result.get("verification_id"):
        # Return data needed for Vercel to upload document
        return {
            "success": True,
            "verification_id": result["verification_id"],
            "user_data": result["user_data"],
            "school": result["school"],
            "school_id": result.get("school_id"),
            "upload_url": result.get("current_url"),
            "message": "Fraud bypass successful. Ready for document upload."
        }
    else:
        return {
            "success": False,
            "error": result.get("error", "Unknown error"),
            "step": result.get("step"),
            "user_data": result.get("user_data"),
            "school": result.get("school")
        }


def bypass_fraud_sync(verification_url: str, school_name: str = "Pasadena Independent School District"):
    """Synchronous wrapper for bypass_and_get_upload_url"""
    return asyncio.run(bypass_and_get_upload_url(verification_url, school_name))


import httpx
import base64

async def upload_document_after_bypass(verification_id: str, document_base64: str, document_type: str = "image/png"):
    """
    Upload document to SheerID after fraud bypass
    
    Args:
        verification_id: The verification ID from bypass step
        document_base64: Base64 encoded document image
        document_type: MIME type (image/png, image/jpeg, application/pdf)
        
    Returns:
        dict with upload result
    """
    upload_url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}/step/docUpload"
    
    # Decode base64 to bytes
    try:
        document_bytes = base64.b64decode(document_base64)
    except Exception as e:
        return {"success": False, "error": f"Invalid base64: {e}"}
    
    # Prepare multipart form data
    files = {
        "file": ("document.png", document_bytes, document_type)
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Origin": "https://services.sheerid.com",
        "Referer": f"https://services.sheerid.com/verify/?verificationId={verification_id}"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(upload_url, files=files, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "verification_id": verification_id,
                    "response": data,
                    "current_step": data.get("currentStep"),
                    "status": data.get("status")
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response_text": response.text[:500]
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


async def full_teacher_verification(verification_url: str, document_base64: str, school_name: str = "Pasadena Independent School District"):
    """
    Complete teacher verification flow:
    1. Bypass fraud detection with Browserless
    2. Upload document via API
    
    Args:
        verification_url: Initial SheerID URL
        document_base64: Base64 encoded document
        school_name: School name
        
    Returns:
        dict with full verification result
    """
    # Step 1: Bypass fraud
    bypass_result = await bypass_and_get_upload_url(verification_url, school_name)
    
    if not bypass_result["success"]:
        return {
            "success": False,
            "step": "fraud_bypass",
            "error": bypass_result.get("error"),
            "user_data": bypass_result.get("user_data")
        }
    
    verification_id = bypass_result["verification_id"]
    
    # Step 2: Upload document
    upload_result = await upload_document_after_bypass(verification_id, document_base64)
    
    if not upload_result["success"]:
        return {
            "success": False,
            "step": "doc_upload",
            "error": upload_result.get("error"),
            "verification_id": verification_id,
            "user_data": bypass_result["user_data"]
        }
    
    return {
        "success": True,
        "verification_id": verification_id,
        "user_data": bypass_result["user_data"],
        "school": school_name,
        "upload_response": upload_result.get("response"),
        "current_step": upload_result.get("current_step"),
        "status": upload_result.get("status")
    }


def full_verification_sync(verification_url: str, document_base64: str, school_name: str = "Pasadena Independent School District"):
    """Synchronous wrapper for full_teacher_verification"""
    return asyncio.run(full_teacher_verification(verification_url, document_base64, school_name))


# ============================================================
# STUDENT VERIFICATION WITH BROWSERLESS + PROXY
# ============================================================

# Import universities config for student verification
try:
    from .universities_config import (
        UNIVERSITIES, 
        FIRST_NAMES as UNI_FIRST_NAMES, 
        LAST_NAMES as UNI_LAST_NAMES,
        get_random_university,
        get_random_student_name,
        get_random_dob
    )
    UNIVERSITIES_AVAILABLE = True
except ImportError:
    UNIVERSITIES_AVAILABLE = False
    UNIVERSITIES = []
    UNI_FIRST_NAMES = FIRST_NAMES
    UNI_LAST_NAMES = LAST_NAMES
    print("⚠️ universities_config not available, using default names")


def get_proxy_config():
    """Get proxy configuration from environment variables"""
    proxy_host = os.environ.get('SCRAPE_PROXY_HOST', 'rp.scrapegw.com')
    proxy_port = os.environ.get('SCRAPE_PROXY_PORT', '6060')
    proxy_user = os.environ.get('SCRAPE_PROXY_USER', '')
    proxy_pass = os.environ.get('SCRAPE_PROXY_PASS', '')
    
    if proxy_user and proxy_pass:
        return {
            "server": f"http://{proxy_host}:{proxy_port}",
            "username": proxy_user,
            "password": proxy_pass
        }
    return None


def generate_student_data():
    """Generate random student data for verification"""
    if UNIVERSITIES_AVAILABLE:
        name = get_random_student_name()
        first_name = name["first_name"]
        last_name = name["last_name"]
    else:
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
    
    email_domain = random.choice(EMAIL_DOMAINS)
    email = f"{first_name.lower()}.{last_name.lower()}.{random.randint(100, 999)}@{email_domain}"
    
    # Generate birth date (age 19-25)
    from datetime import datetime, timedelta
    today = datetime.now()
    min_age = 19
    max_age = 25
    age = random.randint(min_age, max_age)
    birth_year = today.year - age
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    birth_date = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"  # YYYY-MM-DD format
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "birth_date": birth_date
    }


def get_random_university_for_student():
    """Get a random university from universities_config"""
    if UNIVERSITIES_AVAILABLE and UNIVERSITIES:
        return random.choice(UNIVERSITIES)
    # Fallback to Art Institute universities
    return {
        "id": 8961,
        "idExtended": "8961",
        "name": "The Art Institute of Austin",
        "city": "Austin",
        "state": "TX",
        "country": "US"
    }


async def verify_student_with_browserless(verification_url: str, use_proxy: bool = True):
    """
    Run SheerID STUDENT verification using Browserless.io cloud browser with proxy
    
    Flow:
    1. Connect to Browserless with rotating API key
    2. Use proxy for US IP
    3. Fill form with random university, name, DOB
    4. Submit form
    5. Close browser immediately after submit (don't wait for result)
    6. Return university and student data for host to continue
    
    Args:
        verification_url: SheerID verification URL
        use_proxy: Whether to use proxy (default True)
        
    Returns:
        dict with:
        - success: bool
        - verification_id: str
        - university: dict (id, name, city, state)
        - student_data: dict (first_name, last_name, email, birth_date)
        - error: str if failed
    """
    # Get rotating Browserless URL
    browserless_url = get_browserless_url()
    if not browserless_url:
        return {"success": False, "error": "No Browserless API keys configured"}
    
    # Select random university
    university = get_random_university_for_student()
    student_data = generate_student_data()
    
    result = {
        "success": False,
        "university": university,
        "student_data": student_data,
        "verification_id": None,
        "error": None,
        "step": None
    }
    
    print(f"🎓 Student Verification with Browserless")
    print(f"   University: {university['name']} ({university.get('city', '')}, {university.get('state', '')})")
    print(f"   Student: {student_data['first_name']} {student_data['last_name']}")
    print(f"   DOB: {student_data['birth_date']}")
    
    async with async_playwright() as p:
        browser = None
        try:
            # Get proxy config
            proxy_config = get_proxy_config() if use_proxy else None
            
            print(f"🔗 Connecting to Browserless.io...")
            if proxy_config:
                print(f"🌐 Using proxy: {proxy_config['server']}")
            
            # Connect to Browserless.io cloud browser
            browser = await p.chromium.connect_over_cdp(
                browserless_url,
                timeout=60000
            )
            print(f"✅ Connected to cloud browser")
            
            # Create context with proxy if available
            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "locale": "en-US",
                "timezone_id": "America/New_York",
            }
            
            if proxy_config:
                context_options["proxy"] = proxy_config
            
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            page.set_default_timeout(60000)
            
            # Remove webdriver detection
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
            """)
            
            # Navigate to verification page
            print(f"📄 Loading verification page...")
            await page.goto(verification_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)
            print(f"✅ Page loaded")
            
            # Extract verification_id from URL before filling form
            import re
            vid_match = re.search(r'verificationId=([a-f0-9]+)', verification_url)
            if vid_match:
                result["verification_id"] = vid_match.group(1)
                print(f"📋 Extracted verification_id from URL: {result['verification_id']}")
            
            # Wait for form to be ready - student form has different selectors
            print(f"⏳ Waiting for student form...")
            try:
                await page.wait_for_selector('#sid-organization, input[name="organization"], #sid-first-name', timeout=30000)
            except:
                # Try alternative selectors
                await page.wait_for_selector('input[type="text"]', timeout=30000)
            print(f"✅ Form ready")
            
            # Fill University/Organization
            print(f"📝 Filling university: {university['name']}...")
            try:
                # Try different selectors for organization input
                org_selectors = ['#sid-organization', 'input[name="organization"]', '[data-testid="organization-input"]']
                org_input = None
                for selector in org_selectors:
                    try:
                        org_input = page.locator(selector)
                        if await org_input.count() > 0:
                            break
                    except:
                        continue
                
                if org_input and await org_input.count() > 0:
                    await org_input.click()
                    # Type first part of university name for autocomplete
                    search_term = university['name'][:20] if len(university['name']) > 20 else university['name']
                    await org_input.fill(search_term)
                    await asyncio.sleep(2)  # Wait for autocomplete
                    
                    # Select from dropdown
                    try:
                        option = page.locator('[role="option"], [role="listbox"] li, .sid-org-option').first
                        await option.click()
                    except:
                        await org_input.press("ArrowDown")
                        await org_input.press("Enter")
                    
                    await asyncio.sleep(0.5)
                    print(f"✅ University selected")
            except Exception as e:
                print(f"⚠️ Error filling university: {e}")
            
            # Fill First Name
            print(f"📝 Filling student info...")
            try:
                first_input = page.locator('#sid-first-name, input[name="firstName"]').first
                await first_input.fill(student_data["first_name"])
            except Exception as e:
                print(f"⚠️ Error filling first name: {e}")
            
            # Fill Last Name
            try:
                last_input = page.locator('#sid-last-name, input[name="lastName"]').first
                await last_input.fill(student_data["last_name"])
            except Exception as e:
                print(f"⚠️ Error filling last name: {e}")
            
            # Fill Birth Date
            try:
                # Try different date input formats
                dob_input = page.locator('#sid-birth-date, input[name="birthDate"], input[type="date"]').first
                if await dob_input.count() > 0:
                    await dob_input.fill(student_data["birth_date"])
            except Exception as e:
                print(f"⚠️ Error filling birth date: {e}")
            
            # Fill Email
            try:
                email_input = page.locator('#sid-email, input[name="email"]').first
                await email_input.fill(student_data["email"])
            except Exception as e:
                print(f"⚠️ Error filling email: {e}")
            
            await asyncio.sleep(1)
            print(f"✅ Form filled")
            
            # Click Submit
            print(f"🚀 Submitting form...")
            try:
                submit_btn = page.locator('button[type="submit"], .sid-submit-btn, button:has-text("Verify")').first
                await submit_btn.click()
            except Exception as e:
                print(f"⚠️ Error clicking submit: {e}")
            
            # Wait briefly for form submission to process (3 seconds max)
            await asyncio.sleep(3)
            
            # Quick check for immediate fraud rejection
            page_content = await page.content()
            page_url = page.url
            
            print(f"📍 Current URL after submit: {page_url}")
            
            # Check for fraud rejection
            if "fraud" in page_content.lower() or "unable to verify" in page_content.lower():
                result["error"] = "fraudRulesReject"
                result["step"] = "rejected"
                print(f"❌ Fraud detection triggered")
            else:
                # Form submitted successfully - assume it will go to docUpload
                # Extract verification_id from new URL if available
                vid_match = re.search(r'verificationId=([a-f0-9]+)', page_url)
                if vid_match:
                    result["verification_id"] = vid_match.group(1)
                elif not result["verification_id"]:
                    # Try to find in page content
                    vid_match = re.search(r'"verificationId"\s*:\s*"([a-f0-9]+)"', page_content)
                    if vid_match:
                        result["verification_id"] = vid_match.group(1)
                
                # Mark as success - host will handle the rest
                result["success"] = True
                result["step"] = "submitted"
                result["current_url"] = page_url
                print(f"✅ Form submitted successfully!")
                print(f"   VerificationId: {result.get('verification_id')}")
                print(f"🔌 Closing browser - host will continue with transcript generation and upload")
            
            # Close browser immediately
            if browser:
                await browser.close()
                print(f"✅ Browser closed")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Error: {e}")
            if browser:
                try:
                    await browser.close()
                except:
                    pass
    
    return result


def verify_student_sync(verification_url: str, use_proxy: bool = True):
    """Synchronous wrapper for verify_student_with_browserless"""
    return asyncio.run(verify_student_with_browserless(verification_url, use_proxy))


async def student_bypass_and_get_data(verification_url: str, use_proxy: bool = True):
    """
    Bypass fraud detection for STUDENT verification and return data for transcript generation
    
    Flow:
    1. Browserless fills form with random university, name, DOB
    2. SheerID accepts (no fraud reject)
    3. Returns verification_id + university + student data
    4. Host can then generate transcript image and upload to docUpload
    
    Args:
        verification_url: Initial SheerID verification URL
        use_proxy: Whether to use proxy (default True)
        
    Returns:
        dict with:
        - success: bool
        - verification_id: str (for API upload)
        - university: dict (id, name, city, state for transcript)
        - student_data: dict (first_name, last_name, birth_date for transcript)
        - error: str if failed
    """
    result = await verify_student_with_browserless(verification_url, use_proxy)
    
    if result["success"] and result.get("verification_id"):
        return {
            "success": True,
            "verification_id": result["verification_id"],
            "university": result["university"],
            "student_data": result["student_data"],
            "upload_url": result.get("current_url"),
            "message": "Student fraud bypass successful. Ready for transcript generation and upload."
        }
    else:
        return {
            "success": False,
            "error": result.get("error", "Unknown error"),
            "step": result.get("step"),
            "university": result.get("university"),
            "student_data": result.get("student_data")
        }


def student_bypass_sync(verification_url: str, use_proxy: bool = True):
    """Synchronous wrapper for student_bypass_and_get_data"""
    return asyncio.run(student_bypass_and_get_data(verification_url, use_proxy))


async def full_student_verification(verification_url: str, use_proxy: bool = True):
    """
    Complete student verification flow:
    1. Bypass fraud detection with Browserless + Proxy
    2. Generate transcript image (caller should do this)
    3. Upload document via API
    
    This function only does step 1 and returns data for step 2-3
    
    Args:
        verification_url: Initial SheerID URL
        use_proxy: Whether to use proxy
        
    Returns:
        dict with verification data for transcript generation
    """
    return await student_bypass_and_get_data(verification_url, use_proxy)
