"""
Locket Gold Web Interface API
Handles web-based Locket Gold activation with SePay payment integration
"""

from flask import Blueprint, request, jsonify
import asyncio
import uuid
import os
import random
from datetime import datetime, timedelta

# Import Locket services
try:
    from api.services import locket, nextdns
except ImportError:
    from .services import locket, nextdns

# Import Supabase client
try:
    from .supabase_client import get_supabase_client
except ImportError:
    # Fallback if import fails
    def get_supabase_client():
        from supabase import create_client
        import os
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')  # Use correct env var name
        return create_client(url, key)

locket_web_bp = Blueprint('locket_web', __name__)

# In-memory cache for profile data (5 minutes TTL)
profile_cache = {}
PROFILE_CACHE_TTL = 300  # 5 minutes in seconds

# Add CORS headers to all responses
@locket_web_bp.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# Test endpoint to verify blueprint is working
@locket_web_bp.route('/api/locket/test', methods=['GET', 'POST'])
def test_endpoint():
    return jsonify({
        'success': True,
        'message': 'Locket Web Blueprint is working!',
        'method': request.method
    })

# ============================================
# PROFILE FETCH ENDPOINT
# ============================================

@locket_web_bp.route('/api/locket/profile/<uid>', methods=['GET'])
def get_locket_profile(uid):
    """
    Fetch user profile data from Locket API
    
    Args:
        uid: Locket user ID
    
    Returns:
        {
            "success": bool,
            "profile": {
                "uid": str,
                "username": str,
                "display_name": str,
                "avatar_url": str,
                "bio": Optional[str]
            }
        }
    """
    try:
        import time
        import requests
        
        # Check cache first
        cache_key = f"profile_{uid}"
        current_time = time.time()
        
        if cache_key in profile_cache:
            cached_data, cached_time = profile_cache[cache_key]
            if current_time - cached_time < PROFILE_CACHE_TTL:
                print(f"✅ [PROFILE] Cache hit for UID: {uid}")
                return jsonify({
                    'success': True,
                    'profile': cached_data,
                    'cached': True
                })
        
        # Fetch from Locket API
        print(f"🔄 [PROFILE] Fetching profile for UID: {uid}")
        
        try:
            response = requests.get(
                f'https://api.locketcamera.com/user/{uid}',
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract profile data
                profile = {
                    'uid': uid,
                    'username': data.get('username', ''),
                    'display_name': data.get('displayName', data.get('username', '')),
                    'avatar_url': data.get('profilePicture', ''),
                    'bio': data.get('bio', '')
                }
                
                # Cache the result
                profile_cache[cache_key] = (profile, current_time)
                
                print(f"✅ [PROFILE] Fetched profile for {profile['username']}")
                
                return jsonify({
                    'success': True,
                    'profile': profile,
                    'cached': False
                })
            else:
                print(f"⚠️ [PROFILE] Locket API returned {response.status_code}")
                # Return default profile
                return jsonify({
                    'success': True,
                    'profile': {
                        'uid': uid,
                        'username': '',
                        'display_name': 'Locket User',
                        'avatar_url': '',
                        'bio': ''
                    },
                    'default': True
                })
                
        except requests.Timeout:
            print(f"⚠️ [PROFILE] Timeout fetching profile for UID: {uid}")
            return jsonify({
                'success': True,
                'profile': {
                    'uid': uid,
                    'username': '',
                    'display_name': 'Locket User',
                    'avatar_url': '',
                    'bio': ''
                },
                'default': True
            })
        except requests.RequestException as e:
            print(f"⚠️ [PROFILE] Request error: {e}")
            return jsonify({
                'success': True,
                'profile': {
                    'uid': uid,
                    'username': '',
                    'display_name': 'Locket User',
                    'avatar_url': '',
                    'bio': ''
                },
                'default': True
            })
            
    except Exception as e:
        print(f"❌ [PROFILE] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching profile: {str(e)}'
        }), 500

# ============================================
# SUCCESS PAGE DATA ENDPOINT
# ============================================

@locket_web_bp.route('/api/locket/success-data/<session_id>', methods=['GET'])
def get_success_data(session_id):
    """
    Get all data needed for success page
    
    Args:
        session_id: Session ID from locket_sessions table
    
    Returns:
        {
            "success": bool,
            "session": {
                "username": str,
                "uid": str,
                "package_type": str,
                "has_firebase_tokens": bool
            },
            "activation": {
                "id": int,
                "status": str,
                "dns_link": str,
                "dns_provider": str,
                "badge_set": bool,
                "badge_error": Optional[str],
                "created_at": str
            },
            "profile": {
                "username": str,
                "display_name": str,
                "avatar_url": str
            }
        }
    """
    try:
        print(f"🔄 [SUCCESS_DATA] Fetching data for session: {session_id}")
        
        # Get session from database
        session = get_session(session_id)
        
        if not session:
            print(f"❌ [SUCCESS_DATA] Session not found: {session_id}")
            return jsonify({
                'success': False,
                'message': 'Session không tồn tại'
            }), 404
        
        # Check if session is paid (or is reactivation)
        if not session.get('paid', False) and not session.get('is_reactivation', False):
            print(f"⚠️ [SUCCESS_DATA] Session not paid: {session_id}")
            return jsonify({
                'success': False,
                'message': 'Session chưa được thanh toán',
                'needs_payment': True
            }), 400
        
        # Get activation data from locket_activations table
        supabase = get_supabase_client()
        if not supabase:
            print(f"❌ [SUCCESS_DATA] Supabase client not available")
            return jsonify({
                'success': False,
                'message': 'Database not available'
            }), 500
        
        # Find activation by username and uid (most recent)
        username = session.get('username', '')
        uid = session.get('uid', '')
        
        activation_result = supabase.table('locket_activations')\
            .select('*')\
            .eq('locket_username', username)\
            .eq('locket_uid', uid)\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        activation = None
        if activation_result.data and len(activation_result.data) > 0:
            activation = activation_result.data[0]
            print(f"✅ [SUCCESS_DATA] Found activation: {activation['id']}")
        else:
            print(f"⚠️ [SUCCESS_DATA] No activation found for {username}")
        
        # Check if Firebase tokens are available
        has_firebase_tokens = bool(
            session.get('firebase_jwt') and 
            session.get('firebase_appcheck') and 
            session.get('firebase_fcm')
        )
        
        # Use session data only (don't fetch from Locket API)
        profile_data = {
            'username': username,
            'display_name': username or 'Locket User',
            'avatar_url': ''
        }
        
        # Generate NEW DNS link (always use latest hardcoded profiles)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            pid, dns_link, dns_provider = get_or_assign_dns_profile(username, loop)
            print(f"✅ [SUCCESS_DATA] Generated new DNS link: {dns_link}")
        finally:
            loop.close()
        
        # Build response
        response_data = {
            'success': True,
            'session': {
                'session_id': session_id,
                'username': username,
                'uid': uid,
                'package_type': session.get('package_type', '1year'),
                'has_firebase_tokens': has_firebase_tokens,
                'created_at': session.get('created_at', '')
            },
            'profile': profile_data
        }
        
        # Add activation data if available
        if activation:
            # Use NEW DNS link instead of old one from database
            response_data['activation'] = {
                'id': activation.get('id'),
                'status': activation.get('status', 'processing'),
                'dns_link': dns_link,  # NEW link with correct blocklist
                'dns_provider': 'nextdns_hardcoded',
                'badge_set': activation.get('badge_set', False),
                'badge_error': activation.get('badge_error'),
                'created_at': activation.get('created_at', ''),
                'completed_at': activation.get('completed_at')
            }
            
            # Update database with new DNS link
            try:
                supabase.table('locket_activations')\
                    .update({
                        'nextdns_link': dns_link,
                        'dns_provider': 'nextdns_hardcoded'
                    })\
                    .eq('id', activation.get('id'))\
                    .execute()
                print(f"✅ [SUCCESS_DATA] Updated activation {activation.get('id')} with new DNS link")
            except Exception as e:
                print(f"⚠️ [SUCCESS_DATA] Failed to update DNS link: {e}")
        else:
            # No activation yet - might still be processing
            response_data['activation'] = {
                'id': None,
                'status': 'pending',
                'dns_link': dns_link,  # Still provide NEW link
                'dns_provider': 'nextdns_hardcoded',
                'badge_set': False,
                'badge_error': None,
                'created_at': '',
                'completed_at': None
            }
        
        print(f"✅ [SUCCESS_DATA] Returning data for session: {session_id}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ [SUCCESS_DATA] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching success data: {str(e)}'
        }), 500

# ============================================
# BADGE TOGGLE ENDPOINT
# ============================================

@locket_web_bp.route('/api/locket/set-badge', methods=['POST'])
def set_badge_manual():
    """
    Manually set Gold badge using stored Firebase tokens
    
    Request Body:
        {
            "session_id": str,
            "uid": str
        }
    
    Returns:
        {
            "success": bool,
            "message": str,
            "badge_set": bool
        }
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id', '')
        uid = data.get('uid', '')
        
        if not session_id or not uid:
            return jsonify({
                'success': False,
                'message': 'Missing session_id or uid'
            }), 400
        
        print(f"🔄 [SET_BADGE] Manual badge setting for UID: {uid}, Session: {session_id}")
        
        # Get session from database
        session = get_session(session_id)
        
        if not session:
            print(f"❌ [SET_BADGE] Session not found: {session_id}")
            return jsonify({
                'success': False,
                'message': 'Session không tồn tại'
            }), 404
        
        # Retrieve Firebase tokens from session
        firebase_jwt = session.get('firebase_jwt')
        firebase_appcheck = session.get('firebase_appcheck')
        firebase_fcm = session.get('firebase_fcm')
        
        if not firebase_jwt or not firebase_appcheck or not firebase_fcm:
            print(f"⚠️ [SET_BADGE] Firebase tokens not available in session")
            return jsonify({
                'success': False,
                'message': 'Firebase tokens không có sẵn. Vui lòng bật badge thủ công trong app Locket.'
            }), 400
        
        print(f"🔑 [SET_BADGE] Firebase tokens retrieved from session")
        
        # Import badge service
        try:
            from api.services import locket_badge
        except ImportError:
            from .services import locket_badge
        
        # Call badge setting service
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            badge_set, badge_msg = loop.run_until_complete(
                locket_badge.set_gold_badge(uid, firebase_jwt, firebase_appcheck, firebase_fcm)
            )
            
            if badge_set:
                print(f"✅ [SET_BADGE] Badge set successfully: {badge_msg}")
                
                # Update locket_activations table with badge_set status
                supabase = get_supabase_client()
                if supabase:
                    try:
                        # Find activation by username and uid (most recent)
                        username = session.get('username', '')
                        
                        activation_result = supabase.table('locket_activations')\
                            .select('*')\
                            .eq('locket_username', username)\
                            .eq('locket_uid', uid)\
                            .order('created_at', desc=True)\
                            .limit(1)\
                            .execute()
                        
                        if activation_result.data and len(activation_result.data) > 0:
                            activation_id = activation_result.data[0]['id']
                            
                            # Update badge_set status
                            supabase.table('locket_activations')\
                                .update({
                                    'badge_set': True,
                                    'badge_error': None
                                })\
                                .eq('id', activation_id)\
                                .execute()
                            
                            print(f"✅ [SET_BADGE] Updated activation {activation_id} with badge_set=True")
                        else:
                            print(f"⚠️ [SET_BADGE] No activation found for {username}")
                    except Exception as db_error:
                        print(f"⚠️ [SET_BADGE] Error updating activation: {db_error}")
                
                return jsonify({
                    'success': True,
                    'message': 'Badge đã được bật thành công!',
                    'badge_set': True
                })
            else:
                print(f"⚠️ [SET_BADGE] Badge setting failed: {badge_msg}")
                
                # Update locket_activations table with error
                supabase = get_supabase_client()
                if supabase:
                    try:
                        username = session.get('username', '')
                        
                        activation_result = supabase.table('locket_activations')\
                            .select('*')\
                            .eq('locket_username', username)\
                            .eq('locket_uid', uid)\
                            .order('created_at', desc=True)\
                            .limit(1)\
                            .execute()
                        
                        if activation_result.data and len(activation_result.data) > 0:
                            activation_id = activation_result.data[0]['id']
                            
                            supabase.table('locket_activations')\
                                .update({
                                    'badge_set': False,
                                    'badge_error': badge_msg
                                })\
                                .eq('id', activation_id)\
                                .execute()
                            
                            print(f"✅ [SET_BADGE] Updated activation {activation_id} with badge_error")
                    except Exception as db_error:
                        print(f"⚠️ [SET_BADGE] Error updating activation: {db_error}")
                
                return jsonify({
                    'success': False,
                    'message': f'Không thể bật badge: {badge_msg}',
                    'badge_set': False
                }), 400
        finally:
            loop.close()
        
    except Exception as e:
        print(f"❌ [SET_BADGE] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Lỗi khi bật badge: {str(e)}',
            'badge_set': False
        }), 500

# ============================================
# DNS PROFILE ASSIGNMENT HELPER
# ============================================

def get_or_assign_dns_profile(username, loop):
    """
    Get NextDNS profile using round-robin between 2 hardcoded profiles
    Returns: (profile_id, link, dns_provider)
    """
    # SINGLE NextDNS Profile (no load balancing needed)
    # API Key: 58963f1ae4330ab7bc96e30cbdc51d542f3cd1df
    NEXTDNS_PROFILE_ID = os.environ.get('NEXTDNS_PROFILE_ID', '6dafaa')
    
    pid = NEXTDNS_PROFILE_ID
    link = f"https://apple.nextdns.io/?profile={pid}"
    dns_provider = 'nextdns'
    
    print(f"✅ [NEXTDNS] Assigned profile {pid} to {username}")
    
    return pid, link, dns_provider

# ============================================
# DATABASE SESSION MANAGEMENT
# Replaces in-memory payment_sessions dict
# ============================================

def generate_payment_content():
    """Generate unique payment content: LKxxxxxxx (x = digits 0-9)"""
    import random
    random_digits = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return f"LK{random_digits}"

def create_session(username, uid, is_reactivation, package_type='1year', price=50000, voucher_code=None, discount_amount=0, firebase_jwt=None, firebase_appcheck=None, firebase_fcm=None):
    """Create a new payment session in database"""
    try:
        print(f"🔄 [CREATE_SESSION] Starting for username: {username}, package: {package_type}, price: {price}, voucher: {voucher_code}")
        
        supabase = get_supabase_client()
        if not supabase:
            print("❌ [CREATE_SESSION] Supabase client not available")
            print(f"   SUPABASE_URL exists: {bool(os.getenv('SUPABASE_URL'))}")
            print(f"   SUPABASE_ANON_KEY exists: {bool(os.getenv('SUPABASE_ANON_KEY'))}")
            return None
        
        print("✅ [CREATE_SESSION] Supabase client OK")
        
        session_id = str(uuid.uuid4())
        payment_content = generate_payment_content()
        
        session_data = {
            'session_id': session_id,
            'username': username,
            'uid': uid,
            'is_reactivation': is_reactivation,
            'payment_content': payment_content,
            'paid': False,
            'package_type': package_type,
            'price': price,
            'voucher_code': voucher_code,
            'discount_amount': discount_amount,
            'firebase_jwt': firebase_jwt,
            'firebase_appcheck': firebase_appcheck,
            'firebase_fcm': firebase_fcm
        }
        
        print(f"📝 [CREATE_SESSION] Session data: {session_data}")
        print(f"🔄 [CREATE_SESSION] Inserting into locket_sessions table...")
        
        result = supabase.table('locket_sessions').insert(session_data).execute()
        
        print(f"📊 [CREATE_SESSION] Insert result: {result}")
        
        if result.data:
            print(f"✅ [CREATE_SESSION] Created session: {session_id}")
            return result.data[0]
        else:
            print(f"❌ [CREATE_SESSION] No data returned from insert")
            print(f"   Result object: {result}")
            return None
    except Exception as e:
        print(f"❌ [CREATE_SESSION] Error: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None

def get_session(session_id):
    """Get session from database"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        result = supabase.table('locket_sessions').select('*').eq('session_id', session_id).limit(1).execute()
        
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        print(f"❌ Error getting session: {e}")
        return None

def mark_session_paid(session_id):
    """Mark session as paid in database"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return False
        
        update_data = {
            'paid': True,
            'paid_at': datetime.now().isoformat()
        }
        
        result = supabase.table('locket_sessions').update(update_data).eq('session_id', session_id).execute()
        
        if result.data:
            print(f"✅ Marked session paid: {session_id}")
            return True
        return False
    except Exception as e:
        print(f"❌ Error marking session paid: {e}")
        return False

def find_session_by_payment_content(payment_content):
    """Find session by payment content - supports partial matching"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        # Extract LK code from content if it contains dashes or other text
        # Format: "129456123-LK4416494-812456126" or just "LK4416494"
        import re
        lk_match = re.search(r'LK\d{7}', payment_content)
        
        if lk_match:
            lk_code = lk_match.group(0)
            print(f"🔍 Extracted LK code: {lk_code} from content: {payment_content}")
            
            # Search by the extracted LK code
            result = supabase.table('locket_sessions').select('*').eq('payment_content', lk_code).eq('paid', False).limit(1).execute()
        else:
            # Fallback to exact match
            print(f"⚠️ No LK code found in: {payment_content}, trying exact match")
            result = supabase.table('locket_sessions').select('*').eq('payment_content', payment_content).eq('paid', False).limit(1).execute()
        
        if result.data:
            print(f"✅ Found session: {result.data[0]['session_id']}")
            return result.data[0]
        else:
            print(f"❌ No session found for payment content: {payment_content}")
        return None
    except Exception as e:
        print(f"❌ Error finding session: {e}")
        return None

def generate_qr_url(amount, content):
    """Generate SePay QR code URL using VietQR"""
    # Get bank config from environment or use default
    import os
    
    # Default MB Bank config (replace with your actual info)
    account_number = os.getenv('BANK_ACCOUNT_NUMBER', '188299299')
    account_name = os.getenv('BANK_ACCOUNT_NAME', 'PHAN QUOC DANG QUANG')
    bank_code = os.getenv('BANK_CODE', '970422')  # MB Bank
    
    # VietQR format
    qr_url = f"https://img.vietqr.io/image/{bank_code}-{account_number}-compact2.png?amount={amount}&addInfo={content}&accountName={account_name}"
    
    return qr_url

@locket_web_bp.route('/api/locket/validate-voucher', methods=['POST'])
def validate_voucher():
    """
    Validate a voucher code and return discount information
    """
    try:
        data = request.get_json()
        code = data.get('code', '').strip().upper()
        package_type = data.get('package_type', '1year')
        original_price = data.get('price', 50000)
        
        if not code:
            return jsonify({
                'success': False,
                'message': 'Vui lòng nhập mã voucher'
            }), 400
        
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({
                'success': False,
                'message': 'Database not available'
            }), 500
        
        # Get voucher from database
        result = supabase.table('locket_vouchers')\
            .select('*')\
            .eq('code', code)\
            .eq('active', True)\
            .limit(1)\
            .execute()
        
        if not result.data or len(result.data) == 0:
            return jsonify({
                'success': False,
                'message': 'Mã voucher không hợp lệ'
            }), 404
        
        voucher = result.data[0]
        
        # Check if voucher is still valid (date range)
        from datetime import datetime
        now = datetime.now()
        
        if voucher.get('valid_from'):
            valid_from = datetime.fromisoformat(voucher['valid_from'].replace('Z', '+00:00'))
            if now < valid_from:
                return jsonify({
                    'success': False,
                    'message': 'Mã voucher chưa có hiệu lực'
                }), 400
        
        if voucher.get('valid_until'):
            valid_until = datetime.fromisoformat(voucher['valid_until'].replace('Z', '+00:00'))
            if now > valid_until:
                return jsonify({
                    'success': False,
                    'message': 'Mã voucher đã hết hạn'
                }), 400
        
        # Check usage limit
        max_uses = voucher.get('max_uses')
        used_count = voucher.get('used_count', 0)
        if max_uses is not None and used_count >= max_uses:
            return jsonify({
                'success': False,
                'message': 'Mã voucher đã hết lượt sử dụng'
            }), 400
        
        # Check minimum purchase
        min_purchase = voucher.get('min_purchase', 0)
        if original_price < min_purchase:
            return jsonify({
                'success': False,
                'message': f'Đơn hàng tối thiểu {min_purchase:,} VNĐ để dùng mã này'.replace(',', '.')
            }), 400
        
        # Check applicable packages
        applicable_packages = voucher.get('applicable_packages')
        if applicable_packages and package_type not in applicable_packages:
            return jsonify({
                'success': False,
                'message': 'Mã voucher không áp dụng cho gói này'
            }), 400
        
        # Calculate discount
        discount_type = voucher.get('discount_type')
        discount_value = voucher.get('discount_value', 0)
        
        if discount_type == 'percentage':
            discount_amount = int(original_price * discount_value / 100)
        else:  # fixed
            discount_amount = discount_value
        
        # Ensure discount doesn't exceed original price
        discount_amount = min(discount_amount, original_price)
        final_price = original_price - discount_amount
        
        return jsonify({
            'success': True,
            'voucher': {
                'code': code,
                'discount_type': discount_type,
                'discount_value': discount_value,
                'discount_amount': discount_amount,
                'original_price': original_price,
                'final_price': final_price
            },
            'message': f'Giảm {discount_amount:,} VNĐ'.replace(',', '.')
        })
        
    except Exception as e:
        print(f"❌ Error in validate_voucher: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Lỗi kiểm tra voucher'
        }), 500

@locket_web_bp.route('/api/locket/check', methods=['POST'])
def check_locket_username():
    """
    Check if username needs payment or can be reactivated for free
    """
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        package_type = data.get('package', '1year')
        price = data.get('price', 50000)
        voucher_code = data.get('voucher_code')
        discount_amount = data.get('discount_amount', 0)
        
        # NEW: Accept Firebase tokens (optional)
        firebase_jwt = data.get('firebase_jwt')
        firebase_appcheck = data.get('firebase_appcheck')
        firebase_fcm = data.get('firebase_fcm')
        
        # Log token presence for debugging
        if firebase_jwt or firebase_appcheck or firebase_fcm:
            print(f"🔑 [CHECK] Firebase tokens received:")
            print(f"   JWT: {'✓' if firebase_jwt else '✗'}")
            print(f"   AppCheck: {'✓' if firebase_appcheck else '✗'}")
            print(f"   FCM: {'✓' if firebase_fcm else '✗'}")
        else:
            print(f"⚠️ [CHECK] No Firebase tokens provided - badge setting will be skipped")
        
        if not username:
            return jsonify({
                'success': False,
                'message': 'Vui lòng nhập username'
            }), 400
        
        # Extract username from link if provided
        if "locket.cam/" in username:
            username = username.split("locket.cam/")[-1].split("?")[0]
        
        # Resolve UID
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        uid = loop.run_until_complete(locket.resolve_uid(username))
        
        if not uid:
            loop.close()
            return jsonify({
                'success': False,
                'message': 'Không tìm thấy user Locket này!'
            }), 404
        
        # Check current status
        status = loop.run_until_complete(locket.check_status(uid))
        
        if status and status.get('active'):
            loop.close()
            return jsonify({
                'success': False,
                'message': f'User đã có Gold rồi! Hết hạn: {status.get("expires", "N/A")}'
            }), 400
        
        # Check if username was previously activated (in locket_activations table)
        supabase = get_supabase_client()
        
        # Search by username (not telegram_id since this is web-based)
        is_reactivation = False
        previous_package = None
        try:
            previous_activation = supabase.table('locket_activations').select('*').eq('locket_username', username).eq('status', 'success').order('created_at', desc=True).limit(1).execute()
            
            if previous_activation and hasattr(previous_activation, 'data') and previous_activation.data and len(previous_activation.data) > 0:
                previous_package = previous_activation.data[0].get('package_type', '1year')
                
                # IMPORTANT: Only allow free reactivation if SAME package
                # If user bought 5months before but now wants 12months, they must pay!
                if previous_package == package_type:
                    is_reactivation = True
                    print(f"✅ Free reactivation: Same package ({package_type})")
                else:
                    is_reactivation = False
                    print(f"⚠️ Package changed: {previous_package} → {package_type}, must pay!")
        except Exception as e:
            print(f"Error checking previous activation: {e}")
            is_reactivation = False
        
        # Create session in database with package info, voucher, and Firebase tokens
        session = create_session(
            username, uid, is_reactivation, package_type, price, 
            voucher_code, discount_amount,
            firebase_jwt, firebase_appcheck, firebase_fcm
        )
        
        if not session:
            loop.close()
            return jsonify({
                'success': False,
                'message': 'Không thể tạo session. Vui lòng liên hệ admin để tạo bảng locket_sessions trong database.'
            }), 500
        
        if is_reactivation:
            # Free reactivation - ONLY if same package
            loop.close()
            return jsonify({
                'success': True,
                'needs_payment': False,
                'session_id': session['session_id'],
                'message': f'Bạn đã từng mua gói {package_type}. Kích hoạt lại miễn phí!'
            })
        else:
            # Need payment - use the price from selected package (after discount)
            qr_url = generate_qr_url(price, session['payment_content'])
            
            # Custom message if package changed
            message = None
            if previous_package and previous_package != package_type:
                package_names = {
                    '1month': 'Gói 1 tháng',
                    '5months': 'Gói 5 tháng',
                    '1year': 'Gói 12 tháng'
                }
                old_name = package_names.get(previous_package, previous_package)
                new_name = package_names.get(package_type, package_type)
                message = f'Bạn đã từng mua {old_name}. Để nâng cấp lên {new_name}, vui lòng thanh toán.'
            
            loop.close()
            response_data = {
                'success': True,
                'needs_payment': True,
                'session_id': session['session_id'],
                'qr_url': qr_url,
                'payment_content': session['payment_content'],
                'amount': price,
                'package_type': package_type
            }
            
            if message:
                response_data['message'] = message
            
            return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Error in check_locket_username: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }), 500

@locket_web_bp.route('/api/locket/payment-status/<session_id>', methods=['GET'])
def check_payment_status(session_id):
    """
    Check if payment has been received for this session
    """
    try:
        session = get_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'message': 'Session không tồn tại'
            }), 404
        
        return jsonify({
            'success': True,
            'paid': session.get('paid', False)
        })
        
    except Exception as e:
        print(f"❌ Error in check_payment_status: {e}")
        return jsonify({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }), 500

@locket_web_bp.route('/api/locket/session/<session_id>', methods=['GET'])
def get_session_info(session_id):
    """
    Get session information from locket_sessions table
    """
    try:
        session = get_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'message': 'Session không tồn tại'
            }), 404
        
        return jsonify({
            'success': True,
            'session': session
        })
        
    except Exception as e:
        print(f"❌ Error in get_session_info: {e}")
        return jsonify({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }), 500

@locket_web_bp.route('/api/locket/payment-info/<session_id>', methods=['GET'])
def get_payment_info(session_id):
    """
    Get payment information for a session
    """
    try:
        session = get_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'message': 'Session không tồn tại'
            }), 404
        
        # Get price from session (default to 50000 if not set)
        price = session.get('price', 50000)
        package_type = session.get('package_type', '1year')
        voucher_code = session.get('voucher_code')
        discount_amount = session.get('discount_amount', 0)
        
        # Generate QR URL with correct price
        qr_url = generate_qr_url(price, session['payment_content'])
        
        # Get bank info from environment
        import os
        bank_name = os.getenv('BANK_NAME', 'MB Bank')
        account_number = os.getenv('BANK_ACCOUNT_NUMBER', '188299299')
        account_name = os.getenv('BANK_ACCOUNT_NAME', 'PHAN QUOC DANG QUANG')
        
        # Format amount with thousand separator
        amount_formatted = f"{price:,} VNĐ".replace(',', '.')
        
        response_data = {
            'success': True,
            'qr_url': qr_url,
            'payment_content': session['payment_content'],
            'amount': amount_formatted,
            'amount_raw': price,
            'package_type': package_type,
            'bank_name': bank_name,
            'account_number': account_number,
            'account_name': account_name,
            'username': session['username'],
            'paid': session.get('paid', False)
        }
        
        # Add voucher info if applied
        if voucher_code and discount_amount > 0:
            response_data['voucher_code'] = voucher_code
            response_data['discount_amount'] = discount_amount
            response_data['original_price'] = price + discount_amount
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Error in get_payment_info: {e}")
        return jsonify({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }), 500

@locket_web_bp.route('/api/locket/sepay-webhook', methods=['POST', 'GET'])
def sepay_webhook():
    """
    SePay webhook endpoint
    Receives payment notifications from SePay
    
    GET: Webhook verification (SePay sends GET to verify URL)
    POST: Payment notification
    """
    try:
        # Handle GET request for webhook verification
        if request.method == 'GET':
            print(f"✅ SePay webhook verification - GET request received")
            return jsonify({
                'success': True,
                'message': 'Webhook endpoint is active',
                'service': 'Locket Gold Payment'
            }), 200
        
        # Handle POST request for payment notification
        print(f"📥 SePay webhook - Method: {request.method}")
        print(f"📥 Headers: {dict(request.headers)}")
        print(f"📥 Query params: {dict(request.args)}")
        
        # Try to get data from multiple sources
        data = None
        
        # Try JSON body first
        if request.is_json:
            data = request.get_json()
            print(f"📥 JSON data: {data}")
        
        # Try form data
        if not data and request.form:
            data = request.form.to_dict()
            print(f"📥 Form data: {data}")
        
        # Try query parameters
        if not data and request.args:
            data = request.args.to_dict()
            print(f"📥 Query data: {data}")
        
        if not data:
            print(f"⚠️ No data received in webhook")
            return jsonify({
                'success': False,
                'message': 'No data received'
            }), 400
        
        # Extract payment info - try multiple field names (SePay format)
        transfer_content = (
            data.get('content', '') or
            data.get('transferContent', '') or 
            data.get('description', '') or
            data.get('comment', '') or
            data.get('message', '') or
            data.get('transaction_content', '')
        )
        
        amount = (
            data.get('amount_in', 0) or
            data.get('amount', 0) or
            data.get('transferAmount', 0) or 
            data.get('value', 0) or
            data.get('money', 0)
        )
        
        # Get transaction ID for logging
        transaction_id = (
            data.get('id', '') or
            data.get('transaction_id', '') or
            data.get('transferId', '')
        )
        
        # Convert amount to int if string
        try:
            amount = int(float(amount))
        except:
            amount = 0
        
        print(f"💰 Extracted - Content: '{transfer_content}', Amount: {amount}, TxID: {transaction_id}")
        
        if not transfer_content:
            print(f"⚠️ No transfer content found in webhook data")
            print(f"   Available keys: {list(data.keys())}")
            return jsonify({
                'success': False,
                'message': 'No transfer content'
            }), 400
        
        # Find matching session by payment content
        session = find_session_by_payment_content(transfer_content)
        
        if not session:
            print(f"❌ No session found for content: {transfer_content}")
            return jsonify({
                'success': False,
                'message': 'Session not found',
                'content_received': transfer_content
            }), 404
        
        print(f"✅ Found session: {session['session_id']}")
        
        # Get expected amount from session (default to 50000)
        expected_amount = session.get('price', 50000)
        
        if amount >= expected_amount:
            # Mark as paid
            success = mark_session_paid(session['session_id'])
            if success:
                print(f"✅ Payment confirmed for session {session['session_id']}")
                return jsonify({
                    'success': True,
                    'message': 'Payment confirmed',
                    'session_id': session['session_id']
                }), 200
            else:
                print(f"❌ Failed to mark session as paid")
                return jsonify({
                    'success': False,
                    'message': 'Failed to update session'
                }), 500
        else:
            print(f"⚠️ Amount too low: {amount} < {expected_amount}")
            return jsonify({
                'success': False,
                'message': f'Amount too low: {amount} (expected: {expected_amount})'
            }), 400
        
    except Exception as e:
        print(f"❌ Error in sepay_webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }), 500

@locket_web_bp.route('/api/locket/test-webhook', methods=['POST'])
def test_webhook():
    """
    Test webhook endpoint - manually trigger payment confirmation
    """
    try:
        data = request.get_json()
        payment_content = data.get('payment_content', '')
        
        if not payment_content:
            return jsonify({
                'success': False,
                'message': 'Missing payment_content'
            }), 400
        
        print(f"🧪 Testing webhook for content: {payment_content}")
        
        # Find session
        session = find_session_by_payment_content(payment_content)
        
        if not session:
            return jsonify({
                'success': False,
                'message': f'Session not found for: {payment_content}'
            }), 404
        
        # Mark as paid
        success = mark_session_paid(session['session_id'])
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Payment marked as confirmed',
                'session_id': session['session_id']
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to mark as paid'
            }), 500
        
    except Exception as e:
        print(f"❌ Error in test_webhook: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@locket_web_bp.route('/api/locket/debug-session/<payment_content>', methods=['GET'])
def debug_session(payment_content):
    """
    Debug endpoint to check session status
    """
    try:
        print(f"🔍 Debugging session for content: {payment_content}")
        
        # Find session
        session = find_session_by_payment_content(payment_content)
        
        if not session:
            # Also try to list all sessions
            supabase = get_supabase_client()
            if supabase:
                all_sessions = supabase.table('locket_sessions').select('*').eq('paid', False).order('created_at', desc=True).limit(10).execute()
                return jsonify({
                    'success': False,
                    'message': f'Session not found for: {payment_content}',
                    'recent_unpaid_sessions': all_sessions.data if all_sessions.data else []
                }), 404
        
        return jsonify({
            'success': True,
            'session': session
        })
        
    except Exception as e:
        print(f"❌ Error in debug_session: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@locket_web_bp.route('/api/locket/activate-direct', methods=['POST'])
def activate_locket_direct():
    """
    Direct activation - bypass session (for manual activation after payment)
    """
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        payment_content = data.get('payment_content', '').strip()
        
        if not username:
            return jsonify({
                'success': False,
                'message': 'Vui lòng nhập username'
            }), 400
        
        # Extract username from link if provided
        if "locket.cam/" in username:
            username = username.split("locket.cam/")[-1].split("?")[0]
        
        # If payment_content provided, verify it matches a session
        if payment_content:
            session = find_session_by_payment_content(payment_content)
            if not session:
                return jsonify({
                    'success': False,
                    'message': f'Không tìm thấy session với mã thanh toán: {payment_content}'
                }), 404
            
            # Mark session as paid
            mark_session_paid(session['session_id'])
            print(f"✅ Manually marked session as paid: {session['session_id']}")
        
        # Resolve UID
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        uid = loop.run_until_complete(locket.resolve_uid(username))
        
        if not uid:
            loop.close()
            return jsonify({
                'success': False,
                'message': 'Không tìm thấy user Locket này!'
            }), 404
        
        # Check if previously activated
        supabase = get_supabase_client()
        try:
            previous_activation = supabase.table('locket_activations').select('*').eq('locket_username', username).eq('status', 'success').order('created_at', desc=True).limit(1).execute()
            # FIX: Ensure is_reactivation is always boolean, not array
            is_reactivation = bool(previous_activation and hasattr(previous_activation, 'data') and previous_activation.data and len(previous_activation.data) > 0)
        except Exception as e:
            print(f"Error checking previous activation: {e}")
            is_reactivation = False
        
        # Create activation record
        activation_data = {
            'locket_username': username,
            'locket_uid': uid,
            'status': 'processing',
            'payment_type': 'web_manual_reactivation' if is_reactivation else 'web_manual_payment',
            'amount_charged': 0 if is_reactivation else 20
        }
        
        activation = supabase.table('locket_activations').insert(activation_data).execute()
        activation_id = activation.data[0]['id']
        
        # Inject Gold using new token management system
        from services.token_health import TokenHealthService
        from services.token_price_decoder import TokenPriceDecoder
        from services.monitoring import MonitoringService
        
        # Get best token from pool
        token_health_service = TokenHealthService()
        best_token = loop.run_until_complete(token_health_service.get_best_token())
        
        if not best_token:
            # Fallback to environment token if no tokens in pool
            print("⚠️ No tokens in pool, using environment token")
            token_config = locket.get_token_config()
            token_id = None
        else:
            # Use token from pool
            print(f"✅ Selected token {best_token['id']} from pool")
            token_config = {
                'fetch_token': best_token['fetch_token'],
                'app_transaction': best_token['app_transaction'],
                'is_sandbox': best_token.get('is_sandbox', False)
            }
            token_id = best_token['id']
            
            # Decode price information from token
            decoder = TokenPriceDecoder()
            price_data = decoder.prepare_revenuecat_data(best_token['fetch_token'])
            token_config['price'] = price_data['price']
            token_config['currency'] = price_data['currency']
            token_config['storefront'] = price_data['storefront']
        
        # Inject Gold with decoded price information
        success, msg_result = loop.run_until_complete(locket.inject_gold(uid, token_config))
        
        # Track activation result
        if token_id:
            loop.run_until_complete(token_health_service.track_activation(token_id, success))
        
        if success:
            # Badge setting not available for direct activation (no Firebase tokens)
            badge_set = False
            badge_error = "direct_activation_no_tokens"
            print(f"⚠️ [BADGE] Direct activation - no Firebase tokens available, skipping badge setting")
            
            # Get or assign DNS profile from pool
            pid, link, dns_provider = get_or_assign_dns_profile(username, loop)
            
            # Update activation record with token_id and badge status
            update_data = {
                'status': 'success',
                'nextdns_profile_id': pid,
                'nextdns_link': link,
                'dns_provider': dns_provider,
                'badge_set': badge_set,
                'badge_error': badge_error,
                'completed_at': 'now()'
            }
            
            if token_id:
                update_data['token_id'] = token_id
            
            supabase.table('locket_activations').update(update_data).eq('id', activation_id).execute()
            
            # Schedule retention checks
            monitoring_service = MonitoringService()
            loop.run_until_complete(monitoring_service.schedule_checks(activation_id))
            print(f"✅ Scheduled retention checks for activation {activation_id}")
            
            # Generate DNS profile link based on provider
            if dns_provider == 'cloudflare' or dns_provider == 'nextdns_pool':
                # Cloudflare: Return DoH URL directly
                display_link = link
            else:
                # NextDNS: Return Apple profile link
                display_link = link  # https://apple.nextdns.io/?profile={pid}
            
            response_data = {
                'success': True,
                'message': 'Kích hoạt thành công!',
                'dns_link': display_link,
                'dns_profile_id': pid,
                'dns_provider': dns_provider,
                'badge_set': badge_set,
                'badge_error': badge_error,
                'retention_info': {
                    'domains_blocked': 21,
                    'retention_rate': '99%'
                }
            }
            
            # Add redirect if session was found
            if payment_content and session:
                response_data['redirect'] = f'/locket-success.html?session={session["session_id"]}'
            
            return jsonify(response_data)
        else:
            # Failed
            supabase.table('locket_activations').update({
                'status': 'failed',
                'error_message': msg_result,
                'completed_at': 'now()'
            }).eq('id', activation_id).execute()
            
            loop.close()
            
            return jsonify({
                'success': False,
                'message': f'Kích hoạt thất bại: {msg_result}'
            }), 500
        
    except Exception as e:
        print(f"❌ Error in activate_locket_direct: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }), 500

@locket_web_bp.route('/api/locket/recent-purchases', methods=['GET'])
def get_recent_purchases():
    """
    Get recent successful Locket activations for social proof
    Returns masked usernames and package types
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            # Return fake data if no database connection
            return jsonify({
                'success': True,
                'purchases': generate_fake_purchases()
            })
        
        # Try to get real data from locket_activations table
        try:
            result = supabase.table('locket_activations')\
                .select('locket_username, package_type, created_at')\
                .eq('status', 'success')\
                .order('created_at', desc=True)\
                .limit(20)\
                .execute()
            
            if result.data and len(result.data) > 0:
                # Process real data
                seen_usernames = set()
                purchases = []
                
                for item in result.data:
                    username = item.get('locket_username', '')
                    package_type = item.get('package_type', '1year')
                    
                    if username in seen_usernames:
                        continue
                    
                    seen_usernames.add(username)
                    
                    # Mask username
                    if len(username) <= 3:
                        masked = '*' * len(username)
                    elif len(username) <= 6:
                        masked = '*' * (len(username) - 2) + username[-2:]
                    else:
                        masked = '*' * (len(username) - 3) + username[-3:]
                    
                    # Package display name
                    if package_type == '1month':
                        package_display = 'Gói 1 tháng'
                    elif package_type == '5months':
                        package_display = 'Gói 5 tháng'
                    else:
                        package_display = 'Gói 12 tháng'
                    
                    # Convert time to Vietnam timezone and format as "X giờ trước"
                    created_at_str = item.get('created_at', '')
                    time_display = ''
                    if created_at_str:
                        try:
                            # Parse UTC time from database
                            from datetime import datetime, timezone, timedelta
                            utc_time = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            # Convert to Vietnam time (UTC+7)
                            vietnam_time = utc_time.astimezone(timezone(timedelta(hours=7)))
                            # Calculate time difference
                            now_vietnam = datetime.now(timezone(timedelta(hours=7)))
                            diff = now_vietnam - vietnam_time
                            
                            # Format as "X giờ trước"
                            hours = int(diff.total_seconds() / 3600)
                            if hours < 1:
                                minutes = int(diff.total_seconds() / 60)
                                time_display = f'{minutes} phút trước' if minutes > 0 else 'Vừa xong'
                            elif hours < 24:
                                time_display = f'{hours} giờ trước'
                            else:
                                days = int(hours / 24)
                                time_display = f'{days} ngày trước'
                        except Exception as e:
                            print(f"Error parsing time: {e}")
                            time_display = 'Vừa xong'
                    else:
                        time_display = 'Vừa xong'
                    
                    purchases.append({
                        'username': masked,
                        'package': package_display,
                        'time': time_display
                    })
                    
                    if len(purchases) >= 20:
                        break
                
                # Ensure purchases are sorted by time (newest first)
                # Already sorted by created_at desc from query
                
                return jsonify({
                    'success': True,
                    'purchases': purchases if purchases else generate_fake_purchases()
                })
            else:
                # No data, return fake purchases
                return jsonify({
                    'success': True,
                    'purchases': generate_fake_purchases()
                })
                
        except Exception as db_error:
            print(f"❌ Database error in get_recent_purchases: {db_error}")
            # Return fake data on database error
            return jsonify({
                'success': True,
                'purchases': generate_fake_purchases()
            })
        
    except Exception as e:
        print(f"❌ Error in get_recent_purchases: {e}")
        return jsonify({
            'success': True,
            'purchases': generate_fake_purchases()
        })

def generate_fake_purchases():
    """Generate fake purchase data for display with consistent times"""
    fake_usernames = [
        '***nhi', '***ung', '***inh', '***yen', '***thu',
        '***mai', '***lan', '***hoa', '***nga', '***han',
        '***son', '***tuan', '***long', '***nam', '***duc',
        '***kha', '***minh', '***phat', '***khoa', '***bao'
    ]
    
    packages = ['Gói 1 tháng', 'Gói 5 tháng', 'Gói 12 tháng']
    
    # Fixed time intervals for consistency (not random)
    time_intervals = [
        '5 phút trước', '12 phút trước', '18 phút trước', '25 phút trước', '32 phút trước',
        '45 phút trước', '1 giờ trước', '1 giờ trước', '2 giờ trước', '2 giờ trước',
        '3 giờ trước', '4 giờ trước', '5 giờ trước', '6 giờ trước', '8 giờ trước'
    ]
    
    purchases = []
    
    for i in range(15):
        purchases.append({
            'username': fake_usernames[i % len(fake_usernames)],
            'package': packages[i % len(packages)],
            'time': time_intervals[i]
        })
    
    return purchases

@locket_web_bp.route('/api/locket/activate', methods=['POST', 'OPTIONS'])
def activate_locket():
    """
    Activate Locket Gold after payment confirmation
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    print(f"🔥 [ACTIVATE] Request received - Method: {request.method}")
    print(f"🔥 [ACTIVATE] Headers: {dict(request.headers)}")
    print(f"🔥 [ACTIVATE] Content-Type: {request.content_type}")
    
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        session_id = data.get('session_id', '')
        
        session = get_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'message': 'Session không tồn tại'
            }), 404
        
        # Get price from session
        price = session.get('price', 50000)
        
        # Ensure price is numeric for comparison
        try:
            price_numeric = int(float(price)) if price else 0
        except (ValueError, TypeError):
            price_numeric = 50000
        
        # Verify payment (skip for reactivation or 100% discount)
        if not session['is_reactivation'] and price_numeric > 0 and not session.get('paid', False):
            return jsonify({
                'success': False,
                'message': 'Chưa thanh toán'
            }), 400
        
        uid = session['uid']
        is_reactivation = session['is_reactivation']
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Get package info from session
        package_type = session.get('package_type', '1year')
        voucher_code = session.get('voucher_code')
        
        # Ensure price is integer for database operations (fix type conversion error)
        try:
            price_int = int(float(price)) if price else 0
            if price_int < 0:
                price_int = 0
        except (ValueError, TypeError) as e:
            print(f"⚠️ [ACTIVATE] Invalid price value: {price} (type: {type(price).__name__}), using default 50000")
            print(f"   Error: {e}")
            price_int = 50000
        
        print(f"💰 [ACTIVATE] Price from session: {price} (type: {type(price).__name__})")
        print(f"💰 [ACTIVATE] Converted to int: {price_int}")
        print(f"💰 [ACTIVATE] Amount charged (thousands): {price_int // 1000}")
        
        # Determine payment type
        if is_reactivation:
            payment_type = 'web_free_reactivation'
        elif price_int == 0:
            payment_type = 'web_voucher_100_discount'
        else:
            payment_type = 'web_sepay'
        
        # Create activation record (without telegram_id for web-based)
        activation_data = {
            'locket_username': username,
            'locket_uid': uid,
            'status': 'processing',
            'payment_type': payment_type,
            'amount_charged': 0 if (is_reactivation or price_int == 0) else (price_int // 1000),  # Store in thousands (integer division)
            'package_type': package_type
        }
        
        activation = supabase.table('locket_activations').insert(activation_data).execute()
        
        activation_id = activation.data[0]['id']
        
        # Inject Gold using new token management system
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Import new services
        from services.token_health import TokenHealthService
        from services.token_price_decoder import TokenPriceDecoder
        from services.monitoring import MonitoringService
        
        # Get best token from pool
        token_health_service = TokenHealthService()
        best_token = loop.run_until_complete(token_health_service.get_best_token())
        
        if not best_token:
            # Fallback to environment token if no tokens in pool
            print("⚠️ No tokens in pool, using environment token")
            token_config = locket.get_token_config()
            token_id = None
        else:
            # Use token from pool
            print(f"✅ Selected token {best_token['id']} from pool")
            token_config = {
                'fetch_token': best_token['fetch_token'],
                'app_transaction': best_token['app_transaction'],
                'is_sandbox': best_token.get('is_sandbox', False)
            }
            token_id = best_token['id']
            
            # Decode price information from token
            decoder = TokenPriceDecoder()
            price_data = decoder.prepare_revenuecat_data(best_token['fetch_token'])
            token_config['price'] = price_data['price']
            token_config['currency'] = price_data['currency']
            token_config['storefront'] = price_data['storefront']
        
        # Inject Gold with decoded price information
        success, msg_result = loop.run_until_complete(locket.inject_gold(uid, token_config))
        
        # Track activation result
        if token_id:
            loop.run_until_complete(token_health_service.track_activation(token_id, success))
        
        if success:
            # NEW: Set badge if Firebase tokens are available
            badge_set = False
            badge_error = None
            
            # Retrieve Firebase tokens from session
            firebase_jwt = session.get('firebase_jwt')
            firebase_appcheck = session.get('firebase_appcheck')
            firebase_fcm = session.get('firebase_fcm')
            
            if firebase_jwt and firebase_appcheck and firebase_fcm:
                print(f"🔑 [BADGE] Firebase tokens available, attempting badge setting...")
                try:
                    # Import badge service
                    try:
                        from api.services import locket_badge
                    except ImportError:
                        from .services import locket_badge
                    
                    # Call badge setting service
                    badge_set, badge_msg = loop.run_until_complete(
                        locket_badge.set_gold_badge(uid, firebase_jwt, firebase_appcheck, firebase_fcm)
                    )
                    
                    if badge_set:
                        print(f"✅ [BADGE] Badge set successfully: {badge_msg}")
                    else:
                        badge_error = badge_msg
                        print(f"⚠️ [BADGE] Badge setting failed: {badge_msg}")
                except Exception as e:
                    badge_error = f"Exception: {str(e)}"
                    print(f"❌ [BADGE] Exception during badge setting: {e}")
            else:
                badge_error = "tokens_not_provided"
                print(f"⚠️ [BADGE] Firebase tokens not provided, skipping badge setting")
            
            # Get or assign DNS profile from pool
            pid, link, dns_provider = get_or_assign_dns_profile(username, loop)
            
            # Update activation record with token_id and badge status
            update_data = {
                'status': 'success',
                'nextdns_profile_id': pid,
                'nextdns_link': link,
                'dns_provider': dns_provider,
                'badge_set': badge_set,
                'badge_error': badge_error,
                'completed_at': 'now()'
            }
            
            if token_id:
                update_data['token_id'] = token_id
            
            supabase.table('locket_activations').update(update_data).eq('id', activation_id).execute()
            
            # Schedule retention checks
            monitoring_service = MonitoringService()
            loop.run_until_complete(monitoring_service.schedule_checks(activation_id))
            print(f"✅ Scheduled retention checks for activation {activation_id}")
            
            # Increment voucher usage if voucher was used
            if voucher_code:
                try:
                    # Increment used_count
                    supabase.rpc('increment_voucher_usage', {'voucher_code_param': voucher_code}).execute()
                    
                    # Log voucher usage
                    supabase.table('locket_voucher_usage').insert({
                        'voucher_code': voucher_code,
                        'locket_username': username,
                        'session_id': session_id,
                        'activation_id': activation_id
                    }).execute()
                except Exception as e:
                    print(f"⚠️ Error recording voucher usage: {e}")
            
            loop.close()
            
            # Generate DNS profile link based on provider
            if dns_provider == 'cloudflare' or dns_provider == 'nextdns_pool':
                # Cloudflare: Return DoH URL directly
                display_link = link
                instructions = [
                    '1. Copy DNS URL bên dưới',
                    '2. Vào Settings > General > VPN & Device Management',
                    '3. Chọn DNS > Configure DNS',
                    '4. Chọn Manual, xóa hết DNS cũ',
                    '5. Add Server, paste URL vừa copy',
                    '6. Save. Done! Gold được giữ mãi mãi 🎉'
                ]
            else:
                # NextDNS: Return Apple profile link
                display_link = link  # https://apple.nextdns.io/?profile={pid}
                instructions = [
                    '1. Nhấn vào link DNS bên dưới',
                    '2. Safari sẽ mở, nhấn "Allow"',
                    '3. Vào Settings > Profile Downloaded',
                    '4. Nhấn Install',
                    '5. Nhập passcode',
                    '6. Nhấn Install lần nữa',
                    '7. Done! Gold được giữ mãi mãi 🎉'
                ]
            
            # Build response with badge status
            response_data = {
                'success': True,
                'message': 'Kích hoạt thành công!',
                'redirect': f'/locket-success.html?session={session_id}',
                'dns_link': display_link,
                'dns_profile_id': pid,
                'dns_provider': dns_provider,
                'badge_set': badge_set,
                'instructions': instructions,
                'retention_info': {
                    'domains_blocked': 21,
                    'retention_rate': '99%',
                    'features': [
                        'Chặn 21 endpoints RevenueCat + Apple',
                        'Chặn analytics (stealth mode)',
                        'Chặn tất cả regional endpoints',
                        'Wildcard chặn subdomain mới'
                    ]
                }
            }
            
            # Add badge_error if badge setting failed
            if badge_error:
                response_data['badge_error'] = badge_error
            
            return jsonify(response_data)
        else:
            # Failed
            supabase.table('locket_activations').update({
                'status': 'failed',
                'error_message': msg_result,
                'completed_at': 'now()'
            }).eq('id', activation_id).execute()
            
            loop.close()
            
            return jsonify({
                'success': False,
                'message': f'Kích hoạt thất bại: {msg_result}'
            }), 500
        
    except Exception as e:
        print(f"❌ Error in activate_locket: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Lỗi: {str(e)}'
        }), 500

# ============================================
# DNS VERIFICATION ENDPOINT
# ============================================

@locket_web_bp.route('/api/verify-dns', methods=['POST', 'OPTIONS'])
def verify_dns():
    """
    DNS verification endpoint - accepts test results from client-side JavaScript
    
    Client tests:
    1. Connectivity to api.revenuecat.com (should fail if DNS works)
    2. Connectivity to google.com (should succeed as control)
    
    Returns verification result and updates activation records
    """
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        data = request.get_json()
        
        # Extract test results from client
        revenuecat_blocked = data.get('revenuecat_blocked', False)
        control_accessible = data.get('control_accessible', False)
        user_id = data.get('user_id')  # Optional: can be username or activation ID
        username = data.get('username')  # Locket username
        
        print(f"🔍 DNS Verification Request:")
        print(f"   - RevenueCat blocked: {revenuecat_blocked}")
        print(f"   - Control accessible: {control_accessible}")
        print(f"   - User ID: {user_id}")
        print(f"   - Username: {username}")
        
        # Import DNS verification service
        try:
            from api.services.dns_verification import DNSVerificationService
        except ImportError:
            from .services.dns_verification import DNSVerificationService
        
        # Create service instance
        dns_service = DNSVerificationService()
        
        # Run verification logic
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Use a dummy user_id if not provided (for testing)
        verification_user_id = user_id or 0
        
        verification_result = loop.run_until_complete(
            dns_service.verify_dns_blocking(
                verification_user_id,
                revenuecat_blocked,
                control_accessible
            )
        )
        
        # If username provided, update all activations for this user
        if username and verification_result['success']:
            try:
                supabase = get_supabase_client()
                if supabase:
                    # Get all activations for this username
                    activations_result = supabase.table('locket_activations')\
                        .select('id')\
                        .eq('locket_username', username)\
                        .execute()
                    
                    if activations_result.data:
                        # Update all activations
                        for activation in activations_result.data:
                            loop.run_until_complete(
                                dns_service.update_activation_verification_status(
                                    activation['id'],
                                    True
                                )
                            )
                        
                        print(f"✅ Updated {len(activations_result.data)} activations for username: {username}")
            except Exception as e:
                print(f"⚠️ Could not update activations: {e}")
        
        loop.close()
        
        # Return result to client
        return jsonify({
            'success': verification_result['success'],
            'revenuecat_blocked': verification_result['revenuecat_blocked'],
            'control_accessible': verification_result['control_accessible'],
            'reason': verification_result['reason'],
            'verified_at': verification_result['verified_at'],
            'message': verification_result['reason']
        })
        
    except Exception as e:
        print(f"❌ Error in verify_dns: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Lỗi kiểm tra DNS: {str(e)}',
            'reason': f'Verification error: {str(e)}'
        }), 500

@locket_web_bp.route('/api/verify-dns/test', methods=['GET'])
def verify_dns_test_page():
    """
    Return a simple test page for DNS verification
    Redirects to the test-dns-verification.html file
    """
    return jsonify({
        'success': True,
        'message': 'DNS verification test endpoint',
        'test_page': '/test-dns-verification.html',
        'api_endpoint': '/api/verify-dns',
        'instructions': [
            '1. Open test-dns-verification.html in your browser',
            '2. The page will automatically test connectivity',
            '3. Results will be sent to /api/verify-dns endpoint',
            '4. Check if RevenueCat is blocked and Google is accessible'
        ]
    })
