"""
Simple Red Envelope API - No external dependencies
Just fetch from Supabase and return
"""

from flask import Blueprint, jsonify, request
import os

red_envelope_simple_bp = Blueprint('red_envelope_simple', __name__)

def get_supabase_client():
    """Get Supabase client"""
    try:
        from supabase import create_client
        url = os.environ.get('SUPABASE_URL')
        # Try both SUPABASE_KEY and SUPABASE_ANON_KEY
        key = os.environ.get('SUPABASE_KEY') or os.environ.get('SUPABASE_ANON_KEY')
        
        print(f"🔍 Supabase URL exists: {bool(url)}")
        print(f"🔍 Supabase KEY exists: {bool(key)}")
        
        if url and key:
            client = create_client(url, key)
            print(f"✅ Supabase client created successfully")
            return client
        else:
            print(f"❌ Missing Supabase credentials: URL={bool(url)}, KEY={bool(key)}")
    except Exception as e:
        print(f"❌ Supabase client error: {e}")
        import traceback
        traceback.print_exc()
    return None

@red_envelope_simple_bp.route('/api/red-envelope/unclaimed', methods=['GET'])
def get_unclaimed():
    """Get unclaimed envelopes - only show envelopes that have reached spawn_time"""
    try:
        print("📥 GET /api/red-envelope/unclaimed called")
        
        supabase = get_supabase_client()
        if not supabase:
            print("❌ Supabase client not available")
            return jsonify({'success': False, 'error': 'Database not available', 'envelopes': [], 'count': 0})
        
        # Get current time
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc).isoformat()
        
        print(f"🔍 Querying red_envelopes table (current time: {current_time})...")
        # Query unclaimed envelopes that have reached spawn_time
        result = supabase.table('red_envelopes').select('*').is_('claimed_by', 'null').lte('spawn_time', current_time).execute()
        
        print(f"📊 Query result: {len(result.data) if result.data else 0} envelopes found (spawn_time <= now)")
        
        envelopes = []
        if result.data:
            for env in result.data:
                envelopes.append({
                    'id': env.get('id')
                    # reward_amount and spawn_time intentionally hidden for security
                    # Users should not know the amount or spawn time before claiming
                })
        
        print(f"✅ Returning {len(envelopes)} unclaimed envelopes (visible now)")
        return jsonify({
            'success': True,
            'envelopes': envelopes,
            'count': len(envelopes)
        })
        
    except Exception as e:
        print(f"❌ Error getting unclaimed envelopes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'envelopes': [],
            'count': 0
        })

@red_envelope_simple_bp.route('/api/red-envelope/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard - simple version"""
    try:
        print("📥 GET /api/red-envelope/leaderboard called")
        
        supabase = get_supabase_client()
        if not supabase:
            print("❌ Supabase client not available")
            return jsonify({'success': True, 'claims': [], 'count': 0})
        
        print("🔍 Querying claimed envelopes...")
        # Query recent claims
        result = supabase.table('red_envelopes').select('*').not_.is_('claimed_by', 'null').order('claimed_at', desc=True).limit(5).execute()
        
        print(f"📊 Query result: {len(result.data) if result.data else 0} claims found")
        
        claims = []
        if result.data:
            for claim in result.data:
                user_id = claim.get('claimed_by', '')
                # Mask user ID
                if len(user_id) > 4:
                    masked = '*' * (len(user_id) - 4) + user_id[-4:]
                else:
                    masked = '***' + user_id
                
                claims.append({
                    'masked_user_id': masked,
                    'reward_amount': claim.get('reward_amount'),
                    'claimed_at': claim.get('claimed_at')
                })
        
        print(f"✅ Returning {len(claims)} claims")
        return jsonify({
            'success': True,
            'claims': claims,
            'count': len(claims)
        })
        
    except Exception as e:
        print(f"❌ Error getting leaderboard: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': True,
            'claims': [],
            'count': 0
        })

@red_envelope_simple_bp.route('/api/red-envelope/claim', methods=['POST'])
def claim_envelope():
    """Claim red envelope - add cash and send Telegram notification
    
    Rate limit: 1 request per 2 seconds per IP to prevent spam
    """
    print("📥 POST /api/red-envelope/claim called")
    
    # Simple rate limiting using IP address
    from flask import request as flask_request
    import time
    
    # Get client IP
    client_ip = flask_request.headers.get('X-Forwarded-For', flask_request.remote_addr)
    if client_ip:
        client_ip = client_ip.split(',')[0].strip()
    
    # Check rate limit (store in memory - simple but effective)
    if not hasattr(claim_envelope, 'last_request_time'):
        claim_envelope.last_request_time = {}
    
    current_time = time.time()
    last_time = claim_envelope.last_request_time.get(client_ip, 0)
    
    if current_time - last_time < 2:  # 2 seconds cooldown
        return jsonify({
            'success': False, 
            'error': 'Vui lòng đợi 2 giây trước khi thử lại / Please wait 2 seconds before trying again'
        }), 429
    
    claim_envelope.last_request_time[client_ip] = current_time
    
    # Clean old entries (older than 1 hour)
    claim_envelope.last_request_time = {
        ip: t for ip, t in claim_envelope.last_request_time.items() 
        if current_time - t < 3600
    }
    
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    envelope_id = data.get('envelope_id')
    lang = data.get('lang', 'vi')  # Get language from request
    
    if not telegram_id or not envelope_id:
        return jsonify({'success': False, 'error': 'Missing telegram_id or envelope_id'})
    
    supabase = get_supabase_client()
    if not supabase:
        return jsonify({'success': False, 'error': 'Database not available'})
    
    try:
        # STEP 1: Check if user exists FIRST (before any updates)
        user_result = supabase.table('users').select('*').eq('telegram_id', str(telegram_id)).execute()
        
        if not user_result.data:
            print(f"⚠️ User {telegram_id} not found in database")
            error_messages = {
                'vi': 'Không tìm thấy user. Vui lòng start bot trước: https://t.me/SheerID_VIP_Bot',
                'en': 'User not found. Please start the bot first: https://t.me/SheerID_VIP_Bot',
                'zh': '未找到用户。请先启动机器人：https://t.me/SheerID_VIP_Bot'
            }
            return jsonify({'success': False, 'error': error_messages.get(lang, error_messages['vi'])})
        
        user = user_result.data[0]
        current_cash = user.get('cash', 0)
        
        # STEP 2: Check if user already claimed today (1 per day limit)
        from datetime import datetime, timezone, timedelta
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        existing_claim = supabase.table('red_envelopes').select('id', count='exact').eq('claimed_by', str(telegram_id)).gte('claimed_at', today_start.isoformat()).execute()
        
        # Check count (more reliable than checking data array)
        claim_count = existing_claim.count if existing_claim.count is not None else len(existing_claim.data or [])
        
        if claim_count > 0:
            error_messages = {
                'vi': 'Bạn đã nhận bao lì xì hôm nay rồi! Quay lại vào ngày mai nhé 😊',
                'en': 'You already claimed a red envelope today! Come back tomorrow 😊',
                'zh': '您今天已经领取过红包了！明天再来吧 😊'
            }
            return jsonify({'success': False, 'error': error_messages.get(lang, error_messages['vi'])})
        
        # STEP 3: Check if envelope exists and is unclaimed
        envelope_result = supabase.table('red_envelopes').select('*').eq('id', envelope_id).is_('claimed_by', 'null').execute()
        
        if not envelope_result.data:
            error_messages = {
                'vi': 'Bao lì xì đã được nhận hoặc không tồn tại',
                'en': 'Envelope already claimed or not found',
                'zh': '红包已被领取或不存在'
            }
            return jsonify({'success': False, 'error': error_messages.get(lang, error_messages['vi'])})
        
        # STEP 4: All checks passed - now update envelope as claimed (with race condition protection)
        update_result = supabase.table('red_envelopes').update({
            'claimed_by': str(telegram_id),
            'claimed_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', envelope_id).is_('claimed_by', 'null').execute()  # Only update if still unclaimed
        
        # Check if update was successful (race condition protection)
        if not update_result.data or len(update_result.data) == 0:
            error_messages = {
                'vi': 'Bao lì xì đã được nhận bởi người khác! Thử bao lì xì khác nhé 😊',
                'en': 'Envelope was claimed by someone else! Try another one 😊',
                'zh': '红包已被其他人领取！试试其他的吧 😊'
            }
            return jsonify({'success': False, 'error': error_messages.get(lang, error_messages['vi'])})
        
        # CRITICAL: Double-check daily limit AFTER claiming (race condition protection)
        # If user somehow claimed multiple times, rollback this claim
        recheck_claim = supabase.table('red_envelopes').select('id', count='exact').eq('claimed_by', str(telegram_id)).gte('claimed_at', today_start.isoformat()).execute()
        recheck_count = recheck_claim.count if recheck_claim.count is not None else len(recheck_claim.data or [])
        
        if recheck_count > 1:
            # User has multiple claims! Rollback this one
            print(f"⚠️ User {telegram_id} has {recheck_count} claims today! Rolling back {envelope_id}")
            supabase.table('red_envelopes').update({
                'claimed_by': None,
                'claimed_at': None
            }).eq('id', envelope_id).execute()
            
            error_messages = {
                'vi': 'Bạn đã nhận bao lì xì hôm nay rồi! Quay lại vào ngày mai nhé 😊',
                'en': 'You already claimed a red envelope today! Come back tomorrow 😊',
                'zh': '您今天已经领取过红包了！明天再来吧 😊'
            }
            return jsonify({'success': False, 'error': error_messages.get(lang, error_messages['vi'])})
        
        envelope = envelope_result.data[0]
        reward_amount = envelope.get('reward_amount', 0)
        
        # STEP 5: Add cash to user
        new_cash = current_cash + reward_amount
        
        supabase.table('users').update({
            'cash': new_cash
        }).eq('telegram_id', str(telegram_id)).execute()
        
        print(f"✅ Added {reward_amount} cash to user {telegram_id} (new balance: {new_cash})")
        
    except Exception as e:
        print(f"❌ Error during claim process: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'An error occurred while claiming. Please try again later.'
        })
    
    # STEP 6: Send Telegram notification (after successful claim, outside try-catch)
    try:
        import os
        import requests as req
        
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if bot_token:
            # Multilingual messages
            messages = {
                'vi': f"🧧 *Chúc Mừng!*\n\nBạn đã nhận được *{reward_amount} cash* từ bao lì xì!\n\n💰 Số dư mới: *{new_cash} cash*\n\n⏰ Bạn có thể nhận bao lì xì tiếp theo vào ngày mai!",
                'en': f"🧧 *Congratulations!*\n\nYou received *{reward_amount} cash* from red envelope!\n\n💰 New balance: *{new_cash} cash*\n\n⏰ You can claim another red envelope tomorrow!",
                'zh': f"🧧 *恭喜！*\n\n您从红包中获得了 *{reward_amount} cash*！\n\n💰 新余额：*{new_cash} cash*\n\n⏰ 您可以在明天领取下一个红包！"
            }
            
            message = messages.get(lang, messages['vi'])
            
            req.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', json={
                'chat_id': telegram_id,
                'text': message,
                'parse_mode': 'Markdown'
            }, timeout=5)
            
            print(f"✅ Sent Telegram notification to {telegram_id} (lang: {lang})")
    except Exception as e:
        # Notification failure should NOT affect the claim success
        print(f"⚠️ Could not send Telegram notification: {e}")
    
    # Always return success if we got here (cash was added successfully)
    return jsonify({
        'success': True,
        'reward_amount': reward_amount,
        'new_balance': new_cash,
        'message': f'Đã nhận {reward_amount} cash!'
    })

@red_envelope_simple_bp.route('/api/red-envelope/health', methods=['GET'])
def health():
    """Health check"""
    print("📥 GET /api/red-envelope/health called")
    supabase = get_supabase_client()
    return jsonify({
        'success': True, 
        'status': 'ok',
        'supabase_connected': supabase is not None
    })

