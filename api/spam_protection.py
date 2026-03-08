"""
Spam Protection and Job Management System
Prevents command spam and manages running verification jobs
"""
import time
from .supabase_client import get_supabase_client

def _get_user_language(supabase, telegram_id, telegram_lang_code=None):
    """Helper function to get user language - prioritizes Telegram language_code over database"""
    # PRIORITY 1: Use Telegram language_code if available (most accurate)
    if telegram_lang_code:
        if telegram_lang_code.startswith('en'):
            return 'en'
        elif telegram_lang_code.startswith('zh'):
            return 'zh'
        # If telegram_lang_code is 'vi' or other, continue to check database
    
    # PRIORITY 2: Check database language setting
    try:
        user_result = supabase.table('users').select('language').eq('telegram_id', str(telegram_id)).limit(1).execute()
        if user_result.data:
            db_lang = user_result.data[0].get('language', 'vi')
            # Only use database language if no telegram_lang_code was provided
            if not telegram_lang_code:
                return db_lang
            # If telegram_lang_code is 'vi', use database setting
            if telegram_lang_code.startswith('vi'):
                return db_lang
    except:
        pass
    
    # PRIORITY 3: Default to Vietnamese
    return 'vi'

def check_spam_protection(telegram_id, telegram_lang_code=None):
    """
    Check if user is allowed to send commands (spam protection)
    Returns: (allowed: bool, error_message: str or None)
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return True, None
        
        current_time = int(time.time())
        
        # Get user spam data
        result = supabase.table('user_spam_protection').select('*').eq('telegram_id', str(telegram_id)).limit(1).execute()
        
        if not result.data:
            # First time user, create record
            supabase.table('user_spam_protection').insert({
                'telegram_id': str(telegram_id),
                'command_count': 1,
                'last_command_time': current_time,
                'blocked_until': 0,
                'current_job_start': 0,
                'current_job_type': None
            }).execute()
            return True, None
        
        user_data = result.data[0]
        command_count = user_data.get('command_count', 0)
        last_command_time = user_data.get('last_command_time', 0)
        blocked_until = user_data.get('blocked_until', 0)
        current_job_start = user_data.get('current_job_start', 0)
        current_job_type = user_data.get('current_job_type')
        
        # Check if user is currently blocked
        if blocked_until > current_time:
            remaining = blocked_until - current_time
            
            # ⚠️ IMPORTANT: DO NOT update command_count or last_command_time when user is blocked
            # This prevents resetting the block timer when user checks remaining time
            
            # Friendly messages with random proverbs
            import random
            
            vi_messages = [
                f"🐢 Bạn ơi đừng vội đừng vàng, dừng chân một xíu đợi chàng verify! ⏳\n\n💤 Còn lại: {remaining} giây\n\n💡 Có câu: 'Nhanh chân lẹ tay, chậm mà chắc!'",
                f"🌸 Chậm mà chắc, nhanh hỏng việc nha bạn! 🐌\n\n⏰ Nghỉ tay thêm: {remaining} giây\n\n💭 'Từ từ mới chóng, vội vàng hỏng việc'",
                f"🍵 Uống tách trà, thư giãn một chút đi bạn êi! ☕\n\n⏳ Thời gian chờ: {remaining} giây\n\n🎋 'Ăn quả nhớ kẻ trồng cây, verify nhớ đợi tí xíu thôi'",
                f"🐰 Thỏ chạy nhanh nhưng rùa về đích trước nha! 🏁\n\n⏱️ Đợi thêm: {remaining} giây\n\n✨ 'Chậm mà chắc, nhanh hỏng việc'",
                f"🎵 Đừng vội vàng chi bạn ơi, hãy nghỉ ngơi một tí! 🌙\n\n⏰ Còn: {remaining} giây\n\n🌟 'Có công mài sắt, có ngày nên kim'"
            ]
            
            en_messages = [
                f"🐢 Easy there, friend! Rome wasn't built in a day! ⏳\n\n💤 Wait: {remaining} seconds\n\n💡 'Slow and steady wins the race!'",
                f"🌸 Patience is a virtue, dear friend! 🐌\n\n⏰ Cooldown: {remaining} seconds\n\n💭 'Good things come to those who wait'",
                f"🍵 Take a tea break, relax a bit! ☕\n\n⏳ Time left: {remaining} seconds\n\n🎋 'Haste makes waste, patience brings success'",
                f"🐰 Remember the tortoise and the hare? 🏁\n\n⏱️ Please wait: {remaining} seconds\n\n✨ 'Slow and steady wins the race'",
                f"🎵 Don't rush, take your time! 🌙\n\n⏰ Remaining: {remaining} seconds\n\n🌟 'Patience is the key to paradise'"
            ]
            
            zh_messages = [
                f"🐢 朋友别着急，慢慢来比较快哦！⏳\n\n💤 等待：{remaining} 秒\n\n💡 '欲速则不达，慢工出细活'",
                f"🌸 心急吃不了热豆腐呀！🐌\n\n⏰ 冷却时间：{remaining} 秒\n\n💭 '慢慢来，比较快'",
                f"🍵 喝杯茶，休息一下吧！☕\n\n⏳ 剩余时间：{remaining} 秒\n\n🎋 '磨刀不误砍柴工'",
                f"🐰 记得龟兔赛跑的故事吗？🏁\n\n⏱️ 请等待：{remaining} 秒\n\n✨ '慢工出细活，心急吃不了热豆腐'",
                f"🎵 别急别急，慢慢来！🌙\n\n⏰ 还需：{remaining} 秒\n\n🌟 '耐心是成功的钥匙'"
            ]
            
            # Get user language with fallback
            lang = _get_user_language(supabase, telegram_id, telegram_lang_code)
            
            if lang == 'en':
                return False, random.choice(en_messages)
            elif lang == 'zh':
                return False, random.choice(zh_messages)
            else:
                return False, random.choice(vi_messages)
        
        # Check if user has a running job (5 minute cooldown)
        if current_job_start and current_job_start > 0:
            job_elapsed = current_time - current_job_start
            if job_elapsed < 300:  # 5 minutes = 300 seconds
                remaining = 300 - job_elapsed
                minutes = remaining // 60
                seconds = remaining % 60
                return False, f"⏳ Job đang chạy ({current_job_type}). Còn lại: {minutes}:{seconds:02d}\n\n💡 Dùng /cancel để hủy job"
        
        # Reset command count if more than 1 minute has passed
        if current_time - last_command_time > 60:
            command_count = 0
        
        # Increment command count
        command_count += 1
        
        # Check if user is at 3 commands (warning before block)
        if command_count == 3:
            # Update command count but don't block yet - just warn
            supabase.table('user_spam_protection').update({
                'command_count': command_count,
                'last_command_time': current_time
            }).eq('telegram_id', str(telegram_id)).execute()
            
            # Friendly warning messages
            import random
            
            vi_warnings = [
                "⚠️ Nài nài từ từ thôiiiiiiiiiiiiiiii! 🐌\n\n💭 Bạn đã gõ 3 lệnh rồi đó!\n\n🚨 Còn 2 lệnh nữa thôi, lệnh thứ 6 sẽ bị chặn 30 giây nha!\n\n💡 'Chậm mà chắc, nhanh hỏng việc' 🌸",
                "⚠️ Ối dồi ôi! Từ từ thôi bạn êiiiii! 🐢\n\n💭 3 lệnh rồi, đừng vội nữa!\n\n🚨 Còn được 2 lệnh, spam quá 5 = nghỉ 30 giây đó!\n\n💡 'Có công mài sắt, có ngày nên kim' ✨",
                "⚠️ Hây hây! Chậm lại một chút nào! 🍵\n\n💭 Đã 3 lệnh trong 1 phút rồi!\n\n🚨 Tối đa 5 lệnh, lệnh thứ 6 sẽ bị khóa 30 giây!\n\n💡 'Từ từ mới chóng, vội vàng hỏng việc' 🌙"
            ]
            
            en_warnings = [
                "⚠️ Whoa whoa, easy there friend! 🐌\n\n💭 You've sent 3 commands already!\n\n🚨 Only 2 more left, 6th command will be blocked for 30 seconds!\n\n💡 'Slow and steady wins the race' 🌸",
                "⚠️ Hold your horses! Take it easy! 🐢\n\n💭 That's 3 commands, don't rush!\n\n🚨 2 more allowed, spam over 5 = 30 second timeout!\n\n💡 'Patience is a virtue' ✨",
                "⚠️ Hey hey! Slow down a bit! 🍵\n\n💭 3 commands in 1 minute already!\n\n🚨 Max 5 commands, 6th will be blocked for 30 seconds!\n\n💡 'Good things come to those who wait' 🌙"
            ]
            
            zh_warnings = [
                "⚠️ 哎哎哎，慢点慢点啦！🐌\n\n💭 已经3条命令了哦！\n\n🚨 还剩2条，第6条就要被封30秒啦！\n\n💡 '慢工出细活，心急吃不了热豆腐' 🌸",
                "⚠️ 别急别急！慢慢来！🐢\n\n💭 3条命令了，别着急！\n\n🚨 还能发2条，超过5条 = 封禁30秒！\n\n💡 '欲速则不达' ✨",
                "⚠️ 嘿嘿！慢一点啦！🍵\n\n💭 1分钟内已经3条命令了！\n\n🚨 最多5条，第6条将被封锁30秒！\n\n💡 '磨刀不误砍柴工' 🌙"
            ]
            
            # Get user language with fallback
            lang = _get_user_language(supabase, telegram_id, telegram_lang_code)
            
            if lang == 'en':
                return False, random.choice(en_warnings)
            elif lang == 'zh':
                return False, random.choice(zh_warnings)
            else:
                return False, random.choice(vi_warnings)
        
        # Check if user exceeded 5 commands in 1 minute (6th command = block)
        if command_count > 5:
            # Block user for 30 seconds
            blocked_until = current_time + 30
            supabase.table('user_spam_protection').update({
                'command_count': command_count,
                'last_command_time': current_time,
                'blocked_until': blocked_until
            }).eq('telegram_id', str(telegram_id)).execute()
            
            # Friendly first block message
            import random
            
            vi_first_block = [
                "🐢 Bạn ơi đừng vội đừng vàng, dừng chân một xíu đợi chàng verify! ⏳\n\n💤 Nghỉ ngơi: 30 giây\n\n💡 'Chậm mà chắc, nhanh hỏng việc!'",
                "🌸 Ối dồi ôi! Bạn gõ nhanh quá rồi! 🐌\n\n⏰ Thư giãn: 30 giây\n\n💭 'Từ từ mới chóng, vội vàng hỏng việc'",
                "🍵 Hãy uống tách trà và thư giãn nhé! ☕\n\n⏳ Chờ tí: 30 giây\n\n🎋 'Có công mài sắt, có ngày nên kim'"
            ]
            
            en_first_block = [
                "🐢 Whoa there, speedy! Let's take a breather! ⏳\n\n💤 Cooldown: 30 seconds\n\n💡 'Slow and steady wins the race!'",
                "🌸 Easy does it, friend! Too fast! 🐌\n\n⏰ Relax: 30 seconds\n\n💭 'Good things come to those who wait'",
                "🍵 Time for a tea break! ☕\n\n⏳ Wait: 30 seconds\n\n🎋 'Patience is a virtue'"
            ]
            
            zh_first_block = [
                "🐢 朋友慢点，别着急哦！⏳\n\n💤 休息：30 秒\n\n💡 '慢工出细活'",
                "🌸 哎呀！太快啦！🐌\n\n⏰ 放松：30 秒\n\n💭 '心急吃不了热豆腐'",
                "🍵 喝杯茶休息一下！☕\n\n⏳ 等待：30 秒\n\n🎋 '磨刀不误砍柴工'"
            ]
            
            # Get user language with fallback
            lang = _get_user_language(supabase, telegram_id, telegram_lang_code)
            
            if lang == 'en':
                return False, random.choice(en_first_block)
            elif lang == 'zh':
                return False, random.choice(zh_first_block)
            else:
                return False, random.choice(vi_first_block)
        
        # Update command count and time
        supabase.table('user_spam_protection').update({
            'command_count': command_count,
            'last_command_time': current_time
        }).eq('telegram_id', str(telegram_id)).execute()
        
        return True, None
        
    except Exception as e:
        print(f"❌ Spam protection error: {e}")
        return True, None  # Allow on error

def start_user_job(telegram_id, job_type):
    """Mark that user has started a job"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return
        
        current_time = int(time.time())
        
        # Check if record exists
        result = supabase.table('user_spam_protection').select('telegram_id').eq('telegram_id', str(telegram_id)).limit(1).execute()
        
        if result.data:
            # Update existing record
            supabase.table('user_spam_protection').update({
                'current_job_start': current_time,
                'current_job_type': job_type,
                'command_count': 0,
                'last_command_time': current_time
            }).eq('telegram_id', str(telegram_id)).execute()
        else:
            # Insert new record
            supabase.table('user_spam_protection').insert({
                'telegram_id': str(telegram_id),
                'command_count': 0,
                'last_command_time': current_time,
                'blocked_until': 0,
                'current_job_start': current_time,
                'current_job_type': job_type
            }).execute()
        
        print(f"✅ Started job {job_type} for user {telegram_id}")
    except Exception as e:
        print(f"❌ Failed to start job: {e}")

def end_user_job(telegram_id):
    """Mark that user's job has ended"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return
        
        supabase.table('user_spam_protection').update({
            'current_job_start': 0,
            'current_job_type': None
        }).eq('telegram_id', str(telegram_id)).execute()
        
        print(f"✅ Ended job for user {telegram_id}")
    except Exception as e:
        print(f"❌ Failed to end job: {e}")

def cancel_user_job(telegram_id):
    """
    Cancel user's current job
    Returns: job_type if cancelled, None if no job running
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        result = supabase.table('user_spam_protection').select('current_job_type').eq('telegram_id', str(telegram_id)).limit(1).execute()
        
        if result.data and result.data[0].get('current_job_type'):
            job_type = result.data[0]['current_job_type']
            
            supabase.table('user_spam_protection').update({
                'current_job_start': 0,
                'current_job_type': None
            }).eq('telegram_id', str(telegram_id)).execute()
            
            print(f"✅ Cancelled job {job_type} for user {telegram_id}")
            return job_type
        else:
            return None
    except Exception as e:
        print(f"❌ Failed to cancel job: {e}")
        return None

def get_user_job_status(telegram_id):
    """
    Get user's current job status
    Returns: dict with job info or None
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        result = supabase.table('user_spam_protection').select('*').eq('telegram_id', str(telegram_id)).limit(1).execute()
        
        if result.data:
            user_data = result.data[0]
            current_job_start = user_data.get('current_job_start', 0)
            current_job_type = user_data.get('current_job_type')
            
            if current_job_start and current_job_start > 0 and current_job_type:
                current_time = int(time.time())
                elapsed = current_time - current_job_start
                remaining = max(0, 300 - elapsed)  # 5 minutes = 300 seconds
                
                return {
                    'job_type': current_job_type,
                    'start_time': current_job_start,
                    'elapsed': elapsed,
                    'remaining': remaining,
                    'is_running': remaining > 0
                }
        
        return None
    except Exception as e:
        print(f"❌ Failed to get job status: {e}")
        return None

def init_spam_protection_table():
    """Initialize spam protection table in Supabase"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            print("⚠️ Supabase client not available")
            return False
        
        # Check if table exists by trying to query it
        try:
            supabase.table('user_spam_protection').select('telegram_id').limit(1).execute()
            print("✅ user_spam_protection table already exists")
            return True
        except Exception:
            print("⚠️ user_spam_protection table does not exist")
            print("📝 Please create the table manually in Supabase with this SQL:")
            print("""
CREATE TABLE IF NOT EXISTS user_spam_protection (
    id BIGSERIAL PRIMARY KEY,
    telegram_id TEXT UNIQUE NOT NULL,
    command_count INTEGER DEFAULT 0,
    last_command_time BIGINT DEFAULT 0,
    blocked_until BIGINT DEFAULT 0,
    current_job_start BIGINT DEFAULT 0,
    current_job_type TEXT DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_spam_telegram_id ON user_spam_protection(telegram_id);
            """)
            return False
            
    except Exception as e:
        print(f"❌ Failed to initialize spam protection table: {e}")
        return False
