"""
Giftcode System - Hệ thống quản lý giftcode tặng xu/cash
"""
from datetime import datetime
import random
import string

def generate_random_code(length=8):
    """Tạo mã giftcode ngẫu nhiên"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def create_giftcode(supabase, code, reward_type, reward_amount, max_uses, created_by_admin_id):
    """
    Tạo giftcode mới
    
    Args:
        supabase: Supabase client
        code: Mã giftcode (VD: NEWYEAR2024)
        reward_type: 'coins' hoặc 'cash'
        reward_amount: Số xu/cash tặng
        max_uses: Số lần sử dụng tối đa
        created_by_admin_id: ID admin tạo
    
    Returns:
        dict: Thông tin giftcode đã tạo hoặc None nếu lỗi
    """
    try:
        # Kiểm tra mã đã tồn tại chưa
        existing = supabase.table('giftcodes').select('*').eq('code', code.upper()).execute()
        if existing.data:
            return {'error': '❌ Mã giftcode này đã tồn tại rồi! Vui lòng chọn mã khác nhé 😊'}
        
        # Tạo giftcode mới
        giftcode_data = {
            'code': code.upper(),
            'reward_type': reward_type,
            'reward_amount': int(reward_amount),
            'max_uses': int(max_uses),
            'current_uses': 0,
            'is_active': True,
            'created_by': created_by_admin_id,
            'created_at': datetime.now().isoformat()
        }
        
        result = supabase.table('giftcodes').insert(giftcode_data).execute()
        
        if result.data:
            return result.data[0]
        return None
        
    except Exception as e:
        print(f"❌ Error creating giftcode: {e}")
        return {'error': str(e)}

def use_giftcode(supabase, code, user_id, telegram_id):
    """
    Sử dụng giftcode
    
    Args:
        supabase: Supabase client
        code: Mã giftcode
        user_id: ID user trong database
        telegram_id: Telegram ID của user
    
    Returns:
        dict: Kết quả sử dụng giftcode
    """
    try:
        # Lấy thông tin giftcode
        giftcode_resp = supabase.table('giftcodes').select('*').eq('code', code.upper()).execute()
        
        if not giftcode_resp.data:
            return {'success': False, 'message': '❌ Mã giftcode không tồn tại!\n\n💡 Vui lòng kiểm tra lại mã hoặc liên hệ:\n👤 Admin: @meepzizhere\n� Kênh: https://t.me/channel_sheerid_vip_bot'}
        
        giftcode = giftcode_resp.data[0]
        
        # Kiểm tra giftcode còn hoạt động không
        if not giftcode.get('is_active'):
            return {'success': False, 'message': '😔 Mã giftcode này đã hết hạn!\n\n💬 Liên hệ để biết thêm chi tiết:\n👤 Admin: @meepzizhere\n📢 Kênh: https://t.me/channel_sheerid_vip_bot'}
        
        # Kiểm tra đã hết lượt sử dụng chưa
        if giftcode.get('current_uses', 0) >= giftcode.get('max_uses', 0):
            return {'success': False, 'message': '😢 Rất tiếc! Mã giftcode này đã hết lượt sử dụng rồi\n\n🎁 Theo dõi kênh để nhận mã mới:\n📢 https://t.me/channel_sheerid_vip_bot'}
        
        # Kiểm tra user đã sử dụng giftcode này chưa
        used_check = supabase.table('giftcode_usage').select('*').eq('giftcode_id', giftcode['id']).eq('user_id', user_id).execute()
        
        if used_check.data:
            return {'success': False, 'message': '😊 Bạn đã sử dụng mã giftcode này rồi!\n\n💡 Mỗi người chỉ được dùng 1 lần thôi nhé.\n\n🎁 Theo dõi kênh để nhận mã mới:\n📢 https://t.me/channel_sheerid_vip_bot'}
        
        # Lấy thông tin user hiện tại
        user_resp = supabase.table('users').select('*').eq('id', user_id).execute()
        if not user_resp.data:
            return {'success': False, 'message': '❌ Không tìm thấy thông tin user'}
        
        user = user_resp.data[0]
        reward_type = giftcode.get('reward_type')
        reward_amount = giftcode.get('reward_amount', 0)
        
        # Cập nhật số dư user
        if reward_type == 'coins':
            new_coins = user.get('coins', 0) + reward_amount
            supabase.table('users').update({
                'coins': new_coins,
                'updated_at': datetime.now().isoformat()
            }).eq('id', user_id).execute()
            
            reward_text = f"{reward_amount} xu"
            new_balance = new_coins
            
        elif reward_type == 'cash':
            new_cash = user.get('cash', 0) + reward_amount
            supabase.table('users').update({
                'cash': new_cash,
                'updated_at': datetime.now().isoformat()
            }).eq('id', user_id).execute()
            
            reward_text = f"{reward_amount} cash"
            new_balance = new_cash
        else:
            return {'success': False, 'message': '❌ Loại phần thưởng không hợp lệ'}
        
        # Ghi nhận lượt sử dụng
        usage_data = {
            'giftcode_id': giftcode['id'],
            'user_id': user_id,
            'telegram_id': str(telegram_id),
            'used_at': datetime.now().isoformat()
        }
        supabase.table('giftcode_usage').insert(usage_data).execute()
        
        # Cập nhật số lần sử dụng của giftcode
        new_uses = giftcode.get('current_uses', 0) + 1
        supabase.table('giftcodes').update({
            'current_uses': new_uses,
            'updated_at': datetime.now().isoformat()
        }).eq('id', giftcode['id']).execute()
        
        # Tạo transaction record
        transaction_data = {
            'user_id': user_id,
            'type': 'giftcode',
            'amount': reward_amount,
            'description': f'Sử dụng giftcode: {code.upper()}',
            'status': 'completed',
            'created_at': datetime.now().isoformat()
        }
        supabase.table('transactions').insert(transaction_data).execute()
        
        return {
            'success': True,
            'message': f'🎉 Chúc mừng! Bạn đã nhận quà thành công!\n\n💝 Phần thưởng: {reward_text}\n💰 Số dư hiện tại: {new_balance}\n\n✨ Cảm ơn bạn đã sử dụng dịch vụ!\n\n📢 Theo dõi kênh để nhận thêm quà:\nhttps://t.me/channel_sheerid_vip_bot',
            'reward_type': reward_type,
            'reward_amount': reward_amount,
            'new_balance': new_balance
        }
        
    except Exception as e:
        print(f"❌ Error using giftcode: {e}")
        return {'success': False, 'message': f'❌ Lỗi: {str(e)}'}

def get_giftcode_info(supabase, code):
    """Lấy thông tin giftcode"""
    try:
        result = supabase.table('giftcodes').select('*').eq('code', code.upper()).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        print(f"❌ Error getting giftcode info: {e}")
        return None

def list_all_giftcodes(supabase):
    """Liệt kê tất cả giftcodes"""
    try:
        result = supabase.table('giftcodes').select('*').order('created_at', desc=True).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"❌ Error listing giftcodes: {e}")
        return []

def deactivate_giftcode(supabase, code):
    """Vô hiệu hóa giftcode"""
    try:
        result = supabase.table('giftcodes').update({
            'is_active': False,
            'updated_at': datetime.now().isoformat()
        }).eq('code', code.upper()).execute()
        
        return result.data is not None
    except Exception as e:
        print(f"❌ Error deactivating giftcode: {e}")
        return False

def get_giftcode_usage_stats(supabase, code):
    """Lấy thống kê sử dụng giftcode"""
    try:
        # Lấy thông tin giftcode
        giftcode_resp = supabase.table('giftcodes').select('*').eq('code', code.upper()).execute()
        if not giftcode_resp.data:
            return None
        
        giftcode = giftcode_resp.data[0]
        
        # Lấy danh sách người đã sử dụng
        usage_resp = supabase.table('giftcode_usage').select('*, users(telegram_id, username, first_name)').eq('giftcode_id', giftcode['id']).order('used_at', desc=True).execute()
        
        return {
            'giftcode': giftcode,
            'usage_list': usage_resp.data if usage_resp.data else []
        }
    except Exception as e:
        print(f"❌ Error getting giftcode usage stats: {e}")
        return None
