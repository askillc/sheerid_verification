"""
SheerID Bot API Webhook Handler

Handles webhook callbacks from SheerID Bot API when verification jobs complete.
Verifies signature, updates job status, deducts balance on success, and notifies user.

Requirements: 5.1-5.5
"""

import os
import json
import hmac
import hashlib
from flask import Flask, request, jsonify
from datetime import datetime


# Multilingual messages for webhook notifications
WEBHOOK_MESSAGES = {
    'success': {
        'vi': """🎉 Xác minh {type_name} thành công!

✅ Trạng thái: Đã xác minh
🆔 Mã: {job_id}
💰 Đã trừ: {cost_text}
{balance_text}

🎓 Bạn đã có thể sử dụng ưu đãi!""",
        'en': """🎉 {type_name} verification successful!

✅ Status: Verified
🆔 Code: {job_id}
💰 Deducted: {cost_text}
{balance_text}

🎓 You can now use the benefits!""",
        'zh': """🎉 {type_name} 验证成功！

✅ 状态：已验证
🆔 代码: {job_id}
💰 已扣除: {cost_text}
{balance_text}

🎓 您现在可以使用优惠了！"""
    },
    'vip_success': {
        'vi': """🎉 Xác minh {type_name} thành công!

✅ Trạng thái: Đã xác minh
🆔 Mã: {job_id}
👑 VIP: MIỄN PHÍ - Không trừ tiền

🎓 Bạn đã có thể sử dụng ưu đãi!""",
        'en': """🎉 {type_name} verification successful!

✅ Status: Verified
🆔 Code: {job_id}
👑 VIP: FREE - No charge

🎓 You can now use the benefits!""",
        'zh': """🎉 {type_name} 验证成功！

✅ 状态：已验证
🆔 代码: {job_id}
👑 VIP: 免费 - 不收费

🎓 您现在可以使用优惠了！"""
    },
    'failed': {
        'vi': """❌ Xác minh {type_name} thất bại

🔍 Lý do: {reason}
🆔 Mã: {job_id}

💰 Hoàn: +10 cash
💵 Số dư: {new_balance} cash

💡 Vui lòng thử lại với link khác.

📖 Hướng dẫn lấy link mới: https://t.me/channel_sheerid_vip_bot/265""",
        'en': """❌ {type_name} verification failed

🔍 Reason: {reason}
🆔 Code: {job_id}

💰 Refunded: +10 cash
💵 Balance: {new_balance} cash

💡 Please try again with a different link.

📖 Guide to get new link: https://t.me/channel_sheerid_vip_bot/265""",
        'zh': """❌ {type_name} 验证失败

🔍 原因：{reason}
🆔 代码: {job_id}

💰 已退款：+10 现金
💵 余额：{new_balance} 现金

💡 请使用其他链接重试。

📖 获取新链接指南: https://t.me/channel_sheerid_vip_bot/265"""
    },
    'fraud_failed': {
        'vi': """❌ Xác minh {type_name} thất bại

🔍 Lý do: {reason}
🆔 Mã: {job_id}

💰 Hoàn: +10 cash
💵 Số dư: {new_balance} cash

⚠️ Link của bạn bị lỗi, vui lòng lấy link mới đúng cách hoặc đổi trình duyệt và VPN khác để có thể verify.

📖 Hướng dẫn lấy link mới: https://t.me/channel_sheerid_vip_bot/265""",
        'en': """❌ {type_name} verification failed

🔍 Reason: {reason}
🆔 Code: {job_id}

💰 Refunded: +10 cash
💵 Balance: {new_balance} cash

⚠️ Your link has an error. Please get a new link properly or change your browser and VPN to verify.

📖 Guide to get new link: https://t.me/channel_sheerid_vip_bot/265""",
        'zh': """❌ {type_name} 验证失败

🔍 原因：{reason}
🆔 代码: {job_id}

💰 已退款：+10 现金
💵 余额：{new_balance} 现金

⚠️ 您的链接有错误，请正确获取新链接或更换浏览器和VPN以进行验证。

📖 获取新链接指南: https://t.me/channel_sheerid_vip_bot/265"""
    }
}

# Verification type display names
VERIFICATION_TYPE_NAMES = {
    'gemini': {'vi': 'Gemini', 'en': 'Gemini', 'zh': 'Gemini'},
    'perplexity': {'vi': 'Perplexity', 'en': 'Perplexity', 'zh': 'Perplexity'},
    'teacher': {'vi': 'Teacher', 'en': 'Teacher', 'zh': 'Teacher'}
}

DEFAULT_LANGUAGE = 'vi'


def verify_webhook_signature(payload: dict, signature: str, api_key: str) -> bool:
    """
    Verify webhook signature using HMAC-SHA256
    
    The signature is computed as:
    HMAC-SHA256(JSON.stringify(payload, sorted_keys), api_key)
    
    Args:
        payload: Webhook payload dictionary
        signature: X-Webhook-Signature header value
        api_key: SheerID Bot API key
    
    Returns:
        True if signature is valid, False otherwise
    
    Requirements: 5.1, 5.4
    """
    if not signature or not api_key:
        print(f"❌ Webhook signature or API key missing")
        return False
    
    try:
        # Serialize payload with sorted keys for consistent signature
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        # Compute HMAC-SHA256 signature
        expected_signature = hmac.new(
            key=api_key.encode('utf-8'),
            msg=payload_str.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Compare signatures (constant-time comparison)
        is_valid = hmac.compare_digest(signature.lower(), expected_signature.lower())
        
        if is_valid:
            print(f"✅ Webhook signature verified")
        else:
            print(f"❌ Webhook signature mismatch")
            print(f"   Expected: {expected_signature}")
            print(f"   Received: {signature}")
        
        return is_valid
        
    except Exception as e:
        print(f"❌ Error verifying webhook signature: {e}")
        return False


def get_sheerid_bot_job_by_api_id(api_job_id: str):
    """
    Get SheerID Bot job from database by API job_id
    
    Args:
        api_job_id: API Job ID (api_xxx format) to look up
    
    Returns:
        Job record dict or None
    """
    try:
        try:
            from api.supabase_client import get_supabase_client
        except ImportError:
            from supabase_client import get_supabase_client
        client = get_supabase_client()
        
        if not client:
            print(f"❌ Supabase client not available")
            return None
        
        # Find by api_job_id in result_details
        result = client.table('sheerid_bot_jobs').select('*').execute()
        if result.data:
            for job in result.data:
                result_details = job.get('result_details') or {}
                if isinstance(result_details, str):
                    try:
                        result_details = json.loads(result_details)
                    except:
                        result_details = {}
                if result_details.get('api_job_id') == api_job_id:
                    print(f"✅ Found job by api_job_id: {api_job_id} -> internal job_id: {job.get('job_id')}")
                    return job
        
        print(f"❌ Job with api_job_id {api_job_id} not found")
        return None
        
    except Exception as e:
        print(f"❌ Error getting SheerID Bot job by api_id: {e}")
        return None


def get_sheerid_bot_job(job_id: str):
    """
    Get SheerID Bot job from database by job_id
    
    Args:
        job_id: Job ID to look up
    
    Returns:
        Job record dict or None
    """
    try:
        try:
            from api.supabase_client import get_supabase_client
        except ImportError:
            from supabase_client import get_supabase_client
        client = get_supabase_client()
        
        if not client:
            print(f"❌ Supabase client not available")
            return None
        
        # Try to find by job_id first
        result = client.table('sheerid_bot_jobs').select('*').eq('job_id', job_id).limit(1).execute()
        
        if result.data:
            return result.data[0]
        
        # Also try to find by api_job_id in result_details
        # This handles case where webhook uses API's job_id instead of our internal job_id
        result = client.table('sheerid_bot_jobs').select('*').execute()
        if result.data:
            for job in result.data:
                result_details = job.get('result_details') or {}
                if isinstance(result_details, str):
                    try:
                        result_details = json.loads(result_details)
                    except:
                        result_details = {}
                if result_details.get('api_job_id') == job_id:
                    return job
        
        print(f"❌ Job {job_id} not found in sheerid_bot_jobs")
        return None
        
    except Exception as e:
        print(f"❌ Error getting SheerID Bot job: {e}")
        return None


def update_sheerid_bot_job_status(job_id: str, status: str, result_details: dict = None):
    """
    Update SheerID Bot job status in database
    
    Args:
        job_id: Job ID to update
        status: New status ('success', 'failed', 'processing')
        result_details: Additional result details to store
    
    Returns:
        True on success, False on failure
    
    Requirements: 5.2, 5.3
    """
    try:
        try:
            from api.supabase_client import get_supabase_client
        except ImportError:
            from supabase_client import get_supabase_client
        client = get_supabase_client()
        
        if not client:
            return False
        
        update_data = {
            'status': status,
            'updated_at': datetime.now().isoformat()
        }
        
        if status in ['success', 'failed', 'cancelled', 'invalid_link']:
            update_data['completed_at'] = datetime.now().isoformat()
        
        if result_details:
            # Merge with existing result_details
            job = get_sheerid_bot_job(job_id)
            if job:
                existing_details = job.get('result_details') or {}
                if isinstance(existing_details, str):
                    try:
                        existing_details = json.loads(existing_details)
                    except:
                        existing_details = {}
                existing_details.update(result_details)
                update_data['result_details'] = existing_details
            else:
                update_data['result_details'] = result_details
        
        client.table('sheerid_bot_jobs').update(update_data).eq('job_id', job_id).execute()
        print(f"✅ Updated SheerID Bot job status: {job_id} -> {status}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating SheerID Bot job status: {e}")
        return False


def deduct_user_balance(user_id: int, amount: int, description: str = ''):
    """
    Deduct cash from user balance
    
    Args:
        user_id: User ID
        amount: Amount to deduct (positive number)
        description: Transaction description
    
    Returns:
        New balance on success, None on failure
    
    Requirements: 1.3, 2.3, 3.3
    """
    try:
        try:
            from api.supabase_client import get_supabase_client
        except ImportError:
            from supabase_client import get_supabase_client
        client = get_supabase_client()
        
        if not client:
            return None
        
        # Get current balance
        result = client.table('users').select('id, cash, coins').eq('id', user_id).limit(1).execute()
        
        if not result.data:
            print(f"❌ User {user_id} not found")
            return None
        
        user = result.data[0]
        current_cash = int(user.get('cash') or 0)
        new_cash = current_cash - amount
        
        if new_cash < 0:
            print(f"❌ Insufficient balance: {current_cash} < {amount}")
            return None
        
        # Update balance
        update_result = client.table('users').update({
            'cash': new_cash,
            'updated_at': datetime.now().isoformat()
        }).eq('id', user_id).execute()
        
        if not update_result.data:
            print(f"❌ Failed to update user balance")
            return None
        
        # Record transaction
        try:
            client.table('transactions').insert({
                'user_id': user_id,
                'type': 'verification',
                'amount': -amount,
                'coins': 0,
                'description': description or f'SheerID Bot verification: -{amount} cash',
                'status': 'completed',
                'created_at': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            print(f"⚠️ Could not record transaction: {e}")
        
        print(f"✅ Deducted {amount} cash from user {user_id}: {current_cash} -> {new_cash}")
        return new_cash
        
    except Exception as e:
        print(f"❌ Error deducting user balance: {e}")
        return None


def send_telegram_notification(telegram_id: int, message: str):
    """
    Send Telegram notification to user
    
    Args:
        telegram_id: User's Telegram ID
        message: Message to send
    
    Returns:
        True on success, False on failure
    """
    try:
        import requests
        
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print(f"❌ TELEGRAM_BOT_TOKEN not configured")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # Send plain text without any parse_mode to avoid markdown parsing issues
        # This is the safest approach - no escaping needed
        data = {
            'chat_id': telegram_id,
            'text': message,
            'disable_web_page_preview': False  # Allow link preview for guide
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Sent Telegram notification to {telegram_id}")
            return True
        else:
            print(f"❌ Telegram API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending Telegram notification: {e}")
        return False


def get_user_language(telegram_id: int) -> str:
    """Get user's preferred language from database"""
    try:
        try:
            from api.supabase_client import get_supabase_client
        except ImportError:
            from supabase_client import get_supabase_client
        client = get_supabase_client()
        
        if client:
            result = client.table('users').select('language').eq('telegram_id', str(telegram_id)).limit(1).execute()
            if result.data and len(result.data) > 0:
                return result.data[0].get('language', DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE
    except Exception as e:
        print(f"Error getting user language: {e}")
    
    return DEFAULT_LANGUAGE


def handle_sheerid_webhook(request_data):
    """
    Main webhook handler for SheerID Bot API callbacks
    
    Expected payload format:
    {
        "job_id": "string",
        "status": "success" | "failed",
        "result_details": {
            "verification_id": "string",
            "error_message": "string" (if failed)
        }
    }
    
    Args:
        request_data: Flask request object
    
    Returns:
        JSON response
    
    Requirements: 5.1-5.5
    """
    try:
        print(f"📥 Received SheerID Bot webhook")
        
        # Get API key for signature verification
        api_key = os.getenv('SHEERID_BOT_API_KEY')
        if not api_key:
            print(f"❌ SHEERID_BOT_API_KEY not configured")
            return jsonify({'error': 'Server configuration error'}), 500
        
        # Parse payload
        try:
            payload = request_data.get_json()
        except Exception as e:
            print(f"❌ Invalid JSON payload: {e}")
            return jsonify({'error': 'Invalid JSON payload'}), 400
        
        if not payload:
            print(f"❌ Empty payload")
            return jsonify({'error': 'Empty payload'}), 400
        
        print(f"📋 Webhook payload: {json.dumps(payload, indent=2)}")
        
        # Verify signature - Requirements: 5.1, 5.4
        signature = request_data.headers.get('X-Webhook-Signature')
        
        if not verify_webhook_signature(payload, signature, api_key):
            print(f"🚨 SECURITY WARNING: Invalid webhook signature!")
            return jsonify({'error': 'Invalid signature'}), 401
        
        # Extract job info
        job_id = payload.get('job_id')
        status = payload.get('status', '').lower()
        result_details = payload.get('result_details', {})
        
        if not job_id:
            print(f"❌ Missing job_id in payload")
            return jsonify({'error': 'Missing job_id'}), 400
        
        # Map API statuses to internal statuses
        # Keep invalid_link as-is for database
        # expired -> cancelled (user's link issue, not system failure)
        # error -> failed (system error)
        # cancelled, canceled -> cancelled (with 2 L's for database constraint)
        # rejected, rejected_late_stage -> failed (fraud rejection)
        original_status = payload.get('status', '')
        if status == 'invalid_link':
            # Keep invalid_link status for database
            if not result_details:
                result_details = {}
            result_details['error_message'] = "Link không hợp lệ"
        elif status in ['cancelled', 'canceled', 'expired']:
            status = 'cancelled'  # Use 2 L's for database constraint
            if not result_details:
                result_details = {}
            result_details['original_status'] = original_status
            if original_status == 'expired':
                result_details['error_message'] = "Link đã hết hạn"
            else:
                result_details['error_message'] = "Xác minh đã bị hủy"
        elif status in ['error']:
            status = 'failed'
            if not result_details:
                result_details = {}
            result_details['original_status'] = original_status
            result_details['error_message'] = "Lỗi hệ thống"
        elif status in ['rejected', 'rejected_late_stage']:
            status = 'failed'
            if not result_details:
                result_details = {}
            result_details['original_status'] = original_status
            if original_status == 'rejected_late_stage':
                result_details['error_message'] = "Xác minh bị từ chối ở giai đoạn cuối (FRAUD)"
            else:
                result_details['error_message'] = "Xác minh bị từ chối (FRAUD)"
            result_details['fraud_rejection'] = True
        
        if status not in ['success', 'failed', 'cancelled', 'invalid_link', 'processing']:
            print(f"❌ Invalid status: {status}")
            return jsonify({'error': 'Invalid status'}), 400
        
        # Get job from database
        # API sends api_xxx job ID, need to find by api_job_id
        api_job_id = job_id  # This is the API's job ID
        job = get_sheerid_bot_job_by_api_id(api_job_id)
        
        # If not found by api_job_id, try internal job_id
        if not job:
            job = get_sheerid_bot_job(job_id)
        
        if not job:
            print(f"❌ Job {job_id} not found")
            return jsonify({'error': 'Job not found'}), 404
        
        # Use internal job_id for display and updates
        internal_job_id = job.get('job_id')
        
        # Check if job already completed (prevent duplicate processing)
        current_status = job.get('status', '')
        if current_status in ['success', 'failed', 'cancelled', 'invalid_link']:
            print(f"⚠️ Job {internal_job_id} already completed with status: {current_status}")
            return jsonify({'message': 'Job already processed'}), 200
        
        # Get user info
        user_id = job.get('user_id')
        telegram_id = job.get('telegram_id')
        verification_type = job.get('verification_type', 'gemini')
        cost = job.get('cost', 10)
        payment_method = job.get('payment_method', 'cash')  # Get payment method from job
        
        # Check if user is VIP
        is_vip = False
        try:
            from .telegram import get_user
            user = get_user(telegram_id)
            if user:
                is_vip = user.get('is_vip', False)
                # Check VIP expiry if exists
                vip_expiry = user.get('vip_expiry')
                if is_vip and vip_expiry:
                    from datetime import datetime
                    try:
                        if isinstance(vip_expiry, str):
                            expiry_date = datetime.fromisoformat(vip_expiry.replace('Z', '+00:00'))
                        else:
                            expiry_date = vip_expiry
                        if expiry_date < datetime.now(expiry_date.tzinfo):
                            is_vip = False
                            print(f"⚠️ User {telegram_id} VIP expired")
                    except Exception as e:
                        print(f"⚠️ Error checking VIP expiry: {e}")
                
                if is_vip:
                    print(f"👑 User {telegram_id} is VIP - verification will be FREE")
        except Exception as e:
            print(f"⚠️ Error checking VIP status: {e}")
        
        # Get user language
        user_lang = get_user_language(int(telegram_id)) if telegram_id else DEFAULT_LANGUAGE
        
        # Get type display name
        type_names = VERIFICATION_TYPE_NAMES.get(verification_type, VERIFICATION_TYPE_NAMES['gemini'])
        type_name = type_names.get(user_lang, type_names['vi'])
        
        # Store verification_id if provided - Requirements: 5.5
        if result_details.get('verification_id'):
            result_details['verification_id'] = result_details['verification_id']
        
        # Update job status using internal job_id
        update_sheerid_bot_job_status(internal_job_id, status, result_details)
        
        # Handle success - Requirements: 5.2
        if status == 'success':
            # Check if user is VIP - VIP users get FREE verification (refund the hold)
            if is_vip:
                # VIP user - refund the hold (coins or cash)
                try:
                    from supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    if supabase and user_id:
                        if payment_method == "coins":
                            # Refund 25 coins (was held upfront)
                            user_result = supabase.table('users').select('coins').eq('id', user_id).execute()
                            if user_result.data:
                                current_coins = user_result.data[0].get('coins', 0)
                                new_coins = current_coins + 25
                                supabase.table('users').update({'coins': new_coins}).eq('id', user_id).execute()
                                print(f"💰 Refunded 25 coins hold to VIP user {user_id}. New balance: {new_coins}")
                        else:
                            # Refund 10 cash (was held upfront)
                            user_result = supabase.table('users').select('cash').eq('id', user_id).execute()
                            if user_result.data:
                                current_cash = user_result.data[0].get('cash', 0)
                                new_cash = current_cash + 10
                                supabase.table('users').update({'cash': new_cash}).eq('id', user_id).execute()
                                print(f"💰 Refunded 10 cash hold to VIP user {user_id}. New balance: {new_cash}")
                except Exception as e:
                    print(f"❌ Error refunding VIP hold: {e}")
                
                print(f"👑 VIP user {telegram_id} - FREE verification (refunded hold)")
                
                # Send VIP success notification
                msg_template = WEBHOOK_MESSAGES['vip_success'].get(user_lang, WEBHOOK_MESSAGES['vip_success']['vi'])
                message = msg_template.format(
                    type_name=type_name,
                    job_id=internal_job_id
                )
                send_telegram_notification(int(telegram_id), message)
                
                print(f"✅ Webhook processed successfully: job={internal_job_id}, status=success, VIP=FREE (refunded)")
            else:
                # Regular user - payment already deducted upfront, just confirm success
                print(f"✅ Regular user {telegram_id} - payment already deducted upfront")
                
                # Get current balance for display
                try:
                    from .telegram import get_user
                    user = get_user(telegram_id)
                    if user:
                        if payment_method == "coins":
                            new_balance_coins = user.get('coins', 0)
                            new_balance_cash = user.get('cash', 0)
                            cost_text = "25 Xu"
                            balance_text = f"🪙 Xu: {new_balance_coins} | 💵 Cash: {new_balance_cash}"
                        else:
                            new_balance_cash = user.get('cash', 0)
                            new_balance_coins = user.get('coins', 0)
                            cost_text = f"{cost} Cash"
                            balance_text = f"💵 Cash: {new_balance_cash} | 🪙 Xu: {new_balance_coins}"
                    else:
                        cost_text = f"{cost} {'Xu' if payment_method == 'coins' else 'Cash'}"
                        balance_text = "💵 Số dư: N/A"
                except:
                    cost_text = f"{cost} {'Xu' if payment_method == 'coins' else 'Cash'}"
                    balance_text = "💵 Số dư: N/A"
                
                # Send success notification with internal job_id
                msg_template = WEBHOOK_MESSAGES['success'].get(user_lang, WEBHOOK_MESSAGES['success']['vi'])
                message = msg_template.format(
                    type_name=type_name,
                    job_id=internal_job_id,
                    cost_text=cost_text,
                    balance_text=balance_text
                )
                send_telegram_notification(int(telegram_id), message)
                
                print(f"✅ Webhook processed successfully: job={internal_job_id}, status=success, payment_already_deducted")
        
        # Handle cancellation - Requirements: 5.3
        elif status == 'cancelled':
            error_message = result_details.get('error_message', 'Xác minh đã bị hủy')
            
            # REFUND payment for ALL users (both VIP and non-VIP) when verification is cancelled
            new_balance = 0
            refund_amount = 0
            balance_type = "cash"
            
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase and user_id:
                    if payment_method == "coins":
                        # Refund 25 coins
                        user_result = supabase.table('users').select('coins').eq('id', user_id).execute()
                        if user_result.data:
                            current_coins = user_result.data[0].get('coins', 0)
                            new_balance = current_coins + 25
                            refund_amount = 25
                            balance_type = "xu"
                            supabase.table('users').update({'coins': new_balance}).eq('id', user_id).execute()
                            print(f"💰 Refunded 25 coins to user {user_id} (canceled). New balance: {new_balance}")
                    else:
                        # Refund 10 cash
                        user_result = supabase.table('users').select('cash').eq('id', user_id).execute()
                        if user_result.data:
                            current_cash = user_result.data[0].get('cash', 0)
                            new_balance = current_cash + 10
                            refund_amount = 10
                            balance_type = "cash"
                            supabase.table('users').update({'cash': new_balance}).eq('id', user_id).execute()
                            if is_vip:
                                print(f"💰 Refunded 10 cash hold to VIP user {user_id} (canceled). New balance: {new_balance}")
                            else:
                                print(f"💰 Refunded 10 cash to user {user_id} (canceled). New balance: {new_balance}")
            except Exception as e:
                print(f"❌ Error refunding payment: {e}")
            
            # Send cancellation notification
            msg_template = WEBHOOK_MESSAGES['failed'].get(user_lang, WEBHOOK_MESSAGES['failed']['vi'])
            message = msg_template.format(
                type_name=type_name,
                job_id=internal_job_id,
                reason=error_message,
                new_balance=new_balance
            )
            send_telegram_notification(int(telegram_id), message)
            
            print(f"✅ Webhook processed: job={internal_job_id}, status=cancelled, reason={error_message}, refunded={refund_amount} {balance_type}, new_balance={new_balance}")
        
        # Handle invalid_link - Requirements: 5.3
        elif status == 'invalid_link':
            error_message = result_details.get('error_message', 'Link không hợp lệ')
            
            # REFUND payment for ALL users (both VIP and non-VIP) when link is invalid
            new_balance = 0
            refund_amount = 0
            balance_type = "cash"
            
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase and user_id:
                    if payment_method == "coins":
                        # Refund 25 coins
                        user_result = supabase.table('users').select('coins').eq('id', user_id).execute()
                        if user_result.data:
                            current_coins = user_result.data[0].get('coins', 0)
                            new_balance = current_coins + 25
                            refund_amount = 25
                            balance_type = "xu"
                            supabase.table('users').update({'coins': new_balance}).eq('id', user_id).execute()
                            print(f"💰 Refunded 25 coins to user {user_id} (invalid_link). New balance: {new_balance}")
                    else:
                        # Refund 10 cash
                        user_result = supabase.table('users').select('cash').eq('id', user_id).execute()
                        if user_result.data:
                            current_cash = user_result.data[0].get('cash', 0)
                            new_balance = current_cash + 10
                            refund_amount = 10
                            balance_type = "cash"
                            supabase.table('users').update({'cash': new_balance}).eq('id', user_id).execute()
                            if is_vip:
                                print(f"💰 Refunded 10 cash hold to VIP user {user_id} (invalid_link). New balance: {new_balance}")
                            else:
                                print(f"💰 Refunded 10 cash to user {user_id} (invalid_link). New balance: {new_balance}")
            except Exception as e:
                print(f"❌ Error refunding payment: {e}")
            
            # Send invalid link notification
            msg_template = WEBHOOK_MESSAGES['failed'].get(user_lang, WEBHOOK_MESSAGES['failed']['vi'])
            message = msg_template.format(
                type_name=type_name,
                job_id=internal_job_id,
                reason=error_message,
                new_balance=new_balance
            )
            send_telegram_notification(int(telegram_id), message)
            
            print(f"✅ Webhook processed: job={internal_job_id}, status=invalid_link, reason={error_message}, refunded={refund_amount} {balance_type}, new_balance={new_balance}")
        
        # Handle failure - Requirements: 5.3
        elif status == 'failed':
            error_message = result_details.get('error_message', 'Unknown error')
            is_fraud = result_details.get('fraud_rejection', False)
            
            # REFUND payment for ALL users (both VIP and non-VIP) when verification fails
            new_balance = 0
            refund_amount = 0
            balance_type = "cash"
            
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase and user_id:
                    if payment_method == "coins":
                        # Refund 25 coins
                        user_result = supabase.table('users').select('coins').eq('id', user_id).execute()
                        if user_result.data:
                            current_coins = user_result.data[0].get('coins', 0)
                            new_balance = current_coins + 25
                            refund_amount = 25
                            balance_type = "xu"
                            supabase.table('users').update({'coins': new_balance}).eq('id', user_id).execute()
                            print(f"💰 Refunded 25 coins to user {user_id} (failed). New balance: {new_balance}")
                    else:
                        # Refund 10 cash
                        user_result = supabase.table('users').select('cash').eq('id', user_id).execute()
                        if user_result.data:
                            current_cash = user_result.data[0].get('cash', 0)
                            new_balance = current_cash + 10
                            refund_amount = 10
                            balance_type = "cash"
                            supabase.table('users').update({'cash': new_balance}).eq('id', user_id).execute()
                            if is_vip:
                                print(f"💰 Refunded 10 cash hold to VIP user {user_id} (failed). New balance: {new_balance}")
                            else:
                                print(f"💰 Refunded 10 cash to user {user_id} (failed). New balance: {new_balance}")
            except Exception as e:
                print(f"❌ Error refunding payment: {e}")
            
            # Use fraud_failed message template if this is a fraud rejection
            if is_fraud:
                msg_template = WEBHOOK_MESSAGES['fraud_failed'].get(user_lang, WEBHOOK_MESSAGES['fraud_failed']['vi'])
            else:
                msg_template = WEBHOOK_MESSAGES['failed'].get(user_lang, WEBHOOK_MESSAGES['failed']['vi'])
            
            # Send failure notification with refund info and new balance
            message = msg_template.format(
                type_name=type_name,
                job_id=internal_job_id,
                reason=error_message,
                new_balance=new_balance
            )
            send_telegram_notification(int(telegram_id), message)
            
            print(f"✅ Webhook processed: job={internal_job_id}, status=failed, fraud={is_fraud}, reason={error_message}, refunded={refund_amount} {balance_type}, new_balance={new_balance}")
        
        return jsonify({'message': 'Webhook processed successfully'}), 200
        
    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500


# Flask app for Vercel serverless function
app = Flask(__name__)


@app.route('/api/sheerid-webhook', methods=['POST'])
def sheerid_webhook_endpoint():
    """
    Webhook endpoint for SheerID Bot API
    
    Route: POST /api/sheerid-webhook
    
    Requirements: 5.1
    """
    return handle_sheerid_webhook(request)
