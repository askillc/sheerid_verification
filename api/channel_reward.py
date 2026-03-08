"""
Channel Membership Reward System
Rewards users with 10 cash for joining the official channel (one-time only)
Requires 24 hours waiting period after joining to prevent spam
"""

import os
import requests
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta

# Channel configuration
REWARD_CHANNEL_ID = os.getenv('REWARD_CHANNEL_ID', '@channel_sheerid_vip_bot')
REWARD_AMOUNT = 10  # 10 cash reward
WAITING_PERIOD_HOURS = 24  # Must wait 24 hours after joining

def check_channel_membership(telegram_id: int, bot_token: str) -> bool:
    """
    Check if a user is a member of the reward channel
    
    Args:
        telegram_id: User's Telegram ID
        bot_token: Bot token for API calls
        
    Returns:
        True if user is a member, False otherwise
    """
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getChatMember"
        params = {
            'chat_id': REWARD_CHANNEL_ID,
            'user_id': telegram_id
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if not data.get('ok'):
            print(f"❌ Channel membership check failed: {data.get('description')}")
            return False
        
        # Check if user is a member (status can be: creator, administrator, member)
        status = data.get('result', {}).get('status', '')
        is_member = status in ['creator', 'administrator', 'member']
        
        print(f"✅ Channel membership check: user {telegram_id} status = {status}, is_member = {is_member}")
        return is_member
        
    except Exception as e:
        print(f"❌ Error checking channel membership: {e}")
        return False


def has_claimed_channel_reward(user: Dict) -> bool:
    """
    Check if user has already claimed the channel reward
    
    Args:
        user: User dictionary from database
        
    Returns:
        True if already claimed, False otherwise
    """
    if isinstance(user, dict):
        return user.get('channel_reward_claimed', False)
    return False


def record_channel_join(user_id: int, telegram_id: int, bot_token: str) -> Tuple[bool, str]:
    """
    Record when user joins the channel (first step)
    
    Args:
        user_id: Database user ID
        telegram_id: Telegram user ID
        bot_token: Bot token for API calls
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Import here to avoid circular imports
        from supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        if not supabase:
            return False, "database_error"
        
        # Get current user data
        result = supabase.table('users').select('*').eq('id', user_id).execute()
        if not result.data:
            return False, "user_not_found"
        
        user = result.data[0]
        
        # Check if already claimed
        if user.get('channel_reward_claimed', False):
            return False, "already_claimed"
        
        # Check channel membership
        if not check_channel_membership(telegram_id, bot_token):
            return False, "not_member"
        
        # Check if already recorded join time
        if user.get('channel_joined_at'):
            # Already recorded, check if 24 hours passed
            joined_at = datetime.fromisoformat(user['channel_joined_at'].replace('Z', '+00:00'))
            now = datetime.now(joined_at.tzinfo)
            hours_passed = (now - joined_at).total_seconds() / 3600
            
            if hours_passed >= WAITING_PERIOD_HOURS:
                return True, "can_claim"
            else:
                hours_remaining = WAITING_PERIOD_HOURS - hours_passed
                return False, f"waiting|{hours_remaining:.1f}"
        
        # Record join time
        now = datetime.utcnow().isoformat() + 'Z'
        update_result = supabase.table('users').update({
            'channel_joined_at': now
        }).eq('id', user_id).execute()
        
        if update_result.data:
            print(f"✅ Recorded channel join: user {telegram_id} at {now}")
            return True, "join_recorded"
        else:
            return False, "database_error"
            
    except Exception as e:
        print(f"❌ Error recording channel join: {e}")
        import traceback
        traceback.print_exc()
        return False, "error"


def claim_channel_reward(user_id: int, telegram_id: int, bot_token: str) -> Tuple[bool, str, int]:
    """
    Process channel reward claim (after 24 hours waiting period)
    
    Args:
        user_id: Database user ID
        telegram_id: Telegram user ID
        bot_token: Bot token for API calls
        
    Returns:
        Tuple of (success, message, new_cash_balance)
    """
    try:
        # Import here to avoid circular imports
        from supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        if not supabase:
            return False, "❌ Database connection error", 0
        
        # Get current user data
        result = supabase.table('users').select('*').eq('id', user_id).execute()
        if not result.data:
            return False, "❌ User not found", 0
        
        user = result.data[0]
        
        # Check if already claimed
        if user.get('channel_reward_claimed', False):
            return False, "already_claimed", user.get('cash', 0)
        
        # Check channel membership
        if not check_channel_membership(telegram_id, bot_token):
            return False, "not_member", user.get('cash', 0)
        
        # Check if join time is recorded
        if not user.get('channel_joined_at'):
            return False, "not_recorded", user.get('cash', 0)
        
        # Check if 24 hours have passed
        joined_at = datetime.fromisoformat(user['channel_joined_at'].replace('Z', '+00:00'))
        now = datetime.now(joined_at.tzinfo)
        hours_passed = (now - joined_at).total_seconds() / 3600
        
        if hours_passed < WAITING_PERIOD_HOURS:
            hours_remaining = WAITING_PERIOD_HOURS - hours_passed
            return False, f"waiting|{hours_remaining:.1f}", user.get('cash', 0)
        
        # Award the reward
        current_cash = user.get('cash', 0)
        new_cash = current_cash + REWARD_AMOUNT
        
        # Update database
        update_result = supabase.table('users').update({
            'cash': new_cash,
            'channel_reward_claimed': True
        }).eq('id', user_id).execute()
        
        if update_result.data:
            print(f"✅ Channel reward claimed: user {telegram_id} received {REWARD_AMOUNT} cash")
            return True, "success", new_cash
        else:
            return False, "❌ Database update failed", current_cash
            
    except Exception as e:
        print(f"❌ Error claiming channel reward: {e}")
        import traceback
        traceback.print_exc()
        return False, f"❌ Error: {str(e)}", 0


def get_channel_reward_info(language: str = 'vi') -> Dict[str, str]:
    """
    Get multilingual messages for channel reward system
    
    Args:
        language: User's language preference ('vi', 'en', 'zh')
        
    Returns:
        Dictionary with message templates
    """
    messages = {
        'vi': {
            'info': f"🎁 Tham gia kênh chính thức và nhận {REWARD_AMOUNT} cash miễn phí!\n\n"
                   f"📢 Kênh: {REWARD_CHANNEL_ID}\n"
                   f"💰 Phần thưởng: {REWARD_AMOUNT} cash (chỉ 1 lần)\n"
                   f"⏰ Yêu cầu: Đợi 24 giờ sau khi tham gia\n\n"
                   f"Cách nhận:\n"
                   f"1️⃣ Tham gia kênh: {REWARD_CHANNEL_ID}\n"
                   f"2️⃣ Gõ /checkchannel để xác nhận\n"
                   f"3️⃣ Đợi 24 giờ\n"
                   f"4️⃣ Gõ lại /checkchannel để nhận {REWARD_AMOUNT} cash!",
            
            'success': f"🎉 Chúc mừng! Bạn đã nhận {REWARD_AMOUNT} cash!\n\n"
                      f"💰 Số dư mới: {{new_cash}} cash\n\n"
                      f"Cảm ơn bạn đã tham gia kênh của chúng tôi! 🙏",
            
            'already_claimed': f"ℹ️ Bạn đã nhận phần thưởng kênh rồi!\n\n"
                              f"Mỗi người chỉ được nhận 1 lần duy nhất.",
            
            'not_member': f"❌ Bạn chưa tham gia kênh!\n\n"
                         f"Vui lòng tham gia kênh trước: {REWARD_CHANNEL_ID}\n"
                         f"Sau đó quay lại và gõ /checkchannel",
            
            'join_recorded': [
                f"✅ Đã xác nhận bạn tham gia kênh!\n\n⏰ Vui lòng đợi 24 giờ để nhận {REWARD_AMOUNT} cash\n📅 Bạn có thể nhận sau: {{claim_time}}\n\n💡 Gõ /checkchannel sau 24 giờ để nhận thưởng!",
                f"🎊 Chào mừng bạn đến với gia đình!\n\n⏳ Hãy kiên nhẫn 24 giờ nữa nhé, {REWARD_AMOUNT} cash đang chờ bạn!\n📅 Thời gian nhận thưởng: {{claim_time}}\n\n🎁 Quay lại sau 24 giờ và gõ /checkchannel!",
                f"🌟 Tuyệt vời! Bạn đã join kênh thành công!\n\n⏰ Chỉ cần đợi 24 tiếng nữa thôi, {REWARD_AMOUNT} cash sẽ là của bạn!\n📅 Hẹn gặp lại: {{claim_time}}\n\n💎 Nhớ quay lại gõ /checkchannel nhé!",
                f"🎉 Xác nhận thành công! Bạn đã là thành viên rồi!\n\n⏳ 24 giờ trôi nhanh lắm, {REWARD_AMOUNT} cash đang đợi bạn đấy!\n📅 Có thể nhận từ: {{claim_time}}\n\n🚀 Gõ /checkchannel sau 24h để bay lên!",
                f"🎈 Yeahhh! Chào mừng bạn gia nhập!\n\n⏰ Đợi 24 giờ để bot kiểm tra bạn là thành viên thật nhé!\n📅 Thời gian mở khóa: {{claim_time}}\n💰 Phần thưởng: {REWARD_AMOUNT} cash\n\n✨ Hẹn gặp lại sau 24h!"
            ],
            
            'waiting': [
                f"⏳ Vui lòng đợi thêm {{hours}} giờ nữa!\n\n📅 Bạn có thể nhận sau: {{claim_time}}\n💰 Phần thưởng: {REWARD_AMOUNT} cash\n\n💡 Quay lại sau để nhận thưởng nhé!",
                f"🐢 Chậm mà chắc! Còn {{hours}} giờ nữa thôi!\n\n📅 Thời gian nhận thưởng: {{claim_time}}\n💎 Phần thưởng: {REWARD_AMOUNT} cash\n\n🎁 Kiên nhẫn một chút, quà đang đến!",
                f"⏰ Đồng hồ vẫn đang tích tắc! Còn {{hours}} giờ!\n\n📅 Hẹn gặp lại: {{claim_time}}\n💰 Giải thưởng: {REWARD_AMOUNT} cash\n\n🌟 Thời gian trôi nhanh lắm, đợi tí nhé!",
                f"🎪 Chương trình đang chuẩn bị! {{hours}} giờ nữa!\n\n📅 Show time: {{claim_time}}\n🎁 Phần thưởng: {REWARD_AMOUNT} cash\n\n🎉 Sắp đến lượt bạn rồi!",
                f"🌙 Ngủ một giấc đi, còn {{hours}} giờ mà!\n\n📅 Thức dậy lúc: {{claim_time}}\n💰 Quà tặng: {REWARD_AMOUNT} cash\n\n✨ Mơ về {REWARD_AMOUNT} cash nhé!"
            ],
            
            'can_claim': [
                f"🎉 Chúc mừng! 24 giờ đã trôi qua rồi!\n\n💰 Bạn đã kiên nhẫn chờ đợi, giờ là lúc nhận thưởng {REWARD_AMOUNT} cash!\n👉 Gõ /checkchannel ngay nào! 🎁",
                f"⏰ Đồng hồ đã điểm 24 tiếng rồi đó!\n\n🎊 Phần thưởng {REWARD_AMOUNT} cash đang chờ bạn!\n💎 Gõ /checkchannel để mở hộp quà nhé! 🎁",
                f"🌟 Wow! Bạn đã chờ đủ 24 giờ rồi!\n\n🎁 {REWARD_AMOUNT} cash đang nằm trong túi quà của bạn!\n✨ Gõ /checkchannel để nhận ngay thôi!",
                f"🎈 Yeahhh! Thời gian chờ đợi đã kết thúc!\n\n💰 {REWARD_AMOUNT} cash đang gọi tên bạn đấy!\n🚀 Gõ /checkchannel để bay lên nào!",
                f"🎪 Trống hội đã điểm! 24 giờ đã đủ rồi!\n\n🎁 Phần thưởng {REWARD_AMOUNT} cash sẵn sàng!\n🎯 Gõ /checkchannel để rinh về nhà!"
            ],
            
            'error': "❌ Có lỗi xảy ra. Vui lòng thử lại sau."
        },
        'en': {
            'info': f"🎁 Join our official channel and get {REWARD_AMOUNT} cash for free!\n\n"
                   f"📢 Channel: {REWARD_CHANNEL_ID}\n"
                   f"💰 Reward: {REWARD_AMOUNT} cash (one-time only)\n"
                   f"⏰ Requirement: Wait 24 hours after joining\n\n"
                   f"How to claim:\n"
                   f"1️⃣ Join channel: {REWARD_CHANNEL_ID}\n"
                   f"2️⃣ Type /checkchannel to confirm\n"
                   f"3️⃣ Wait 24 hours\n"
                   f"4️⃣ Type /checkchannel again to get {REWARD_AMOUNT} cash!",
            
            'success': f"🎉 Congratulations! You received {REWARD_AMOUNT} cash!\n\n"
                      f"💰 New balance: {{new_cash}} cash\n\n"
                      f"Thank you for joining our channel! 🙏",
            
            'already_claimed': f"ℹ️ You already claimed the channel reward!\n\n"
                              f"Each user can only claim once.",
            
            'not_member': f"❌ You haven't joined the channel yet!\n\n"
                         f"Please join first: {REWARD_CHANNEL_ID}\n"
                         f"Then come back and type /checkchannel",
            
            'join_recorded': [
                f"✅ Channel membership confirmed!\n\n⏰ Please wait 24 hours to receive {REWARD_AMOUNT} cash\n📅 You can claim after: {{claim_time}}\n\n💡 Type /checkchannel after 24 hours to claim!",
                f"🎊 Welcome to the family!\n\n⏳ Just 24 hours of patience, {REWARD_AMOUNT} cash is waiting!\n📅 Claim time: {{claim_time}}\n\n🎁 Come back in 24 hours and type /checkchannel!",
                f"🌟 Awesome! You've joined successfully!\n\n⏰ Only 24 hours to go, {REWARD_AMOUNT} cash will be yours!\n📅 See you at: {{claim_time}}\n\n💎 Remember to type /checkchannel!",
                f"🎉 Confirmed! You're a member now!\n\n⏳ 24 hours flies by, {REWARD_AMOUNT} cash is waiting!\n📅 Available from: {{claim_time}}\n\n🚀 Type /checkchannel after 24h to blast off!",
                f"🎈 Yeahhh! Welcome aboard!\n\n⏰ Wait 24 hours so we can verify you're a real member!\n📅 Unlock time: {{claim_time}}\n💰 Reward: {REWARD_AMOUNT} cash\n\n✨ See you in 24h!"
            ],
            
            'waiting': [
                f"⏳ Please wait {{hours}} more hours!\n\n📅 You can claim after: {{claim_time}}\n💰 Reward: {REWARD_AMOUNT} cash\n\n💡 Come back later to claim your reward!",
                f"🐢 Slow and steady! Just {{hours}} hours left!\n\n📅 Claim time: {{claim_time}}\n💎 Reward: {REWARD_AMOUNT} cash\n\n🎁 Be patient, your gift is coming!",
                f"⏰ The clock is ticking! {{hours}} hours to go!\n\n📅 See you at: {{claim_time}}\n💰 Prize: {REWARD_AMOUNT} cash\n\n🌟 Time flies, hang in there!",
                f"🎪 The show is preparing! {{hours}} hours more!\n\n📅 Show time: {{claim_time}}\n🎁 Reward: {REWARD_AMOUNT} cash\n\n🎉 Your turn is coming soon!",
                f"🌙 Take a nap, {{hours}} hours remaining!\n\n📅 Wake up at: {{claim_time}}\n💰 Gift: {REWARD_AMOUNT} cash\n\n✨ Dream about {REWARD_AMOUNT} cash!"
            ],
            
            'can_claim': [
                f"🎉 Congratulations! 24 hours have passed!\n\n💰 Your patience paid off! Claim your {REWARD_AMOUNT} cash now!\n👉 Type /checkchannel right away! 🎁",
                f"⏰ The clock has struck 24 hours!\n\n🎊 Your {REWARD_AMOUNT} cash reward is waiting!\n💎 Type /checkchannel to open your gift! 🎁",
                f"🌟 Wow! You've waited the full 24 hours!\n\n🎁 {REWARD_AMOUNT} cash is in your gift box!\n✨ Type /checkchannel to claim it now!",
                f"🎈 Yeahhh! The waiting period is over!\n\n💰 {REWARD_AMOUNT} cash is calling your name!\n🚀 Type /checkchannel to blast off!",
                f"🎪 The drums are rolling! 24 hours complete!\n\n🎁 Your {REWARD_AMOUNT} cash reward is ready!\n🎯 Type /checkchannel to take it home!"
            ],
            
            'error': "❌ An error occurred. Please try again later."
        },
        'zh': {
            'info': f"🎁 加入官方频道，免费获得 {REWARD_AMOUNT} cash！\n\n"
                   f"📢 频道：{REWARD_CHANNEL_ID}\n"
                   f"💰 奖励：{REWARD_AMOUNT} cash（仅限一次）\n"
                   f"⏰ 要求：加入后等待24小时\n\n"
                   f"领取方法：\n"
                   f"1️⃣ 加入频道：{REWARD_CHANNEL_ID}\n"
                   f"2️⃣ 输入 /checkchannel 确认\n"
                   f"3️⃣ 等待24小时\n"
                   f"4️⃣ 再次输入 /checkchannel 获得 {REWARD_AMOUNT} cash！",
            
            'success': f"🎉 恭喜！您获得了 {REWARD_AMOUNT} cash！\n\n"
                      f"💰 新余额：{{new_cash}} cash\n\n"
                      f"感谢您加入我们的频道！🙏",
            
            'already_claimed': f"ℹ️ 您已经领取过频道奖励了！\n\n"
                              f"每个用户只能领取一次。",
            
            'not_member': f"❌ 您还没有加入频道！\n\n"
                         f"请先加入：{REWARD_CHANNEL_ID}\n"
                         f"然后返回并输入 /checkchannel",
            
            'join_recorded': [
                f"✅ 频道会员资格已确认！\n\n⏰ 请等待24小时以获得 {REWARD_AMOUNT} cash\n📅 您可以在以下时间后领取：{{claim_time}}\n\n💡 24小时后输入 /checkchannel 领取！",
                f"🎊 欢迎加入大家庭！\n\n⏳ 只需耐心等待24小时，{REWARD_AMOUNT} cash 等着您！\n📅 领取时间：{{claim_time}}\n\n🎁 24小时后回来输入 /checkchannel！",
                f"🌟 太棒了！您已成功加入！\n\n⏰ 只剩24小时了，{REWARD_AMOUNT} cash 将属于您！\n📅 约定时间：{{claim_time}}\n\n💎 记得输入 /checkchannel！",
                f"🎉 确认成功！您现在是会员了！\n\n⏳ 24小时很快就过，{REWARD_AMOUNT} cash 在等您！\n📅 可领取时间：{{claim_time}}\n\n🚀 24小时后输入 /checkchannel 起飞！",
                f"🎈 耶！欢迎上船！\n\n⏰ 等待24小时让我们验证您是真实会员！\n📅 解锁时间：{{claim_time}}\n💰 奖励：{REWARD_AMOUNT} cash\n\n✨ 24小时后见！"
            ],
            
            'waiting': [
                f"⏳ 请再等待 {{hours}} 小时！\n\n📅 您可以在以下时间后领取：{{claim_time}}\n💰 奖励：{REWARD_AMOUNT} cash\n\n💡 稍后回来领取您的奖励！",
                f"🐢 慢工出细活！还剩 {{hours}} 小时！\n\n📅 领取时间：{{claim_time}}\n💎 奖励：{REWARD_AMOUNT} cash\n\n🎁 耐心点，礼物正在路上！",
                f"⏰ 时钟在滴答！还有 {{hours}} 小时！\n\n📅 约定时间：{{claim_time}}\n💰 奖品：{REWARD_AMOUNT} cash\n\n🌟 时间过得很快，坚持住！",
                f"🎪 节目正在准备！还有 {{hours}} 小时！\n\n📅 开场时间：{{claim_time}}\n🎁 奖励：{REWARD_AMOUNT} cash\n\n🎉 马上就轮到您了！",
                f"🌙 睡一觉吧，还剩 {{hours}} 小时！\n\n📅 醒来时间：{{claim_time}}\n💰 礼物：{REWARD_AMOUNT} cash\n\n✨ 梦见 {REWARD_AMOUNT} cash 吧！"
            ],
            
            'can_claim': [
                f"🎉 恭喜！24小时已经过去了！\n\n💰 您的耐心得到了回报！现在领取您的 {REWARD_AMOUNT} cash！\n👉 立即输入 /checkchannel！🎁",
                f"⏰ 时钟已经敲响24小时！\n\n🎊 您的 {REWARD_AMOUNT} cash 奖励正在等待！\n💎 输入 /checkchannel 打开您的礼物！🎁",
                f"🌟 哇！您已经等待了整整24小时！\n\n🎁 {REWARD_AMOUNT} cash 在您的礼盒里！\n✨ 输入 /checkchannel 立即领取！",
                f"🎈 耶！等待期结束了！\n\n💰 {REWARD_AMOUNT} cash 在呼唤您的名字！\n🚀 输入 /checkchannel 起飞吧！",
                f"🎪 鼓声响起！24小时完成！\n\n🎁 您的 {REWARD_AMOUNT} cash 奖励准备好了！\n🎯 输入 /checkchannel 带回家！"
            ],
            
            'error': "❌ 发生错误。请稍后再试。"
        }
    }
    
    return messages.get(language, messages['vi'])
