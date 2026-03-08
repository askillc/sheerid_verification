"""
VIP Tiers System - Multi-link parallel verification support

VIP Tiers:
- Basic: 1 link at a time (unlimited verify) - 1200 cash (48 USDT) / 7 days
- Pro: 3 links at a time (unlimited verify) - 1800 cash (72 USDT) / 7 days
- Business: 5 links at a time (unlimited verify) - 2400 cash (96 USDT) / 7 days
"""

import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

# VIP Tier Configuration
VIP_TIERS = {
    'basic': {
        'name': 'VIP Basic',
        'concurrent_links': 1,
        'price_7_days': 1200,     # 48 USDT
        'price_30_days': 4000,    # 160 USDT (save 33%)
        'description': {
            'vi': '1 link/lần - Verify không giới hạn',
            'en': '1 link at a time - Unlimited verify',
            'zh': '每次1个链接 - 无限验证'
        }
    },
    'pro': {
        'name': 'VIP Pro',
        'concurrent_links': 3,
        'price_7_days': 1800,     # 72 USDT
        'price_30_days': 6000,    # 240 USDT (save 33%)
        'description': {
            'vi': '3 link song song - Verify không giới hạn',
            'en': '3 links parallel - Unlimited verify',
            'zh': '3个链接并行 - 无限验证'
        }
    },
    'business': {
        'name': 'VIP Business',
        'concurrent_links': 5,
        'price_7_days': 2400,     # 96 USDT
        'price_30_days': 8000,    # 320 USDT (save 33%)
        'description': {
            'vi': '5 link song song - Verify không giới hạn',
            'en': '5 links parallel - Unlimited verify',
            'zh': '5个链接并行 - 无限验证'
        }
    }
}

# Track active verifications per user
USER_ACTIVE_VERIFICATIONS: Dict[str, set] = {}  # telegram_id -> set of job_ids
USER_VERIFICATION_LOCK = threading.Lock()


def get_user_concurrent_limit(user: dict) -> int:
    """Get user's concurrent verification limit based on VIP tier"""
    if not user:
        return 0
    
    # Check if VIP is active
    is_vip = user.get('is_vip', False)
    vip_expiry = user.get('vip_expiry')
    
    if not is_vip:
        return 0  # Non-VIP users pay per verification
    
    # Check expiry
    if vip_expiry:
        try:
            expiry_dt = datetime.fromisoformat(vip_expiry.replace('Z', '+00:00'))
            if expiry_dt < datetime.now(expiry_dt.tzinfo):
                return 0  # VIP expired
        except:
            pass
    
    # Get tier
    vip_type = user.get('vip_type', 'basic')
    concurrent_links = user.get('concurrent_links')
    
    # If concurrent_links is set, use it directly
    if concurrent_links and concurrent_links > 0:
        return concurrent_links
    
    # Otherwise use tier default
    tier_config = VIP_TIERS.get(vip_type, VIP_TIERS['basic'])
    return tier_config['concurrent_links']


def get_user_active_count(telegram_id: str) -> int:
    """Get number of active verifications for a user"""
    with USER_VERIFICATION_LOCK:
        active_jobs = USER_ACTIVE_VERIFICATIONS.get(str(telegram_id), set())
        return len(active_jobs)


def can_start_verification(telegram_id: str, user: dict) -> Tuple[bool, str, int]:
    """
    Check if user can start a new verification
    Returns: (can_start, reason_message, slots_available)
    """
    telegram_id = str(telegram_id)
    
    # Get concurrent limit
    limit = get_user_concurrent_limit(user)
    
    if limit == 0:
        # Non-VIP or expired - they pay per verification, no limit
        return True, "", 999
    
    # VIP user - check concurrent limit
    active_count = get_user_active_count(telegram_id)
    slots_available = limit - active_count
    
    if slots_available <= 0:
        vip_type = user.get('vip_type', 'basic')
        tier_name = VIP_TIERS.get(vip_type, {}).get('name', 'VIP')
        return False, f"⚠️ Bạn đang chạy {active_count}/{limit} link.\n\n💡 {tier_name} cho phép tối đa {limit} link song song.\n⏳ Vui lòng chờ job hiện tại hoàn thành.", 0
    
    return True, "", slots_available


def add_active_verification(telegram_id: str, job_id: str) -> bool:
    """Add a job to user's active verifications"""
    telegram_id = str(telegram_id)
    with USER_VERIFICATION_LOCK:
        if telegram_id not in USER_ACTIVE_VERIFICATIONS:
            USER_ACTIVE_VERIFICATIONS[telegram_id] = set()
        USER_ACTIVE_VERIFICATIONS[telegram_id].add(job_id)
        print(f"🔗 Added job {job_id} to user {telegram_id}. Active: {len(USER_ACTIVE_VERIFICATIONS[telegram_id])}")
        return True


def remove_active_verification(telegram_id: str, job_id: str) -> bool:
    """Remove a job from user's active verifications"""
    telegram_id = str(telegram_id)
    with USER_VERIFICATION_LOCK:
        if telegram_id in USER_ACTIVE_VERIFICATIONS:
            USER_ACTIVE_VERIFICATIONS[telegram_id].discard(job_id)
            print(f"✅ Removed job {job_id} from user {telegram_id}. Active: {len(USER_ACTIVE_VERIFICATIONS[telegram_id])}")
            return True
        return False


def get_user_verification_status(telegram_id: str, user: dict) -> dict:
    """Get user's verification status for display"""
    telegram_id = str(telegram_id)
    limit = get_user_concurrent_limit(user)
    active_count = get_user_active_count(telegram_id)
    
    with USER_VERIFICATION_LOCK:
        active_jobs = list(USER_ACTIVE_VERIFICATIONS.get(telegram_id, set()))
    
    vip_type = user.get('vip_type', 'basic') if user else 'none'
    
    return {
        'vip_type': vip_type,
        'concurrent_limit': limit,
        'active_count': active_count,
        'slots_available': max(0, limit - active_count),
        'active_jobs': active_jobs
    }


def upgrade_vip_tier(user_id: int, new_tier: str, days: int = 7) -> Tuple[bool, str]:
    """
    Upgrade user's VIP tier
    Returns: (success, message)
    """
    if new_tier not in VIP_TIERS:
        return False, f"❌ Gói VIP không hợp lệ: {new_tier}"
    
    tier_config = VIP_TIERS[new_tier]
    concurrent_links = tier_config['concurrent_links']
    
    try:
        from .supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            return False, "❌ Không thể kết nối database"
        
        # Get current user data
        user_data = supabase.table('users').select('is_vip, vip_expiry, vip_type').eq('id', user_id).execute()
        
        if not user_data.data:
            return False, "❌ Không tìm thấy user"
        
        current_data = user_data.data[0]
        current_expiry = current_data.get('vip_expiry')
        
        # Calculate new expiry
        import pytz
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        current_time = datetime.now(vn_tz)
        
        if current_expiry:
            try:
                expiry_dt = datetime.fromisoformat(current_expiry.replace('Z', '+00:00'))
                expiry_dt = expiry_dt.replace(tzinfo=pytz.UTC).astimezone(vn_tz)
                # If current VIP still valid, add days to it
                if expiry_dt > current_time:
                    new_expiry = expiry_dt + timedelta(days=days)
                else:
                    new_expiry = current_time + timedelta(days=days)
            except:
                new_expiry = current_time + timedelta(days=days)
        else:
            new_expiry = current_time + timedelta(days=days)
        
        # Update user
        supabase.table('users').update({
            'is_vip': True,
            'vip_expiry': new_expiry.isoformat(),
            'vip_type': new_tier,
            'concurrent_links': concurrent_links,
            'updated_at': datetime.now().isoformat()
        }).eq('id', user_id).execute()
        
        formatted_expiry = new_expiry.strftime('%d/%m/%Y %H:%M')
        tier_name = tier_config['name']
        
        return True, f"✅ Đã nâng cấp lên {tier_name}!\n\n🔗 Số link song song: {concurrent_links}\n⏰ Hạn sử dụng: {formatted_expiry}"
        
    except Exception as e:
        return False, f"❌ Lỗi: {str(e)}"


def get_vip_shop_text(user_lang: str = 'vi') -> str:
    """Generate VIP shop text for display"""
    
    if user_lang == 'en':
        text = """👑 VIP PACKAGES

🔹 VIP Basic (1 link)
   💵 7 days: 1200 cash (48 USDT)
   📝 Command: /mua vip7

🔹 VIP Pro (3 links parallel)
   💵 7 days: 1800 cash (72 USDT)
   📝 Command: /mua vippro7

🔹 VIP Business (5 links parallel)
   💵 7 days: 2400 cash (96 USDT)
   📝 Command: /mua vipbiz7

💡 VIP Benefits:
• Free student verification (unlimited)
• Parallel link processing
• Priority support"""
    
    elif user_lang == 'zh':
        text = """👑 VIP套餐

🔹 VIP Basic (1个链接)
   💵 7天: 1200 cash (48 USDT)
   📝 命令: /mua vip7

🔹 VIP Pro (3个链接并行)
   💵 7天: 1800 cash (72 USDT)
   📝 命令: /mua vippro7

🔹 VIP Business (5个链接并行)
   💵 7天: 2400 cash (96 USDT)
   📝 命令: /mua vipbiz7

💡 VIP权益:
• 免费学生验证（无限）
• 并行链接处理
• 优先支持"""
    
    else:  # Vietnamese default
        text = """👑 GÓI VIP

🔹 VIP Basic (1 link)
   💵 7 ngày: 1200 cash (48 USDT)
   📝 Lệnh: /mua vip7

🔹 VIP Pro (3 link song song)
   💵 7 ngày: 1800 cash (72 USDT)
   📝 Lệnh: /mua vippro7

🔹 VIP Business (5 link song song)
   💵 7 ngày: 2400 cash (96 USDT)
   📝 Lệnh: /mua vipbiz7

💡 Quyền lợi VIP:
• Verify student miễn phí (không giới hạn)
• Chạy nhiều link song song
• Hỗ trợ ưu tiên"""
    
    return text
