"""
Red Envelope Minigame API
Handles spawning and claiming red envelopes on status monitor page

Features:
- 30 spawns per day at random times
- Envelopes stay until claimed (no expiry)
- Each user can only claim 1 envelope per day
- Race condition handling - first claimer wins
- Multi-language support (Vietnamese, English, Chinese)
"""

from flask import Blueprint, request, jsonify
import os
import uuid
from datetime import datetime, timedelta
import random
import requests

red_envelope_bp = Blueprint('red_envelope', __name__)

# Supabase credentials
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

# Bot token for sending Telegram notifications
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Multi-language messages
MESSAGES = {
    'vi': {
        'success': '🧧 Chúc mừng! Bạn đã nhận được {amount} cash từ bao lì xì!\n\n💰 Số dư hiện tại: {balance} cash',
        'already_claimed_today': '❌ Bạn đã nhận bao lì xì hôm nay rồi!\n\n🎁 Quay lại vào ngày mai nhé!',
        'too_slow': '😅 Chậm tay rồi bạn ơi!\n\n🧧 Bao lì xì này đã được người khác nhận mất rồi.\n💪 Chúc bạn may mắn lần sau!',
        'not_found': '❌ Không tìm thấy bao lì xì này',
        'user_not_found': '❌ Không tìm thấy tài khoản.\n\n📱 Vui lòng /start bot trước!',
        'invalid_id': '❌ Telegram ID không hợp lệ'
    },
    'en': {
        'success': '🧧 Congratulations! You received {amount} cash from the red envelope!\n\n💰 Current balance: {balance} cash',
        'already_claimed_today': '❌ You already claimed a red envelope today!\n\n🎁 Come back tomorrow!',
        'too_slow': '😅 Too slow!\n\n🧧 Someone else already claimed this red envelope.\n💪 Better luck next time!',
        'not_found': '❌ Red envelope not found',
        'user_not_found': '❌ User not found.\n\n📱 Please /start the bot first!',
        'invalid_id': '❌ Invalid Telegram ID'
    },
    'zh': {
        'success': '🧧 恭喜！您从红包中获得了 {amount} 现金！\n\n💰 当前余额：{balance} 现金',
        'already_claimed_today': '❌ 您今天已经领取过红包了！\n\n🎁 明天再来吧！',
        'too_slow': '😅 手慢了！\n\n🧧 这个红包已经被别人领走了。\n💪 下次加油！',
        'not_found': '❌ 找不到红包',
        'user_not_found': '❌ 找不到用户。\n\n📱 请先 /start 机器人！',
        'invalid_id': '❌ 无效的 Telegram ID'
    }
}

def get_message(lang, key, **kwargs):
    """Get localized message"""
    lang = lang if lang in MESSAGES else 'en'
    message = MESSAGES[lang].get(key, MESSAGES['en'][key])
    return message.format(**kwargs) if kwargs else message

def supabase_request(method, endpoint, data=None, params=None):
    """Make request to Supabase REST API"""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    
    if method == 'GET':
        response = requests.get(url, headers=headers, params=params)
    elif method == 'POST':
        response = requests.post(url, headers=headers, json=data)
    elif method == 'PATCH':
        response = requests.patch(url, headers=headers, json=data, params=params)
    elif method == 'DELETE':
        response = requests.delete(url, headers=headers, params=params)
    
    return response

@red_envelope_bp.route('/api/red-envelope/spawn', methods=['POST'])
def spawn_red_envelope():
    """
    Spawn a new red envelope
    No expiry - stays until claimed
    """
    try:
        envelope_id = str(uuid.uuid4())
        cash_amount = random.randint(1, 5)
        
        response = supabase_request('POST', 'red_envelopes', data={
            'envelope_id': envelope_id,
            'cash_amount': cash_amount,
            'is_claimed': False
        })
        
        if response.status_code not in [200, 201]:
            return jsonify({'success': False, 'error': f'Database error'}), 500
        
        return jsonify({
            'success': True,
            'envelope': {
                'id': envelope_id,
                'amount': cash_amount
            }
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to spawn red envelope: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@red_envelope_bp.route('/api/red-envelope/claim', methods=['POST'])
def claim_red_envelope():
    """
    Claim a red envelope with race condition handling
    - Check if user already claimed today
    - Atomic claim operation (first wins)
    - Multi-language support
    """
    try:
        data = request.json
        envelope_id = data.get('envelope_id')
        telegram_id = data.get('telegram_id')
        lang = data.get('lang', 'vi')  # Default to Vietnamese
        
        if not envelope_id or not telegram_id:
            return jsonify({
                'success': False,
                'error': get_message(lang, 'invalid_id')
            }), 400
        
        # Validate telegram_id
        try:
            telegram_id = int(telegram_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': get_message(lang, 'invalid_id')
            }), 400
        
        # Check if user exists
        user_response = supabase_request('GET', 'users', params={'telegram_id': f'eq.{telegram_id}'})
        if user_response.status_code != 200:
            return jsonify({'success': False, 'error': 'Database error'}), 500
        
        users = user_response.json()
        if not users:
            return jsonify({
                'success': False,
                'error': get_message(lang, 'user_not_found')
            }), 404
        
        user = users[0]
        
        # Check if user already claimed today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        claimed_today_response = supabase_request('GET', 'red_envelopes', params={
            'claimed_by_telegram_id': f'eq.{telegram_id}',
            'claimed_at': f'gte.{today_start}',
            'is_claimed': 'eq.true'
        })
        
        if claimed_today_response.status_code == 200:
            claimed_today = claimed_today_response.json()
            if claimed_today and len(claimed_today) > 0:
                return jsonify({
                    'success': False,
                    'error': get_message(lang, 'already_claimed_today'),
                    'already_claimed': True
                }), 400
        
        # Get envelope
        envelope_response = supabase_request('GET', 'red_envelopes', params={'envelope_id': f'eq.{envelope_id}'})
        if envelope_response.status_code != 200:
            return jsonify({'success': False, 'error': 'Database error'}), 500
        
        envelopes = envelope_response.json()
        if not envelopes:
            return jsonify({
                'success': False,
                'error': get_message(lang, 'not_found')
            }), 404
        
        envelope = envelopes[0]
        
        # Check if already claimed (race condition check)
        if envelope['is_claimed']:
            return jsonify({
                'success': False,
                'error': get_message(lang, 'too_slow'),
                'too_slow': True
            }), 400
        
        cash_amount = envelope['cash_amount']
        
        # ATOMIC OPERATION: Try to claim (race condition handled by database)
        # Update with condition that is_claimed must still be false
        claim_response = supabase_request('PATCH', 'red_envelopes',
            data={
                'is_claimed': True,
                'claimed_at': datetime.now().isoformat(),
                'claimed_by_telegram_id': telegram_id
            },
            params={
                'envelope_id': f'eq.{envelope_id}',
                'is_claimed': 'eq.false'  # Only update if still unclaimed
            }
        )
        
        # Check if update was successful (returns empty if already claimed)
        if claim_response.status_code == 200:
            updated = claim_response.json()
            if not updated or len(updated) == 0:
                # Someone else claimed it first
                return jsonify({
                    'success': False,
                    'error': get_message(lang, 'too_slow'),
                    'too_slow': True
                }), 400
        else:
            return jsonify({'success': False, 'error': 'Database error'}), 500
        
        # Successfully claimed! Add cash to user
        new_cash = user['cash'] + cash_amount
        supabase_request('PATCH', 'users',
            data={'cash': new_cash},
            params={'telegram_id': f'eq.{telegram_id}'}
        )
        
        # Send Telegram notification (all 3 languages)
        try:
            message = get_message(lang, 'success', amount=cash_amount, balance=new_cash)
            
            requests.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
                json={
                    'chat_id': telegram_id,
                    'text': message
                },
                timeout=5
            )
        except Exception as e:
            print(f"[WARNING] Failed to send Telegram notification: {e}")
        
        return jsonify({
            'success': True,
            'amount': cash_amount,
            'new_balance': new_cash,
            'message': get_message(lang, 'success', amount=cash_amount, balance=new_cash)
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to claim red envelope: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@red_envelope_bp.route('/api/red-envelope/stats', methods=['GET'])
def get_red_envelope_stats():
    """Get red envelope statistics"""
    try:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        # Get all envelopes from today
        response = supabase_request('GET', 'red_envelopes',
            params={'spawned_at': f'gte.{today_start}'}
        )
        
        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'Database error'}), 500
        
        all_envelopes = response.json()
        total_spawned = len(all_envelopes)
        
        claimed_envelopes = [e for e in all_envelopes if e['is_claimed']]
        total_claimed = len(claimed_envelopes)
        total_cash = sum(e['cash_amount'] for e in claimed_envelopes)
        
        # Unclaimed envelopes still available
        unclaimed = total_spawned - total_claimed
        
        return jsonify({
            'success': True,
            'stats': {
                'total_spawned_today': total_spawned,
                'total_claimed_today': total_claimed,
                'unclaimed_available': unclaimed,
                'total_cash_distributed_today': total_cash,
                'claim_rate': round((total_claimed / total_spawned * 100) if total_spawned > 0 else 0, 2)
            }
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to get red envelope stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@red_envelope_bp.route('/api/red-envelope/check-user-claimed', methods=['GET'])
def check_user_claimed_today():
    """Check if user already claimed today"""
    try:
        telegram_id = request.args.get('telegram_id')
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Missing telegram_id'}), 400
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        response = supabase_request('GET', 'red_envelopes', params={
            'claimed_by_telegram_id': f'eq.{telegram_id}',
            'claimed_at': f'gte.{today_start}',
            'is_claimed': 'eq.true'
        })
        
        if response.status_code == 200:
            claimed = response.json()
            return jsonify({
                'success': True,
                'already_claimed': len(claimed) > 0
            })
        
        return jsonify({'success': False, 'error': 'Database error'}), 500
        
    except Exception as e:
        print(f"[ERROR] Failed to check user claimed status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
