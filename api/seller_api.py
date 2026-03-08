"""
Seller API Module
Allows sellers to integrate SheerID verification into their websites
"""

import os
import uuid
import secrets
import requests
from datetime import datetime
from flask import Blueprint, request, jsonify
from functools import wraps

seller_bp = Blueprint('seller', __name__)

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_supabase_client():
    """Get Supabase client"""
    try:
        from .supabase_client import get_supabase_client as get_client
        return get_client()
    except:
        return None

def generate_api_key():
    """Generate a secure API key for seller"""
    return f"sk_{secrets.token_hex(24)}"

def get_seller_by_api_key(api_key):
    """Get seller by API key"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        result = supabase.table('sellers').select('*').eq('api_key', api_key).eq('is_active', True).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        print(f"Error getting seller: {e}")
        return None

def deduct_seller_credit(seller_id):
    """Deduct 1 credit from seller"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return False
        
        # Get current credits
        seller = supabase.table('sellers').select('credits').eq('id', seller_id).execute()
        if not seller.data:
            return False
        
        current_credits = seller.data[0].get('credits', 0)
        if current_credits < 1:
            return False
        
        # Deduct credit and increment total_used
        supabase.table('sellers').update({
            'credits': current_credits - 1,
            'total_used': supabase.table('sellers').select('total_used').eq('id', seller_id).execute().data[0].get('total_used', 0) + 1,
            'updated_at': datetime.now().isoformat()
        }).eq('id', seller_id).execute()
        
        return True
    except Exception as e:
        print(f"Error deducting credit: {e}")
        return False

def refund_seller_credit(seller_id):
    """Refund 1 credit to seller (when verification fails)"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return False
        
        seller = supabase.table('sellers').select('credits, total_used').eq('id', seller_id).execute()
        if not seller.data:
            return False
        
        current_credits = seller.data[0].get('credits', 0)
        total_used = seller.data[0].get('total_used', 0)
        
        supabase.table('sellers').update({
            'credits': current_credits + 1,
            'total_used': max(0, total_used - 1),
            'updated_at': datetime.now().isoformat()
        }).eq('id', seller_id).execute()
        
        return True
    except Exception as e:
        print(f"Error refunding credit: {e}")
        return False

def create_seller_job(seller_id, job_id, sheerid_url):
    """Create a seller job record"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        result = supabase.table('seller_jobs').insert({
            'seller_id': seller_id,
            'job_id': job_id,
            'sheerid_url': sheerid_url,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }).execute()
        
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error creating seller job: {e}")
        return None

def update_seller_job(job_id, status, result=None):
    """Update seller job status"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return False
        
        update_data = {
            'status': status,
            'updated_at': datetime.now().isoformat()
        }
        if result:
            update_data['result'] = result
        
        supabase.table('seller_jobs').update(update_data).eq('job_id', job_id).execute()
        return True
    except Exception as e:
        print(f"Error updating seller job: {e}")
        return False

def get_seller_job(job_id, seller_id):
    """Get seller job by job_id and seller_id"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        result = supabase.table('seller_jobs').select('*').eq('job_id', job_id).eq('seller_id', seller_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        print(f"Error getting seller job: {e}")
        return None

def send_webhook(webhook_url, data):
    """Send webhook notification to seller"""
    try:
        if not webhook_url:
            return False
        
        response = requests.post(
            webhook_url,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending webhook: {e}")
        return False

def validate_sheerid_verification_exists(url):
    """
    Validate if SheerID verification exists by calling SheerID API
    Returns: (is_valid, error_message, verification_data)
    """
    import re
    
    try:
        # Extract verificationId from URL
        verification_id = None
        
        # Try to get from query parameter first
        if 'verificationId=' in url:
            verification_id = url.split('verificationId=')[-1].split('&')[0]
        
        # If no verificationId in query, this might be a new verification (no ID yet)
        if not verification_id:
            print(f"⚠️ No verificationId in URL - this is a new verification request")
            return True, None, None  # Allow new verifications without ID
        
        # Validate format: must be 24 hex characters (MongoDB ObjectId)
        if not re.match(r'^[a-f0-9]{24}$', verification_id):
            print(f"❌ Invalid verificationId format: {verification_id}")
            return False, "Invalid verificationId format (must be 24 hex characters)", None
        
        # Call SheerID API to check if verification exists
        api_url = f"https://my.sheerid.com/rest/v2/verification/{verification_id}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Origin': 'https://services.sheerid.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        data = response.json()
        
        print(f"🔍 SheerID API response for {verification_id}: status={response.status_code}")
        
        if response.status_code == 200:
            current_step = data.get('currentStep', '')
            error_ids = data.get('errorIds', [])
            
            # Check for noVerification error
            if 'noVerification' in error_ids or current_step == 'error':
                error_msg = data.get('systemErrorMessage', 'Verification not found')
                print(f"❌ Verification not found: {error_msg}")
                return False, "Verification ID does not exist", None
            
            # Check if already completed (success)
            if current_step == 'success':
                print(f"✅ Verification {verification_id} already completed (success)")
                return True, "already_verified", data
            
            # Check if in docUpload state
            if current_step == 'docUpload':
                print(f"⚠️ Verification {verification_id} is in docUpload state")
                return False, "Verification is in docUpload state - needs to be reset", data
            
            # Valid verification in progress
            print(f"✅ Verification {verification_id} exists, step: {current_step}")
            return True, None, data
            
        elif response.status_code == 404:
            error_msg = data.get('systemErrorMessage', 'Verification not found')
            print(f"❌ Verification not found (404): {error_msg}")
            return False, "Verification ID does not exist", None
        else:
            print(f"⚠️ SheerID API returned {response.status_code}")
            # Don't block on API errors, allow verification to proceed
            return True, None, None
            
    except requests.exceptions.Timeout:
        print(f"⚠️ SheerID API timeout - allowing verification to proceed")
        return True, None, None  # Don't block on timeout
    except Exception as e:
        print(f"⚠️ Error validating verification: {e}")
        return True, None, None  # Don't block on errors

# ============================================
# API KEY AUTHENTICATION DECORATOR
# ============================================

def require_api_key(f):
    """Decorator to require valid API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'Missing API key. Include X-API-Key header.'
            }), 401
        
        seller = get_seller_by_api_key(api_key)
        if not seller:
            return jsonify({
                'success': False,
                'error': 'Invalid or inactive API key.'
            }), 401
        
        # Add seller to request context
        request.seller = seller
        return f(*args, **kwargs)
    
    return decorated_function

# ============================================
# API ENDPOINTS
# ============================================

@seller_bp.route('/api/seller/verify', methods=['POST'])
@require_api_key
def seller_verify():
    """
    Start a verification job
    
    Headers:
        X-API-Key: seller_api_key
    
    Body:
        {
            "sheerid_url": "https://services.sheerid.com/verify/...",
            "webhook_url": "https://your-site.com/callback" (optional)
        }
    
    Response:
        {
            "success": true,
            "job_id": "xxx-xxx-xxx",
            "status": "processing",
            "remaining_credits": 99
        }
    """
    try:
        seller = request.seller
        data = request.get_json() or {}
        
        sheerid_url = data.get('sheerid_url', '').strip()
        webhook_url = data.get('webhook_url', seller.get('webhook_url', ''))
        
        # Validate URL
        if not sheerid_url:
            return jsonify({
                'success': False,
                'error': 'Missing sheerid_url parameter'
            }), 400
        
        if 'sheerid.com' not in sheerid_url:
            return jsonify({
                'success': False,
                'error': 'Invalid SheerID URL'
            }), 400
        
        # Validate verificationId exists via SheerID API
        is_valid, error_msg, verification_data = validate_sheerid_verification_exists(sheerid_url)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'error': f'Invalid SheerID link: {error_msg}',
                'error_code': 'INVALID_VERIFICATION_ID'
            }), 400
        
        # Check if already verified
        if error_msg == 'already_verified':
            return jsonify({
                'success': True,
                'status': 'already_verified',
                'message': 'This verification link has already been completed successfully',
                'remaining_credits': seller.get('credits', 0)  # No credit deducted
            })
        
        # Check credits
        if seller.get('credits', 0) < 1:
            return jsonify({
                'success': False,
                'error': 'Insufficient credits. Please top up your account.',
                'remaining_credits': 0
            }), 402
        
        # Deduct credit first
        if not deduct_seller_credit(seller['id']):
            return jsonify({
                'success': False,
                'error': 'Failed to deduct credit'
            }), 500
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create seller job record
        create_seller_job(seller['id'], job_id, sheerid_url)
        
        # Call the verification function directly (not via HTTP)
        try:
            from .index import _submit_sheerid_verification
            
            # Prepare payload for verification
            verification_payload = {
                'url': sheerid_url,
                'job_id': job_id,
                'seller_id': seller['id'],
                'webhook_url': webhook_url,
                'verification_type': 'sheerid'
            }
            
            print(f"🏪 Seller {seller['id']} starting verification for job {job_id}")
            result = _submit_sheerid_verification(verification_payload)
            print(f"📋 Verification result for seller job: {result}")
            
            if result.get('success'):
                # Check for success indicators
                status = result.get('status', 'processing')
                current_step = result.get('currentStep', '')
                
                # Normalize status
                if current_step == 'success' or status in ['success', 'approved', 'completed']:
                    final_status = 'completed'
                else:
                    final_status = status if status else 'processing'
                
                print(f"📊 Seller job {job_id} final status: {final_status}")
                update_seller_job(job_id, final_status, result)
                
                # If completed immediately, send webhook
                if final_status == 'completed':
                    if webhook_url:
                        send_webhook(webhook_url, {
                            'event': 'verification.completed',
                            'job_id': job_id,
                            'status': 'success',
                            'data': result
                        })
                
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    'status': final_status,
                    'remaining_credits': seller.get('credits', 0) - 1
                })
            else:
                # Verification failed - refund credit
                refund_seller_credit(seller['id'])
                update_seller_job(job_id, 'failed', result)
                
                return jsonify({
                    'success': False,
                    'job_id': job_id,
                    'error': result.get('error', 'Verification failed'),
                    'remaining_credits': seller.get('credits', 0)  # Credit refunded
                })
                
        except requests.exceptions.Timeout:
            # Timeout - job may still be processing
            update_seller_job(job_id, 'processing')
            return jsonify({
                'success': True,
                'job_id': job_id,
                'status': 'processing',
                'message': 'Verification is being processed. Check status with /api/seller/status/{job_id}',
                'remaining_credits': seller.get('credits', 0) - 1
            })
            
        except Exception as e:
            # Error - refund credit
            refund_seller_credit(seller['id'])
            update_seller_job(job_id, 'failed', {'error': str(e)})
            
            return jsonify({
                'success': False,
                'job_id': job_id,
                'error': f'Verification error: {str(e)}',
                'remaining_credits': seller.get('credits', 0)
            }), 500
            
    except Exception as e:
        print(f"Error in seller_verify: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@seller_bp.route('/api/seller/status/<job_id>', methods=['GET'])
@require_api_key
def seller_job_status(job_id):
    """
    Get verification job status
    
    Headers:
        X-API-Key: seller_api_key
    
    Response:
        {
            "success": true,
            "job_id": "xxx-xxx-xxx",
            "status": "completed",
            "result": {...}
        }
    """
    try:
        seller = request.seller
        
        job = get_seller_job(job_id, seller['id'])
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': job.get('status', 'unknown'),
            'result': job.get('result'),
            'created_at': job.get('created_at'),
            'updated_at': job.get('updated_at')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@seller_bp.route('/api/seller/balance', methods=['GET'])
@require_api_key
def seller_balance():
    """
    Get seller account balance
    
    Headers:
        X-API-Key: seller_api_key
    
    Response:
        {
            "success": true,
            "credits": 100,
            "total_used": 50,
            "name": "Seller Name"
        }
    """
    try:
        seller = request.seller
        
        return jsonify({
            'success': True,
            'name': seller.get('name'),
            'credits': seller.get('credits', 0),
            'total_used': seller.get('total_used', 0),
            'rate_limit': seller.get('rate_limit', 10)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@seller_bp.route('/api/seller/jobs', methods=['GET'])
@require_api_key
def seller_jobs_list():
    """
    Get list of seller's verification jobs
    
    Headers:
        X-API-Key: seller_api_key
    
    Query params:
        limit: number of jobs to return (default 20)
        offset: pagination offset (default 0)
        status: filter by status (optional)
    
    Response:
        {
            "success": true,
            "jobs": [...],
            "total": 100
        }
    """
    try:
        seller = request.seller
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        status_filter = request.args.get('status')
        
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({'success': False, 'error': 'Database unavailable'}), 500
        
        query = supabase.table('seller_jobs').select('*', count='exact').eq('seller_id', seller['id'])
        
        if status_filter:
            query = query.eq('status', status_filter)
        
        result = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        return jsonify({
            'success': True,
            'jobs': result.data or [],
            'total': result.count or 0,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# ADMIN FUNCTIONS (for Telegram bot)
# ============================================

def create_seller(name, email=None, initial_credits=0, webhook_url=None, telegram_id=None):
    """Create a new seller account"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None, "Database unavailable"
        
        api_key = generate_api_key()
        
        insert_data = {
            'name': name,
            'email': email,
            'api_key': api_key,
            'credits': initial_credits,
            'webhook_url': webhook_url,
            'is_active': True,
            'created_at': datetime.now().isoformat()
        }
        
        # Add telegram_id if provided (for cash-to-credits conversion)
        if telegram_id:
            insert_data['telegram_id'] = telegram_id
        
        result = supabase.table('sellers').insert(insert_data).execute()
        
        if result.data:
            return result.data[0], None
        return None, "Failed to create seller"
        
    except Exception as e:
        return None, str(e)

def add_seller_credits(seller_id_or_api_key, credits):
    """Add credits to seller account"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return False, "Database unavailable"
        
        # Find seller by ID or API key
        if isinstance(seller_id_or_api_key, int):
            seller = supabase.table('sellers').select('*').eq('id', seller_id_or_api_key).execute()
        else:
            seller = supabase.table('sellers').select('*').eq('api_key', seller_id_or_api_key).execute()
        
        if not seller.data:
            return False, "Seller not found"
        
        current_credits = seller.data[0].get('credits', 0)
        new_credits = current_credits + credits
        
        supabase.table('sellers').update({
            'credits': new_credits,
            'updated_at': datetime.now().isoformat()
        }).eq('id', seller.data[0]['id']).execute()
        
        return True, f"Added {credits} credits. New balance: {new_credits}"
        
    except Exception as e:
        return False, str(e)

def get_all_sellers():
    """Get all sellers"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return []
        
        result = supabase.table('sellers').select('*').order('created_at', desc=True).execute()
        return result.data or []
        
    except Exception as e:
        print(f"Error getting sellers: {e}")
        return []

def toggle_seller_status(seller_id, is_active):
    """Enable/disable seller"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return False
        
        supabase.table('sellers').update({
            'is_active': is_active,
            'updated_at': datetime.now().isoformat()
        }).eq('id', seller_id).execute()
        
        return True
    except Exception as e:
        print(f"Error toggling seller: {e}")
        return False
