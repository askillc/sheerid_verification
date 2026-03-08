# Force reload: 2026-02-17 11:30 - Enable coins verify (25 xu)
from flask import Flask, request, jsonify
import sqlite3
import json
import os
import asyncio

# Locket Gold services
from api.services import locket, nextdns

# ============================================
# MULTILINGUAL SUPPORT - Embedded translations
# ============================================
TRANSLATIONS = {
    # Welcome messages
    'welcome_message': {
        'vi': '🎉 Chào mừng bạn đến với SheerID VIP Bot!\n\n📋 Lệnh cơ bản:\n/me - Xem thông tin tài khoản\n/verify <link> - Xác minh sinh viên\n/checkin - Điểm danh nhận xu\n/shop - Cửa hàng sản phẩm\n/lang - Đổi ngôn ngữ\n\n💡 Gửi /help để xem hướng dẫn chi tiết\n\n🎁 Nhận 10 cash miễn phí:\n📢 Tham gia: @channel_sheerid_vip_bot\n⏰ Đợi 24 giờ\n👉 Gõ /checkchannel để nhận!',
        'en': '🎉 Welcome to SheerID VIP Bot!\n\n📋 Basic commands:\n/me - View account info\n/verify <link> - Student verification\n/checkin - Daily check-in\n/shop - Product store\n/lang - Change language\n\n💡 Send /help for detailed guide\n\n🎁 Get 10 cash for free:\n📢 Join: @channel_sheerid_vip_bot\n⏰ Wait 24 hours\n👉 Type /checkchannel to claim!',
        'zh': '🎉 欢迎使用 SheerID VIP 机器人！\n\n📋 基本命令：\n/me - 查看账户信息\n/verify <link> - 学生验证\n/checkin - 每日签到\n/shop - 产品商店\n/lang - 更改语言\n\n💡 发送 /help 查看详细指南\n\n🎁 免费获得 10 cash：\n📢 加入：@channel_sheerid_vip_bot\n⏰ 等待24小时\n👉 输入 /checkchannel 领取！'
    },
    
    # Language selection
    'select_language': {
        'vi': '🌍 Chọn ngôn ngữ của bạn:',
        'en': '🌍 Select your language:',
        'zh': '🌍 选择您的语言：'
    },
    'language_changed': {
        'vi': '✅ Đã đổi ngôn ngữ sang Tiếng Việt',
        'en': '✅ Language changed to English',
        'zh': '✅ 语言已更改为中文'
    },
    
    # Check-in
    'checkin_success': {
        'vi': '✅ Điểm danh thành công!\n\n🪙 +1 xu\n📅 Ngày {day}\n\n💰 Tổng xu: {total_coins}',
        'en': '✅ Check-in Successful!\n\n🪙 +1 coin\n📅 Day {day}\n\n💰 Total coins: {total_coins}',
        'zh': '✅ 签到成功！\n\n🪙 +1 金币\n📅 第 {day} 天\n\n💰 总金币：{total_coins}'
    },
    'checkin_already': {
        'vi': '⏰ Bạn đã điểm danh hôm nay rồi!\n\n🕐 Quay lại vào ngày mai để nhận xu.',
        'en': '⏰ You have already checked in today!\n\n🕐 Come back tomorrow to get coins.',
        'zh': '⏰ 您今天已经签到过了！\n\n🕐 明天再来获取金币。'
    },
    
    # Help
    'help_message': {
        'vi': '📋 Hướng dẫn sử dụng SheerID VIP Bot\n\n🔹 Lệnh cơ bản:\n/start - Khởi động bot\n/me - Xem thông tin tài khoản\n/verify <link> - Xác minh sinh viên\n/vs <link> - Xác minh Spotify Student\n/vc <link> - Xác minh giáo viên\n/queue - Xem hàng chờ verify\n/shop - Cửa hàng sản phẩm\n/checkin - Điểm danh nhận xu\n/giftcode <code> - Sử dụng mã quà\n/nap - Nạp tiền (chỉ ngân hàng VN)\n/crypto - Nạp tiền crypto (quốc tế)\n/lang - Đổi ngôn ngữ\n\n💰 Hệ thống tiền tệ:\n🪙 Xu: Dùng để verify\n💵 Cash: Dùng để mua VIP, sản phẩm\n\n📞 Hỗ trợ: @meepzizhere',
        'en': '📋 SheerID VIP Bot User Guide\n\n🔹 Basic Commands:\n/start - Start bot\n/me - View account info\n/verify <link> - Student verification\n/vs <link> - Spotify Student verification\n/vc <link> - Teacher verification\n/queue - View verification queue\n/shop - Product store\n/checkin - Daily check-in\n/giftcode <code> - Use gift code\n/nap - Deposit (Vietnam bank only)\n/crypto - Crypto deposit (International)\n/lang - Change language\n\n⚠️ Note: /nap only works with Vietnamese banks\n🌍 International users: Please use /crypto\n\n📞 Support: @meepzizhere',
        'zh': '📋 SheerID VIP 机器人使用指南\n\n🔹 基本命令：\n/start - 启动机器人\n/me - 查看账户信息\n/verify <link> - 学生验证\n/vs <link> - Spotify 学生验证\n/vc <link> - 教师验证\n/queue - 查看验证队列\n/shop - 产品商店\n/checkin - 每日签到\n/giftcode <code> - 使用礼品码\n/nap - 充值（仅限越南银行）\n/crypto - 加密货币充值（国际用户）\n/lang - 更改语言\n\n⚠️ 注意：/nap 仅适用于越南银行\n🌍 国际用户：请使用 /crypto\n\n📞 支持：@meepzizhere'
    },
    
    # Verification
    'verify_start': {
        'vi': '⏳ Đang xử lý xác minh...\n\n🆔 Job ID: {job_id}\n⏰ Vui lòng chờ 1-2 phút',
        'en': '⏳ Processing verification...\n\n🆔 Job ID: {job_id}\n⏰ Please wait 1-2 minutes',
        'zh': '⏳ 正在处理验证...\n\n🆔 任务ID: {job_id}\n⏰ 请等待1-2分钟'
    },
    'verify_success': {
        'vi': '🎉 Xác minh thành công!\n\n✅ Trạng thái: Đã xác minh\n🆔 Job ID: {job_id}\n\n🎓 Bạn đã có thể sử dụng ưu đãi sinh viên!',
        'en': '🎉 Verification Successful!\n\n✅ Status: Verified\n🆔 Job ID: {job_id}\n\n🎓 You can now use student discounts!',
        'zh': '🎉 验证成功！\n\n✅ 状态：已验证\n🆔 任务ID: {job_id}\n\n🎓 您现在可以使用学生优惠了！'
    },
    'verify_failed': {
        'vi': '❌ Xác minh thất bại\n\n🔍 Lý do: {reason}\n🆔 Job ID: {job_id}\n\n💡 Vui lòng thử lại với link khác.',
        'en': '❌ Verification Failed\n\n🔍 Reason: {reason}\n🆔 Job ID: {job_id}\n\n💡 Please try again with a different link.',
        'zh': '❌ 验证失败\n\n🔍 原因：{reason}\n🆔 任务ID: {job_id}\n\n💡 请使用其他链接重试。'
    },
    'verify_insufficient': {
        'vi': '❌ Không đủ Xu/Cash!\n\n💵 CASH: {cash} | 🪙 Xu: {coins}\n💰 Cần: 10 Xu/Cash\n\n💡 Dùng /nap để nạp thêm\n🌍 Dùng /crypto để nạp crypto',
        'en': '❌ Insufficient Coins/Cash!\n\n💵 CASH: {cash} | 🪙 Coins: {coins}\n💰 Need: 10 Coins/Cash\n\n💡 Use /nap to top up\n🌍 Use /crypto for crypto deposit',
        'zh': '❌ 金币/现金不足！\n\n💵 现金: {cash} | 🪙 金币: {coins}\n💰 需要: 10 金币/现金\n\n💡 使用 /nap 充值\n🌍 使用 /crypto 加密货币充值'
    },
    'verify_invalid_link': {
        'vi': '❌ Link không hợp lệ!\n\n💡 Vui lòng gửi link SheerID hợp lệ.\nVí dụ: /verify https://services.sheerid.com/...',
        'en': '❌ Invalid link!\n\n💡 Please send a valid SheerID link.\nExample: /verify https://services.sheerid.com/...',
        'zh': '❌ 链接无效！\n\n💡 请发送有效的 SheerID 链接。\n示例：/verify https://services.sheerid.com/...'
    },
    
    # Shop
    'shop_title': {
        'vi': '🛒 Cửa hàng SheerID VIP\n\n💰 Số dư: {coins} xu | {cash} cash',
        'en': '🛒 SheerID VIP Shop\n\n💰 Balance: {coins} coins | {cash} cash',
        'zh': '🛒 SheerID VIP 商店\n\n💰 余额：{coins} 金币 | {cash} 现金'
    },
    'shop_buy_success': {
        'vi': '✅ Mua hàng thành công!\n\n📦 Sản phẩm: {product}\n💰 Giá: {price}',
        'en': '✅ Purchase successful!\n\n📦 Product: {product}\n💰 Price: {price}',
        'zh': '✅ 购买成功！\n\n📦 产品：{product}\n💰 价格：{price}'
    },
    'shop_insufficient': {
        'vi': '❌ Không đủ tiền!\n\n💰 Số dư: {balance}\n💵 Cần: {price}',
        'en': '❌ Insufficient funds!\n\n💰 Balance: {balance}\n💵 Need: {price}',
        'zh': '❌ 余额不足！\n\n💰 余额：{balance}\n💵 需要：{price}'
    },
    'shop_out_of_stock': {
        'vi': '❌ Sản phẩm đã hết hàng!',
        'en': '❌ Product out of stock!',
        'zh': '❌ 产品缺货！'
    },
    
    # Giftcode
    'giftcode_success': {
        'vi': '🎁 Giftcode thành công!\n\n💰 Bạn đã nhận: {amount} {type}\n🎫 Code: {code}\n\n✨ Chúc mừng bạn!',
        'en': '🎁 Giftcode Success!\n\n💰 You received: {amount} {type}\n🎫 Code: {code}\n\n✨ Congratulations!',
        'zh': '🎁 礼品码成功！\n\n💰 您获得了：{amount} {type}\n🎫 代码：{code}\n\n✨ 恭喜您！'
    },
    'giftcode_invalid': {
        'vi': '❌ Giftcode không hợp lệ hoặc đã hết lượt sử dụng.',
        'en': '❌ Invalid giftcode or usage limit exceeded.',
        'zh': '❌ 礼品码无效或已超出使用次数。'
    },
    'giftcode_already_used': {
        'vi': '❌ Bạn đã sử dụng giftcode này rồi!',
        'en': '❌ You have already used this giftcode!',
        'zh': '❌ 您已经使用过此礼品码！'
    },
    'giftcode_usage': {
        'vi': '💡 Cách sử dụng giftcode:\n\n📝 Gõ: /giftcode <mã_của_bạn>\n\n🎁 Ví dụ: /giftcode NEWYEAR2024\n\n📢 Theo dõi kênh để nhận mã mới:\nhttps://t.me/channel_sheerid_vip_bot',
        'en': '💡 How to use giftcode:\n\n📝 Type: /giftcode <your_code>\n\n🎁 Example: /giftcode NEWYEAR2024\n\n📢 Follow channel for new codes:\nhttps://t.me/channel_sheerid_vip_bot',
        'zh': '💡 如何使用礼品码：\n\n📝 输入：/giftcode <您的代码>\n\n🎁 示例：/giftcode NEWYEAR2024\n\n📢 关注频道获取新代码：\nhttps://t.me/channel_sheerid_vip_bot'
    },
    
    # VIP
    'vip_active': {
        'vi': '✅ Đang hoạt động',
        'en': '✅ Active',
        'zh': '✅ 活跃'
    },
    'vip_expired': {
        'vi': '❌ Không có VIP',
        'en': '❌ No VIP',
        'zh': '❌ 无VIP'
    },
    'vip_until': {
        'vi': '✅ Còn hạn đến {date}',
        'en': '✅ Valid until {date}',
        'zh': '✅ 有效期至 {date}'
    },
    
    # Crypto
    'crypto_deposit': {
        'vi': '💰 Nạp tiền bằng Crypto\n\n🔹 USDT (TRC20):\nĐịa chỉ: {trc20}\n\n🔹 USDT (BEP20):\nĐịa chỉ: {bep20}\n\n💱 Tỷ giá: 1 USDT = {rate} Cash\n⏰ Xử lý tự động trong 5-10 phút',
        'en': '💰 Crypto Deposit\n\n🔹 USDT (TRC20):\nAddress: {trc20}\n\n🔹 USDT (BEP20):\nAddress: {bep20}\n\n💱 Rate: 1 USDT = {rate} Cash\n⏰ Auto-processed in 5-10 minutes',
        'zh': '💰 加密货币充值\n\n🔹 USDT (TRC20):\n地址：{trc20}\n\n🔹 USDT (BEP20):\n地址：{bep20}\n\n💱 汇率：1 USDT = {rate} 现金\n⏰ 5-10分钟内自动处理'
    },
    
    # Referral
    'referral_info': {
        'vi': '🎁 Hệ thống giới thiệu\n\n🔗 Link giới thiệu của bạn:\n{link}\n\n👥 Đã mời: {count} người\n💰 Thưởng: +3 xu/người',
        'en': '🎁 Referral System\n\n🔗 Your referral link:\n{link}\n\n👥 Referred: {count} people\n💰 Reward: +3 coins/person',
        'zh': '🎁 推荐系统\n\n🔗 您的推荐链接：\n{link}\n\n👥 已推荐：{count} 人\n💰 奖励：+3 金币/人'
    },
    
    # Maintenance
    'maintenance_mode': {
        'vi': '🔧 Hệ thống đang bảo trì\n\nChúng tôi đang nâng cấp hệ thống.\n\n⏰ Vui lòng thử lại sau.',
        'en': '🔧 System Under Maintenance\n\nWe are upgrading the system.\n\n⏰ Please try again later.',
        'zh': '🔧 系统维护中\n\n我们正在升级系统。\n\n⏰ 请稍后再试。'
    },
    
    # Errors
    'error_generic': {
        'vi': '❌ Có lỗi xảy ra. Vui lòng thử lại sau.',
        'en': '❌ An error occurred. Please try again later.',
        'zh': '❌ 发生错误。请稍后再试。'
    },
    'error_start_first': {
        'vi': '❌ Vui lòng /start trước',
        'en': '❌ Please /start first',
        'zh': '❌ 请先 /start'
    },
    'invalid_command': {
        'vi': '❌ Lệnh không hợp lệ. Gửi /help để xem danh sách lệnh.',
        'en': '❌ Invalid command. Send /help to see command list.',
        'zh': '❌ 无效命令。发送 /help 查看命令列表。'
    },
    
    # Account info labels
    'account_title': {
        'vi': '👤 Thông tin cá nhân:',
        'en': '👤 Account Information:',
        'zh': '👤 账户信息：'
    },
    'account_id': {
        'vi': '🆔 ID',
        'en': '🆔 ID',
        'zh': '🆔 ID'
    },
    'account_name': {
        'vi': '👤 Tên',
        'en': '👤 Name',
        'zh': '👤 姓名'
    },
    'account_username': {
        'vi': '📱 Username',
        'en': '📱 Username',
        'zh': '📱 用户名'
    },
    'account_coins': {
        'vi': '🪙 Số dư Xu',
        'en': '🪙 Coins Balance',
        'zh': '🪙 金币余额'
    },
    'account_cash': {
        'vi': '💵 Số dư CASH',
        'en': '💵 Cash Balance',
        'zh': '💵 现金余额'
    },
    'account_vip': {
        'vi': '👑 VIP',
        'en': '👑 VIP',
        'zh': '👑 VIP'
    },
    'account_joined': {
        'vi': '📅 Tham gia',
        'en': '📅 Joined',
        'zh': '📅 加入时间'
    },
    'account_rate': {
        'vi': '💰 Tỷ giá',
        'en': '💰 Exchange Rate',
        'zh': '💰 汇率'
    },
    'account_rate_info': {
        'vi': '• 1 xu = 1,000 VNĐ\n• 1 cash = 1,000 VNĐ',
        'en': '• 1 coin = 1,000 VND\n• 1 cash = 1,000 VND',
        'zh': '• 1 金币 = 1,000 越南盾\n• 1 现金 = 1,000 越南盾'
    },
    'account_deposit': {
        'vi': '🔗 Nạp cash: /nap',
        'en': '🔗 Deposit: /nap',
        'zh': '🔗 充值: /nap'
    },
    'account_verify_title': {
        'vi': '📊 Verify:',
        'en': '📊 Verification:',
        'zh': '📊 验证：'
    },
    'account_payment_title': {
        'vi': '💳 Nạp tiền:',
        'en': '💳 Payments:',
        'zh': '💳 充值记录：'
    },
    'account_recent_jobs': {
        'vi': '📝 5 job gần nhất:',
        'en': '📝 Recent 5 jobs:',
        'zh': '📝 最近5个任务：'
    },
    'account_tip': {
        'vi': '💡 Sử dụng /verify (URL) để xác minh SheerID',
        'en': '💡 Use /verify (URL) to verify SheerID',
        'zh': '💡 使用 /verify (URL) 进行 SheerID 验证'
    },
    'account_support': {
        'vi': '❓ Hỗ trợ: @meepzizhere',
        'en': '❓ Support: @meepzizhere',
        'zh': '❓ 支持: @meepzizhere'
    },
    'account_channel': {
        'vi': '📢 Kênh thông báo: https://t.me/channel_sheerid_vip_bot',
        'en': '📢 Channel: https://t.me/channel_sheerid_vip_bot',
        'zh': '📢 频道: https://t.me/channel_sheerid_vip_bot'
    },
    
    # Currency types
    'coins': {
        'vi': 'xu',
        'en': 'coins',
        'zh': '金币'
    },
    'cash': {
        'vi': 'cash',
        'en': 'cash',
        'zh': '现金'
    }
}

DEFAULT_LANGUAGE = 'vi'
LANGUAGES = {
    'vi': '🇻🇳 Tiếng Việt',
    'en': '🇺🇸 English', 
    'zh': '🇨🇳 中文'
}

def get_text(key, lang=None, **kwargs):
    """Get translated text for given key and language"""
    if lang is None:
        lang = DEFAULT_LANGUAGE
    if key not in TRANSLATIONS:
        return f"[Missing: {key}]"
    if lang not in TRANSLATIONS[key]:
        lang = DEFAULT_LANGUAGE
    text = TRANSLATIONS[key][lang]
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text

def get_user_language(supabase, telegram_id):
    """Get user's preferred language from database"""
    try:
        if supabase:
            result = supabase.table('users').select('language').eq('telegram_id', telegram_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0].get('language', DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE
    except Exception as e:
        print(f"Error getting user language: {e}")
    return DEFAULT_LANGUAGE

def set_user_language(supabase, telegram_id, language):
    """Set user's preferred language in database"""
    try:
        if supabase and language in LANGUAGES:
            supabase.table('users').update({'language': language}).eq('telegram_id', telegram_id).execute()
            return True
    except Exception as e:
        print(f"Error setting user language: {e}")
    return False
# ============================================

# Performance optimization: Global caches and connection pooling
USER_CACHE = {}  # Cache user data
CONFIG_CACHE_TIME = 0  # Last config load time
USER_CACHE_TIME = {}  # Per-user cache timestamps
CACHE_DURATION = 30  # Cache duration in seconds
USER_CACHE_DURATION = 10  # User cache duration in seconds

# Global HTTP session for connection pooling
TELEGRAM_SESSION = None

# Global set to track notified jobs to prevent duplicate notifications
NOTIFIED_JOBS = set()

# Queue system removed - verifications run immediately
import threading

# ============================================
# TEACHER VERIFICATION QUEUE SYSTEM
# Giới hạn 5 teacher verifications đồng thời
# ============================================
TEACHER_QUEUE_LOCK = threading.Lock()
TEACHER_ACTIVE_JOBS = set()  # Set of active teacher job_ids
TEACHER_QUEUE = []  # List of (chat_id, user, url, job_id, payment_method, user_lang) waiting
TEACHER_MAX_CONCURRENT = 999  # Maximum concurrent teacher verifications (no queue limit)

def get_teacher_queue_position(job_id):
    """Get position in teacher queue (0 = not in queue, 1+ = position)"""
    with TEACHER_QUEUE_LOCK:
        for i, item in enumerate(TEACHER_QUEUE):
            if item[3] == job_id:  # job_id is at index 3
                return i + 1
        return 0

def get_teacher_queue_status():
    """Get current teacher queue status"""
    with TEACHER_QUEUE_LOCK:
        return {
            'active': len(TEACHER_ACTIVE_JOBS),
            'waiting': len(TEACHER_QUEUE),
            'max_concurrent': TEACHER_MAX_CONCURRENT
        }

def can_start_teacher_verification():
    """Check if we can start a new teacher verification"""
    with TEACHER_QUEUE_LOCK:
        return len(TEACHER_ACTIVE_JOBS) < TEACHER_MAX_CONCURRENT

def add_teacher_to_active(job_id):
    """Add a job to active teacher jobs"""
    with TEACHER_QUEUE_LOCK:
        TEACHER_ACTIVE_JOBS.add(job_id)
        print(f"🎓 Added teacher job {job_id} to active. Active: {len(TEACHER_ACTIVE_JOBS)}/{TEACHER_MAX_CONCURRENT}")

def remove_teacher_from_active(job_id):
    """Remove a job from active teacher jobs and process next in queue"""
    with TEACHER_QUEUE_LOCK:
        if job_id in TEACHER_ACTIVE_JOBS:
            TEACHER_ACTIVE_JOBS.discard(job_id)
            print(f"🎓 Removed teacher job {job_id} from active. Active: {len(TEACHER_ACTIVE_JOBS)}/{TEACHER_MAX_CONCURRENT}")
        
        # Process next job in queue if available
        if TEACHER_QUEUE and len(TEACHER_ACTIVE_JOBS) < TEACHER_MAX_CONCURRENT:
            next_job = TEACHER_QUEUE.pop(0)
            chat_id, user, url, next_job_id, payment_method, user_lang = next_job
            TEACHER_ACTIVE_JOBS.add(next_job_id)
            # Capture queue_remaining inside lock for accurate count
            queue_remaining_snapshot = len(TEACHER_QUEUE)
            print(f"🎓 Starting queued teacher job {next_job_id}. Queue remaining: {queue_remaining_snapshot}")
            
            # Start the verification in a new thread
            def start_queued_job(q_remaining=queue_remaining_snapshot):
                try:
                    # Notify user their turn has come
                    send_telegram_message(chat_id, f"""✅ Đến lượt của bạn!

🆔 Job ID: `{next_job_id}`
⏳ Đang bắt đầu verify Teacher...
📊 Hàng chờ: {q_remaining} người đang chờ""")
                    
                    # Execute the verification
                    _execute_teacher_verification(chat_id, user, url, next_job_id, payment_method, user_lang)
                except Exception as e:
                    print(f"❌ Error starting queued teacher job {next_job_id}: {e}")
                    remove_teacher_from_active(next_job_id)
            
            thread = threading.Thread(target=start_queued_job, daemon=True)
            thread.start()

def add_teacher_to_queue(chat_id, user, url, job_id, payment_method, user_lang):
    """Add a teacher verification to the queue (with duplicate check)"""
    with TEACHER_QUEUE_LOCK:
        # Check if job already in queue or active
        if job_id in TEACHER_ACTIVE_JOBS:
            print(f"🎓 Teacher job {job_id} already active, skipping queue add")
            return -1  # Already active
        
        for item in TEACHER_QUEUE:
            if item[3] == job_id:  # job_id is at index 3
                print(f"🎓 Teacher job {job_id} already in queue, skipping duplicate add")
                return -1  # Already in queue
        
        TEACHER_QUEUE.append((chat_id, user, url, job_id, payment_method, user_lang))
        position = len(TEACHER_QUEUE)
        print(f"🎓 Added teacher job {job_id} to queue at position {position}")
        return position

# ============================================
# STUDENT VERIFICATION QUEUE SYSTEM
# Giới hạn 3 student verifications đồng thời
# ============================================
STUDENT_QUEUE_LOCK = threading.Lock()
STUDENT_ACTIVE_JOBS = set()  # Set of active student job_ids
STUDENT_QUEUE = []  # List of (chat_id, user, url, job_id, payment_method, user_lang) waiting
STUDENT_MAX_CONCURRENT = 999  # No queue limit - process all immediately

# Multilingual messages for student queue
STUDENT_QUEUE_MESSAGES = {
    'queue_added': {
        'vi': """⏳ Bạn đã được thêm vào hàng chờ!

🆔 Job ID: `{job_id}`
📊 Vị trí trong hàng chờ: #{position}
👥 Đang xử lý: {active}/{max_concurrent}
⏰ Thời gian chờ ước tính: ~{wait_time} phút

💡 Hệ thống sẽ tự động thông báo khi đến lượt bạn.""",
        'en': """⏳ You have been added to the queue!

🆔 Job ID: `{job_id}`
📊 Queue position: #{position}
👥 Processing: {active}/{max_concurrent}
⏰ Estimated wait time: ~{wait_time} minutes

💡 System will notify you when it's your turn.""",
        'zh': """⏳ 您已加入排队！

🆔 任务ID: `{job_id}`
📊 排队位置: #{position}
👥 正在处理: {active}/{max_concurrent}
⏰ 预计等待时间: ~{wait_time} 分钟

💡 轮到您时系统会自动通知。"""
    },
    'your_turn': {
        'vi': """✅ Đến lượt của bạn!

🆔 Job ID: `{job_id}`
⏳ Đang bắt đầu verify Student...
📊 Hàng chờ: {queue_remaining} người đang chờ""",
        'en': """✅ It's your turn!

🆔 Job ID: `{job_id}`
⏳ Starting Student verification...
📊 Queue: {queue_remaining} people waiting""",
        'zh': """✅ 轮到您了！

🆔 任务ID: `{job_id}`
⏳ 正在开始学生验证...
📊 排队: {queue_remaining} 人等待中"""
    },
    'processing': {
        'vi': """✅ Đã tạo job verify!

🆔 Job ID: `{job_id}`
🔗 Link: {display_url}
💰 Phí: {fee_text}
{coin_status}
⏳ Trạng thái: Đang xử lý...
📊 Slot: {active}/{max_concurrent}""",
        'en': """✅ Verification job created!

🆔 Job ID: `{job_id}`
🔗 Link: {display_url}
💰 Fee: {fee_text}
{coin_status}
⏳ Status: Processing...
📊 Slot: {active}/{max_concurrent}""",
        'zh': """✅ 验证任务已创建！

🆔 任务ID: `{job_id}`
🔗 链接: {display_url}
💰 费用: {fee_text}
{coin_status}
⏳ 状态: 处理中...
📊 插槽: {active}/{max_concurrent}"""
    }
}

def get_student_queue_position(job_id):
    """Get position in student queue (0 = not in queue, 1+ = position)"""
    with STUDENT_QUEUE_LOCK:
        for i, item in enumerate(STUDENT_QUEUE):
            if item[3] == job_id:  # job_id is at index 3
                return i + 1
        return 0

def get_student_queue_status():
    """Get current student queue status"""
    with STUDENT_QUEUE_LOCK:
        return {
            'active': len(STUDENT_ACTIVE_JOBS),
            'waiting': len(STUDENT_QUEUE),
            'max_concurrent': STUDENT_MAX_CONCURRENT
        }

def can_start_student_verification():
    """Check if we can start a new student verification"""
    with STUDENT_QUEUE_LOCK:
        return len(STUDENT_ACTIVE_JOBS) < STUDENT_MAX_CONCURRENT

def add_student_to_active(job_id):
    """Add a job to active student jobs"""
    with STUDENT_QUEUE_LOCK:
        STUDENT_ACTIVE_JOBS.add(job_id)
        print(f"🎓 Added student job {job_id} to active. Active: {len(STUDENT_ACTIVE_JOBS)}/{STUDENT_MAX_CONCURRENT}")

def remove_student_from_active(job_id):
    """Remove a job from active student jobs and process next in queue"""
    with STUDENT_QUEUE_LOCK:
        if job_id in STUDENT_ACTIVE_JOBS:
            STUDENT_ACTIVE_JOBS.discard(job_id)
            print(f"🎓 Removed student job {job_id} from active. Active: {len(STUDENT_ACTIVE_JOBS)}/{STUDENT_MAX_CONCURRENT}")
        
        # Process next job in queue if available
        if STUDENT_QUEUE and len(STUDENT_ACTIVE_JOBS) < STUDENT_MAX_CONCURRENT:
            next_job = STUDENT_QUEUE.pop(0)
            chat_id, user, url, next_job_id, payment_method, user_lang = next_job
            STUDENT_ACTIVE_JOBS.add(next_job_id)
            # Capture queue_remaining inside lock for accurate count
            queue_remaining_snapshot = len(STUDENT_QUEUE)
            print(f"🎓 Starting queued student job {next_job_id}. Queue remaining: {queue_remaining_snapshot}")
            
            # Start the verification in a new thread
            def start_queued_student_job(q_remaining=queue_remaining_snapshot):
                try:
                    # Notify user their turn has come (multilingual)
                    msg_template = STUDENT_QUEUE_MESSAGES['your_turn'].get(user_lang, STUDENT_QUEUE_MESSAGES['your_turn']['vi'])
                    msg = msg_template.format(
                        job_id=next_job_id,
                        queue_remaining=q_remaining
                    )
                    send_telegram_message(chat_id, msg)
                    
                    # Execute the verification
                    _execute_verification(chat_id, user, url, next_job_id, payment_method, user_lang)
                except Exception as e:
                    print(f"❌ Error starting queued student job {next_job_id}: {e}")
                finally:
                    # Always remove from active when done to process next in queue
                    remove_student_from_active(next_job_id)
            
            thread = threading.Thread(target=start_queued_student_job, daemon=True)
            thread.start()

def add_student_to_queue(chat_id, user, url, job_id, payment_method, user_lang):
    """Add a student verification to the queue (with duplicate check)"""
    with STUDENT_QUEUE_LOCK:
        # Check if job already in queue or active
        if job_id in STUDENT_ACTIVE_JOBS:
            print(f"🎓 Job {job_id} already active, skipping queue add")
            return -1  # Already active
        
        for item in STUDENT_QUEUE:
            if item[3] == job_id:  # job_id is at index 3
                print(f"🎓 Job {job_id} already in queue, skipping duplicate add")
                return -1  # Already in queue
        
        STUDENT_QUEUE.append((chat_id, user, url, job_id, payment_method, user_lang))
        position = len(STUDENT_QUEUE)
        print(f"🎓 Added student job {job_id} to queue at position {position}")
        return position

def _execute_teacher_verification(chat_id, user, url, job_id, payment_method, user_lang='vi'):
    """Execute teacher verification API call - with queue management"""
    try:
        # Re-check payment ability just before dispatch
        user_id = user.get('id') if isinstance(user, dict) else user[0]
        vip_active = is_vip_active(user)
        
        if not vip_active:
            wallets_check = supabase_get_wallets_by_user_id(user_id)
            if wallets_check:
                c_cash, c_bonus = wallets_check
                if (c_bonus < 50) and (c_cash < 50):
                    send_telegram_message(chat_id, "❌ Số dư thay đổi: Không đủ Xu/Cash để tiếp tục verify Teacher.")
                    remove_teacher_from_active(job_id)
                    return
        
        print(f"🎓 DEBUG: Starting teacher verification for job {job_id}")
        
        # Call the ChatGPT verification API
        import requests
        api_url = "https://dqsheerid.vercel.app/start-verification-chatgpt"
        payload = {
            "url": url,
            "job_id": job_id
        }
        
        print(f"🎓 DEBUG: Calling API {api_url} with payload: {payload}")
        try:
            response = requests.post(api_url, json=payload, timeout=35)
        except requests.exceptions.Timeout:
            print(f"🎓 WARN: Teacher verification API timed out for job {job_id}")
            send_telegram_message(chat_id, "⏳ Teacher verification đang được xử lý... Hệ thống sẽ tự động thông báo khi xong.")
            # Don't remove from active - job is still processing in background
            return
        except requests.exceptions.RequestException as e:
            print(f"🎓 WARN: Teacher verification API error for job {job_id}: {e}")
            send_telegram_message(chat_id, "⏳ Teacher verification đang được xử lý... Hệ thống sẽ tự động thông báo khi xong.")
            return
        
        print(f"🎓 DEBUG: API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"🎓 DEBUG: API response result: {result}")
            if result.get('success'):
                result_status = result.get('status', '').lower()
                if result_status == 'pending' or result_status == 'pending_background':
                    send_telegram_message(chat_id, """🎓 Teacher verification đang được SheerID review!

⏳ Trạng thái: Đang chờ kết quả từ SheerID
📋 Hệ thống sẽ tự động poll và thông báo khi có kết quả
⏱️ Thời gian chờ: 5-40 phút

💡 Bạn có thể tiếp tục sử dụng bot bình thường.""")
                elif result_status == 'completed':
                    # Job completed immediately - remove from active
                    remove_teacher_from_active(job_id)
                elif result_status == 'failed':
                    remove_teacher_from_active(job_id)
            else:
                error_msg = result.get('error', 'Unknown error')
                send_telegram_message(chat_id, f"❌ Lỗi verify Teacher: {error_msg}")
                remove_teacher_from_active(job_id)
        else:
            send_telegram_message(chat_id, f"❌ Lỗi xử lý. Vui lòng thử lại sau.")
            remove_teacher_from_active(job_id)
            
    except Exception as e:
        print(f"🎓 ERROR in teacher verification for job {job_id}: {e}")
        import traceback
        traceback.print_exc()
        remove_teacher_from_active(job_id)

def _execute_verification(chat_id, user, url, job_id, payment_method, user_lang='vi', verification_type='sheerid'):
    """Execute the actual verification API call - called from queue system"""
    telegram_id = None  # Track for VIP concurrent limit
    try:
        # Handle case where user is None (added from index.py queue)
        if user is None:
            # Get user from job info
            try:
                from .supabase_client import get_verification_job_by_id, get_user_by_telegram_id
                job_info = get_verification_job_by_id(job_id)
                if job_info:
                    telegram_id = job_info.get('telegram_id')
                    if telegram_id:
                        user = get_user_by_telegram_id(telegram_id)
                        chat_id = telegram_id
            except Exception as e:
                print(f"⚠️ Failed to get user from job: {e}")
        
        # Get telegram_id for VIP tracking
        if user:
            telegram_id = user.get('telegram_id') if isinstance(user, dict) else str(chat_id)
        
        # Track active verification for VIP concurrent limit
        if telegram_id and payment_method == 'free':
            try:
                from .vip_tiers import add_active_verification
                add_active_verification(telegram_id, job_id)
            except Exception as e:
                print(f"⚠️ Error tracking active verification: {e}")
        
        # Re-check payment ability just before dispatch
        if user is None:
            print(f"⚠️ User is None for job {job_id}, skipping payment check")
            user_id = None
            vip_active = False
        else:
            user_id = user.get('id') if isinstance(user, dict) else user[0]
            vip_active = is_vip_active(user)
        
        if not vip_active and user_id is not None:
            wallets_check = supabase_get_wallets_by_user_id(user_id)
            if wallets_check:
                c_cash, c_bonus = wallets_check
                if (c_bonus < 5) and (c_cash < 5):
                    if chat_id:
                        send_telegram_message(chat_id, "❌ Số dư thay đổi: Không đủ Xu/Cash để tiếp tục verify.")
                    return
        
        print(f"DEBUG: About to call verification API for job {job_id}")
        
        # Call the verification API with from_queue=True to bypass queue check
        import requests
        import os
        # Use local URL if running locally, otherwise use Vercel
        base_url = os.environ.get('API_BASE_URL', 'https://dqsheerid.vercel.app')
        api_url = f"{base_url}/start-verification"
        print(f"DEBUG: Using API URL: {api_url}")
        payload = {
            "url": url,
            "job_id": job_id,
            "from_queue": True,  # Bypass queue check - already processed from queue
            "verification_type": verification_type  # Pass verification type for proxy selection
        }
        
        print(f"DEBUG: Calling API {api_url} with payload: {payload}")
        try:
            response = requests.post(api_url, json=payload, timeout=35)
        except requests.exceptions.Timeout:
            print("WARN: Verification API timed out; treating as in-progress and will notify on completion.")
            send_telegram_message(chat_id, "⏳ Verification đang được xử lý... Hệ thống sẽ tự động thông báo khi xong.")
            return
        except requests.exceptions.RequestException as e:
            print(f"WARN: Verification API request error: {e}; treating as in-progress")
            send_telegram_message(chat_id, "⏳ Verification đang được xử lý... Hệ thống sẽ tự động thông báo khi xong.")
            return
        
        print(f"DEBUG: API response status: {response.status_code}")
        body_preview = ''
        try:
            body_preview = response.text[:1000]
        except Exception:
            pass
        print(f"DEBUG: API response: {body_preview}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"🔍 DEBUG: API response result: {result}")
            if result.get('success'):
                print(f"✅ Verification started successfully for job {job_id}")
                print(f"DEBUG: Verification result details: {result}")
                
                # Check if job is pending or completed
                result_status = result.get('status', '').lower()
                print(f"🔍 DEBUG: result_status = '{result_status}'")
                if result_status == 'pending':
                    # Job is pending - send pending message to user
                    print(f"🔍 DEBUG: Sending pending message to chat_id {chat_id}")
                    result_send = send_telegram_message(chat_id, "⏳ Verification đang được xử lý... Vui lòng đợi kết quả!")
                    print(f"🔍 DEBUG: Pending message send result: {result_send}")
                elif result_status == 'pending_background':
                    # Job is in background polling (Teacher verification reviewing)
                    print(f"🔍 DEBUG: Job in background polling, sending notification")
                    result_send = send_telegram_message(chat_id, """🎓 Teacher verification đang được SheerID review!

⏳ Trạng thái: Đang chờ kết quả từ SheerID
📋 Hệ thống sẽ tự động poll và thông báo khi có kết quả

⏱️ Thời gian chờ: 5-30 phút
✅ Khi success: Bạn sẽ nhận thông báo + trừ xu/cash
❌ Khi fail: Bạn sẽ nhận thông báo + không trừ xu/cash

💡 Không cần làm gì thêm, chỉ cần chờ!""")
                    print(f"🔍 DEBUG: Background pending message send result: {result_send}")
                elif result_status == 'failed':
                    # Job failed - send failure message
                    error_msg = result.get('error') or result.get('message') or 'Quá thời gian verify'
                    print(f"🔍 DEBUG: Job failed, sending failure message: {error_msg}")
                    result_send = send_telegram_message(chat_id, f"❌ Verification thất bại: {error_msg}")
                    print(f"🔍 DEBUG: Failure message send result: {result_send}")
                else:
                    # Job is completed - API already handled charging + notification
                    # No need to call start_verification_process again as it would create duplicate API calls
                    print(f"✅ Job {job_id} completed - API already processed charging and notification")
            else:
                # API returned success: False - send failure notification
                error_msg = result.get('error') or result.get('message') or 'Quá thời gian verify'
                reason = result.get('reason', '')
                
                # Check if it's a timeout
                if reason == 'timeout' or 'timeout' in error_msg.lower():
                    error_msg = "Quá thời gian verify"
                
                # Check if it's fraud rejection
                is_fraud = error_msg == 'fraudRulesReject' or 'fraud' in str(error_msg).lower()
                
                print(f"❌ Verification failed: {error_msg} (fraud={is_fraud})")
                
                # Update job status to failed or fraud_reject
                if job_id:
                    try:
                        from supabase_client import update_verification_job_status
                        status = 'fraud_reject' if is_fraud else 'failed'
                        update_verification_job_status(job_id, status)
                        print(f"✅ Updated job {job_id} status to {status}")
                    except Exception as e:
                        print(f"❌ Error updating job status: {e}")
                
                print(f"🔍 DEBUG: Sending failure message to chat_id {chat_id}")
                result_send = send_telegram_message(chat_id, f"❌ Verification thất bại: {error_msg}\n\n💰 Không bị trừ xu/cash\n🔄 Bạn có thể thử lại với link mới")
                print(f"🔍 DEBUG: Send result: {result_send}")
        else:
            # Non-200: treat as still processing; avoid false failure -> we'll notify when done
            print(f"❌ API call failed with status {response.status_code}; treating as in-progress")
            send_telegram_message(chat_id, "⏳ Verification đang được xử lý... Hệ thống sẽ tự động thông báo khi xong.")
            
    except Exception as e:
        print(f"❌ Error in _execute_verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Remove from VIP active tracking when done
        if telegram_id and payment_method == 'free':
            try:
                from .vip_tiers import remove_active_verification
                remove_active_verification(telegram_id, job_id)
            except Exception as e:
                print(f"⚠️ Error removing active verification tracking: {e}")
        
        # Filter technical errors for user-friendly messages
        error_str = str(e)
        if "HTTPSConnectionPool" in error_str or "Read timed out" in error_str:
            send_telegram_message(chat_id, "❌ Verification thất bại do timeout. Vui lòng thử lại sau.")
        elif "Connection" in error_str and "timeout" in error_str:
            send_telegram_message(chat_id, "❌ Kết nối timeout. Vui lòng thử lại sau.")
        else:
            send_telegram_message(chat_id, f"❌ Lỗi trong quá trình verify: {error_str}")

def run_async_task(func, *args, **kwargs):
    """Run function in background thread for non-critical operations"""
    def wrapper():
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"Async task error: {e}")
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()

def batch_database_queries(queries):
    """Execute multiple database queries in batch for better performance"""
    results = []
    if not SUPABASE_AVAILABLE:
        return results
    
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            return results
        
        for query in queries:
            try:
                result = query(supabase)
                results.append(result)
            except Exception as e:
                print(f"Batch query error: {e}")
                results.append(None)
    except Exception as e:
        print(f"Batch database error: {e}")
    
    return results

def create_optimized_session():
    """Create optimized HTTP session with connection pooling"""
    global TELEGRAM_SESSION
    if TELEGRAM_SESSION is None:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        TELEGRAM_SESSION = session
    return TELEGRAM_SESSION

import requests
import uuid
import time
from datetime import datetime, timezone, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading
import logging

def get_vietnam_time():
    """Get current time in Vietnam timezone (UTC+7)"""
    vietnam_tz = timezone(timedelta(hours=7))
    return datetime.now(vietnam_tz)

def format_vietnam_time(format_str='%d/%m/%Y %H:%M:%S'):
    """Format current Vietnam time"""
    return get_vietnam_time().strftime(format_str)

def convert_utc_to_vietnam(utc_timestamp_str, format_str='%d/%m/%Y %H:%M:%S'):
    """Convert UTC timestamp string to Vietnam time"""
    try:
        if not utc_timestamp_str or utc_timestamp_str == 'N/A':
            return 'N/A'
        
        # Parse UTC timestamp
        utc_time = datetime.fromisoformat(str(utc_timestamp_str).replace('Z', '+00:00'))
        
        # Convert to Vietnam timezone (UTC+7)
        vietnam_tz = timezone(timedelta(hours=7))
        vietnam_time = utc_time.astimezone(vietnam_tz)
        
        return vietnam_time.strftime(format_str)
    except Exception as e:
        print(f"Error converting time: {e}")
        return str(utc_timestamp_str)[:19] if utc_timestamp_str else 'N/A'

# Reduce httpx logging to reduce console spam
logging.getLogger("httpx").setLevel(logging.WARNING)
try:
    # Try different import paths
    try:
        from supabase_client import get_user_by_telegram_id as get_user_from_supabase, create_user as create_user_in_supabase, update_user_coins as update_user_coins_in_supabase, add_coins_to_user as add_coins_to_user_in_supabase, get_all_users as get_all_users_from_supabase
        print("✅ Supabase client loaded successfully in telegram.py")
        SUPABASE_AVAILABLE = True
    except ImportError:
        # Try importing from api directory
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        from supabase_client import get_user_by_telegram_id as get_user_from_supabase, create_user as create_user_in_supabase, update_user_coins as update_user_coins_in_supabase, add_coins_to_user as add_coins_to_user_in_supabase, get_all_users as get_all_users_from_supabase
        print("✅ Supabase client loaded successfully in telegram.py (from api directory)")
        SUPABASE_AVAILABLE = True
except ImportError as e:
    print(f"❌ Supabase client not found in telegram.py: {e}")
    print("🔄 Falling back to SQLite")
    SUPABASE_AVAILABLE = False
except Exception as e:
    print(f"❌ Error loading Supabase client in telegram.py: {e}")
    print("🔄 Falling back to SQLite")
    SUPABASE_AVAILABLE = False

print(f"🔍 SUPABASE_AVAILABLE flag: {SUPABASE_AVAILABLE}")
# Fallback functions - use SQLite instead
def get_user_from_supabase(telegram_id, force_reload=False):
    """Get user with optimized caching to reduce DB calls"""
    global USER_CACHE, USER_CACHE_TIME
    import time
    
    current_time = time.time()
    cache_key = str(telegram_id)
    
    # Check cache first with improved logic
    if not force_reload and cache_key in USER_CACHE:
        cache_time = USER_CACHE_TIME.get(cache_key, 0)
        if (current_time - cache_time) < USER_CACHE_DURATION:
            return USER_CACHE[cache_key]
    
    if SUPABASE_AVAILABLE:
        if not force_reload:
            print(f"🔄 Using Supabase: Getting user: {telegram_id}")
        try:
            from supabase_client import get_user_by_telegram_id
            user = get_user_by_telegram_id(telegram_id)
            if user:
                # Cache the result with separate timestamp tracking
                USER_CACHE[cache_key] = user
                USER_CACHE_TIME[cache_key] = current_time
            return user
        except Exception as e:
            print(f"❌ Supabase error: {e}")
            print("🔄 Falling back to SQLite")
    
    print(f"🔄 Fallback: Getting user from SQLite: {telegram_id}")
    # Direct SQLite query to avoid infinite loop
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            user = {
                'id': user_data[0],
                'telegram_id': str(user_data[1]),
                'username': user_data[2],
                'first_name': user_data[3],
                'last_name': user_data[4],
                'coins': user_data[5],
                'is_vip': bool(user_data[6]),
                'vip_expiry': user_data[7],
                'created_at': user_data[8],
                'updated_at': user_data[9]
            }
            # Cache the result
            USER_CACHE[cache_key] = (user, current_time)
            return user
        return None
    except Exception as e:
        print(f"❌ Error in fallback get_user: {e}")
        return None
    
def create_user_in_supabase(telegram_id, username, first_name, last_name):
    if SUPABASE_AVAILABLE:
        print(f"🔄 Using Supabase: Creating user: {telegram_id}")
        try:
            from supabase_client import create_user
            return create_user(telegram_id, username, first_name, last_name)
        except Exception as e:
            print(f"❌ Supabase error: {e}")
            print("🔄 Falling back to SQLite")
    
    print(f"🔄 Fallback: Creating user in SQLite: {telegram_id}")
    # Direct SQLite query to avoid infinite loop
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create tables if not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                coins INTEGER DEFAULT 0,
                is_vip BOOLEAN DEFAULT 0,
                vip_expiry DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(255) UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                sheerid_url TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                student_info TEXT,
                card_filename VARCHAR(255),
                upload_result TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # No welcome bonus - new users start with 0 coins
        welcome_bonus = 0
        
        # Insert user
        cursor.execute('''
            INSERT INTO users (telegram_id, username, first_name, last_name, coins, is_vip, vip_expiry, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (telegram_id, username, first_name, last_name, welcome_bonus, False, None, datetime.now().isoformat(), datetime.now().isoformat()))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        user_data = {
            'id': user_id,
            'telegram_id': str(telegram_id),
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'coins': welcome_bonus,
            'is_vip': False,
            'vip_expiry': None,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        print(f"✅ User created in SQLite: {user_data}")
        return user_data
        
    except Exception as e:
        print(f"❌ Error creating user in SQLite: {e}")
        return None
    
def update_user_coins_in_supabase(telegram_id, coins_change, transaction_type, description):
    if SUPABASE_AVAILABLE:
        print(f"🔄 Using Supabase: Updating coins: {telegram_id}")
        try:
            from supabase_client import update_user_coins
            return update_user_coins(telegram_id, coins_change, transaction_type, description)
        except Exception as e:
            print(f"❌ Supabase error: {e}")
            print("🔄 Falling back to SQLite")
    
    print(f"🔄 Fallback: Updating coins in SQLite: {telegram_id}")
    # Direct SQLite query to avoid infinite loop
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current user
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            conn.close()
            return False
        
        current_coins = user_data[5]
        new_coins = current_coins + coins_change
        
        # Update coins
        cursor.execute('''
            UPDATE users 
            SET coins = ?, updated_at = ?
            WHERE telegram_id = ?
        ''', (new_coins, datetime.now().isoformat(), telegram_id))
        
        # Insert transaction record
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, coins, description, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_data[0], transaction_type, coins_change * 1000, coins_change, description, 'completed', datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Updated coins: {current_coins} -> {new_coins}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating coins: {e}")
        return False

def add_coins_to_user_in_supabase(telegram_id, coins, transaction_info):
    if SUPABASE_AVAILABLE:
        print(f"🔄 Using Supabase: Adding coins: {telegram_id}")
        try:
            from supabase_client import add_coins_to_user
            return add_coins_to_user(telegram_id, coins, transaction_info)
        except Exception as e:
            print(f"❌ Supabase error: {e}")
            print("🔄 Falling back to SQLite")
    
    print(f"🔄 Fallback: Adding coins in SQLite: {telegram_id}")
    return update_user_coins_in_supabase(telegram_id, coins, 'deposit', transaction_info)

def get_all_users_from_supabase():
    if SUPABASE_AVAILABLE:
        print("🔄 Using Supabase: Getting all users")
        try:
            from supabase_client import get_all_users
            return get_all_users()
        except Exception as e:
            print(f"❌ Supabase error: {e}")
            print("🔄 Falling back to SQLite")
    
    print("🔄 Fallback: Getting all users from SQLite")
    # Direct SQLite query to avoid infinite loop
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, telegram_id, username, first_name, last_name, coins, is_vip, vip_expiry, created_at
            FROM users 
            ORDER BY created_at DESC
        ''')
        
        users = cursor.fetchall()
        conn.close()
        
        users_list = []
        for user in users:
            users_list.append({
                'id': user[0],
                'telegram_id': str(user[1]),
                'username': user[2],
                'first_name': user[3],
                'last_name': user[4],
                'coins': user[5],
                'is_vip': user[6],
                'vip_expiry': user[7],
                'created_at': user[8]
            })
        
        return users_list
        
    except Exception as e:
        print(f"❌ Error getting all users: {e}")
        return []

app = Flask(__name__)


# Database path
DB_PATH = "/tmp/sheerid_bot.db"

# Admin configuration
ADMIN_TELEGRAM_IDS = [7162256181]  # Thêm ID của admin vào đây
# Tạm thời thêm @meepzizhere - cần lấy ID chính xác sau khi user gửi tin nhắn

# Bot configuration
BOT_CONFIG = {
    'welcome_message': 'Chào mừng bạn đến với SheerID VIP Bot! 🎉\n\nSử dụng /me để xem thông tin tài khoản\nSử dụng /verify để bắt đầu xác minh\nSử dụng /checkin để nhận xu hàng ngày',
    'verify_price': 3,  # Xu cần trả để verify
    'daily_bonus': 1,   # Xu checkin hàng ngày
    'maintenance_mode': False,  # TẮT CHẾ ĐỘ BẢO TRÌ
    'verify_maintenance': False,  # TẮT BẢO TRÌ VERIFY (/verify) - Student hoạt động
    'vc_maintenance': True,  # TẮT BẢO TRÌ /VC (ChatGPT Teacher) - Teacher hoạt động
    'maintenance_message': (
        "🔧 Bot đang trong chế độ bảo trì\n\n"
        "📝 Lý do: Cập nhật Doc\n"
        "⏰ Thời gian bảo trì dự kiến: 30 phút\n"
        "📢 Sẽ thông báo khi hoàn tất bảo trì tại kênh thông báo: https://t.me/channel_sheerid_vip_bot!\n\n"
        "Cảm ơn bạn đã kiên nhẫn chờ đợi! 🙏"
    ),
    'last_updated': '09/10/2025 12:30:00',
    # Base prices (admin-set; default 0 until set)
    'google_trial_price': 4,
    'google_verified_price': 6,
    'canva_price': 299,
    'ai_ultra_price': 20,
    'chatgpt_price': 60,
    'spotify_price': 0,
    # VIP prices (optional)
    'google_trial_price_vip': 4,
    'google_verified_price_vip': 5,
    'canva_price_vip': 279,
    'ai_ultra_price_vip': 23,
    'chatgpt_price_vip': 55,
    'spotify_price_vip': 0,
    # VIP packages (admin-set)
    'vip1_price': 30,
    'vip7_price': 150,
    'vip30_price': 300
}

# Cache for bot config to avoid repeated DB calls
CONFIG_LOADED = False
CONFIG_LAST_LOADED = 0
CONFIG_CACHE_DURATION = 30  # seconds

# User cache to avoid repeated DB calls
USER_CACHE = {}
USER_CACHE_DURATION = 10  # seconds

# Create a session with connection pooling for better performance
def create_optimized_session():
    """Create a requests session with connection pooling and retry strategy"""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    # Mount adapter with retry strategy
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20
    )
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

# Global session for reuse
TELEGRAM_SESSION = create_optimized_session()

def run_async_task(func, *args, **kwargs):
    """Run a function asynchronously in background thread"""
    def wrapper():
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"Error in async task: {e}")
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()

def load_bot_config(force_reload=False):
    """Load bot configuration from database with caching"""
    global BOT_CONFIG, CONFIG_LOADED, CONFIG_LAST_LOADED
    import time
    
    current_time = time.time()
    
    # Use cache if loaded recently and not forcing reload
    if CONFIG_LOADED and not force_reload and (current_time - CONFIG_LAST_LOADED) < CONFIG_CACHE_DURATION:
        return
    
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            config_resp = supabase.table('bot_config').select('*').execute()
            if config_resp.data:
                for item in config_resp.data:
                    key = item.get('config_key')
                    value = item.get('config_value')
                    
                    # Allow DB to control maintenance modes
                    if key == 'maintenance_mode':
                        bool_value = str(value).lower() == 'true'
                        BOT_CONFIG['maintenance_mode'] = bool_value
                        print(f"🔧 DB maintenance_mode = {bool_value}")
                        continue
                    
                    if key == 'verify_maintenance':
                        bool_value = str(value).lower() == 'true'
                        BOT_CONFIG['verify_maintenance'] = bool_value
                        print(f"🔧 DB verify_maintenance = {bool_value}")
                        continue
                    
                    if key == 'vc_maintenance':
                        bool_value = str(value).lower() == 'true'
                        BOT_CONFIG['vc_maintenance'] = bool_value
                        print(f"🔧 DB vc_maintenance = {bool_value}")
                        continue
                    
                    # Load maintenance_message from DB
                    if key == 'maintenance_message' and value:
                        BOT_CONFIG['maintenance_message'] = value
                        print(f"🔧 DB maintenance_message loaded")
                        continue
                    
                    # Accept all other keys from DB
                    BOT_CONFIG[key] = value
                CONFIG_LOADED = True
                CONFIG_LAST_LOADED = current_time
    except Exception as e:
        print(f"Error loading bot config: {e}")

def save_bot_config(key, value):
    """Save bot configuration to database"""
    global CONFIG_LOADED, CONFIG_LAST_LOADED
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if supabase:
            # Try to update first
            update_resp = supabase.table('bot_config').update({'config_value': value}).eq('config_key', key).execute()
            if not update_resp.data:
                # If no rows updated, insert new
                supabase.table('bot_config').insert({'config_key': key, 'config_value': value}).execute()
    except Exception as e:
        print(f"Error saving bot config: {e}")
    finally:
        # Always update in-memory cache so features reflect immediately
        BOT_CONFIG[key] = value
        # Invalidate cache to force reload on next request
        CONFIG_LOADED = False

# EMERGENCY STOP FLAG - DỪNG TẤT CẢ HOẠT ĐỘNG NGAY LẬP TỨC
EMERGENCY_STOP = False  # TẮT KHẨN CẤP - BOT HOẠT ĐỘNG BÌNH THƯỜNG
BROADCAST_IN_PROGRESS = False  # Chặn re-entrant broadcast/noti loops
GIFT_IN_PROGRESS = False  # Chặn re-entrant gift commands

def handle_admin_emergency(chat_id, mode):
    """Toggle emergency stop immediately; breaks ongoing broadcasts."""
    try:
        global EMERGENCY_STOP, BROADCAST_IN_PROGRESS
        if mode.lower() in ('on', 'true', '1'):  # enable stop
            EMERGENCY_STOP = True
            BROADCAST_IN_PROGRESS = False
            try:
                save_bot_config('emergency_stop', '1')
            except Exception:
                pass
            send_telegram_message(chat_id, "🚨 ĐÃ BẬT chế độ dừng khẩn cấp! Tất cả gửi tin sẽ dừng ngay.")
        elif mode.lower() in ('off', 'false', '0'):
            EMERGENCY_STOP = False
            try:
                save_bot_config('emergency_stop', '0')
            except Exception:
                pass
            send_telegram_message(chat_id, "✅ ĐÃ TẮT chế độ dừng khẩn cấp. Có thể gửi lại.")
        else:
            send_telegram_message(chat_id, "❌ Sử dụng: /admin emergency on|off")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi emergency: {str(e)}")

def is_admin(telegram_id):
    """Check if user is admin"""
    return telegram_id in ADMIN_TELEGRAM_IDS

def save_config():
    """Save bot configuration to file"""
    try:
        config_file = "/tmp/bot_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(BOT_CONFIG, f, ensure_ascii=False, indent=2)
        print(f"✅ Bot config saved to {config_file}")
    except Exception as e:
        print(f"❌ Error saving config: {e}")

def load_config():
    """Load bot configuration from file"""
    global BOT_CONFIG
    try:
        config_file = "/tmp/bot_config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                BOT_CONFIG = json.load(f)
            print(f"✅ Bot config loaded from {config_file}")
    except Exception as e:
        print(f"❌ Error loading config: {e}")

def is_maintenance_mode():
    """Check if bot is in maintenance mode"""
    try:
        # Check maintenance status from config
        verify_maintenance = BOT_CONFIG.get('verify_maintenance', False)
        maintenance_mode = BOT_CONFIG.get('maintenance_mode', False)
        env_maintenance = os.environ.get('VERIFY_MAINTENANCE', 'false').lower() == 'true'
        
        is_maintenance = verify_maintenance or maintenance_mode or env_maintenance
        
        if is_maintenance:
            print("🔧 MAINTENANCE MODE ACTIVE")
        else:
            print("✅ Maintenance mode: DISABLED")
        
        return is_maintenance
    except Exception as e:
        print(f"❌ Error in is_maintenance_mode: {e}")
        return False

def is_bot_closed():
    """Global shutdown: block all non-admin interactions when enabled - FORCE DISABLED"""
    try:
        # 🚨 EMERGENCY: Force disable bot shutdown completely
        BOT_CONFIG['bot_closed'] = False
        
        # Clear environment variables
        if 'BOT_CLOSED' in os.environ:
            del os.environ['BOT_CLOSED']
        if 'BOT_CLOSED_MESSAGE' in os.environ:
            del os.environ['BOT_CLOSED_MESSAGE']
        
        # Always return False - bot shutdown is disabled
        print(f"🔍 DEBUG is_bot_closed: FORCE DISABLED - returning False")
        return False
    except Exception as e:
        print(f"🔍 DEBUG is_bot_closed: error={e}")
        return False

def get_bot_closed_message():
    """Message to show users when bot is globally closed."""
    try:
        return os.environ.get('BOT_CLOSED_MESSAGE') or BOT_CONFIG.get('bot_closed_message') or (
            "🚫 Bot hiện đang tạm dừng hoạt động. Vui lòng quay lại sau.\n\n"
            "💬 Mọi thắc mắc vui lòng liên hệ admin: @meepzizhere"
        )
    except Exception:
        return "🚫 Bot hiện đang tạm dừng hoạt động. Vui lòng quay lại sau."

def is_vip_active(user):
    """Check if user has active VIP status (not expired).
    Supports both tuple-form users (legacy) and dict-form users (Supabase)."""
    if not user:
        return False

    # Normalize fields
    if isinstance(user, dict):
        is_vip = bool(user.get('is_vip', False))
        vip_expiry = user.get('vip_expiry')
    else:
        # tuple format indices: [6] is_vip, [7] vip_expiry
        is_vip = bool(user[6]) if len(user) > 6 else False
        vip_expiry = user[7] if len(user) > 7 else None

    if not is_vip:
        return False

    if not vip_expiry:
        # No expiry → treat as active
        return True

    # Compare against Vietnam timezone now
    from datetime import datetime, timezone, timedelta
    try:
        expiry_date_utc = datetime.fromisoformat(str(vip_expiry).replace('Z', '+00:00'))
        vietnam_tz = timezone(timedelta(hours=7))
        current_vietnam_time = datetime.now(vietnam_tz)
        expiry_date_vietnam = expiry_date_utc.astimezone(vietnam_tz)
        return current_vietnam_time < expiry_date_vietnam
    except Exception:
        # If parsing fails, treat as expired for safety
        return False

def validate_sheerid_url(url):
    """Validate if URL is a valid SheerID verification URL"""
    import re
    
    print(f"DEBUG: Validating URL: {url}")
    
    # Check if URL starts with http/https
    if not url.startswith(('http://', 'https://')):
        print("DEBUG: URL does not start with http/https")
        return False
    
    # Check if URL contains sheerid.com domain
    if 'sheerid.com' not in url:
        print("DEBUG: URL does not contain sheerid.com")
        return False
    
    # Check if URL contains /verify/ path OR is a SheerID URL without /verify/
    if '/verify/' not in url and 'services.sheerid.com' not in url:
        print("DEBUG: URL does not contain /verify/ or is not SheerID")
        return False
    
    # Check if URL has proper format: https://services.sheerid.com/verify/... OR https://services.sheerid.com/... (allow query parameters)
    pattern1 = r'^https?://(?:www\.)?services\.sheerid\.com/verify/[a-zA-Z0-9_-]+(?:/.*)?(?:\?.*)?$'
    pattern2 = r'^https?://(?:www\.)?services\.sheerid\.com/[a-zA-Z0-9_-]+(?:/.*)?(?:\?.*)?$'
    result1 = bool(re.match(pattern1, url))
    result2 = bool(re.match(pattern2, url))
    result = result1 or result2
    print(f"DEBUG: Pattern1 match result: {result1}")
    print(f"DEBUG: Pattern2 match result: {result2}")
    print(f"DEBUG: Final result: {result}")
    return result

def validate_sheerid_verification_exists(url):
    """
    Validate if SheerID verification exists by calling SheerID API
    Returns: (is_valid, error_message, verification_data)
    """
    import re
    import requests
    from urllib.parse import urlparse, parse_qs
    
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
            return False, "verificationId không hợp lệ (phải là 24 ký tự hex)", None
        
        # Extract program ID from URL path if available
        program_id = None
        if '/verify/' in url:
            # URL format: https://services.sheerid.com/verify/{programId}/?verificationId=...
            parts = url.split('/verify/')
            if len(parts) > 1:
                program_id = parts[1].split('/')[0].split('?')[0]
                print(f"📋 Extracted program ID: {program_id}")
        
        # Call SheerID API to check if verification exists
        # Try services.sheerid.com first, then my.sheerid.com as fallback
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Origin': 'https://services.sheerid.com',
            'Referer': url,  # Add referer to help with CORS
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Try multiple API endpoints - some verifications only work with specific endpoints
        api_urls = [
            f"https://services.sheerid.com/rest/v2/verification/{verification_id}",
            f"https://my.sheerid.com/rest/v2/verification/{verification_id}",
        ]
        
        # If we have program ID, also try program-specific endpoint
        if program_id:
            api_urls.insert(0, f"https://services.sheerid.com/rest/v2/program/{program_id}/verification/{verification_id}")
        
        response = None
        data = None
        for api_url in api_urls:
            try:
                response = requests.get(api_url, headers=headers, timeout=10)
                data = response.json()
                print(f"🔍 SheerID API response for {verification_id}: status={response.status_code} (from {api_url.split('/rest')[0]})")
                if response.status_code == 200:
                    break  # Found valid response
            except Exception as e:
                print(f"⚠️ API call failed for {api_url}: {e}")
                continue
        
        if response is None or data is None:
            print(f"⚠️ All SheerID API endpoints failed - allowing verification to proceed")
            return True, None, None
        
        if response.status_code == 200:
            current_step = data.get('currentStep', '')
            error_ids = data.get('errorIds', [])
            
            # Check for noVerification error
            if 'noVerification' in error_ids or current_step == 'error':
                error_msg = data.get('systemErrorMessage', 'Verification không tồn tại')
                print(f"❌ Verification not found: {error_msg}")
                return False, f"❌ Verification không tồn tại!\n\nID: {verification_id}\nLỗi: {error_msg}", None
            
            # Check if already completed (success)
            if current_step == 'success':
                print(f"✅ Verification {verification_id} already completed (success)")
                return True, None, data
            
            # Valid verification in progress
            print(f"✅ Verification {verification_id} exists, step: {current_step}")
            return True, None, data
            
        elif response.status_code == 404:
            error_msg = data.get('systemErrorMessage', 'Verification không tồn tại') if data else 'Not found'
            print(f"⚠️ Verification API returned 404: {error_msg}")
            
            # Some SheerID programs don't allow external API queries
            # ChatGPT Teacher (68d47554aa292d20b9bec8f7) is one of them
            # Don't block - allow verification to proceed
            known_restricted_programs = [
                '68d47554aa292d20b9bec8f7',  # ChatGPT Teacher K12
                '5e1e3c3c3c3c3c3c3c3c3c3c',  # Example
            ]
            
            if program_id and program_id in known_restricted_programs:
                print(f"✅ Program {program_id} is known to restrict API access - allowing verification")
                return True, None, None
            
            # For other programs, still allow but log warning
            # Many new verifications return 404 initially
            print(f"⚠️ 404 but allowing verification to proceed (may be new or restricted)")
            return True, None, None
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

def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables if not exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(255),
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            coins INTEGER DEFAULT 0,
            is_vip BOOLEAN DEFAULT FALSE,
            vip_expiry DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verification_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id VARCHAR(255) UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            sheerid_url TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            student_info TEXT,
            card_filename VARCHAR(255),
            upload_result TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type VARCHAR(50) NOT NULL,
            amount INTEGER NOT NULL,
            coins INTEGER DEFAULT 0,
            description TEXT,
            status VARCHAR(50) DEFAULT 'pending',
            job_id VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_settings (
            key VARCHAR(255) PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create referrals table (fallback for SQLite)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL,
            referral_code VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            reward_given BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            FOREIGN KEY (referrer_id) REFERENCES users(id),
            FOREIGN KEY (referred_id) REFERENCES users(id),
            UNIQUE(referred_id)
        )
    ''')
    
    # Insert default settings if not exist
    cursor.execute('SELECT COUNT(*) FROM bot_settings')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO bot_settings (key, value) VALUES (?, ?)', ('verify_cost', '10'))
        cursor.execute('INSERT INTO bot_settings (key, value) VALUES (?, ?)', ('vip_verify_cost', '3'))
        cursor.execute('INSERT INTO bot_settings (key, value) VALUES (?, ?)', ('welcome_bonus', '2'))
        cursor.execute('INSERT INTO bot_settings (key, value) VALUES (?, ?)', ('vip_price', '250'))
    
    # Update existing welcome_bonus to 2
    cursor.execute('UPDATE bot_settings SET value = ? WHERE key = ?', ('2', 'welcome_bonus'))
    
    # Add vip_expiry column if not exists (migration)
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN vip_expiry DATETIME')
        print("Added vip_expiry column to users table")
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    conn.commit()
    conn.close()

def get_user(telegram_id):
    """Get user by telegram_id from Supabase first, then SQLite fallback"""
    try:
        # Try Supabase first
        if SUPABASE_AVAILABLE:
            print(f"🔄 Using Supabase: Getting user: {telegram_id}")
            try:
                from supabase_client import get_user_by_telegram_id
                user = get_user_by_telegram_id(str(telegram_id))
                if user:
                    print(f"✅ Found user in Supabase: {user}")
                    return user
                else:
                    print(f"❌ User {telegram_id} not found in Supabase")
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                print("🔄 Falling back to SQLite")
        
        # Fallback to SQLite
        print(f"🔄 Fallback: Getting user from SQLite: {telegram_id}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create tables if not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                coins INTEGER DEFAULT 0,
                is_vip BOOLEAN DEFAULT 0,
                vip_expiry DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id VARCHAR(255) UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                sheerid_url TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                student_info TEXT,
                card_filename VARCHAR(255),
                upload_result TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            user = {
                'id': user_data[0],
                'telegram_id': str(user_data[1]),
                'username': user_data[2],
                'first_name': user_data[3],
                'last_name': user_data[4],
                'coins': user_data[5],
                'is_vip': bool(user_data[6]),
                'vip_expiry': user_data[7],
                'created_at': user_data[8],
                'updated_at': user_data[9]
            }
            
            # Sync user data to file for SePay webhook compatibility
            try:
                user_file = f"/tmp/user_{telegram_id}.json"
                with open(user_file, 'w', encoding='utf-8') as f:
                    json.dump(user, f, ensure_ascii=False, indent=2)
                print(f"✅ User data synced to file: {user_file} - {user['coins']} xu")
            except Exception as e:
                print(f"⚠️ Warning: Could not sync user data to file: {e}")
            
            print(f"✅ Found user in SQLite: {user}")
            return user
        else:
            print(f"❌ User {telegram_id} not found in SQLite")
            return None

    except Exception as e:
        print(f"❌ Error getting user: {e}")
        return None

def create_user(telegram_id, username, first_name, last_name):
    """Create new user in Supabase"""
    try:
        # Check if user already exists first (with cache)
        existing_user = get_user_from_supabase(telegram_id)
        if existing_user:
            print(f"✅ User {telegram_id} already exists in Supabase, returning existing user")
            return existing_user
        
        # Create user in Supabase
        user_data = create_user_in_supabase(telegram_id, username, first_name, last_name)
        
        if user_data:
            # Add checkin transaction for today to prevent double checkin
            today = format_vietnam_time('%Y-%m-%d')
            update_user_coins_in_supabase(telegram_id, 0, 'checkin', f'Checkin ngày {today} (tài khoản mới)')
            
            # Save user data to file for SePay webhook compatibility
            try:
                user_file = f"/tmp/user_{telegram_id}.json"
                with open(user_file, 'w', encoding='utf-8') as f:
                    json.dump(user_data, f, ensure_ascii=False, indent=2)
                print(f"✅ User data saved to file for SePay sync: {user_file}")
            except Exception as e:
                print(f"⚠️ Warning: Could not save user data to file: {e}")
            
            if SUPABASE_AVAILABLE:
                print(f"✅ Created user in Supabase: {telegram_id}")
            else:
                print(f"✅ Created user in SQLite (fallback): {telegram_id}")
                print(f"⚠️ Supabase not available, using SQLite fallback")
            
            # Send notification to admin about new user
            try:
                admin_notification = f"""🆕 USER MỚI ĐĂNG KÝ

👤 Thông tin user:
🆔 ID: {telegram_id}
👤 Tên: {first_name} {last_name if last_name and last_name != '' else ''}
📱 Username: @{username if username else 'N/A'}
💰 Xu khởi đầu: 5 xu
⏰ Thời gian: {format_vietnam_time()} (VN)

🎉 Chào mừng user mới!

---
SheerID VIP Bot"""
                
                # Send to admin (only if not emergency stop)
                if not EMERGENCY_STOP:
                    admin_ids = [7162256181]  # Admin ID
                    for admin_id in admin_ids:
                        send_telegram_message(admin_id, admin_notification)
                        print(f"✅ Sent new user notification to admin {admin_id}")
                else:
                    print("🚨 EMERGENCY STOP: Skipping admin notification")
            except Exception as e:
                print(f"❌ Failed to send new user notification: {e}")
            
            return user_data
        else:
            if SUPABASE_AVAILABLE:
                print(f"❌ Failed to create user in Supabase: {telegram_id}")
            else:
                print(f"❌ Failed to create user in SQLite (fallback): {telegram_id}")
            return None

    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return None
def create_user_from_telegram_data(telegram_id, username, first_name, last_name):
    """Create user from Telegram data using file-based storage"""
    try:
        print(f"👤 Creating new user from Telegram data: {telegram_id}")
        
        # File path for user data
        user_file = f'/tmp/user_{telegram_id}.json'
        
        # Create new user with Telegram data
        user_data = {
            'id': 1,
            'telegram_id': telegram_id,
            'username': username or 'user',
            'first_name': first_name or 'User',
            'last_name': last_name or '',
            'coins': 4,  # Welcome bonus - 4 xu for new users
            'is_vip': 0,
            'vip_expiry': None,
            'created_at': datetime.now().isoformat()
        }
        
        # Save user data
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ User created: {user_data}")
        
        # Send notification to admin about new user
        try:
            admin_notification = f"""🆕 USER MỚI ĐĂNG KÝ (FALLBACK)

👤 Thông tin user:
🆔 ID: {telegram_id}
👤 Tên: {first_name} {last_name if last_name and last_name != '' else ''}
📱 Username: @{username if username else 'N/A'}
💰 Xu khởi đầu: 5 xu
⏰ Thời gian: {format_vietnam_time()} (VN)

🎉 Chào mừng user mới!

---
SheerID VIP Bot"""
            
            # Send to admin (only if not emergency stop)
            if not EMERGENCY_STOP:
                admin_ids = [7162256181]  # Admin ID
                for admin_id in admin_ids:
                    send_telegram_message(admin_id, admin_notification)
                    print(f"✅ Sent new user notification to admin {admin_id}")
            else:
                print("🚨 EMERGENCY STOP: Skipping admin notification")
        except Exception as e:
            print(f"❌ Failed to send new user notification: {e}")
        
        return (
            user_data.get('id', 1),
            user_data.get('telegram_id', telegram_id),
            user_data.get('username', 'user'),
            user_data.get('first_name', 'User'),
            user_data.get('last_name', ''),
            user_data.get('coins', 5),
            user_data.get('is_vip', 0),
            user_data.get('vip_expiry'),
            user_data.get('created_at', '2025-09-21T00:00:00')
        )
        
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        import traceback
        traceback.print_exc()
        return None

def update_user_coins(user_id, amount, transaction_type, description, job_id=None):
    """Update user coins and add transaction"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Update coins
    cursor.execute('UPDATE users SET coins = coins + ? WHERE id = ?', (amount, user_id))
    
    # Add transaction
    cursor.execute('''
        INSERT INTO transactions (user_id, type, amount, description, job_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, transaction_type, amount, description, job_id))
    
    conn.commit()
    conn.close()

def create_verification_job(user_id, sheerid_url, verification_type='sheerid', payment_method=None):
    """Create new verification job with type support (sheerid or chatgpt) and payment method tracking"""
    job_id = str(uuid.uuid4())
    print(f"DEBUG: Creating verification job - user_id: {user_id}, job_id: {job_id}, type: {verification_type}, payment: {payment_method}")
    
    # Try Supabase first
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from supabase_client import create_verification_job as create_job_supabase, get_user_by_telegram_id
        
        # Store payment_method for later use
        _payment_method = payment_method
        
        # Get user info to get telegram_id
        user = get_user_by_telegram_id(user_id) if isinstance(user_id, str) else None
        if not user:
            # Try to get user by ID
            try:
                from supabase_client import get_supabase_client
                client = get_supabase_client()
                if client:
                    result = client.table('users').select('*').eq('id', user_id).execute()
                    if result.data:
                        user = result.data[0]
            except:
                pass
        
        if user:
            telegram_id = user.get('telegram_id')
            # Extract verification_id from URL
            verification_id = None
            if 'verificationId=' in sheerid_url:
                verification_id = sheerid_url.split('verificationId=')[-1].split('&')[0]
            
            # Create job in Supabase with verification_type and payment_method
            print(f"DEBUG: Calling create_job_supabase with telegram_id: {telegram_id}, type: {verification_type}, payment: {_payment_method}")
            success = create_job_supabase(job_id, user_id, telegram_id, sheerid_url, verification_id, verification_type, _payment_method)
            if success:
                print(f"✅ Created verification job in Supabase: {job_id} (type: {verification_type})")
                return job_id
            else:
                print(f"❌ Failed to create job in Supabase: {job_id}")
        
        print("❌ Supabase failed, falling back to SQLite")
        
    except ImportError:
        print("❌ Supabase client not available, using SQLite")
    except Exception as e:
        print(f"❌ Supabase error: {e}, falling back to SQLite")
    
    # Fallback to SQLite
    print(f"DEBUG: Fallback to SQLite for job: {job_id}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Add verification_type column if not exists
        try:
            cursor.execute('ALTER TABLE verification_jobs ADD COLUMN verification_type VARCHAR(50) DEFAULT "sheerid"')
        except:
            pass  # Column already exists
        
        # Add payment_method column if not exists
        try:
            cursor.execute('ALTER TABLE verification_jobs ADD COLUMN payment_method VARCHAR(10) DEFAULT NULL')
        except:
            pass  # Column already exists
        
        cursor.execute('''
            INSERT INTO verification_jobs (job_id, user_id, sheerid_url, status, verification_type, payment_method)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (job_id, user_id, sheerid_url, 'pending', verification_type, payment_method))
        
        conn.commit()
        conn.close()
        print(f"✅ Created verification job in SQLite: {job_id} (type: {verification_type}, payment: {payment_method})")
        return job_id
    except Exception as e:
        print(f"❌ Failed to create job in SQLite: {e}")
        return None

def update_verification_job(job_id, status, student_info=None, card_filename=None, upload_result=None):
    """Update verification job status"""
    print(f"🔄 DEBUG: Updating job {job_id} to status: {status}")
    
    # Try Supabase first
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from supabase_client import update_verification_job_status as update_job_supabase
        
        print(f"🔄 DEBUG: Calling Supabase update for job {job_id}")
        success = update_job_supabase(job_id, status, student_info, card_filename, upload_result)
        if success:
            print(f"✅ Updated verification job in Supabase: {job_id} to {status}")
            return
        else:
            print(f"❌ Supabase update returned False for job {job_id}")
        
        print("❌ Supabase failed, falling back to SQLite")
        
    except ImportError:
        print("❌ Supabase client not available, using SQLite")
    except Exception as e:
        print(f"❌ Supabase error: {e}, falling back to SQLite")
    
    # Fallback to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    update_fields = ['status = ?']
    params = [status]
    
    if student_info:
        update_fields.append('student_info = ?')
        params.append(json.dumps(student_info))
    
    if card_filename:
        update_fields.append('card_filename = ?')
        params.append(card_filename)
    
    if upload_result:
        update_fields.append('upload_result = ?')
        params.append(json.dumps(upload_result))
    
    if status in ['completed', 'failed']:
        update_fields.append('completed_at = ?')
        params.append(datetime.now().isoformat())
    
    params.append(job_id)
    
    query = f'''
        UPDATE verification_jobs 
        SET {', '.join(update_fields)}
        WHERE job_id = ?
    '''
    
    print(f"🔄 DEBUG: SQLite query: {query}")
    print(f"🔄 DEBUG: SQLite params: {params}")
    
    cursor.execute(query, params)
    
    rows_affected = cursor.rowcount
    print(f"🔄 DEBUG: SQLite rows affected: {rows_affected}")
    
    conn.commit()
    conn.close()
    
    if rows_affected > 0:
        print(f"✅ Updated verification job in SQLite: {job_id} to {status}")
    else:
        print(f"❌ No rows updated in SQLite for job {job_id}")

@app.route('/telegram/webhook/job-completed', methods=['POST'])
def webhook_job_completed():
    """Webhook to handle completed verification jobs"""
    try:
        payload = request.get_json(silent=True) or {}
        job_id = payload.get('job_id')
        job_data = payload.get('job_data')
        verification_result = payload.get('verification_result')
        
        if not job_id or not job_data:
            return jsonify({"error": "Missing job_id or job_data"}), 400
        
        print(f"🔄 Webhook received for completed job: {job_id}")
        print(f"🔍 DEBUG: job_data = {job_data}")
        print(f"🔍 DEBUG: verification_result = {verification_result}")
        
        print(f"📋 Job {job_id} completed")
        
        # Call process_completed_verification to handle payment and notification
        print(f"🔄 Calling process_completed_verification...")
        process_completed_verification(job_id, job_data, verification_result)
        print(f"✅ process_completed_verification completed")
        
        return jsonify({"success": True, "message": "Payment and notification processed"})
        
    except Exception as e:
        print(f"❌ Error in webhook_job_completed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def handle_admin_checkip(chat_id):
    """Admin: Check current WWProxy IP status"""
    try:
        # Import directly from api.index module
        from api.index import get_ip_status
        
        status = get_ip_status()
        
        if not status['ip']:
            message = "🌐 **IP Status**\n\n"
            message += "❌ Chưa có IP nào được cache\n"
            message += "💡 IP sẽ được fetch khi có request verify tiếp theo"
        else:
            age_min = status['age_minutes']
            age_sec = status['age_seconds'] % 60
            remaining_min = status['remaining_seconds'] // 60
            remaining_sec = status['remaining_seconds'] % 60
            
            message = "🌐 **WWProxy IP Status**\n\n"
            message += f"📍 **IP hiện tại:** `{status['ip']}`\n"
            message += f"⏱️ **Thời gian sống:** {age_min}m {age_sec}s\n"
            message += f"⏳ **Còn lại:** {remaining_min}m {remaining_sec}s\n"
            message += f"📊 **Trạng thái:** {status['status']}\n\n"
            
            if status['remaining_seconds'] > 0:
                message += f"✅ IP đang hoạt động bình thường\n"
                message += f"🔄 Sẽ tự động đổi IP sau {remaining_min}m {remaining_sec}s"
            else:
                message += f"⚠️ IP đã hết hạn cache\n"
                message += f"🔄 Sẽ fetch IP mới ở request tiếp theo"
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"❌ Error checking IP: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi kiểm tra IP: {str(e)}")

def handle_admin_rotateip(chat_id):
    """Admin: Force rotate IP immediately"""
    try:
        # Import directly from api.index module
        from api.index import force_rotate_ip
        
        result = force_rotate_ip()
        
        message = "🔄 **Force Rotate IP**\n\n"
        
        if result['old_ip']:
            message += f"🗑️ **IP cũ:** `{result['old_ip']}`\n"
        else:
            message += f"ℹ️ Không có IP cũ trong cache\n"
        
        message += f"\n✅ {result['message']}\n"
        message += f"🔄 IP mới sẽ được fetch ở request verify tiếp theo"
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"❌ Error rotating IP: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi rotate IP: {str(e)}")

@app.route('/telegram/test', methods=['GET'])
def test_telegram():
    """Test endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Telegram bot is working',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    """Handle Telegram webhook"""
    try:
        # Maintenance gate for non-admin users (except /start command)
        try:
            data_peek = request.get_json(silent=True) or {}
            chat_id_peek = None
            user_id_peek = None
            text_peek = None
            if 'message' in data_peek:
                chat_id_peek = data_peek['message']['chat']['id']
                user_id_peek = data_peek['message']['from']['id']
                text_peek = data_peek['message'].get('text', '')
            elif 'callback_query' in data_peek:
                chat_id_peek = data_peek['callback_query']['message']['chat']['id']
                user_id_peek = data_peek['callback_query']['from']['id']
                text_peek = data_peek['callback_query'].get('data', '')
            
            # Allow /start command even during maintenance
            is_start_command = text_peek and text_peek.strip().lower() == '/start'
            
            if False:  # 🚨 NUCLEAR: Disabled maintenance check
                msg = BOT_CONFIG.get('maintenance_message') or "Máy chủ đang bảo trì. Vui lòng thử lại sau."
                if chat_id_peek:
                    try:
                        send_telegram_message(chat_id_peek, msg)
                    except Exception:
                        pass
                return jsonify({'ok': True})
        except Exception:
            pass

        # Load bot configuration from database (with caching) - only if not recently loaded
        load_bot_config()
        
        # Debug: In tất cả headers (only in development) - disabled to reduce logs
        # if os.environ.get('ENVIRONMENT') != 'production':
        #     print("=== DEBUG: Received Headers ===")
        #     for header, value in request.headers:
        #         print(f"{header}: {value}")
        #     print("=== END DEBUG ===")
        
        # Kiểm tra Vercel Automation Bypass Secret
        bypass_secret = os.environ.get('VERCEL_AUTOMATION_BYPASS_SECRET')
        if bypass_secret:
            # Nếu có automation bypass secret, kiểm tra nó
            received_bypass = request.headers.get('x-vercel-protection-bypass')
            print(f"Expected bypass secret: {bypass_secret}")
            print(f"Received bypass: {received_bypass}")
            
            if received_bypass != bypass_secret:
                print("Unauthorized: Invalid automation bypass secret")
                return jsonify({'status': 'Unauthorized'}), 401
            else:
                print("✅ Automation bypass secret valid!")
        else:
            print("No VERCEL_AUTOMATION_BYPASS_SECRET found, skipping bypass check")
            # Fallback: Kiểm tra secret token
            secret_token = os.environ.get('TELEGRAM_SECRET_TOKEN')
            received_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
            
            print(f"Expected token: {secret_token}")
            print(f"Received token: {received_token}")
            
            if received_token != secret_token:
                print("Unauthorized: Invalid secret token")
                return jsonify({'status': 'Unauthorized'}), 401
        
        data = request.get_json()
        # print(f"Received webhook data: {data}")  # Disabled to reduce logs
        
        # Handle callback queries (inline keyboard buttons)
        if 'callback_query' in data:
            callback_query = data['callback_query']
            chat_id = callback_query['message']['chat']['id']
            telegram_id = callback_query['from']['id']
            callback_data = callback_query['data']

            # Global shutdown: block all non-admins for any callback
            if is_bot_closed() and not is_admin(telegram_id):
                send_telegram_message(chat_id, get_bot_closed_message())
                return jsonify({'ok': True})
            
            # Ban check: block all callbacks for banned users (except admins)
            if not is_admin(telegram_id):
                try:
                    from .supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    if supabase:
                        resp = supabase.table('users').select('is_blocked').eq('telegram_id', str(telegram_id)).limit(1).execute()
                        if resp.data and resp.data[0].get('is_blocked'):
                            print(f"🚫 BLOCKED USER {telegram_id} tried to use callback: {callback_data}")
                            send_telegram_message(chat_id, "🚫 <b>Account Blocked</b>\n\nYour account has been blocked by Admin.\n\n📞 Contact @meepzizhere if you believe this is a mistake.", parse_mode='HTML')
                            return jsonify({'ok': True})
                except Exception as e:
                    print(f"⚠️ Callback ban check error: {e}")
            
            print(f"Processing callback query: chat_id={chat_id}, telegram_id={telegram_id}, data='{callback_data}'")
            
            # Check if user is admin for admin callback queries
            if callback_data.startswith('admin_users_page_') and not is_admin(telegram_id):
                print(f"Non-admin user {telegram_id} tried to use admin callback")
                return jsonify({'ok': True})
            
            # Handle admin users pagination
            if callback_data.startswith('admin_users_page_'):
                try:
                    page = int(callback_data.split('_')[-1])
                    print(f"🔄 Admin pagination: Going to page {page}")
                    handle_admin_list_users(chat_id, page)
                    
                    # Answer callback query
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                    
                    return jsonify({'ok': True})
                except Exception as e:
                    print(f"❌ Error in admin pagination: {e}")
                    # Answer callback query even if there's an error
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id'], 'text': 'Có lỗi xảy ra'}, timeout=10)
                    return jsonify({'ok': True})
            
            # Handle admin users info callback
            elif callback_data == 'admin_users_info':
                try:
                    print(f"🔄 Admin users info callback")
                    handle_admin_list_users(chat_id, 1)
                    
                    # Answer callback query
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                    
                    return jsonify({'ok': True})
                except Exception as e:
                    print(f"❌ Error in admin users info: {e}")
                    # Answer callback query even if there's an error
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id'], 'text': 'Có lỗi xảy ra'}, timeout=10)
                    return jsonify({'ok': True})

            # Handle crypto payment callbacks
            elif callback_data == 'crypto_binance':
                try:
                    handle_crypto_binance_callback(chat_id, telegram_id)
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                except Exception as e:
                    print(f"❌ Error crypto_binance: {e}")
                return jsonify({'ok': True})
            
            elif callback_data == 'crypto_bybit':
                try:
                    handle_crypto_bybit_callback(chat_id, telegram_id)
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                except Exception as e:
                    print(f"❌ Error crypto_bybit: {e}")
                return jsonify({'ok': True})
            
            elif callback_data == 'crypto_bsc':
                try:
                    handle_crypto_bsc_callback(chat_id, telegram_id)
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                except Exception as e:
                    print(f"❌ Error crypto_bsc: {e}")
                return jsonify({'ok': True})
            
            elif callback_data == 'crypto_trc20':
                try:
                    handle_crypto_trc20_callback(chat_id, telegram_id)
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                except Exception as e:
                    print(f"❌ Error crypto_trc20: {e}")
                return jsonify({'ok': True})
            
            # Handle transaction history callbacks
            elif callback_data == 'lsgd_nap':
                try:
                    handle_lsgd_nap_callback(chat_id, telegram_id)
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                except Exception as e:
                    print(f"❌ Error lsgd_nap: {e}")
                return jsonify({'ok': True})
            
            elif callback_data == 'lsgd_shop':
                try:
                    handle_lsgd_shop_callback(chat_id, telegram_id)
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                except Exception as e:
                    print(f"❌ Error lsgd_shop: {e}")
                return jsonify({'ok': True})
            
            # Handle referral list callbacks
            elif callback_data.startswith('referral_list_'):
                try:
                    parts = callback_data.split('_')
                    if len(parts) >= 4:
                        user_id = int(parts[2])
                        page = int(parts[3])
                        handle_referral_list_callback(chat_id, user_id, page)
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                except Exception as e:
                    print(f"❌ Error referral_list: {e}")
                return jsonify({'ok': True})
            
            # Handle back to invite callback
            elif callback_data.startswith('back_to_invite_'):
                try:
                    user_id = int(callback_data.split('_')[3])
                    user = get_user_by_id(user_id)
                    if user:
                        handle_invite_command(chat_id, user)
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                except Exception as e:
                    print(f"❌ Error back_to_invite: {e}")
                return jsonify({'ok': True})
            
            # Handle language selection callbacks
            elif callback_data.startswith('lang_'):
                try:
                    lang_code = callback_data.split('_')[1]
                    if lang_code in LANGUAGES:
                        # Get supabase client
                        try:
                            from supabase_client import get_supabase_client
                            supabase = get_supabase_client()
                        except:
                            supabase = None
                        
                        # Update user language
                        if set_user_language(supabase, telegram_id, lang_code):
                            message = get_text('language_changed', lang_code)
                            send_telegram_message(chat_id, message)
                        else:
                            send_telegram_message(chat_id, "❌ Error updating language")
                    
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id'], 'text': '✅ Language updated!'}, timeout=10)
                except Exception as e:
                    print(f"❌ Error lang callback: {e}")
                return jsonify({'ok': True})
            
            # Handle hdsd language callbacks
            elif callback_data == 'hdsd_en':
                try:
                    send_detailed_help_message_en(chat_id)
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                except Exception as e:
                    print(f"❌ Error hdsd_en: {e}")
                return jsonify({'ok': True})
            
            elif callback_data == 'hdsd_tr':
                try:
                    send_detailed_help_message_tr(chat_id)
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                except Exception as e:
                    print(f"❌ Error hdsd_tr: {e}")
                return jsonify({'ok': True})
            
            # Handle shop language callbacks
            elif callback_data == 'shop_en':
                try:
                    handle_shop_command_en(chat_id)
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                except Exception as e:
                    print(f"❌ Error shop_en: {e}")
                return jsonify({'ok': True})
            
            elif callback_data == 'shop_tr':
                try:
                    handle_shop_command_tr(chat_id)
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        TELEGRAM_SESSION.post(answer_url, json={'callback_query_id': callback_query['id']}, timeout=10)
                except Exception as e:
                    print(f"❌ Error shop_tr: {e}")
                return jsonify({'ok': True})
            
            # Handle new user language selection callbacks
            elif callback_data.startswith('newuser_lang_'):
                try:
                    # Extract language code and optional referrer
                    parts = callback_data.replace('newuser_lang_', '').split('_ref_')
                    lang_code = parts[0]  # vi, en, or zh
                    referrer_id = parts[1] if len(parts) > 1 else None
                    
                    print(f"🌍 New user {telegram_id} selected language: {lang_code}, referrer: {referrer_id}")
                    
                    # Get or create user
                    user = get_user_from_supabase(telegram_id)
                    if not user:
                        # Create new user with selected language
                        user_data = callback_query['from']
                        username = user_data.get('username', '')
                        first_name = user_data.get('first_name', '')
                        last_name = user_data.get('last_name', '')
                        user = create_user_in_supabase(telegram_id, username, first_name, last_name)
                    
                    # Update user language
                    try:
                        from supabase_client import get_supabase_client
                        supabase = get_supabase_client()
                        if supabase:
                            set_user_language(supabase, telegram_id, lang_code)
                    except Exception as e:
                        print(f"Error setting language: {e}")
                    
                    # Process referral if exists
                    if referrer_id:
                        try:
                            process_referral(telegram_id, referrer_id)
                        except Exception as e:
                            print(f"Error processing referral: {e}")
                    
                    # Send welcome message in selected language
                    send_welcome_message(chat_id, user, lang_code)
                    
                    # Answer callback
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
                    if bot_token:
                        answer_url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        lang_names = {'vi': 'Tiếng Việt', 'en': 'English', 'zh': '中文'}
                        TELEGRAM_SESSION.post(answer_url, json={
                            'callback_query_id': callback_query['id'],
                            'text': f'✅ {lang_names.get(lang_code, lang_code)}'
                        }, timeout=10)
                except Exception as e:
                    print(f"❌ Error newuser_lang callback: {e}")
                    import traceback
                    traceback.print_exc()
                return jsonify({'ok': True})
            
            return jsonify({'ok': True})
        
        if 'message' not in data:
            print("No message in data")
            return jsonify({'ok': True})
        
        message = data['message']
        chat_id = message['chat']['id']
        user_info = message['from']
        text = message.get('text', '')

        # Global shutdown: block all non-admins (except /start)
        if is_bot_closed():
            try:
                telegram_id_shutdown = user_info['id']
            except Exception:
                telegram_id_shutdown = None
            if telegram_id_shutdown and not is_admin(telegram_id_shutdown):
                if not (text and text.strip().lower() == '/start'):
                    send_telegram_message(chat_id, get_bot_closed_message())
                    return jsonify({'ok': True})
        
        print(f"Processing message: chat_id={chat_id}, text='{text}', user={user_info}")
        
        telegram_id = user_info['id']
        username = user_info.get('username', '')
        first_name = user_info.get('first_name', '')
        last_name = user_info.get('last_name', '')
        
        # Ban check: block all commands for banned users (except admins)
        if not is_admin(telegram_id):
            # Direct check from Supabase for reliability
            try:
                from .supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    resp = supabase.table('users').select('is_blocked').eq('telegram_id', str(telegram_id)).limit(1).execute()
                    if resp.data and resp.data[0].get('is_blocked'):
                        print(f"🚫 BLOCKED USER {telegram_id} tried to use command: {text}")
                        send_telegram_message(chat_id, "🚫 <b>Account Blocked</b>\n\nYour account has been blocked by Admin.\n\n📞 Contact @meepzizhere if you believe this is a mistake.", parse_mode='HTML')
                        return jsonify({'ok': True})
            except Exception as e:
                print(f"⚠️ Ban check error: {e}")
                # Fallback to is_user_banned function
                if is_user_banned(telegram_id):
                    print(f"🚫 BLOCKED USER {telegram_id} (fallback check)")
                    send_telegram_message(chat_id, "🚫 <b>Account Blocked</b>\n\nYour account has been blocked by Admin.\n\n📞 Contact @meepzizhere if you believe this is a mistake.", parse_mode='HTML')
                    return jsonify({'ok': True})
        
        # Spam protection: block users who spam commands (except admins and /start)
        if not is_admin(telegram_id) and text and not text.startswith('/start'):
            try:
                from .spam_protection import check_spam_protection
                # Get language_code from user_info
                language_code = user_info.get('language_code', 'vi')
                allowed, error_msg = check_spam_protection(telegram_id, language_code)
                if not allowed:
                    print(f"🚫 SPAM BLOCKED: User {telegram_id} - {error_msg}")
                    send_telegram_message(chat_id, error_msg)
                    return jsonify({'ok': True})
            except Exception as e:
                print(f"⚠️ Spam protection error: {e}")
                # Continue on error

        # Handle admin commands first (before creating user)
        if text.startswith('/admin'):
            print(f"🔍 DEBUG: Processing admin command: '{text}' from user {telegram_id}")
            # Check if user is admin before processing
            if not is_admin(telegram_id):
                print(f"Non-admin user {telegram_id} tried to use admin command")
                return jsonify({'ok': True})
            # Get or create user for admin
            user = get_user(telegram_id)
            if not user:
                print(f"Creating new admin user: {telegram_id}")
                user = create_user(telegram_id, username, first_name, last_name)
            else:
                print(f"Found existing admin user: {user}")
            print(f"🔍 DEBUG: About to call handle_admin_command with text: '{text}'")
            handle_admin_command(chat_id, user, text)
            print(f"🔍 DEBUG: handle_admin_command completed for text: '{text}'")
            return jsonify({'ok': True})
        
        # 🚨 NUCLEAR: Completely disable maintenance check
        if False:  # Never execute maintenance block
            send_telegram_message(chat_id, "🔧 Bot đang trong chế độ bảo trì. Vui lòng thử lại sau!")
            return jsonify({'ok': True})
        
        # Handle /start command separately to avoid duplicate user creation
        if text.startswith('/start'):
            print("Handling /start command")
            
            # Check for referral code
            referral_code = None
            if ' ' in text:
                parts = text.split(' ', 1)
                if len(parts) > 1 and parts[1].startswith('ref_'):
                    referral_code = parts[1][4:]  # Remove 'ref_' prefix
                    print(f"🔗 Referral code detected: {referral_code}")
            
            user = get_user(telegram_id)
            
            # Check ban status for existing users on /start too
            if user and not is_admin(telegram_id):
                if user.get('is_blocked'):
                    print(f"🚫 BLOCKED USER {telegram_id} tried /start")
                    send_telegram_message(chat_id, "🚫 <b>Account Blocked</b>\n\nYour account has been blocked by Admin.\n\n📞 Contact @meepzizhere if you believe this is a mistake.", parse_mode='HTML')
                    return jsonify({'ok': True})
            if not user:
                print(f"Creating new user: {telegram_id}")
                user = create_user(telegram_id, username, first_name, last_name)
                if not user:
                    print(f"❌ Failed to create user: {telegram_id}")
                    send_telegram_message(chat_id, "❌ Có lỗi xảy ra khi tạo tài khoản. Vui lòng thử lại sau.")
                    return jsonify({'ok': True})
                print(f"✅ New user created: {telegram_id}")
                
                # Process referral if exists
                if referral_code:
                    process_referral(telegram_id, user, referral_code)
                
                # NEW USER: Show language selection FIRST before welcome message
                send_language_selection_for_new_user(chat_id, referral_code)
                return jsonify({'ok': True})
            else:
                print(f"✅ User already exists: {telegram_id}")
                # Send welcome message for existing user too
                send_welcome_message(chat_id, user)
                return jsonify({'ok': True})
        else:
            # Get user for other commands (don't auto-create)
            user = get_user(telegram_id)
            if not user:
                print(f"❌ User {telegram_id} not found. Please use /start first.")
                send_telegram_message(chat_id, "❌ Bạn chưa đăng ký tài khoản! Vui lòng sử dụng /start để đăng ký.")
                return jsonify({'ok': True})
            else:
                print(f"Found existing user: {user}")
                # Enforce ban after user resolution as a second guard
                if not is_admin(telegram_id) and user.get('is_blocked'):
                    print(f"🚫 BLOCKED USER {telegram_id} tried to use command: {text}")
                    send_telegram_message(chat_id, "🚫 <b>Account Blocked</b>\n\nYour account has been blocked by Admin.\n\n📞 Contact @meepzizhere if you believe this is a mistake.", parse_mode='HTML')
                    return jsonify({'ok': True})
        
        # Handle user data format (dictionary from Supabase/SQLite fallback)
        if isinstance(user, dict):
            user_id = user.get('id', 1)
            username = user.get('username', 'user')
            first_name = user.get('first_name', 'User')
            last_name = user.get('last_name', '')
            coins = user.get('coins', 0)
            is_vip = user.get('is_vip', False)
            vip_expiry = user.get('vip_expiry')
            created_at = user.get('created_at', '2025-09-21T00:00:00')
        else:
            # Fallback for tuple format (old code)
            user_id = user[0]
            username = user[1]
            first_name = user[2]
            last_name = user[3]
            coins = user[4]
            is_vip = user[5]
            vip_expiry = user[6]
            created_at = user[7]
        
        
        # Handle other commands
        if text.startswith('/hdsd'):
            print("Handling /hdsd command")
            send_detailed_help_message(chat_id)
        elif text.startswith('/vs'):
            # IMPORTANT: Must be BEFORE /verify to avoid matching /verify first
            print("Handling /vs command (Spotify Student verification)")
            handle_vs_command(chat_id, user, text)
        elif text.startswith('/vp'):
            # Perplexity verification via SheerID Bot API
            print("Handling /vp command (Perplexity verification)")
            handle_sheerid_verification(chat_id, user, text, 'perplexity')
        elif text.startswith('/verify3') or text.startswith('/verify5'):
            # Batch verify multiple links - MUST be before /verify
            print("Handling batch verify command")
            handle_verify_batch_command(chat_id, user, text)
        elif text.startswith('/verify') or (text.startswith('/v ') or text == '/v'):
            # Gemini Student verification via SheerID Bot API
            # Note: /v must be checked with space or exact match to avoid matching /vs, /vc, /vip, etc.
            print("Handling /verify or /v command (Gemini verification)")
            handle_sheerid_verification(chat_id, user, text, 'gemini')
        elif text.startswith('/vc3') or text.startswith('/vc5'):
            # Batch VC verify multiple links - MUST be before /vc
            print("Handling batch VC command")
            handle_vc_batch_command(chat_id, user, text)
        elif text.startswith('/vc'):
            # Teacher verification via SheerID Bot API
            print("Handling /vc command (Teacher verification)")
            handle_sheerid_verification(chat_id, user, text, 'teacher')
        elif text.startswith('/help'):
            print("Handling /help command")
            # Get user language safely
            user_lang = DEFAULT_LANGUAGE
            try:
                telegram_id = user.get('telegram_id') if isinstance(user, dict) else user[1] if user and len(user) > 1 else None
                if telegram_id:
                    from supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    if supabase:
                        user_lang = get_user_language(supabase, telegram_id)
            except Exception as e:
                print(f"Error getting language for /help: {e}")
            send_help_message(chat_id, user_lang)
        elif text.startswith('/queue'):
            print("Handling /queue command")
            handle_queue_command(chat_id, user)
        elif text.startswith('/status'):
            print("Handling /status command")
            try:
                user_lang = get_user_language(supabase, telegram_id)
            except Exception as e:
                print(f"Error getting language for /status: {e}")
                user_lang = 'vi'
            handle_status_command(chat_id, text, user_lang)
        elif text.startswith('/me'):
            print("Handling /me command")
            send_user_info(chat_id, user)
        elif text.startswith('/vip'):
            print("Handling /vip command")
            handle_vip_command(chat_id, user)
        elif text.startswith('/crypto'):
            print("🔍 DEBUG: Handling /crypto command")
            try:
                handle_crypto_command(chat_id, user)
                print("✅ DEBUG: /crypto command completed")
            except Exception as e:
                print(f"❌ DEBUG: /crypto error: {e}")
                import traceback
                traceback.print_exc()
                send_telegram_message(chat_id, f"❌ Lỗi lệnh /crypto: {e}")
        elif text.startswith('/nap'):
            print("Handling /nap command")
            handle_nap_command(chat_id, user, text)
        elif text.startswith('/binance'):
            print("🔍 DEBUG: Handling /binance command")
            try:
                handle_binance_command(chat_id, user, text)
                print("✅ DEBUG: /binance command completed")
            except Exception as e:
                print(f"❌ DEBUG: /binance error: {e}")
                import traceback
                traceback.print_exc()
                send_telegram_message(chat_id, f"❌ Lỗi lệnh /binance: {e}")
        elif text.startswith('/relocket'):
            print("🔍 DEBUG: Handling /relocket command")
            try:
                handle_relocket_command(chat_id, user, text)
                print("✅ DEBUG: /relocket command completed")
            except Exception as e:
                print(f"❌ DEBUG: /relocket error: {e}")
                import traceback
                traceback.print_exc()
                send_telegram_message(chat_id, f"❌ Lỗi lệnh /relocket: {e}")
        elif text.startswith('/locket'):
            print("🔍 DEBUG: Handling /locket command")
            try:
                handle_locket_command(chat_id, user, text)
                print("✅ DEBUG: /locket command completed")
            except Exception as e:
                print(f"❌ DEBUG: /locket error: {e}")
                import traceback
                traceback.print_exc()
                send_telegram_message(chat_id, f"❌ Lỗi lệnh /locket: {e}")
        elif text.startswith('/buycredits'):
            print("🔍 DEBUG: Handling /buycredits command")
            try:
                handle_buycredits_command(chat_id, user, text)
                print("✅ DEBUG: /buycredits command completed")
            except Exception as e:
                print(f"❌ DEBUG: /buycredits error: {e}")
                import traceback
                traceback.print_exc()
                send_telegram_message(chat_id, f"❌ Lỗi lệnh /buycredits: {e}")
        elif text.startswith('/seller'):
            print("🔍 DEBUG: Handling /seller command")
            try:
                handle_seller_command(chat_id, user, text)
                print("✅ DEBUG: /seller command completed")
            except Exception as e:
                print(f"❌ DEBUG: /seller error: {e}")
                import traceback
                traceback.print_exc()
                send_telegram_message(chat_id, f"❌ Lỗi lệnh /seller: {e}")
        elif text.startswith('/claim'):
            print("Handling /claim command")
            handle_claim_command(chat_id, user, text)
        elif text.startswith('/checkin') or text.startswith('/diemdanh'):
            print("Handling /checkin or /diemdanh command")
            handle_checkin_command(chat_id, user)
        elif text.startswith('/checkchannel') or text.startswith('/join'):
            print("Handling /checkchannel or /join command")
            handle_checkchannel_command(chat_id, user)
        elif text.startswith('/myjobs'):
            print("Handling /myjobs command")
            handle_myjobs_command(chat_id, user)
        elif text.startswith('/lsgd'):
            print("🔍 DEBUG: Handling /lsgd command")
            try:
                handle_lsgd_command(chat_id, user)
                print("✅ DEBUG: /lsgd command completed")
            except Exception as e:
                print(f"❌ DEBUG: /lsgd error: {e}")
                import traceback
                traceback.print_exc()
                send_telegram_message(chat_id, f"❌ Lỗi lệnh /lsgd: {e}")
        elif text.startswith('/invite'):
            print("Handling /invite command")
            handle_invite_command(chat_id, user)
        elif text.startswith('/link'):
            print("Handling /link command")
            handle_link_command(chat_id, user, text)
        elif text.startswith('/quests'):
            print("Handling /quests command")
            handle_quests_command(chat_id, user)
        elif text.startswith('/vip'):
            print("Handling /vip command")
            handle_vip_command(chat_id, user)
        elif text.startswith('/mua '):
            # New shop purchase syntax
            parts = text.split()
            if len(parts) == 1:
                send_telegram_message(chat_id, "❓ Cú pháp: /mua <trial|verified|canva|ultra|aiultra45|chatgpt|spotify|vpnss|per|per1m|gpt1m|m365|adobe4m|vip7|vip30> [số_lượng]")
            else:
                kind = parts[1].lower()
                qty = 1
                if len(parts) >= 3:
                    try:
                        qty = int(parts[2])
                    except Exception:
                        qty = 1
                if kind in ('trial','verified','canva','chatgpt','spotify','ultra','aiultra45','vpnss','per','per1m','gpt1m','m365','adobe4m'):
                    handle_buy_google_accounts_typed(
                        chat_id,
                        user,
                        qty,
                        verified=(kind=='verified'),
                        canva=(kind=='canva'),
                        chatgpt=(kind=='chatgpt'),
                        ultra=(kind=='ultra'),
                        ultra45=(kind=='aiultra45'),
                        spotify=(kind=='spotify'),
                        surfshark=(kind=='vpnss'),
                        perplexity=(kind=='per'),
                        perplexity1m=(kind=='per1m'),
                        gpt1m=(kind=='gpt1m'),
                        m365=(kind=='m365'),
                        adobe4m=(kind=='adobe4m')
                    )
                elif kind in ('vip7','vip30'):
                    days = 7 if kind=='vip7' else 30
                    handle_buy_vip_days(chat_id, user, days)
                elif kind in ('vippro7', 'vippro30'):
                    days = 7 if kind=='vippro7' else 30
                    handle_buy_vip_tier(chat_id, user, 'pro', days)
                elif kind in ('vipbiz7', 'vipbiz30', 'vipbusiness7', 'vipbusiness30'):
                    days = 7 if kind in ('vipbiz7', 'vipbusiness7') else 30
                    handle_buy_vip_tier(chat_id, user, 'business', days)
                else:
                    send_telegram_message(chat_id, "❌ Loại hàng không hợp lệ. Dùng /shop để xem danh mục.")
        elif text.startswith('/shop'):
            handle_shop_command(chat_id)
        elif text.startswith('/muaacc') or text.startswith('/buyacc'):
            handle_buy_google_account(chat_id, user)
        elif text.startswith('/giftcode'):
            # /giftcode <mã>
            parts = text.split()
            if len(parts) >= 2:
                code = parts[1]
                handle_user_use_giftcode(chat_id, user, code)
            else:
                # Get user language for giftcode usage message
                telegram_id = user.get('telegram_id') if isinstance(user, dict) else user[1] if user and len(user) > 1 else None
                try:
                    from supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    user_lang = get_user_language(supabase, telegram_id)
                except:
                    user_lang = DEFAULT_LANGUAGE
                send_telegram_message(chat_id, get_text('giftcode_usage', user_lang))
        elif text.startswith('/lang'):
            print("Handling /lang command")
            handle_language_command(chat_id, user, text)
        elif text.startswith('/cancel') or text.startswith('/huy'):
            print("Handling /cancel or /huy command")
            handle_cancel_job_command(chat_id, user)
        elif text.startswith('/fix'):
            print("Handling /fix command - burn SheerID link")
            handle_fix_command(chat_id, user, text)
        else:
            print(f"Unknown command: {text}")
            # Get user language for unknown command message
            telegram_id = user.get('telegram_id') if isinstance(user, dict) else user[1] if user and len(user) > 1 else None
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                user_lang = get_user_language(supabase, telegram_id)
            except:
                user_lang = DEFAULT_LANGUAGE
            send_unknown_command(chat_id, user_lang)
        
        # Process non-critical operations asynchronously
        run_async_task(lambda: print("Webhook processed successfully"))
        return jsonify({'ok': True})
        
    except Exception as e:
        print(f"❌ Telegram webhook error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500

def send_welcome_message(chat_id, user, lang=None):
    """Send welcome message to user with language support"""
    # Get user's language preference
    if lang is None and user:
        try:
            telegram_id = user.get('telegram_id') if isinstance(user, dict) else user[1]
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                lang = get_user_language(supabase, telegram_id)
            else:
                lang = 'vi'
        except:
            lang = 'vi'
    if not lang:
        lang = 'vi'
    
    if not user:
        # No user - generic welcome
        message = "🎉 Chào mừng đến với SheerID VIP Bot!\n\n❓ Cần hỗ trợ? Liên hệ: @meepzizhere"
    else:
        # Handle user data format (dictionary from Supabase/SQLite fallback)
        if isinstance(user, dict):
            coins = user.get('coins', 0)
            is_vip = user.get('is_vip', False)
            vip_expiry = user.get('vip_expiry')
        else:
            # Fallback for tuple format (old code)
            coins = user[5]
            is_vip = is_vip_active(user)
            vip_expiry = user[7] if len(user) > 7 else None
        
        vip_status = "❌ Hết hạn"
        if is_vip and vip_expiry:
            from datetime import datetime, timezone, timedelta
            try:
                # Parse UTC expiry time and convert to Vietnam time
                expiry_date_utc = datetime.fromisoformat(str(vip_expiry).replace('Z', '+00:00'))
                vietnam_tz = timezone(timedelta(hours=7))
                now_vn = datetime.now(vietnam_tz)
                expiry_date_vietnam = expiry_date_utc.astimezone(vietnam_tz)
                if lang == 'vi':
                    vip_status = f"✅ Có (hết hạn: {expiry_date_vietnam.strftime('%d/%m/%Y %H:%M')} VN)" if now_vn < expiry_date_vietnam else "❌ Hết hạn"
                elif lang == 'en':
                    vip_status = f"✅ Yes (expires: {expiry_date_vietnam.strftime('%Y-%m-%d %H:%M')} VN)" if now_vn < expiry_date_vietnam else "❌ Expired"
                else:
                    vip_status = f"✅ 是 (到期: {expiry_date_vietnam.strftime('%Y-%m-%d %H:%M')} VN)" if now_vn < expiry_date_vietnam else "❌ 已过期"
            except:
                vip_status = "❌ Hết hạn" if lang == 'vi' else ("❌ Expired" if lang == 'en' else "❌ 已过期")
        elif not is_vip:
            vip_status = "❌ Hết hạn" if lang == 'vi' else ("❌ Expired" if lang == 'en' else "❌ 已过期")
        
        # Handle user data format (dictionary from SQLite)
        if isinstance(user, dict):
            telegram_id = user.get('telegram_id', '1')
            username = user.get('username', 'user')
            first_name = user.get('first_name', 'User')
            last_name = user.get('last_name', '')
            coins = user.get('coins', 0)
        else:
            # Fallback for tuple format (old code)
            telegram_id = user[1]
            username = user[2]
            first_name = user[3]
            last_name = user[4]
            coins = user[5]
        
        # Multilingual welcome messages for existing users
        welcome_messages = {
            'vi': f"""🎉 Chào mừng trở lại SheerID VIP Bot!

👤 Thông tin tài khoản:
• Tên: {first_name or 'N/A'} {last_name if last_name and last_name != 'User' else ''}
• Username: @{username or 'N/A'}
• ID: {telegram_id}
• Xu hiện tại: {coins} 🪙
• VIP: {vip_status}

🎁 ĐỪNG BỎ LỠ GIFTCODE & ƯU ĐÃI!
📢 Tham gia kênh thông báo để:
   ✨ Nhận GIFTCODE miễn phí
   🎉 Cập nhật ưu đãi HOT đầu tiên
   🔔 Không bỏ lỡ sự kiện đặc biệt
   
👉 Tham gia ngay: https://t.me/channel_sheerid_vip_bot

❓ Cần hỗ trợ? Liên hệ admin: @meepzizhere""",

            'en': f"""🎉 Welcome back to SheerID VIP Bot!

👤 Account Info:
• Name: {first_name or 'N/A'} {last_name if last_name and last_name != 'User' else ''}
• Username: @{username or 'N/A'}
• ID: {telegram_id}
• Current Coins: {coins} 🪙
• VIP: {vip_status}

🎁 DON'T MISS GIFTCODES & OFFERS!
📢 Join our channel for:
   ✨ Free GIFTCODES
   🎉 Hot deals first
   🔔 Special events
   
👉 Join now: https://t.me/channel_sheerid_vip_bot

❓ Need help? Contact: @meepzizhere""",

            'zh': f"""🎉 欢迎回到 SheerID VIP 机器人！

👤 账户信息：
• 姓名：{first_name or 'N/A'} {last_name if last_name and last_name != 'User' else ''}
• 用户名：@{username or 'N/A'}
• ID：{telegram_id}
• 当前金币：{coins} 🪙
• VIP：{vip_status}

🎁 不要错过礼品码和优惠！
📢 加入我们的频道获取：
   ✨ 免费礼品码
   🎉 最新优惠
   🔔 特别活动
   
👉 立即加入：https://t.me/channel_sheerid_vip_bot

❓ 需要帮助？联系：@meepzizhere"""
        }
        
        message = welcome_messages.get(lang, welcome_messages['vi'])
    
    # Use plain text to avoid Markdown parsing issues with special characters in usernames
    send_telegram_message_plain(chat_id, message)

def send_balance_message(chat_id, user):
    """Send balance information"""
    coins = user[5] if user else 0
    # Auto-expire VIP if needed before display
    try:
        if user:
            if isinstance(user, tuple):
                _is_vip = bool(user[6]) if len(user) > 6 else False
                _vip_expiry = user[7] if len(user) > 7 else None
                if _is_vip and _vip_expiry:
                    from datetime import datetime, timezone, timedelta
                    expiry_date_utc = datetime.fromisoformat(str(_vip_expiry).replace('Z', '+00:00'))
                    vietnam_tz = timezone(timedelta(hours=7))
                    if datetime.now(vietnam_tz) >= expiry_date_utc.astimezone(vietnam_tz):
                        # expire in Supabase if available
                        try:
                            from supabase_client import get_supabase_client
                            supabase = get_supabase_client()
                            if supabase:
                                supabase.table('users').update({'is_vip': False}).eq('id', user[0]).execute()
                        except Exception:
                            pass
                        _is_vip = False
                is_vip = _is_vip
            else:
                _is_vip = bool(user.get('is_vip', False))
                vip_expiry = user.get('vip_expiry')
                if _is_vip and vip_expiry:
                    from datetime import datetime, timezone, timedelta
                    expiry_date_utc = datetime.fromisoformat(str(vip_expiry).replace('Z', '+00:00'))
                    vietnam_tz = timezone(timedelta(hours=7))
                    if datetime.now(vietnam_tz) >= expiry_date_utc.astimezone(vietnam_tz):
                        try:
                            from supabase_client import get_supabase_client
                            supabase = get_supabase_client()
                            if supabase:
                                supabase.table('users').update({'is_vip': False}).eq('id', user.get('id')).execute()
                        except Exception:
                            pass
                        _is_vip = False
                is_vip = _is_vip
        else:
            is_vip = False
    except Exception:
        is_vip = is_vip_active(user)
    
    message = f"""
💰 Số dư tài khoản:

🪙 Xu hiện tại: {coins}
👑 VIP: {'✅ Có' if is_vip else '❌ Không'}

💡 Sử dụng /verify <URL> để xác minh SheerID
    """
    
    send_telegram_message(chat_id, message)


# ============================================
# SHEERID BOT API INTEGRATION
# Unified verification handler for all verification types
# Requirements: 1.1-1.5, 2.1-2.5, 3.1-3.5
# ============================================

# Verification types configuration
SHEERID_BOT_VERIFICATION_TYPES = {
    'gemini': {
        'commands': ['/verify', '/v'],
        'cost': 10,
        'display_name': 'Gemini',
        'display_name_vi': 'Gemini Student'
    },
    'perplexity': {
        'commands': ['/vp'],
        'cost': 25,
        'display_name': 'Perplexity',
        'display_name_vi': 'Perplexity'
    },
    'teacher': {
        'commands': ['/vc'],
        'cost': 50,
        'display_name': 'Teacher',
        'display_name_vi': 'Teacher'
    },
    'spotify': {
        'commands': ['/vs'],
        'cost': 10,
        'display_name': 'Spotify',
        'display_name_vi': 'Spotify Student'
    }
}

# Multilingual messages for SheerID Bot API verification
SHEERID_BOT_MESSAGES = {
    'no_url': {
        'vi': '❌ Vui lòng cung cấp URL xác minh\n\nVí dụ: {command} https://services.sheerid.com/verify/...',
        'en': '❌ Please provide verification URL\n\nExample: {command} https://services.sheerid.com/verify/...',
        'zh': '❌ 请提供验证 URL\n\n示例：{command} https://services.sheerid.com/verify/...'
    },
    'invalid_url': {
        'vi': '❌ URL không đúng định dạng!\n\n✅ URL hợp lệ: https://services.sheerid.com/verify/...',
        'en': '❌ Invalid URL format!\n\n✅ Valid URL: https://services.sheerid.com/verify/...',
        'zh': '❌ URL 格式无效！\n\n✅ 有效URL：https://services.sheerid.com/verify/...'
    },
    'insufficient_balance': {
        'vi': '❌ Không đủ Cash để verify {type_name}!\n\n💵 CASH: {cash}\n💰 Cần: {cost} Cash\n\n💡 Dùng lệnh /nap để nạp thêm\n🌍 Dùng /crypto để nạp crypto (quốc tế)\n\n🎁 Hoặc nhận 10 cash miễn phí:\n📢 Tham gia: @channel_sheerid_vip_bot\n⏰ Đợi 24 giờ\n👉 Gõ /checkchannel để nhận!',
        'en': '❌ Insufficient Cash for {type_name} verification!\n\n💵 CASH: {cash}\n💰 Need: {cost} Cash\n\n💡 Use /nap to top up (Vietnam bank)\n🌍 Use /crypto for crypto deposit (International)\n\n🎁 Or get 10 cash for free:\n📢 Join: @channel_sheerid_vip_bot\n⏰ Wait 24 hours\n👉 Type /checkchannel to claim!',
        'zh': '❌ {type_name} 验证现金不足！\n\n💵 现金: {cash}\n💰 需要: {cost} 现金\n\n💡 使用 /nap 充值（越南银行）\n🌍 使用 /crypto 加密货币充值（国际用户）\n\n🎁 或免费获得 10 cash：\n📢 加入：@channel_sheerid_vip_bot\n⏰ 等待24小时\n👉 输入 /checkchannel 领取！'
    },
    'job_created': {
        'vi': '✅ Đã tạo job verify {type_name}!\n\n🆔 Job ID: `{job_id}`\n💰 Phí: {fee_text}\n{balance_text}\n⏳ Đang xử lý...\n\n⏱️ Thời gian dự kiến: 2-5 phút\n💡 Hệ thống sẽ tự động thông báo khi hoàn thành.',
        'en': '✅ {type_name} verification job created!\n\n🆔 Job ID: `{job_id}`\n💰 Fee: {fee_text}\n{balance_text}\n⏳ Processing...\n\n⏱️ Estimated time: 2-5 minutes\n💡 You will be notified when completed.',
        'zh': '✅ {type_name} 验证任务已创建！\n\n🆔 任务ID: `{job_id}`\n💰 费用: {fee_text}\n{balance_text}\n⏳ 处理中...\n\n⏱️ 预计时间: 2-5分钟\n💡 完成后会通知您。'
    },
    'api_error': {
        'vi': '❌ Lỗi xử lý: {error}\n\n💡 Vui lòng thử lại sau.',
        'en': '❌ Processing Error: {error}\n\n💡 Please try again later.',
        'zh': '❌ 处理错误: {error}\n\n💡 请稍后再试。'
    },
    'api_insufficient_credits': {
        'vi': '❌ Dịch vụ tạm thời không khả dụng.\n\n💡 Vui lòng thử lại sau hoặc liên hệ admin.',
        'en': '❌ Service temporarily unavailable.\n\n💡 Please try again later or contact admin.',
        'zh': '❌ 服务暂时不可用。\n\n💡 请稍后再试或联系管理员。'
    },
    'api_maintenance': {
        'vi': '🔧 Dịch vụ đang bảo trì.\n\n⏰ Vui lòng thử lại sau.',
        'en': '🔧 Service under maintenance.\n\n⏰ Please try again later.',
        'zh': '🔧 服务维护中。\n\n⏰ 请稍后再试。'
    },
    'api_rate_limited': {
        'vi': '⏳ Hệ thống đang bận. Vui lòng thử lại sau vài giây.',
        'en': '⏳ System busy. Please try again in a few seconds.',
        'zh': '⏳ 系统繁忙。请稍后再试。'
    },
    'api_not_configured': {
        'vi': '❌ Dịch vụ chưa được cấu hình.\n\n💡 Vui lòng liên hệ admin.',
        'en': '❌ Service not configured.\n\n💡 Please contact admin.',
        'zh': '❌ 服务未配置。\n\n💡 请联系管理员。'
    }
}


def handle_sheerid_verification(chat_id, user, text, verify_type: str):
    """
    Unified handler for all SheerID Bot API verifications
    
    Args:
        chat_id: Telegram chat ID
        user: User object (dict or tuple)
        text: Command text including URL
        verify_type: Type of verification ('gemini', 'perplexity', 'teacher')
    
    Requirements: 1.1-1.5, 2.1-2.5, 3.1-3.5
    """
    try:
        # Check maintenance mode based on verification type
        if verify_type == 'teacher':
            # Check VC Teacher maintenance
            vc_maintenance = BOT_CONFIG.get('vc_maintenance', False)
            env_vc_maintenance = os.environ.get('VC_MAINTENANCE', 'false').lower() == 'true'
            is_maintenance = vc_maintenance or env_vc_maintenance
            maintenance_key = 'vc_maintenance'
        else:
            # Check Verify maintenance for gemini/perplexity
            verify_maintenance = BOT_CONFIG.get('verify_maintenance', False)
            env_verify_maintenance = os.environ.get('VERIFY_MAINTENANCE', 'false').lower() == 'true'
            is_maintenance = verify_maintenance or env_verify_maintenance
            maintenance_key = 'verify_maintenance'
        
        print(f"🔍 DEBUG handle_sheerid_verification: {maintenance_key} = {is_maintenance}")
        
        if is_maintenance:
            # Allow admin to bypass maintenance
            if chat_id not in ADMIN_TELEGRAM_IDS:
                maintenance_msg = BOT_CONFIG.get('maintenance_message', 
                    "🔧 Hệ thống đang bảo trì. Vui lòng thử lại sau.")
                # Use plain text to avoid Markdown parsing issues with special characters
                send_telegram_message_plain(chat_id, maintenance_msg)
                return
            else:
                print(f"⚠️ Admin {chat_id} bypassing maintenance mode")
        
        # Get verification type config
        type_config = SHEERID_BOT_VERIFICATION_TYPES.get(verify_type)
        if not type_config:
            send_telegram_message(chat_id, f"❌ Invalid verification type: {verify_type}")
            return
        
        cost = type_config['cost']
        display_name = type_config['display_name']
        command = type_config['commands'][0]  # Primary command for examples
        
        # Get user language
        telegram_id = user.get('telegram_id') if isinstance(user, dict) else user[1] if user and len(user) > 1 else None
        user_lang = DEFAULT_LANGUAGE
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase and telegram_id:
                user_lang = get_user_language(supabase, telegram_id)
        except:
            pass
        
        # Extract URL from command text
        # Remove command prefix at the beginning only (not in URL)
        url = text.strip()
        for cmd in type_config['commands']:
            if url.startswith(cmd):
                url = url[len(cmd):].strip()
                break
        
        print(f"DEBUG handle_sheerid_verification: type={verify_type}, url={url[:50] if url else 'None'}...")
        
        # Validate URL - Requirements: 1.5, 2.5, 3.5
        if not url:
            msg = SHEERID_BOT_MESSAGES['no_url'].get(user_lang, SHEERID_BOT_MESSAGES['no_url']['vi'])
            send_telegram_message(chat_id, msg.format(command=command))
            return
        
        if not validate_sheerid_url(url):
            msg = SHEERID_BOT_MESSAGES['invalid_url'].get(user_lang, SHEERID_BOT_MESSAGES['invalid_url']['vi'])
            send_telegram_message(chat_id, msg)
            return
        
        # Get user_id and check balance
        if isinstance(user, dict):
            user_id = user.get('id', 0)
            is_vip = user.get('is_vip', False)
            wallets = supabase_get_wallets_by_user_id(user_id)
            cash = wallets[0] if wallets else int(user.get('cash') or 0)
            bonus = wallets[1] if wallets else int(user.get('coins') or 0)
            coins_verify_unlocked = user.get('coins_verify_unlocked', False)
            total_cash_spent = user.get('total_cash_spent', 0)
        else:
            user_id = user[0]
            is_vip = bool(user[6]) if len(user) > 6 else False  # is_vip is at index 6
            wallets = supabase_get_wallets_by_user_id(user_id)
            cash = wallets[0] if wallets else user[5]
            bonus = wallets[1] if wallets else 0
            # For tuple users, fetch coins_verify_unlocked from Supabase
            coins_verify_unlocked = False
            total_cash_spent = 0
            try:
                if SUPABASE_AVAILABLE:
                    from supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    if supabase:
                        user_resp = supabase.table('users').select('coins_verify_unlocked', 'total_cash_spent').eq('id', user_id).execute()
                        if user_resp.data:
                            coins_verify_unlocked = user_resp.data[0].get('coins_verify_unlocked', False)
                            total_cash_spent = user_resp.data[0].get('total_cash_spent', 0)
            except Exception as e:
                print(f"⚠️ Error fetching coins_verify_unlocked: {e}")
        
        # COINS PAYMENT LOGIC - Only for student verification (gemini)
        payment_method = "cash"  # Default to cash
        if verify_type == 'gemini' and not is_vip:
            try:
                # Auto-unlock if conditions met (first deposit OR spent >= 30 cash)
                if not coins_verify_unlocked:
                    if cash > 10 or total_cash_spent >= 30:
                        coins_verify_unlocked = True
                        # Update database
                        try:
                            if SUPABASE_AVAILABLE:
                                from supabase_client import get_supabase_client
                                supabase = get_supabase_client()
                                if supabase:
                                    supabase.table('users').update({'coins_verify_unlocked': True}).eq('id', user_id).execute()
                                    print(f"✅ Auto-unlocked coins verify for user {user_id}")
                        except Exception as e:
                            print(f"⚠️ Failed to auto-unlock: {e}")
                
                # Count coins verifications today (for 3/day limit)
                coins_verify_count_today = 0
                if coins_verify_unlocked and SUPABASE_AVAILABLE:
                    try:
                        from supabase_client import get_supabase_client
                        from datetime import datetime, timezone, timedelta
                        supabase = get_supabase_client()
                        if supabase:
                            # Use Vietnam timezone (UTC+7)
                            vietnam_tz = timezone(timedelta(hours=7))
                            now_vn = datetime.now(vietnam_tz)
                            today_start = now_vn.replace(hour=0, minute=0, second=0, microsecond=0)
                            today_end = now_vn.replace(hour=23, minute=59, second=59, microsecond=999999)
                            
                            # Count COINS verifications today (payment_method = 'coins')
                            # Count both pending and completed to prevent spam abuse
                            coins_resp = (
                                supabase
                                .table('sheerid_bot_jobs')
                                .select('id', count='exact')
                                .eq('user_id', user_id)
                                .in_('status', ['pending', 'completed'])
                                .eq('payment_method', 'coins')
                                .gte('created_at', today_start.isoformat())
                                .lte('created_at', today_end.isoformat())
                                .execute()
                            )
                            coins_verify_count_today = int(getattr(coins_resp, 'count', 0) or 0)
                            print(f"🔍 DEBUG: User {user_id} coins verifications today (pending+completed): {coins_verify_count_today}/3")
                    except Exception as e:
                        print(f"DEBUG: Error counting coins verifications: {e}")
                        coins_verify_count_today = 0
                
                # Determine payment method
                verify_cost_coins = 25  # Coins cost
                coins_daily_limit = 3  # Max 3 coins verifications per day
                
                # Check if can use coins (unlocked + enough coins + under daily limit)
                coins_under_limit = coins_verify_count_today < coins_daily_limit
                can_use_coins = coins_verify_unlocked and (bonus >= verify_cost_coins) and coins_under_limit
                
                print(f"🔍 DEBUG PAYMENT: user={user_id}, coins_unlocked={coins_verify_unlocked}, bonus={bonus}, cash={cash}, coins_today={coins_verify_count_today}/3")
                
                if can_use_coins:
                    # Prefer coins if unlocked, available, and under limit
                    payment_method = "coins"
                    cost = 25  # Override cost for coins
                    print(f"✅ Will use COINS: 25 xu")
                else:
                    payment_method = "cash"
                    print(f"✅ Will use CASH: 10 cash")
            except Exception as e:
                print(f"❌ Error checking coins payment: {e}")
                import traceback
                traceback.print_exc()
                payment_method = "cash"
        
        # Check balance - Requirements: 1.3, 1.4, 2.3, 2.4, 3.3, 3.4
        # Note: Balance is only deducted on success via webhook
        if payment_method == "coins":
            if bonus < 25:
                msg = SHEERID_BOT_MESSAGES['insufficient_balance'].get(user_lang, SHEERID_BOT_MESSAGES['insufficient_balance']['vi'])
                send_telegram_message(chat_id, msg.format(
                    type_name=display_name,
                    cash=bonus,
                    cost=25
                ))
                return
        elif cash < cost:
            msg = SHEERID_BOT_MESSAGES['insufficient_balance'].get(user_lang, SHEERID_BOT_MESSAGES['insufficient_balance']['vi'])
            send_telegram_message(chat_id, msg.format(
                type_name=display_name,
                cash=cash,
                cost=cost
            ))
            return
        
        # Check if SheerID Bot API is configured - Requirements: 7.1-7.4
        try:
            from .sheerid_bot_client import SheerIDBotClient, get_sheerid_bot_client, SheerIDAPIError
        except ImportError:
            try:
                from sheerid_bot_client import SheerIDBotClient, get_sheerid_bot_client, SheerIDAPIError
            except ImportError:
                msg = SHEERID_BOT_MESSAGES['api_not_configured'].get(user_lang, SHEERID_BOT_MESSAGES['api_not_configured']['vi'])
                send_telegram_message(chat_id, msg)
                return
        
        if not SheerIDBotClient.is_configured():
            msg = SHEERID_BOT_MESSAGES['api_not_configured'].get(user_lang, SHEERID_BOT_MESSAGES['api_not_configured']['vi'])
            send_telegram_message(chat_id, msg)
            return
        
        # ============================================
        # DEDUCT PAYMENT UPFRONT (BEFORE creating job) to prevent spam abuse
        # ============================================
        print(f"🔍 DEBUG UPFRONT DEDUCTION: user_id={user_id}, payment_method={payment_method}, cash={cash}, bonus={bonus}, is_vip={is_vip}")
        # VIP: Will refund on both success and fail (free verification)
        # Non-VIP: Will refund only on fail, keep on success
        # This prevents users from spamming multiple jobs with limited cash/coins
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            print(f"🔍 DEBUG: supabase={supabase is not None}, payment_method={payment_method}")
            if supabase:
                if payment_method == "coins" and bonus >= 25:
                    # Deduct 25 coins immediately to hold/prevent spam
                    new_bonus = bonus - 25
                    print(f"🔍 DEBUG: About to deduct coins. Current: {bonus}, New: {new_bonus}")
                    result = supabase.table('users').update({'coins': new_bonus}).eq('id', user_id).execute()
                    print(f"🔍 DEBUG: Update result: {result}")
                    print(f"💰 HOLD: Deducted 25 coins from user {user_id}. Will refund only on fail. New balance: {new_bonus}")
                    bonus = new_bonus  # Update local variable for display
                    print(f"✅ Database updated: user {user_id} coins = {new_bonus}")
                elif payment_method == "cash" and cash >= 10:
                    # Deduct 10 cash immediately to hold/prevent spam
                    new_cash = cash - 10
                    print(f"🔍 DEBUG: About to deduct cash. Current: {cash}, New: {new_cash}")
                    result = supabase.table('users').update({'cash': new_cash}).eq('id', user_id).execute()
                    print(f"🔍 DEBUG: Update result: {result}")
                    if is_vip:
                        print(f"💰 HOLD: Deducted 10 cash from VIP user {user_id}. Will refund on completion. New balance: {new_cash}")
                    else:
                        print(f"💰 HOLD: Deducted 10 cash from user {user_id}. Will refund only on fail. New balance: {new_cash}")
                    cash = new_cash  # Update local variable for display
                    print(f"✅ Database updated: user {user_id} cash = {new_cash}")
                else:
                    print(f"⚠️ DEBUG: Skipped deduction - payment_method={payment_method}, cash={cash}, bonus={bonus}")
            else:
                print(f"⚠️ DEBUG: Skipped deduction - supabase not available")
        except Exception as e:
            print(f"❌ Error deducting upfront payment: {e}")
            import traceback
            traceback.print_exc()
        
        # Create local job record first - Requirements: 1.2, 2.2, 3.2
        # Use 'sheerid_bot' prefix to distinguish from legacy jobs
        job_id = create_sheerid_bot_job(user_id, telegram_id, url, verify_type, cost, payment_method)
        
        if not job_id:
            send_telegram_message(chat_id, "❌ Lỗi tạo job. Vui lòng thử lại.")
            return
        
        # Send initial confirmation (without URL to hide API details)
        msg = SHEERID_BOT_MESSAGES['job_created'].get(user_lang, SHEERID_BOT_MESSAGES['job_created']['vi'])
        
        # Format fee and balance text based on payment method
        if payment_method == "coins":
            fee_text = "25 Xu"
            balance_text = f"🪙 Xu: {bonus} | 💵 Cash: {cash}"
        else:
            fee_text = f"{cost} Cash"
            balance_text = f"💵 Cash: {cash} | 🪙 Xu: {bonus}"
        
        send_telegram_message(chat_id, msg.format(
            type_name=display_name,
            job_id=job_id,
            fee_text=fee_text,
            balance_text=balance_text
        ))
        
        # Submit to SheerID Bot API - Requirements: 1.1, 2.1, 3.1
        try:
            client = get_sheerid_bot_client()
            if not client:
                # REFUND the upfront payment since API is not configured
                try:
                    if SUPABASE_AVAILABLE:
                        from supabase_client import get_supabase_client
                        supabase = get_supabase_client()
                        if supabase:
                            print(f"🔍 DEBUG REFUND: Attempting to refund 10 cash to user_id={user_id}")
                            # Get current cash - query by database ID, not telegram_id
                            user_result = supabase.table('users').select('cash, telegram_id').eq('id', user_id).execute()
                            if user_result.data:
                                current_cash = user_result.data[0].get('cash', 0)
                                telegram_id_for_log = user_result.data[0].get('telegram_id', 'unknown')
                                new_cash = current_cash + 10
                                update_result = supabase.table('users').update({'cash': new_cash}).eq('id', user_id).execute()
                                print(f"💰 REFUND SUCCESS: Returned 10 cash to user_id={user_id} (telegram_id={telegram_id_for_log}) due to API not configured. Old balance: {current_cash}, New balance: {new_cash}")
                                print(f"🔍 DEBUG REFUND: Update result: {update_result.data}")
                            else:
                                print(f"❌ REFUND FAILED: User {user_id} not found in database")
                except Exception as refund_error:
                    print(f"❌ Error refunding cash: {refund_error}")
                    import traceback
                    traceback.print_exc()
                
                msg = SHEERID_BOT_MESSAGES['api_not_configured'].get(user_lang, SHEERID_BOT_MESSAGES['api_not_configured']['vi'])
                msg += f"\n\n💰 Hoàn: +10 cash"
                send_telegram_message(chat_id, msg)
                # Update job status to failed
                update_sheerid_bot_job_status(job_id, 'failed', error_message='API not configured')
                return
            
            # Get webhook URL from environment
            webhook_url = os.getenv('SHEERID_BOT_WEBHOOK_URL')
            
            # Submit verification
            result = client.submit_verification(
                url=url,
                verification_type=verify_type,
                webhook_url=webhook_url
            )
            
            api_job_id = result.get('job_id')
            status = result.get('status', 'pending')
            estimated_time = result.get('estimated_time', 120)
            
            # Update local job with API job_id
            update_sheerid_bot_job_api_id(job_id, api_job_id)
            
            # Don't send api_submitted message to hide API details from users
            # The job_created message already informed user that request is being processed
            
            print(f"✅ Verification submitted: job_id={job_id}, type={verify_type}")
            
        except SheerIDAPIError as e:
            # Handle specific API errors - Requirements: 4.1-4.5
            error_code = e.code
            error_msg = str(e)
            
            print(f"❌ Verification error: {error_code} - {error_msg}")
            
            # Update job status
            update_sheerid_bot_job_status(job_id, 'failed', error_message=error_msg)
            
            # REFUND the upfront payment since verification failed
            try:
                if SUPABASE_AVAILABLE:
                    from supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    if supabase:
                        print(f"🔍 DEBUG REFUND: Attempting to refund 10 cash to user_id={user_id}")
                        # Get current cash - query by database ID, not telegram_id
                        user_result = supabase.table('users').select('cash, telegram_id').eq('id', user_id).execute()
                        if user_result.data:
                            current_cash = user_result.data[0].get('cash', 0)
                            telegram_id_for_log = user_result.data[0].get('telegram_id', 'unknown')
                            new_cash = current_cash + 10
                            update_result = supabase.table('users').update({'cash': new_cash}).eq('id', user_id).execute()
                            print(f"💰 REFUND SUCCESS: Returned 10 cash to user_id={user_id} (telegram_id={telegram_id_for_log}) due to API error. Old balance: {current_cash}, New balance: {new_cash}")
                            print(f"🔍 DEBUG REFUND: Update result: {update_result.data}")
                        else:
                            print(f"❌ REFUND FAILED: User {user_id} not found in database")
            except Exception as refund_error:
                print(f"❌ Error refunding cash: {refund_error}")
                import traceback
                traceback.print_exc()
            
            # Send appropriate error message based on error code
            if error_code == 'INVALID_API_KEY':
                # Log and notify admin
                print(f"🚨 CRITICAL: Invalid SheerID Bot API key!")
                msg = SHEERID_BOT_MESSAGES['api_not_configured'].get(user_lang, SHEERID_BOT_MESSAGES['api_not_configured']['vi'])
            elif error_code == 'INSUFFICIENT_CREDITS':
                msg = SHEERID_BOT_MESSAGES['api_insufficient_credits'].get(user_lang, SHEERID_BOT_MESSAGES['api_insufficient_credits']['vi'])
            elif error_code == 'RATE_LIMITED':
                msg = SHEERID_BOT_MESSAGES['api_rate_limited'].get(user_lang, SHEERID_BOT_MESSAGES['api_rate_limited']['vi'])
            elif error_code == 'MAINTENANCE_MODE':
                msg = SHEERID_BOT_MESSAGES['api_maintenance'].get(user_lang, SHEERID_BOT_MESSAGES['api_maintenance']['vi'])
            else:
                # Use generic error message without including raw error (may contain HTML)
                msg = SHEERID_BOT_MESSAGES['api_error'].get(user_lang, SHEERID_BOT_MESSAGES['api_error']['vi'])
                msg = msg.format(error="Vui lòng thử lại sau")
            
            # Add refund info to error message
            msg += f"\n\n💰 Hoàn: +10 cash"
            
            # Use plain text to avoid Markdown parsing issues
            send_telegram_message_plain(chat_id, msg)
            
        except Exception as e:
            print(f"❌ Unexpected error in handle_sheerid_verification: {e}")
            
            # REFUND the upfront payment since verification failed
            try:
                if SUPABASE_AVAILABLE:
                    from supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    if supabase:
                        print(f"🔍 DEBUG REFUND: Attempting to refund 10 cash to user_id={user_id}")
                        # Get current cash - query by database ID, not telegram_id
                        user_result = supabase.table('users').select('cash, telegram_id').eq('id', user_id).execute()
                        if user_result.data:
                            current_cash = user_result.data[0].get('cash', 0)
                            telegram_id_for_log = user_result.data[0].get('telegram_id', 'unknown')
                            new_cash = current_cash + 10
                            update_result = supabase.table('users').update({'cash': new_cash}).eq('id', user_id).execute()
                            print(f"💰 REFUND SUCCESS: Returned 10 cash to user_id={user_id} (telegram_id={telegram_id_for_log}) due to unexpected error. Old balance: {current_cash}, New balance: {new_cash}")
                            print(f"🔍 DEBUG REFUND: Update result: {update_result.data}")
                        else:
                            print(f"❌ REFUND FAILED: User {user_id} not found in database")
            except Exception as refund_error:
                print(f"❌ Error refunding cash: {refund_error}")
                import traceback
                traceback.print_exc()
            
            # Send error message with refund info
            error_msgs = {
                'vi': f"❌ Lỗi không mong đợi!\n\n💰 Hoàn: +10 cash\n\n💡 Vui lòng thử lại sau.",
                'en': f"❌ Unexpected error!\n\n💰 Refunded: +10 cash\n\n💡 Please try again later.",
                'zh': f"❌ 意外错误！\n\n💰 已退款：+10 现金\n\n💡 请稍后重试。"
            }
            send_telegram_message(chat_id, error_msgs.get(user_lang, error_msgs['vi']))
            import traceback
            traceback.print_exc()
            
            # Update job status
            update_sheerid_bot_job_status(job_id, 'failed', error_message=str(e))
            
            # Use generic error message to avoid exposing internal errors
            msg = SHEERID_BOT_MESSAGES['api_error'].get(user_lang, SHEERID_BOT_MESSAGES['api_error']['vi'])
            send_telegram_message_plain(chat_id, msg.format(error="Vui lòng thử lại sau"))
            
    except Exception as e:
        print(f"❌ Error in handle_sheerid_verification: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")


def create_sheerid_bot_job(user_id, telegram_id, sheerid_url, verification_type, cost, payment_method='cash'):
    """
    Create a new SheerID Bot API job in the database
    
    Requirements: 1.2, 2.2, 3.2
    """
    job_id = str(uuid.uuid4())
    print(f"DEBUG: Creating SheerID Bot job - user_id: {user_id}, job_id: {job_id}, type: {verification_type}, cost: {cost}, payment: {payment_method}")
    
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        if supabase:
            # Insert into sheerid_bot_jobs table
            data = {
                'user_id': user_id,
                'telegram_id': telegram_id,
                'job_id': job_id,
                'verification_type': verification_type,
                'sheerid_url': sheerid_url,
                'status': 'pending',
                'cost': cost,
                'payment_method': payment_method
            }
            
            result = supabase.table('sheerid_bot_jobs').insert(data).execute()
            
            if result.data:
                print(f"✅ Created SheerID Bot job in Supabase: {job_id} (payment: {payment_method})")
                return job_id
            else:
                print(f"❌ Failed to create SheerID Bot job in Supabase")
                return None
        else:
            print(f"❌ Supabase client not available")
            return None
            
    except Exception as e:
        print(f"❌ Error creating SheerID Bot job: {e}")
        import traceback
        traceback.print_exc()
        return None


def update_sheerid_bot_job_status(job_id, status, error_message=None, result_details=None):
    """
    Update SheerID Bot job status in database
    
    Requirements: 5.2, 5.3
    """
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        if supabase:
            update_data = {
                'status': status,
                'updated_at': 'now()'
            }
            
            if status in ['success', 'failed']:
                update_data['completed_at'] = 'now()'
            
            if error_message:
                update_data['result_details'] = {'error': error_message}
            elif result_details:
                update_data['result_details'] = result_details
            
            supabase.table('sheerid_bot_jobs').update(update_data).eq('job_id', job_id).execute()
            print(f"✅ Updated SheerID Bot job status: {job_id} -> {status}")
            return True
            
    except Exception as e:
        print(f"❌ Error updating SheerID Bot job status: {e}")
    
    return False


def update_sheerid_bot_job_api_id(job_id, api_job_id):
    """
    Update SheerID Bot job with API job ID
    """
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        if supabase:
            # Store API job_id in result_details
            supabase.table('sheerid_bot_jobs').update({
                'result_details': {'api_job_id': api_job_id},
                'status': 'processing',
                'updated_at': 'now()'
            }).eq('job_id', job_id).execute()
            print(f"✅ Updated SheerID Bot job with API ID: {job_id} -> {api_job_id}")
            return True
            
    except Exception as e:
        print(f"❌ Error updating SheerID Bot job API ID: {e}")
    
    return False


def get_sheerid_bot_job(job_id):
    """
    Get SheerID Bot job by job_id
    """
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        if supabase:
            result = supabase.table('sheerid_bot_jobs').select('*').eq('job_id', job_id).execute()
            if result.data:
                return result.data[0]
            
    except Exception as e:
        print(f"❌ Error getting SheerID Bot job: {e}")
    
    return None


def handle_verify_batch_command(chat_id, user, text):
    """
    Handle batch verify command: /verify3 or /verify5
    Allows VIP Pro/Business users to submit multiple links at once
    
    Usage:
    /verify3 link1 link2 link3
    /verify5 link1 link2 link3 link4 link5
    """
    import threading
    
    try:
        # Determine batch size from command
        if text.startswith('/verify5'):
            batch_size = 5
            links_text = text.replace('/verify5', '').strip()
        else:  # /verify3
            batch_size = 3
            links_text = text.replace('/verify3', '').strip()
        
        # Get user info
        telegram_id = user.get('telegram_id') if isinstance(user, dict) else user[1] if user and len(user) > 1 else None
        user_id = user.get('id') if isinstance(user, dict) else user[0] if user else None
        
        # Get user language
        user_lang = DEFAULT_LANGUAGE
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase and telegram_id:
                user_lang = get_user_language(supabase, telegram_id)
        except:
            pass
        
        # Check VIP status
        vip_active = False
        concurrent_limit = 1
        
        if isinstance(user, dict):
            is_vip = user.get('is_vip', False)
            vip_expiry = user.get('vip_expiry')
            concurrent_limit = user.get('concurrent_links', 1) or 1
            
            if is_vip and vip_expiry:
                try:
                    from datetime import datetime
                    import pytz
                    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
                    expiry_dt = datetime.fromisoformat(vip_expiry.replace('Z', '+00:00'))
                    vip_active = expiry_dt > datetime.now(expiry_dt.tzinfo)
                except:
                    vip_active = is_vip
            else:
                vip_active = is_vip
        
        # Check if user has VIP with enough concurrent slots
        if not vip_active:
            no_vip_msgs = {
                'vi': f"❌ Lệnh /verify{batch_size} chỉ dành cho VIP!\n\n💡 Mua gói VIP để sử dụng:\n• VIP Pro (3 link): /mua vippro7\n• VIP Business (5 link): /mua vipbiz7",
                'en': f"❌ /verify{batch_size} command is VIP only!\n\n💡 Buy VIP package to use:\n• VIP Pro (3 links): /mua vippro7\n• VIP Business (5 links): /mua vipbiz7",
                'zh': f"❌ /verify{batch_size} 命令仅限VIP用户！\n\n💡 购买VIP套餐使用：\n• VIP Pro (3链接): /mua vippro7\n• VIP Business (5链接): /mua vipbiz7"
            }
            send_telegram_message(chat_id, no_vip_msgs.get(user_lang, no_vip_msgs['vi']))
            return
        
        if concurrent_limit < batch_size:
            upgrade_msgs = {
                'vi': f"❌ Gói VIP của bạn chỉ hỗ trợ {concurrent_limit} link song song.\n\n💡 Nâng cấp để dùng /verify{batch_size}:\n• VIP Pro (3 link): /mua vippro7\n• VIP Business (5 link): /mua vipbiz7",
                'en': f"❌ Your VIP package only supports {concurrent_limit} parallel links.\n\n💡 Upgrade to use /verify{batch_size}:\n• VIP Pro (3 links): /mua vippro7\n• VIP Business (5 links): /mua vipbiz7",
                'zh': f"❌ 您的VIP套餐仅支持 {concurrent_limit} 个并行链接。\n\n💡 升级以使用 /verify{batch_size}：\n• VIP Pro (3链接): /mua vippro7\n• VIP Business (5链接): /mua vipbiz7"
            }
            send_telegram_message(chat_id, upgrade_msgs.get(user_lang, upgrade_msgs['vi']))
            return
        
        # Parse links - support multiple formats: space, newline, comma separated
        import re
        # Find all SheerID URLs
        url_pattern = r'https?://services\.sheerid\.com/verify/[^\s,]+'
        links = re.findall(url_pattern, links_text)
        
        if not links:
            usage_msgs = {
                'vi': f"❌ Không tìm thấy link SheerID!\n\n📝 Cách dùng:\n/verify{batch_size} link1 link2 link3\n\nHoặc mỗi link một dòng:\n/verify{batch_size}\nhttps://services.sheerid.com/verify/xxx\nhttps://services.sheerid.com/verify/yyy\nhttps://services.sheerid.com/verify/zzz",
                'en': f"❌ No SheerID links found!\n\n📝 Usage:\n/verify{batch_size} link1 link2 link3\n\nOr one link per line:\n/verify{batch_size}\nhttps://services.sheerid.com/verify/xxx\nhttps://services.sheerid.com/verify/yyy\nhttps://services.sheerid.com/verify/zzz",
                'zh': f"❌ 未找到SheerID链接！\n\n📝 用法：\n/verify{batch_size} link1 link2 link3\n\n或每行一个链接：\n/verify{batch_size}\nhttps://services.sheerid.com/verify/xxx\nhttps://services.sheerid.com/verify/yyy\nhttps://services.sheerid.com/verify/zzz"
            }
            send_telegram_message(chat_id, usage_msgs.get(user_lang, usage_msgs['vi']))
            return
        
        # Limit to batch_size
        links = links[:batch_size]
        
        if len(links) < 2:
            single_link_msgs = {
                'vi': f"💡 Chỉ có 1 link? Dùng /verify {links[0]} thay vì /verify{batch_size}",
                'en': f"💡 Only 1 link? Use /verify {links[0]} instead of /verify{batch_size}",
                'zh': f"💡 只有1个链接？使用 /verify {links[0]} 而不是 /verify{batch_size}"
            }
            send_telegram_message(chat_id, single_link_msgs.get(user_lang, single_link_msgs['vi']))
            return
        
        # Check available slots
        try:
            from .vip_tiers import can_start_verification, get_user_active_count
            active_count = get_user_active_count(str(telegram_id))
            slots_available = concurrent_limit - active_count
            
            if slots_available < len(links):
                not_enough_slots_msgs = {
                    'vi': f"⚠️ Bạn chỉ còn {slots_available}/{concurrent_limit} slot trống.\n\n🔗 Đang chạy: {active_count} link\n📝 Yêu cầu: {len(links)} link\n\n💡 Vui lòng chờ các job hiện tại hoàn thành hoặc gửi ít link hơn.",
                    'en': f"⚠️ You only have {slots_available}/{concurrent_limit} slots available.\n\n🔗 Running: {active_count} links\n📝 Requested: {len(links)} links\n\n💡 Please wait for current jobs to complete or submit fewer links.",
                    'zh': f"⚠️ 您只有 {slots_available}/{concurrent_limit} 个可用槽位。\n\n🔗 正在运行：{active_count} 个链接\n📝 请求：{len(links)} 个链接\n\n💡 请等待当前任务完成或提交更少的链接。"
                }
                send_telegram_message(chat_id, not_enough_slots_msgs.get(user_lang, not_enough_slots_msgs['vi']))
                return
        except ImportError:
            pass
        
        # Send confirmation message
        links_preview = '\n'.join([f"  {i+1}. ...{link[-30:]}" for i, link in enumerate(links)])
        confirm_msgs = {
            'vi': f"🚀 Bắt đầu verify {len(links)} link song song!\n\n📋 Danh sách:\n{links_preview}\n\n⏳ Mỗi link sẽ mất 2-5 phút...",
            'en': f"🚀 Starting parallel verification of {len(links)} links!\n\n📋 List:\n{links_preview}\n\n⏳ Each link takes 2-5 minutes...",
            'zh': f"🚀 开始并行验证 {len(links)} 个链接！\n\n📋 列表：\n{links_preview}\n\n⏳ 每个链接需要2-5分钟..."
        }
        send_telegram_message(chat_id, confirm_msgs.get(user_lang, confirm_msgs['vi']))
        
        # Process each link in parallel using threads
        def process_single_link(link, index):
            """Process a single link - calls handle_verify_command logic"""
            try:
                # Create a fake text command for the existing handler
                fake_text = f"/verify {link}"
                handle_verify_command(chat_id, user, fake_text)
            except Exception as e:
                error_msgs = {
                    'vi': f"❌ Link {index+1} lỗi: {str(e)[:50]}",
                    'en': f"❌ Link {index+1} error: {str(e)[:50]}",
                    'zh': f"❌ 链接 {index+1} 错误：{str(e)[:50]}"
                }
                send_telegram_message(chat_id, error_msgs.get(user_lang, error_msgs['vi']))
        
        # Start threads for each link
        threads = []
        for i, link in enumerate(links):
            t = threading.Thread(target=process_single_link, args=(link, i))
            t.start()
            threads.append(t)
            # Small delay between starts to avoid rate limiting
            import time
            time.sleep(0.5)
        
        # Don't wait for threads - they run in background
        
    except Exception as e:
        print(f"❌ Error in handle_verify_batch_command: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)[:100]}")


def handle_verify_command(chat_id, user, text):
    """Handle verify command"""
    try:
        # Check VERIFY-specific maintenance mode (ONLY verify_maintenance, NOT maintenance_mode or vc_maintenance)
        verify_maintenance = BOT_CONFIG.get('verify_maintenance', False)
        env_verify_maintenance = os.environ.get('VERIFY_MAINTENANCE', 'false').lower() == 'true'
        
        # IMPORTANT: Do NOT check maintenance_mode here - /verify is independent from /vc
        is_verify_maintenance = verify_maintenance or env_verify_maintenance
        
        print(f"🔍 DEBUG handle_verify: verify_maintenance = {is_verify_maintenance}")
        if is_verify_maintenance:
            # Allow admin to bypass maintenance
            if chat_id not in ADMIN_TELEGRAM_IDS:
                maintenance_msg = BOT_CONFIG.get('maintenance_message', 
                    "🔧 Chức năng /verify đang bảo trì.\n\n"
                    "Vui lòng thử lại sau. Cảm ơn bạn!")
                send_telegram_message(chat_id, maintenance_msg, parse_mode=None)
                return
            else:
                print(f"✅ Admin {chat_id} bypassing VERIFY maintenance mode")
        
        # Get user language
        telegram_id = user.get('telegram_id') if isinstance(user, dict) else user[1] if user and len(user) > 1 else None
        user_lang = DEFAULT_LANGUAGE
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase and telegram_id:
                user_lang = get_user_language(supabase, telegram_id)
        except:
            pass
        
        # Extract URL from /verify (remove support for /verifycash)
        url = text.replace('/verify', '').strip()
        print(f"DEBUG: Original text: {text}")
        print(f"DEBUG: Extracted URL: {url}")
        
        # Multilingual messages for verify command
        verify_msgs = {
            'no_url': {
                'vi': '❌ Vui lòng cung cấp URL SheerID\n\nVí dụ: /verify https://services.sheerid.com/verify/...',
                'en': '❌ Please provide SheerID URL\n\nExample: /verify https://services.sheerid.com/verify/...',
                'zh': '❌ 请提供 SheerID URL\n\n示例：/verify https://services.sheerid.com/verify/...'
            },
            'invalid_url': {
                'vi': '❌ URL không đúng định dạng SheerID!\n\n✅ URL hợp lệ: https://services.sheerid.com/verify/...\n❌ URL không hợp lệ: https://example.com/...',
                'en': '❌ Invalid SheerID URL format!\n\n✅ Valid URL: https://services.sheerid.com/verify/...\n❌ Invalid URL: https://example.com/...',
                'zh': '❌ SheerID URL 格式无效！\n\n✅ 有效URL：https://services.sheerid.com/verify/...\n❌ 无效URL：https://example.com/...'
            }
        }
        
        if not url:
            send_telegram_message(chat_id, verify_msgs['no_url'].get(user_lang, verify_msgs['no_url']['vi']))
            return
        
        # Validate URL format
        if not validate_sheerid_url(url):
            send_telegram_message(chat_id, verify_msgs['invalid_url'].get(user_lang, verify_msgs['invalid_url']['vi']))
            return
        
        # Validate verificationId exists via SheerID API
        is_valid, error_msg, verification_data = validate_sheerid_verification_exists(url)
        if not is_valid:
            # Show specific error message if available, otherwise generic message
            if error_msg:
                send_telegram_message(chat_id, error_msg)
            else:
                reject_msgs = {
                    'vi': "❌ Link SheerID không hợp lệ!\n\n💡 Vui lòng lấy link khác hợp lệ.",
                    'en': "❌ Invalid SheerID link!\n\n💡 Please get another valid link.",
                    'zh': "❌ SheerID 链接无效！\n\n💡 请获取另一个有效链接。"
                }
                send_telegram_message(chat_id, reject_msgs.get(user_lang, reject_msgs['vi']))
            return
        
        # Check if verification already completed (success)
        if verification_data and verification_data.get('currentStep') == 'success':
            already_verified_msgs = {
                'vi': "✅ Link này đã được verify thành công rồi!\n\n💡 Không cần chạy verification nữa.",
                'en': "✅ This link has already been verified successfully!\n\n💡 No need to run verification again.",
                'zh': "✅ 此链接已成功验证！\n\n💡 无需再次运行验证。"
            }
            send_telegram_message(chat_id, already_verified_msgs.get(user_lang, already_verified_msgs['vi']))
            return
        
        # Check if verification is in docUpload state (needs to be fixed)
        if verification_data and verification_data.get('currentStep') == 'docUpload':
            current_step = verification_data.get('currentStep', 'docUpload')
            docupload_msgs = {
                'vi': f"⚠️ Link của bạn đang ở trạng thái: {current_step}\n\n💡 Vui lòng dùng lệnh:\n/fix {url}\n\nđể giới hạn link, sau đó quay lại trang reload để lấy link mới.\n\nRồi quay lại bot /verify (link_mới)",
                'en': f"⚠️ Your link is in state: {current_step}\n\n💡 Please use command:\n/fix {url}\n\nto limit the link, then go back to the page and reload to get a new link.\n\nThen come back to bot /verify (new_link)",
                'zh': f"⚠️ 您的链接处于状态：{current_step}\n\n💡 请使用命令：\n/fix {url}\n\n来限制链接，然后返回页面刷新获取新链接。\n\n然后回到机器人 /verify (新链接)"
            }
            send_telegram_message(chat_id, docupload_msgs.get(user_lang, docupload_msgs['vi']))
            return
        
        # Check if verification is in pending state (already submitted, waiting for review)
        if verification_data and verification_data.get('currentStep') == 'pending':
            awaiting_step = verification_data.get('awaitingStep', '').lower()
            rejection_reasons = verification_data.get('rejectionReasons', [])
            
            # If pending with docupload awaiting or has rejection reasons - link was already used
            if awaiting_step == 'docupload' or rejection_reasons:
                rejection_msg = ', '.join(rejection_reasons) if rejection_reasons else ''
                pending_used_msgs = {
                    'vi': f"⚠️ Link này đã được sử dụng trước đó và đang chờ xử lý.\n\n📋 Trạng thái: pending (awaitingStep: {awaiting_step})\n{f'❌ Lý do từ chối: {rejection_msg}' if rejection_msg else ''}\n\n💡 Vui lòng dùng lệnh:\n/fix {url}\n\nđể giới hạn link, sau đó quay lại trang reload để lấy link mới.",
                    'en': f"⚠️ This link has already been used and is pending review.\n\n📋 Status: pending (awaitingStep: {awaiting_step})\n{f'❌ Rejection reason: {rejection_msg}' if rejection_msg else ''}\n\n💡 Please use command:\n/fix {url}\n\nto limit the link, then go back to the page and reload to get a new link.",
                    'zh': f"⚠️ 此链接已被使用，正在等待审核。\n\n📋 状态：pending (awaitingStep: {awaiting_step})\n{f'❌ 拒绝原因：{rejection_msg}' if rejection_msg else ''}\n\n💡 请使用命令：\n/fix {url}\n\n来限制链接，然后返回页面刷新获取新链接。"
                }
                send_telegram_message(chat_id, pending_used_msgs.get(user_lang, pending_used_msgs['vi']))
                return
            else:
                # Pure pending state - link is being reviewed
                pending_msgs = {
                    'vi': f"⏳ Link này đang trong trạng thái chờ xử lý (pending).\n\n💡 Vui lòng đợi hoặc lấy link mới nếu đã chờ quá lâu.",
                    'en': f"⏳ This link is currently pending review.\n\n💡 Please wait or get a new link if you've been waiting too long.",
                    'zh': f"⏳ 此链接正在等待审核中。\n\n💡 请等待，或者如果等待时间过长，请获取新链接。"
                }
                send_telegram_message(chat_id, pending_msgs.get(user_lang, pending_msgs['vi']))
                return
        
        # Send initial notification (multilingual) - IMPORTANT: Must use US VPN when creating link
        initial_msgs = {
            'vi': '⚠️ QUAN TRỌNG: Bạn PHẢI dùng VPN US khi tạo link xác minh để tránh bị từ chối.\n\n⏰ Quá trình verify có thể mất 2-5 phút, vui lòng đợi.',
            'en': '⚠️ IMPORTANT: You MUST use US VPN when creating verification link to avoid rejection.\n\n⏰ Verification process may take 2-5 minutes, please wait.',
            'zh': '⚠️ 重要：创建验证链接时必须使用美国VPN，否则会被拒绝。\n\n⏰ 验证过程可能需要 2-5 分钟，请耐心等待。'
        }
        
        send_telegram_message(chat_id, initial_msgs.get(user_lang, initial_msgs['vi']), parse_mode=None)
        
        # Get user_id for checking existing jobs
        if isinstance(user, dict):
            user_id = user.get('id', 0)
        else:
            user_id = user[0]

        # Daily success limit: allow max 5 successful verifies per day FOR COIN-BASED verifies only (non-VIP users)
        try:
            from datetime import datetime
            today = format_vietnam_time('%Y-%m-%d')
            verify_count_today = 0
            # Determine if this attempt is likely coin-based (coins >= 2) or will fall back to cash
            will_use_coins = False
            try:
                wallets_preview = supabase_get_wallets_by_user_id(user_id)
                if wallets_preview:
                    _, coins_preview = wallets_preview
                    will_use_coins = coins_preview >= 2
            except Exception:
                will_use_coins = False
            
            # Only check daily limit for non-VIP users
            if not vip_active and SUPABASE_AVAILABLE:
                try:
                    from supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    if supabase:
                        # Count from verification_jobs completed today
                        resp = (
                            supabase
                            .table('verification_jobs')
                            .select('id', count='exact')
                            .eq('user_id', user_id)
                            .in_('status', ['completed','success'])
                            .gte('created_at', f"{today} 00:00:00")
                            .lte('created_at', f"{today} 23:59:59")
                            .execute()
                        )
                        verify_count_today = int(getattr(resp, 'count', 0) or 0)
                except Exception:
                    verify_count_today = 0
            if verify_count_today == 0 and not vip_active:
                # Fallback to SQLite if Supabase not available or count failed (only for non-VIP users)
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT COUNT(*) FROM verification_jobs 
                        WHERE user_id = ? AND status IN ('completed','success') AND DATE(created_at) = ?
                    ''', (user_id, today))
                    verify_count_today = (cursor.fetchone() or [0])[0]
                    conn.close()
                except Exception:
                    pass
            # Determine if daily coin quota exceeded (only for non-VIP users)
            force_cash_due_to_quota = (not vip_active) and (verify_count_today >= 2)
            # If quota 5 lần bằng Xu đã hết, không chặn – tiếp tục và ép dùng CASH ở bước trừ tiền
        except Exception:
            # Soft-fail rate limit if any unexpected error
            pass
        
        # Check if user already has a pending verification job (only recent ones)
        # VIP Pro users with concurrent_links > 1 can have multiple pending jobs
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                from datetime import datetime, timedelta
                supabase = get_supabase_client()
                if supabase:
                    # Get user's concurrent_links limit (default 1 for non-VIP)
                    concurrent_limit = 1
                    if isinstance(user, dict):
                        concurrent_limit = user.get('concurrent_links', 1) or 1
                    
                    # Only check jobs from last 24 hours to avoid old stuck jobs
                    yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
                    existing_jobs = supabase.table('verification_jobs').select('id, status, created_at').eq('user_id', user_id).eq('status', 'pending').gte('created_at', yesterday).execute()
                    
                    # Allow up to concurrent_limit pending jobs
                    pending_count = len(existing_jobs.data) if existing_jobs.data else 0
                    if pending_count >= concurrent_limit:
                        job_info = existing_jobs.data[0]
                        created_at = job_info.get('created_at', '')
                        pending_msgs = {
                            'vi': f"❌ Bạn đã có {pending_count} job verify đang chờ xử lý (tối đa {concurrent_limit})!\n\n⏳ Job ID: `{job_info.get('id')}`\n📅 Tạo lúc: {created_at[:19] if created_at else 'N/A'}\n\n🔄 Vui lòng chờ job hiện tại hoàn thành trước khi tạo job mới.\n\n💡 Nếu job quá cũ, bạn có thể dùng /cancel để hủy.",
                            'en': f"❌ You already have {pending_count} pending verification job(s) (max {concurrent_limit})!\n\n⏳ Job ID: `{job_info.get('id')}`\n📅 Created: {created_at[:19] if created_at else 'N/A'}\n\n🔄 Please wait for the current job to complete before creating a new one.\n\n💡 If the job is too old, you can use /cancel to cancel it.",
                            'zh': f"❌ 您已有 {pending_count} 个待处理的验证任务（最多 {concurrent_limit}）！\n\n⏳ 任务ID: `{job_info.get('id')}`\n📅 创建时间: {created_at[:19] if created_at else 'N/A'}\n\n🔄 请等待当前任务完成后再创建新任务。\n\n💡 如果任务太旧，您可以使用 /cancel 取消它。"
                        }
                        send_telegram_message(chat_id, pending_msgs.get(user_lang, pending_msgs['vi']))
                        return
            except Exception as e:
                print(f"Error checking existing jobs: {e}")
        
        # Check wallets/eligibility and daily limits
        vip_active = is_vip_active(user)
        cash_verify_limit = None  # Default: no limit (None = unlimited)
        if isinstance(user, dict):
            wallets = supabase_get_wallets_by_user_id(user.get('id'))
            cash = wallets[0] if wallets else int(user.get('cash') or 0)
            bonus = wallets[1] if wallets else int(user.get('coins') or 0)
            cash_verify_limit = user.get('cash_verify_limit')  # None = unlimited
        else:
            # For tuple users, try to fetch wallets from Supabase for accurate balances
            wallets = supabase_get_wallets_by_user_id(user[0])
            if wallets:
                cash, bonus = wallets[0], wallets[1]
            else:
                # Fallback to legacy tuple layout if no wallets available
                cash = user[5]
                bonus = 0
            # Try to get cash_verify_limit from Supabase
            try:
                if SUPABASE_AVAILABLE:
                    from supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    if supabase:
                        user_resp = supabase.table('users').select('cash_verify_limit').eq('id', user[0]).execute()
                        if user_resp.data:
                            cash_verify_limit = user_resp.data[0].get('cash_verify_limit')
            except Exception:
                pass
        
        verify_cost = 10  # Student verification cost: 10 xu/cash
        
        # Determine payment method based on VIP status and daily limits
        if vip_active:
            # VIP: FREE student verification - no payment required!
            can_pay = True  # VIP always can verify for free
            payment_method = "free"
            
            # Check concurrent link limit for VIP users
            try:
                from .vip_tiers import can_start_verification, get_user_concurrent_limit
                can_start, limit_msg, slots_available = can_start_verification(telegram_id, user)
                concurrent_limit = get_user_concurrent_limit(user)
                
                if not can_start:
                    send_telegram_message(chat_id, limit_msg)
                    return
                
                # Show slots info in fee text
                if concurrent_limit > 1:
                    fee_text = f"MIỄN PHÍ (⭐ VIP | 🔗 {slots_available}/{concurrent_limit} slot)"
                else:
                    fee_text = "MIỄN PHÍ (⭐ VIP)"
            except ImportError:
                fee_text = "MIỄN PHÍ (⭐ VIP)"
            except Exception as e:
                print(f"⚠️ Error checking concurrent limit: {e}")
                fee_text = "MIỄN PHÍ (⭐ VIP)"
            
            print(f"⭐ VIP user {telegram_id} - FREE student verification!")
        else:
            # Regular user: COINS + CASH VERIFICATION (25 xu or 10 cash)
            try:
                # Check if user has unlocked coins verify
                if isinstance(user, dict):
                    coins_verify_unlocked = user.get('coins_verify_unlocked', False)
                    total_cash_spent = user.get('total_cash_spent', 0)
                else:
                    # For tuple users, fetch from Supabase
                    coins_verify_unlocked = False
                    total_cash_spent = 0
                    try:
                        if SUPABASE_AVAILABLE:
                            from supabase_client import get_supabase_client
                            supabase = get_supabase_client()
                            if supabase:
                                user_resp = supabase.table('users').select('coins_verify_unlocked', 'total_cash_spent').eq('id', user[0]).execute()
                                if user_resp.data:
                                    coins_verify_unlocked = user_resp.data[0].get('coins_verify_unlocked', False)
                                    total_cash_spent = user_resp.data[0].get('total_cash_spent', 0)
                    except Exception as e:
                        print(f"⚠️ Error fetching coins_verify_unlocked for tuple user: {e}")
                
                # Auto-unlock if conditions met (first deposit OR spent >= 30 cash)
                if not coins_verify_unlocked:
                    if cash > 10 or total_cash_spent >= 30:
                        coins_verify_unlocked = True
                        # Update database
                        try:
                            if SUPABASE_AVAILABLE:
                                from supabase_client import get_supabase_client
                                supabase = get_supabase_client()
                                if supabase:
                                    supabase.table('users').update({'coins_verify_unlocked': True}).eq('id', user_id).execute()
                                    print(f"✅ Auto-unlocked coins verify for user {user_id}")
                        except Exception as e:
                            print(f"⚠️ Failed to auto-unlock: {e}")
                
                # Count coins verifications today (for 3/day limit)
                coins_verify_count_today = 0
                if coins_verify_unlocked and SUPABASE_AVAILABLE:
                    try:
                        from supabase_client import get_supabase_client
                        from datetime import datetime, timezone, timedelta
                        supabase = get_supabase_client()
                        if supabase:
                            # Use Vietnam timezone (UTC+7)
                            vietnam_tz = timezone(timedelta(hours=7))
                            now_vn = datetime.now(vietnam_tz)
                            today_start = now_vn.replace(hour=0, minute=0, second=0, microsecond=0)
                            today_end = now_vn.replace(hour=23, minute=59, second=59, microsecond=999999)
                            
                            # Count COINS verifications today (payment_method = 'coins')
                            # Count both pending and completed to prevent spam abuse
                            coins_resp = (
                                supabase
                                .table('sheerid_bot_jobs')
                                .select('id', count='exact')
                                .eq('user_id', user_id)
                                .in_('status', ['pending', 'completed'])
                                .eq('payment_method', 'coins')
                                .gte('created_at', today_start.isoformat())
                                .lte('created_at', today_end.isoformat())
                                .execute()
                            )
                            coins_verify_count_today = int(getattr(coins_resp, 'count', 0) or 0)
                            print(f"🔍 DEBUG: User {user_id} coins verifications today (pending+completed): {coins_verify_count_today}/3")
                    except Exception as e:
                        print(f"DEBUG: Error counting coins verifications: {e}")
                        coins_verify_count_today = 0
                
                # Determine payment method
                verify_cost_cash = 10  # Cash cost
                verify_cost_coins = 25  # Coins cost
                coins_daily_limit = 3  # Max 3 coins verifications per day
                
                # Check if can use coins (unlocked + enough coins + under daily limit)
                coins_under_limit = coins_verify_count_today < coins_daily_limit
                can_use_coins = coins_verify_unlocked and (bonus >= verify_cost_coins) and coins_under_limit
                can_use_cash = cash >= verify_cost_cash
                
                print(f"🔍 DEBUG PAYMENT: user={user_id}, coins_unlocked={coins_verify_unlocked}, bonus={bonus}, cash={cash}, coins_today={coins_verify_count_today}/3")
                
                if can_use_coins:
                    # Prefer coins if unlocked, available, and under limit
                    payment_method = "coins"
                    fee_text = f"25 Xu (🔓 {coins_verify_count_today}/3 hôm nay)"
                    print(f"✅ Will use COINS: 25 xu")
                elif can_use_cash:
                    # Fallback to cash
                    payment_method = "cash"
                    fee_text = f"10 Cash"
                    print(f"✅ Will use CASH: 10 cash")
                else:
                    # Cannot verify - show appropriate message
                    if not coins_verify_unlocked:
                        # Show unlock requirements
                        unlock_msgs = {
                            'vi': f"🔒 Verify bằng Xu chưa mở khóa!\n\n💰 Để mở khóa verify bằng 25 Xu (tối đa 3 lần/ngày), bạn cần:\n✅ Nạp tiền lần đầu (hiện tại: {cash} cash)\n   HOẶC\n✅ Chi tiêu >= 30 cash (đã chi: {total_cash_spent} cash)\n\n💡 Sau khi mở khóa, bạn có thể verify bằng 25 Xu thay vì 10 Cash!\n\n📌 Hiện tại bạn có thể:\n💵 Verify bằng 10 Cash (dùng /verify)\n💳 Nạp tiền: /nap hoặc /crypto",
                            'en': f"🔒 Coins verify not unlocked!\n\n💰 To unlock 25 Xu verify (max 3 times/day), you need:\n✅ Make first deposit (current: {cash} cash)\n   OR\n✅ Spend >= 30 cash (spent: {total_cash_spent} cash)\n\n💡 After unlock, you can verify with 25 Xu instead of 10 Cash!\n\n📌 Currently you can:\n💵 Verify with 10 Cash (use /verify)\n💳 Deposit: /nap or /crypto",
                            'zh': f"🔒 硬币验证未解锁！\n\n💰 要解锁 25 硬币验证（每天最多3次），您需要：\n✅ 首次充值（当前：{cash} 现金）\n   或\n✅ 消费 >= 30 现金（已消费：{total_cash_spent} 现金）\n\n💡 解锁后，您可以用 25 硬币代替 10 现金验证！\n\n📌 目前您可以：\n💵 用 10 现金验证（使用 /verify）\n💳 充值：/nap 或 /crypto"
                        }
                        send_telegram_message(chat_id, unlock_msgs.get(user_lang, unlock_msgs['vi']))
                        return
                    elif coins_verify_unlocked and not coins_under_limit:
                        # Unlocked but exceeded daily coins limit
                        quota_msgs = {
                            'vi': f"🚫 Bạn đã hết quota verify bằng Xu hôm nay!\n\n💰 Xu: {bonus}\n📊 Đã verify bằng Xu: {coins_verify_count_today}/{coins_daily_limit}\n\n💡 Bạn có thể:\n✅ Verify bằng 10 Cash (không giới hạn)\n⏰ Đợi đến ngày mai để verify bằng Xu\n💳 Nạp thêm: /nap hoặc /crypto",
                            'en': f"🚫 You've reached your daily Coins verify limit!\n\n💰 Coins: {bonus}\n📊 Coins verifications today: {coins_verify_count_today}/{coins_daily_limit}\n\n💡 You can:\n✅ Verify with 10 Cash (unlimited)\n⏰ Wait until tomorrow for Coins verify\n💳 Top up: /nap or /crypto",
                            'zh': f"🚫 您已达到今日硬币验证上限！\n\n💰 硬币：{bonus}\n📊 今日硬币验证：{coins_verify_count_today}/{coins_daily_limit}\n\n💡 您可以：\n✅ 用 10 现金验证（无限制）\n⏰ 等到明天再用硬币验证\n💳 充值：/nap 或 /crypto"
                        }
                        send_telegram_message(chat_id, quota_msgs.get(user_lang, quota_msgs['vi']))
                        return
                    else:
                        # Unlocked but no money
                        insufficient_msgs = {
                            'vi': f"❌ Không đủ tiền để verify!\n\n💰 Xu: {bonus} (cần 25 Xu | {coins_verify_count_today}/3 hôm nay)\n💵 Cash: {cash} (cần 10 Cash)\n\n💡 Dùng /nap để nạp thêm\n🌍 Dùng /crypto để nạp crypto\n\n🎁 Hoặc nhận 10 cash miễn phí:\n📢 Tham gia: @channel_sheerid_vip_bot\n⏰ Đợi 24 giờ\n👉 Gõ /checkchannel để nhận!",
                            'en': f"❌ Insufficient funds!\n\n💰 Coins: {bonus} (need 25 Coins | {coins_verify_count_today}/3 today)\n💵 Cash: {cash} (need 10 Cash)\n\n💡 Use /nap to top up\n🌍 Use /crypto for crypto deposit\n\n🎁 Or get 10 cash for free:\n📢 Join: @channel_sheerid_vip_bot\n⏰ Wait 24 hours\n👉 Type /checkchannel to claim!",
                            'zh': f"❌ 余额不足！\n\n💰 硬币：{bonus}（需要 25 硬币 | 今日 {coins_verify_count_today}/3）\n💵 现金：{cash}（需要 10 现金）\n\n💡 使用 /nap 充值\n🌍 使用 /crypto 加密货币充值\n\n🎁 或免费获得 10 cash：\n📢 加入：@channel_sheerid_vip_bot\n⏰ 等待24小时\n👉 输入 /checkchannel 领取！"
                        }
                        send_telegram_message(chat_id, insufficient_msgs.get(user_lang, insufficient_msgs['vi']))
                        return
            except Exception as e:
                print(f"❌ Error checking payment options: {e}")
                import traceback
                traceback.print_exc()
                # Fallback: only allow cash payment method
                if cash >= 10:
                    payment_method = "cash"
                    fee_text = "10 Cash"
                else:
                    print(f"⚠️ User {user_id} insufficient funds")
                    insufficient_msgs2 = {
                        'vi': f"❌ Không đủ tiền!\n\n💵 CASH: {cash}\n💰 Cần: 10 Cash\n\n💡 Dùng lệnh /nap để nạp thêm (VN)\n🌍 Dùng /crypto để nạp crypto (quốc tế)\n\n🎁 Hoặc nhận 10 cash miễn phí:\n📢 Tham gia: @channel_sheerid_vip_bot\n⏰ Đợi 24 giờ\n👉 Gõ /checkchannel để nhận!",
                        'en': f"❌ Insufficient funds!\n\n💵 CASH: {cash}\n💰 Need: 10 Cash\n\n💡 Use /nap to top up (Vietnam bank only)\n🌍 Use /crypto for crypto deposit (International)\n\n🎁 Or get 10 cash for free:\n📢 Join: @channel_sheerid_vip_bot\n⏰ Wait 24 hours\n👉 Type /checkchannel to claim!",
                        'zh': f"❌ 余额不足！\n\n💵 现金: {cash}\n💰 需要: 10 现金\n\n💡 使用 /nap 充值（仅限越南银行）\n🌍 使用 /crypto 加密货币充值（国际用户）\n\n🎁 或免费获得 10 cash：\n📢 加入：@channel_sheerid_vip_bot\n⏰ 等待24小时\n👉 输入 /checkchannel 领取！"
                    }
                    send_telegram_message(chat_id, insufficient_msgs2.get(user_lang, insufficient_msgs2['vi']))
                    return
        
        # ============================================
        # DEDUCT PAYMENT UPFRONT (BEFORE creating job) to prevent spam abuse
        # ============================================
        print(f"🔍 DEBUG UPFRONT DEDUCTION: user_id={user_id}, payment_method={payment_method}, cash={cash}, bonus={bonus}, vip_active={vip_active}")
        # VIP: Will refund on both success and fail (free verification)
        # Non-VIP: Will refund only on fail, keep on success
        # This prevents users from spamming multiple jobs with limited cash/coins
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            if supabase:
                if payment_method == "coins":
                    # Deduct 25 coins immediately to hold/prevent spam
                    new_bonus = bonus - 25
                    print(f"🔍 DEBUG: About to deduct coins. Current: {bonus}, New: {new_bonus}")
                    result = supabase.table('users').update({'coins': new_bonus}).eq('id', user_id).execute()
                    print(f"🔍 DEBUG: Update result: {result}")
                    print(f"💰 HOLD: Deducted 25 coins from user {user_id}. Will refund only on fail. New balance: {new_bonus}")
                    bonus = new_bonus  # Update local variable for display
                    print(f"✅ Database updated: user {user_id} coins = {new_bonus}")
                    
                elif payment_method == "cash" and cash >= 10:
                    # Deduct 10 cash immediately to hold/prevent spam
                    new_cash = cash - 10
                    print(f"🔍 DEBUG: About to deduct cash. Current: {cash}, New: {new_cash}")
                    result = supabase.table('users').update({'cash': new_cash}).eq('id', user_id).execute()
                    print(f"🔍 DEBUG: Update result: {result}")
                    if vip_active:
                        print(f"💰 HOLD: Deducted 10 cash from VIP user {user_id}. Will refund on completion. New balance: {new_cash}")
                    else:
                        print(f"💰 HOLD: Deducted 10 cash from user {user_id}. Will refund only on fail. New balance: {new_cash}")
                    cash = new_cash  # Update local variable for display
                    print(f"✅ Database updated: user {user_id} cash = {new_cash}")
                else:
                    print(f"⚠️ DEBUG: Skipped deduction - payment_method={payment_method}, cash={cash}, bonus={bonus}")
            else:
                print(f"⚠️ DEBUG: Skipped deduction - supabase not available")
        except Exception as e:
            print(f"❌ Error deducting upfront payment: {e}")
            import traceback
            traceback.print_exc()
        
        # Create verification job with payment_method
        job_id = create_verification_job(user_id, url, verification_type='sheerid', payment_method=payment_method if not vip_active else "vip")
        
        # Send confirmation with payment method (coins or cash)
        if vip_active:
            coin_status = f"👑 VIP: {cash} Cash"
        elif payment_method == "coins":
            coin_status = f"💰 Xu: {bonus} (đã trừ 25 xu)"
        else:
            coin_status = f"💵 CASH: {cash}"
        
        # Fix URL to ensure it has /verify/ path for SheerID links
        # Also add locale=vi for Vietnamese language form
        display_url = url
        if 'services.sheerid.com' in url and '/verify/' not in url:
            # Extract the verification ID from URL
            import re
            # Try to find the ID after domain: services.sheerid.com/ID/?params
            match = re.search(r'services\.sheerid\.com/([a-zA-Z0-9_-]+)(?:/|\?|$)', url)
            if match:
                verification_id = match.group(1)
                # Reconstruct URL with /verify/ path and locale=vi
                if '?' in url:
                    query_string = url.split('?', 1)[1]
                    # Add locale=vi if not already present
                    if 'locale=' not in query_string:
                        query_string += '&locale=vi'
                    display_url = f"https://services.sheerid.com/verify/{verification_id}/?{query_string}"
                else:
                    display_url = f"https://services.sheerid.com/verify/{verification_id}/?locale=vi"
        elif 'services.sheerid.com' in url:
            # URL already has /verify/ path, just add locale=vi if not present
            if 'locale=' not in url:
                if '?' in url:
                    display_url = url + '&locale=vi'
                else:
                    display_url = url + '?locale=vi'
            
        # ============================================
        # STUDENT QUEUE SYSTEM - Max 3 concurrent
        # ============================================
        queue_status = get_student_queue_status()
        
        if can_start_student_verification():
            # Can start immediately - add to active
            add_student_to_active(job_id)
            
            # Send processing message (multilingual) - NO MARKDOWN to avoid URL parsing issues
            # Updated: 2026-02-01 - Disabled markdown parsing completely
            msg_template = STUDENT_QUEUE_MESSAGES['processing'].get(user_lang, STUDENT_QUEUE_MESSAGES['processing']['vi'])
            message = msg_template.format(
                job_id=job_id,
                display_url=display_url,
                fee_text=fee_text,
                coin_status=coin_status,
                active=queue_status['active'] + 1,
                max_concurrent=STUDENT_MAX_CONCURRENT
            )
            send_telegram_message(chat_id, message, parse_mode=None)
            
            # Start verification immediately
            print(f"✅ Starting student verification immediately for job {job_id}")
            
            # Execute verification in background thread
            def run_verification():
                try:
                    _execute_verification(chat_id, user, url, job_id, payment_method, user_lang)
                except Exception as e:
                    print(f"❌ Verification error for job {job_id}: {e}")
                finally:
                    # Always remove from active when done
                    remove_student_from_active(job_id)
            
            thread = threading.Thread(target=run_verification, daemon=True)
            thread.start()
        else:
            # Queue is full - add to waiting queue
            position = add_student_to_queue(chat_id, user, url, job_id, payment_method, user_lang)
            wait_time = position * 3  # Estimate ~3 minutes per verification
            
            # Send queue notification (multilingual)
            msg_template = STUDENT_QUEUE_MESSAGES['queue_added'].get(user_lang, STUDENT_QUEUE_MESSAGES['queue_added']['vi'])
            message = msg_template.format(
                job_id=job_id,
                position=position,
                active=queue_status['active'],
                max_concurrent=STUDENT_MAX_CONCURRENT,
                wait_time=wait_time
            )
            send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"❌ Error in handle_verify_command: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_vs_command(chat_id, user, text):
    """Handle Spotify Student verification command - /vs"""
    try:
        # Check VERIFY-specific maintenance mode (same as /verify)
        verify_maintenance = BOT_CONFIG.get('verify_maintenance', False)
        env_verify_maintenance = os.environ.get('VERIFY_MAINTENANCE', 'false').lower() == 'true'
        is_verify_maintenance = verify_maintenance or env_verify_maintenance
        
        print(f"🔍 DEBUG handle_vs: verify_maintenance = {is_verify_maintenance}")
        if is_verify_maintenance:
            if chat_id not in ADMIN_TELEGRAM_IDS:
                maintenance_msg = BOT_CONFIG.get('maintenance_message', 
                    "🔧 Chức năng /vs đang bảo trì.\n\n"
                    "Vui lòng thử lại sau. Cảm ơn bạn!")
                send_telegram_message(chat_id, maintenance_msg, parse_mode=None)
                return
            else:
                print(f"✅ Admin {chat_id} bypassing VERIFY maintenance mode")
        
        # Get user language
        telegram_id = user.get('telegram_id') if isinstance(user, dict) else user[1] if user and len(user) > 1 else None
        user_lang = DEFAULT_LANGUAGE
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase and telegram_id:
                user_lang = get_user_language(supabase, telegram_id)
        except:
            pass
        
        # Extract URL from /vs command
        url = text.replace('/vs', '').strip()
        print(f"DEBUG /vs: Original text: {text}")
        print(f"DEBUG /vs: Extracted URL: {url}")
        
        # Multilingual messages for /vs command
        vs_msgs = {
            'no_url': {
                'vi': '❌ Vui lòng cung cấp URL Spotify SheerID\n\nVí dụ: /vs https://services.sheerid.com/verify/63fd266996552d469aea40e1/?country=US&locale=en-US&verificationId=...',
                'en': '❌ Please provide Spotify SheerID URL\n\nExample: /vs https://services.sheerid.com/verify/63fd266996552d469aea40e1/?country=US&locale=en-US&verificationId=...',
                'zh': '❌ 请提供 Spotify SheerID URL\n\n示例：/vs https://services.sheerid.com/verify/63fd266996552d469aea40e1/?country=US&locale=en-US&verificationId=...'
            },
            'invalid_url': {
                'vi': '❌ URL không đúng định dạng Spotify SheerID!\n\n✅ URL hợp lệ: https://services.sheerid.com/verify/63fd266996552d469aea40e1/...\n\n💡 Lệnh /vs dành riêng cho Spotify Student verification',
                'en': '❌ Invalid Spotify SheerID URL format!\n\n✅ Valid URL: https://services.sheerid.com/verify/63fd266996552d469aea40e1/...\n\n💡 /vs command is for Spotify Student verification only',
                'zh': '❌ Spotify SheerID URL 格式无效！\n\n✅ 有效URL：https://services.sheerid.com/verify/63fd266996552d469aea40e1/...\n\n💡 /vs 命令仅用于 Spotify 学生验证'
            }
        }
        
        if not url:
            send_telegram_message(chat_id, vs_msgs['no_url'].get(user_lang, vs_msgs['no_url']['vi']))
            return
        
        # Validate URL format - must be SheerID URL
        if not validate_sheerid_url(url):
            send_telegram_message(chat_id, vs_msgs['invalid_url'].get(user_lang, vs_msgs['invalid_url']['vi']))
            return
        
        # Check if this is a Spotify verification link (program ID: 63fd266996552d469aea40e1)
        spotify_program_id = '63fd266996552d469aea40e1'
        is_spotify_link = spotify_program_id in url
        
        if not is_spotify_link:
            not_spotify_msgs = {
                'vi': f'❌ Đây không phải link Spotify Student!\n\n💡 Link Spotify phải chứa: {spotify_program_id}\n\n📝 Nếu bạn muốn verify link khác, hãy dùng /verify',
                'en': f'❌ This is not a Spotify Student link!\n\n💡 Spotify link must contain: {spotify_program_id}\n\n📝 If you want to verify other links, use /verify',
                'zh': f'❌ 这不是 Spotify 学生链接！\n\n💡 Spotify 链接必须包含：{spotify_program_id}\n\n📝 如果您想验证其他链接，请使用 /verify'
            }
            send_telegram_message(chat_id, not_spotify_msgs.get(user_lang, not_spotify_msgs['vi']))
            return
        
        # Validate verificationId exists via SheerID API
        is_valid, error_msg, verification_data = validate_sheerid_verification_exists(url)
        if not is_valid:
            reject_msgs = {
                'vi': "❌ Link Spotify SheerID không hợp lệ!\n\n💡 Vui lòng lấy link khác hợp lệ.",
                'en': "❌ Invalid Spotify SheerID link!\n\n💡 Please get another valid link.",
                'zh': "❌ Spotify SheerID 链接无效！\n\n💡 请获取另一个有效链接。"
            }
            send_telegram_message(chat_id, reject_msgs.get(user_lang, reject_msgs['vi']))
            return
        
        # Check if verification already completed
        if verification_data and verification_data.get('currentStep') == 'success':
            already_verified_msgs = {
                'vi': "✅ Link Spotify này đã được verify thành công rồi!\n\n💡 Không cần chạy verification nữa.",
                'en': "✅ This Spotify link has already been verified successfully!\n\n💡 No need to run verification again.",
                'zh': "✅ 此 Spotify 链接已成功验证！\n\n💡 无需再次运行验证。"
            }
            send_telegram_message(chat_id, already_verified_msgs.get(user_lang, already_verified_msgs['vi']))
            return
        
        # Check if verification is in docUpload state
        if verification_data and verification_data.get('currentStep') == 'docUpload':
            current_step = verification_data.get('currentStep', 'docUpload')
            docupload_msgs = {
                'vi': f"⚠️ Link Spotify của bạn đang ở trạng thái: {current_step}\n\n💡 Vui lòng dùng lệnh:\n/fix {url}\n\nđể giới hạn link, sau đó quay lại trang reload để lấy link mới.\n\nRồi quay lại bot /vs <link_mới>",
                'en': f"⚠️ Your Spotify link is in state: {current_step}\n\n💡 Please use command:\n/fix {url}\n\nto limit the link, then go back to the page and reload to get a new link.\n\nThen come back to bot /vs <new_link>",
                'zh': f"⚠️ 您的 Spotify 链接处于状态：{current_step}\n\n💡 请使用命令：\n/fix {url}\n\n来限制链接，然后返回页面刷新获取新链接。\n\n然后回到机器人 /vs <新链接>"
            }
            send_telegram_message(chat_id, docupload_msgs.get(user_lang, docupload_msgs['vi']))
            return
        
        # Check if verification is in pending state (already submitted, waiting for review)
        if verification_data and verification_data.get('currentStep') == 'pending':
            awaiting_step = verification_data.get('awaitingStep', '').lower()
            rejection_reasons = verification_data.get('rejectionReasons', [])
            
            if awaiting_step == 'docupload' or rejection_reasons:
                rejection_msg = ', '.join(rejection_reasons) if rejection_reasons else ''
                pending_used_msgs = {
                    'vi': f"⚠️ Link Spotify này đã được sử dụng trước đó và đang chờ xử lý.\n\n📋 Trạng thái: pending (awaitingStep: {awaiting_step})\n{f'❌ Lý do từ chối: {rejection_msg}' if rejection_msg else ''}\n\n💡 Vui lòng dùng lệnh:\n/fix {url}\n\nđể giới hạn link, sau đó quay lại trang reload để lấy link mới.",
                    'en': f"⚠️ This Spotify link has already been used and is pending review.\n\n📋 Status: pending (awaitingStep: {awaiting_step})\n{f'❌ Rejection reason: {rejection_msg}' if rejection_msg else ''}\n\n💡 Please use command:\n/fix {url}\n\nto limit the link, then go back to the page and reload to get a new link.",
                    'zh': f"⚠️ 此 Spotify 链接已被使用，正在等待审核。\n\n📋 状态：pending (awaitingStep: {awaiting_step})\n{f'❌ 拒绝原因：{rejection_msg}' if rejection_msg else ''}\n\n💡 请使用命令：\n/fix {url}\n\n来限制链接，然后返回页面刷新获取新链接。"
                }
                send_telegram_message(chat_id, pending_used_msgs.get(user_lang, pending_used_msgs['vi']))
                return
            else:
                pending_msgs = {
                    'vi': f"⏳ Link Spotify này đang trong trạng thái chờ xử lý (pending).\n\n💡 Vui lòng đợi hoặc lấy link mới nếu đã chờ quá lâu.",
                    'en': f"⏳ This Spotify link is currently pending review.\n\n💡 Please wait or get a new link if you've been waiting too long.",
                    'zh': f"⏳ 此 Spotify 链接正在等待审核中。\n\n💡 请等待，或者如果等待时间过长，请获取新链接。"
                }
                send_telegram_message(chat_id, pending_msgs.get(user_lang, pending_msgs['vi']))
                return
        
        # Send initial notification
        initial_msgs = {
            'vi': '🎵 **Spotify Student Verification**\n\n⏰ Quá trình verify có thể mất 2-5 phút, vui lòng đợi.',
            'en': '🎵 **Spotify Student Verification**\n\n⏰ Verification process may take 2-5 minutes, please wait.',
            'zh': '🎵 **Spotify 学生验证**\n\n⏰ 验证过程可能需要 2-5 分钟，请耐心等待。'
        }
        send_telegram_message(chat_id, initial_msgs.get(user_lang, initial_msgs['vi']), parse_mode=None)
        
        # Get user_id
        if isinstance(user, dict):
            user_id = user.get('id', 0)
        else:
            user_id = user[0]
        
        # Check VIP status
        vip_active = False
        try:
            vip_active = check_vip_status(user_id)
        except:
            pass
        
        # Get user balance
        cash = 0
        bonus = 0
        try:
            wallets = supabase_get_wallets_by_user_id(user_id)
            if wallets:
                cash, bonus = wallets
        except Exception as e:
            print(f"Error getting wallets: {e}")
        
        # Determine payment method (same as /verify - 5 xu/cash)
        payment_method = None
        fee_text = ""
        
        if vip_active:
            payment_method = "vip"
            fee_text = "0 (VIP)"
        else:
            # Check daily limits for xu verification
            xu_verify_count_today = 0
            try:
                if SUPABASE_AVAILABLE:
                    from supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    if supabase:
                        today = format_vietnam_time('%Y-%m-%d')
                        resp = (
                            supabase
                            .table('verification_jobs')
                            .select('id', count='exact')
                            .eq('user_id', user_id)
                            .eq('status', 'completed')
                            .eq('payment_method', 'xu')
                            .gte('created_at', f"{today}T00:00:00")
                            .lte('created_at', f"{today}T23:59:59")
                            .execute()
                        )
                        xu_verify_count_today = int(getattr(resp, 'count', 0) or 0)
            except Exception as e:
                print(f"Error checking daily limits: {e}")
            
            # Determine payment method
            can_use_xu = (xu_verify_count_today < 2) and (bonus >= 10)
            can_use_cash = cash >= 10
            
            if can_use_xu:
                payment_method = "xu"
                fee_text = f"10 Xu ({xu_verify_count_today + 1}/2 hôm nay)"
            elif can_use_cash:
                payment_method = "cash"
                fee_text = "10 Cash"
            else:
                # Insufficient balance
                insufficient_msgs = {
                    'vi': f"❌ Không đủ tiền để verify Spotify!\n\n💵 CASH: {cash} | 🪙 Xu: {bonus}\n📊 Đã verify XU: {xu_verify_count_today}/2 lần hôm nay\n💰 Cần: 10 Xu hoặc 10 Cash\n\n💡 Dùng lệnh /nap để nạp thêm\n🌍 Dùng /crypto để nạp crypto (quốc tế)",
                    'en': f"❌ Insufficient balance to verify Spotify!\n\n💵 CASH: {cash} | 🪙 Coins: {bonus}\n📊 XU verifications today: {xu_verify_count_today}/2\n💰 Need: 10 Coins or 10 Cash\n\n💡 Use /nap to top up (Vietnam bank)\n🌍 Use /crypto for crypto deposit (International)",
                    'zh': f"❌ 余额不足，无法验证 Spotify！\n\n💵 现金: {cash} | 🪙 金币: {bonus}\n📊 今日金币验证: {xu_verify_count_today}/2 次\n💰 需要: 10 金币或 10 现金\n\n💡 使用 /nap 充值（越南银行）\n🌍 使用 /crypto 加密货币充值（国际用户）"
                }
                send_telegram_message(chat_id, insufficient_msgs.get(user_lang, insufficient_msgs['vi']))
                return
        
        # Create verification job with type 'spotify'
        job_id = create_verification_job(user_id, url, verification_type='spotify', payment_method=payment_method)
        
        # Send confirmation
        if vip_active:
            coin_status = f"👑 VIP: {cash} Cash | {bonus} Xu"
        else:
            coin_status = f"💵 CASH: {cash} | 🪙 Xu: {bonus}"
        
        confirm_msgs = {
            'vi': f"""🎵 **Spotify Student Verification**

🆔 Job ID: {job_id}
🔗 Link: Spotify Student
💰 Phí: {fee_text}
{coin_status}

⏳ Đang xử lý... Vui lòng đợi 2-5 phút.""",
            'en': f"""🎵 **Spotify Student Verification**

🆔 Job ID: {job_id}
🔗 Link: Spotify Student
💰 Fee: {fee_text}
{coin_status}

⏳ Processing... Please wait 2-5 minutes.""",
            'zh': f"""🎵 **Spotify 学生验证**

🆔 任务ID: {job_id}
🔗 链接: Spotify Student
💰 费用: {fee_text}
{coin_status}

⏳ 处理中... 请等待 2-5 分钟。"""
        }
        send_telegram_message(chat_id, confirm_msgs.get(user_lang, confirm_msgs['vi']))
        
        print(f"✅ Created Spotify verification job {job_id} for user {user_id}")
        
        # Execute verification in background thread (same as /verify)
        def run_spotify_verification():
            try:
                _execute_verification(chat_id, user, url, job_id, payment_method, user_lang, verification_type='spotify')
            except Exception as e:
                print(f"❌ Spotify verification error for job {job_id}: {e}")
            finally:
                # Always remove from active when done
                remove_student_from_active(job_id)
        
        thread = threading.Thread(target=run_spotify_verification, daemon=True)
        thread.start()
        print(f"🚀 Started Spotify verification thread for job {job_id}")
        
    except Exception as e:
        print(f"❌ Error in handle_vs_command: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")


def handle_vc_batch_command(chat_id, user, text):
    """
    Handle batch VC command: /vc3 or /vc5
    Allows VIP Pro/Business users to submit multiple ChatGPT Teacher links at once
    
    Usage:
    /vc3 link1 link2 link3
    /vc5 link1 link2 link3 link4 link5
    """
    import threading
    
    try:
        # Determine batch size from command
        if text.startswith('/vc5'):
            batch_size = 5
            links_text = text.replace('/vc5', '').strip()
        else:  # /vc3
            batch_size = 3
            links_text = text.replace('/vc3', '').strip()
        
        # Get user info
        telegram_id = user.get('telegram_id') if isinstance(user, dict) else user[1] if user and len(user) > 1 else None
        user_id = user.get('id') if isinstance(user, dict) else user[0] if user else None
        
        # Get user language
        user_lang = DEFAULT_LANGUAGE
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase and telegram_id:
                user_lang = get_user_language(supabase, telegram_id)
        except:
            pass
        
        # Check VIP status
        vip_active = False
        concurrent_limit = 1
        
        if isinstance(user, dict):
            is_vip = user.get('is_vip', False)
            vip_expiry = user.get('vip_expiry')
            concurrent_limit = user.get('concurrent_links', 1) or 1
            
            if is_vip and vip_expiry:
                try:
                    from datetime import datetime
                    import pytz
                    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
                    expiry_dt = datetime.fromisoformat(vip_expiry.replace('Z', '+00:00'))
                    vip_active = expiry_dt > datetime.now(expiry_dt.tzinfo)
                except:
                    vip_active = is_vip
            else:
                vip_active = is_vip
        
        # Check if user has VIP with enough concurrent slots
        if not vip_active:
            no_vip_msgs = {
                'vi': f"❌ Lệnh /vc{batch_size} chỉ dành cho VIP!\n\n💡 Mua gói VIP để sử dụng:\n• VIP Pro (3 link): /mua vippro7\n• VIP Business (5 link): /mua vipbiz7",
                'en': f"❌ /vc{batch_size} command is VIP only!\n\n💡 Buy VIP package to use:\n• VIP Pro (3 links): /mua vippro7\n• VIP Business (5 links): /mua vipbiz7",
                'zh': f"❌ /vc{batch_size} 命令仅限VIP用户！\n\n💡 购买VIP套餐使用：\n• VIP Pro (3链接): /mua vippro7\n• VIP Business (5链接): /mua vipbiz7"
            }
            send_telegram_message(chat_id, no_vip_msgs.get(user_lang, no_vip_msgs['vi']))
            return
        
        if concurrent_limit < batch_size:
            upgrade_msgs = {
                'vi': f"❌ Gói VIP của bạn chỉ hỗ trợ {concurrent_limit} link song song.\n\n💡 Nâng cấp để dùng /vc{batch_size}:\n• VIP Pro (3 link): /mua vippro7\n• VIP Business (5 link): /mua vipbiz7",
                'en': f"❌ Your VIP package only supports {concurrent_limit} parallel links.\n\n💡 Upgrade to use /vc{batch_size}:\n• VIP Pro (3 links): /mua vippro7\n• VIP Business (5 links): /mua vipbiz7",
                'zh': f"❌ 您的VIP套餐仅支持 {concurrent_limit} 个并行链接。\n\n💡 升级以使用 /vc{batch_size}：\n• VIP Pro (3链接): /mua vippro7\n• VIP Business (5链接): /mua vipbiz7"
            }
            send_telegram_message(chat_id, upgrade_msgs.get(user_lang, upgrade_msgs['vi']))
            return
        
        # Parse links - support multiple formats: space, newline, comma separated
        import re
        # Find all SheerID URLs (ChatGPT Teacher uses same SheerID format)
        url_pattern = r'https?://services\.sheerid\.com/verify/[^\s,]+'
        links = re.findall(url_pattern, links_text)
        
        if not links:
            usage_msgs = {
                'vi': f"❌ Không tìm thấy link SheerID!\n\n📝 Cách dùng:\n/vc{batch_size} link1 link2 link3\n\nHoặc mỗi link một dòng:\n/vc{batch_size}\nhttps://services.sheerid.com/verify/xxx\nhttps://services.sheerid.com/verify/yyy\nhttps://services.sheerid.com/verify/zzz",
                'en': f"❌ No SheerID links found!\n\n📝 Usage:\n/vc{batch_size} link1 link2 link3\n\nOr one link per line:\n/vc{batch_size}\nhttps://services.sheerid.com/verify/xxx\nhttps://services.sheerid.com/verify/yyy\nhttps://services.sheerid.com/verify/zzz",
                'zh': f"❌ 未找到SheerID链接！\n\n📝 用法：\n/vc{batch_size} link1 link2 link3\n\n或每行一个链接：\n/vc{batch_size}\nhttps://services.sheerid.com/verify/xxx\nhttps://services.sheerid.com/verify/yyy\nhttps://services.sheerid.com/verify/zzz"
            }
            send_telegram_message(chat_id, usage_msgs.get(user_lang, usage_msgs['vi']))
            return
        
        # Limit to batch_size
        links = links[:batch_size]
        
        if len(links) < 2:
            single_link_msgs = {
                'vi': f"💡 Chỉ có 1 link? Dùng /vc {links[0]} thay vì /vc{batch_size}",
                'en': f"💡 Only 1 link? Use /vc {links[0]} instead of /vc{batch_size}",
                'zh': f"💡 只有1个链接？使用 /vc {links[0]} 而不是 /vc{batch_size}"
            }
            send_telegram_message(chat_id, single_link_msgs.get(user_lang, single_link_msgs['vi']))
            return
        
        # Check available slots
        try:
            from .vip_tiers import can_start_verification, get_user_active_count
            active_count = get_user_active_count(str(telegram_id))
            slots_available = concurrent_limit - active_count
            
            if slots_available < len(links):
                not_enough_slots_msgs = {
                    'vi': f"⚠️ Bạn chỉ còn {slots_available}/{concurrent_limit} slot trống.\n\n🔗 Đang chạy: {active_count} link\n📝 Yêu cầu: {len(links)} link\n\n💡 Vui lòng chờ các job hiện tại hoàn thành hoặc gửi ít link hơn.",
                    'en': f"⚠️ You only have {slots_available}/{concurrent_limit} slots available.\n\n🔗 Running: {active_count} links\n📝 Requested: {len(links)} links\n\n💡 Please wait for current jobs to complete or submit fewer links.",
                    'zh': f"⚠️ 您只有 {slots_available}/{concurrent_limit} 个可用槽位。\n\n🔗 正在运行：{active_count} 个链接\n📝 请求：{len(links)} 个链接\n\n💡 请等待当前任务完成或提交更少的链接。"
                }
                send_telegram_message(chat_id, not_enough_slots_msgs.get(user_lang, not_enough_slots_msgs['vi']))
                return
        except ImportError:
            pass
        
        # Send confirmation message
        links_preview = '\n'.join([f"  {i+1}. ...{link[-30:]}" for i, link in enumerate(links)])
        confirm_msgs = {
            'vi': f"🚀 Bắt đầu verify {len(links)} link ChatGPT Teacher song song!\n\n📋 Danh sách:\n{links_preview}\n\n⏳ Mỗi link sẽ mất 2-5 phút...",
            'en': f"🚀 Starting parallel ChatGPT Teacher verification of {len(links)} links!\n\n📋 List:\n{links_preview}\n\n⏳ Each link takes 2-5 minutes...",
            'zh': f"🚀 开始并行验证 {len(links)} 个ChatGPT Teacher链接！\n\n📋 列表：\n{links_preview}\n\n⏳ 每个链接需要2-5分钟..."
        }
        send_telegram_message(chat_id, confirm_msgs.get(user_lang, confirm_msgs['vi']))
        
        # Process each link in parallel using threads
        def process_single_link(link, index):
            """Process a single link - calls handle_vc_command logic"""
            try:
                # Create a fake text command for the existing handler
                fake_text = f"/vc {link}"
                handle_vc_command(chat_id, user, fake_text)
            except Exception as e:
                error_msgs = {
                    'vi': f"❌ Link {index+1} lỗi: {str(e)[:50]}",
                    'en': f"❌ Link {index+1} error: {str(e)[:50]}",
                    'zh': f"❌ 链接 {index+1} 错误：{str(e)[:50]}"
                }
                send_telegram_message(chat_id, error_msgs.get(user_lang, error_msgs['vi']))
        
        # Start threads for each link
        threads = []
        for i, link in enumerate(links):
            t = threading.Thread(target=process_single_link, args=(link, i))
            t.start()
            threads.append(t)
            # Small delay between starts to avoid rate limiting
            import time
            time.sleep(0.5)
        
        # Don't wait for threads - they run in background
        
    except Exception as e:
        print(f"❌ Error in handle_vc_batch_command: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)[:100]}")


def handle_vc_command(chat_id, user, text):
    """Handle ChatGPT Teacher verification command - /vc"""
    try:
        # Check VC-specific maintenance mode
        vc_maintenance = BOT_CONFIG.get('vc_maintenance', False)
        env_vc_maintenance = os.environ.get('VC_MAINTENANCE', 'false').lower() == 'true'
        is_vc_maintenance = vc_maintenance or env_vc_maintenance
        
        print(f"🔍 DEBUG handle_vc: vc_maintenance = {is_vc_maintenance}")
        if is_vc_maintenance:
            # Allow admin to bypass maintenance
            if chat_id not in ADMIN_TELEGRAM_IDS:
                maintenance_msg = """🔧 The /vc command is currently under maintenance.

⏰ Please try again later.

📢 Follow our announcement channel for updates:
https://t.me/channel_sheerid_vip_bot

Thank you for your patience! 🙏"""
                send_telegram_message(chat_id, maintenance_msg, parse_mode=None)
                return
            else:
                print(f"✅ Admin {chat_id} bypassing VC maintenance mode")
        
        # Get user language
        telegram_id = user.get('telegram_id') if isinstance(user, dict) else user[1] if user and len(user) > 1 else None
        user_lang = DEFAULT_LANGUAGE
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase and telegram_id:
                user_lang = get_user_language(supabase, telegram_id)
        except:
            pass
        
        # Extract URL from /vc
        url = text.replace('/vc', '').strip()
        print(f"DEBUG /vc: Original text: {text}")
        print(f"DEBUG /vc: Extracted URL: {url}")
        
        if not url:
            send_telegram_message(chat_id, "❌ Vui lòng cung cấp URL SheerID cho ChatGPT Teacher\n\nVí dụ: /vc https://services.sheerid.com/verify/...")
            return
        
        # Validate URL format (SheerID URL with ChatGPT redirect)
        if not validate_sheerid_url(url):
            send_telegram_message(chat_id, "❌ URL không đúng định dạng SheerID!\n\n✅ URL hợp lệ: https://services.sheerid.com/verify/...\n❌ URL không hợp lệ: https://example.com/...")
            return
        
        # Validate verificationId exists via SheerID API
        is_valid, error_msg, verification_data = validate_sheerid_verification_exists(url)
        if not is_valid:
            # Show the specific error message if available
            if error_msg:
                send_telegram_message(chat_id, error_msg)
            else:
                send_telegram_message(chat_id, "❌ Link ChatGPT Teacher không hợp lệ!\n\n💡 Vui lòng lấy link khác hợp lệ.")
            return
        
        # Check if verification already completed (success)
        if verification_data and verification_data.get('currentStep') == 'success':
            send_telegram_message(chat_id, "✅ Link ChatGPT Teacher này đã được verify thành công rồi!\n\n💡 Không cần chạy verification nữa.")
            return
        
        # Check if verification is in docUpload state (needs to be fixed)
        if verification_data and verification_data.get('currentStep') == 'docUpload':
            current_step = verification_data.get('currentStep', 'docUpload')
            send_telegram_message(chat_id, f"⚠️ Link ChatGPT Teacher của bạn đang ở trạng thái: {current_step}\n\n💡 Vui lòng dùng lệnh:\n/fix {url}\n\nđể giới hạn link, sau đó quay lại trang reload để lấy link mới.\n\nRồi quay lại bot /vc <link_mới>")
            return
        
        # Check if verification is in pending state (already submitted, waiting for review)
        if verification_data and verification_data.get('currentStep') == 'pending':
            awaiting_step = verification_data.get('awaitingStep', '').lower()
            rejection_reasons = verification_data.get('rejectionReasons', [])
            
            if awaiting_step == 'docupload' or rejection_reasons:
                rejection_msg = ', '.join(rejection_reasons) if rejection_reasons else ''
                msg = f"⚠️ Link ChatGPT Teacher này đã được sử dụng trước đó và đang chờ xử lý.\n\n📋 Trạng thái: pending (awaitingStep: {awaiting_step})\n{f'❌ Lý do từ chối: {rejection_msg}' if rejection_msg else ''}\n\n💡 Vui lòng dùng lệnh:\n/fix {url}\n\nđể giới hạn link, sau đó quay lại trang reload để lấy link mới."
                send_telegram_message(chat_id, msg)
                return
            else:
                send_telegram_message(chat_id, f"⏳ Link ChatGPT Teacher này đang trong trạng thái chờ xử lý (pending).\n\n💡 Vui lòng đợi hoặc lấy link mới nếu đã chờ quá lâu.")
                return
        
        # Send initial notification
        message = """🎓 **CHATGPT TEACHER VERIFICATION**

⏰ Quá trình verify có thể mất 20-50 giây, vui lòng đợi.

🇺🇸 VPN to USA

🌍 Verification process may take 20-50 seconds, please wait."""
        
        send_telegram_message(chat_id, message)
        
        # Get user_id
        if isinstance(user, dict):
            user_id = user.get('id', 0)
        else:
            user_id = user[0]

        # Check wallets/eligibility
        vip_active = is_vip_active(user)
        if isinstance(user, dict):
            wallets = supabase_get_wallets_by_user_id(user.get('id'))
            cash = wallets[0] if wallets else int(user.get('cash') or 0)
            bonus = wallets[1] if wallets else int(user.get('coins') or 0)
        else:
            wallets = supabase_get_wallets_by_user_id(user[0])
            if wallets:
                cash, bonus = wallets[0], wallets[1]
            else:
                cash = user[5]
                bonus = 0
        
        verify_cost = 50  # ChatGPT Teacher costs 50 xu/cash
        
        # Determine payment method - ChatGPT Teacher has different pricing
        # VIP users: 50 xu/cash, no limit
        # Regular users: 50 xu (only 1 time EVER) or 50 cash (unlimited)
        if vip_active:
            can_pay = (bonus >= 75) or (cash >= 75)
            if not can_pay:
                insufficient_vc_msgs = {
                    'vi': f"❌ Không đủ Xu/Cash!\n\n💵 CASH: {cash} | 🪙 Xu: {bonus}\n💰 Cần: 75 Xu/Cash (ChatGPT Teacher)\n\n💡 Dùng lệnh /nap để nạp thêm\n🌍 Dùng /crypto để nạp crypto (quốc tế)",
                    'en': f"❌ Insufficient Coins/Cash!\n\n💵 CASH: {cash} | 🪙 Coins: {bonus}\n💰 Need: 75 Coins/Cash (ChatGPT Teacher)\n\n💡 Use /nap to top up (Vietnam bank)\n🌍 Use /crypto for crypto deposit (International)",
                    'zh': f"❌ 金币/现金不足！\n\n💵 现金: {cash} | 🪙 金币: {bonus}\n💰 需要: 75 金币/现金 (ChatGPT Teacher)\n\n💡 使用 /nap 充值（越南银行）\n🌍 使用 /crypto 加密货币充值（国际用户）"
                }
                send_telegram_message(chat_id, insufficient_vc_msgs.get(user_lang, insufficient_vc_msgs['vi']))
                return
            payment_method = "xu" if bonus >= 75 else "cash"
            fee_text = f"75 {payment_method.upper()} (VIP: không giới hạn)"
        else:
            # Regular user: Check if ever used xu for ChatGPT verification
            try:
                verify_count_ever = 0
                if SUPABASE_AVAILABLE:
                    try:
                        from supabase_client import get_supabase_client
                        supabase = get_supabase_client()
                        if supabase:
                            # Count ALL ChatGPT verifications ever (not just today)
                            resp = (
                                supabase
                                .table('verification_jobs')
                                .select('id', count='exact')
                                .eq('user_id', user_id)
                                .eq('status', 'completed')
                                .eq('verification_type', 'chatgpt')
                                .execute()
                            )
                            verify_count_ever = int(getattr(resp, 'count', 0) or 0)
                            print(f"DEBUG /vc: User {user_id} has {verify_count_ever} ChatGPT verifications EVER")
                    except Exception as e:
                        print(f"DEBUG /vc: Error counting verifications: {e}")
                        verify_count_ever = 0
                
                # Check if can use xu (only 1 time ever)
                can_use_xu = (verify_count_ever < 1) and (bonus >= 75)
                can_use_cash = cash >= 75
                
                # Determine payment method
                if can_use_xu:
                    payment_method = "xu"
                    fee_text = f"75 Xu (lần duy nhất)"
                elif can_use_cash:
                    payment_method = "cash"
                    if verify_count_ever >= 1:
                        fee_text = f"75 Cash (đã dùng quota xu 1 lần)"
                        switch_message = f"""⚠️ **Thông báo chuyển đổi thanh toán**

📊 Bạn đã sử dụng quota xu cho ChatGPT Teacher (1 lần duy nhất)
💰 Hệ thống sẽ tự động chuyển sang thanh toán bằng CASH
💵 Phí: 75 Cash (thay vì 75 Xu)

🔄 Tiếp tục verify với CASH..."""
                        send_telegram_message(chat_id, switch_message)
                    else:
                        fee_text = f"75 Cash (không đủ xu, tự động chuyển sang Cash)"
                        switch_message = f"""⚠️ **Thông báo chuyển đổi thanh toán**

🪙 Xu hiện tại: {bonus} (cần 75 Xu)
💰 Hệ thống sẽ tự động chuyển sang thanh toán bằng CASH
💵 Phí: 75 Cash (thay vì 75 Xu)

🔄 Tiếp tục verify với CASH..."""
                        send_telegram_message(chat_id, switch_message)
                else:
                    insufficient_vc_msgs2 = {
                        'vi': f"❌ Không đủ tiền để verify!\n\n💵 CASH: {cash} | 🪙 Xu: {bonus}\n📊 Đã verify: {verify_count_ever}/1 lần (xu)\n💰 Cần: 75 Xu (1 lần duy nhất) hoặc 75 Cash (không giới hạn)\n\n💡 Dùng lệnh /nap để nạp thêm\n🌍 Dùng /crypto để nạp crypto (quốc tế)",
                        'en': f"❌ Insufficient balance to verify!\n\n💵 CASH: {cash} | 🪙 Coins: {bonus}\n📊 Verified: {verify_count_ever}/1 time (coins)\n💰 Need: 75 Coins (one-time only) or 75 Cash (unlimited)\n\n💡 Use /nap to top up (Vietnam bank)\n🌍 Use /crypto for crypto deposit (International)",
                        'zh': f"❌ 余额不足，无法验证！\n\n💵 现金: {cash} | 🪙 金币: {bonus}\n📊 已验证: {verify_count_ever}/1 次（金币）\n💰 需要: 75 金币（仅一次）或 75 现金（无限制）\n\n💡 使用 /nap 充值（越南银行）\n🌍 使用 /crypto 加密货币充值（国际用户）"
                    }
                    send_telegram_message(chat_id, insufficient_vc_msgs2.get(user_lang, insufficient_vc_msgs2['vi']))
                    return
                    
            except Exception as e:
                print(f"Error checking limits: {e}")
                if bonus >= 75:
                    payment_method = "xu"
                    fee_text = "75 Xu"
                elif cash >= 75:
                    payment_method = "cash"
                    fee_text = "75 Cash"
                else:
                    insufficient_vc_msgs3 = {
                        'vi': f"❌ Không đủ Xu/Cash!\n\n💵 CASH: {cash} | 🪙 Xu: {bonus}\n💰 Cần: 75 Xu hoặc 75 Cash\n\n💡 Dùng lệnh /nap để nạp thêm\n🌍 Dùng /crypto để nạp crypto (quốc tế)",
                        'en': f"❌ Insufficient Coins/Cash!\n\n💵 CASH: {cash} | 🪙 Coins: {bonus}\n💰 Need: 75 Coins or 75 Cash\n\n💡 Use /nap to top up (Vietnam bank)\n🌍 Use /crypto for crypto deposit (International)",
                        'zh': f"❌ 金币/现金不足！\n\n💵 现金: {cash} | 🪙 金币: {bonus}\n💰 需要: 75 金币或 75 现金\n\n💡 使用 /nap 充值（越南银行）\n🌍 使用 /crypto 加密货币充值（国际用户）"
                    }
                    send_telegram_message(chat_id, insufficient_vc_msgs3.get(user_lang, insufficient_vc_msgs3['vi']))
                    return
        
        # Create verification job with type 'chatgpt' and payment_method
        job_id = create_verification_job(user_id, url, verification_type='chatgpt', payment_method=payment_method)
        
        # Send confirmation
        if vip_active:
            coin_status = f"👑 VIP: {cash} Cash | {bonus} Xu"
        else:
            coin_status = f"💵 CASH: {cash} | 🪙 Xu: {bonus}"
        
        # ============================================
        # TEACHER QUEUE SYSTEM - Max 5 concurrent
        # ============================================
        queue_status = get_teacher_queue_status()
        
        if can_start_teacher_verification():
            # Can start immediately
            add_teacher_to_active(job_id)
            
            message = f"""✅ Đã tạo job verify ChatGPT Teacher!

🆔 Job ID: `{job_id}`
🔗 Link: {url}
💰 Phí: {fee_text}
{coin_status}
⏳ Trạng thái: Đang xử lý...
📊 Slot: {queue_status['active'] + 1}/{TEACHER_MAX_CONCURRENT}"""
            
            send_telegram_message(chat_id, message, parse_mode=None)
            
            # Start verification in background thread
            print(f"🎓 DEBUG /vc: Starting teacher verification immediately for job {job_id}")
            
            def run_teacher_verification():
                try:
                    _execute_teacher_verification(chat_id, user, url, job_id, payment_method, user_lang)
                except Exception as e:
                    print(f"❌ Teacher verification error for job {job_id}: {e}")
                    remove_teacher_from_active(job_id)
            
            thread = threading.Thread(target=run_teacher_verification, daemon=True)
            thread.start()
        else:
            # Add to queue
            position = add_teacher_to_queue(chat_id, user, url, job_id, payment_method, user_lang)
            
            message = f"""⏳ Đã thêm vào hàng chờ Teacher Verification!

🆔 Job ID: `{job_id}`
🔗 Link: {url}
💰 Phí: {fee_text}
{coin_status}

📊 **Trạng thái hàng chờ:**
👥 Đang xử lý: {queue_status['active']}/{TEACHER_MAX_CONCURRENT} người
📋 Vị trí của bạn: #{position} trong hàng chờ
⏱️ Ước tính: ~{position * 10}-{position * 30} phút

💡 Hệ thống sẽ tự động thông báo khi đến lượt bạn!
🔔 Bạn có thể tiếp tục sử dụng bot bình thường."""
            
            send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"❌ Error in handle_vc_command: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")


# NOTE: /fix command has been removed


def handle_fix_command(chat_id, user, text):
    """Handle /fix command - Upload blank image 3 times to burn a SheerID link"""
    try:
        # Get user language
        user_lang = DEFAULT_LANGUAGE
        try:
            telegram_id = user.get('telegram_id') if isinstance(user, dict) else user[1] if user and len(user) > 1 else None
            if telegram_id:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    user_lang = get_user_language(supabase, telegram_id)
        except:
            pass
        
        # Extract URL from /fix command
        url = text.replace('/fix', '').strip()
        
        # Help messages in different languages
        help_messages = {
            'vi': """🔧 Lệnh /fix - Reset link docUpload

📝 Cách dùng: /fix <URL>

Ví dụ:
/fix https://services.sheerid.com/verify/...?verificationId=...

⚠️ Lệnh này sẽ:
1. Upload ảnh blank 3 lần liên tiếp
2. Mỗi lần upload sẽ bị reject
3. Sau 3 lần, link sẽ về trạng thái error
4. Bạn có thể lấy link mới từ trang gốc

💡 Dùng khi link bị stuck ở docUpload""",
            'en': """🔧 /fix Command - Reset docUpload link

📝 Usage: /fix <URL>

Example:
/fix https://services.sheerid.com/verify/...?verificationId=...

⚠️ This command will:
1. Upload blank image 3 times consecutively
2. Each upload will be rejected
3. After 3 times, link will go to error state
4. You can get a new link from the original page

💡 Use when link is stuck at docUpload""",
            'zh': """🔧 /fix 命令 - 重置 docUpload 链接

📝 用法: /fix <URL>

示例:
/fix https://services.sheerid.com/verify/...?verificationId=...

⚠️ 此命令将:
1. 连续上传空白图片3次
2. 每次上传都会被拒绝
3. 3次后，链接将进入错误状态
4. 您可以从原始页面获取新链接

💡 当链接卡在 docUpload 时使用"""
        }
        
        if not url:
            send_telegram_message(chat_id, help_messages.get(user_lang, help_messages['vi']))
            return
        
        # Extract verification ID from URL
        verification_id = None
        
        # Try to extract from verificationId parameter
        if 'verificationId=' in url:
            try:
                verification_id = url.split('verificationId=')[1].split('&')[0]
            except:
                pass
        
        # Try to extract from path
        if not verification_id and '/verify/' in url:
            try:
                path_part = url.split('/verify/')[1]
                if '/' in path_part:
                    verification_id = path_part.split('/')[0]
                elif '?' in path_part:
                    verification_id = path_part.split('?')[0]
                else:
                    verification_id = path_part
            except:
                pass
        
        # Error messages for invalid URL
        invalid_url_msgs = {
            'vi': "❌ Không tìm thấy verificationId trong URL. Vui lòng kiểm tra lại link.",
            'en': "❌ Could not find verificationId in URL. Please check the link.",
            'zh': "❌ 在URL中找不到verificationId。请检查链接。"
        }
        
        if not verification_id:
            send_telegram_message(chat_id, invalid_url_msgs.get(user_lang, invalid_url_msgs['vi']))
            return
        
        # Starting messages
        starting_msgs = {
            'vi': f"""🔧 Bắt đầu fix link...

🆔 Verification ID: `{verification_id}`
⏳ Đang upload ảnh blank 3 lần...

Vui lòng đợi...""",
            'en': f"""🔧 Starting to fix link...

🆔 Verification ID: `{verification_id}`
⏳ Uploading blank image 3 times...

Please wait...""",
            'zh': f"""🔧 开始修复链接...

🆔 验证ID: `{verification_id}`
⏳ 正在上传空白图片3次...

请稍候..."""
        }
        
        send_telegram_message(chat_id, starting_msgs.get(user_lang, starting_msgs['vi']))
        
        # Process fix directly (not via API call)
        import requests
        import io
        from PIL import Image
        
        try:
            # Create blank white image
            blank_img = Image.new('RGB', (100, 100), color='white')
            img_buffer = io.BytesIO()
            blank_img.save(img_buffer, format='JPEG', quality=50)
            img_buffer.seek(0)
            blank_image_data = img_buffer.read()
            
            max_attempts = 3
            attempts = 0
            final_status = 'unknown'
            
            for attempt in range(max_attempts):
                attempts += 1
                print(f"🔄 Fix attempt {attempts}/{max_attempts} for {verification_id}")
                
                try:
                    # Step 1: Check current status
                    status_url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}"
                    headers = {
                        'Accept': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    status_resp = requests.get(status_url, headers=headers, timeout=30)
                    if status_resp.status_code == 200:
                        status_data = status_resp.json()
                        current_step = status_data.get('currentStep', '').lower()
                        print(f"📊 Current step: {current_step}")
                        
                        # If already in error state, we're done
                        if current_step in ['error', 'rejected', 'failed']:
                            final_status = current_step
                            print(f"✅ Link already in error state: {current_step}")
                            break
                    
                    # Step 2: Upload blank image (using Vercel default IP, no proxy)
                    upload_url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}/step/docUpload"
                    
                    # Use pre-saved blank image data for each upload
                    files = {
                        'file': ('blank.jpg', blank_image_data, 'image/jpeg')
                    }
                    
                    upload_headers = {
                        'Accept': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Origin': 'https://services.sheerid.com',
                        'Referer': f'https://services.sheerid.com/verify/{verification_id}'
                    }
                    
                    upload_resp = requests.post(upload_url, files=files, headers=upload_headers, timeout=30)
                    print(f"📤 Upload response: {upload_resp.status_code}")
                    
                    if upload_resp.status_code == 200:
                        upload_data = upload_resp.json()
                        new_step = upload_data.get('currentStep', '').lower()
                        print(f"📊 After upload step: {new_step}")
                        final_status = new_step
                        
                        # If reached error state, we're done
                        if new_step in ['error', 'rejected', 'failed']:
                            print(f"✅ Reached error state after {attempts} attempts")
                            break
                    else:
                        print(f"❌ Upload failed: {upload_resp.status_code}")
                        final_status = f"upload_error_{upload_resp.status_code}"
                    
                    # Wait a bit before next attempt
                    import time
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"❌ Error in attempt {attempts}: {e}")
                    continue
            
            # Success messages
            success_msgs = {
                'vi': f"""✅ Fix hoàn tất!

🔄 Số lần upload: {attempts}
📊 Trạng thái cuối: {final_status}

💡 Bây giờ bạn có thể:
- Vào trang gốc để lấy link SheerID mới
- Hoặc thử /verify với link mới""",
                'en': f"""✅ Fix completed!

🔄 Upload attempts: {attempts}
📊 Final status: {final_status}

💡 Now you can:
- Go to the original page to get a new SheerID link
- Or try /verify with a new link""",
                'zh': f"""✅ 修复完成！

🔄 上传次数: {attempts}
📊 最终状态: {final_status}

💡 现在您可以:
- 前往原始页面获取新的SheerID链接
- 或使用新链接尝试 /verify"""
            }
            send_telegram_message(chat_id, success_msgs.get(user_lang, success_msgs['vi']))
                
        except Exception as e:
            error_msgs = {
                'vi': f"❌ Lỗi: {str(e)}",
                'en': f"❌ Error: {str(e)}",
                'zh': f"❌ 错误: {str(e)}"
            }
            send_telegram_message(chat_id, error_msgs.get(user_lang, error_msgs['vi']))
        
    except Exception as e:
        print(f"❌ Error in handle_fix_command: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")


def handle_vip_command(chat_id, user):
    """Handle VIP purchase command"""
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    
    # Handle user data format (dictionary from SQLite)
    if isinstance(user, dict):
        user_id = user.get('id', 1)
        username = user.get('username', 'user')
        first_name = user.get('first_name', 'User')
        last_name = user.get('last_name', '')
        coins = user.get('coins', 0)
        is_vip = user.get('is_vip', False)
        vip_expiry = user.get('vip_expiry')
        created_at = user.get('created_at', '2025-09-21T00:00:00')
    else:
        # Fallback for tuple format (old code)
        user_id = user[0]
        username = user[1]
        first_name = user[2]
        last_name = user[3]
        coins = user[4]
        is_vip = user[5]
        vip_expiry = user[6]
        created_at = user[7]
    
    # Check VIP status and auto-expire if past
    from datetime import datetime, timezone, timedelta
    vip_status = "❌ Hết hạn"
    expiry_text = None
    expired = False
    if is_vip and vip_expiry:
        try:
            expiry_date_utc = datetime.fromisoformat(vip_expiry.replace('Z', '+00:00'))
            vietnam_tz = timezone(timedelta(hours=7))
            now_vn = datetime.now(vietnam_tz)
            expiry_vn = expiry_date_utc.astimezone(vietnam_tz)
            if now_vn < expiry_vn:
                vip_status = f"✅ Có (hết hạn: {expiry_vn.strftime('%d/%m/%Y %H:%M')} VN)"
                expiry_text = expiry_vn.strftime('%d/%m/%Y %H:%M') + ' VN'
            else:
                expired = True
        except Exception:
            expired = True
    elif is_vip and not vip_expiry:
        # has VIP flag but no expiry, treat as expired for consistency
        expired = True
    
    if expired:
        # Auto-fix: update Supabase to set is_vip False
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                supabase.table('users').update({ 'is_vip': False }).eq('id', user_id).execute()
        except Exception:
            pass
        send_telegram_message(chat_id, "❌ VIP đã hết hạn!")
        return
    
    if is_vip:
        # Detailed VIP info for users who still have active VIP
        expiry_line = expiry_text or 'N/A'
        message = f"""
👑 Bạn đã là VIP rồi!

📅 Ngày hết hạn: {expiry_line}

🎁 Quyền lợi:
- Verify không giới hạn
- Ưu tiên xử lý, hỗ trợ
- Mua đồ trong /shop rẻ hơn
- Checkin hằng ngày nhận 1 xu
        """
        send_telegram_message(chat_id, message)
        return
    
    # Get VIP price
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM bot_settings WHERE key = ?', ('vip_price',))
    vip_price = int(cursor.fetchone()[0])
    conn.close()
    
    if coins < vip_price:
        message = f"❌ Không đủ xu! Cần {vip_price} xu để mua VIP (Bạn có {coins} xu)\n\n💬 Liên hệ admin để mua VIP: @meepzizhere"
        send_telegram_message(chat_id, message)
        return
    
    # Purchase VIP
    update_user_coins(user_id, -vip_price, 'purchase', 'Mua VIP')
    
    # Update user VIP status with default expiry (30 days)
    from datetime import datetime, timedelta
    expiry_date = datetime.now() + timedelta(days=30)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_vip = TRUE, vip_expiry = ? WHERE id = ?', (expiry_date.isoformat(), user_id))
    conn.commit()
    conn.close()
    
    message = f"""
🎉 Chúc mừng! Bạn đã trở thành VIP!

👑 Quyền lợi VIP:
• Verify Unlimited
• Ưu tiên xử lý
• Hỗ trợ 24/7

⏰ Hết hạn: {expiry_date.strftime('%d/%m/%Y %H:%M')}
💰 Xu còn lại: {coins - vip_price}
❓ Hỗ trợ: @meepzizhere
    """
    
    send_telegram_message(chat_id, message)

def send_detailed_help_message(chat_id):
    """Send detailed help message for /hdsd command"""
    message = """
🎯 **HƯỚNG DẪN CHI TIẾT - GOOGLE GEMINI STUDENTS**

📋 **Các bước thực hiện:**

1️⃣ **Cài đặt VPN**
   • Ưu tiên VPN có độ trust mạnh, bảo mật cao
   • Gợi ý: SurfShark, Proton, HMA, ExpressVPN
   • Fake VPN qua 🇻🇳 Việt Nam (Hiện tại - Bắt buộc)

2️⃣ **Chuẩn bị tài khoản Google**
   • Đăng nhập tài khoản Google (bắt buộc có ưu đãi)
   • Tài khoản phải đủ điều kiện nhận offer - Có thể mua tài khoản ở /shop

3️⃣ **Truy cập trang xác minh**
   • Vào link: https://gemini.google/students
   • Bấm nút "Get offer" để xác minh

4️⃣ **Lấy link SheerID**
   • Copy link có dạng: services.sheerid.com/verify/...
   • Lưu ý: Link phải đầy đủ và chính xác

5️⃣ **Verify qua Bot**
   • Quay lại @SheerID_VIP_Bot trên Telegram
   • Gửi lệnh: /verify <link>
   • Chờ bot xử lý và trả kết quả

6️⃣ **Hoàn tất xác minh**
   • Sau khi Verify xong, quay lại Google
   • Reload trang sẽ thấy trạng thái "hoàn tất"
   • Chuyển hướng về trang Student để thêm thanh toán

7️⃣ **Done!**
   • Bạn đã có Google AI Pro miễn phí 1 năm
   • Bao gồm: Gemini Pro, 2TB storage, NotebookLM

🆘 **Hỗ trợ:** @meepzizhere
📢 **Kênh thông báo:** https://t.me/channel_sheerid_vip_bot
    """
    
    # Create inline keyboard with language options
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🇺🇸 English", "callback_data": "hdsd_en"},
                {"text": "🇹🇷 Türkçe", "callback_data": "hdsd_tr"}
            ]
        ]
    }
    
    send_telegram_message_with_keyboard(chat_id, message, keyboard["inline_keyboard"])

def send_detailed_help_message_en(chat_id):
    """Send detailed help message in English"""
    message = """
🎯 **DETAILED GUIDE - GOOGLE GEMINI STUDENTS**

📋 **Steps to follow:**

1️⃣ **Install VPN**
   • Priority: VPN with strong trust and high security
   • Suggestions: SurfShark, Proton, HMA, ExpressVPN
   • Fake VPN to 🇻🇳 Vietnam (Currently - Required)

2️⃣ **Prepare Google Account**
   • Login to Google account (must have offers)
   • Account must be eligible for offers - Can buy accounts at /shop

3️⃣ **Access verification page**
   • Go to: https://gemini.google/students
   • Click "Get offer" button to verify

4️⃣ **Get SheerID link**
   • Copy link format: services.sheerid.com/verify/...
   • Note: Link must be complete and accurate

5️⃣ **Verify via Bot**
   • Return to @SheerID_VIP_Bot on Telegram
   • Send command: /verify <link>
   • Wait for bot to process and return result

6️⃣ **Complete verification**
   • After verification is done, return to Google
   • Reload page to see "completed" status
   • Redirect to Student page to add payment

7️⃣ **Done!**
   • You now have Google AI Pro free for 1 year
   • Includes: Gemini Pro, 2TB storage, NotebookLM

🆘 **Support:** @meepzizhere
📢 **Channel:** https://t.me/channel_sheerid_vip_bot
    """
    
    send_telegram_message(chat_id, message, parse_mode=None)

def send_detailed_help_message_tr(chat_id):
    """Send detailed help message in Turkish"""
    message = """
🎯 **DETAYLI KILAVUZ - GOOGLE GEMINI ÖĞRENCİLER**

📋 **Takip edilecek adımlar:**

1️⃣ **VPN Kurulumu**
   • Öncelik: Güçlü güven ve yüksek güvenlikli VPN
   • Öneriler: SurfShark, Proton, HMA, ExpressVPN
   • VPN'i 🇻🇳 Vietnam'a ayarlayın (Şu anda - Gerekli)

2️⃣ **Google Hesabı Hazırlığı**
   • Google hesabına giriş yapın (teklifleri olmalı)
   • Hesap teklifler için uygun olmalı - /shop'tan hesap satın alabilirsiniz

3️⃣ **Doğrulama sayfasına erişim**
   • Şu adrese gidin: https://gemini.google/students
   • Doğrulamak için "Get offer" düğmesine tıklayın

4️⃣ **SheerID linkini alın**
   • Link formatını kopyalayın: services.sheerid.com/verify/...
   • Not: Link tam ve doğru olmalıdır

5️⃣ **Bot üzerinden doğrulama**
   • Telegram'da @SheerID_VIP_Bot'a dönün
   • Komutu gönderin: /verify <link>
   • Bot'un işlemesi ve sonucu döndürmesini bekleyin

6️⃣ **Doğrulamayı tamamlayın**
   • Doğrulama tamamlandıktan sonra Google'a dönün
   • "Tamamlandı" durumunu görmek için sayfayı yenileyin
   • Ödeme eklemek için Öğrenci sayfasına yönlendirileceksiniz

7️⃣ **Tamamlandı!**
   • Artık 1 yıl ücretsiz Google AI Pro'nuz var
   • İçerir: Gemini Pro, 2TB depolama, NotebookLM

🆘 **Destek:** @meepzizhere
📢 **Kanal:** https://t.me/channel_sheerid_vip_bot
    """
    
    send_telegram_message(chat_id, message, parse_mode=None)

def send_help_message(chat_id, user_lang='vi'):
    """Send help message in user's language"""
    
    help_messages = {
        'vi': """
📖 Hướng dẫn sử dụng SheerID VIP Bot:

🔧 Các lệnh chính:
/hdsd - Hướng dẫn chi tiết
/verify <link> - Verify link SheerID (Gemini)
/vs <link> - Verify Spotify Student (cần IP US)
/vc <link> - Verify ChatGPT Teacher
/cancel hoặc /huy - Hủy job verify đang chờ
/status - Xem thông tin bot hiện tại
/help - Trợ giúp và danh sách lệnh
/me - Xem thông tin cá nhân
/lang - Đổi ngôn ngữ

💰 Quản lý xu:
/nap - Nạp xu (chỉ ngân hàng Việt Nam)
/crypto - Nạp xu bằng crypto (quốc tế)
/checkin - Nhận xu miễn phí mỗi ngày
/checkchannel - Nhận 10 cash khi join channel (1 lần)
/shop - Cửa hàng

📊 Theo dõi:
/myjobs - Xem danh sách job của bạn
/lsgd - Lịch sử giao dịch

🤝 Mời bạn bè:
/invite - Tạo link mời bạn bè
/link <mã_mời> - Liên kết với người mời

🪙 Hệ thống xu:
• Verify thường: 3 xu
• Verify VIP: 0 xu / không giới hạn
• Mời bạn bè: 3 xu/người

❓ Hỗ trợ: @meepzizhere
📢 Kênh: https://t.me/channel_sheerid_vip_bot
        """,
        'en': """
📖 SheerID VIP Bot User Guide:

🔧 Main Commands:
/hdsd - Detailed guide
/verify <link> - Verify SheerID link (Gemini)
/vs <link> - Verify Spotify Student (US IP required)
/vc <link> - Verify ChatGPT Teacher
/cancel - Cancel pending verify job
/status - View current bot info
/help - Help and command list
/me - View personal info
/lang - Change language

💰 Coin Management:
/nap - Deposit (Vietnam bank only)
/crypto - Deposit with crypto (International)
/checkin - Get free coins daily
/checkchannel - Get 10 cash for joining channel (once)
/shop - Store

⚠️ Note: /nap only works with Vietnamese banks
🌍 International users: Please use /crypto

📊 Tracking:
/myjobs - View your jobs
/lsgd - Transaction history

🤝 Invite Friends:
/invite - Create invite link
/link <code> - Link with referrer

🪙 Coin System:
• Regular verify: 3 coins
• VIP verify: 0 coins / unlimited
• Invite friends: 3 coins/person

❓ Support: @meepzizhere
📢 Channel: https://t.me/channel_sheerid_vip_bot
        """,
        'zh': """
📖 SheerID VIP 机器人使用指南：

🔧 主要命令：
/hdsd - 详细指南
/verify <link> - 验证 SheerID 链接 (Gemini)
/vs <link> - 验证 Spotify 学生（需要美国 IP）
/vc <link> - 验证 ChatGPT Teacher
/cancel - 取消待处理的验证任务
/status - 查看当前机器人信息
/help - 帮助和命令列表
/me - 查看个人信息
/lang - 更改语言

💰 金币管理：
/nap - 充值（仅限越南银行）
/crypto - 加密货币充值（国际用户）
/checkin - 每日免费金币
/checkchannel - 加入频道获得 10 cash（一次）
/shop - 商店

⚠️ 注意：/nap 仅适用于越南银行
🌍 国际用户：请使用 /crypto

📊 跟踪：
/myjobs - 查看您的任务
/lsgd - 交易历史

🤝 邀请好友：
/invite - 创建邀请链接
/link <code> - 与推荐人关联

🪙 金币系统：
• 普通验证：3 金币
• VIP验证：0 金币 / 无限
• 邀请好友：3 金币/人

❓ 支持：@meepzizhere
📢 频道：https://t.me/channel_sheerid_vip_bot
        """
    }
    
    message = help_messages.get(user_lang, help_messages['vi'])
    send_telegram_message(chat_id, message, parse_mode=None)

def handle_queue_command(chat_id, user):
    """Handle /queue command - queue system removed"""
    send_telegram_message(chat_id, "✅ Hệ thống không còn hàng chờ. Verification chạy ngay lập tức!\n\n💡 Dùng /verify <URL> để bắt đầu.")

def handle_status_command(chat_id, text='', user_lang='vi'):
    """
    Handle /status command to query SheerID Bot API for job status
    
    If job_id is provided: Query API for job status
    If no job_id: Show general bot information
    
    Requirements: 6.1-6.5
    """
    try:
        # Parse job_id from command text
        parts = text.strip().split()
        job_id = parts[1] if len(parts) > 1 else None
        
        if job_id:
            # Query SheerID Bot API for job status (Requirements 6.1-6.5)
            _handle_job_status_query(chat_id, job_id, user_lang)
        else:
            # Show general bot information (original behavior)
            _show_bot_status(chat_id, user_lang)
        
    except Exception as e:
        print(f"❌ Error in handle_status_command: {e}")
        import traceback
        traceback.print_exc()
        error_msg = {
            'vi': "❌ Lỗi hiển thị thông tin!",
            'en': "❌ Error displaying information!",
            'zh': "❌ 显示信息时出错！"
        }
        send_telegram_message(chat_id, error_msg.get(user_lang, error_msg['vi']))


def _handle_job_status_query(chat_id, job_id, user_lang='vi'):
    """
    Query SheerID Bot API for job status
    
    Requirements: 6.1-6.5
    """
    try:
        from .sheerid_bot_client import get_sheerid_bot_client, SheerIDAPIError
        
        # Get API client
        client = get_sheerid_bot_client()
        if not client:
            error_msg = {
                'vi': "❌ Dịch vụ SheerID Bot API chưa được cấu hình.",
                'en': "❌ SheerID Bot API service is not configured.",
                'zh': "❌ SheerID Bot API 服务未配置。"
            }
            send_telegram_message(chat_id, error_msg.get(user_lang, error_msg['vi']))
            return
        
        # Query job status (Requirement 6.1)
        print(f"🔍 Querying job status for: {job_id}")
        result = client.get_job_status(job_id)
        
        status = result.get('status', 'unknown').lower()
        
        # Handle different statuses (Requirements 6.2-6.4)
        if status in ['pending', 'processing']:
            # Requirement 6.2: Display current status with estimated wait time
            estimated_time = result.get('estimated_time', 120)  # Default 2 minutes
            estimated_minutes = max(1, estimated_time // 60)
            
            msg = {
                'vi': f"""⏳ Trạng thái Job

🆔 Job ID: `{job_id}`
📊 Trạng thái: {'Đang chờ' if status == 'pending' else 'Đang xử lý'}
⏱️ Thời gian chờ ước tính: ~{estimated_minutes} phút

💡 Hệ thống sẽ tự động thông báo khi hoàn thành.""",
                'en': f"""⏳ Job Status

🆔 Job ID: `{job_id}`
📊 Status: {'Pending' if status == 'pending' else 'Processing'}
⏱️ Estimated wait time: ~{estimated_minutes} minutes

💡 System will notify you when completed.""",
                'zh': f"""⏳ 任务状态

🆔 任务ID: `{job_id}`
📊 状态: {'等待中' if status == 'pending' else '处理中'}
⏱️ 预计等待时间: ~{estimated_minutes} 分钟

💡 完成后系统会自动通知您。"""
            }
            send_telegram_message(chat_id, msg.get(user_lang, msg['vi']))
            
        elif status == 'success':
            # Requirement 6.3: Display success message with verification details
            result_details = result.get('result_details', {})
            verification_id = result_details.get('verification_id', 'N/A')
            verification_type = result.get('type', 'unknown')
            
            msg = {
                'vi': f"""✅ Xác minh thành công!

🆔 Job ID: `{job_id}`
📊 Trạng thái: Thành công
🎓 Loại: {verification_type.title()}
🔑 Verification ID: {verification_id}

🎉 Bạn đã có thể sử dụng ưu đãi!""",
                'en': f"""✅ Verification Successful!

🆔 Job ID: `{job_id}`
📊 Status: Success
🎓 Type: {verification_type.title()}
🔑 Verification ID: {verification_id}

🎉 You can now use the benefits!""",
                'zh': f"""✅ 验证成功！

🆔 任务ID: `{job_id}`
📊 状态: 成功
🎓 类型: {verification_type.title()}
🔑 验证ID: {verification_id}

🎉 您现在可以使用优惠了！"""
            }
            send_telegram_message(chat_id, msg.get(user_lang, msg['vi']))
            
        elif status == 'failed':
            # Requirement 6.4: Display failure reason
            error_message = result.get('error_message', result.get('error', 'Unknown error'))
            
            msg = {
                'vi': f"""❌ Xác minh thất bại

🆔 Job ID: `{job_id}`
📊 Trạng thái: Thất bại
🔍 Lý do: {error_message}

💡 Vui lòng thử lại với link khác.""",
                'en': f"""❌ Verification Failed

🆔 Job ID: `{job_id}`
📊 Status: Failed
🔍 Reason: {error_message}

💡 Please try again with a different link.""",
                'zh': f"""❌ 验证失败

🆔 任务ID: `{job_id}`
📊 状态: 失败
🔍 原因: {error_message}

💡 请使用其他链接重试。"""
            }
            send_telegram_message(chat_id, msg.get(user_lang, msg['vi']))
            
        else:
            # Unknown status
            msg = {
                'vi': f"""📋 Trạng thái Job

🆔 Job ID: `{job_id}`
📊 Trạng thái: {status}

💡 Liên hệ hỗ trợ nếu cần giúp đỡ.""",
                'en': f"""📋 Job Status

🆔 Job ID: `{job_id}`
📊 Status: {status}

💡 Contact support if you need help.""",
                'zh': f"""📋 任务状态

🆔 任务ID: `{job_id}`
📊 状态: {status}

💡 如需帮助请联系支持。"""
            }
            send_telegram_message(chat_id, msg.get(user_lang, msg['vi']))
            
    except SheerIDAPIError as e:
        # Requirement 6.5: Handle JOB_NOT_FOUND
        if e.code == 'JOB_NOT_FOUND':
            msg = {
                'vi': f"""❌ Không tìm thấy Job

🆔 Job ID: `{job_id}`

💡 Job không tồn tại hoặc đã hết hạn.
📝 Kiểm tra lại Job ID và thử lại.""",
                'en': f"""❌ Job Not Found

🆔 Job ID: `{job_id}`

💡 Job does not exist or has expired.
📝 Please check the Job ID and try again.""",
                'zh': f"""❌ 未找到任务

🆔 任务ID: `{job_id}`

💡 任务不存在或已过期。
📝 请检查任务ID后重试。"""
            }
        else:
            # Other errors - hide API details
            msg = {
                'vi': f"❌ Lỗi xử lý. Vui lòng thử lại sau.",
                'en': f"❌ Processing error. Please try again later.",
                'zh': f"❌ 处理错误。请稍后再试。"
            }
        send_telegram_message(chat_id, msg.get(user_lang, msg['vi']))
        
    except Exception as e:
        print(f"❌ Error querying job status: {e}")
        import traceback
        traceback.print_exc()
        msg = {
            'vi': "❌ Lỗi khi truy vấn trạng thái job. Vui lòng thử lại sau.",
            'en': "❌ Error querying job status. Please try again later.",
            'zh': "❌ 查询任务状态时出错。请稍后再试。"
        }
        send_telegram_message(chat_id, msg.get(user_lang, msg['vi']))


def _show_bot_status(chat_id, user_lang='vi'):
    """Show general bot information (original /status behavior)"""
    # Current target configuration - USA
    current_country = "United States"
    current_country_flag = "🇺🇸"
    
    msg = {
        'vi': f"""🌍 Quốc gia hỗ trợ / Supported Country:
{current_country_flag} {current_country}

💡 Hướng dẫn:
• Fake VPN sang các quốc gia có Ưu đãi Gemini
• Dùng IP tại {current_country_flag} {current_country} rồi thử lại /verify

📊 Xem trạng thái real-time:
🔗 https://dqsheerid.vercel.app/status/gemini

📋 Kiểm tra trạng thái job:
• Dùng: /status <job_id>
• Ví dụ: /status abc123""",
        'en': f"""🌍 Supported Country:
{current_country_flag} {current_country}

💡 Instructions:
• Switch your VPN to countries with Gemini offers
• Ensure your IP is in {current_country_flag} {current_country}, then run /verify again

📊 View real-time status:
🔗 https://dqsheerid.vercel.app/status/gemini

📋 Check job status:
• Use: /status <job_id>
• Example: /status abc123""",
        'zh': f"""🌍 支持的国家:
{current_country_flag} {current_country}

💡 说明:
• 将VPN切换到有Gemini优惠的国家
• 确保您的IP在 {current_country_flag} {current_country}，然后再次运行 /verify

📊 查看实时状态:
🔗 https://dqsheerid.vercel.app/status/gemini

📋 检查任务状态:
• 使用: /status <job_id>
• 示例: /status abc123"""
    }
    send_telegram_message(chat_id, msg.get(user_lang, msg['vi']))

def send_unknown_command(chat_id, user_lang='vi'):
    """Send unknown command message"""
    send_telegram_message(chat_id, get_text('invalid_command', user_lang))

def send_admin_menu(chat_id):
    """Send admin menu with inline keyboard"""
    message = "🔧 ADMIN MENU\n\nChọn danh mục để xem lệnh:"
    keyboard = [
        [
            {"text": "👥 Quản lý User", "callback_data": "admin_users"},
            {"text": "💰 Quản lý Ví", "callback_data": "admin_wallet"}
        ],
        [
            {"text": "👑 VIP", "callback_data": "admin_vip"},
            {"text": "📊 Jobs", "callback_data": "admin_jobs"}
        ],
        [
            {"text": "📢 Broadcast", "callback_data": "admin_broadcast"},
            {"text": "🛒 Shop & Giá", "callback_data": "admin_shop"}
        ],
        [
            {"text": "⚙️ Cấu hình", "callback_data": "admin_config"},
            {"text": "🛠️ Công cụ", "callback_data": "admin_tools"}
        ]
    ]
    send_telegram_message_with_keyboard(chat_id, message, keyboard)

def handle_admin_callback(chat_id, callback_data):
    """Handle admin menu callbacks"""
    if callback_data == "admin_users":
        message = """👥 QUẢN LÝ USER:

/admin users [trang] - Danh sách user (5/user/trang)
/admin add <telegram_id> <username> <first_name> [last_name]
/admin delete <telegram_id>
/admin clear - Xóa tất cả user (cẩn thận)"""
        send_telegram_message(chat_id, message)
    
    elif callback_data == "admin_wallet":
        message = """💰 QUẢN LÝ VÍ:

/admin coins <telegram_id> <amount> [lý_do] - Set Xu cho user
/admin cash <telegram_id> <amount> [lý_do] - Cộng/trừ CASH cho user
/admin refund <telegram_id> <amount> - Hoàn Xu cho user
/admin giftcoins <số_xu> <lý_do> - Tặng xu cho TẤT CẢ user
/admin giftcash <số_cash> <lý_do> - Tặng cash cho TẤT CẢ user
/admin transactions - Xem giao dịch gần đây"""
        send_telegram_message(chat_id, message)
    
    elif callback_data == "admin_vip":
        message = """👑 VIP:

/admin vip <telegram_id> <số_ngày> - Bật VIP theo ngày (0=tắt)
/admin vipexpiry <telegram_id> <YYYY-MM-DD HH:MM> - Set hạn VIP
/admin vipall <số_ngày> - Set VIP cho toàn bộ user
/admin vipbatch <ids_csv> <số_ngày> - Set VIP cho danh sách user"""
        send_telegram_message(chat_id, message)
    
    elif callback_data == "admin_jobs":
        message = """📊 JOBS:

/admin jobs <telegram_id> - Xem jobs SheerID của user"""
        send_telegram_message(chat_id, message)
    
    elif callback_data == "admin_broadcast":
        message = """📢 BROADCAST:

/admin noti <nội_dung>
/admin w <telegram_id> <nội_dung> - Nhắn riêng (whisper) đến user
/admin daily-send - Gửi thông báo hằng ngày (thật) cho toàn bộ user
/admin emergency on|off - Bật/Tắt dừng khẩn cấp ngay lập tức
/admin broadcast <message>
/admin broadcastvip <message>
/admin daily - Test thông báo hằng ngày
/admin ban <telegram_id> <lý_do> - Khóa user và gửi thông báo
/admin unban <telegram_id> <ghi_chú> - Mở khóa user và gửi thông báo"""
        send_telegram_message(chat_id, message)
    
    elif callback_data == "admin_shop":
        message = """🛒 SHOP & GIÁ:

/admin setgtrial <giá> - Đặt giá Google Trial (CASH)
/admin setgtrialvip <giá> - Đặt giá VIP Google Trial (CASH)
/admin setgverified <giá> - Đặt giá Google Verified (CASH)
/admin setgverifiedvip <giá> - Đặt giá VIP Google Verified (CASH)
/admin setcanva <giá> - Đặt giá Canva Admin Edu (CASH)
/admin setcanvavip <giá> - Đặt giá VIP Canva Admin Edu (CASH)
/admin setaiultra <giá> - Đặt giá Google AI ULTRA 25k Credits (CASH)
/admin setaiultravip <giá> - Đặt giá VIP Google AI ULTRA (CASH)
/admin setaiultra45 <giá> - Đặt giá Google AI ULTRA 45k Credits (CASH)
/admin setaiultra45v <giá> - Đặt giá VIP Google AI ULTRA 45k Credits (CASH)
/admin setchatgpt <giá> - Đặt giá ChatGPT Plus 3 Months (CASH)
/admin setchatgptvip <giá> - Đặt giá VIP ChatGPT Plus 3 Months (CASH)
/admin setspotify <giá> - Đặt giá Spotify Premium 4M CODE (CASH)
/admin setspotifyvip <giá> - Đặt giá VIP Spotify Premium 4M CODE (CASH)
/admin setsurfshark <giá> - Đặt giá Surfshark VPN (CASH)
/admin setsurfsharkv <giá> - Đặt giá VIP Surfshark VPN (CASH)
/admin setper <giá> - Đặt giá Perplexity PRO 1 Năm (CASH)
/admin setperv <giá> - Đặt giá VIP Perplexity PRO 1 Năm (CASH)
/admin setper1m <giá> - Đặt giá Perplexity PRO 1 Month (CASH)
/admin setper1mv <giá> - Đặt giá VIP Perplexity PRO 1 Month (CASH)
/admin setgpt1m <giá> - Đặt giá ChatGPT Code 1 Month (CASH)
/admin setgpt1mv <giá> - Đặt giá VIP ChatGPT Code 1 Month (CASH)
/admin setm365 <giá> - Đặt giá Microsoft 365 Personal 1 Năm (CASH)
/admin setm365v <giá> - Đặt giá VIP Microsoft 365 Personal 1 Năm (CASH)
/admin setadobe4m <giá> - Đặt giá ADOBE FULL APP 4 Months (CASH)
/admin setadobe4mv <giá> - Đặt giá VIP ADOBE FULL APP 4 Months (CASH)
/admin addviprices - Thêm tất cả giá VIP vào Supabase
/admin settype <account_id> <trial|verified|canva|chatgpt|spotify|surfshark|perplexity> - Chuyển loại tài khoản
/admin setvip7 <giá> - Đặt giá VIP 7 ngày (CASH)
/admin setvip30 <giá> - Đặt giá VIP 30 ngày (CASH)
/admin stock - Xem số lượng AVAILABLE
/admin importcsv <url_csv> - Import từ CSV công khai"""
        send_telegram_message(chat_id, message)
    
    elif callback_data == "admin_config":
        message = """⚙️ CẤU HÌNH:

/admin config - Xem cấu hình bot
/admin setwelcome <message>
/admin setprice <amount> - Giá verify
/admin setbonus <amount> - Xu checkin/ngày (áp dụng cho /checkin hoặc /diemdanh)
/admin maintenance on/off/force/status"""
        send_telegram_message(chat_id, message)
    
    elif callback_data == "admin_tools":
        message = """🛠️ CÔNG CỤ:

/admin migratexu - Gộp legacy về Xu (CASH=0)
/admin migratecash - Chuyển toàn bộ CASH → Xu (CASH=0)

❓ Hỗ trợ: @meepzizhere"""
        send_telegram_message(chat_id, message)

# ===== Google Account Selling (Supabase-backed) =====

def supabase_adjust_wallet_by_user_id(user_id, cash_delta=0, bonus_delta=0):
    """Refactored: Adjust wallets by user id using columns cash (CASH) and coins (Xu).
    Treat bonus_delta as delta to coins; cash_delta to cash. Returns (cash, coins)."""
    try:
        from supabase_client import get_supabase_client
        client = get_supabase_client()
        if not client:
            return None
        # fetch
        resp = client.table('users').select('id, coins, cash').eq('id', user_id).limit(1).execute()
        if not resp.data:
            return None
        row = resp.data[0]
        cash = int(row.get('cash') or 0)
        coins = int(row.get('coins') or 0)
        new_cash = cash + int(cash_delta)
        new_coins = coins + int(bonus_delta)
        if new_cash < 0 or new_coins < 0:
            return None
        upd = {
            'cash': new_cash,
            'coins': new_coins
        }
        u2 = client.table('users').update(upd).eq('id', user_id).execute()
        if not u2.data:
            return None
        return new_cash, new_coins
    except Exception:
        return None

def supabase_get_wallets_by_user_id(user_id):
    """Return (cash, coins) for a user from Supabase by id."""
    try:
        from supabase_client import get_supabase_client
        client = get_supabase_client()
        if not client:
            return None
        resp = client.table('users').select('id, coins, cash').eq('id', user_id).limit(1).execute()
        if not resp.data:
            return None
        row = resp.data[0]
        cash = int(row.get('cash') or 0)
        coins = int(row.get('coins') or 0)
        return cash, coins
    except Exception:
        return None

# --- Ban helpers ---
def is_user_banned(telegram_id):
    """Check if user is banned/blocked - returns True if blocked"""
    print(f"🔍 Checking ban status for user {telegram_id}")
    try:
        if SUPABASE_AVAILABLE:
            try:
                from .supabase_client import get_supabase_client
            except ImportError:
                from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                # 1) Try users table - check is_blocked column (primary)
                try:
                    resp = supabase.table('users').select('is_banned, is_blocked').eq('telegram_id', str(telegram_id)).limit(1).execute()
                    print(f"🔍 Ban check response for {telegram_id}: {resp.data}")
                    if resp.data:
                        row = resp.data[0]
                        # Check both is_banned and is_blocked
                        is_banned = bool(row.get('is_banned') or False)
                        is_blocked = bool(row.get('is_blocked') or False)
                        print(f"🔍 User {telegram_id}: is_banned={is_banned}, is_blocked={is_blocked}")
                        if is_banned or is_blocked:
                            print(f"🚫 User {telegram_id} is BLOCKED!")
                            return True
                        else:
                            print(f"✅ User {telegram_id} is NOT blocked")
                            return False
                except Exception as e:
                    print(f"⚠️ Error checking ban status: {e}")
                # 2) Fallback: dedicated user_bans table
                try:
                    b = supabase.table('user_bans').select('is_banned').eq('telegram_id', str(telegram_id)).limit(1).execute()
                    if b.data:
                        return bool(b.data[0].get('is_banned') or False)
                except Exception:
                    pass
                # 3) Fallback: bot_config key 'banned_users' as CSV
                try:
                    cfg = supabase.table('bot_config').select('config_key,config_value').eq('config_key','banned_users').limit(1).execute()
                    if cfg.data:
                        raw = cfg.data[0].get('config_value') or ''
                        ids = [s.strip() for s in str(raw).split(',') if s.strip()]
                        return str(telegram_id) in ids
                except Exception:
                    pass
                # 4) In-memory BOT_CONFIG fallback
                try:
                    raw = BOT_CONFIG.get('banned_users') or ''
                    ids = [s.strip() for s in str(raw).split(',') if s.strip()]
                    if str(telegram_id) in ids:
                        return True
                except Exception:
                    pass
        # SQLite fallback
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]
        if 'is_banned' in cols:
            cur.execute("SELECT is_banned FROM users WHERE telegram_id = ? LIMIT 1", (str(telegram_id),))
            r = cur.fetchone()
            conn.close()
            if r is not None:
                return bool(r[0])
        conn.close()
        return False
    except Exception:
        return False

def set_user_ban(telegram_id, banned, reason=""):
    try:
        updated = False
        if SUPABASE_AVAILABLE:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                # Ensure user exists
                check = supabase.table('users').select('id').eq('telegram_id', str(telegram_id)).limit(1).execute()
                if check.data:
                    try:
                        supabase.table('users').update({'is_banned': bool(banned), 'ban_reason': reason}).eq('telegram_id', str(telegram_id)).execute()
                        updated = True
                    except Exception:
                        updated = False
                # If users table update failed or columns missing, try user_bans table
                if not updated:
                    try:
                        supabase.table('user_bans').upsert({
                            'telegram_id': str(telegram_id),
                            'is_banned': bool(banned),
                            'reason': reason,
                            'updated_at': datetime.utcnow().isoformat()
                        }, on_conflict='telegram_id').execute()
                        updated = True
                    except Exception:
                        updated = False
                # Final fallback: store in bot_config as CSV list
                if not updated:
                    try:
                        cfg = supabase.table('bot_config').select('config_key,config_value').eq('config_key','banned_users').limit(1).execute()
                        ids = []
                        if cfg.data:
                            raw = cfg.data[0].get('config_value') or ''
                            ids = [s.strip() for s in str(raw).split(',') if s.strip()]
                        sid = str(telegram_id)
                        if banned:
                            if sid not in ids:
                                ids.append(sid)
                        else:
                            ids = [x for x in ids if x != sid]
                        new_val = ','.join(ids)
                        save_bot_config('banned_users', new_val)
                        if banned:
                            save_bot_config(f'ban_reason_{sid}', reason)
                        else:
                            save_bot_config(f'ban_reason_{sid}', '')
                        updated = True
                    except Exception:
                        # Update in-memory fallback as last resort
                        sid = str(telegram_id)
                        raw = BOT_CONFIG.get('banned_users') or ''
                        ids = [s.strip() for s in str(raw).split(',') if s.strip()]
                        if banned and sid not in ids:
                            ids.append(sid)
                        if not banned:
                            ids = [x for x in ids if x != sid]
                        BOT_CONFIG['banned_users'] = ','.join(ids)
                        updated = True
        if not updated:
            # SQLite fallback: best-effort add columns and update
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            try:
                cur.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE users ADD COLUMN ban_reason TEXT")
            except Exception:
                pass
            cur.execute("UPDATE users SET is_banned = ?, ban_reason = ? WHERE telegram_id = ?", (1 if banned else 0, reason, str(telegram_id)))
            conn.commit()
            conn.close()
        return True
    except Exception:
        return False

def handle_admin_ban_user(chat_id, target_telegram_id, reason):
    try:
        ok = set_user_ban(target_telegram_id, True, reason)
        if ok:
            send_telegram_message(chat_id, f"✅ Đã khóa user {target_telegram_id}")
            # notify user
            try:
                notify_msg = (
                    "❗ Tài khoản của bạn đã bị khóa\n"
                    f"📄 Lý do: {reason}\n"
                    "📞 Vui lòng liên hệ admin @meepzizhere để được hỗ trợ"
                )
                send_telegram_message(target_telegram_id, notify_msg)
            except Exception:
                pass
        else:
            send_telegram_message(chat_id, "❌ Không thể khóa user (lỗi hệ thống)")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi ban user: {str(e)}")

def handle_admin_unban_user(chat_id, target_telegram_id, reason):
    """Admin unbans a user and notifies them."""
    try:
        ok = set_user_ban(target_telegram_id, False, reason)
        if ok:
            send_telegram_message(chat_id, f"✅ Đã mở khóa user {target_telegram_id}")
            # notify user
            try:
                notify_msg = (
                    "✅ Tài khoản của bạn đã được mở khóa\n"
                    f"📄 Ghi chú: {reason}"
                )
                send_telegram_message(target_telegram_id, notify_msg)
            except Exception:
                pass
        else:
            send_telegram_message(chat_id, "❌ Không thể mở khóa user (lỗi hệ thống)")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi unban user: {str(e)}")

def admin_migrate_all_balances_to_xu(chat_id):
    """Admin tool: move all users' current balances to Xu (bonus), set CASH to 0.
    Logic per user: new_bonus = coins_bonus + coins_cash + coins; coins_cash=0; coins=new_bonus.
    """
    if not SUPABASE_AVAILABLE:
        send_telegram_message(chat_id, "❌ Supabase không khả dụng. Không thể migrate.")
        return
    try:
        from supabase_client import get_supabase_client
        client = get_supabase_client()
        if not client:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase.")
            return
        resp = client.table('users').select('id, coins, coins_cash, coins_bonus').execute()
        users = resp.data or []
        migrated = 0
        for u in users:
            uid = u.get('id')
            legacy = int(u.get('coins') or 0)
            cash = int(u.get('coins_cash') or 0)
            bonus = int(u.get('coins_bonus') or 0)
            new_bonus = bonus + cash + legacy
            update = {
                'coins_bonus': new_bonus,
                'coins_cash': 0,
                'coins': new_bonus
            }
            try:
                client.table('users').update(update).eq('id', uid).execute()
                migrated += 1
            except Exception:
                pass
        send_telegram_message(chat_id, f"✅ Đã migrate số dư cho {migrated} user: tất cả chuyển sang 🪙 Xu, CASH=0")
    except Exception as e:
        print(f"❌ Migrate to Xu error: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi migrate: {str(e)}")

def admin_migrate_cash_to_coins(chat_id):
    """Admin tool: move all users' CASH into Xu (coins), set CASH to 0."""
    if not SUPABASE_AVAILABLE:
        send_telegram_message(chat_id, "❌ Supabase không khả dụng. Không thể migrate.")
        return
    try:
        from supabase_client import get_supabase_client
        client = get_supabase_client()
        if not client:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase.")
            return
        resp = client.table('users').select('id, coins, cash').execute()
        users = resp.data or []
        migrated = 0
        for u in users:
            uid = u.get('id')
            coins = int(u.get('coins') or 0)
            cash = int(u.get('cash') or 0)
            if cash == 0:
                continue
            new_coins = coins + cash
            update = {
                'coins': new_coins,
                'cash': 0
            }
            try:
                client.table('users').update(update).eq('id', uid).execute()
                migrated += 1
            except Exception:
                pass
        send_telegram_message(chat_id, f"✅ Đã chuyển CASH→Xu cho {migrated} user. Tất cả CASH = 0")
    except Exception as e:
        print(f"❌ Migrate cash→coins error: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi migrate: {str(e)}")
def handle_admin_set_google_price(chat_id, amount_str):
    """Admin sets Google account price (Trial)"""
    try:
        amount = int(amount_str)
        if amount <= 0:
            send_telegram_message(chat_id, "❌ Giá phải > 0")
            return
        save_bot_config('google_trial_price', amount)
        BOT_CONFIG['last_updated'] = format_vietnam_time()
        send_telegram_message(chat_id, f"✅ Đã đặt giá Google Trial: {amount} CASH")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi đặt giá: {str(e)}")

def handle_admin_set_google_verify_price(chat_id, amount_str):
    """Admin sets Google verified account price"""
    try:
        amount = int(amount_str)
        if amount <= 0:
            send_telegram_message(chat_id, "❌ Giá phải > 0")
            return
        save_bot_config('google_verified_price', amount)
        BOT_CONFIG['last_updated'] = format_vietnam_time()
        send_telegram_message(chat_id, f"✅ Đã đặt giá Google Verified: {amount} CASH")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi đặt giá: {str(e)}")

def handle_admin_set_canva_price(chat_id, amount_str):
    """Admin sets Canva Admin Edu account price"""
    try:
        amount = int(amount_str)
        if amount <= 0:
            send_telegram_message(chat_id, "❌ Giá phải > 0")
            return
        save_bot_config('canva_price', amount)
        # Update in-memory cache so /shop reflects immediately
        BOT_CONFIG['canva_price'] = amount
        BOT_CONFIG['last_updated'] = format_vietnam_time()
        send_telegram_message(chat_id, f"✅ Đã đặt giá Canva Admin Edu: {amount} CASH")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi đặt giá: {str(e)}")


def handle_admin_set_vip7_price(chat_id, amount_str):
    """Admin sets VIP 7 days price"""
    try:
        amount = int(amount_str)
        if amount <= 0:
            send_telegram_message(chat_id, "❌ Giá phải > 0")
            return
        save_bot_config('vip7_price', amount)
        BOT_CONFIG['last_updated'] = format_vietnam_time()
        send_telegram_message(chat_id, f"✅ Đã đặt giá VIP 7 ngày: {amount} CASH")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi đặt giá: {str(e)}")

def handle_admin_set_vip30_price(chat_id, amount_str):
    """Admin sets VIP 30 days price"""
    try:
        amount = int(amount_str)
        if amount <= 0:
            send_telegram_message(chat_id, "❌ Giá phải > 0")
            return
        save_bot_config('vip30_price', amount)
        BOT_CONFIG['last_updated'] = format_vietnam_time()
        send_telegram_message(chat_id, f"✅ Đã đặt giá VIP 30 ngày: {amount} CASH")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi đặt giá: {str(e)}")

def handle_admin_set_account_type(chat_id, account_id, new_type):
    """Admin changes account type (trial/verified/canva/chatgpt/spotify/surfshark)"""
    try:
        if new_type not in ('trial', 'verified', 'canva', 'chatgpt', 'spotify', 'surfshark', 'perplexity'):
            send_telegram_message(chat_id, "❌ Loại tài khoản phải là 'trial', 'verified', 'canva', 'chatgpt', 'spotify', 'surfshark' hoặc 'perplexity'")
            return
        
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
            
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
            
        # Update account type
        result = supabase.table('google_accounts').update({'type': new_type}).eq('id', account_id).execute()
        
        if result.data:
            send_telegram_message(chat_id, f"✅ Đã chuyển tài khoản {account_id} thành loại {new_type}")
        else:
            send_telegram_message(chat_id, f"❌ Không tìm thấy tài khoản với ID {account_id}")
            
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi chuyển loại tài khoản: {str(e)}")

def handle_admin_fix_country(chat_id):
    """Fix country settings back to United States"""
    try:
        send_telegram_message(chat_id, "🔧 Fixing country settings...")
        
        # Correct settings
        correct_settings = {
            'current_country': 'United States',
            'current_country_flag': '🇺🇸',
            'current_university': 'University of Maryland Global Campus',
            'current_locale': 'en-US',
            'supported_country': 'United States',
            'target_country': 'United States'
        }
        
        fixed_count = 0
        removed_count = 0
        
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                
                if supabase:
                    # Remove any Vietnam configs
                    try:
                        vietnam_configs = supabase.table('bot_config').select('config_key, config_value').execute()
                        
                        for config in vietnam_configs.data:
                            key = config['config_key']
                            value = config['config_value']
                            
                            # Check if contains Vietnam references
                            if ('vietnam' in key.lower() or 
                                'vietnam' in str(value).lower() or 
                                'việt nam' in str(value).lower()):
                                
                                supabase.table('bot_config').delete().eq('config_key', key).execute()
                                print(f"🗑️ Removed Vietnam config: {key} = {value}")
                                removed_count += 1
                    except Exception as e:
                        print(f"⚠️ Error removing Vietnam configs: {e}")
                    
                    # Set correct settings
                    for key, value in correct_settings.items():
                        try:
                            supabase.table('bot_config').upsert({
                                'config_key': key,
                                'config_value': value
                            }).execute()
                            print(f"✅ Set {key} = {value}")
                            fixed_count += 1
                        except Exception as e:
                            print(f"❌ Error setting {key}: {e}")
                    
                    # Force reload config
                    global CONFIG_LOADED
                    CONFIG_LOADED = False
                    load_bot_config(force_reload=True)
                    
                    message = f"""✅ Country settings fixed!

🔧 Actions taken:
• Removed {removed_count} Vietnam configs
• Set {fixed_count} US configs

🇺🇸 Current settings:
• Country: United States
• Flag: 🇺🇸
• University: University of Maryland Global Campus
• Locale: en-US

💡 Test with /status to verify"""
                    
                    send_telegram_message(chat_id, message)
                else:
                    send_telegram_message(chat_id, "❌ Supabase client not available")
            except Exception as e:
                send_telegram_message(chat_id, f"❌ Supabase error: {e}")
        else:
            # Fallback: Update in-memory config
            global BOT_CONFIG
            for key, value in correct_settings.items():
                BOT_CONFIG[key] = value
                fixed_count += 1
            
            send_telegram_message(chat_id, f"✅ Fixed {fixed_count} settings in memory (Supabase not available)")
            
    except Exception as e:
        print(f"❌ Error in handle_admin_fix_country: {e}")
        send_telegram_message(chat_id, f"❌ Error fixing country: {e}")

def handle_admin_create_config_table(chat_id):
    """Admin creates bot_config table"""
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        
        # Try to create table first (this will fail if table exists, which is fine)
        try:
            # Create table using raw SQL
            create_sql = """
            CREATE TABLE IF NOT EXISTS public.bot_config (
                id SERIAL PRIMARY KEY,
                config_key VARCHAR(255) UNIQUE NOT NULL,
                config_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
            # Use RPC to execute SQL
            supabase.rpc('exec_sql', {'sql': create_sql}).execute()
            send_telegram_message(chat_id, "✅ Đã tạo bảng bot_config")
        except Exception as e:
            print(f"Table creation error (may already exist): {e}")
        
        # Insert default values
        default_configs = [
            ('google_trial_price', '4'),
            ('google_verified_price', '6'),
            ('vip1_price', '30'),
            ('vip7_price', '150'),
            ('vip30_price', '300')
        ]
        
        for key, value in default_configs:
            try:
                supabase.table('bot_config').upsert({
                    'config_key': key,
                    'config_value': value
                }).execute()
            except Exception as e:
                print(f"Error inserting {key}: {e}")
        
        send_telegram_message(chat_id, "✅ Đã thêm giá mặc định vào bot_config")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi tạo bảng: {str(e)}")

def handle_admin_stock(chat_id):
    """Show available stock count from Supabase table google_accounts"""
    try:
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        resp = supabase.table('google_accounts').select('id', count='exact').eq('status','available').execute()
        count = resp.count or 0
        send_telegram_message(chat_id, f"📦 Kho còn: {count} tài khoản AVAILABLE")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi kiểm tra kho: {str(e)}")
def handle_shop_command(chat_id):
    """Show shop items and prices"""
    try:
        price_trial = int(BOT_CONFIG.get('google_trial_price', 0) or 0)
        price_verified = int(BOT_CONFIG.get('google_verified_price', 0) or 0)
        # Defaults ensure immediate correct display even before admin sets
        price_canva = int(BOT_CONFIG.get('canva_price', 0) or 0)
        price_ai_ultra = int(BOT_CONFIG.get('ai_ultra_price', 0) or 0)
        price_ai_ultra45 = int(BOT_CONFIG.get('ai_ultra45_price', 200) or 200)  # Default 200 CASH
        price_spotify = int(BOT_CONFIG.get('spotify_price', 0) or 0)
        price_surfshark = int(BOT_CONFIG.get('surfshark_price', 0) or 0)
        price_perplexity = int(BOT_CONFIG.get('perplexity_price', 0) or 0)
        price_perplexity1m = int(BOT_CONFIG.get('perplexity1m_price', 10) or 10)  # Default 10 CASH
        price_ai_ultra45 = int(BOT_CONFIG.get('ai_ultra45_price', 200) or 200)  # Default 200 CASH
        price_gpt1m = int(BOT_CONFIG.get('gpt1m_price', 15) or 15)  # Default 15 CASH
        price_m365 = int(BOT_CONFIG.get('m365_price', 15) or 15)  # Default 15 CASH
        price_adobe4m = int(BOT_CONFIG.get('adobe4m_price', 20) or 20)  # Default 20 CASH
        # VIP member prices (optional)
        vip_price_trial = float(BOT_CONFIG.get('google_trial_price_vip', 0) or 0)
        vip_price_verified = float(BOT_CONFIG.get('google_verified_price_vip', 0) or 0)
        vip_price_canva = float(BOT_CONFIG.get('canva_price_vip', 0) or 0)
        vip_price_ai_ultra = float(BOT_CONFIG.get('ai_ultra_price_vip', 0) or 0)
        vip_price_ai_ultra45 = float(BOT_CONFIG.get('ai_ultra45_price_vip', 190) or 190)  # Default 190 CASH for VIP
        vip_price_chatgpt = float(BOT_CONFIG.get('chatgpt_price_vip', 0) or 0)
        vip_price_spotify = float(BOT_CONFIG.get('spotify_price_vip', 0) or 0)
        vip_price_surfshark = float(BOT_CONFIG.get('surfshark_price_vip', 0) or 0)
        vip_price_perplexity = float(BOT_CONFIG.get('perplexity_price_vip', 0) or 0)
        vip_price_perplexity1m = float(BOT_CONFIG.get('perplexity1m_price_vip', 9) or 9)  # Default 9 CASH for VIP
        vip_price_gpt1m = float(BOT_CONFIG.get('gpt1m_price_vip', 12) or 12)  # Default 12 CASH for VIP
        vip_price_m365 = float(BOT_CONFIG.get('m365_price_vip', 12) or 12)  # Default 12 CASH for VIP
        vip_price_adobe4m = float(BOT_CONFIG.get('adobe4m_price_vip', 18) or 18)  # Default 18 CASH for VIP
        
        # Format VIP prices to remove .0 for whole numbers
        def format_vip_price(price):
            if price == int(price):
                return str(int(price))
            return str(price)
        vip1 = int(BOT_CONFIG.get('vip1_price', 0) or 0)
        vip7 = int(BOT_CONFIG.get('vip7_price', 0) or 0)
        vip30 = int(BOT_CONFIG.get('vip30_price', 0) or 0)

        total_trial = 0
        total_verified = 0
        total_canva = 0
        total_ultra = 0
        total_ultra45 = 0
        total_chatgpt = 0
        total_spotify = 0
        total_surfshark = 0
        total_perplexity = 0
        total_perplexity1m = 0
        total_gpt1m = 0
        total_m365 = 0
        total_adobe4m = 0
        sold_trial = 0
        sold_verified = 0
        sold_canva = 0
        sold_ultra = 0
        sold_ultra45 = 0
        sold_chatgpt = 0
        sold_spotify = 0
        sold_surfshark = 0
        sold_perplexity = 0
        sold_perplexity1m = 0
        sold_gpt1m = 0
        sold_m365 = 0
        sold_adobe4m = 0
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                
                # Batch all count queries for better performance
                def get_counts(supabase):
                    counts = {}
                    # Trial accounts
                    c1 = supabase.table('google_accounts').select('id', count='exact').eq('status','AVAILABLE').eq('type','trial').execute()
                    counts['trial_available'] = c1.count or 0
                    if counts['trial_available'] == 0:
                        c1 = supabase.table('google_accounts').select('id', count='exact').eq('status','available').eq('type','trial').execute()
                        counts['trial_available'] = c1.count or 0
                    
                    # Verified accounts
                    c2 = supabase.table('google_accounts').select('id', count='exact').eq('status','AVAILABLE').eq('type','verified').execute()
                    counts['verified_available'] = c2.count or 0
                    if counts['verified_available'] == 0:
                        c2 = supabase.table('google_accounts').select('id', count='exact').eq('status','available').eq('type','verified').execute()
                        counts['verified_available'] = c2.count or 0
                    
                    # Canva accounts
                    c3 = supabase.table('google_accounts').select('id', count='exact').eq('status','AVAILABLE').eq('type','canva').execute()
                    counts['canva_available'] = c3.count or 0
                    if counts['canva_available'] == 0:
                        c3 = supabase.table('google_accounts').select('id', count='exact').eq('status','available').eq('type','canva').execute()
                        counts['canva_available'] = c3.count or 0
                    
                    # Ultra accounts
                    c4 = supabase.table('google_accounts').select('id', count='exact').eq('status','AVAILABLE').eq('type','ultra').execute()
                    counts['ultra_available'] = c4.count or 0
                    if counts['ultra_available'] == 0:
                        c4 = supabase.table('google_accounts').select('id', count='exact').eq('status','available').eq('type','ultra').execute()
                        counts['ultra_available'] = c4.count or 0
                    
                    # Ultra 45k accounts
                    c4_45 = supabase.table('google_accounts').select('id', count='exact').eq('status','AVAILABLE').eq('type','ultra45').execute()
                    counts['ultra45_available'] = c4_45.count or 0
                    if counts['ultra45_available'] == 0:
                        c4_45 = supabase.table('google_accounts').select('id', count='exact').eq('status','available').eq('type','ultra45').execute()
                        counts['ultra45_available'] = c4_45.count or 0
                    
                    # ChatGPT accounts
                    c5 = supabase.table('google_accounts').select('id', count='exact').eq('status','AVAILABLE').eq('type','chatgpt').execute()
                    counts['chatgpt_available'] = c5.count or 0
                    if counts['chatgpt_available'] == 0:
                        c5 = supabase.table('google_accounts').select('id', count='exact').eq('status','available').eq('type','chatgpt').execute()
                        counts['chatgpt_available'] = c5.count or 0
                    
                    # Spotify accounts
                    c6 = supabase.table('google_accounts').select('id', count='exact').eq('status','AVAILABLE').eq('type','spotify').execute()
                    counts['spotify_available'] = c6.count or 0
                    if counts['spotify_available'] == 0:
                        c6 = supabase.table('google_accounts').select('id', count='exact').eq('status','available').eq('type','spotify').execute()
                        counts['spotify_available'] = c6.count or 0
                    
                    # Surfshark accounts
                    c7 = supabase.table('google_accounts').select('id', count='exact').eq('status','AVAILABLE').eq('type','surfshark').execute()
                    counts['surfshark_available'] = c7.count or 0
                    if counts['surfshark_available'] == 0:
                        c7 = supabase.table('google_accounts').select('id', count='exact').eq('status','available').eq('type','surfshark').execute()
                        counts['surfshark_available'] = c7.count or 0
                    
                    # Perplexity accounts
                    c8 = supabase.table('google_accounts').select('id', count='exact').eq('status','AVAILABLE').eq('type','perplexity').execute()
                    counts['perplexity_available'] = c8.count or 0
                    if counts['perplexity_available'] == 0:
                        c8 = supabase.table('google_accounts').select('id', count='exact').eq('status','available').eq('type','perplexity').execute()
                        counts['perplexity_available'] = c8.count or 0
                    
                    # Perplexity 1 Month accounts
                    c9 = supabase.table('google_accounts').select('id', count='exact').eq('status','AVAILABLE').eq('type','perplexity1m').execute()
                    counts['perplexity1m_available'] = c9.count or 0
                    if counts['perplexity1m_available'] == 0:
                        c9 = supabase.table('google_accounts').select('id', count='exact').eq('status','available').eq('type','perplexity1m').execute()
                        counts['perplexity1m_available'] = c9.count or 0
                    
                    # ChatGPT Code 1 Month accounts
                    c9b = supabase.table('google_accounts').select('id', count='exact').eq('status','AVAILABLE').eq('type','gpt1m').execute()
                    counts['gpt1m_available'] = c9b.count or 0
                    if counts['gpt1m_available'] == 0:
                        c9b = supabase.table('google_accounts').select('id', count='exact').eq('status','available').eq('type','gpt1m').execute()
                        counts['gpt1m_available'] = c9b.count or 0
                    
                    # Microsoft 365 accounts
                    c10 = supabase.table('google_accounts').select('id', count='exact').eq('status','AVAILABLE').eq('type','m365').execute()
                    counts['m365_available'] = c10.count or 0
                    if counts['m365_available'] == 0:
                        c10 = supabase.table('google_accounts').select('id', count='exact').eq('status','available').eq('type','m365').execute()
                        counts['m365_available'] = c10.count or 0
                    
                    # Adobe 4 Months accounts
                    c11 = supabase.table('google_accounts').select('id', count='exact').eq('status','AVAILABLE').eq('type','adobe4m').execute()
                    counts['adobe4m_available'] = c11.count or 0
                    if counts['adobe4m_available'] == 0:
                        c11 = supabase.table('google_accounts').select('id', count='exact').eq('status','available').eq('type','adobe4m').execute()
                        counts['adobe4m_available'] = c11.count or 0
                    
                    return counts
                
                counts = get_counts(supabase)
                total_trial = counts.get('trial_available', 0)
                total_verified = counts.get('verified_available', 0)
                total_canva = counts.get('canva_available', 0)
                total_ultra = counts.get('ultra_available', 0)
                total_ultra45 = counts.get('ultra45_available', 0)
                total_chatgpt = counts.get('chatgpt_available', 0)
                total_spotify = counts.get('spotify_available', 0)
                total_surfshark = counts.get('surfshark_available', 0)
                total_perplexity = counts.get('perplexity_available', 0)
                total_perplexity1m = counts.get('perplexity1m_available', 0)
                total_gpt1m = counts.get('gpt1m_available', 0)
                total_m365 = counts.get('m365_available', 0)
                total_adobe4m = counts.get('adobe4m_available', 0)
                
                # Count sold items from google_accounts table
                try:
                    # Count sold items by type and status='SOLD'
                    trial_sold = supabase.table('google_accounts').select('id', count='exact').eq('status','SOLD').eq('type','trial').execute()
                    sold_trial = trial_sold.count or 0
                    
                    verified_sold = supabase.table('google_accounts').select('id', count='exact').eq('status','SOLD').eq('type','verified').execute()
                    sold_verified = verified_sold.count or 0
                    
                    canva_sold = supabase.table('google_accounts').select('id', count='exact').eq('status','SOLD').eq('type','canva').execute()
                    sold_canva = canva_sold.count or 0
                    
                    ultra_sold = supabase.table('google_accounts').select('id', count='exact').eq('status','SOLD').eq('type','ultra').execute()
                    sold_ultra = ultra_sold.count or 0
                    
                    ultra45_sold = supabase.table('google_accounts').select('id', count='exact').eq('status','SOLD').eq('type','ultra45').execute()
                    sold_ultra45 = ultra45_sold.count or 0
                    
                    chatgpt_sold = supabase.table('google_accounts').select('id', count='exact').eq('status','SOLD').eq('type','chatgpt').execute()
                    sold_chatgpt = chatgpt_sold.count or 0
                    
                    spotify_sold = supabase.table('google_accounts').select('id', count='exact').eq('status','SOLD').eq('type','spotify').execute()
                    sold_spotify = spotify_sold.count or 0
                    
                    surfshark_sold = supabase.table('google_accounts').select('id', count='exact').eq('status','SOLD').eq('type','surfshark').execute()
                    sold_surfshark = surfshark_sold.count or 0
                    
                    perplexity_sold = supabase.table('google_accounts').select('id', count='exact').eq('status','SOLD').eq('type','perplexity').execute()
                    sold_perplexity = perplexity_sold.count or 0
                    
                    perplexity1m_sold = supabase.table('google_accounts').select('id', count='exact').eq('status','SOLD').eq('type','perplexity1m').execute()
                    sold_perplexity1m = perplexity1m_sold.count or 0
                    
                    gpt1m_sold = supabase.table('google_accounts').select('id', count='exact').eq('status','SOLD').eq('type','gpt1m').execute()
                    sold_gpt1m = gpt1m_sold.count or 0
                    
                    m365_sold = supabase.table('google_accounts').select('id', count='exact').eq('status','SOLD').eq('type','m365').execute()
                    sold_m365 = m365_sold.count or 0
                    
                    adobe4m_sold = supabase.table('google_accounts').select('id', count='exact').eq('status','SOLD').eq('type','adobe4m').execute()
                    sold_adobe4m = adobe4m_sold.count or 0
                except Exception as e:
                    print(f"Error counting sold items: {e}")
                    sold_trial = 0
                    sold_verified = 0
                    sold_canva = 0
                    sold_ultra = 0
                    sold_ultra45 = 0
                    sold_chatgpt = 0
                    sold_spotify = 0
                    sold_surfshark = 0
                    sold_perplexity = 0
                    sold_perplexity1m = 0
                    sold_gpt1m = 0
                    sold_perplexity1m = 0
                    sold_m365 = 0
                    sold_adobe4m = 0
            except Exception as e:
                print(f"Error getting counts: {e}")
                # Fallback values
                total_trial = 0
                total_verified = 0
                total_canva = 0
                total_ultra = 0
                total_ultra45 = 0
                total_chatgpt = 0
                total_spotify = 0
                total_surfshark = 0
                total_perplexity = 0
                total_perplexity1m = 0
                total_m365 = 0
                total_adobe4m = 0
                sold_trial = 0
                sold_verified = 0
                sold_canva = 0
                sold_ultra = 0
                sold_ultra45 = 0
                sold_chatgpt = 0
                sold_spotify = 0
                sold_surfshark = 0
                sold_perplexity = 0
                sold_perplexity1m = 0
                sold_m365 = 0
                sold_adobe4m = 0

        # Compose price lines with VIP if configured
        trial_line = (
            f"1) 🌱 Google có tỷ lệ Trial\n   📦 Kho: {total_trial} | 🛒 Đã bán: {sold_trial}\n   💵 Giá: {price_trial} cash"
            + (f" | 👑 VIP: {format_vip_price(vip_price_trial)} cash" if vip_price_trial > 0 else "") + "\n\n"
        )
        verified_line = (
            f"2) ✅ Google Verified\n   📦 Kho: {total_verified} | 🛒 Đã bán: {sold_verified}\n   💵 Giá: {price_verified} cash"
            + (f" | 👑 VIP: {format_vip_price(vip_price_verified)} cash" if vip_price_verified > 0 else "") + "\n\n"
        )
        canva_line = (
            f"3) 🎨 Canva Admin Edu\n   📦 Kho: {total_canva} | 🛒 Đã bán: {sold_canva}\n   💵 Giá: {price_canva} cash"
            + (f" | 👑 VIP: {format_vip_price(vip_price_canva)} cash" if vip_price_canva > 0 else "") + "\n\n"
        )
        ai_ultra_line = (
            f"4) 🤖 Google AI ULTRA 25k Credits\n   📦 Kho: {total_ultra} | 🛒 Đã bán: {sold_ultra}\n   💵 Giá: {price_ai_ultra} cash"
            + (f" | 👑 VIP: {format_vip_price(vip_price_ai_ultra)} cash" if vip_price_ai_ultra > 0 else "") + "\n\n"
        )
        ai_ultra45_line = (
            f"5) 🤖 Google AI ULTRA 45k Credits\n   📦 Kho: {total_ultra45} | 🛒 Đã bán: {sold_ultra45}\n   💵 Giá: {price_ai_ultra45} cash"
            + (f" | 👑 VIP: {format_vip_price(vip_price_ai_ultra45)} cash" if vip_price_ai_ultra45 > 0 else "") + "\n\n"
        )
        chatgpt_line = (
            f"6) 💬 ChatGPT Plus 3 Months\n   📦 Kho: {total_chatgpt} | 🛒 Đã bán: {sold_chatgpt}\n   💵 Giá: {int(BOT_CONFIG.get('chatgpt_price', 0) or 0)} cash"
            + (f" | 👑 VIP: {format_vip_price(vip_price_chatgpt)} cash" if vip_price_chatgpt > 0 else "") + "\n\n"
        )
        spotify_line = (
            f"7) 🎵 Spotify Premium 4M CODE\n   📦 Kho: {total_spotify} | 🛒 Đã bán: {sold_spotify}\n   💵 Giá: {price_spotify} cash"
            + (f" | 👑 VIP: {format_vip_price(vip_price_spotify)} cash" if vip_price_spotify > 0 else "") + "\n\n"
        )
        surfshark_line = (
            f"8) 🦈 Surfshark VPN Premium 2 Month CODE\n   📦 Kho: {total_surfshark} | 🛒 Đã bán: {sold_surfshark}\n   💵 Giá: {price_surfshark} cash"
            + (f" | 👑 VIP: {format_vip_price(vip_price_surfshark)} cash" if vip_price_surfshark > 0 else "") + "\n\n"
        )
        perplexity_line = (
            f"9) 🧠 Perplexity PRO 1 Năm\n   📦 Kho: {total_perplexity} | 🛒 Đã bán: {sold_perplexity}\n   💵 Giá: {price_perplexity} cash"
            + (f" | 👑 VIP: {format_vip_price(vip_price_perplexity)} cash" if vip_price_perplexity > 0 else "") + "\n\n"
        )
        perplexity1m_line = (
            f"10) 🧠 Perplexity PRO 1 Month\n   📦 Kho: {total_perplexity1m} | 🛒 Đã bán: {sold_perplexity1m}\n   💵 Giá: {price_perplexity1m} cash"
            + (f" | 👑 VIP: {format_vip_price(vip_price_perplexity1m)} cash" if vip_price_perplexity1m > 0 else "") + "\n\n"
        )
        gpt1m_line = (
            f"11) 🤖 ChatGPT Code 1 Month\n   📦 Kho: {total_gpt1m} | 🛒 Đã bán: {sold_gpt1m}\n   💵 Giá: {price_gpt1m} cash"
            + (f" | 👑 VIP: {format_vip_price(vip_price_gpt1m)} cash" if vip_price_gpt1m > 0 else "") + "\n\n"
        )
        m365_line = (
            f"12) 💼 Tài khoản Microsoft 365 Personal 1 Năm\n   📦 Kho: {total_m365} | 🛒 Đã bán: {sold_m365}\n   💵 Giá: {price_m365} cash"
            + (f" | 👑 VIP: {format_vip_price(vip_price_m365)} cash" if vip_price_m365 > 0 else "") + "\n\n"
        )
        adobe4m_line = (
            f"13) 🎨 ADOBE FULL APP 4 Months\n   📦 Kho: {total_adobe4m} | 🛒 Đã bán: {sold_adobe4m}\n   💵 Giá: {price_adobe4m} cash"
            + (f" | 👑 VIP: {format_vip_price(vip_price_adobe4m)} cash" if vip_price_adobe4m > 0 else "") + "\n\n"
        )
        
        print(f"🔍 DEBUG: perplexity1m_line = {perplexity1m_line}")
        print(f"🔍 DEBUG: price_perplexity1m = {price_perplexity1m}")
        print(f"🔍 DEBUG: total_perplexity1m = {total_perplexity1m}")
        print(f"🔍 DEBUG: sold_perplexity1m = {sold_perplexity1m}")

        print(f"🔍 DEBUG: About to construct shop message...")
        print(f"🔍 DEBUG: perplexity1m_line exists: {bool(perplexity1m_line)}")
        
        message = (
            "🛍️ SHOP\n\n"
            + trial_line
            + verified_line
            + canva_line
            + ai_ultra_line
            + ai_ultra45_line
            + chatgpt_line
            + spotify_line
            + surfshark_line
            + perplexity_line
            + perplexity1m_line
            + gpt1m_line
            + m365_line
            + adobe4m_line
            + f"14) ⭐ VIP Basic 7 ngày (1 link)\n   💵 Giá: 1200 cash (48 USDT)\n\n"
            + f"15) ⭐ VIP Pro 7 ngày (3 link song song)\n   💵 Giá: 1800 cash (72 USDT)\n\n"
            + f"16) ⭐ VIP Business 7 ngày (5 link song song)\n   💵 Giá: 2400 cash (96 USDT)\n\n"
            + "Lệnh nhanh:\n"
            + "• /mua trial <số_lượng>\n"
            + "• /mua verified <số_lượng>\n"
            + "• /mua canva <số_lượng>\n"
            + "• /mua ultra <số_lượng>\n"
            + "• /mua aiultra45 <số_lượng>\n"
            + "• /mua chatgpt <số_lượng>\n"
            + "• /mua spotify <số_lượng>\n"
            + "• /mua vpnss <số_lượng>\n"
            + "• /mua per <số_lượng>\n"
            + "• /mua per1m <số_lượng>\n"
            + "• /mua gpt1m <số_lượng>\n"
            + "• /mua m365 <số_lượng>\n"
            + "• /mua adobe4m <số_lượng>\n"
            + "• /mua vip7 | /mua vippro7 | /mua vipbiz7\n"
            + "\n💡 Xem chi tiết VIP: /vip"
        )
        
        print(f"🔍 DEBUG: Final message length: {len(message)}")
        print(f"🔍 DEBUG: Message contains 'Perplexity PRO 1 Month': {'Perplexity PRO 1 Month' in message}")
        print(f"🔍 DEBUG: Sending shop message to {chat_id}")
        
        # Create inline keyboard with language options
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🇺🇸 English", "callback_data": "shop_en"},
                    {"text": "🇹🇷 Türkçe", "callback_data": "shop_tr"}
                ]
            ]
        }
        
        send_telegram_message_with_keyboard(chat_id, message, keyboard["inline_keyboard"])
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi shop: {str(e)}")

def handle_shop_command_en(chat_id):
    """Show shop items and prices in English"""
    try:
        # Get prices from BOT_CONFIG
        price_trial = int(BOT_CONFIG.get('google_trial_price', 0) or 0)
        price_verified = int(BOT_CONFIG.get('google_verified_price', 0) or 0)
        price_canva = int(BOT_CONFIG.get('canva_price', 0) or 0)
        price_ai_ultra = int(BOT_CONFIG.get('ai_ultra_price', 0) or 0)
        price_ai_ultra45 = int(BOT_CONFIG.get('ai_ultra45_price', 200) or 200)
        price_chatgpt = int(BOT_CONFIG.get('chatgpt_price', 0) or 0)
        price_spotify = int(BOT_CONFIG.get('spotify_price', 0) or 0)
        price_surfshark = int(BOT_CONFIG.get('surfshark_price', 0) or 0)
        price_perplexity = int(BOT_CONFIG.get('perplexity_price', 0) or 0)
        price_perplexity1m = int(BOT_CONFIG.get('perplexity1m_price', 10) or 10)
        price_m365 = int(BOT_CONFIG.get('m365_price', 15) or 15)
        
        # VIP prices
        vip_price_trial = float(BOT_CONFIG.get('google_trial_price_vip', 0) or 0)
        vip_price_verified = float(BOT_CONFIG.get('google_verified_price_vip', 0) or 0)
        vip_price_canva = float(BOT_CONFIG.get('canva_price_vip', 0) or 0)
        vip_price_ai_ultra = float(BOT_CONFIG.get('ai_ultra_price_vip', 0) or 0)
        vip_price_ai_ultra45 = float(BOT_CONFIG.get('ai_ultra45_price_vip', 190) or 190)
        vip_price_chatgpt = float(BOT_CONFIG.get('chatgpt_price_vip', 0) or 0)
        vip_price_spotify = float(BOT_CONFIG.get('spotify_price_vip', 0) or 0)
        vip_price_surfshark = float(BOT_CONFIG.get('surfshark_price_vip', 0) or 0)
        vip_price_perplexity = float(BOT_CONFIG.get('perplexity_price_vip', 0) or 0)
        vip_price_perplexity1m = float(BOT_CONFIG.get('perplexity1m_price_vip', 9) or 9)
        vip_price_m365 = float(BOT_CONFIG.get('m365_price_vip', 12) or 12)
        
        vip7 = int(BOT_CONFIG.get('vip7_price', 0) or 0)
        vip30 = int(BOT_CONFIG.get('vip30_price', 0) or 0)
        
        # Format VIP prices
        def format_vip_price(price):
            if price == int(price):
                return str(int(price))
            return str(price)
        
        message = f"""🛍️ **SHOP - ENGLISH**

🎓 **Google Accounts & Services:**
1) 🎓 Google Trial - Basic account
   💵 Price: {price_trial} cash{f" | 👑 VIP: {format_vip_price(vip_price_trial)} cash" if vip_price_trial > 0 else ""}

2) ✅ Google Verified - Verified account
   💵 Price: {price_verified} cash{f" | 👑 VIP: {format_vip_price(vip_price_verified)} cash" if vip_price_verified > 0 else ""}

3) 🎨 Canva Admin Edu - Design platform
   💵 Price: {price_canva} cash{f" | 👑 VIP: {format_vip_price(vip_price_canva)} cash" if vip_price_canva > 0 else ""}

4) 🤖 Google AI ULTRA 25k Credits - AI service
   💵 Price: {price_ai_ultra} cash{f" | 👑 VIP: {format_vip_price(vip_price_ai_ultra)} cash" if vip_price_ai_ultra > 0 else ""}

5) 🤖 Google AI ULTRA 45k Credits - Enhanced AI service
   💵 Price: {price_ai_ultra45} cash{f" | 👑 VIP: {format_vip_price(vip_price_ai_ultra45)} cash" if vip_price_ai_ultra45 > 0 else ""}

6) 💬 ChatGPT Plus 3 Months - AI assistant
   💵 Price: {price_chatgpt} cash{f" | 👑 VIP: {format_vip_price(vip_price_chatgpt)} cash" if vip_price_chatgpt > 0 else ""}

7) 🎵 Spotify Premium - Music streaming
   💵 Price: {price_spotify} cash{f" | 👑 VIP: {format_vip_price(vip_price_spotify)} cash" if vip_price_spotify > 0 else ""}

8) 🦈 Surfshark VPN Premium 2 Month - VPN service
   💵 Price: {price_surfshark} cash{f" | 👑 VIP: {format_vip_price(vip_price_surfshark)} cash" if vip_price_surfshark > 0 else ""}

9) 🧠 Perplexity PRO 1 Year - AI search
   💵 Price: {price_perplexity} cash{f" | 👑 VIP: {format_vip_price(vip_price_perplexity)} cash" if vip_price_perplexity > 0 else ""}

10) 🧠 Perplexity PRO 1 Month - AI search (monthly)
   💵 Price: {price_perplexity1m} cash{f" | 👑 VIP: {format_vip_price(vip_price_perplexity1m)} cash" if vip_price_perplexity1m > 0 else ""}

11) 💼 Microsoft 365 Personal 1 Year - Office suite
   💵 Price: {price_m365} cash{f" | 👑 VIP: {format_vip_price(vip_price_m365)} cash" if vip_price_m365 > 0 else ""}

12) 🎨 ADOBE FULL APP 4 Months - Creative suite
   💵 Price: {price_adobe4m} cash{f" | 👑 VIP: {format_vip_price(vip_price_adobe4m)} cash" if vip_price_adobe4m > 0 else ""}

⭐ **VIP Memberships:**
13) ⭐ VIP 7 days - Premium access
   💵 Price: {vip7} cash

14) ⭐ VIP 30 days - Extended premium access
   💵 Price: {vip30} cash

💡 **Quick Commands:**
• /mua trial <quantity>
• /mua verified <quantity>
• /mua canva <quantity>
• /mua ultra <quantity>
• /mua aiultra45 <quantity>
• /mua chatgpt <quantity>
• /mua spotify <quantity>
• /mua vpnss <quantity>
• /mua per <quantity>
• /mua per1m <quantity>
• /mua m365 <quantity>
• /mua adobe4m <quantity>
• /mua vip7 | /mua vip30

🆘 **Support:** @meepzizhere
📢 **Channel:** https://t.me/channel_sheerid_vip_bot"""
        
        send_telegram_message(chat_id, message)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Shop error: {str(e)}")

def handle_shop_command_tr(chat_id):
    """Show shop items and prices in Turkish"""
    try:
        # Get prices from BOT_CONFIG
        price_trial = int(BOT_CONFIG.get('google_trial_price', 0) or 0)
        price_verified = int(BOT_CONFIG.get('google_verified_price', 0) or 0)
        price_canva = int(BOT_CONFIG.get('canva_price', 0) or 0)
        price_ai_ultra = int(BOT_CONFIG.get('ai_ultra_price', 0) or 0)
        price_ai_ultra45 = int(BOT_CONFIG.get('ai_ultra45_price', 200) or 200)
        price_chatgpt = int(BOT_CONFIG.get('chatgpt_price', 0) or 0)
        price_spotify = int(BOT_CONFIG.get('spotify_price', 0) or 0)
        price_surfshark = int(BOT_CONFIG.get('surfshark_price', 0) or 0)
        price_perplexity = int(BOT_CONFIG.get('perplexity_price', 0) or 0)
        price_perplexity1m = int(BOT_CONFIG.get('perplexity1m_price', 10) or 10)
        price_m365 = int(BOT_CONFIG.get('m365_price', 15) or 15)
        price_adobe4m = int(BOT_CONFIG.get('adobe4m_price', 20) or 20)
        
        # VIP prices
        vip_price_trial = float(BOT_CONFIG.get('google_trial_price_vip', 0) or 0)
        vip_price_verified = float(BOT_CONFIG.get('google_verified_price_vip', 0) or 0)
        vip_price_canva = float(BOT_CONFIG.get('canva_price_vip', 0) or 0)
        vip_price_ai_ultra = float(BOT_CONFIG.get('ai_ultra_price_vip', 0) or 0)
        vip_price_ai_ultra45 = float(BOT_CONFIG.get('ai_ultra45_price_vip', 190) or 190)
        vip_price_chatgpt = float(BOT_CONFIG.get('chatgpt_price_vip', 0) or 0)
        vip_price_spotify = float(BOT_CONFIG.get('spotify_price_vip', 0) or 0)
        vip_price_surfshark = float(BOT_CONFIG.get('surfshark_price_vip', 0) or 0)
        vip_price_perplexity = float(BOT_CONFIG.get('perplexity_price_vip', 0) or 0)
        vip_price_perplexity1m = float(BOT_CONFIG.get('perplexity1m_price_vip', 9) or 9)
        vip_price_m365 = float(BOT_CONFIG.get('m365_price_vip', 12) or 12)
        vip_price_adobe4m = float(BOT_CONFIG.get('adobe4m_price_vip', 18) or 18)
        
        vip7 = int(BOT_CONFIG.get('vip7_price', 0) or 0)
        vip30 = int(BOT_CONFIG.get('vip30_price', 0) or 0)
        
        # Format VIP prices
        def format_vip_price(price):
            if price == int(price):
                return str(int(price))
            return str(price)
        
        message = f"""🛍️ **MAĞAZA - TÜRKÇE**

🎓 **Google Hesapları ve Hizmetler:**
1) 🎓 Google Trial - Temel hesap
   💵 Fiyat: {price_trial} cash{f" | 👑 VIP: {format_vip_price(vip_price_trial)} cash" if vip_price_trial > 0 else ""}

2) ✅ Google Verified - Doğrulanmış hesap
   💵 Fiyat: {price_verified} cash{f" | 👑 VIP: {format_vip_price(vip_price_verified)} cash" if vip_price_verified > 0 else ""}

3) 🎨 Canva Admin Edu - Tasarım platformu
   💵 Fiyat: {price_canva} cash{f" | 👑 VIP: {format_vip_price(vip_price_canva)} cash" if vip_price_canva > 0 else ""}

4) 🤖 Google AI ULTRA 25k Credits - AI hizmeti
   💵 Fiyat: {price_ai_ultra} cash{f" | 👑 VIP: {format_vip_price(vip_price_ai_ultra)} cash" if vip_price_ai_ultra > 0 else ""}

5) 🤖 Google AI ULTRA 45k Credits - Gelişmiş AI hizmeti
   💵 Fiyat: {price_ai_ultra45} cash{f" | 👑 VIP: {format_vip_price(vip_price_ai_ultra45)} cash" if vip_price_ai_ultra45 > 0 else ""}

6) 💬 ChatGPT Plus 3 Ay - AI asistanı
   💵 Fiyat: {price_chatgpt} cash{f" | 👑 VIP: {format_vip_price(vip_price_chatgpt)} cash" if vip_price_chatgpt > 0 else ""}

7) 🎵 Spotify Premium - Müzik akışı
   💵 Fiyat: {price_spotify} cash{f" | 👑 VIP: {format_vip_price(vip_price_spotify)} cash" if vip_price_spotify > 0 else ""}

8) 🦈 Surfshark VPN Premium 2 Ay - VPN hizmeti
   💵 Fiyat: {price_surfshark} cash{f" | 👑 VIP: {format_vip_price(vip_price_surfshark)} cash" if vip_price_surfshark > 0 else ""}

9) 🧠 Perplexity PRO 1 Yıl - AI arama
   💵 Fiyat: {price_perplexity} cash{f" | 👑 VIP: {format_vip_price(vip_price_perplexity)} cash" if vip_price_perplexity > 0 else ""}

10) 🧠 Perplexity PRO 1 Ay - AI arama (aylık)
   💵 Fiyat: {price_perplexity1m} cash{f" | 👑 VIP: {format_vip_price(vip_price_perplexity1m)} cash" if vip_price_perplexity1m > 0 else ""}

11) 💼 Microsoft 365 Personal 1 Yıl - Ofis paketi
   💵 Fiyat: {price_m365} cash{f" | 👑 VIP: {format_vip_price(vip_price_m365)} cash" if vip_price_m365 > 0 else ""}

12) 🎨 ADOBE FULL APP 4 Ay - Yaratıcı paket
   💵 Fiyat: {price_adobe4m} cash{f" | 👑 VIP: {format_vip_price(vip_price_adobe4m)} cash" if vip_price_adobe4m > 0 else ""}

⭐ **VIP Üyelikler:**
13) ⭐ VIP 7 gün - Premium erişim
   💵 Fiyat: {vip7} cash

14) ⭐ VIP 30 gün - Uzatılmış premium erişim
   💵 Fiyat: {vip30} cash

💡 **Hızlı Komutlar:**
• /mua trial <miktar>
• /mua verified <miktar>
• /mua canva <miktar>
• /mua ultra <miktar>
• /mua aiultra45 <miktar>
• /mua chatgpt <miktar>
• /mua spotify <miktar>
• /mua vpnss <miktar>
• /mua per <miktar>
• /mua per1m <miktar>
• /mua m365 <miktar>
• /mua adobe4m <miktar>
• /mua vip7 | /mua vip30

🆘 **Destek:** @meepzizhere
📢 **Kanal:** https://t.me/channel_sheerid_vip_bot"""
        
        send_telegram_message(chat_id, message)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Mağaza hatası: {str(e)}")

def handle_admin_import_csv(chat_id, csv_url):
    """Admin import accounts from public CSV into Supabase google_accounts (add new only)"""
    try:
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        import csv, io, requests
        r = requests.get(csv_url, timeout=20)
        r.raise_for_status()
        content = r.text
        reader = csv.DictReader(io.StringIO(content))
        added = 0
        for row in reader:
            email = (row.get('Email') or row.get('email') or '').strip()
            password = (row.get('Password') or row.get('password') or '').strip()
            if not email or not password:
                continue
            recovery = (row.get('RecoveryEmail') or row.get('recovery_email') or '').strip()
            note = (row.get('Note') or '').strip()
            status = (row.get('Status') or 'AVAILABLE').strip() or 'AVAILABLE'
            source = (row.get('Source') or '').strip()
            quality = (row.get('Quality') or '').strip()
            tag = (row.get('Tag') or '').strip()
            try:
                # ignore duplicate by email
                exists = supabase.table('google_accounts').select('id').eq('email', email).limit(1).execute()
                if exists.data:
                    continue
                supabase.table('google_accounts').insert({
                    'email': email,
                    'password': password,
                    'recovery_email': recovery,
                    'note': note,
                    'status': status if status.upper() in ('AVAILABLE','SOLD','INVALID') else 'AVAILABLE',
                    'type': row.get('Type', 'trial').strip().lower() or 'trial',  # Get type from CSV or default to trial
                    'source': source,
                    'quality': quality,
                    'tag': tag
                }).execute()
                added += 1
            except Exception:
                continue
        send_telegram_message(chat_id, f"✅ Đã import {added} tài khoản vào kho")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi import CSV: {str(e)}")

def handle_buy_google_accounts_typed(chat_id, user, quantity, verified=False, canva=False, chatgpt=False, ultra=False, ultra45=False, spotify=False, surfshark=False, perplexity=False, perplexity1m=False, gpt1m=False, m365=False, adobe4m=False):
    """Buy Google accounts by type (trial/verified/canva). Uses CASH."""
    try:
        if quantity <= 0:
            quantity = 1
        # Detect VIP for preferential pricing
        vip_active = is_vip_active(user)
        if canva:
            # Prefer VIP price if active and configured
            vip_price = BOT_CONFIG.get('canva_price_vip') if vip_active else None
            price = int(float(vip_price)) if vip_price else 0
            if price <= 0:
                price = int(BOT_CONFIG.get('canva_price', 0) or 0)
            if price <= 0:
                send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setcanva <giá> trước.")
                return
            account_type = 'canva'
        elif verified:
            vip_price = BOT_CONFIG.get('google_verified_price_vip') if vip_active else None
            price = int(float(vip_price)) if vip_price else 0
            if price <= 0:
                price = int(BOT_CONFIG.get('google_verified_price', 0) or 0)
            if price <= 0:
                send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setgverified <giá> trước.")
                return
            account_type = 'verified'
        elif chatgpt:
            # Prefer VIP price if active and configured
            vip_price = BOT_CONFIG.get('chatgpt_price_vip') if vip_active else None
            price = int(float(vip_price)) if vip_price else 0
            if price <= 0:
                price = int(BOT_CONFIG.get('chatgpt_price', 0) or 0)
            if price <= 0:
                send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setchatgpt <giá> trước.")
                return
            account_type = 'chatgpt'
        elif ultra:
            # Prefer VIP price if active and configured
            vip_price = BOT_CONFIG.get('ai_ultra_price_vip') if vip_active else None
            price = int(float(vip_price)) if vip_price else 0
            if price <= 0:
                price = int(BOT_CONFIG.get('ai_ultra_price', 0) or 0)
            if price <= 0:
                send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setaiultra <giá> trước.")
                return
            account_type = 'ultra'
        elif ultra45:
            # Prefer VIP price if active and configured
            vip_price = BOT_CONFIG.get('ai_ultra45_price_vip') if vip_active else None
            price = int(float(vip_price)) if vip_price else 0
            if price <= 0:
                price = int(BOT_CONFIG.get('ai_ultra45_price', 200) or 200)  # Default 200 CASH
            if price <= 0:
                send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setaiultra45 <giá> trước.")
                return
            account_type = 'ultra45'
        elif spotify:
            # Prefer VIP price if active and configured
            vip_price = BOT_CONFIG.get('spotify_price_vip') if vip_active else None
            price = int(float(vip_price)) if vip_price else 0
            if price <= 0:
                price = int(BOT_CONFIG.get('spotify_price', 0) or 0)
            if price <= 0:
                send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setspotify <giá> trước.")
                return
            account_type = 'spotify'
        elif surfshark:
            # Prefer VIP price if active and configured
            vip_price = BOT_CONFIG.get('surfshark_price_vip') if vip_active else None
            price = int(float(vip_price)) if vip_price else 0
            if price <= 0:
                price = int(BOT_CONFIG.get('surfshark_price', 0) or 0)
            if price <= 0:
                send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setsurfshark <giá> trước.")
                return
            account_type = 'surfshark'
        elif perplexity:
            # Prefer VIP price if active and configured
            vip_price = BOT_CONFIG.get('perplexity_price_vip') if vip_active else None
            price = int(float(vip_price)) if vip_price else 0
            if price <= 0:
                price = int(BOT_CONFIG.get('perplexity_price', 0) or 0)
            if price <= 0:
                send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setper <giá> trước.")
                return
            account_type = 'perplexity'
        elif perplexity1m:
            # Prefer VIP price if active and configured
            vip_price = BOT_CONFIG.get('perplexity1m_price_vip') if vip_active else None
            price = int(float(vip_price)) if vip_price else 0
            if price <= 0:
                price = int(BOT_CONFIG.get('perplexity1m_price', 10) or 10)  # Default 10 CASH
            if price <= 0:
                send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setper1m <giá> trước.")
                return
            account_type = 'perplexity1m'
        elif gpt1m:
            # Prefer VIP price if active and configured
            vip_price = BOT_CONFIG.get('gpt1m_price_vip') if vip_active else None
            price = int(float(vip_price)) if vip_price else 0
            if price <= 0:
                price = int(BOT_CONFIG.get('gpt1m_price', 15) or 15)  # Default 15 CASH
            if price <= 0:
                send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setgpt1m <giá> trước.")
                return
            account_type = 'gpt1m'
        elif m365:
            # Prefer VIP price if active and configured
            vip_price = BOT_CONFIG.get('m365_price_vip') if vip_active else None
            price = int(float(vip_price)) if vip_price else 0
            if price <= 0:
                price = int(BOT_CONFIG.get('m365_price', 15) or 15)  # Default 15 CASH
            if price <= 0:
                send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setm365 <giá> trước.")
                return
            account_type = 'm365'
        elif adobe4m:
            # Prefer VIP price if active and configured
            vip_price = BOT_CONFIG.get('adobe4m_price_vip') if vip_active else None
            price = int(float(vip_price)) if vip_price else 0
            if price <= 0:
                price = int(BOT_CONFIG.get('adobe4m_price', 20) or 20)  # Default 20 CASH
            if price <= 0:
                send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setadobe4m <giá> trước.")
                return
            account_type = 'adobe4m'
        else:
            vip_price = BOT_CONFIG.get('google_trial_price_vip') if vip_active else None
            price = int(float(vip_price)) if vip_price else 0
            if price <= 0:
                price = int(BOT_CONFIG.get('google_trial_price', 0) or 0)
            if price <= 0:
                send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setgtrial <giá> trước.")
                return
            account_type = 'trial'
        table_name = 'google_accounts'

        # wallets
        if isinstance(user, dict):
            user_id = user.get('id'); wallets = supabase_get_wallets_by_user_id(user.get('id')); cash = wallets[0] if wallets else int(user.get('cash') or 0)
        else:
            user_id = user[0]; cash = user[5]

        total_cost = price * quantity
        if cash < total_cost:
            send_telegram_message(chat_id, f"💸 Bạn không đủ 💵 Cash.\n💳 Cần {total_cost} Cash để mua\n🏷️ Giá {price}Cash/acc\n💰 Cash hiện có: {cash}")
            return

        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return

        # Check stock - try uppercase first (as shown in database)
        count_resp = supabase.table(table_name).select('id', count='exact').eq('status','AVAILABLE').eq('type',account_type).execute()
        available = count_resp.count or 0
        if available == 0:
            # Fallback to lowercase
            count_resp = supabase.table(table_name).select('id', count='exact').eq('status','available').eq('type',account_type).execute()
            available = count_resp.count or 0
        if available < quantity:
            product_name = (
                "Google Trial" if account_type == "trial" else
                "Google Verified" if account_type == "verified" else
                "Canva Admin Edu" if account_type == "canva" else
                "ChatGPT Plus 3 Months" if account_type == "chatgpt" else
                "Spotify Premium 4M CODE" if account_type == "spotify" else
                "Surfshark VPN" if account_type == "surfshark" else
                "Perplexity PRO 1 Năm" if account_type == "perplexity" else
                "Perplexity PRO 1 Month" if account_type == "perplexity1m" else
                "Tài khoản Microsoft 365 Personal 1 Năm" if account_type == "m365" else
                "Google AI ULTRA 25k Credits"
            )
            send_telegram_message(chat_id, f"❌ {product_name} Đã hết hàng!\n📦 Kho: {available}")
            return

        # Reserve and collect - use atomic update approach
        reserved = []
        for _ in range(quantity * 3):
            if len(reserved) >= quantity:
                break
            # Try uppercase first (as shown in database), then lowercase
            try:
                resp = (
                    supabase.table(table_name)
                    .select('id,email,password,recovery_email,note')
                    .eq('status','AVAILABLE')
                    .eq('type',account_type)
                    .order('added_at')
                    .limit(1)
                    .execute()
                )
            except Exception:
                # Fallback without order if column missing
                resp = (
                    supabase.table(table_name)
                    .select('id,email,password,recovery_email,note')
                    .eq('status','AVAILABLE')
                    .eq('type',account_type)
                    .limit(1)
                    .execute()
                )
            if not resp.data:
                try:
                    resp = (
                        supabase.table(table_name)
                        .select('id,email,password,recovery_email,note')
                        .eq('status','available')
                        .eq('type',account_type)
                        .order('added_at')
                        .limit(1)
                        .execute()
                    )
                except Exception:
                    resp = (
                        supabase.table(table_name)
                        .select('id,email,password,recovery_email,note')
                        .eq('status','available')
                        .eq('type',account_type)
                        .limit(1)
                        .execute()
                    )
            if not resp.data:
                break
            acc = resp.data[0]
            
            # Atomic update: try to reserve by updating status from available to sold
            try:
                # Update status to SOLD and add buyer info (constraint now allows SOLD)
                upd = supabase.table(table_name).update({
                    'status':'SOLD',
                    'buyer_telegram_id':chat_id,
                    'sold_at':datetime.utcnow().isoformat(),
                    'price_at_sale':price
                }).eq('id', acc['id']).eq('status','AVAILABLE').execute()
                
                if not upd.data or len(upd.data) == 0:
                    # Try lowercase fallback
                    upd = supabase.table(table_name).update({
                        'status':'SOLD',
                        'buyer_telegram_id':chat_id,
                        'sold_at':datetime.utcnow().isoformat(),
                        'price_at_sale':price
                    }).eq('id', acc['id']).eq('status','available').execute()
                    
                if not upd.data or len(upd.data) == 0:
                    continue
                    
            except Exception as e:
                print(f"Error updating account {acc['id']}: {repr(e)}")
                # If update fails, skip this account
                continue
                
            # Check if we successfully updated the account
            if upd.data and len(upd.data) > 0:
                reserved.append(acc)

        if len(reserved) < quantity:
            for acc in reserved:
                try:
                    # Rollback status to AVAILABLE and clear buyer info
                    supabase.table(table_name).update({
                        'status':'AVAILABLE',
                        'buyer_telegram_id':None,
                        'sold_at':None,
                        'price_at_sale':None
                    }).eq('id', acc['id']).execute()
                except Exception:
                    try:
                        # Try lowercase fallback
                        supabase.table(table_name).update({
                            'status':'available',
                            'buyer_telegram_id':None,
                            'sold_at':None,
                            'price_at_sale':None
                        }).eq('id', acc['id']).execute()
                    except Exception:
                        pass
            product_name = "Canva Admin Edu" if canva else ("Google Verified" if verified else ("ChatGPT Plus 3 Months" if chatgpt else ("Google AI ULTRA 45k Credits" if ultra45 else ("Spotify Premium 4M CODE" if spotify else ("Surfshark VPN" if surfshark else ("Perplexity PRO 1 Năm" if perplexity else ("Perplexity PRO 1 Month" if perplexity1m else "Google Trial")))))))
            send_telegram_message(chat_id, f"❌ Không đủ {product_name} trong kho. Vui lòng thử lại.")
            return

        # Deduct cash (log purchase transaction for quests)
        try:
            wallets = supabase_adjust_wallet_by_user_id(user_id, cash_delta=-total_cost)
            if wallets is None:
                raise Exception('Không trừ được CASH')
            # Log purchase transaction in Supabase for quest tracking
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    supabase.table('transactions').insert({
                        'user_id': user_id,
                        'type': 'purchase',
                        'amount': total_cost,
                        'description': f'Mua {quantity} {account_type}'
                    }).execute()
            except Exception:
                pass
        except Exception:
            for acc in reserved:
                try:
                    # Rollback status to AVAILABLE and clear buyer info
                    supabase.table(table_name).update({
                        'status':'AVAILABLE',
                        'buyer_telegram_id':None,
                        'sold_at':None,
                        'price_at_sale':None
                    }).eq('id', acc['id']).execute()
                except Exception:
                    try:
                        # Try lowercase fallback
                        supabase.table(table_name).update({
                            'status':'available',
                            'buyer_telegram_id':None,
                            'sold_at':None,
                            'price_at_sale':None
                        }).eq('id', acc['id']).execute()
                    except Exception:
                        pass
            send_telegram_message(chat_id, "❌ Giao dịch thất bại khi trừ CASH. Vui lòng thử lại.")
            return

        # Success
        product_name = "Canva Admin Edu" if canva else ("Google Verified" if verified else ("ChatGPT Plus 3 Months" if chatgpt else ("Spotify Premium 4M CODE" if spotify else ("Surfshark VPN" if surfshark else ("Perplexity PRO 1 Năm" if perplexity else ("Perplexity PRO 1 Month" if perplexity1m else "Google Trial"))))))
        lines = [
            f"🎉 MUA {product_name.upper()} THÀNH CÔNG!",
            f"📦 Số lượng: {quantity}",
            f"💰 Đã trừ: {total_cost} CASH",
            f"💵 Số dư hiện tại: {wallets[0]} CASH",
            "",
            "📋 THÔNG TIN TÀI KHOẢN:" if not chatgpt else "📋 THÔNG TIN CODE:"
        ]
        for acc in reserved:
            if chatgpt:
                # For ChatGPT, show code instead of email/password
                lines.extend([
                    f"Code: {acc.get('email', 'N/A')}",
                    f"Ghi chú: {acc.get('note', 'N/A')}",
                    ""
                ])
            else:
                recovery = acc.get('recovery_email') or 'N/A'
                lines.extend([
                    f"Email: {acc.get('email')}",
                    f"Mật khẩu: {acc.get('password')}",
                    f"Mail khôi phục: {recovery}",
                    ""
                ])
        send_telegram_message(chat_id, "\n".join(lines))
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi mua acc: {repr(e)}")

def handle_buy_vip_days(chat_id, user, days):
    try:
        if days not in (1, 7, 30):
            send_telegram_message(chat_id, "❌ Gói VIP không hợp lệ")
            return
        price_key = 'vip1_price' if days == 1 else ('vip7_price' if days == 7 else 'vip30_price')
        price = int(BOT_CONFIG.get(price_key, 0) or 0)
        if price <= 0:
            send_telegram_message(chat_id, f"❌ Admin chưa đặt giá VIP {days} ngày. Dùng /admin setvip{days} <giá> trước.")
            return
        # wallets
        if isinstance(user, dict):
            user_id = user.get('id')
            wallets = supabase_get_wallets_by_user_id(user.get('id'))
            cash = wallets[0] if wallets else int(user.get('cash') or 0)
        else:
            user_id = user[0]
            cash = user[5]
        if cash < price:
            send_telegram_message(chat_id, f"💸 Bạn không đủ 💵 Cash.\n💳 Cần {price} Cash để mua\n💰 Cash hiện có: {cash}")
            return
        # deduct
        wallets = supabase_adjust_wallet_by_user_id(user_id, cash_delta=-price)
        if wallets is None:
            send_telegram_message(chat_id, "❌ Không trừ được CASH")
            return
        # add vip days to existing expiry or set new expiry
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            # Get current user data to check existing VIP expiry
            user_data = supabase.table('users').select('is_vip, vip_expiry').eq('id', user_id).execute()
            current_vip_expiry = None
            if user_data.data and len(user_data.data) > 0:
                current_vip_expiry = user_data.data[0].get('vip_expiry')
            # Calculate new expiry
            from datetime import datetime, timedelta
            import pytz
            vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            current_time = datetime.now(vn_tz)
            if current_vip_expiry:
                try:
                    current_expiry = datetime.fromisoformat(current_vip_expiry.replace('Z', '+00:00'))
                    current_expiry = current_expiry.replace(tzinfo=pytz.UTC).astimezone(vn_tz)
                except Exception:
                    current_expiry = current_time
                new_expiry = current_expiry + timedelta(days=days)
                expiry = new_expiry.isoformat()
            else:
                expiry = (current_time + timedelta(days=days)).isoformat()
            # Update VIP status
            supabase.table('users').update({'is_vip': True, 'vip_expiry': expiry}).eq('id', user_id).execute()
            # Format expiry date for display
            expiry_datetime = datetime.fromisoformat(expiry)
            formatted_expiry = expiry_datetime.strftime('%d/%m/%Y %H:%M')
            # Get current cash balance
            current_wallets = supabase_get_wallets_by_user_id(user_id)
            current_cash = current_wallets[0] if current_wallets else 0
            # Send success message
            success_message = (
                f"🎉 Đã mua VIP {days} ngày.\n"
                f"⏰ Hạn sử dụng: {formatted_expiry}\n"
                f"💰 Số dư hiện tại: {current_cash} Cash"
                f"❓ Kiểm tra VIP và các quyền lợi: /vip"

            )
            send_telegram_message(chat_id, success_message)
        except Exception as e:
            send_telegram_message(chat_id, f"❌ Lỗi cập nhật VIP: {str(e)}")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi mua VIP: {str(e)}")


def handle_buy_vip_tier(chat_id, user, tier, days):
    """Handle buying VIP Pro or Business tier"""
    try:
        from .vip_tiers import VIP_TIERS, upgrade_vip_tier
        
        if tier not in VIP_TIERS:
            send_telegram_message(chat_id, "❌ Gói VIP không hợp lệ")
            return
        
        tier_config = VIP_TIERS[tier]
        
        # Get price based on days
        if days == 7:
            price = tier_config['price_7_days']
        elif days == 30:
            price = tier_config['price_30_days']
        else:
            send_telegram_message(chat_id, "❌ Chỉ hỗ trợ gói 7 hoặc 30 ngày")
            return
        
        # Get user wallets
        if isinstance(user, dict):
            user_id = user.get('id')
            wallets = supabase_get_wallets_by_user_id(user.get('id'))
            cash = wallets[0] if wallets else int(user.get('cash') or 0)
        else:
            user_id = user[0]
            cash = user[5]
        
        tier_name = tier_config['name']
        concurrent_links = tier_config['concurrent_links']
        
        if cash < price:
            send_telegram_message(chat_id, f"""💸 Không đủ Cash để mua {tier_name}!

💳 Cần: {price} Cash ({price/25:.0f} USDT)
💰 Hiện có: {cash} Cash

🔗 {tier_name}: {concurrent_links} link song song
📅 Thời hạn: {days} ngày

💡 Nạp thêm: /nap hoặc /crypto""")
            return
        
        # Deduct cash
        wallets = supabase_adjust_wallet_by_user_id(user_id, cash_delta=-price)
        if wallets is None:
            send_telegram_message(chat_id, "❌ Không trừ được CASH")
            return
        
        # Upgrade VIP tier
        success, message = upgrade_vip_tier(user_id, tier, days)
        
        if success:
            current_wallets = supabase_get_wallets_by_user_id(user_id)
            current_cash = current_wallets[0] if current_wallets else 0
            
            send_telegram_message(chat_id, f"""🎉 Đã mua {tier_name} {days} ngày!

🔗 Số link song song: {concurrent_links}
💰 Đã trừ: {price} Cash
💵 Số dư: {current_cash} Cash

{message}

💡 Quyền lợi:
• Verify student miễn phí (không giới hạn)
• Chạy {concurrent_links} link cùng lúc
• Hỗ trợ ưu tiên

❓ Kiểm tra VIP: /vip""")
        else:
            # Refund if upgrade failed
            supabase_adjust_wallet_by_user_id(user_id, cash_delta=price)
            send_telegram_message(chat_id, message)
            
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi mua VIP: {str(e)}")


def handle_buy_google_account(chat_id, user):
    """User buys one Google account from stock"""
    try:
        price = int(BOT_CONFIG.get('google_verified_price', 0) or 0)
        if price <= 0:
            send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setgverified <giá> trước.")
            return
        # Get user wallets (cash only for purchases)
        if isinstance(user, dict):
            user_id = user.get('id'); wallets = supabase_get_wallets_by_user_id(user.get('id')); cash = wallets[0] if wallets else int(user.get('cash') or 0)
        else:
            user_id = user[0]; cash = user[5]
        if cash < price:
            send_telegram_message(chat_id, f"💸 Bạn không đủ 💵 Cash.\n💳 Cần {price} Cash để mua\n💰 Cash hiện có: {cash}")
            return
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        # Try to reserve an AVAILABLE account (handle uppercase/lowercase status)
        reserved = None
        try_attempts = 3
        for _ in range(try_attempts):
            # Try uppercase first (as shown in database), then lowercase
            resp = supabase.table('google_accounts').select('id,email,password,recovery_email,note').eq('status','AVAILABLE').order('added_at').limit(1).execute()
            if not resp.data:
                resp = supabase.table('google_accounts').select('id,email,password,recovery_email,note').eq('status','available').order('added_at').limit(1).execute()
            if not resp.data:
                break
            acc = resp.data[0]
            
            # Atomic update: try to reserve by updating status from available to sold
            try:
                # Update status to SOLD and add buyer info (constraint now allows SOLD)
                upd = supabase.table('google_accounts').update({
                    'status':'SOLD',
                    'buyer_telegram_id': chat_id,
                    'sold_at': datetime.utcnow().isoformat(),
                    'price_at_sale': price
                }).eq('id', acc['id']).eq('status','AVAILABLE').execute()
                if not upd.data or len(upd.data) == 0:
                    # Fallback to lowercase
                    upd = supabase.table('google_accounts').update({
                        'status':'SOLD',
                        'buyer_telegram_id': chat_id,
                        'sold_at': datetime.utcnow().isoformat(),
                        'price_at_sale': price
                    }).eq('id', acc['id']).eq('status','available').execute()
            except Exception:
                # If update fails, skip this account
                continue
                
            if upd.data and len(upd.data) > 0:
                reserved = acc
                break
        if not reserved:
            product_name = "Canva Admin Edu" if canva else ("Google Verified" if verified else ("Google AI ULTRA 45k Credits" if ultra45 else "Google Trial"))
            send_telegram_message(chat_id, f"❌ Kho {product_name} đã hết hàng. Vui lòng thử lại sau!")
            return
        # Deduct CASH only
        try:
            wallets = supabase_adjust_wallet_by_user_id(user_id, cash_delta=-price)
            if wallets is None:
                raise Exception('Không trừ được xu CASH')
        except Exception:
            # rollback status to AVAILABLE if coin update failed
            try:
                supabase.table('google_accounts').update({'status':'AVAILABLE','buyer_telegram_id':None,'sold_at':None,'price_at_sale':None}).eq('id', reserved['id']).execute()
            except Exception:
                supabase.table('google_accounts').update({'status':'available','buyer_telegram_id':None,'sold_at':None,'price_at_sale':None}).eq('id', reserved['id']).execute()
            send_telegram_message(chat_id, "❌ Giao dịch thất bại khi trừ CASH. Vui lòng thử lại.")
            return
        # Success message
        info_lines = [
            "✅ MUA TÀI KHOẢN THÀNH CÔNG!",
            f"💰 Đã trừ: {price} CASH",
            f"💵 Số dư hiện tại: {wallets[0]} CASH",
            "",
            "📋 THÔNG TIN TÀI KHOẢN:",
            f"Email: {reserved.get('email')}",
            f"Mật khẩu: {reserved.get('password')}",
            f"Mail khôi phục: {reserved.get('recovery_email') or 'N/A'}"
        ]
        if reserved.get('note'):
            info_lines.append(f"Ghi chú: {reserved.get('note')}")
        send_telegram_message(chat_id, "\n".join(info_lines))
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi mua acc: {str(e)}")

def handle_buy_google_accounts_bulk(chat_id, user, quantity):
    """User buys multiple Google accounts (min 5) from stock atomically"""
    try:
        price = int(BOT_CONFIG.get('google_verified_price', 0) or 0)
        if price <= 0:
            send_telegram_message(chat_id, "❌ Admin chưa đặt giá. Dùng /admin setgverified <giá> trước.")
            return

        # Get user coins and id
        if isinstance(user, dict):
            user_id = user.get('id'); wallets = supabase_get_wallets_by_user_id(user.get('id')); cash = wallets[0] if wallets else int(user.get('cash') or 0)
        else:
            user_id = user[0]; cash = user[5]

        if quantity < 5:
            send_telegram_message(chat_id, "❌ Số lượng tối thiểu là 5. Cú pháp: /mua <số_lượng>")
            return

        total_cost = price * quantity
        if cash < total_cost:
            send_telegram_message(chat_id, f"💸 Bạn không đủ 💵 Cash.\n💳 Cần {total_cost} Cash để mua\n🏷️ Giá {price}Cash/acc\n💰 Cash hiện có: {cash}")
            return

        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return

        # Check stock first (handle both case variants)
        try:
            count_resp = supabase.table('google_accounts').select('id', count='exact').eq('status','available').execute()
            if (count_resp.count or 0) == 0:
                count_resp = supabase.table('google_accounts').select('id', count='exact').eq('status','available').execute()
            available = count_resp.count or 0
            if available < quantity:
                send_telegram_message(chat_id, f"❌ Google Account Đã hết hàng!\n📦 Kho: {available}")
                return
        except Exception:
            pass

        reserved_list = []
        try_attempts = quantity * 3
        for _ in range(try_attempts):
            if len(reserved_list) >= quantity:
                break
            resp = supabase.table('google_accounts').select('id,email,password,recovery_email,note').eq('status','AVAILABLE').order('added_at').limit(1).execute()
            if not resp.data:
                resp = supabase.table('google_accounts').select('id,email,password,recovery_email,note').eq('status','available').order('added_at').limit(1).execute()
            if not resp.data:
                break
            acc = resp.data[0]
            try:
                # Update status to SOLD and add buyer info (constraint now allows SOLD)
                upd = supabase.table('google_accounts').update({
                    'status':'SOLD',
                    'buyer_telegram_id': chat_id,
                    'sold_at': datetime.utcnow().isoformat(),
                    'price_at_sale': price
                }).eq('id', acc['id']).eq('status','AVAILABLE').execute()
            except Exception:
                # Fallback to lowercase
                upd = supabase.table('google_accounts').update({
                    'status':'SOLD',
                    'buyer_telegram_id': chat_id,
                    'sold_at': datetime.utcnow().isoformat(),
                    'price_at_sale': price
                }).eq('id', acc['id']).eq('status','available').execute()
            if upd.data:
                reserved_list.append(acc)

        if len(reserved_list) < quantity:
            # rollback any reserved
            for acc in reserved_list:
                try:
                    supabase.table('google_accounts').update({'status':'available','buyer_telegram_id':None,'sold_at':None,'price_at_sale':None}).eq('id', acc['id']).execute()
                except Exception:
                    try:
                        supabase.table('google_accounts').update({'status':'available','buyer_telegram_id':None,'sold_at':None,'price_at_sale':None}).eq('id', acc['id']).execute()
                    except Exception:
                        pass
            product_name = "Canva Admin Edu" if canva else ("Google Verified" if verified else ("ChatGPT Plus 3 Months" if chatgpt else ("Google AI ULTRA 45k Credits" if ultra45 else ("Spotify Premium 4M CODE" if spotify else ("Surfshark VPN" if surfshark else ("Perplexity PRO 1 Năm" if perplexity else ("Perplexity PRO 1 Month" if perplexity1m else "Google Trial")))))))
            send_telegram_message(chat_id, f"❌ Không đủ {product_name} trong kho. Vui lòng thử lại.")
            return

        # Deduct coins for all
        try:
            wallets = supabase_adjust_wallet_by_user_id(user_id, cash_delta=-total_cost)
            if wallets is None:
                raise Exception('Không trừ được xu CASH')
        except Exception:
            # rollback all reservations
            for acc in reserved_list:
                try:
                    supabase.table('google_accounts').update({'status':'available','buyer_telegram_id':None,'sold_at':None,'price_at_sale':None}).eq('id', acc['id']).execute()
                except Exception:
                    pass
            send_telegram_message(chat_id, "❌ Giao dịch thất bại khi trừ CASH. Vui lòng thử lại.")
            return

        # Success message: send list
        lines = [
            "✅ MUA TÀI KHOẢN THÀNH CÔNG!",
            f"📦 Số lượng: {quantity}",
            f"💰 Đã trừ: {total_cost} CASH",
            f"💵 Số dư hiện tại: {wallets[0]} CASH",
            "",
            "📋 THÔNG TIN TÀI KHOẢN:"
        ]
        for acc in reserved_list:
            lines.extend([
                f"Email: {acc.get('email')}",
                f"Mật khẩu: {acc.get('password')}",
                f"Mail khôi phục: {acc.get('recovery_email') or 'N/A'}",
                ""
            ])
        send_telegram_message(chat_id, "\n".join(lines))
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi mua acc số lượng: {str(e)}")

def send_telegram_message(chat_id, text, parse_mode=None):
    """Send message to Telegram with optimized session - Default: NO markdown parsing"""
    # EMERGENCY STOP - CHỈ CHO PHÉP ADMIN NHẬN TIN TRẢ LỜI LỆNH
    if EMERGENCY_STOP and chat_id != 7162256181:
        print(f"🚨 EMERGENCY STOP: Blocked message to {chat_id}: {text[:50]}...")
        return False
    
    # Allow admin to receive broadcast notifications (but prevent id loop
    if chat_id == 7162256181 and "THÔNG BÁO" in text:
        print(f"🚫 Skipping admin notification to prevent loop: {text[:50]}...")
        return False
        
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
    if not bot_token:
        print(f"Would send to {chat_id}: {text}")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'disable_web_page_preview': True
    }
    
    # Only add parse_mode if specified
    if parse_mode:
        data['parse_mode'] = parse_mode
    
    try:
        # Use optimized session with connection pooling
        session = create_optimized_session()
        response = session.post(url, json=data, timeout=5)  # Reduced timeout
        if response.status_code == 200:
            result = response.json()
            # Return message_id for editing later
            return result.get('result', {}).get('message_id')
        else:
            print(f"Telegram API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return False

def edit_telegram_message(chat_id, message_id, text, parse_mode='HTML'):
    """Edit an existing Telegram message"""
    if EMERGENCY_STOP and chat_id != 7162256181:
        print(f"🚨 EMERGENCY STOP: Blocked edit to {chat_id}")
        return False
    
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
    if not bot_token:
        print(f"Would edit message {message_id} for {chat_id}: {text}")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
    data = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True
    }
    
    try:
        session = create_optimized_session()
        response = session.post(url, json=data, timeout=5)
        if response.status_code == 200:
            return True
        else:
            print(f"Telegram edit error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Failed to edit Telegram message: {e}")
        return False

def send_telegram_message_plain(chat_id, text):
    """Send message to Telegram WITHOUT parse_mode (plain text) - avoids HTML/Markdown parsing issues"""
    # EMERGENCY STOP - CHỈ CHO PHÉP ADMIN NHẬN TIN TRẢ LỜI LỆNH
    if EMERGENCY_STOP and chat_id != 7162256181:
        print(f"🚨 EMERGENCY STOP: Blocked message to {chat_id}: {text[:50]}...")
        return False
        
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
    if not bot_token:
        print(f"Would send to {chat_id}: {text}")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'disable_web_page_preview': True
    }
    # NO parse_mode - plain text only to avoid HTML/Markdown parsing errors
    
    try:
        session = create_optimized_session()
        response = session.post(url, json=data, timeout=5)
        if response.status_code == 200:
            return True
        else:
            print(f"Telegram API error (plain): {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Failed to send Telegram message (plain): {e}")
        return False

def send_telegram_message_with_keyboard(chat_id, text, keyboard):
    """Send message to Telegram with inline keyboard"""
    
    # UNIVERSAL KEYBOARD FORMAT FIX
    if isinstance(keyboard, list):
        keyboard = {"inline_keyboard": keyboard}
        print(f"🔧 Auto-fixed keyboard format for {chat_id}")
    
    # EMERGENCY STOP - CHỈ CHO PHÉP ADMIN NHẬN TIN TRẢ LỜI LỆNH
    if EMERGENCY_STOP and chat_id != 7162256181:
        print(f"🚨 EMERGENCY STOP: Blocked message with keyboard to {chat_id}: {text[:50]}...")
        return False
        
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
    if not bot_token:
        print(f"Would send keyboard message to {chat_id}: {text}")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'reply_markup': keyboard
    }
    
    try:
        # Use optimized session with connection pooling
        session = create_optimized_session()
        response = session.post(url, json=data, timeout=10)
        if response.status_code == 200:
            return True
        else:
            print(f"Telegram API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Failed to send keyboard message: {e}")
        return False

def check_and_send_pending_broadcasts():
    """Auto check and send pending broadcasts from database"""
    try:
        if not SUPABASE_AVAILABLE:
            return
        
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            return
        
        # Check for pending broadcasts
        broadcasts = supabase.table('broadcast_messages').select('*').eq('status', 'pending').order('created_at').limit(1).execute()
        
        if not broadcasts.data:
            return
        
        broadcast = broadcasts.data[0]
        broadcast_id = broadcast['id']
        message = broadcast['message']
        
        print(f"📢 Auto-sending broadcast ID: {broadcast_id}")
        
        # Update status to sending
        supabase.table('broadcast_messages').update({'status': 'sending'}).eq('id', broadcast_id).execute()
        
        # Get all users (excluding admin)
        users_resp = supabase.table('users').select('telegram_id').neq('telegram_id', 7162256181).is_('telegram_id', 'not.null').execute()
        
        if not users_resp.data:
            return
        
        success_count = 0
        total_users = len(users_resp.data)
        
        print(f"📢 Sending broadcast to {total_users} users...")
        
        # Send to each user
        for user in users_resp.data:
            telegram_id = user['telegram_id']
            try:
                success = send_telegram_message(telegram_id, f"📢 THÔNG BÁO TỪ ADMIN:\n\n{message}")
                if success:
                    success_count += 1
                time.sleep(0.05)  # Rate limiting
            except Exception as e:
                print(f"❌ Error sending broadcast to {telegram_id}: {e}")
        
        # Update final status
        supabase.table('broadcast_messages').update({
            'status': 'completed',
            'sent_count': success_count
        }).eq('id', broadcast_id).execute()
        
        print(f"✅ Auto-broadcast completed: {success_count}/{total_users} sent")
        
    except Exception as e:
        print(f"❌ Error in auto-broadcast: {e}")

def send_telegram_message_with_keyboard(chat_id, text, keyboard):
    """Send message to Telegram with inline keyboard"""
    
    # UNIVERSAL KEYBOARD FORMAT FIX
    if isinstance(keyboard, list):
        keyboard = {"inline_keyboard": keyboard}
        print(f"🔧 Auto-fixed keyboard format for {chat_id}")
    
    # EMERGENCY STOP - CHỈ CHO PHÉP ADMIN NHẬN TIN TRẢ LỜI LỆNH
    if EMERGENCY_STOP and chat_id != 7162256181:
        print(f"🚨 EMERGENCY STOP: Blocked message with keyboard to {chat_id}: {text[:50]}...")
        return False
    
    # Allow admin to receive broadcast notifications (but prevent other loops)
    if chat_id == 7162256181 and "THÔNG BÁO" in text and "📢 THÔNG BÁO TỪ ADMIN:" not in text:
        print(f"🚫 Skipping admin notification with keyboard to prevent loop: {text[:50]}...")
        return False
        
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
    if not bot_token:
        print(f"Would send to {chat_id}: {text} with keyboard")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # Convert keyboard format for Telegram API
    if isinstance(keyboard, list):
        reply_markup = {"inline_keyboard": keyboard}
    else:
        reply_markup = keyboard
    
    data = {
        'chat_id': chat_id,
        'text': text,
        'reply_markup': reply_markup
    }
    
    print(f"🔍 DEBUG: Sending keyboard data: {data}")
    
    try:
        # Use optimized session with connection pooling
        session = create_optimized_session()
        response = session.post(url, json=data, timeout=5)  # Reduced timeout
        if response.status_code == 200:
            return True
        else:
            print(f"Telegram API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Failed to send Telegram message with keyboard: {e}")
        return False

def get_user_verify_stats(user_id, telegram_id):
    """Get user verification statistics from Supabase"""
    try:
        if not SUPABASE_AVAILABLE:
            return "• Hôm nay: N/A\n• Tổng: N/A\n• Số lượt Verify bằng xu hôm nay: N/A"
        
        from supabase_client import get_supabase_client
        from datetime import datetime, timezone, timedelta
        
        supabase = get_supabase_client()
        if not supabase:
            return "• Hôm nay: N/A\n• Tổng: N/A\n• Số lượt Verify bằng xu hôm nay: N/A"
        
        # Get today's date in Vietnam timezone
        vietnam_tz = timezone(timedelta(hours=7))
        today_vietnam = datetime.now(vietnam_tz)
        today_start = today_vietnam.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_vietnam.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Convert to UTC for database query
        today_start_utc = today_start.astimezone(timezone.utc).isoformat()
        today_end_utc = today_end.astimezone(timezone.utc).isoformat()
        
        # Get today's completed verifications
        today_completed = supabase.table('verification_jobs').select('id').eq('user_id', user_id).eq('status', 'completed').gte('created_at', today_start_utc).lte('created_at', today_end_utc).execute()
        
        # Get today's total verifications (all statuses)
        today_total = supabase.table('verification_jobs').select('id').eq('user_id', user_id).gte('created_at', today_start_utc).lte('created_at', today_end_utc).execute()
        
        # Get all time completed verifications
        total_completed = supabase.table('verification_jobs').select('id').eq('user_id', user_id).eq('status', 'completed').execute()
        
        # Get all time total verifications
        total_all = supabase.table('verification_jobs').select('id').eq('user_id', user_id).execute()
        
        # For now, assume all verifications use coins (since we don't have payment_method column)
        # This can be updated later when payment_method column is added
        today_coin_verifications = len(today_completed.data) if today_completed.data else 0
        
        today_completed_count = len(today_completed.data) if today_completed.data else 0
        today_total_count = len(today_total.data) if today_total.data else 0
        total_completed_count = len(total_completed.data) if total_completed.data else 0
        total_all_count = len(total_all.data) if total_all.data else 0
        
        return f"""• Hôm nay: {today_completed_count}/{today_total_count} thành công
• Tổng: {total_completed_count}/{total_all_count} thành công
• Số lượt Verify bằng xu hôm nay: {today_coin_verifications}/2"""
        
    except Exception as e:
        print(f"Error getting verify stats: {e}")
        return "• Hôm nay: N/A\n• Tổng: N/A\n• Số lượt Verify bằng xu hôm nay: N/A"

def get_user_payment_stats(user_id, telegram_id):
    """Get user payment transaction statistics from Supabase"""
    try:
        if not SUPABASE_AVAILABLE:
            return "• Số giao dịch: N/A"
        
        from supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        if not supabase:
            return "• Số giao dịch: N/A"
        
        # Check if payment_transactions table exists
        try:
            # Get completed payment transactions count
            completed_payments = supabase.table('payment_transactions').select('id').eq('user_id', user_id).eq('status', 'completed').execute()
            payment_count = len(completed_payments.data) if completed_payments.data else 0
            
            return f"• Số giao dịch: {payment_count}"
            
        except Exception as table_error:
            # Table doesn't exist yet
            print(f"Payment transactions table not found: {table_error}")
            return "• Số giao dịch: 0"
        
    except Exception as e:
        print(f"Error getting payment stats: {e}")
        return "• Số giao dịch: N/A"

def get_user_recent_jobs(user_id, telegram_id):
    """Get user's 5 most recent verification jobs"""
    try:
        if not SUPABASE_AVAILABLE:
            return "• Không có dữ liệu"
        
        from supabase_client import get_supabase_client
        from datetime import datetime, timezone, timedelta
        
        supabase = get_supabase_client()
        if not supabase:
            return "• Không có dữ liệu"
        
        # Get 5 most recent jobs
        recent_jobs = supabase.table('verification_jobs').select('id, status, created_at').eq('user_id', user_id).order('created_at', desc=True).limit(5).execute()
        
        if not recent_jobs.data:
            return "• Chưa có job nào"
        
        # Format jobs
        vietnam_tz = timezone(timedelta(hours=7))
        job_lines = []
        
        for job in recent_jobs.data:
            job_id = job.get('id', 'N/A')
            status = job.get('status', 'unknown')
            created_at = job.get('created_at', '')
            
            # Convert to Vietnam time
            try:
                created_date_utc = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_date_vietnam = created_date_utc.astimezone(vietnam_tz)
                date_str = created_date_vietnam.strftime('%d-%m-%Y %H:%M')
            except:
                date_str = 'N/A'
            
            # Status icon
            if status == 'completed':
                status_icon = '✅'
            elif status == 'failed':
                status_icon = '❌'
            elif status == 'cancelled':
                status_icon = '🚫'
            else:
                status_icon = '⏳'
            
            # Truncate job ID to first 8 characters
            short_job_id = str(job_id)[:8] if job_id != 'N/A' else 'N/A'
            
            job_lines.append(f"• {date_str} | {short_job_id} | {status_icon}")
        
        return '\n'.join(job_lines)
        
    except Exception as e:
        print(f"Error getting recent jobs: {e}")
        return "• Không có dữ liệu"


def handle_vip_command(chat_id, user):
    """Handle /vip command - show VIP info and packages"""
    try:
        if not user:
            send_telegram_message(chat_id, "❌ Vui lòng /start trước")
            return
        
        # Get user VIP info
        if isinstance(user, dict):
            is_vip = user.get('is_vip', False)
            vip_expiry = user.get('vip_expiry')
            vip_type = user.get('vip_type', 'basic')
            concurrent_links = user.get('concurrent_links', 1)
            telegram_id = user.get('telegram_id')
        else:
            is_vip = False
            vip_expiry = None
            vip_type = 'basic'
            concurrent_links = 1
            telegram_id = str(chat_id)
        
        # Get VIP tier info
        try:
            from .vip_tiers import VIP_TIERS, get_user_verification_status
            tier_config = VIP_TIERS.get(vip_type, VIP_TIERS['basic'])
            tier_name = tier_config['name']
            
            # Get active verification status
            status = get_user_verification_status(telegram_id, user)
            active_count = status['active_count']
            slots_available = status['slots_available']
        except:
            tier_name = "VIP Basic"
            active_count = 0
            slots_available = concurrent_links
        
        # Format expiry
        if is_vip and vip_expiry:
            try:
                from datetime import datetime
                expiry_dt = datetime.fromisoformat(vip_expiry.replace('Z', '+00:00'))
                expiry_str = expiry_dt.strftime('%d/%m/%Y %H:%M')
                vip_status = f"✅ {tier_name} - Còn hạn đến {expiry_str}"
            except:
                vip_status = f"✅ {tier_name} - Đang hoạt động"
        else:
            vip_status = "❌ Chưa có VIP"
        
        # Build message
        if is_vip:
            message = f"""👑 THÔNG TIN VIP

📊 Trạng thái: {vip_status}
🔗 Số link song song: {concurrent_links}
📈 Đang chạy: {active_count}/{concurrent_links} slot
✨ Slot trống: {slots_available}

💡 Quyền lợi VIP:
• Verify student MIỄN PHÍ (không giới hạn)
• Chạy {concurrent_links} link cùng lúc
• Hỗ trợ ưu tiên

━━━━━━━━━━━━━━━━━━━━━━
📦 NÂNG CẤP GÓI VIP:

🔹 VIP Pro (3 link song song)
   💵 7 ngày: 1800 cash (72 USDT)
   📝 Lệnh: /mua vippro7

🔹 VIP Business (5 link song song)
   💵 7 ngày: 2400 cash (96 USDT)
   📝 Lệnh: /mua vipbiz7

💡 Nạp tiền: /nap hoặc /crypto"""
        else:
            message = f"""👑 GÓI VIP

📊 Trạng thái: {vip_status}

━━━━━━━━━━━━━━━━━━━━━━
📦 CÁC GÓI VIP:

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
• Verify student MIỄN PHÍ (không giới hạn)
• Chạy nhiều link cùng lúc
• Hỗ trợ ưu tiên

💰 Nạp tiền: /nap hoặc /crypto"""
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"Error in handle_vip_command: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")


def send_user_info(chat_id, user):
    """Send user information"""
    try:
        if not user:
            send_telegram_message(chat_id, "❌ Không tìm thấy thông tin user")
            return
        
        # Handle user data format (dictionary from SQLite)
        if isinstance(user, dict):
            user_id = user.get('id', 1)
            telegram_id = user.get('telegram_id', '1')
            username = user.get('username', 'user')
            first_name = user.get('first_name', 'User')
            last_name = user.get('last_name', '')
            coins = user.get('coins', 0)
            is_vip = user.get('is_vip', False)
            vip_expiry = user.get('vip_expiry')
            created_at = user.get('created_at', '2025-09-21T00:00:00')
        else:
            # Fallback for tuple format (old code)
            user_id = user[0]
            telegram_id = user[1]  # telegram_id is the second element
            username = user[2]
            first_name = user[3]
            last_name = user[4]
            coins = user[5]
            is_vip = user[6]
            vip_expiry = user[7]
            created_at = user[8]
        
        # Get user language
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            user_lang = get_user_language(supabase, telegram_id)
        except:
            user_lang = DEFAULT_LANGUAGE
        
        vip_status = "❌"
        vip_expiry_line = ""
        if is_vip and vip_expiry:
            from datetime import datetime, timezone, timedelta
            try:
                # Parse UTC expiry time and convert to Vietnam time
                expiry_date_utc = datetime.fromisoformat(vip_expiry.replace('Z', '+00:00'))
                vietnam_tz = timezone(timedelta(hours=7))
                expiry_date_vietnam = expiry_date_utc.astimezone(vietnam_tz)
                vip_status = "✅"
                vip_expiry_line = f"(Hết hạn: {expiry_date_vietnam.strftime('%d/%m/%Y %H:%M')} VN)"
            except:
                vip_status = "✅"
        elif is_vip and not vip_expiry:
            vip_status = "✅"
        
        # Convert created_at to Vietnam time
        created_at_formatted = 'N/A'
        if created_at:
            try:
                from datetime import datetime, timezone, timedelta
                created_date_utc = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                vietnam_tz = timezone(timedelta(hours=7))
                created_date_vietnam = created_date_utc.astimezone(vietnam_tz)
                created_at_formatted = created_date_vietnam.strftime('%d/%m/%Y %H:%M')
            except:
                created_at_formatted = created_at[:10]
        
        # Wallet view: prefer Supabase (cash, coins) if available
        cash_view = 0
        coins_view = coins
        try:
            if isinstance(user, dict) and user.get('id'):
                wallets = supabase_get_wallets_by_user_id(user.get('id'))
                if wallets:
                    cash_view, coins_view = wallets
        except Exception:
            pass
        
        # Escape special characters for Markdown
        def escape_markdown(text):
            """Escape special characters for Telegram Markdown"""
            if not text:
                return text
            # Don't escape if it's already in backticks or is a username
            if text.startswith('`') or text.startswith('@'):
                return text
            # Escape special Markdown characters
            special_chars = ['_', '*', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
            for char in special_chars:
                text = text.replace(char, f'\\{char}')
            return text
        
        # Get stats with error handling
        verify_stats = get_user_verify_stats(user_id, telegram_id)
        payment_stats = get_user_payment_stats(user_id, telegram_id)
        recent_jobs = get_user_recent_jobs(user_id, telegram_id)
        
        # Multilingual labels
        labels = {
            'vi': {
                'title': '👤 Thông tin cá nhân:',
                'id': '🆔 ID',
                'name': '👤 Tên',
                'username': '📱 Username',
                'coins': '🪙 Số dư Xu',
                'cash': '💵 Số dư CASH',
                'vip': '👑 VIP',
                'joined': '📅 Tham gia',
                'rate': '💰 Tỷ giá',
                'rate_info': '• 1 xu = 1,000 VNĐ\n• 1 cash = 1,000 VNĐ',
                'deposit': '🔗 Nạp cash: /nap',
                'verify_title': '📊 Verify:',
                'payment_title': '💳 Nạp tiền:',
                'recent_jobs': '📝 5 job gần nhất:',
                'tip': '💡 Sử dụng /verify (URL) để xác minh SheerID',
                'support': '❓ Hỗ trợ: @meepzizhere',
                'channel': '📢 Kênh thông báo: https://t.me/channel_sheerid_vip_bot'
            },
            'en': {
                'title': '👤 Account Information:',
                'id': '🆔 ID',
                'name': '👤 Name',
                'username': '📱 Username',
                'coins': '🪙 Coins Balance',
                'cash': '💵 Cash Balance',
                'vip': '👑 VIP',
                'joined': '📅 Joined',
                'rate': '💰 Exchange Rate',
                'rate_info': '• 1 coin = 1,000 VND\n• 1 cash = 1,000 VND',
                'deposit': '🔗 Deposit: /nap',
                'verify_title': '📊 Verification:',
                'payment_title': '💳 Payments:',
                'recent_jobs': '📝 Recent 5 jobs:',
                'tip': '💡 Use /verify (URL) to verify SheerID',
                'support': '❓ Support: @meepzizhere',
                'channel': '📢 Channel: https://t.me/channel_sheerid_vip_bot'
            },
            'zh': {
                'title': '👤 账户信息：',
                'id': '🆔 ID',
                'name': '👤 姓名',
                'username': '📱 用户名',
                'coins': '🪙 金币余额',
                'cash': '💵 现金余额',
                'vip': '👑 VIP',
                'joined': '📅 加入时间',
                'rate': '💰 汇率',
                'rate_info': '• 1 金币 = 1,000 越南盾\n• 1 现金 = 1,000 越南盾',
                'deposit': '🔗 充值: /nap',
                'verify_title': '📊 验证：',
                'payment_title': '💳 充值记录：',
                'recent_jobs': '📝 最近5个任务：',
                'tip': '💡 使用 /verify (URL) 进行 SheerID 验证',
                'support': '❓ 支持: @meepzizhere',
                'channel': '📢 频道: https://t.me/channel_sheerid_vip_bot'
            }
        }
        
        l = labels.get(user_lang, labels['vi'])
        
        message = f"""{l['title']}

{l['id']}: `{telegram_id}`
{l['name']}: {first_name or 'N/A'} {last_name if last_name and last_name != 'User' else ''}
{l['username']}: @{username or 'N/A'}
{l['coins']}: {coins_view}
{l['cash']}: {cash_view}
{l['vip']}: {vip_status} {vip_expiry_line}
{l['joined']}: {created_at_formatted} VN

{l['rate']}:
{l['rate_info']}
{l['deposit']}

{l['verify_title']}
{verify_stats}

{l['payment_title']}
{payment_stats}

{l['recent_jobs']}
{recent_jobs}

{l['tip']}
{l['support']}
{l['channel']}"""
        
        send_telegram_message(chat_id, message, parse_mode=None)
        
    except Exception as e:
        print(f"❌ Error in send_user_info: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi khi lấy thông tin user. Vui lòng thử lại sau.\n\nError: {str(e)[:100]}", parse_mode=None)

def handle_nap_command(chat_id, user, text):
    """Handle nap (deposit) command"""
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    
    # Handle user data format (dictionary from SQLite)
    if isinstance(user, dict):
        user_id = user.get('id', 1)
        username = user.get('username', 'user')
        first_name = user.get('first_name', 'User')
        last_name = user.get('last_name', '')
        coins = user.get('coins', 0)
        is_vip = user.get('is_vip', False)
        vip_expiry = user.get('vip_expiry')
        created_at = user.get('created_at', '2025-09-21T00:00:00')
    else:
        # Fallback for tuple format (old code)
        user_id = user[0]
        username = user[1]
        first_name = user[2]
        last_name = user[3]
        coins = user[4]
        is_vip = user[5]
        vip_expiry = user[6]
        created_at = user[7]
    
    # Parse amount from command if provided
    amount = None
    if len(text.split()) > 1:
        try:
            amount = int(text.split()[1])
            if amount < 10 or amount > 1000:
                send_telegram_message(chat_id, "❌ Số xu phải từ 10 đến 1000")
                return
        except ValueError:
            send_telegram_message(chat_id, "❌ Số xu không hợp lệ")
            return
    
    if amount:
        # Create QR code directly
        create_and_send_qr(chat_id, user, amount)
    else:
        # Ask for amount
        send_telegram_message(chat_id, f"""💰 Nạp CASH vào tài khoản

💎 Tỷ giá: 1 cash = 1,000 VNĐ
📊 CASH sẽ được cộng tự động sau khi chuyển khoản

📝 Cách sử dụng rất đơn giản:

💡 Ví dụ bạn muốn nạp 10,000 VNĐ?
   Gõ lệnh: /nap 10

💡 Ví dụ bạn muốn nạp 50,000 VNĐ?
   Gõ lệnh: /nap 50

💡 Ví dụ bạn muốn nạp 100,000 VNĐ?
   Gõ lệnh: /nap 100

📌 Lưu ý:
• Tối thiểu: 10 cash (10,000 VNĐ)
• Tối đa: 1,000 cash (1,000,000 VNĐ)

❓ Cần hỗ trợ? Liên hệ: @meepzizhere
📢 Nhận xu/cash miễn phí? Tham gia kênh thông báo: https://t.me/channel_sheerid_vip_bot
""", parse_mode=None)

def handle_crypto_command(chat_id, user):
    """Handle crypto top-up command for international users"""
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    
    message = """🌍 Crypto Top-up for International Users

💰 Quick Wallet Addresses (Click to copy):

🔷 Polygon (MATIC)
0xf7acd69a02fcce2a3962c78cc2733500d086c1a0

🔷 Plasma
0xf7acd69a02fcce2a3962c78cc2733500d086c1a0

☀️ Solana (SOL)
7qFfyCQByqLRW5SRDHVLtvCT3hMeEGUJunP8dqheGVfo

---

You can also choose one of the following payment methods:
• Binance Pay
• Bybit Pay
• USDT BSC (BEP20)
• USDT TRC20 (TRON)

👇 Please select one option below to get payment details."""
    
    # Create inline keyboard with 4 buttons (2 rows)
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "💳 Binance Pay", "callback_data": "crypto_binance"},
                {"text": "💳 Bybit Pay", "callback_data": "crypto_bybit"}
            ],
            [
                {"text": "🔷 USDT BSC", "callback_data": "crypto_bsc"},
                {"text": "🔶 USDT TRC20", "callback_data": "crypto_trc20"}
            ]
        ]
    }
    
    print(f"🔍 DEBUG: Sending crypto keyboard to {chat_id}")
    result = send_telegram_message_with_keyboard(chat_id, message, keyboard)
    print(f"🔍 DEBUG: Keyboard send result: {result}")

def send_validation_error_message(chat_id, error_message, transaction_id):
    """
    Send appropriate error message based on validation error type
    
    Args:
        chat_id: Telegram chat ID
        error_message: Error message from validation
        transaction_id: Transaction ID for reference
    """
    if "already exists" in error_message.lower():
        send_telegram_message(chat_id,
            "✅ This transaction has already been processed!\n\n"
            f"🔗 Transaction Hash: {transaction_id}\n\n"
            "Check balance: /me"
        )
    elif error_message.startswith("TRANSACTION_TOO_OLD:"):
        # Parse error message: TRANSACTION_TOO_OLD:hours_old:expiry_hours
        parts = error_message.split(":")
        hours_old = parts[1] if len(parts) > 1 else "N/A"
        expiry_hours = parts[2] if len(parts) > 2 else "2"
        send_telegram_message(chat_id,
            f"❌ Transaction too old!\n\n"
            f"⏰ Age: {hours_old} hours\n"
            f"⏰ Limit: {expiry_hours} hours\n\n"
            f"📝 Transactions are only processed within {expiry_hours} hours after completion.\n\n"
            f"💡 If this is a valid transaction, please contact admin @meepzizhere for manual processing."
        )
    else:
        send_telegram_message(chat_id,
            f"❌ Validation error: {error_message}"
        )


def handle_napusdt_command(chat_id, user, text):
    """
    Handle /crypto command - Show USDT deposit instructions
    Requires user to include Note: BN<telegram_id> when transferring
    """
    import os
    
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    
    # Get telegram_id and language
    if isinstance(user, dict):
        telegram_id = str(user.get('telegram_id'))
        user_lang = user.get('language', 'vi') or 'vi'
    else:
        telegram_id = str(user[1])
        user_lang = 'vi'
    
    # Get addresses from env
    trc20_addr = os.getenv('TRON_WALLET_ADDRESS', 'TRy8XMUkWrcQmsF4zU66swwmc1jcMBdAvt')
    bep20_addr = os.getenv('BSC_WALLET_ADDRESS', '0xf7acd69a02fcce2a3962c78cc2733500d086c1a0')
    usdt_rate = os.getenv('USDT_TO_CASH_RATE', '25')
    binance_id = '723807570'
    
    # Multilingual messages
    messages = {
        'vi': f"""💰 NẠP USDT TỰ ĐỘNG

━━━━━━━━━━━━━━━━━━━━
📍 CHUYỂN TIỀN ĐẾN:

🔹 Binance Pay ID: `{binance_id}`
🔹 TRC20: `{trc20_addr}`
🔹 BEP20: `{bep20_addr}`

💱 Tỷ giá: 1 USDT = {usdt_rate} CASH
━━━━━━━━━━━━━━━━━━━━

⚠️ BẮT BUỘC GHI NOTE/MEMO:
📝 Note: `BN{telegram_id}`

🚨 QUAN TRỌNG:
• PHẢI ghi Note: BN{telegram_id} khi chuyển
• Không ghi Note = KHÔNG nhận được tiền
• Hệ thống tự động cộng trong 1-5 phút

📋 Quy định:
• Min: 1 USDT
• Max: 10,000 USDT

❓ Hỗ trợ: @meepzizhere""",

        'en': f"""💰 AUTO USDT DEPOSIT

━━━━━━━━━━━━━━━━━━━━
📍 TRANSFER TO:

🔹 Binance Pay ID: `{binance_id}`
🔹 TRC20: `{trc20_addr}`
🔹 BEP20: `{bep20_addr}`

💱 Rate: 1 USDT = {usdt_rate} CASH
━━━━━━━━━━━━━━━━━━━━

⚠️ REQUIRED NOTE/MEMO:
📝 Note: `BN{telegram_id}`

🚨 IMPORTANT:
• MUST include Note: BN{telegram_id} when transferring
• No Note = NO credit received
• Auto-credited within 1-5 minutes

📋 Rules:
• Min: 1 USDT
• Max: 10,000 USDT

❓ Support: @meepzizhere""",

        'zh': f"""💰 自动USDT充值

━━━━━━━━━━━━━━━━━━━━
📍 转账至:

🔹 Binance Pay ID: `{binance_id}`
🔹 TRC20: `{trc20_addr}`
🔹 BEP20: `{bep20_addr}`

💱 汇率: 1 USDT = {usdt_rate} CASH
━━━━━━━━━━━━━━━━━━━━

⚠️ 必须填写备注/MEMO:
📝 备注: `BN{telegram_id}`

🚨 重要提示:
• 转账时必须填写备注: BN{telegram_id}
• 不填备注 = 无法到账
• 1-5分钟内自动到账

📋 规则:
• 最小: 1 USDT
• 最大: 10,000 USDT

? 客服: @meepzizhere"""
    }
    
    message = messages.get(user_lang, messages['vi'])
    send_telegram_message(chat_id, message)


def handle_binance_command(chat_id, user, text):
    """
    Handle /binance <id> command - Supports BOTH methods
    
    Automatically detects and processes:
    1. Binance Internal Transfer (Order ID) - via Binance API
    2. USDT TRC20 (Transaction Hash) - via TronScan API
    
    Command format: /binance <order_id_or_tx_hash>
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 4.1, 4.2
    """
    # ============================================
    # MAINTENANCE MODE - /binance command (from database)
    # ============================================
    try:
        binance_maintenance = BOT_CONFIG.get('binance_maintenance', False)
        env_binance_maintenance = os.environ.get('BINANCE_MAINTENANCE', 'false').lower() == 'true'
        is_binance_maintenance = binance_maintenance or env_binance_maintenance
        
        if is_binance_maintenance:
            # Check if user is admin (admins can bypass maintenance)
            is_admin = False
            if user:
                telegram_id = user.get('telegram_id') if isinstance(user, dict) else str(chat_id)
                admin_ids = os.environ.get('ADMIN_IDS', '').split(',')
                is_admin = str(telegram_id) in admin_ids
            
            if not is_admin:
                maintenance_message = """🔧 Lệnh /binance đang bảo trì

Chức năng nạp tiền qua Binance/USDT đang được nâng cấp.

💡 Để nạp cash, vui lòng liên hệ admin:
👤 @meepzizhere

⏰ Xin lỗi vì sự bất tiện này!"""
                send_telegram_message(chat_id, maintenance_message)
                return
    except Exception as e:
        print(f"⚠️ Error checking binance maintenance: {e}")
    # ============================================
    # END MAINTENANCE MODE
    # ============================================
    
    try:
        # Import required modules for both methods
        from api.binance_api_client import BinanceAPIClient
        from api.tronscan_api_client import TronScanAPIClient
        from api.binance_deposits import (
            parse_binance_content,
            validate_binance_transaction,
            add_cash_from_binance,
            send_binance_deposit_notification,
            get_binance_deposit_by_tx_id
        )
        
        if not user:
            send_telegram_message(chat_id, "❌ Vui lòng /start trước")
            return
        
        # Extract telegram_id from user
        if isinstance(user, dict):
            telegram_id = str(user.get('telegram_id'))
        else:
            telegram_id = str(user[1])
        
        print(f"🔍 Processing /binance command from user {telegram_id}")
        
        # Parse command format: /binance <tx_hash>
        # Requirement 1.1, 1.2
        parts = text.strip().split()
        
        if len(parts) < 2:
            send_telegram_message(chat_id, 
                "❌ Invalid syntax!\n\n"
                "📝 Usage: /binance <tx_hash>\n\n"
                "💡 Example: /binance abc123def456...\n\n"
                "❓ What is TX Hash? It's the Transaction ID you receive after transferring USDT TRC20."
            )
            return
        
        transaction_id = parts[1].strip()
        
        # Validate transaction_id format
        # Requirement 1.2
        if not transaction_id or len(transaction_id) < 8:
            send_telegram_message(chat_id,
                "❌ Invalid transaction ID!\n\n"
                "ID must be at least 8 characters.\n\n"
                "💡 Binance Order ID example: /binance 123456789\n"
                "💡 TRC20 Hash example: /binance abc123def456..."
            )
            return
        
        # Auto-detect transaction type based on ID format
        # - Short numeric (8-15 digits) → Binance Order ID
        # - Starts with 0x (66 chars) → ETH/BSC Transaction Hash (will try both)
        # - Long alphanumeric (64 chars, no 0x) → TRC20 Transaction Hash
        is_binance_order = transaction_id.isdigit() and len(transaction_id) <= 15
        is_blockchain_hash = transaction_id.startswith('0x') and len(transaction_id) == 66
        is_trc20_hash = not transaction_id.startswith('0x') and len(transaction_id) == 64
        
        if is_binance_order:
            print(f"🔍 Detected: Binance Internal Transfer (Order ID)")
            transaction_type = "binance"
        elif is_blockchain_hash:
            print(f"🔍 Detected: Blockchain Transaction (0x...) - will try ETH then BSC")
            transaction_type = "blockchain"
        elif is_trc20_hash:
            print(f"🔍 Detected: USDT TRC20 (Transaction Hash)")
            transaction_type = "trc20"
        else:
            # Ambiguous - try all methods
            print(f"⚠️ Ambiguous ID format, will try all methods")
            transaction_type = "auto"
        
        # Send "Processing..." message to user
        send_telegram_message(chat_id, "⏳ Processing your transaction...\n\nPlease wait a moment.")
        
        print(f"📋 Transaction ID: {transaction_id}")
        print(f"📋 Type: {transaction_type}")
        print(f"👤 User telegram_id: {telegram_id}")
        
        # Process based on detected type
        if transaction_type == "binance" or transaction_type == "auto":
            # Try Binance API first
            success = process_binance_internal_transfer(
                chat_id, telegram_id, transaction_id, user
            )
            if success:
                return
            
            if transaction_type == "auto":
                print("⚠️ Binance API failed, trying blockchain...")
        
        if transaction_type == "blockchain" or transaction_type == "auto":
            # Try ETH first, then BSC
            print("🔍 Trying Ethereum first...")
            success = process_eth_transfer(
                chat_id, telegram_id, transaction_id, user
            )
            if success:
                return
            
            print("🔍 ETH failed, trying BSC...")
            success = process_bsc_transfer(
                chat_id, telegram_id, transaction_id, user
            )
            if success:
                return
            
            if transaction_type == "auto":
                print("⚠️ Blockchain failed, trying TRC20...")
        
        if transaction_type == "trc20" or transaction_type == "auto":
            # Try TronScan API
            success = process_trc20_transfer(
                chat_id, telegram_id, transaction_id, user
            )
            if success:
                return
        
        # If all failed
        send_telegram_message(chat_id,
            "❌ Unable to process transaction!\n\n"
            "Please check the ID and try again.\n\n"
            "💡 Binance Order ID: Short number (e.g.: 123456789)\n"
            "💡 ETH/BSC Hash: 0x... (e.g.: 0xabc123...)\n"
            "💡 TRC20 Hash: Long string (e.g.: abc123def456...)\n\n"
            "Contact admin @meepzizhere if you need help."
        )
        
    except Exception as e:
        print(f"❌ Error in handle_binance_command: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id,
            "❌ An error occurred while processing!\n\n"
            "Please try again later or contact admin @meepzizhere."
        )


def process_binance_internal_transfer(chat_id, telegram_id, order_id, user):
    """
    Process Binance Internal Transfer (Binance Pay)
    
    Args:
        chat_id: Telegram chat ID
        telegram_id: User's Telegram ID
        order_id: Binance Order ID
        user: User object
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from api.binance_api_client import BinanceAPIClient
        from api.binance_deposits import (
            parse_binance_content,
            validate_binance_transaction,
            add_cash_from_binance,
            send_binance_deposit_notification
        )
        
        print(f"💳 Processing Binance Internal Transfer: {order_id}")
        
        # Query Binance API
        try:
            client = BinanceAPIClient()
            transaction = client.get_transaction_by_order_id(order_id)
        except ValueError as e:
            print(f"❌ Binance API configuration error: {e}")
            send_telegram_message(chat_id,
                "❌ Binance API not configured!\n\n"
                "Please use USDT TRC20 or contact admin."
            )
            return False
        except Exception as e:
            print(f"❌ Error querying Binance API: {e}")
            return False
        
        if not transaction:
            print(f"❌ Binance transaction not found: {order_id}")
            return False
        
        print(f"✅ Binance transaction found: {transaction}")
        
        # Check transaction age (must be within 2 hours)
        from datetime import datetime, timedelta, timezone
        
        tx_timestamp = transaction.get('timestamp')
        tx_time = None
        if tx_timestamp:
            # Binance timestamp is in milliseconds
            tx_time = datetime.fromtimestamp(tx_timestamp / 1000, tz=timezone.utc)
            current_time = datetime.now(timezone.utc)
            time_diff = current_time - tx_time
            
            # Get expiry time from env (default 2 hours)
            expiry_hours = float(os.getenv('TRANSACTION_EXPIRY_HOURS', '2'))
            max_age = timedelta(hours=expiry_hours)
            
            print(f"⏰ Transaction time: {tx_time}")
            print(f"⏰ Current time: {current_time}")
            print(f"⏰ Age: {time_diff}")
            print(f"⏰ Max age: {max_age}")
            
            if time_diff > max_age:
                hours_old = time_diff.total_seconds() / 3600
                send_telegram_message(chat_id,
                    f"❌ Giao dịch quá cũ!\n\n"
                    f"⏰ Thời gian giao dịch: {tx_time.strftime('%d/%m/%Y %H:%M:%S')} UTC\n"
                    f"⏰ Đã qua: {hours_old:.1f} giờ\n"
                    f"⏰ Giới hạn: {expiry_hours} giờ\n\n"
                    f"📝 Giao dịch chỉ được xử lý trong vòng {expiry_hours} giờ sau khi hoàn thành.\n\n"
                    f"💡 Nếu đây là giao dịch hợp lệ, vui lòng liên hệ admin @meepzizhere để xử lý thủ công."
                )
                return False
        
        # Parse content to get telegram_id (REQUIRED for Binance Internal Transfer)
        content = transaction.get('content', '')
        extracted_telegram_id = parse_binance_content(content)
        
        print(f"📝 Content: {content}")
        print(f"🔍 Extracted telegram_id: {extracted_telegram_id}")
        
        # BINANCE INTERNAL TRANSFER: Note is REQUIRED
        # Must have note with format BN{telegram_id} to identify recipient
        
        if not extracted_telegram_id:
            send_telegram_message(chat_id,
                "❌ Nội dung chuyển khoản không đúng format!\n\n"
                f"Nội dung: {content}\n\n"
                "📝 Format đúng: BN{telegram_id}\n"
                f"💡 Ví dụ: BN{telegram_id}\n\n"
                "⚠️ Binance Internal Transfer yêu cầu note để xác định người nhận."
            )
            return False
        
        if extracted_telegram_id != telegram_id:
            send_telegram_message(chat_id,
                "❌ This transaction belongs to another user!\n\n"
                f"Telegram ID in transaction: {extracted_telegram_id}\n"
                f"Your Telegram ID: {telegram_id}\n\n"
                "💡 The content doesn't match your account."
            )
            return False
        
        print(f"✅ Note matches user: {telegram_id}")
        
        # Get transaction details
        transaction_id = transaction.get('transaction_id')
        amount = transaction.get('amount', 0)
        currency = transaction.get('currency', 'VND')
        
        print(f"💰 Amount: {amount} {currency}")
        
        # Validate transaction
        is_valid, error_message = validate_binance_transaction(
            transaction_id=transaction_id,
            telegram_id=telegram_id,
            amount=amount,
            transaction_time=tx_time
        )
        
        if not is_valid:
            send_validation_error_message(chat_id, error_message, transaction_id)
            return False
        
        # Add cash
        success = add_cash_from_binance(
            telegram_id=telegram_id,
            amount=amount,
            transaction_id=transaction_id,
            content=f"Binance Internal: {content}"
        )
        
        if not success:
            send_telegram_message(chat_id,
                "❌ Error adding cash!\n\n"
                "Contact admin @meepzizhere."
            )
            return False
        
        # Get new balance
        user_updated = get_user(telegram_id)
        if isinstance(user_updated, dict):
            new_balance = user_updated.get('cash', 0) or 0
        else:
            new_balance = amount
        
        # Send notification
        send_binance_deposit_notification(
            telegram_id=telegram_id,
            amount=amount,
            new_balance=new_balance,
            transaction_id=transaction_id
        )
        
        print(f"✅ Binance Internal Transfer processed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error in process_binance_internal_transfer: {e}")
        import traceback
        traceback.print_exc()
        return False


def process_bsc_transfer(chat_id, telegram_id, tx_hash, user):
    """
    Process USDT BEP20 Transfer (BSC on-chain) using FREE RPC
    
    Args:
        chat_id: Telegram chat ID
        telegram_id: User's Telegram ID
        tx_hash: BSC Transaction Hash (0x...)
        user: User object
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from api.bsc_rpc_client import BSCRPCClient
        from api.binance_deposits import (
            validate_binance_transaction,
            add_cash_from_binance,
            send_binance_deposit_notification
        )
        
        print(f"⛓️ Processing BSC/BEP20 Transfer (RPC): {tx_hash}")
        
        # Query BSC RPC
        try:
            client = BSCRPCClient()
            transaction = client.get_transaction_by_hash(tx_hash)
        except Exception as e:
            print(f"❌ Error querying BSC RPC: {e}")
            return False
        
        if not transaction:
            print(f"❌ BSC transaction not found: {tx_hash}")
            return False
        
        print(f"✅ BSC transaction found: {transaction}")
        
        # Verify wallet address
        expected_address = os.getenv('BSC_WALLET_ADDRESS', '')
        to_address = transaction.get('to_address', '')
        
        if not expected_address:
            send_telegram_message(chat_id,
                "❌ BSC wallet address not configured!\n\n"
                "Contact admin @meepzizhere."
            )
            return False
        
        if to_address.lower() != expected_address.lower():
            send_telegram_message(chat_id,
                "❌ Transaction not sent to our wallet!\n\n"
                f"Received: {to_address}\n"
                f"Expected: {expected_address}"
            )
            return False
        
        # BSC doesn't have memo, credit to command sender
        content = f"BSC - credited to sender {telegram_id}"
        print(f"ℹ️ BSC transaction, crediting to: {telegram_id}")
        
        # Get transaction details
        transaction_id = transaction.get('transaction_id')
        amount_usdt = transaction.get('amount', 0)
        tx_timestamp = transaction.get('timestamp', 0)
        
        # Check transaction age (must be within 2 hours)
        from datetime import datetime, timezone, timedelta
        tx_time = None
        if tx_timestamp:
            tx_time = datetime.fromtimestamp(tx_timestamp / 1000, tz=timezone.utc)
            current_time = datetime.now(timezone.utc)
            time_diff = current_time - tx_time
            
            # Get expiry time from env (default 2 hours)
            expiry_hours = float(os.getenv('TRANSACTION_EXPIRY_HOURS', '2'))
            max_age = timedelta(hours=expiry_hours)
            
            print(f"⏰ Transaction time: {tx_time}")
            print(f"⏰ Current time: {current_time}")
            print(f"⏰ Age: {time_diff}")
            print(f"⏰ Max age: {max_age}")
            
            if time_diff > max_age:
                hours_old = time_diff.total_seconds() / 3600
                send_telegram_message(chat_id,
                    f"❌ Giao dịch quá cũ!\n\n"
                    f"⏰ Thời gian giao dịch: {tx_time.strftime('%d/%m/%Y %H:%M:%S')} UTC\n"
                    f"⏰ Đã qua: {hours_old:.1f} giờ\n"
                    f"⏰ Giới hạn: {expiry_hours} giờ\n\n"
                    f"📝 Giao dịch chỉ được xử lý trong vòng {expiry_hours} giờ sau khi hoàn thành.\n\n"
                    f"💡 Nếu đây là giao dịch hợp lệ, vui lòng liên hệ admin @meepzizhere để xử lý thủ công."
                )
                return False
        
        # Convert USDT to CASH
        usdt_to_cash_rate = float(os.getenv('USDT_TO_CASH_RATE', '25'))
        amount_cash = amount_usdt * usdt_to_cash_rate
        
        print(f"💰 {amount_usdt} USDT = {amount_cash:,.0f} CASH")
        
        # Validate transaction
        is_valid, error_message = validate_binance_transaction(
            transaction_id=transaction_id,
            telegram_id=telegram_id,
            amount=amount_cash,
            transaction_time=tx_time
        )
        
        if not is_valid:
            send_validation_error_message(chat_id, error_message, transaction_id)
            return False
        
        # Add cash
        success = add_cash_from_binance(
            telegram_id=telegram_id,
            amount=amount_cash,
            transaction_id=transaction_id,
            content=f"BSC/BEP20: {content} | {amount_usdt} USDT @ {usdt_to_cash_rate}"
        )
        
        if not success:
            send_telegram_message(chat_id,
                "❌ Error adding cash!\n\n"
                "Contact admin @meepzizhere."
            )
            return False
        
        # Get new balance
        user_updated = get_user(telegram_id)
        if isinstance(user_updated, dict):
            new_balance = user_updated.get('cash', 0) or 0
        else:
            new_balance = amount_cash
        
        # Send notification
        send_binance_deposit_notification(
            telegram_id=telegram_id,
            amount=amount_cash,
            new_balance=new_balance,
            transaction_id=transaction_id
        )
        
        # Send conversion details
        send_telegram_message(chat_id,
            f"💱 Conversion:\n"
            f"   {amount_usdt} USDT × {usdt_to_cash_rate} = {amount_cash:,.0f} CASH"
        )
        
        print(f"✅ BSC Transfer processed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error in process_bsc_transfer: {e}")
        import traceback
        traceback.print_exc()
        return False


def process_eth_transfer(chat_id, telegram_id, tx_hash, user):
    """
    Process USDT ERC20 Transfer (Ethereum on-chain)
    
    Args:
        chat_id: Telegram chat ID
        telegram_id: User's Telegram ID
        tx_hash: ETH Transaction Hash (0x...)
        user: User object
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from api.etherscan_api_client import EtherscanAPIClient
        from api.binance_deposits import (
            parse_binance_content,
            validate_binance_transaction,
            add_cash_from_binance,
            send_binance_deposit_notification
        )
        
        print(f"⛓️ Processing ETH/ERC20 Transfer: {tx_hash}")
        
        # Query Etherscan API
        try:
            client = EtherscanAPIClient()
            transaction = client.get_transaction_by_hash(tx_hash)
        except Exception as e:
            print(f"❌ Error querying Etherscan API: {e}")
            return False
        
        if not transaction:
            print(f"❌ ETH transaction not found: {tx_hash}")
            return False
        
        print(f"✅ ETH transaction found: {transaction}")
        
        # Verify wallet address
        expected_address = os.getenv('ETH_WALLET_ADDRESS', '')
        to_address = transaction.get('to_address', '')
        
        if not expected_address:
            send_telegram_message(chat_id,
                "❌ ETH wallet address not configured!\n\n"
                "Contact admin @meepzizhere."
            )
            return False
        
        if to_address.lower() != expected_address.lower():
            send_telegram_message(chat_id,
                "❌ Transaction not sent to our wallet!\n\n"
                f"Received address: {to_address}\n"
                f"Expected address: {expected_address}"
            )
            return False
        
        # ETH doesn't have memo, always credit to command sender
        content = f"ETH - credited to sender {telegram_id}"
        print(f"ℹ️ ETH transaction, crediting to command sender: {telegram_id}")
        
        # Get transaction details and convert USDT to CASH
        transaction_id = transaction.get('transaction_id')
        amount_usdt = transaction.get('amount', 0)
        currency = transaction.get('currency', 'USDT')
        tx_timestamp = transaction.get('timestamp', 0)
        
        # Parse transaction time for validation
        from datetime import datetime, timezone
        tx_time = None
        if tx_timestamp:
            tx_time = datetime.fromtimestamp(tx_timestamp / 1000, tz=timezone.utc)
            print(f"⏰ Transaction time: {tx_time}")
        
        # Convert USDT to CASH (1 USDT = 25 CASH)
        usdt_to_cash_rate = float(os.getenv('USDT_TO_CASH_RATE', '25'))
        amount_cash = amount_usdt * usdt_to_cash_rate
        
        print(f"💰 Amount: {amount_usdt} {currency} = {amount_cash:,.0f} CASH")
        print(f"💱 Rate: 1 USDT = {usdt_to_cash_rate} CASH")
        
        # Validate transaction
        is_valid, error_message = validate_binance_transaction(
            transaction_id=transaction_id,
            telegram_id=telegram_id,
            amount=amount_cash,
            transaction_time=tx_time
        )
        
        if not is_valid:
            send_validation_error_message(chat_id, error_message, transaction_id)
            return False
        
        # Add cash
        success = add_cash_from_binance(
            telegram_id=telegram_id,
            amount=amount_cash,
            transaction_id=transaction_id,
            content=f"ETH/ERC20: {content} | {amount_usdt} USDT @ {usdt_to_cash_rate} CASH/USDT"
        )
        
        if not success:
            send_telegram_message(chat_id,
                "❌ Error adding cash!\n\n"
                "Contact admin @meepzizhere."
            )
            return False
        
        # Get new balance
        user_updated = get_user(telegram_id)
        if isinstance(user_updated, dict):
            new_balance = user_updated.get('cash', 0) or 0
        else:
            new_balance = amount_cash
        
        # Send notification
        send_binance_deposit_notification(
            telegram_id=telegram_id,
            amount=amount_cash,
            new_balance=new_balance,
            transaction_id=transaction_id
        )
        
        # Send conversion details
        send_telegram_message(chat_id,
            f"💱 Conversion details:\n"
            f"   {amount_usdt} USDT × {usdt_to_cash_rate} = {amount_cash:,.0f} CASH"
        )
        
        print(f"✅ ETH/ERC20 Transfer processed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error in process_eth_transfer: {e}")
        import traceback
        traceback.print_exc()
        return False


def handle_seller_command(chat_id, user, text):
    """
    Handle /seller commands for sellers
    /seller help - Show seller commands
    /seller info - Show seller account info
    /seller jobs - Show recent jobs
    /seller api - Show API key and docs
    """
    try:
        from .supabase_client import get_supabase_client
        
        if not user:
            send_telegram_message(chat_id, "❌ Vui lòng /start trước")
            return
        
        # Get telegram_id
        if isinstance(user, dict):
            telegram_id = user.get('telegram_id')
            user_lang = user.get('language', 'vi') or 'vi'
        else:
            telegram_id = user[1]
            user_lang = 'vi'
        
        # Check if user is a seller
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Lỗi kết nối database")
            return
        
        # Try both string and int formats for telegram_id
        print(f"🔍 DEBUG /seller: Looking for seller with telegram_id={telegram_id} (type: {type(telegram_id)})")
        seller_result = supabase.table('sellers').select('*').eq('telegram_id', str(telegram_id)).execute()
        print(f"🔍 DEBUG /seller: Query result: {seller_result.data}")
        
        if not seller_result.data:
            msg = (
                "❌ *Bạn chưa là Seller*\n\n"
                "Liên hệ Admin để đăng ký làm Seller:\n"
                "• Được cấp API key riêng\n"
                "• Tích hợp verify vào website của bạn\n"
                "• Giá sỉ ưu đãi\n\n"
                "📞 Contact: @meepzizhere"
            )
            send_telegram_message(chat_id, msg)
            return
        
        seller = seller_result.data[0]
        
        # Parse subcommand
        parts = text.strip().split()
        subcommand = parts[1].lower() if len(parts) > 1 else 'help'
        
        if subcommand == 'help':
            msg = (
                "📋 *SELLER COMMANDS*\n\n"
                "🔹 `/seller help` - Xem hướng dẫn này\n"
                "🔹 `/seller info` - Xem thông tin tài khoản seller\n"
                "🔹 `/seller jobs` - Xem 10 jobs gần đây\n"
                "🔹 `/seller api` - Xem API key và docs\n"
                "🔹 `/buycredits <số>` - Mua credits bằng cash\n\n"
                "📖 *API Documentation:*\n"
                "https://dqsheerid.vercel.app/docs\n\n"
                "💡 *Tỷ giá:* 3 cash = 1 credit"
            )
            send_telegram_message(chat_id, msg)
            
        elif subcommand == 'info':
            status_icon = "✅" if seller.get('is_active') else "❌"
            status_text = "Active" if seller.get('is_active') else "Inactive"
            # Get seller info - replace underscore to avoid any parsing issues
            seller_name = str(seller.get('name', 'N/A')).replace('_', ' ')
            seller_email = str(seller.get('email', 'N/A') or 'N/A').replace('_', ' ')
            created_date = seller.get('created_at', 'N/A')[:10] if seller.get('created_at') else 'N/A'
            msg = (
                "👤 SELLER INFO\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🆔 Seller ID: {seller.get('id')}\n"
                f"📛 Tên: {seller_name}\n"
                f"📧 Email: {seller_email}\n"
                f"💳 Credits: {seller.get('credits', 0)}\n"
                f"📊 Đã dùng: {seller.get('total_used', 0)}\n"
                f"📌 Trạng thái: {status_icon} {status_text}\n"
                f"📅 Ngày tạo: {created_date}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💡 Dùng /seller help để xem các lệnh"
            )
            result = send_telegram_message_plain(chat_id, msg)
            print(f"DEBUG /seller info result: {result}")
            
        elif subcommand == 'jobs':
            # Get recent jobs
            jobs_result = supabase.table('seller_jobs').select('*').eq('seller_id', seller.get('id')).order('created_at', desc=True).limit(10).execute()
            
            if not jobs_result.data:
                send_telegram_message(chat_id, "📭 Chưa có job nào")
                return
            
            msg = "📋 *10 JOBS GẦN ĐÂY*\n\n"
            for job in jobs_result.data:
                status_emoji = "✅" if job.get('status') == 'completed' else "❌" if job.get('status') == 'failed' else "⏳"
                created = job.get('created_at', '')[:16].replace('T', ' ') if job.get('created_at') else 'N/A'
                msg += f"{status_emoji} `{job.get('job_id', 'N/A')[:8]}...` - {job.get('status', 'N/A')} - {created}\n"
            
            send_telegram_message(chat_id, msg)
            
        elif subcommand == 'api':
            api_key = seller.get('api_key', 'N/A')
            # Mask API key for security
            masked_key = api_key[:10] + '...' + api_key[-4:] if len(api_key) > 14 else api_key
            
            msg = (
                f"🔑 *API INFORMATION*\n\n"
                f"📌 API Key: `{masked_key}`\n"
                f"(Dùng /seller apikey để xem full key)\n\n"
                f"📖 *API Docs:*\n"
                f"https://dqsheerid.vercel.app/docs\n\n"
                f"🔗 *Base URL:*\n"
                f"`https://dqsheerid.vercel.app`\n\n"
                f"📡 *Endpoints:*\n"
                f"• `POST /api/seller/verify` - Submit verification\n"
                f"• `GET /api/seller/status/<job_id>` - Check status\n"
                f"• `GET /api/seller/balance` - Check credits"
            )
            send_telegram_message(chat_id, msg)
            
        elif subcommand == 'apikey':
            api_key = seller.get('api_key', 'N/A')
            msg = (
                f"🔑 *YOUR API KEY*\n\n"
                f"`{api_key}`\n\n"
                f"⚠️ Giữ bí mật key này!"
            )
            send_telegram_message(chat_id, msg)
            
        else:
            send_telegram_message(chat_id, "❌ Lệnh không hợp lệ. Dùng `/seller help` để xem hướng dẫn.")
            
    except Exception as e:
        print(f"Error in handle_seller_command: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi: {e}")


def handle_buycredits_command(chat_id, user, text):
    """
    Handle /buycredits <amount> command
    Allows sellers to convert their cash to seller credits
    
    Rate: Read from seller's exchange_rate in database (default 3 cash = 1 credit)
    """
    try:
        from .supabase_client import get_supabase_client
        
        DEFAULT_CASH_PER_CREDIT = 3  # Default: 3 cash = 1 credit
        
        if not user:
            send_telegram_message(chat_id, "❌ Vui lòng /start trước")
            return
        
        # Get telegram_id and language
        if isinstance(user, dict):
            telegram_id = user.get('telegram_id')
            user_cash = user.get('cash', 0)
            user_lang = user.get('language', 'vi') or 'vi'
        else:
            telegram_id = user[1]
            user_cash = user[8] if len(user) > 8 else 0
            user_lang = 'vi'
        
        # Get seller's exchange rate from database
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Database connection error!")
            return
        
        seller_result = supabase.table('sellers').select('*').eq('telegram_id', telegram_id).eq('is_active', True).execute()
        
        # Get exchange rate from seller or use default
        # exchange_rate in database = cash per credit (e.g., 5 means 5 cash = 1 credit)
        if seller_result.data:
            seller = seller_result.data[0]
            raw_rate = seller.get('exchange_rate', DEFAULT_CASH_PER_CREDIT)
            # If rate is stored as VND (>= 100), convert to cash (assuming 1000 VND = 1 cash)
            if raw_rate >= 100:
                CASH_PER_CREDIT = raw_rate // 1000
            else:
                CASH_PER_CREDIT = raw_rate
            if CASH_PER_CREDIT < 1:
                CASH_PER_CREDIT = DEFAULT_CASH_PER_CREDIT
        else:
            CASH_PER_CREDIT = DEFAULT_CASH_PER_CREDIT
        
        # Parse command
        parts = text.strip().split()
        
        if len(parts) < 2:
            max_credits = user_cash // CASH_PER_CREDIT
            example_cost = 10 * CASH_PER_CREDIT
            
            if user_lang == 'en':
                msg = (
                    "📊 *Buy Credits for Seller API*\n\n"
                    f"Usage: `/buycredits <credits>`\n\n"
                    f"💱 Rate: {CASH_PER_CREDIT} cash = 1 credit\n"
                    f"💵 Current cash: {user_cash}\n"
                    f"🎯 Max can buy: {max_credits} credits\n\n"
                    f"Example: `/buycredits 10` - Buy 10 credits (costs {example_cost} cash)"
                )
            elif user_lang == 'zh':
                msg = (
                    "📊 *购买卖家API积分*\n\n"
                    f"用法: `/buycredits <积分数>`\n\n"
                    f"💱 汇率: {CASH_PER_CREDIT} cash = 1 credit\n"
                    f"💵 当前现金: {user_cash}\n"
                    f"🎯 最多可购买: {max_credits} 积分\n\n"
                    f"示例: `/buycredits 10` - 购买10积分 (花费 {example_cost} cash)"
                )
            else:
                msg = (
                    "📊 *Mua Credits cho Seller API*\n\n"
                    f"Cú pháp: `/buycredits <số_credits>`\n\n"
                    f"💱 Tỷ giá: {CASH_PER_CREDIT} cash = 1 credit\n"
                    f"💵 Cash hiện tại: {user_cash}\n"
                    f"🎯 Có thể mua tối đa: {max_credits} credits\n\n"
                    f"Ví dụ: `/buycredits 10` - Mua 10 credits (tốn {example_cost} cash)"
                )
            send_telegram_message(chat_id, msg)
            return
        
        try:
            amount = int(parts[1])
        except ValueError:
            err = "❌ Credits must be an integer!" if user_lang == 'en' else "❌ 积分必须是整数！" if user_lang == 'zh' else "❌ Số credits phải là số nguyên!"
            send_telegram_message(chat_id, err)
            return
        
        if amount <= 0:
            err = "❌ Credits must be greater than 0!" if user_lang == 'en' else "❌ 积分必须大于0！" if user_lang == 'zh' else "❌ Số credits phải lớn hơn 0!"
            send_telegram_message(chat_id, err)
            return
        
        # Calculate cash needed
        cash_needed = amount * CASH_PER_CREDIT
        
        # Check if user has enough cash
        if user_cash < cash_needed:
            max_credits = user_cash // CASH_PER_CREDIT
            if user_lang == 'en':
                msg = (
                    f"❌ Insufficient cash!\n\n"
                    f"💵 Current cash: {user_cash}\n"
                    f"💰 Need: {cash_needed} cash (for {amount} credits)\n"
                    f"🎯 Max can buy: {max_credits} credits\n\n"
                    "💡 Top up cash with /nap or /crypto"
                )
            elif user_lang == 'zh':
                msg = (
                    f"❌ 现金不足！\n\n"
                    f"💵 当前现金: {user_cash}\n"
                    f"💰 需要: {cash_needed} cash (购买 {amount} 积分)\n"
                    f"🎯 最多可购买: {max_credits} 积分\n\n"
                    "💡 使用 /nap 或 /crypto 充值"
                )
            else:
                msg = (
                    f"❌ Không đủ cash!\n\n"
                    f"💵 Cash hiện tại: {user_cash}\n"
                    f"💰 Cần: {cash_needed} cash (cho {amount} credits)\n"
                    f"🎯 Có thể mua tối đa: {max_credits} credits\n\n"
                    "💡 Nạp thêm cash bằng /nap hoặc /crypto"
                )
            send_telegram_message(chat_id, msg)
            return
        
        # Seller already fetched above, check if exists
        if not seller_result.data:
            if user_lang == 'en':
                msg = "❌ You don't have a Seller account!\n\n📞 Contact admin to register Seller API:\n@meepzizhere"
            elif user_lang == 'zh':
                msg = "❌ 您还没有卖家账户！\n\n📞 联系管理员注册卖家API:\n@meepzizhere"
            else:
                msg = "❌ Bạn chưa có tài khoản Seller!\n\n📞 Liên hệ admin để đăng ký Seller API:\n@meepzizhere"
            send_telegram_message(chat_id, msg)
            return
        
        # seller already fetched above
        seller_id = seller['id']
        current_credits = seller.get('credits', 0)
        
        # Deduct cash from user
        user_result = supabase.table('users').select('cash').eq('telegram_id', telegram_id).execute()
        if not user_result.data:
            send_telegram_message(chat_id, "❌ User not found!")
            return
        
        current_cash = user_result.data[0].get('cash', 0)
        cash_needed = amount * CASH_PER_CREDIT
        
        if current_cash < cash_needed:
            send_telegram_message(chat_id, f"❌ Insufficient cash! Have: {current_cash}, need: {cash_needed}")
            return
        
        # Update user cash
        supabase.table('users').update({
            'cash': current_cash - cash_needed
        }).eq('telegram_id', telegram_id).execute()
        
        # Add credits to seller
        new_credits = current_credits + amount
        supabase.table('sellers').update({
            'credits': new_credits
        }).eq('id', seller_id).execute()
        
        # Send success message based on language
        new_cash = current_cash - cash_needed
        if user_lang == 'en':
            msg = (
                f"✅ *Credits purchased successfully!*\n\n"
                f"💰 Credits bought: +{amount}\n"
                f"💵 Cash deducted: -{cash_needed} (rate {CASH_PER_CREDIT}:1)\n\n"
                f"📊 *New balance:*\n"
                f"• Cash: {new_cash}\n"
                f"• Seller Credits: {new_credits}\n\n"
                f"🔑 Seller ID: {seller_id}"
            )
        elif user_lang == 'zh':
            msg = (
                f"✅ *积分购买成功！*\n\n"
                f"💰 购买积分: +{amount}\n"
                f"💵 扣除现金: -{cash_needed} (汇率 {CASH_PER_CREDIT}:1)\n\n"
                f"📊 *新余额:*\n"
                f"• 现金: {new_cash}\n"
                f"• 卖家积分: {new_credits}\n\n"
                f"🔑 卖家ID: {seller_id}"
            )
        else:
            msg = (
                f"✅ *Mua credits thành công!*\n\n"
                f"💰 Credits đã mua: +{amount}\n"
                f"💵 Cash đã trừ: -{cash_needed} (tỷ giá {CASH_PER_CREDIT}:1)\n\n"
                f"📊 *Số dư mới:*\n"
                f"• Cash: {new_cash}\n"
                f"• Seller Credits: {new_credits}\n\n"
                f"🔑 Seller ID: {seller_id}"
            )
        send_telegram_message(chat_id, msg)
        
        print(f"✅ User {telegram_id} bought {amount} credits (cost {cash_needed} cash) for seller {seller_id}")
        
    except Exception as e:
        print(f"❌ Error in handle_buycredits_command: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi: {e}")


def process_trc20_transfer(chat_id, telegram_id, tx_hash, user):
    """
    Process USDT TRC20 Transfer (on-chain)
    
    Args:
        chat_id: Telegram chat ID
        telegram_id: User's Telegram ID
        tx_hash: TRC20 Transaction Hash
        user: User object
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from api.tronscan_api_client import TronScanAPIClient
        from api.binance_deposits import (
            parse_binance_content,
            validate_binance_transaction,
            add_cash_from_binance,
            send_binance_deposit_notification
        )
        
        print(f"⛓️ Processing TRC20 Transfer: {tx_hash}")
        
        # Query TronScan API
        try:
            client = TronScanAPIClient()
            transaction = client.get_transaction_by_hash(tx_hash)
        except Exception as e:
            print(f"❌ Error querying TronScan API: {e}")
            return False
        
        if not transaction:
            print(f"❌ TRC20 transaction not found: {tx_hash}")
            return False
        
        print(f"✅ TRC20 transaction found: {transaction}")
        
        # Check transaction age (must be within 2 hours)
        from datetime import datetime, timedelta, timezone
        
        tx_timestamp = transaction.get('timestamp', 0)
        tx_time = None
        if tx_timestamp:
            # Convert milliseconds to seconds
            tx_time = datetime.fromtimestamp(tx_timestamp / 1000, tz=timezone.utc)
            current_time = datetime.now(timezone.utc)
            time_diff = current_time - tx_time
            
            # Get expiry time from env (default 2 hours)
            expiry_hours = float(os.getenv('TRANSACTION_EXPIRY_HOURS', '2'))
            max_age = timedelta(hours=expiry_hours)
            
            print(f"⏰ Transaction time: {tx_time}")
            print(f"⏰ Current time: {current_time}")
            print(f"⏰ Age: {time_diff}")
            print(f"⏰ Max age: {max_age}")
            
            if time_diff > max_age:
                hours_old = time_diff.total_seconds() / 3600
                send_telegram_message(chat_id,
                    f"❌ Giao dịch quá cũ!\n\n"
                    f"⏰ Thời gian giao dịch: {tx_time.strftime('%d/%m/%Y %H:%M:%S')} UTC\n"
                    f"⏰ Đã qua: {hours_old:.1f} giờ\n"
                    f"⏰ Giới hạn: {expiry_hours} giờ\n\n"
                    f"📝 Giao dịch chỉ được xử lý trong vòng {expiry_hours} giờ sau khi hoàn thành.\n\n"
                    f"💡 Nếu đây là giao dịch hợp lệ, vui lòng liên hệ admin @meepzizhere để xử lý thủ công."
                )
                return False
        
        # Verify wallet address
        expected_address = os.getenv('TRON_WALLET_ADDRESS', '')
        to_address = transaction.get('to_address', '')
        
        if not expected_address:
            send_telegram_message(chat_id,
                "❌ TRON wallet address not configured!\n\n"
                "Contact admin @meepzizhere."
            )
            return False
        
        if to_address.lower() != expected_address.lower():
            send_telegram_message(chat_id,
                "❌ Transaction not sent to our wallet!\n\n"
                f"Received address: {to_address}\n"
                f"Expected address: {expected_address}"
            )
            return False
        
        # Parse memo for telegram_id (OPTIONAL)
        content = transaction.get('content', '')
        extracted_telegram_id = parse_binance_content(content)
        
        print(f"📝 Memo: {content if content else '(empty)'}")
        print(f"🔍 Extracted telegram_id: {extracted_telegram_id}")
        
        # NEW LOGIC: Memo is OPTIONAL
        # - If no memo → Credit to command sender (telegram_id)
        # - If has memo → Validate it matches command sender
        
        if extracted_telegram_id:
            # Memo exists, verify it matches command sender
            if extracted_telegram_id != telegram_id:
                send_telegram_message(chat_id,
                    "❌ This transaction belongs to another user!\n\n"
                    f"Telegram ID in memo: {extracted_telegram_id}\n"
                    f"Your Telegram ID: {telegram_id}\n\n"
                    "💡 The memo doesn't match your account.\n"
                    "If this is your transaction, please send it without memo or with correct memo."
                )
                return False
            print(f"✅ Memo matches command sender: {telegram_id}")
        else:
            # No memo, credit to command sender
            print(f"ℹ️ No memo found, crediting to command sender: {telegram_id}")
            content = f"No memo - credited to sender {telegram_id}"
        
        # Get transaction details and convert USDT to CASH
        transaction_id = transaction.get('transaction_id')
        amount_usdt = transaction.get('amount', 0)
        currency = transaction.get('currency', 'USDT')
        
        # Convert USDT to CASH (1 USDT = 25 CASH)
        usdt_to_cash_rate = float(os.getenv('USDT_TO_CASH_RATE', '25'))
        amount_cash = amount_usdt * usdt_to_cash_rate
        
        print(f"💰 Amount: {amount_usdt} {currency} = {amount_cash:,.0f} CASH")
        print(f"💱 Rate: 1 USDT = {usdt_to_cash_rate} CASH")
        
        # Validate transaction
        is_valid, error_message = validate_binance_transaction(
            transaction_id=transaction_id,
            telegram_id=telegram_id,
            amount=amount_cash,
            transaction_time=tx_time
        )
        
        if not is_valid:
            send_validation_error_message(chat_id, error_message, transaction_id)
            return False
        
        # Add cash
        success = add_cash_from_binance(
            telegram_id=telegram_id,
            amount=amount_cash,
            transaction_id=transaction_id,
            content=f"TRC20: {content} | {amount_usdt} USDT @ {usdt_to_cash_rate} CASH/USDT"
        )
        
        if not success:
            send_telegram_message(chat_id,
                "❌ Error adding cash!\n\n"
                "Contact admin @meepzizhere."
            )
            return False
        
        # Get new balance
        user_updated = get_user(telegram_id)
        if isinstance(user_updated, dict):
            new_balance = user_updated.get('cash', 0) or 0
        else:
            new_balance = amount_cash
        
        # Send notification
        send_binance_deposit_notification(
            telegram_id=telegram_id,
            amount=amount_cash,
            new_balance=new_balance,
            transaction_id=transaction_id
        )
        
        # Send conversion details
        send_telegram_message(chat_id,
            f"💱 Conversion details:\n"
            f"   {amount_usdt} USDT × {usdt_to_cash_rate} = {amount_cash:,.0f} CASH"
        )
        
        print(f"✅ TRC20 Transfer processed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error in process_trc20_transfer: {e}")
        import traceback
        traceback.print_exc()
        return False


def handle_crypto_binance_callback(chat_id, telegram_id):
    """Handle Binance Pay callback - Auto deposit via Binance API"""
    import os
    
    # Get deposit addresses from env
    trc20_addr = os.getenv('TRON_WALLET_ADDRESS', 'TRy8XMUkWrcQmsF4zU66swwmc1jcMBdAvt')
    bep20_addr = os.getenv('BSC_WALLET_ADDRESS', '0xf7acd69a02fcce2a3962c78cc2733500d086c1a0')
    usdt_rate = os.getenv('USDT_TO_CASH_RATE', '25')
    binance_id = '723807570'  # Binance Pay ID for internal transfer
    
    message = f"""💳 BINANCE AUTO DEPOSIT

━━━━━━━━━━━━━━━━━━━━
📍 TRANSFER TO:

🔹 Binance Pay ID: `{binance_id}`
🔹 TRC20: `{trc20_addr}`
🔹 BEP20: `{bep20_addr}`

💱 Rate: 1 USDT = {usdt_rate} CASH
━━━━━━━━━━━━━━━━━━━━

🚨 REQUIRED NOTE/MEMO:
📝 Note: `BN{telegram_id}`

⚠️ IMPORTANT:
• MUST include Note: BN{telegram_id}
• No Note = NO credit received
• Auto-credited within 1-5 minutes

📋 Rules: Min 1 USDT

❓ Support: @meepzizhere"""
    
    # Send photo with caption
    binance_path = os.path.join(os.path.dirname(__file__), "binance.jpg")
    send_telegram_photo_with_markdown(chat_id, binance_path, message)

def send_telegram_photo(chat_id, photo_filename, caption=""):
    """Send photo file to Telegram chat"""
    try:
        print(f"🔍 DEBUG: Sending photo {photo_filename} to {chat_id}")
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
        if not bot_token:
            print("No bot token available")
            return False
        
        # Check if file exists
        print(f"🔍 DEBUG: Checking if file exists: {photo_filename}")
        print(f"🔍 DEBUG: Current working directory: {os.getcwd()}")
        print(f"🔍 DEBUG: File exists: {os.path.exists(photo_filename)}")
        
        if not os.path.exists(photo_filename):
            print(f"Photo file not found: {photo_filename}")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        
        # Send file as multipart/form-data
        with open(photo_filename, 'rb') as photo_file:
            files = {'photo': photo_file}
            data = {
                'chat_id': chat_id,
                'caption': caption
            }
            
            response = requests.post(url, data=data, files=files, timeout=30)
            print(f"Photo sent: {response.status_code} - {photo_filename}")
            return response.status_code == 200
        
    except Exception as e:
        print(f"Failed to send photo: {e}")
        return False

def send_telegram_photo_with_markdown(chat_id, photo_filename, caption=""):
    """Send photo file to Telegram chat with Markdown formatting"""
    try:
        print(f"🔍 DEBUG: Sending photo with markdown {photo_filename} to {chat_id}")
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
        if not bot_token:
            print("No bot token available")
            return False
        
        # Check if file exists
        if not os.path.exists(photo_filename):
            print(f"Photo file not found: {photo_filename}")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        
        # Send file as multipart/form-data with Markdown
        with open(photo_filename, 'rb') as photo_file:
            files = {'photo': photo_file}
            data = {
                'chat_id': chat_id,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, data=data, files=files, timeout=30)
            print(f"Photo with markdown sent: {response.status_code} - {photo_filename}")
            return response.status_code == 200
        
    except Exception as e:
        print(f"Failed to send photo with markdown: {e}")
        return False

def handle_crypto_bybit_callback(chat_id, telegram_id):
    """Handle Bybit Pay callback"""
    message = """💳 Payment via Bybit Pay

⚠️ My Bybit ID: `510982773`

After completing the transfer, contact admin @meepzizhere to manually credit your coins.

📋 Deposit rules:
• Min: 1 USDT
• Rate: 1 USDT = 24 CASH

💰 CASH can be used for:
• Verify (if Coins are not enough, CASH will be deducted)
• Use in /shop

❓ Help: /help""".format(telegram_id)
    
    # Send photo with caption
    import os
    bybit_path = os.path.join(os.path.dirname(__file__), "bybit.jpg")
    send_telegram_photo_with_markdown(chat_id, bybit_path, message)

def handle_crypto_bsc_callback(chat_id, telegram_id):
    """Handle USDT BSC (BEP20) callback"""
    import os
    bsc_wallet = os.getenv('BSC_WALLET_ADDRESS', '0xf7acd69a02fcce2a3962c78cc2733500d086c1a0')
    
    message = f"""🔷 USDT BSC (BEP20) - Auto Payment

📍 **Wallet Address:**
`{bsc_wallet}`

📋 **Instructions:**
1. Open Binance → Withdraw
2. Select: USDT
3. Network: **BEP20 (BSC)**
4. Paste address above
5. Amount: Min 1 USDT
6. Withdraw

7. Copy transaction hash (0x...)
8. **Auto pay:** `/binance 0x<hash>`

⏰ **Time Limit:** 2 hours
💱 **Rate:** 1 USDT = 24 CASH
🕐 **Speed:** 10-30 seconds

💰 **CASH can be used for:**
• Verify (if Coins not enough)
• Shop purchases

❓ **Help:** /help
👤 **Contact:** @meepzizhere"""
    
    # Send photo with caption
    bsc_path = os.path.join(os.path.dirname(__file__), "binancebsc.jpg")
    send_telegram_photo_with_markdown(chat_id, bsc_path, message)

def handle_crypto_trc20_callback(chat_id, telegram_id):
    """Handle USDT TRC20 (TRON) callback"""
    import os
    tron_wallet = os.getenv('TRON_WALLET_ADDRESS', 'TRy8XMUkWrcQmsF4zU66swwmc1jcMBdAvt')
    
    message = f"""🔶 USDT TRC20 (TRON) - Auto Payment

📍 **Wallet Address:**
`{tron_wallet}`

📋 **Instructions:**
1. Open Binance → Withdraw
2. Select: USDT
3. Network: **TRC20 (TRON)**
4. Paste address above
5. Amount: Min 1 USDT
6. Withdraw

7. Copy transaction hash (64 chars)
8. **Auto pay:** `/binance <hash>`

⏰ **Time Limit:** 2 hours
💱 **Rate:** 1 USDT = 24 CASH
🕐 **Speed:** 1-2 minutes

💰 **CASH can be used for:**
• Verify (if Coins not enough)
• Shop purchases

❓ **Help:** /help
👤 **Contact:** @meepzizhere"""
    
    # Send photo with caption
    trc_path = os.path.join(os.path.dirname(__file__), "binancetrc.jpg")
    send_telegram_photo_with_markdown(chat_id, trc_path, message)

def handle_lsgd_nap_callback(chat_id, telegram_id):
    """Handle transaction history - deposit callback"""
    try:
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối database")
            return
        
        # Get user's deposit transactions
        transactions = supabase.table('payment_transactions').select('transfer_amount, transaction_date, transaction_code, gateway, status').eq('telegram_id', telegram_id).order('created_at', desc=True).limit(10).execute()
        
        if not transactions.data:
            send_telegram_message(chat_id, "💳 Bạn chưa có giao dịch nạp tiền nào.")
            return
        
        # Calculate totals
        total_transactions = len(transactions.data)
        total_amount = sum(tx.get('transfer_amount', 0) for tx in transactions.data if tx.get('status') == 'completed')
        
        message = f"""💳 LỊCH SỬ NẠP TIỀN

📊 Tổng giao dịch: {total_transactions}
💰 Tổng số tiền đã nạp: {total_amount:,.0f} VNĐ

"""
        
        for i, tx in enumerate(transactions.data, 1):
            amount = tx.get('transfer_amount', 0)
            date = tx.get('transaction_date', 'N/A')
            code = tx.get('transaction_code', 'N/A')
            gateway = tx.get('gateway', 'N/A')
            status = tx.get('status', 'unknown')
            
            # Format date to MM-DD-YYYY HH:MM Vietnam time
            try:
                from datetime import datetime, timezone, timedelta
                if date and date != 'N/A':
                    # Parse the date string (assuming it's in format YYYY-MM-DD HH:MM:SS)
                    if 'T' in date:
                        date_obj = datetime.fromisoformat(date.replace('Z', '+00:00'))
                    else:
                        date_obj = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                        date_obj = date_obj.replace(tzinfo=timezone.utc)
                    
                    # Convert to Vietnam timezone
                    vietnam_tz = timezone(timedelta(hours=7))
                    date_vietnam = date_obj.astimezone(vietnam_tz)
                    date_str = date_vietnam.strftime('%m-%d-%Y %H:%M')
                else:
                    date_str = 'N/A'
            except:
                date_str = str(date)[:16] if date != 'N/A' else 'N/A'
            
            status_emoji = '✅' if status == 'completed' else '⏳' if status == 'pending' else '❌'
            
            message += f"""
{i}. {status_emoji} {amount:,.0f} VNĐ
📅 {date_str}
🏦 {gateway}
🆔 {code}
---"""
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"Error in lsgd_nap_callback: {e}")
        send_telegram_message(chat_id, "❌ Lỗi khi lấy lịch sử nạp tiền")

def handle_lsgd_shop_callback(chat_id, telegram_id):
    """Handle transaction history - shop callback"""
    try:
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối database")
            return
        
        # Get user's Google account purchases
        purchases = supabase.table('google_accounts').select('type, status, sold_at, price_at_sale, email').eq('buyer_telegram_id', telegram_id).order('sold_at', desc=True).limit(10).execute()
        
        if not purchases.data:
            message = """🛒 LỊCH SỬ MUA HÀNG /SHOP

💳 Bạn chưa mua sản phẩm nào.

Hiện tại bạn có thể:
• Sử dụng /shop để xem sản phẩm
• Mua VIP: /mua vip7, /mua vip30
• Mua Google accounts: /mua trial, /mua verified"""
            send_telegram_message(chat_id, message)
            return
        
        # Calculate totals
        total_orders = len(purchases.data)
        total_amount = sum(purchase.get('price_at_sale', 0) for purchase in purchases.data)
        
        message = f"""🛒 LỊCH SỬ MUA HÀNG

📊 Tổng số đơn hàng: {total_orders}
💰 Tổng số tiền: {total_amount:,.0f} CASH

"""
        
        for i, purchase in enumerate(purchases.data, 1):
            account_type = purchase.get('type', 'N/A')
            status = purchase.get('status', 'unknown')
            sold_at = purchase.get('sold_at', 'N/A')
            price = purchase.get('price_at_sale', 0)
            email = purchase.get('email', 'N/A')
            
            # Format date from sold_at to MM-DD-YYYY HH:MM
            try:
                from datetime import datetime, timezone, timedelta
                if sold_at and sold_at != 'N/A':
                    sold_date_utc = datetime.fromisoformat(sold_at.replace('Z', '+00:00'))
                    vietnam_tz = timezone(timedelta(hours=7))
                    sold_date_vietnam = sold_date_utc.astimezone(vietnam_tz)
                    date_str = sold_date_vietnam.strftime('%m-%d-%Y %H:%M')
                else:
                    date_str = 'N/A'
            except:
                date_str = str(sold_at)[:16] if sold_at and sold_at != 'N/A' else 'N/A'
            
            # No status emoji needed
            
            # Product name with emoji
            product_names = {
                'trial': '🌱 Google có tỷ lệ Trial',
                'verified': '✅ Google Verified',
                'canva': '🎨 Canva Admin Edu',
                'ultra': '🤖 Google AI ULTRA 25k Credits',
                'chatgpt': '💬 ChatGPT Plus 3 Months',
                'surfshark': '🦈 Surfshark VPN Premium 2 Month CODE',

                'vip7': '⭐️ VIP 7 ngày',
                'vip30': '⭐️ VIP 30 ngày'
            }
            
            product_name = product_names.get(account_type, account_type)
            
            message += f"""
{i}. {product_name}
📅 {date_str}
💰 {price:,.0f} CASH
📧 {email}
---"""
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"Error in lsgd_shop_callback: {e}")
        send_telegram_message(chat_id, "❌ Lỗi khi lấy lịch sử mua hàng")

def show_payment_info(chat_id, user):
    """Show payment information with QR code"""
    try:
        # MB Bank configuration
        # Handle user data format (dictionary from SQLite)
        if isinstance(user, dict):
            user_id = user.get('id', 1)
            telegram_id = user.get('telegram_id', '1')
            coins = user.get('coins', 0)
        else:
            # Fallback for tuple format (old code)
            user_id = user[0]
            telegram_id = user[1]  # telegram_id is the second element
            coins = user[5]
        
        bank_id = "970422"  # MB Bank
        account_number = "188299299"
        account_name = "PHAN QUOC DANG QUANG"
        description = f"DQ{telegram_id}"  # DQ + Telegram ID
        
        # Send payment info message
        message = f"""💰 Nạp CASH vào tài khoản

💎 Tỷ giá: 1 cash = 1,000 VNĐ
📊 CASH sẽ được cộng tự động sau khi chuyển khoản

🏦 Ngân hàng: MB Bank
💳 STK: `{account_number}`
📝 Nội dung: `{description}`

💡 Lưu ý:
• Tối thiểu: 5.000 VNĐ (5 xu)
• Tối đa: 1.000.000 VNĐ (1,000 xu)
• Xu sẽ được cộng tự động sau khi chuyển khoản

❓ Hỗ trợ: @meepzizhere"""
        
        # Send message
        send_telegram_message(chat_id, message)
        
        # Send QR code image
        send_qr_image(chat_id, "https://dqsheerid.vercel.app/QR_Code.png", f"Nạp cash - {description}")
        
    except Exception as e:
        print(f"Error showing payment info: {e}")
        send_telegram_message(chat_id, "❌ Lỗi hiển thị thông tin thanh toán. Vui lòng thử lại")

def create_and_send_qr(chat_id, user, coins):
    """Create QR code using SePay API and send to user"""
    try:
        # Handle user data format (dictionary from SQLite)
        if isinstance(user, dict):
            user_id = user.get('id', 1)
            telegram_id = user.get('telegram_id', '1')
            username = user.get('username', 'user')
            first_name = user.get('first_name', 'User')
            last_name = user.get('last_name', '')
            user_coins = user.get('coins', 0)
            is_vip = user.get('is_vip', False)
            vip_expiry = user.get('vip_expiry')
            created_at = user.get('created_at', '2025-09-21T00:00:00')
        else:
            # Fallback for tuple format (old code)
            user_id = user[0]
            telegram_id = user[1]  # telegram_id is the second element
            username = user[2]
            first_name = user[3]
            last_name = user[4]
            user_coins = user[5]
            is_vip = user[6]
            vip_expiry = user[7]
            created_at = user[8]
        
        print(f"Creating QR for user {user_id}, coins: {coins}")
        
        amount = coins * 1000  # 1 xu = 1000 VNĐ
        print(f"Calculated amount: {amount} VNĐ")
        
        # Generate transaction ID
        import uuid
        transaction_id = f"TXN_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        print(f"Generated transaction ID: {transaction_id}")
        
        # MB Bank Virtual Account configuration
        bank_id = "970422"  # MB Bank (corrected ID)
        account_number = "VQRQAHGFY9482"  # Virtual Account (VA)
        account_name = "PHAN QUOC DANG QUANG"
        
        # Virtual Account - transaction code for identification
        description = f"DQ{telegram_id}"  # DQ + Telegram ID
        
        print(f"Bank config - ID: {bank_id}, Account: {account_number}, Description: {description}")
        
        # Create QR code using SePay API
        qr_data = create_sepay_qr(account_number, amount, description, bank_id)
        
        print(f"QR data result: {qr_data}")
        
        if not qr_data:
            print("QR data is None, sending error message")
            send_telegram_message(chat_id, "❌ Lỗi tạo QR code. Vui lòng thử lại")
            return
        
        # Store pending payment
        import json
        import os
        from datetime import datetime, timedelta
        
        payment_data = {
            'transaction_id': transaction_id,
            'telegram_id': telegram_id,
            'coins': coins,
            'amount': amount,
            'qr_content': qr_data.get('qrCode', ''),
            'qr_data_url': qr_data.get('qrDataURL', ''),
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(minutes=15)).isoformat()
        }
        
        # Save payment data
        os.makedirs('/tmp/pending_payments', exist_ok=True)
        payment_file = f'/tmp/pending_payments/{transaction_id}.json'
        with open(payment_file, 'w') as f:
            json.dump(payment_data, f)
        
        # Send QR code message
        message = f"""💰 Nạp CASH qua QR

🆔 User ID: `{telegram_id}`
🏦 BANK: MB Bank
💳 STK VA: `{account_number}`
📝 Nội dung: `{description}`
� Số tiền: {amount:,} VNĐ = {coins} cash
�💎 Tỷ giá: 1 cash = 1,000 VNĐ
⏰ Thời gian: CASH sẽ được cộng tự động trong vài phút

❓ Hướng dẫn: /help
❓ Hỗ trợ: @meepzizhere
"""
        
        # Send message with QR code
        send_telegram_message(chat_id, message)
        
        # Send dynamic QR code image
        qr_image_url = qr_data.get('qrDataURL', '')
        if qr_image_url:
            send_qr_image(chat_id, qr_image_url, f"Nạp {coins} xu - {amount:,} VNĐ")
        else:
            # Fallback to static QR if dynamic fails
            send_qr_image(chat_id, "https://dqsheerid.vercel.app/QR_Code.png", f"Nạp {coins} xu - {amount:,} VNĐ")
        
    except Exception as e:
        print(f"Error creating QR: {e}")
        send_telegram_message(chat_id, "❌ Lỗi tạo QR code. Vui lòng thử lại")

def create_sepay_qr(account_number, amount, description, bank_id="970422"):
    """Create QR code using SePay API"""
    try:
        print(f"Creating SePay QR code - Account: {account_number}, Amount: {amount}, Description: {description}, Bank: {bank_id}")
        
        # SePay API configuration
        sepay_token = os.getenv('SEPAY_TOKEN')
        if not sepay_token:
            print("❌ SEPAY_TOKEN not found, using VietQR fallback")
            # Fallback to VietQR if SePay token not configured
            qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_number}-compact2.jpg?amount={amount}&addInfo={description}"
            qr_data_string = f"{bank_id}|{account_number}|PHAN QUOC DANG QUANG|{amount}|{description}"
            
            return {
                'qrCode': qr_data_string,
                'qrDataURL': qr_url,
                'amount': amount,
                'description': description,
                'account_number': account_number,
                'account_name': 'PHAN QUOC DANG QUANG'
            }
        
        # SePay API request
        sepay_url = "https://api.sepay.vn/v1/payment"
        headers = {
            'Authorization': f'Bearer {sepay_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'account_number': account_number,
            'amount': amount,
            'description': description,
            'bank_id': bank_id,
            'webhook_url': 'https://dqsheerid.vercel.app/payment-webhook'
        }
        
        print(f"SePay API request: {data}")
        
        # Try SePay API with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"🔄 SePay API attempt {attempt + 1}/{max_retries}")
                response = requests.post(sepay_url, json=data, headers=headers, timeout=30)
                print(f"SePay API response: {response.status_code} - {response.text}")
                break
            except Exception as e:
                print(f"❌ SePay API attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2)  # Wait 2 seconds before retry
        
        if response.status_code == 200:
            result = response.json()
            print(f"SePay QR creation successful: {result}")
            return result
        else:
            print(f"❌ SePay API error: {response.status_code} - {response.text}")
            # Fallback to VietQR
            qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_number}-compact2.jpg?amount={amount}&addInfo={description}"
            qr_data_string = f"{bank_id}|{account_number}|PHAN QUOC DANG QUANG|{amount}|{description}"
            
            return {
                'qrCode': qr_data_string,
                'qrDataURL': qr_url,
                'amount': amount,
                'description': description,
                'account_number': account_number,
                'account_name': 'PHAN QUOC DANG QUANG'
            }
            
    except Exception as e:
        print(f"Error creating SePay QR code: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback to VietQR
        try:
            qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_number}-compact2.jpg?amount={amount}&addInfo={description}"
            qr_data_string = f"{bank_id}|{account_number}|PHAN QUOC DANG QUANG|{amount}|{description}"
            
            return {
                'qrCode': qr_data_string,
                'qrDataURL': qr_url,
                'amount': amount,
                'description': description,
                'account_number': account_number,
                'account_name': 'PHAN QUOC DANG QUANG'
            }
        except Exception as fallback_error:
            print(f"Fallback error: {fallback_error}")
            return None

def create_vietqr_code(account_number, amount, description, bank_id="970416"):
    """Create QR code using VietQR API"""
    try:
        # VietQR API configuration
        # Thay đổi thông tin này bằng thông tin thật từ VietQR
        access_key = os.environ.get('VIETQR_ACCESS_KEY', 'your_access_key_here')
        secret_key = os.environ.get('VIETQR_SECRET_KEY', 'your_secret_key_here')
        basic_auth = os.environ.get('VIETQR_BASIC_AUTH', 'your_basic_auth_here')
        
        if access_key == 'your_access_key_here':
            # Fallback to simple QR generation
            qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_number}-compact2.jpg?amount={amount}&addInfo={description}"
            return {
                'qrCode': f"{bank_id}|{account_number}|PHAN QUOC DANG QUANG|{amount}|{description}",
                'qrDataURL': qr_url
            }
        
        # Get token first
        token = get_vietqr_token(access_key, secret_key, basic_auth)
        if not token:
            return None
        
        # Generate QR code
        url = "https://api.vietqr.io/v2/generate"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        data = {
            'accountNo': account_number,
            'accountName': 'PHAN QUOC DANG QUANG',
            'acqId': bank_id,
            'amount': amount,
            'addInfo': description,
            'format': 'text',
            'template': 'compact2'
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('data', {})
        else:
            print(f"VietQR API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error creating VietQR code: {e}")
        return None

def get_vietqr_token(access_key, secret_key, basic_auth):
    """Get token from VietQR API"""
    try:
        url = "https://api.vietqr.io/v2/auth/access-token"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {basic_auth}'
        }
        
        data = {
            'accessKey': access_key,
            'secretKey': secret_key
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('data', {}).get('accessToken')
        else:
            print(f"VietQR token error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error getting VietQR token: {e}")
        return None

def send_qr_image(chat_id, qr_url, caption):
    """Send QR code image to Telegram"""
    try:
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8009967142:AAGrp_uH5642XWgIGJwWz4xLcKgG6-_lAcc')
        if not bot_token:
            print(f"Would send QR image to {chat_id}: {qr_url}")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        data = {
            'chat_id': chat_id,
            'photo': qr_url,
            'caption': caption
        }
        
        response = requests.post(url, data=data, timeout=30)
        print(f"QR image sent: {response.status_code} - {response.text}")
        return response.status_code == 200
        
    except Exception as e:
        print(f"Failed to send QR image: {e}")
        return False

def handle_language_command(chat_id, user, text):
    """Handle language selection command"""
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    
    # Get telegram_id from user
    if isinstance(user, dict):
        telegram_id = user.get('telegram_id')
    else:
        telegram_id = user[1]
    
    # Get supabase client
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
    except:
        supabase = None
    
    # Parse command
    parts = text.strip().split()
    
    if len(parts) == 1:  # Just /lang - show language selection
        current_lang = get_user_language(supabase, telegram_id)
        message = get_text('select_language', current_lang)
        
        # Create inline keyboard for language selection
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🇻🇳 Tiếng Việt", "callback_data": "lang_vi"},
                    {"text": "🇺🇸 English", "callback_data": "lang_en"}
                ],
                [
                    {"text": "🇨🇳 中文", "callback_data": "lang_zh"}
                ]
            ]
        }
        
        send_telegram_message_with_keyboard(chat_id, message, keyboard)
        
    elif len(parts) == 2:  # /lang <code>
        lang_code = parts[1].lower()
        
        if lang_code in LANGUAGES:
            # Update user language
            if set_user_language(supabase, telegram_id, lang_code):
                message = get_text('language_changed', lang_code)
                send_telegram_message(chat_id, message)
            else:
                send_telegram_message(chat_id, "❌ Error updating language / Lỗi cập nhật ngôn ngữ")
        else:
            available_langs = ", ".join(LANGUAGES.keys())
            send_telegram_message(chat_id, f"❌ Invalid language. Available: {available_langs}\n❌ Ngôn ngữ không hợp lệ. Có sẵn: {available_langs}")
    else:
        send_telegram_message(chat_id, "Usage: /lang or /lang <vi|en|zh>\nCách dùng: /lang hoặc /lang <vi|en|zh>")

def send_language_selection_for_new_user(chat_id, referral_code=None):
    """Send language selection screen for new users before welcome message"""
    message = """🌍 **Chào mừng! / Welcome! / 欢迎!**

Vui lòng chọn ngôn ngữ của bạn:
Please select your language:
请选择您的语言："""
    
    # Create inline keyboard for language selection with newuser prefix
    # Include referral code in callback if exists
    ref_suffix = f"_{referral_code}" if referral_code else ""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🇻🇳 Tiếng Việt", "callback_data": f"newuser_lang_vi{ref_suffix}"},
                {"text": "🇺🇸 English", "callback_data": f"newuser_lang_en{ref_suffix}"}
            ],
            [
                {"text": "🇨🇳 中文", "callback_data": f"newuser_lang_zh{ref_suffix}"}
            ]
        ]
    }
    
    send_telegram_message_with_keyboard(chat_id, message, keyboard)

def handle_checkin_command(chat_id, user):
    """Handle daily checkin command"""
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    
    # Handle user data format (dictionary from SQLite)
    if isinstance(user, dict):
        user_id = user.get('id', 1)
        username = user.get('username', 'user')
        first_name = user.get('first_name', 'User')
        last_name = user.get('last_name', '')
        coins = user.get('coins', 0)
        is_vip = user.get('is_vip', False)
        vip_expiry = user.get('vip_expiry')
        created_at = user.get('created_at', '2025-09-21T00:00:00')
    else:
        # Fallback for tuple format (old code)
        user_id = user[0]
        username = user[1]
        first_name = user[2]
        last_name = user[3]
        coins = user[4]
        is_vip = user[5]
        vip_expiry = user[6]
        created_at = user[7]
    
    # --- Streak data helpers ---
    def get_streak_row_sb(supabase, user_id):
        try:
            r = supabase.table('user_streaks').select('user_id, current_streak, best_streak, last_checkin_date').eq('user_id', user_id).limit(1).execute()
            return r.data[0] if r.data else None
        except Exception:
            return None

    def upsert_streak_sb(supabase, user_id, current_streak, best_streak, last_date):
        try:
            payload = {
                'user_id': user_id,
                'current_streak': current_streak,
                'best_streak': best_streak,
                'last_checkin_date': last_date
            }
            # try update first
            u = supabase.table('user_streaks').update(payload).eq('user_id', user_id).execute()
            if not u.data:
                supabase.table('user_streaks').insert(payload).execute()
        except Exception:
            pass

    # Check if already checked-in today (Supabase first, fallback SQLite)
    today = format_vietnam_time('%Y-%m-%d')
    already_checked = False
    
    print(f"DEBUG: Checking checkin for user {user_id} on date {today}")
    
    if SUPABASE_AVAILABLE:
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                # Convert Vietnam time to UTC for Supabase query
                from datetime import datetime, timezone, timedelta
                vietnam_tz = timezone(timedelta(hours=7))
                
                # Start of day in Vietnam time, convert to UTC
                start_vietnam = datetime.strptime(f"{today} 00:00:00", '%Y-%m-%d %H:%M:%S')
                start_vietnam = start_vietnam.replace(tzinfo=vietnam_tz)
                start_utc = start_vietnam.astimezone(timezone.utc)
                
                # End of day in Vietnam time, convert to UTC  
                end_vietnam = datetime.strptime(f"{today} 23:59:59", '%Y-%m-%d %H:%M:%S')
                end_vietnam = end_vietnam.replace(tzinfo=vietnam_tz)
                end_utc = end_vietnam.astimezone(timezone.utc)
                
                start_utc_str = start_utc.strftime('%Y-%m-%d %H:%M:%S')
                end_utc_str = end_utc.strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"DEBUG: Querying checkin between {start_utc_str} and {end_utc_str} UTC")
                
                q = (
                    supabase
                    .table('transactions')
                    .select('id', count='exact')
                    .eq('user_id', user_id)
                    .eq('type', 'checkin')
                    .gte('created_at', start_utc_str)
                    .lte('created_at', end_utc_str)
                    .execute()
                )
                already_checked = (q.count or 0) > 0
                print(f"DEBUG: Found {q.count or 0} checkin transactions today, already_checked: {already_checked}")
                
                # load streak row for later
                streak_row = get_streak_row_sb(supabase, user_id)
        except Exception as e:
            print(f"DEBUG: Error checking Supabase checkin: {e}")
            already_checked = False
            
    if not already_checked:
        # Fallback to local SQLite log if Supabase not available
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM transactions 
                WHERE user_id = ? AND type = 'checkin' AND DATE(created_at) = ?
            ''', (user_id, today))
            count = cursor.fetchone()[0]
            already_checked = count > 0
            conn.close()
            print(f"DEBUG: SQLite fallback - found {count} checkin transactions today")
        except Exception as e:
            print(f"DEBUG: Error checking SQLite checkin: {e}")
            already_checked = False
    
    # Calculate streak progression (before checking already_checked)
    current_streak = 0
    best_streak = 0
    from datetime import date, timedelta
    if SUPABASE_AVAILABLE:
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                streak_row = get_streak_row_sb(supabase, user_id)
                if streak_row:
                    last_date_str = streak_row.get('last_checkin_date')
                    current_streak = int(streak_row.get('current_streak') or 0)
                    best_streak = int(streak_row.get('best_streak') or 0)
                    try:
                        last_date = date.fromisoformat(str(last_date_str)[:10]) if last_date_str else None
                    except Exception:
                        last_date = None
                    today_date = date.today()
                    if last_date == today_date:
                        # Already checked in today, keep current streak
                        pass
                    elif last_date == today_date - timedelta(days=1):
                        # Consecutive day, increment streak
                        current_streak += 1
                    else:
                        # Gap of more than 1 day, reset streak
                        current_streak = 1
                    best_streak = max(best_streak, current_streak)
                    # persist
                    upsert_streak_sb(supabase, user_id, current_streak, best_streak, today)
                else:
                    current_streak = 1
                    best_streak = 1
                    upsert_streak_sb(supabase, user_id, current_streak, best_streak, today)
        except Exception:
            current_streak = 1
            best_streak = max(best_streak, current_streak)
    else:
        current_streak = 1
        best_streak = max(best_streak, current_streak)

    if already_checked:
        print(f"DEBUG: User {user_id} already checked in today, blocking duplicate checkin")
        # Get user language
        telegram_id = user.get('telegram_id') if isinstance(user, dict) else user[1] if len(user) > 1 else None
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            user_lang = get_user_language(supabase, telegram_id)
        except:
            user_lang = DEFAULT_LANGUAGE
        
        # Show current streak even if already checked in today
        vip_active = is_vip_active(user)
        
        # Multilingual messages
        if user_lang == 'en':
            status_text = "👑 VIP" if vip_active else "👤 Regular"
            message = f"""
❌ You have already checked in today!

{status_text}
🔥 Current streak: {current_streak}
🏆 Best streak: {best_streak}

💡 Come back tomorrow to continue your streak!
🎁 Daily bonus: 1 coin/day
            """
        elif user_lang == 'zh':
            status_text = "👑 VIP" if vip_active else "👤 普通"
            message = f"""
❌ 您今天已经签到过了！

{status_text}
🔥 当前连续签到: {current_streak}
🏆 最高记录: {best_streak}

💡 明天再来继续您的连续签到！
🎁 每日奖励: 1 金币/天
            """
        else:  # Vietnamese default
            status_text = "👑 VIP" if vip_active else "👤 Thường"
            message = f"""
❌ Bạn đã checkin hôm nay rồi!

{status_text}
🔥 Streak hiện tại: {current_streak}
🏆 Kỷ lục: {best_streak}

💡 Hãy quay lại vào ngày mai để tiếp tục streak!
🎁 Bonus hàng ngày: 1 xu/ngày
            """
        send_telegram_message(chat_id, message)
        return

    # Bonus with streak milestones - All users get 1 xu
    vip_active = is_vip_active(user)
    checkin_bonus = 1  # All users get 1 xu
    
    milestone_bonus = 0
    if current_streak in (7, 14, 30):
        milestone_bonus = {7: 5, 14: 10, 30: 20}[current_streak]
    total_bonus = checkin_bonus + milestone_bonus

    print(f"DEBUG: Processing checkin for user {user_id} - bonus: {total_bonus} xu")
    
    # Add checkin bonus to bonus wallet (Supabase). Fallback: legacy coins.
    applied = False
    try:
        wallets = supabase_adjust_wallet_by_user_id(user_id, bonus_delta=total_bonus)
        applied = wallets is not None
        print(f"DEBUG: Supabase wallet adjustment result: {applied}")
    except Exception as e:
        print(f"DEBUG: Supabase wallet adjustment error: {e}")
        applied = False
        
    if not applied:
        # fallback to old coins column
        print(f"DEBUG: Using SQLite fallback for checkin bonus")
        update_user_coins(user_id, total_bonus, 'checkin', f'Checkin ngày {today}')
    else:
        # Log transaction in Supabase to prevent multiple check-ins the same day
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                tx_result = supabase.table('transactions').insert({
                    'user_id': user_id,
                    'type': 'checkin',
                    'amount': total_bonus,
                    'description': f'Checkin ngày {today} (streak {current_streak})'
                }).execute()
                print(f"DEBUG: Checkin transaction logged successfully: {tx_result.data}")
        except Exception as e:
            print(f"DEBUG: Error logging checkin transaction: {e}")
    
    total_xu = None
    try:
        if applied and wallets:
            total_xu = int(wallets[1])
        else:
            total_xu = int(coins) + total_bonus
    except Exception:
        total_xu = int(coins) + total_bonus

    # Get user language for success message
    telegram_id = user.get('telegram_id') if isinstance(user, dict) else user[1] if len(user) > 1 else None
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        user_lang = get_user_language(supabase, telegram_id)
    except:
        user_lang = DEFAULT_LANGUAGE
    
    # Create status text based on language
    if user_lang == 'en':
        status_text = "👑 VIP" if vip_active else "👤 Regular"
        daily_info = f"{checkin_bonus} coin/day"
        bonus_text = f"{total_bonus} ({checkin_bonus} base{f' + {milestone_bonus} milestone' if milestone_bonus else ''})"
        message = f"""
🎉 Check-in successful!

{status_text}
🔥 Current streak: {current_streak}
🏆 Best streak: {best_streak}
🪙 Coins received: {bonus_text}
💰 Total coins: {total_xu}

🎯 Milestones: 7 (+5), 14 (+10), 30 (+20) consecutive days
💡 Check in daily to earn {daily_info} and build your streak!
❓ Support: @meepzizhere
        """
    elif user_lang == 'zh':
        status_text = "👑 VIP" if vip_active else "👤 普通"
        daily_info = f"{checkin_bonus} 金币/天"
        bonus_text = f"{total_bonus} ({checkin_bonus} 基础{f' + {milestone_bonus} 里程碑' if milestone_bonus else ''})"
        message = f"""
🎉 签到成功！

{status_text}
🔥 当前连续签到: {current_streak}
🏆 最高记录: {best_streak}
🪙 获得金币: {bonus_text}
💰 总金币: {total_xu}

🎯 里程碑奖励: 7 (+5), 14 (+10), 30 (+20) 连续天数
💡 每天签到获得 {daily_info} 并累积连续签到！
❓ 支持: @meepzizhere
        """
    else:  # Vietnamese default
        status_text = "👑 VIP" if vip_active else "👤 Thường"
        daily_info = f"{checkin_bonus} xu/ngày"
        bonus_text = f"{total_bonus} ({checkin_bonus} cơ bản{f' + {milestone_bonus} mốc' if milestone_bonus else ''})"
        message = f"""
🎉 Checkin thành công!

{status_text}
🔥 Streak hiện tại: {current_streak}
🏆 Kỷ lục: {best_streak}
🪙 Xu nhận được: {bonus_text}
💰 Tổng xu: {total_xu}

🎯 Mốc thưởng: 7 (+5), 14 (+10), 30 (+20) ngày liên tiếp
💡 Hãy checkin mỗi ngày để nhận {daily_info} và tích lũy streak!
❓ Hỗ trợ: @meepzizhere
        """
    
    send_telegram_message(chat_id, message)

def handle_checkchannel_command(chat_id, user):
    """Handle /checkchannel or /join command - Reward for joining channel (with 24h waiting period)"""
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    
    try:
        from .channel_reward import record_channel_join, claim_channel_reward, get_channel_reward_info, REWARD_CHANNEL_ID, WAITING_PERIOD_HOURS
        from datetime import datetime, timedelta
        
        # Get user data
        if isinstance(user, dict):
            user_id = user.get('id')
            telegram_id = user.get('telegram_id')
        else:
            user_id = user[0]
            telegram_id = user[1]
        
        # Get user language from Supabase
        user_lang = 'vi'
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                user_lang = get_user_language(supabase, telegram_id)
                print(f"🌍 User {telegram_id} language: {user_lang}")
        except Exception as e:
            print(f"⚠️ Error getting language: {e}")
        
        # Get bot token
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            send_telegram_message(chat_id, "❌ Bot configuration error")
            return
        
        # Get localized messages
        messages = get_channel_reward_info(user_lang)
        
        # First, try to record channel join (this checks membership and records time)
        join_success, join_msg = record_channel_join(user_id, telegram_id, bot_token)
        
        if join_msg == "already_claimed":
            send_telegram_message(chat_id, messages['already_claimed'])
            return
        elif join_msg == "not_member":
            # Show message with button to join channel
            message = messages['not_member']
            
            # Create inline keyboard with join button
            channel_url = f"https://t.me/{REWARD_CHANNEL_ID.replace('@', '')}"
            keyboard = {
                'inline_keyboard': [[
                    {'text': '📢 Tham gia kênh' if user_lang == 'vi' else ('📢 Join Channel' if user_lang == 'en' else '📢 加入频道'), 
                     'url': channel_url}
                ]]
            }
            
            send_telegram_message_with_keyboard(chat_id, message, keyboard)
            return
        elif join_msg == "join_recorded":
            # Just recorded join time - show random waiting message
            import random
            claim_time = (datetime.utcnow() + timedelta(hours=WAITING_PERIOD_HOURS)).strftime('%Y-%m-%d %H:%M UTC')
            messages_list = messages['join_recorded']
            message = random.choice(messages_list).format(claim_time=claim_time)
            send_telegram_message(chat_id, message)
            return
        elif join_msg.startswith("waiting|"):
            # Still waiting - show random remaining time message
            import random
            hours_remaining = float(join_msg.split('|')[1])
            claim_time = (datetime.utcnow() + timedelta(hours=hours_remaining)).strftime('%Y-%m-%d %H:%M UTC')
            messages_list = messages['waiting']
            message = random.choice(messages_list).format(hours=f"{hours_remaining:.1f}", claim_time=claim_time)
            send_telegram_message(chat_id, message)
            return
        elif join_msg == "can_claim":
            # 24 hours passed, show fun random message then try to claim
            import random
            messages_list = messages['can_claim']
            fun_message = random.choice(messages_list)
            send_telegram_message(chat_id, fun_message)
            
            # Now try to claim
            success, result_msg, new_balance = claim_channel_reward(user_id, telegram_id, bot_token)
            
            if success:
                # Success - show reward message with new balance
                message = messages['success'].format(new_cash=new_balance)
                send_telegram_message(chat_id, message)
            elif result_msg.startswith("waiting|"):
                # Still need to wait (edge case)
                hours_remaining = float(result_msg.split('|')[1])
                claim_time = (datetime.utcnow() + timedelta(hours=hours_remaining)).strftime('%Y-%m-%d %H:%M UTC')
                message = messages['waiting'].format(hours=f"{hours_remaining:.1f}", claim_time=claim_time)
                send_telegram_message(chat_id, message)
            else:
                # Generic error
                send_telegram_message(chat_id, messages['error'])
        else:
            # Generic error
            send_telegram_message(chat_id, messages['error'])
        
    except Exception as e:
        print(f"❌ Error in handle_checkchannel_command: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_quests_command(chat_id, user):
    """Show quests status and allow claiming rewards"""
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    user_id = user.get('id') if isinstance(user, dict) else user[0]
    today = format_vietnam_time('%Y-%m-%d')
    from datetime import timedelta
    vietnam_now = get_vietnam_time(); start_week = (vietnam_now - timedelta(days=vietnam_now.weekday())).strftime('%Y-%m-%d')
    lines = ["🎯 NHIỆM VỤ"]
    try:
        verified_today = 0
        bought_week = 0
        if SUPABASE_AVAILABLE:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                v = (
                    supabase.table('transactions')
                    .select('id', count='exact')
                    .eq('user_id', user_id)
                    .eq('type', 'verify')
                    .gte('created_at', f"{today} 00:00:00")
                    .execute()
                )
                verified_today = int(v.count or 0)
                p = (
                    supabase.table('transactions')
                    .select('id', count='exact')
                    .eq('user_id', user_id)
                    .eq('type', 'purchase')
                    .gte('created_at', f"{start_week} 00:00:00")
                    .execute()
                )
                bought_week = int(p.count or 0)
                # Claimed flags
                claimed_daily = False
                claimed_weekly = False
                try:
                    qd = supabase.table('user_quests').select('code,last_claim_date').eq('user_id', user_id).eq('code','daily_verify').limit(1).execute()
                    if qd.data:
                        claimed_daily = (str(qd.data[0].get('last_claim_date') or '')[:10] == today)
                except Exception:
                    pass
                try:
                    qw = supabase.table('user_quests').select('code,last_claim_week').eq('user_id', user_id).eq('code','weekly_buy').limit(1).execute()
                    if qw.data:
                        claimed_weekly = (str(qw.data[0].get('last_claim_week') or '') == start_week)
                except Exception:
                    pass
                progress_daily = min(1, verified_today)
                can_claim_daily = (progress_daily >= 1) and not claimed_daily
                lines.append(f"\n• Daily: Verify 1 lần — Tiến độ: {progress_daily}/1 — Thưởng: +2 Xu" + (" — /claim daily" if can_claim_daily else (" — Đã nhận" if claimed_daily else "")))
                progress_weekly = min(1, bought_week)
                can_claim_weekly = (progress_weekly >= 1) and not claimed_weekly
                lines.append(f"• Weekly: Mua 1 sản phẩm — Tiến độ: {progress_weekly}/1 — Thưởng: +3 Xu" + (" — /claim weekly" if can_claim_weekly else (" — Đã nhận" if claimed_weekly else "")))
            else:
                lines.append("❌ Không thể kết nối Supabase để đọc nhiệm vụ!")
        else:
            lines.append("❌ Supabase không khả dụng! Tính năng quest cần DB.")
    except Exception as e:
        lines.append(f"❌ Lỗi đọc nhiệm vụ: {str(e)}")
    send_telegram_message(chat_id, "\n".join(lines))

def handle_claim_command(chat_id, user, text):
    """Claim quest rewards with idempotency"""
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    user_id = user.get('id') if isinstance(user, dict) else user[0]
    parts = text.split()
    if len(parts) < 2:
        send_telegram_message(chat_id, "❌ Cú pháp: /claim daily|weekly")
        return
    kind = parts[1].lower()
    today = format_vietnam_time('%Y-%m-%d')
    from datetime import timedelta
    vietnam_now = get_vietnam_time(); start_week = (vietnam_now - timedelta(days=vietnam_now.weekday())).strftime('%Y-%m-%d')
    if not SUPABASE_AVAILABLE:
        send_telegram_message(chat_id, "❌ Supabase không khả dụng!")
        return
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase!")
            return
        if kind == 'daily':
            v = supabase.table('transactions').select('id', count='exact').eq('user_id', user_id).eq('type','verify').gte('created_at', f"{today} 00:00:00").execute()
            if (v.count or 0) < 1:
                send_telegram_message(chat_id, "❌ Chưa hoàn thành Daily: Verify 1 lần hôm nay")
                return
            qd = supabase.table('user_quests').select('last_claim_date').eq('user_id', user_id).eq('code','daily_verify').limit(1).execute()
            if qd.data and str(qd.data[0].get('last_claim_date') or '')[:10] == today:
                send_telegram_message(chat_id, "✅ Bạn đã nhận phần thưởng Daily hôm nay rồi!")
                return
            reward = 2
            supabase_adjust_wallet_by_user_id(user_id, bonus_delta=reward)
            supabase.table('transactions').insert({'user_id': user_id, 'type': 'quest', 'amount': reward, 'description': 'Quest Daily Verify'}).execute()
            u = supabase.table('user_quests').update({'code':'daily_verify','last_claim_date': today}).eq('user_id', user_id).execute()
            if not u.data:
                supabase.table('user_quests').insert({'user_id': user_id, 'code': 'daily_verify', 'last_claim_date': today}).execute()
            send_telegram_message(chat_id, f"🎁 Đã nhận +{reward} Xu từ Daily!")
        elif kind == 'weekly':
            p = supabase.table('transactions').select('id', count='exact').eq('user_id', user_id).eq('type','purchase').gte('created_at', f"{start_week} 00:00:00").execute()
            if (p.count or 0) < 1:
                send_telegram_message(chat_id, "❌ Chưa hoàn thành Weekly: Mua 1 sản phẩm tuần này")
                return
            qw = supabase.table('user_quests').select('last_claim_week').eq('user_id', user_id).eq('code','weekly_buy').limit(1).execute()
            if qw.data and str(qw.data[0].get('last_claim_week') or '') == start_week:
                send_telegram_message(chat_id, "✅ Bạn đã nhận phần thưởng Weekly tuần này rồi!")
                return
            reward = 3
            supabase_adjust_wallet_by_user_id(user_id, bonus_delta=reward)
            supabase.table('transactions').insert({'user_id': user_id, 'type': 'quest', 'amount': reward, 'description': 'Quest Weekly Purchase'}).execute()
            u = supabase.table('user_quests').update({'code':'weekly_buy','last_claim_week': start_week}).eq('user_id', user_id).execute()
            if not u.data:
                supabase.table('user_quests').insert({'user_id': user_id, 'code': 'weekly_buy', 'last_claim_week': start_week}).execute()
            send_telegram_message(chat_id, f"🎁 Đã nhận +{reward} Xu từ Weekly!")
        else:
            send_telegram_message(chat_id, "❌ Cú pháp: /claim daily|weekly")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi nhận thưởng: {str(e)}")

def handle_myjobs_command(chat_id, user):
    """Handle myjobs command"""
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    
    # Handle both dict and tuple user formats
    if isinstance(user, dict):
        # Two possible shapes:
        # 1) DB user dict: has 'telegram_id' and 'id' (DB id)
        # 2) Telegram payload dict: 'id' is telegram_id and no 'telegram_id' field
        if 'telegram_id' in user:
            user_id = user.get('id')
            telegram_id = user.get('telegram_id')
        else:
            # Raw Telegram user
            telegram_id = user.get('id')
            user_id = None
    else:
        user_id = user[0]
        telegram_id = user[1]

    # If we don't have DB user_id yet, resolve it from telegram_id
    if not user_id:
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    resp = supabase.table('users').select('id').eq('telegram_id', telegram_id).limit(1).execute()
                    if resp.data:
                        user_id = resp.data[0]['id']
            except Exception as e:
                print(f"❌ Supabase error resolving user_id in /myjobs: {e}")
        
        if not user_id:
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    user_id = row[0]
            except Exception as e:
                print(f"❌ SQLite error resolving user_id in /myjobs: {e}")
    
    if not user_id:
        send_telegram_message(chat_id, "❌ Không tìm thấy user trong hệ thống. Vui lòng /start lại!")
        return
    
    jobs = []
    
    # Try Supabase first - Query BOTH tables
    if SUPABASE_AVAILABLE:
        try:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                # Get jobs from NEW sheerid_bot_jobs table (Gemini, Perplexity, Teacher)
                response_new = supabase.table('sheerid_bot_jobs').select('job_id, verification_type, status, created_at, cost, result_details').eq('user_id', user_id).order('created_at', desc=True).limit(10).execute()
                
                # Get jobs from OLD verification_jobs table (Spotify)
                response_old = supabase.table('verification_jobs').select('job_id, sheerid_url, status, created_at, result, student_info, card_filename').eq('user_id', user_id).order('created_at', desc=True).limit(10).execute()
                
                # Combine and format jobs
                combined_jobs = []
                
                # Add new jobs
                if response_new.data:
                    for job in response_new.data:
                        combined_jobs.append({
                            'job_id': job.get('job_id'),
                            'type': job.get('verification_type', 'gemini'),
                            'status': job.get('status'),
                            'created_at': job.get('created_at'),
                            'cost': job.get('cost', 10),
                            'result_details': job.get('result_details'),
                            'source': 'sheerid_bot'
                        })
                    print(f"📊 Found {len(response_new.data)} jobs in sheerid_bot_jobs for user {telegram_id}")
                
                # Add old jobs
                if response_old.data:
                    for job in response_old.data:
                        combined_jobs.append({
                            'job_id': job.get('job_id'),
                            'type': 'spotify',
                            'status': job.get('status'),
                            'created_at': job.get('created_at'),
                            'url': job.get('sheerid_url'),
                            'result': job.get('result'),
                            'student_info': job.get('student_info'),
                            'card_filename': job.get('card_filename'),
                            'source': 'verification_jobs'
                        })
                    print(f"📊 Found {len(response_old.data)} jobs in verification_jobs for user {telegram_id}")
                
                # Sort by created_at descending
                combined_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                jobs = combined_jobs[:10]  # Limit to 10 most recent
                
                print(f"📊 Total combined jobs: {len(jobs)}")
        except Exception as e:
            print(f"❌ Supabase error in myjobs: {e}")
            import traceback
            traceback.print_exc()
    
    if not jobs:
        send_telegram_message(chat_id, "📝 Bạn chưa có job nào. Sử dụng /verify <URL> để tạo job mới!")
        return
    
    message = "📋 Danh sách job của bạn:\n\n"
    
    for i, job in enumerate(jobs, 1):
        job_id = job.get('job_id')
        status = job.get('status', 'unknown').lower()
        created = job.get('created_at')
        job_type = job.get('type', 'unknown')
        source = job.get('source', 'unknown')
        
        # DEBUG: Log the actual status from database
        print(f"🔍 DEBUG MYJOBS: Job {job_id}")
        print(f"  📊 Status: '{status}'")
        print(f"  📅 Created: {created}")
        print(f"  🔧 Type: {job_type}")
        print(f"  📦 Source: {source}")
        
        # Map status to display
        if status in ('pending', 'processing'):
            status_display = status
            status_emoji = '⏳' if status == 'pending' else '🔄'
        elif status in ('completed', 'success'):
            status_display = 'completed'
            status_emoji = '✅'
        elif status in ('failed', 'error', 'cancelled'):
            status_display = 'failed'
            status_emoji = '❌'
        else:
            status_display = 'unknown'
            status_emoji = '❓'
        
        # Type display names
        type_names = {
            'gemini': 'Gemini',
            'perplexity': 'Perplexity',
            'teacher': 'Teacher',
            'spotify': 'Spotify'
        }
        type_display = type_names.get(job_type, job_type.upper())
        
        message += f"""
{i}. 🎯 {type_display}
🆔 Job ID: `{job_id}`
{status_emoji} Trạng thái: {status_display.upper()}
📅 Tạo: {str(created)[:16]}
"""
        
        # Add cost info
        if status_display == 'completed':
            cost = job.get('cost', 10)
            message += f"💰 Đã trừ: {cost} cash\n"
        elif status_display == 'failed':
            message += "💰 Đã hoàn: +10 cash\n"
        
        message += "---\n"
    
    send_telegram_message(chat_id, message)

def handle_lsgd_command(chat_id, user):
    """Handle lsgd (transaction history) command"""
    print(f"🔍 DEBUG: handle_lsgd_command called with chat_id={chat_id}, user={user}")
    
    if not user:
        print("❌ DEBUG: No user provided")
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    
    print("✅ DEBUG: User check passed")
    
    message = """📊 LỊCH SỬ GIAO DỊCH

Hãy chọn những lựa chọn phía dưới để xem lịch sử giao dịch của bạn!"""
    
    # Create inline keyboard with 2 buttons
    keyboard = [[
        {"text": "💳 Lịch sử nạp", "callback_data": "lsgd_nap"},
        {"text": "🛒 Lịch sử mua hàng /shop", "callback_data": "lsgd_shop"}
    ]]
    
    print(f"🔍 DEBUG: Sending lsgd keyboard: {keyboard}")
    print(f"🔍 DEBUG: Message: {message}")
    
    try:
        result = send_telegram_message_with_keyboard(chat_id, message, keyboard)
        print(f"🔍 DEBUG: Keyboard send result: {result}")
        
        if not result:
            print("⚠️ DEBUG: Keyboard failed, sending fallback message")
            fallback_message = """📊 LỊCH SỬ GIAO DỊCH

Hãy chọn loại lịch sử bạn muốn xem:

1️⃣ Để xem lịch sử nạp tiền, reply: nap
2️⃣ Để xem lịch sử mua hàng, reply: shop

Hoặc sử dụng callback buttons nếu có."""
            send_telegram_message(chat_id, fallback_message)
            
    except Exception as e:
        print(f"❌ DEBUG: Keyboard send error: {e}")
        import traceback
        traceback.print_exc()
        
        # Send fallback message
        fallback_message = """📊 LỊCH SỬ GIAO DỊCH

❌ Không thể hiển thị menu tương tác.

Vui lòng sử dụng:
• Lịch sử nạp: reply "nap"  
• Lịch sử mua hàng: reply "shop"

Hoặc thử lại lệnh /lsgd sau."""
        send_telegram_message(chat_id, fallback_message)

def handle_admin_command(chat_id, user, text):
    """Handle admin commands"""
    try:
        if not user:
            send_telegram_message(chat_id, "❌ Vui lòng /start trước")
            return
        
        # Parse admin command
        parts = text.split()
        print(f"🔍 DEBUG: Admin command received: '{text}', parts: {parts}")
        if len(parts) < 2:
            print(f"🔍 DEBUG: Not enough parts, sending help")
            send_admin_help(chat_id)
            return
        
        command = parts[1].lower()
        print(f"🔍 DEBUG: Admin command parsed: '{command}' from text: '{text}'")
        
        if command == "checkip":
            # /admin checkip - Check current WWProxy IP status
            handle_admin_checkip(chat_id)
        elif command == "rotateip":
            # /admin rotateip - Force rotate IP immediately
            handle_admin_rotateip(chat_id)
        elif command == "help":
            message = """🔧 ADMIN COMMANDS:

🌐 IP Management:
/admin checkip - Xem IP hiện tại và thời gian sống
/admin rotateip - Force đổi IP ngay lập tức

👥 User:
/admin users [trang] - Danh sách user (5/user/trang)
/admin user <telegram_id> - Xem thông tin chi tiết user
/admin purchases <telegram_id> - Xem lịch sử mua hàng của user
/admin lsgd [trang] - Xem lịch sử nạp tiền (5/trang)
/admin activities [trang] - Xem tất cả giao dịch server (5/trang)
/admin add <telegram_id> <username> <first_name> [last_name]
/admin delete <telegram_id>
/admin clear - Xóa tất cả user (cẩn thận)

💰 Ví:
/admin coins <telegram_id> <amount> [lý_do] - Set Xu cho user
/admin cash <telegram_id> <amount> [lý_do] - Cộng/trừ CASH cho user
/admin refund <telegram_id> <amount> - Hoàn Xu cho user
/admin transactions - Xem giao dịch gần đây
👑 VIP:
/admin vip <telegram_id> <số_ngày> - Bật VIP theo ngày (0=tắt)
/admin vipexpiry <telegram_id> <YYYY-MM-DD HH:MM> - Set hạn VIP
/admin vipall <số_ngày> - Set VIP cho toàn bộ user
/admin vipbatch <ids_csv> <số_ngày> - Set VIP cho danh sách user

📊 Jobs:
/admin jobs <telegram_id> - Xem jobs SheerID của user

📢 Broadcast:
/admin noti <nội_dung>
/admin w <telegram_id> <nội_dung> - Nhắn riêng (whisper) đến user
/admin daily-send - Gửi thông báo hằng ngày (thật) cho toàn bộ user
/admin emergency on|off - Bật/Tắt dừng khẩn cấp ngay lập tức
/admin broadcast <message>
/admin broadcastvip <message>
/admin daily - Test thông báo hằng ngày
/admin ban <telegram_id> <lý_do> - Khóa user và gửi thông báo
/admin unban <telegram_id> <ghi_chú> - Mở khóa user và gửi thông báo

🛒 Google Accounts:
/admin setgtrial <giá> - Đặt giá Google Trial (CASH)
/admin setgtrialvip <giá> - Đặt giá VIP Google Trial (CASH)
/admin setgverified <giá> - Đặt giá Google Verified (CASH)
/admin setgverifiedvip <giá> - Đặt giá VIP Google Verified (CASH)
/admin setcanva <giá> - Đặt giá Canva Admin Edu (CASH)
/admin setcanvavip <giá> - Đặt giá VIP Canva Admin Edu (CASH)
/admin setaiultra <giá> - Đặt giá Google AI ULTRA 25k Credits (CASH)
/admin setaiultravip <giá> - Đặt giá VIP Google AI ULTRA (CASH)
/admin setaiultra45 <giá> - Đặt giá Google AI ULTRA 45k Credits (CASH)
/admin setaiultra45v <giá> - Đặt giá VIP Google AI ULTRA 45k Credits (CASH)
/admin setchatgpt <giá> - Đặt giá ChatGPT Plus 3 Months (CASH)
/admin setchatgptvip <giá> - Đặt giá VIP ChatGPT Plus 3 Months (CASH)
/admin setm365 <giá> - Đặt giá Microsoft 365 Personal 1 Năm (CASH)
/admin setm365v <giá> - Đặt giá VIP Microsoft 365 Personal 1 Năm (CASH)
/admin setadobe4m <giá> - Đặt giá ADOBE FULL APP 4 Months (CASH)
/admin setadobe4mv <giá> - Đặt giá VIP ADOBE FULL APP 4 Months (CASH)
/admin addviprices - Thêm tất cả giá VIP vào Supabase
/admin settype <account_id> <trial|verified|canva|chatgpt> - Chuyển loại tài khoản
/admin setvip7 <giá> - Đặt giá VIP 7 ngày (CASH)
/admin setvip30 <giá> - Đặt giá VIP 30 ngày (CASH)
/admin stock - Xem số lượng AVAILABLE
/admin importcsv <url_csv> - Import từ CSV công khai

⚙️ Cấu hình:
/admin config - Xem cấu hình bot
/admin setwelcome <message>
/admin setprice <amount> - Giá verify
/admin setbonus <amount> - Xu checkin/ngày (áp dụng cho /checkin hoặc /diemdanh)
/admin maintenance on/off
/admin shutdown on|off|status|setmsg <message>
/admin verify on|off|status - Bật/Tắt chức năng verify

🛠️ Công cụ migrate:
/admin migratexu - Gộp legacy về Xu (CASH=0)
/admin migratecash - Chuyển toàn bộ CASH → Xu (CASH=0)

❓ Hỗ trợ: @meepzizhere"""
            send_telegram_message(chat_id, message)
        elif command == "users":
            # Parse page number if provided
            page = 1
            if len(parts) >= 3:
                try:
                    page = int(parts[2])
                except ValueError:
                    page = 1
            print(f"🔍 DEBUG: Executing /admin users command for page {page}")
            handle_admin_list_users(chat_id, page)
        elif command == "getid":
            # /admin getid <tên>
            if len(parts) >= 3:
                search_name = ' '.join(parts[2:]).lower()
                handle_admin_get_id(chat_id, search_name)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin getid <tên>\n\nVí dụ: /admin getid tran")
        elif command == "checkvip":
            # /admin checkvip - Kiểm tra và cập nhật VIP hết hạn
            handle_admin_check_vip(chat_id)
        elif command == "clear":
            handle_admin_clear_users(chat_id)
        elif command == "daily":
            print(f"🔍 DEBUG: Executing /admin daily command")
            handle_admin_daily_notification(chat_id)
            print(f"🔍 DEBUG: /admin daily command completed")
        elif command == "daily-send":
            # Trigger actual daily broadcast immediately
            if EMERGENCY_STOP:
                send_telegram_message(chat_id, "🚨 Bot đang ở chế độ dừng khẩn cấp! Không gửi được.")
            else:
                result = send_daily_notification()
                if isinstance(result, dict) and result.get('success'):
                    success_count = result.get('success_count', 0)
                    failed_count = result.get('failed_count', 0)
                    total_count = result.get('total_count', 0)
                    
                    message = f"""✅ **Gửi thông báo hằng ngày hoàn tất!**

📊 **Thống kê gửi tin:**
• 👥 Tổng số user: {total_count:,}
• ✅ Gửi thành công: {success_count:,}
• ❌ Gửi thất bại: {failed_count:,}
• 📈 Tỷ lệ thành công: {(success_count/total_count*100):.1f}% (nếu có user)

⏰ Thời gian: {format_vietnam_time()}
                    """
                    send_telegram_message(chat_id, message)
                else:
                    error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else 'Unknown error'
                    send_telegram_message(chat_id, f"❌ Không thể gửi thông báo hằng ngày!\n\n🔍 Lỗi: {error_msg}\n💡 Kiểm tra logs để biết thêm chi tiết.")
        elif command == "config":
            handle_admin_config(chat_id)
        elif command == "setwelcome":
            if len(parts) >= 3:
                message = ' '.join(parts[2:])
                handle_admin_set_welcome(chat_id, message)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setwelcome <message>")
        elif command == "setprice":
            if len(parts) >= 3:
                handle_admin_set_price(chat_id, parts[2])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setprice <amount>")
        elif command == "setbonus":
            if len(parts) >= 3:
                handle_admin_set_bonus(chat_id, parts[2])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setbonus <amount>")
        elif command == "maintenance":
            print(f"🔍 DEBUG: Maintenance command detected, parts: {parts}")
            if len(parts) >= 3:
                mode = parts[2].lower()
                if mode in ['on', 'off', 'status', 'force']:
                    print(f"🔍 DEBUG: Calling handle_admin_maintenance with mode: {mode}")
                    handle_admin_maintenance(chat_id, mode)
                else:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin maintenance on/off/force/status")
            else:
                print(f"🔍 DEBUG: Not enough parts for maintenance command: {len(parts)}")
                send_telegram_message(chat_id, "❌ Sử dụng: /admin maintenance on/off/force/status")
        elif command == "shutdown":
            # /admin shutdown on|off|status|setmsg <message>
            if len(parts) >= 3:
                subcmd = parts[2].lower()
                print(f"🔍 DEBUG: Admin shutdown command: {subcmd}")
                
                if subcmd == 'on':
                    BOT_CONFIG['bot_closed'] = True
                    os.environ['BOT_CLOSED'] = 'true'
                    try:
                        save_bot_config('bot_closed', True)
                        print("✅ Saved bot_closed=ON to database")
                    except Exception as e:
                        print(f"⚠️ Database save failed: {e}")
                    send_telegram_message(chat_id, "🚫 Đã BẬT chế độ đóng bot. Chỉ admin mới sử dụng được.")
                    
                elif subcmd == 'off':
                    print("🚨 FORCE turning off bot shutdown...")
                    
                    # Clear everything aggressively
                    BOT_CONFIG['bot_closed'] = False
                    os.environ.pop('BOT_CLOSED', None)
                    
                    # Clear any related environment variables
                    shutdown_env_vars = [key for key in os.environ.keys() if 'BOT_CLOSED' in key.upper()]
                    for key in shutdown_env_vars:
                        del os.environ[key]
                        print(f"  Cleared env var: {key}")
                    
                    # Force save to database multiple times
                    for i in range(3):
                        try:
                            save_bot_config('bot_closed', False)
                            print(f"✅ Force save attempt {i+1} successful")
                            break
                        except Exception as e:
                            print(f"❌ Force save attempt {i+1} failed: {e}")
                    
                    # Force reload config to ensure consistency
                    CONFIG_LOADED = False
                    load_bot_config(force_reload=True)
                    
                    # Verify the status is actually off
                    final_status = is_bot_closed()
                    print(f"🔍 DEBUG: Final shutdown status after off command: {final_status}")
                    
                    if final_status:
                        send_telegram_message(chat_id, "⚠️ Đã TẮT chế độ đóng bot nhưng vẫn còn vấn đề. Thử lại sau vài giây.")
                    else:
                        send_telegram_message(chat_id, "✅ Đã TẮT chế độ đóng bot. User có thể sử dụng lại.")
                    
                elif subcmd == 'status':
                    # Force show OFF status since shutdown is disabled
                    status_icon = '✅'
                    status_text = 'TẮT'
                    msg = 'Bot hoạt động bình thường'
                    send_telegram_message(chat_id, f"{status_icon} Trạng thái đóng bot: {status_text}\n📝 Message: {msg}")
                    
                elif subcmd == 'setmsg':
                    # Preserve line breaks: take substring after 'shutdown setmsg'
                    raw = text
                    marker = 'shutdown setmsg'
                    idx = raw.lower().find(marker)
                    msg_text = raw[idx + len(marker):].lstrip() if idx != -1 else ''
                    if msg_text:
                        BOT_CONFIG['bot_closed_message'] = msg_text
                        os.environ['BOT_CLOSED_MESSAGE'] = msg_text
                        try:
                            save_bot_config('bot_closed_message', msg_text)
                            print("✅ Saved bot_closed_message to database")
                        except Exception as e:
                            print(f"⚠️ Database save failed: {e}")
                        send_telegram_message(chat_id, "✅ Đã cập nhật thông báo đóng bot.")
                    else:
                        send_telegram_message(chat_id, "❌ Sử dụng: /admin shutdown setmsg <message>")
                else:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin shutdown on|off|status|setmsg <message>")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin shutdown on|off|status|setmsg <message>")
        elif command == "emergency":
            if len(parts) >= 3:
                handle_admin_emergency(chat_id, parts[2])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin emergency on|off")
        elif command == "verify":
            # /admin verify on|off|status
            if len(parts) >= 3:
                subcmd = parts[2].lower()
                if subcmd == 'on':
                    # Enable verify (turn OFF maintenance)
                    BOT_CONFIG['verify_maintenance'] = False
                    BOT_CONFIG['maintenance_mode'] = False
                    os.environ.pop('VERIFY_MAINTENANCE', None)
                    try:
                        save_bot_config('verify_maintenance', False)
                        save_bot_config('maintenance_mode', False)
                        print("✅ Saved verify=ON to database")
                    except Exception as e:
                        print(f"⚠️ Database save failed: {e}")
                    send_telegram_message(chat_id, "✅ Đã BẬT chức năng verify. User có thể sử dụng /verify.")
                elif subcmd == 'off':
                    # Disable verify (turn ON maintenance)
                    BOT_CONFIG['verify_maintenance'] = True
                    BOT_CONFIG['maintenance_mode'] = True
                    os.environ['VERIFY_MAINTENANCE'] = 'true'
                    try:
                        save_bot_config('verify_maintenance', True)
                        save_bot_config('maintenance_mode', True)
                        print("✅ Saved verify=OFF to database")
                    except Exception as e:
                        print(f"⚠️ Database save failed: {e}")
                    send_telegram_message(chat_id, "🚫 Đã TẮT chức năng verify. User không thể sử dụng /verify.")
                elif subcmd == 'status':
                    env_maintenance = os.environ.get('VERIFY_MAINTENANCE', 'false').lower() == 'true'
                    config_maintenance = bool(BOT_CONFIG.get('verify_maintenance') or BOT_CONFIG.get('maintenance_mode'))
                    any_maintenance = env_maintenance or config_maintenance
                    status_icon = '🚫' if any_maintenance else '✅'
                    status_text = 'TẮT' if any_maintenance else 'BẬT'
                    send_telegram_message(chat_id, f"{status_icon} Trạng thái verify: {status_text}")
                else:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin verify on|off|status")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin verify on|off|status")
        elif command == "broadcast":
            if len(parts) >= 3:
                message = ' '.join(parts[2:])
                handle_admin_broadcast(chat_id, message)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin broadcast <message>")
        elif command == "broadcastvip":
            if len(parts) >= 3:
                message = ' '.join(parts[2:])
                handle_admin_broadcast_vip(chat_id, message)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin broadcastvip <message>")
        elif command == "transactions":
            handle_admin_transactions(chat_id)
        elif command == "fix-country":
            handle_admin_fix_country(chat_id)
        elif command == "refund":
            if len(parts) >= 4:
                handle_admin_refund(chat_id, parts[2], parts[3])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin refund <telegram_id> <amount>")
        elif command == "vipall":
            if len(parts) >= 3:
                try:
                    days = int(parts[2])
                except:
                    days = 0
                handle_admin_set_vip_all(chat_id, days)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin vipall <số_ngày>")
        elif command == "vipbatch":
            if len(parts) >= 4:
                ids_csv = parts[2]
                try:
                    days = int(parts[3])
                except:
                    days = 0
                handle_admin_set_vip_batch(chat_id, ids_csv, days)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin vipbatch <ids_csv> <số_ngày>")
        elif command == "coinsall":
            if len(parts) >= 3:
                handle_admin_set_coins_all(chat_id, parts[2])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin coinsall <amount>")
        elif command == "coinsbatch":
            if len(parts) >= 4:
                handle_admin_set_coins_batch(chat_id, parts[2], parts[3])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin coinsbatch <ids_csv> <amount>")
        elif command == "cashall":
            if len(parts) >= 3:
                handle_admin_set_cash_all(chat_id, parts[2])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin cashall <amount>")
        elif command == "cashbatch":
            if len(parts) >= 4:
                handle_admin_set_cash_batch(chat_id, parts[2], parts[3])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin cashbatch <ids_csv> <amount>")
        elif command == "cash":
            if len(parts) >= 4:
                reason = " ".join(parts[4:]) if len(parts) > 4 else ""
                handle_admin_cash(chat_id, parts[2], parts[3], reason)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin cash <telegram_id> <amount> [lý_do]")
        elif command == "add":
            if len(parts) >= 4:
                handle_admin_add_user(chat_id, parts[2], parts[3], parts[4] if len(parts) > 4 else "")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin add <telegram_id> <username> <first_name> [last_name]")
        elif command == "delete":
            if len(parts) >= 3:
                handle_admin_delete_user(chat_id, parts[2])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin delete <telegram_id>")
        elif command == "coins":
            if len(parts) >= 4:
                reason = " ".join(parts[4:]) if len(parts) > 4 else ""
                handle_admin_set_coins(chat_id, parts[2], parts[3], reason)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin coins <telegram_id> <amount> [lý_do]")
        elif command == "vip":
            print(f"🔍 DEBUG: Executing /admin vip command")
            if len(parts) >= 3:
                try:
                    days = int(parts[3])
                    handle_admin_set_vip_days(chat_id, parts[2], days)
                except ValueError:
                    send_telegram_message(chat_id, "❌ Số ngày phải là số nguyên!")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin vip <telegram_id> <số_ngày>")
        elif command == "vipexpiry":
            if len(parts) >= 4:
                handle_admin_set_vip_expiry(chat_id, parts[2], parts[3])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin vipexpiry <telegram_id> <YYYY-MM-DD HH:MM>")
        elif command == "setgtrial":
            if len(parts) >= 3:
                handle_admin_set_google_price(chat_id, parts[2])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setgtrial <giá>")
        elif command == "setgtrialvip":
            if len(parts) >= 3:
                amount = int(parts[2])
                save_bot_config('google_trial_price_vip', amount)
                BOT_CONFIG['google_trial_price_vip'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá VIP Google Trial: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setgtrialvip <giá>")
        elif command == "setgverified":
            if len(parts) >= 3:
                handle_admin_set_google_verify_price(chat_id, parts[2])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setgverified <giá>")
        elif command == "setgverifiedvip":
            if len(parts) >= 3:
                amount = int(parts[2])
                save_bot_config('google_verified_price_vip', amount)
                BOT_CONFIG['google_verified_price_vip'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá VIP Google Verified: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setgverifiedvip <giá>")
        elif command == "setcanva":
            if len(parts) >= 3:
                handle_admin_set_canva_price(chat_id, parts[2])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setcanva <giá>")
        elif command == "setaiultra":
            if len(parts) >= 3:
                try:
                    amount = int(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setaiultra <giá>")
                    return
                save_bot_config('ai_ultra_price', amount)
                BOT_CONFIG['ai_ultra_price'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá Google AI ULTRA 25k Credits: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setaiultra <giá>")
        elif command == "setchatgpt":
            if len(parts) >= 3:
                try:
                    amount = int(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setchatgpt <giá>")
                    return
                save_bot_config('chatgpt_price', amount)
                BOT_CONFIG['chatgpt_price'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá ChatGPT Plus 3 Months: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setchatgpt <giá>")
        elif command == "setaiultravip":
            if len(parts) >= 3:
                try:
                    amount = float(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setaiultravip <giá>")
                    return
                save_bot_config('ai_ultra_price_vip', amount)
                BOT_CONFIG['ai_ultra_price_vip'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá VIP Google AI ULTRA: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setaiultravip <giá>")
        elif command == "setaiultra45":
            if len(parts) >= 3:
                try:
                    amount = int(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setaiultra45 <giá>")
                    return
                save_bot_config('ai_ultra45_price', amount)
                BOT_CONFIG['ai_ultra45_price'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá Google AI ULTRA 45k Credits: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setaiultra45 <giá>")
        elif command == "setaiultra45v":
            if len(parts) >= 3:
                try:
                    amount = float(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setaiultra45v <giá>")
                    return
                save_bot_config('ai_ultra45_price_vip', amount)
                BOT_CONFIG['ai_ultra45_price_vip'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá VIP Google AI ULTRA 45k Credits: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setaiultra45v <giá>")
        elif command == "setchatgptvip":
            if len(parts) >= 3:
                try:
                    amount = float(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setchatgptvip <giá>")
                    return
                save_bot_config('chatgpt_price_vip', amount)
                BOT_CONFIG['chatgpt_price_vip'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá VIP ChatGPT Plus 3 Months: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setchatgptvip <giá>")
        elif command == "setspotify":
            if len(parts) >= 3:
                try:
                    amount = int(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setspotify <giá>")
                    return
                save_bot_config('spotify_price', amount)
                BOT_CONFIG['spotify_price'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá Spotify Premium 4M CODE: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setspotify <giá>")
        elif command == "setspotifyvip":
            if len(parts) >= 3:
                try:
                    amount = float(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setspotifyvip <giá>")
                    return
                save_bot_config('spotify_price_vip', amount)
                BOT_CONFIG['spotify_price_vip'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá VIP Spotify Premium 4M CODE: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setspotifyvip <giá>")
        elif command == "setsurfshark":
            if len(parts) >= 3:
                try:
                    amount = int(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setsurfshark <giá>")
                    return
                save_bot_config('surfshark_price', amount)
                BOT_CONFIG['surfshark_price'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá Surfshark VPN: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setsurfshark <giá>")
        elif command == "setsurfsharkv":
            if len(parts) >= 3:
                try:
                    amount = float(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setsurfsharkv <giá>")
                    return
                save_bot_config('surfshark_price_vip', amount)
                BOT_CONFIG['surfshark_price_vip'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá VIP Surfshark VPN: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setsurfsharkv <giá>")
        elif command == "setper":
            if len(parts) >= 3:
                try:
                    amount = int(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setper <giá>")
                    return
                save_bot_config('perplexity_price', amount)
                BOT_CONFIG['perplexity_price'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá Perplexity PRO 1 Năm: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setper <giá>")
        elif command == "setperv":
            if len(parts) >= 3:
                try:
                    amount = float(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setperv <giá>")
                    return
                save_bot_config('perplexity_price_vip', amount)
                BOT_CONFIG['perplexity_price_vip'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá VIP Perplexity PRO 1 Năm: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setperv <giá>")
        elif command == "setper1m":
            if len(parts) >= 3:
                try:
                    amount = int(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setper1m <giá>")
                    return
                save_bot_config('perplexity1m_price', amount)
                BOT_CONFIG['perplexity1m_price'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá Perplexity PRO 1 Month: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setper1m <giá>")
        elif command == "setper1mv":
            if len(parts) >= 3:
                try:
                    amount = float(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setper1mv <giá>")
                    return
                save_bot_config('perplexity1m_price_vip', amount)
                BOT_CONFIG['perplexity1m_price_vip'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá VIP Perplexity PRO 1 Month: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setper1mv <giá>")
        elif command == "setgpt1m":
            if len(parts) >= 3:
                try:
                    amount = int(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setgpt1m <giá>")
                    return
                save_bot_config('gpt1m_price', amount)
                BOT_CONFIG['gpt1m_price'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá ChatGPT Code 1 Month: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setgpt1m <giá>")
        elif command == "setgpt1mv":
            if len(parts) >= 3:
                try:
                    amount = float(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setgpt1mv <giá>")
                    return
                save_bot_config('gpt1m_price_vip', amount)
                BOT_CONFIG['gpt1m_price_vip'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá VIP ChatGPT Code 1 Month: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setgpt1mv <giá>")
        elif command == "setm365":
            if len(parts) >= 3:
                try:
                    amount = int(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setm365 <giá>")
                    return
                save_bot_config('m365_price', amount)
                BOT_CONFIG['m365_price'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá Microsoft 365 Personal 1 Năm: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setm365 <giá>")
        elif command == "setm365v":
            if len(parts) >= 3:
                try:
                    amount = float(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setm365v <giá>")
                    return
                save_bot_config('m365_price_vip', amount)
                BOT_CONFIG['m365_price_vip'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá VIP Microsoft 365 Personal 1 Năm: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setm365v <giá>")
        elif command == "setadobe4m":
            if len(parts) >= 3:
                try:
                    amount = int(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setadobe4m <giá>")
                    return
                save_bot_config('adobe4m_price', amount)
                BOT_CONFIG['adobe4m_price'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá ADOBE FULL APP 4 Months: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setadobe4m <giá>")
        elif command == "setadobe4mv":
            if len(parts) >= 3:
                try:
                    amount = float(parts[2])
                except Exception:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin setadobe4mv <giá>")
                    return
                save_bot_config('adobe4m_price_vip', amount)
                BOT_CONFIG['adobe4m_price_vip'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá VIP ADOBE FULL APP 4 Months: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setadobe4mv <giá>")
        elif command == "addviprices":
            # Thêm tất cả giá VIP còn thiếu vào Supabase
            try:
                vip_prices = {
                    'google_verified_price_vip': 5.5,
                    'canva_price_vip': 279,
                    'ai_ultra_price_vip': 23,
                    'chatgpt_price_vip': 55
                }
                added_count = 0
                for key, value in vip_prices.items():
                    save_bot_config(key, value)
                    BOT_CONFIG[key] = value
                    added_count += 1
                send_telegram_message(chat_id, f"✅ Đã thêm {added_count} giá VIP vào Supabase")
            except Exception as e:
                send_telegram_message(chat_id, f"❌ Lỗi thêm giá VIP: {str(e)}")
        elif command == "setcanvavip":
            if len(parts) >= 3:
                amount = int(parts[2])
                save_bot_config('canva_price_vip', amount)
                BOT_CONFIG['canva_price_vip'] = amount
                send_telegram_message(chat_id, f"✅ Đã đặt giá VIP Canva: {amount} CASH")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setcanvavip <giá>")
        elif command == "settype":
            if len(parts) >= 4:
                handle_admin_set_account_type(chat_id, parts[2], parts[3])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin settype <account_id> <trial|verified|canva|chatgpt|spotify|surfshark|perplexity>")
        elif command == "setvip7":
            if len(parts) >= 3:
                handle_admin_set_vip7_price(chat_id, parts[2])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setvip7 <giá>")
        elif command == "setvip30":
            if len(parts) >= 3:
                handle_admin_set_vip30_price(chat_id, parts[2])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin setvip30 <giá>")
        elif command == "createconfig":
            handle_admin_create_config_table(chat_id)
        elif command == "migratexu":
            admin_migrate_all_balances_to_xu(chat_id)
        elif command == "stock":
            handle_admin_stock(chat_id)
        elif command == "importcsv":
            if len(parts) >= 3:
                handle_admin_import_csv(chat_id, parts[2])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin importcsv <url_csv>")
        elif command == "migratecash":
            admin_migrate_cash_to_coins(chat_id)
        elif command == "jobs":
            if len(parts) >= 3:
                handle_admin_user_jobs(chat_id, parts[2])
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin jobs <telegram_id>")
        elif command == "noti":
            if len(parts) >= 3:
                # Join all parts after "noti" to get the full message
                notification_text = " ".join(parts[2:])
                
                # Check if broadcast is already in progress
                if BROADCAST_IN_PROGRESS:
                    send_telegram_message(chat_id, "⏳ Hệ thống đang gửi thông báo khác. Vui lòng thử lại sau.")
                else:
                    # Send immediate confirmation
                    send_telegram_message(chat_id, "🚀 Đã bắt đầu gửi thông báo!\n\n📊 Bạn sẽ nhận được cập nhật tiến độ mỗi 50 users.")
                    
                    # Run broadcast in background thread
                    import threading
                    thread = threading.Thread(
                        target=handle_admin_send_notification,
                        args=(chat_id, notification_text),
                        daemon=False  # Changed to False to ensure it completes
                    )
                    thread.start()
                    print(f"🚀 Broadcast thread started: {thread.name}, alive: {thread.is_alive()}")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin noti <nội_dung_thông_báo>")
        elif command == "w":
            # /admin w <telegram_id> <nội_dung>
            if len(parts) >= 4:
                target_telegram_id = parts[2]
                content = " ".join(parts[3:])
                try:
                    send_telegram_message(int(target_telegram_id), f"Tin nhắn từ ADMIN:\n{content}")
                    send_telegram_message(chat_id, f"✅ Đã gửi whisper đến {target_telegram_id}")
                except Exception as e:
                    send_telegram_message(chat_id, f"❌ Không gửi được whisper: {str(e)}")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin w <telegram_id> <nội_dung>")
        elif command == "ban":
            if len(parts) >= 4:
                target_telegram_id = parts[2]
                reason = " ".join(parts[3:])
                handle_admin_ban_user(chat_id, target_telegram_id, reason)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin ban <telegram_id> <lý_do>")
        elif command == "unban":
            if len(parts) >= 4:
                target_telegram_id = parts[2]
                reason = " ".join(parts[3:])
                handle_admin_unban_user(chat_id, target_telegram_id, reason)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin unban <telegram_id> <ghi_chú>")
        elif command == "user":
            if len(parts) >= 3:
                target_telegram_id = parts[2]
                handle_admin_user_info(chat_id, target_telegram_id)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin user <telegram_id>")
        elif command == "purchases":
            if len(parts) >= 3:
                target_telegram_id = parts[2]
                handle_admin_user_purchases(chat_id, target_telegram_id)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin purchases <telegram_id>")
        elif command == "lsgd":
            if len(parts) >= 3:
                try:
                    page = int(parts[2])
                    handle_admin_lsgd(chat_id, page)
                except ValueError:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin lsgd [trang]")
            else:
                handle_admin_lsgd(chat_id, 1)
        elif command == "activities":
            if len(parts) >= 3:
                try:
                    page = int(parts[2])
                    handle_admin_activities(chat_id, page)
                except ValueError:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin activities [trang]")
            else:
                handle_admin_activities(chat_id, 1)
        elif command == "pendingjobs":
            handle_admin_pending_jobs(chat_id)
        elif command == "fixstuckjobs":
            handle_admin_fix_stuck_jobs(chat_id)
        elif command == "giftcoins":
            if len(parts) >= 4:
                try:
                    amount = int(parts[2])
                    reason = ' '.join(parts[3:])
                    handle_admin_gift_coins(chat_id, amount, reason)
                except ValueError:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin giftcoins <số_xu> <lý_do>")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin giftcoins <số_xu> <lý_do>")
        elif command == "giftcash":
            if len(parts) >= 4:
                try:
                    amount = int(parts[2])
                    reason = ' '.join(parts[3:])
                    handle_admin_gift_cash(chat_id, amount, reason)
                except ValueError:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin giftcash <số_cash> <lý_do>")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin giftcash <số_cash> <lý_do>")
        elif command == "giftcode":
            # /admin giftcode <mã> <xu/cash> <số_lượng> <số_lượt>
            if len(parts) >= 6:
                try:
                    code = parts[2]
                    reward_type = parts[3].lower()
                    reward_amount = int(parts[4])
                    max_uses = int(parts[5])
                    handle_admin_create_giftcode(chat_id, code, reward_type, reward_amount, max_uses)
                except ValueError:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin giftcode <mã> <xu/cash> <số_lượng> <số_lượt>")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin giftcode <mã> <xu/cash> <số_lượng> <số_lượt>")
        elif command == "listgiftcodes":
            handle_admin_list_giftcodes(chat_id)
        elif command == "giftcodeinfo":
            if len(parts) >= 3:
                code = parts[2]
                handle_admin_giftcode_info(chat_id, code)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin giftcodeinfo <mã>")
        elif command == "deactivategiftcode":
            if len(parts) >= 3:
                code = parts[2]
                handle_admin_deactivate_giftcode(chat_id, code)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin deactivategiftcode <mã>")
        # ============================================
        # SELLER API COMMANDS
        # ============================================
        elif command == "addseller":
            # /admin addseller <telegram_id> <credits> [name]
            # telegram_id để link với user account cho /buycredits
            if len(parts) >= 4:
                try:
                    seller_telegram_id = int(parts[2])
                    initial_credits = int(parts[3])
                    seller_name = parts[4] if len(parts) >= 5 else f"Seller_{seller_telegram_id}"
                    handle_admin_add_seller(chat_id, seller_name, initial_credits, seller_telegram_id)
                except ValueError:
                    send_telegram_message(chat_id, "❌ Sử dụng: /admin addseller <telegram_id> <credits> [tên]")
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin addseller <telegram_id> <credits> [tên]\n\nVí dụ: /admin addseller 5107573464 10 ShopABC")
        elif command == "addcredits":
            # /admin addcredits <seller_id> <credits>
            if len(parts) >= 4:
                seller_id = int(parts[2])
                credits = int(parts[3])
                handle_admin_add_credits(chat_id, seller_id, credits)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin addcredits <seller_id> <credits>")
        elif command == "sellers":
            # /admin sellers - List all sellers
            handle_admin_list_sellers(chat_id)
        elif command == "seller":
            # /admin seller <seller_id> - View seller details
            if len(parts) >= 3:
                seller_id = int(parts[2])
                handle_admin_view_seller(chat_id, seller_id)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin seller <seller_id>")
        elif command == "toggleseller":
            # /admin toggleseller <seller_id> - Enable/disable seller
            if len(parts) >= 3:
                seller_id = int(parts[2])
                handle_admin_toggle_seller(chat_id, seller_id)
            else:
                send_telegram_message(chat_id, "❌ Sử dụng: /admin toggleseller <seller_id>")
        else:
            message = """🔧 ADMIN COMMANDS:

👥 User:
/admin users [trang] - Danh sách user (5/user/trang)
/admin user <telegram_id> - Xem thông tin chi tiết user
/admin purchases <telegram_id> - Xem lịch sử mua hàng của user
/admin lsgd [trang] - Xem lịch sử nạp tiền (5/trang)
/admin activities [trang] - Xem tất cả giao dịch server (5/trang)
/admin add <telegram_id> <username> <first_name> [last_name]
/admin delete <telegram_id>
/admin clear - Xóa tất cả user (cẩn thận)

💰 Ví:
/admin coins <telegram_id> <amount> [lý_do] - Set Xu cho user
/admin cash <telegram_id> <amount> [lý_do] - Cộng/trừ CASH cho user
/admin refund <telegram_id> <amount> - Hoàn Xu cho user
/admin giftcoins <số_xu> <lý_do> - Tặng xu cho TẤT CẢ user
/admin giftcash <số_cash> <lý_do> - Tặng cash cho TẤT CẢ user
/admin transactions - Xem giao dịch gần đây

🎟️ Giftcode:
/admin giftcode <mã> <xu/cash> <số_lượng> <số_lượt> - Tạo giftcode
/admin listgiftcodes - Xem danh sách giftcode
/admin giftcodeinfo <mã> - Xem chi tiết giftcode
/admin deactivategiftcode <mã> - Vô hiệu hóa giftcode

👑 VIP:
/admin vip <telegram_id> <số_ngày> - Bật VIP theo ngày (0=tắt)
/admin vipexpiry <telegram_id> <YYYY-MM-DD HH:MM> - Set hạn VIP
/admin vipall <số_ngày>
/admin vipbatch <ids_csv> <số_ngày>

🏪 Seller API:
/admin addseller <tên> [credits] - Tạo seller mới
/admin addcredits <seller_id> <credits> - Thêm credits
/admin sellers - Danh sách sellers
/admin seller <seller_id> - Xem chi tiết seller
/admin toggleseller <seller_id> - Bật/tắt seller

❓ Hỗ trợ: @meepzizhere"""
            send_telegram_message(chat_id, message)
    except Exception as e:
        print(f"Error in handle_admin_command: {e}")
        try:
            send_telegram_message(chat_id, f"❌ Lỗi xử lý admin command: {str(e)}")
        except:
            pass

# ============================================
# SELLER API ADMIN HANDLERS
# ============================================

def handle_admin_add_seller(chat_id, name, initial_credits=0, telegram_id=None):
    """Add a new seller with optional telegram_id link"""
    try:
        from .seller_api import create_seller
        from .supabase_client import get_supabase_client
        
        seller, error = create_seller(name, initial_credits=initial_credits, telegram_id=telegram_id)
        
        if seller:
            # Get user language for seller notification
            user_lang = 'vi'  # Default
            if telegram_id:
                try:
                    supabase = get_supabase_client()
                    if supabase:
                        user_result = supabase.table('users').select('language').eq('telegram_id', telegram_id).execute()
                        if user_result.data:
                            user_lang = user_result.data[0].get('language', 'vi') or 'vi'
                except:
                    pass
            
            # Admin message with emoji
            tg_info = f"\n📱 Telegram ID: {telegram_id}" if telegram_id else ""
            admin_msg = (
                "✅ Seller đã được tạo thành công!\n\n"
                f"🆔 ID: {seller['id']}\n"
                f"👤 Tên: {seller['name']}\n"
                f"🔑 API Key: {seller['api_key']}\n"
                f"💰 Credits: {seller['credits']}"
                f"{tg_info}\n\n"
                "⚠️ Lưu API Key này, không thể xem lại!"
            )
            send_telegram_message_plain(chat_id, admin_msg)
            
            # Send notification to seller if telegram_id provided
            if telegram_id:
                # Build message based on user language
                if user_lang == 'en':
                    seller_msg = (
                        "🎉 Welcome! You are now a Seller!\n\n"
                        "✅ Your Seller API account has been created successfully.\n\n"
                        "📋 Account Info:\n"
                        f"🆔 Seller ID: {seller['id']}\n"
                        f"🔑 API Key: {seller['api_key']}\n"
                        f"💰 Credits: {seller['credits']}\n\n"
                        "📚 API Guide: https://dqsheerid.vercel.app/docs\n\n"
                        "💳 Buy more credits: /buycredits [amount]\n"
                        "💱 Rate: 3 cash = 1 credit\n\n"
                        "⚠️ Note: Please save this API Key carefully!\n"
                        "📞 Support: @meepzizhere"
                    )
                elif user_lang == 'zh':
                    seller_msg = (
                        "🎉 欢迎！您现在是卖家了！\n\n"
                        "✅ 您的卖家API账户已成功创建。\n\n"
                        "📋 账户信息：\n"
                        f"🆔 卖家ID: {seller['id']}\n"
                        f"🔑 API密钥: {seller['api_key']}\n"
                        f"💰 积分: {seller['credits']}\n\n"
                        "📚 API指南: https://dqsheerid.vercel.app/docs\n\n"
                        "💳 购买更多积分: /buycredits [数量]\n"
                        "💱 汇率: 3 cash = 1 credit\n\n"
                        "⚠️ 注意：请妥善保存此API密钥！\n"
                        "📞 支持: @meepzizhere"
                    )
                else:  # Vietnamese default
                    seller_msg = (
                        "🎉 Chào mừng bạn đã trở thành Seller!\n\n"
                        "✅ Tài khoản Seller API của bạn đã được tạo thành công.\n\n"
                        "📋 Thông tin tài khoản:\n"
                        f"🆔 Seller ID: {seller['id']}\n"
                        f"🔑 API Key: {seller['api_key']}\n"
                        f"💰 Credits: {seller['credits']}\n\n"
                        "📚 Hướng dẫn API: https://dqsheerid.vercel.app/docs\n\n"
                        "💳 Mua thêm credits: /buycredits [số_lượng]\n"
                        "💱 Tỷ giá: 3 cash = 1 credit\n\n"
                        "⚠️ Lưu ý: Hãy lưu API Key này cẩn thận!\n"
                        "📞 Hỗ trợ: @meepzizhere"
                    )
                try:
                    send_telegram_message_plain(telegram_id, seller_msg)
                    print(f"Sent seller notification to {telegram_id}")
                except Exception as e:
                    print(f"Failed to notify seller {telegram_id}: {e}")
            
            return
        else:
            send_telegram_message_plain(chat_id, f"❌ Lỗi tạo seller: {error}")
            return
        
    except Exception as e:
        send_telegram_message_plain(chat_id, f"❌ Lỗi: {e}")

def handle_admin_add_credits(chat_id, seller_id, credits):
    """Add credits to seller"""
    try:
        from .seller_api import add_seller_credits
        
        success, message = add_seller_credits(seller_id, credits)
        
        if success:
            send_telegram_message(chat_id, f"✅ {message}")
        else:
            send_telegram_message(chat_id, f"❌ {message}")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi: {e}")

def handle_admin_list_sellers(chat_id):
    """List all sellers"""
    try:
        from .seller_api import get_all_sellers
        
        sellers = get_all_sellers()
        
        if not sellers:
            send_telegram_message(chat_id, "📋 Chưa có seller nào.")
            return
        
        message = "📋 DANH SÁCH SELLERS:\n\n"
        for s in sellers:
            status = "✅" if s.get('is_active') else "❌"
            message += f"{status} ID: {s['id']} | {s['name']}\n"
            message += f"   💰 Credits: {s['credits']} | Used: {s.get('total_used', 0)}\n\n"
        
        message += f"📊 Tổng: {len(sellers)} sellers"
        send_telegram_message(chat_id, message)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi: {e}")

def handle_admin_view_seller(chat_id, seller_id):
    """View seller details"""
    try:
        from .supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Database unavailable")
            return
        
        result = supabase.table('sellers').select('*').eq('id', seller_id).execute()
        
        if not result.data:
            send_telegram_message(chat_id, "❌ Seller không tồn tại")
            return
        
        s = result.data[0]
        status = "✅ Active" if s.get('is_active') else "❌ Inactive"
        
        message = f"""👤 SELLER DETAILS

🆔 ID: {s['id']}
👤 Tên: {s['name']}
📧 Email: {s.get('email', 'N/A')}
🔑 API Key: {s['api_key'][:20]}...
💰 Credits: {s['credits']}
📊 Total Used: {s.get('total_used', 0)}
🔗 Webhook: {s.get('webhook_url', 'N/A')}
⚡ Rate Limit: {s.get('rate_limit', 10)}/min
📅 Created: {s.get('created_at', 'N/A')[:19]}
🔄 Status: {status}"""
        
        send_telegram_message(chat_id, message)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi: {e}")

def handle_admin_toggle_seller(chat_id, seller_id):
    """Toggle seller active status"""
    try:
        from .supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Database unavailable")
            return
        
        # Get current status
        result = supabase.table('sellers').select('is_active, name').eq('id', seller_id).execute()
        
        if not result.data:
            send_telegram_message(chat_id, "❌ Seller không tồn tại")
            return
        
        current_status = result.data[0].get('is_active', True)
        new_status = not current_status
        
        # Update status
        supabase.table('sellers').update({
            'is_active': new_status,
            'updated_at': datetime.now().isoformat()
        }).eq('id', seller_id).execute()
        
        status_text = "✅ ACTIVE" if new_status else "❌ INACTIVE"
        send_telegram_message(chat_id, f"🔄 Seller {result.data[0]['name']} đã được chuyển sang: {status_text}")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi: {e}")

def send_admin_help(chat_id):
    """Send admin help message"""
    message = """
🔧 ADMIN COMMANDS:

📋 Quản lý user:
/admin users - Xem danh sách tất cả user
/admin getid <tên> - Tìm telegram_id theo tên user
/admin clear - Xóa toàn bộ user
/admin add <telegram_id> <username> <first_name> [last_name] - Thêm user mới
/admin delete <telegram_id> - Xóa user

💰 Quản lý xu:
/admin coins <telegram_id> <amount> [lý_do] - Set số xu cho user
/admin cash <telegram_id> <amount> [lý_do] - Cộng/trừ CASH cho user
/admin giftcoins <số_xu> <lý_do> - Tặng xu cho TẤT CẢ user
/admin giftcash <số_cash> <lý_do> - Tặng cash cho TẤT CẢ user

🎟️ Giftcode:
/admin giftcode <mã> <xu/cash> <số_lượng> <số_lượt> - Tạo giftcode
/admin listgiftcodes - Xem danh sách giftcode
/admin giftcodeinfo <mã> - Xem chi tiết giftcode
/admin deactivategiftcode <mã> - Vô hiệu hóa giftcode

🛠️ Công cụ:
/admin migratexu - Gộp legacy về Xu (CASH=0)
/admin migratecash - Chuyển toàn bộ CASH sang Xu (CASH=0)
/admin ban <telegram_id> <lý_do> - Khóa user và gửi thông báo
/admin unban <telegram_id> <ghi_chú> - Mở khóa user và gửi thông báo

👑 Quản lý VIP:
/admin vip <telegram_id> <số_ngày> - Set VIP cho user (0 = tắt VIP)
/admin vipexpiry <telegram_id> <YYYY-MM-DD HH:MM> - Set hạn sử dụng VIP
/admin checkvip - Kiểm tra và cập nhật VIP hết hạn

📊 Theo dõi:
/admin jobs <telegram_id> - Xem jobs của user

⚙️ Cấu hình:
/admin setbonus <amount> - Xu checkin/ngày (áp dụng cho /checkin hoặc /diemdanh)

❓ Hỗ trợ: @meepzizhere
    """
    send_telegram_message(chat_id, message)

def handle_admin_cash(chat_id, telegram_id, amount, reason=""):
    """Admin: adjust CASH by telegram_id (positive or negative)."""
    try:
        delta = int(amount)
        from supabase_client import adjust_user_cash_by_telegram_id, get_user_by_telegram_id
        description = f"Admin cash adjust {delta}"
        if reason:
            description += f" | Lý do: {reason}"
        new_cash = adjust_user_cash_by_telegram_id(telegram_id, delta, tx_type='admin_cash', description=description)
        if new_cash is None:
            send_telegram_message(chat_id, "❌ Không cập nhật được CASH (kiểm tra user hoặc số dư).")
            return
        user = get_user_by_telegram_id(str(telegram_id))
        admin_msg = f"✅ Đã thêm {delta} cho user {telegram_id}, Tổng CASH: {new_cash}"
        if reason:
            admin_msg += f"\n📝 Lý do: {reason}"
        send_telegram_message(chat_id, admin_msg)
        
        # Send notification to user
        try:
            action = "added" if delta > 0 else "deducted"
            user_msg = f"💵 ADMIN has {action} {abs(delta)} CASH {'to' if delta > 0 else 'from'} your account\n💰 Current balance: {new_cash} CASH"
            if reason:
                user_msg += f"\n📝 Reason: {reason}"
            
            # Ensure telegram_id is int
            user_chat_id = int(telegram_id) if isinstance(telegram_id, str) else telegram_id
            send_telegram_message(user_chat_id, user_msg)
            print(f"✅ Sent cash notification to user {telegram_id}")
        except Exception as e:
            print(f"⚠️ Failed to send notification to user {telegram_id}: {e}")
            # Don't fail the whole operation if notification fails
    except ValueError:
        send_telegram_message(chat_id, "❌ Số tiền phải là số nguyên!")
    except Exception as e:
        print(f"❌ Error in handle_admin_cash: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_set_vip_all(chat_id, days):
    try:
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        import datetime
        if days and days > 0:
            expiry = (datetime.datetime.utcnow() + datetime.timedelta(days=days)).isoformat()
            update_data = {'is_vip': True, 'vip_expiry': expiry}
        else:
            update_data = {'is_vip': False, 'vip_expiry': None}
        supabase.table('users').update(update_data).neq('id', 0).execute()
        if days and days > 0:
            send_telegram_message(chat_id, f"✅ Đã bật VIP toàn bộ user ({days} ngày)")
        else:
            send_telegram_message(chat_id, "✅ Đã tắt VIP cho toàn bộ user")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi vipall: {str(e)}")

def handle_admin_set_vip_batch(chat_id, ids_csv, days):
    try:
        ids = [x.strip() for x in ids_csv.split(',') if x.strip()]
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        import datetime
        if days and days > 0:
            expiry = (datetime.datetime.utcnow() + datetime.timedelta(days=days)).isoformat()
            upd = {'is_vip': True, 'vip_expiry': expiry}
        else:
            upd = {'is_vip': False, 'vip_expiry': None}
        for tid in ids:
            supabase.table('users').update(upd).eq('telegram_id', tid).execute()
        if days and days > 0:
            send_telegram_message(chat_id, f"✅ Đã bật VIP cho {len(ids)} user ({days} ngày)")
        else:
            send_telegram_message(chat_id, f"✅ Đã tắt VIP cho {len(ids)} user")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi vipbatch: {str(e)}")

def handle_admin_set_coins_all(chat_id, amount):
    try:
        amount = int(amount)
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        supabase.table('users').update({'coins': amount}).neq('id', 0).execute()
        send_telegram_message(chat_id, f"✅ Đã set Xu={amount} cho toàn bộ user")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi coinsall: {str(e)}")

def handle_admin_set_coins_batch(chat_id, ids_csv, amount):
    try:
        amount = int(amount)
        ids = [x.strip() for x in ids_csv.split(',') if x.strip()]
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        for tid in ids:
            supabase.table('users').update({'coins': amount}).eq('telegram_id', tid).execute()
        send_telegram_message(chat_id, f"✅ Đã set Xu cho {len(ids)} user")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi coinsbatch: {str(e)}")

def handle_admin_set_cash_all(chat_id, amount):
    try:
        amount = int(amount)
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        supabase.table('users').update({'cash': amount}).neq('id', 0).execute()
        send_telegram_message(chat_id, f"✅ Đã set CASH={amount} cho toàn bộ user")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi cashall: {str(e)}")

def handle_admin_set_cash_batch(chat_id, ids_csv, amount):
    try:
        amount = int(amount)
        ids = [x.strip() for x in ids_csv.split(',') if x.strip()]
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        for tid in ids:
            supabase.table('users').update({'cash': amount}).eq('telegram_id', tid).execute()
        send_telegram_message(chat_id, f"✅ Đã set CASH cho {len(ids)} user")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi cashbatch: {str(e)}")

def handle_admin_list_users(chat_id, page=1):
    """List users for admin with pagination (5 users per page)"""
    try:
        print(f"🔄 handle_admin_list_users called: chat_id={chat_id}, page={page}")
        # Try to get users from Supabase first
        all_users = None
        if SUPABASE_AVAILABLE:
            print(f"🔄 Using Supabase: Getting all users for admin")
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    # Get all users from Supabase
                    response = supabase.table('users').select('telegram_id, username, first_name, last_name, coins, cash, is_vip, vip_expiry, created_at').order('created_at', desc=True).execute()
                    all_users = response.data if response.data else []
                    
                    if not all_users:
                        send_telegram_message(chat_id, "📝 Chưa có user nào")
                        return
                    
                    # Calculate pagination
                    users_per_page = 5
                    total_users = len(all_users)
                    total_pages = (total_users + users_per_page - 1) // users_per_page
                    page = max(1, min(page, total_pages))  # Ensure page is within valid range
                    
                    offset = (page - 1) * users_per_page
                    users = all_users[offset:offset + users_per_page]
                    
                    print(f"✅ Found {len(users)} users from Supabase for page {page}")
                else:
                    print("❌ Supabase client not available")
                    all_users = None
                
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                print("🔄 Falling back to SQLite")
                all_users = None
        
        if not SUPABASE_AVAILABLE or not all_users:
            # Fallback to SQLite
            print(f"🔄 Fallback: Getting users from SQLite")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            if total_users == 0:
                send_telegram_message(chat_id, "📝 Chưa có user nào")
                conn.close()
                return
            
            # Calculate pagination
            users_per_page = 5
            total_pages = (total_users + users_per_page - 1) // users_per_page
            page = max(1, min(page, total_pages))  # Ensure page is within valid range
            
            offset = (page - 1) * users_per_page
            
            # Get users for current page
            cursor.execute('''
                SELECT telegram_id, username, first_name, last_name, coins, is_vip, vip_expiry, created_at
                FROM users 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (users_per_page, offset))
            
            users = cursor.fetchall()
            conn.close()
            
            # Convert tuple format to dict format for consistency
            users = [{
                'telegram_id': user[0],
                'username': user[1],
                'first_name': user[2],
                'last_name': user[3],
                'coins': user[4],
                'cash': 0,
                'is_vip': user[5],
                'vip_expiry': user[6],
                'created_at': user[7]
            } for user in users]
            
            total_users = len(users)
            total_pages = 1  # For SQLite fallback, we'll show all users on one page

        message = f"👥 DANH SÁCH USER (Trang {page}/{total_pages}):\n\n"
        
        for i, user in enumerate(users, 1):
            # Handle both dict and tuple formats
            if isinstance(user, dict):
                telegram_id = user.get('telegram_id', 'N/A')
                username = user.get('username', 'N/A')
                first_name = user.get('first_name', 'N/A')
                last_name = user.get('last_name', 'N/A')
                coins = user.get('coins', 0)
                cash = user.get('cash', 0)
                is_vip = user.get('is_vip', False)
                vip_expiry = user.get('vip_expiry')
                created_at = user.get('created_at', 'N/A')
            else:
                # Tuple format (fallback)
                telegram_id, username, first_name, last_name, coins, is_vip, vip_expiry, created_at = user
                cash = 0
        
            vip_badge = "👑" if is_vip else ""
            
            vip_status = "✅"
            if is_vip and vip_expiry:
                from datetime import datetime, timezone, timedelta
                try:
                    # Parse UTC expiry time and convert to Vietnam time
                    expiry_date_utc = datetime.fromisoformat(vip_expiry.replace('Z', '+00:00'))
                    vietnam_tz = timezone(timedelta(hours=7))
                    expiry_date_vietnam = expiry_date_utc.astimezone(vietnam_tz)
                    vip_status = f"✅ (hết hạn: {expiry_date_vietnam.strftime('%d/%m/%Y %H:%M')} VN)"
                except:
                    vip_status = "✅"
            elif not is_vip:
                vip_status = "❌"
        
            # Convert created_at to Vietnam time
            try:
                from datetime import datetime, timezone, timedelta
                created_date_utc = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                vietnam_tz = timezone(timedelta(hours=7))
                created_date_vietnam = created_date_utc.astimezone(vietnam_tz)
                created_at_formatted = created_date_vietnam.strftime('%d/%m/%Y %H:%M')
            except:
                created_at_formatted = created_at[:16]
        
            message += f"""
{offset + i}. ID: {telegram_id}
Tên: {first_name} {last_name if last_name and last_name != 'User' else ''}
Username: @{username or 'N/A'}
Xu: {coins} 🪙
Cash: {cash} 💵
VIP: {vip_status} {vip_badge}
Tham gia: {created_at_formatted} VN
---
"""
    
        # Add pagination info
        message += f"\n📊 Tổng: {total_users} user"
        
        # Create inline keyboard for pagination
        keyboard = []
        if total_pages > 1:
            # Navigation buttons
            nav_buttons = []
            
            # Previous page button
            if page > 1:
                nav_buttons.append({
                    "text": "⬅️ Trang trước",
                    "callback_data": f"admin_users_page_{page-1}"
                })
            
            # Page info button
            nav_buttons.append({
                "text": f"📄 {page}/{total_pages}",
                "callback_data": "admin_users_info"
            })
            
            # Next page button
            if page < total_pages:
                nav_buttons.append({
                    "text": "Trang tiếp ➡️",
                    "callback_data": f"admin_users_page_{page+1}"
                })
            
            keyboard.append(nav_buttons)
            
            # First/Last page buttons
            if total_pages > 2:
                first_last_buttons = []
                if page > 2:
                    first_last_buttons.append({
                        "text": "🏠 Đầu",
                        "callback_data": "admin_users_page_1"
                    })
                if page < total_pages - 1:
                    first_last_buttons.append({
                        "text": "🔚 Cuối",
                        "callback_data": f"admin_users_page_{total_pages}"
                    })
                
                if first_last_buttons:
                    keyboard.append(first_last_buttons)
    
        # Send message with inline keyboard
        if keyboard:
            send_telegram_message_with_keyboard(chat_id, message, keyboard)
        else:
            send_telegram_message(chat_id, message)
            
    except Exception as e:
        print(f"❌ Error in handle_admin_list_users: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi khi lấy danh sách user: {str(e)}")

def handle_admin_get_id(chat_id, search_name):
    """Find users by name and show their telegram_id"""
    try:
        print(f"🔍 Searching for users with name containing: '{search_name}'")
        
        found_users = []
        
        # Try Supabase first
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    # Search in first_name, last_name, and username
                    response = supabase.table('users').select('telegram_id, username, first_name, last_name, coins, cash, is_vip').execute()
                    all_users = response.data if response.data else []
                    
                    # Filter users by name (case insensitive)
                    for user in all_users:
                        first_name = (user.get('first_name') or '').lower()
                        last_name = (user.get('last_name') or '').lower()
                        username = (user.get('username') or '').lower()
                        full_name = f"{first_name} {last_name}".strip()
                        
                        if (search_name in first_name or 
                            search_name in last_name or 
                            search_name in username or 
                            search_name in full_name):
                            found_users.append(user)
                    
                    print(f"✅ Found {len(found_users)} users from Supabase")
                else:
                    print("❌ Supabase client not available")
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                print("🔄 Falling back to SQLite")
        
        # Fallback to SQLite if Supabase not available or failed
        if not SUPABASE_AVAILABLE or not found_users:
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # Search in first_name, last_name, and username
                cursor.execute('''
                    SELECT telegram_id, username, first_name, last_name, coins, is_vip
                    FROM users 
                    WHERE LOWER(first_name) LIKE ? 
                       OR LOWER(last_name) LIKE ? 
                       OR LOWER(username) LIKE ?
                       OR LOWER(first_name || ' ' || last_name) LIKE ?
                    ORDER BY created_at DESC
                ''', (f'%{search_name}%', f'%{search_name}%', f'%{search_name}%', f'%{search_name}%'))
                
                users_data = cursor.fetchall()
                conn.close()
                
                # Convert to dict format
                for user_data in users_data:
                    found_users.append({
                        'telegram_id': user_data[0],
                        'username': user_data[1],
                        'first_name': user_data[2],
                        'last_name': user_data[3],
                        'coins': user_data[4],
                        'cash': 0,  # SQLite fallback doesn't have cash
                        'is_vip': user_data[5]
                    })
                
                print(f"✅ Found {len(found_users)} users from SQLite")
            except Exception as e:
                print(f"❌ SQLite error: {e}")
        
        # Format and send results
        if not found_users:
            send_telegram_message(chat_id, f"❌ Không tìm thấy user nào có tên chứa '{search_name}'")
            return
        
        # Limit results to prevent message too long
        max_results = 10
        if len(found_users) > max_results:
            found_users = found_users[:max_results]
            truncated_msg = f"\n\n⚠️ Chỉ hiển thị {max_results} kết quả đầu tiên"
        else:
            truncated_msg = ""
        
        message = f"🔍 **Tìm thấy {len(found_users)} user có tên chứa '{search_name}':**\n\n"
        
        for i, user in enumerate(found_users, 1):
            telegram_id = user.get('telegram_id', 'N/A')
            username = user.get('username', 'N/A')
            first_name = user.get('first_name', '')
            last_name = user.get('last_name', '')
            coins = user.get('coins', 0)
            cash = user.get('cash', 0)
            is_vip = user.get('is_vip', False)
            
            full_name = f"{first_name} {last_name}".strip()
            vip_status = "👑 VIP" if is_vip else "👤 Thường"
            
            message += f"""**{i}. {full_name}**
📱 Telegram ID: `{telegram_id}`
👤 Username: @{username if username and username != 'N/A' else 'Không có'}
💰 Xu: {coins} | 💵 Cash: {cash}
🎭 Loại: {vip_status}
---
"""
        
        message += f"\n📊 Tổng: {len(found_users)} kết quả{truncated_msg}"
        message += f"\n\n💡 **Cách sử dụng:**"
        message += f"\n• Copy telegram ID để dùng cho các lệnh admin khác"
        message += f"\n• Ví dụ: `/admin coins {found_users[0].get('telegram_id')} 100`"
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"❌ Error in handle_admin_get_id: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi khi tìm kiếm user: {str(e)}")

def handle_admin_check_vip(chat_id):
    """Check and update expired VIP users"""
    try:
        print("🔍 Checking VIP expiry for all users...")
        
        expired_users = []
        warning_users = []
        total_vip_users = 0
        
        # Get current Vietnam time
        vietnam_now = get_vietnam_time()
        three_days_later = vietnam_now + timedelta(days=3)
        
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    # Get all VIP users
                    response = supabase.table('users').select('id, telegram_id, first_name, is_vip, vip_expiry').eq('is_vip', True).execute()
                    vip_users = response.data if response.data else []
                    total_vip_users = len(vip_users)
                    
                    print(f"📊 Found {total_vip_users} VIP users to check")
                    
                    for user in vip_users:
                        telegram_id = user.get('telegram_id')
                        first_name = user.get('first_name', 'User')
                        vip_expiry = user.get('vip_expiry')
                        user_id = user.get('id')
                        
                        if not vip_expiry:
                            # VIP without expiry - keep as VIP
                            continue
                        
                        try:
                            # Parse expiry date
                            expiry_date = datetime.fromisoformat(str(vip_expiry).replace('Z', '+00:00'))
                            expiry_vietnam = expiry_date.astimezone(timezone(timedelta(hours=7)))
                            
                            # Check if expired
                            if vietnam_now >= expiry_vietnam:
                                # VIP expired - set to False
                                supabase.table('users').update({
                                    'is_vip': False,
                                    'updated_at': vietnam_now.isoformat()
                                }).eq('id', user_id).execute()
                                
                                expired_users.append({
                                    'telegram_id': telegram_id,
                                    'first_name': first_name,
                                    'expiry': expiry_vietnam.strftime('%d/%m/%Y %H:%M')
                                })
                                
                                # Send expiry notification to user
                                try:
                                    expiry_message = f"""
⚠️ **VIP đã hết hạn!**

👤 Chào {first_name}!
👑 VIP của bạn đã hết hạn vào: {expiry_vietnam.strftime('%d/%m/%Y %H:%M')} VN

🔄 **Thay đổi:**
• Không còn verify không giới hạn
• Checkin chỉ nhận 1 xu/ngày
• Giá shop không còn ưu đãi VIP

💡 **Gia hạn VIP:**
• Sử dụng /vip để mua lại VIP
• Liên hệ admin: @meepzizhere

❓ Hỗ trợ: @meepzizhere
                                    """
                                    send_telegram_message(telegram_id, expiry_message)
                                    print(f"📤 Sent expiry notification to {telegram_id}")
                                except Exception as e:
                                    print(f"❌ Failed to send expiry notification to {telegram_id}: {e}")
                            
                            # Check if expiring within 3 days
                            elif vietnam_now <= expiry_vietnam <= three_days_later:
                                days_left = (expiry_vietnam - vietnam_now).days
                                hours_left = (expiry_vietnam - vietnam_now).seconds // 3600
                                
                                warning_users.append({
                                    'telegram_id': telegram_id,
                                    'first_name': first_name,
                                    'expiry': expiry_vietnam.strftime('%d/%m/%Y %H:%M'),
                                    'days_left': days_left,
                                    'hours_left': hours_left
                                })
                                
                        except Exception as e:
                            print(f"❌ Error processing VIP expiry for user {telegram_id}: {e}")
                    
                    print(f"✅ VIP check completed - Expired: {len(expired_users)}, Warning: {len(warning_users)}")
                    
                else:
                    print("❌ Supabase client not available")
                    send_telegram_message(chat_id, "❌ Supabase không khả dụng!")
                    return
                    
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                send_telegram_message(chat_id, f"❌ Lỗi Supabase: {str(e)}")
                return
        else:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng!")
            return
        
        # Send summary to admin
        message = f"""✅ **Kiểm tra VIP hoàn tất!**

📊 **Thống kê:**
• 👑 Tổng VIP users: {total_vip_users}
• ❌ Đã hết hạn: {len(expired_users)}
• ⚠️ Sắp hết hạn (3 ngày): {len(warning_users)}

⏰ Thời gian kiểm tra: {format_vietnam_time()}
        """
        
        if expired_users:
            message += f"\n\n❌ **Users VIP đã hết hạn:**"
            for user in expired_users[:5]:  # Show max 5
                message += f"\n• {user['first_name']} ({user['telegram_id']}) - Hết hạn: {user['expiry']}"
            if len(expired_users) > 5:
                message += f"\n• ... và {len(expired_users) - 5} user khác"
        
        if warning_users:
            message += f"\n\n⚠️ **Users VIP sắp hết hạn:**"
            for user in warning_users[:5]:  # Show max 5
                days = user['days_left']
                hours = user['hours_left']
                time_left = f"{days} ngày {hours} giờ" if days > 0 else f"{hours} giờ"
                message += f"\n• {user['first_name']} ({user['telegram_id']}) - Còn: {time_left}"
            if len(warning_users) > 5:
                message += f"\n• ... và {len(warning_users) - 5} user khác"
        
        message += f"\n\n💡 **Ghi chú:**"
        message += f"\n• Users hết hạn đã được chuyển về is_vip = False"
        message += f"\n• Đã gửi thông báo hết hạn tới các user"
        message += f"\n• Sử dụng lệnh này định kỳ để duy trì VIP chính xác"
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"❌ Error in handle_admin_check_vip: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi kiểm tra VIP: {str(e)}")

def send_vip_expiry_warnings():
    """Send VIP expiry warnings to users (3 days before expiry) - called automatically"""
    try:
        print("🔔 Checking for VIP expiry warnings...")
        
        # Get current Vietnam time
        vietnam_now = get_vietnam_time()
        three_days_later = vietnam_now + timedelta(days=3)
        
        if not SUPABASE_AVAILABLE:
            print("❌ Supabase not available for VIP warnings")
            return False
        
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            print("❌ Supabase client not available")
            return False
        
        # Get VIP users expiring within 3 days
        response = supabase.table('users').select('telegram_id, first_name, vip_expiry').eq('is_vip', True).not_.is_('vip_expiry', 'null').execute()
        vip_users = response.data if response.data else []
        
        warning_sent = 0
        
        for user in vip_users:
            try:
                telegram_id = user.get('telegram_id')
                first_name = user.get('first_name', 'User')
                vip_expiry = user.get('vip_expiry')
                
                if not vip_expiry:
                    continue
                
                # Parse expiry date
                expiry_date = datetime.fromisoformat(str(vip_expiry).replace('Z', '+00:00'))
                expiry_vietnam = expiry_date.astimezone(timezone(timedelta(hours=7)))
                
                # Check if expiring within 3 days
                if vietnam_now <= expiry_vietnam <= three_days_later:
                    days_left = (expiry_vietnam - vietnam_now).days
                    hours_left = (expiry_vietnam - vietnam_now).seconds // 3600
                    
                    # Check if we should send warning (2 times per day max)
                    today = format_vietnam_time('%Y-%m-%d')
                    warning_key = f"vip_warning_{telegram_id}_{today}"
                    
                    # Simple rate limiting using bot config
                    warnings_today = BOT_CONFIG.get(warning_key, 0)
                    if warnings_today >= 2:
                        continue  # Already sent 2 warnings today
                    
                    # Send warning message
                    time_left = f"{days_left} ngày {hours_left} giờ" if days_left > 0 else f"{hours_left} giờ"
                    
                    warning_message = f"""
⚠️ **VIP sắp hết hạn!**

👤 Chào {first_name}!
👑 VIP của bạn sẽ hết hạn sau: **{time_left}**
📅 Ngày hết hạn: {expiry_vietnam.strftime('%d/%m/%Y %H:%M')} VN

🔄 **Khi VIP hết hạn:**
• Không còn verify không giới hạn
• Checkin chỉ nhận 1 xu/ngày
• Giá shop không còn ưu đãi VIP

💡 **Gia hạn ngay:**
• Sử dụng /vip để mua thêm VIP
• Liên hệ admin: @meepzizhere

❓ Hỗ trợ: @meepzizhere
                    """
                    
                    result = send_telegram_message(telegram_id, warning_message)
                    if result:
                        warning_sent += 1
                        # Update warning count
                        BOT_CONFIG[warning_key] = warnings_today + 1
                        save_bot_config(warning_key, warnings_today + 1)
                        print(f"📤 Sent VIP warning to {telegram_id} ({warnings_today + 1}/2 today)")
                    
            except Exception as e:
                print(f"❌ Error sending VIP warning to {telegram_id}: {e}")
        
        print(f"✅ VIP warnings sent: {warning_sent}")
        return warning_sent > 0
        
    except Exception as e:
        print(f"❌ Error in send_vip_expiry_warnings: {e}")
        return False

def get_daily_stats():
    """Get daily statistics for notification"""
    try:
        total_users = 0
        total_verified = 0
        
        # Get total users from Supabase
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    # Get total users count
                    user_response = supabase.table('users').select('telegram_id', count='exact').execute()
                    total_users = user_response.count if user_response.count else 0
                    
                    # Get total verified jobs count (only completed/successful jobs)
                    verify_response = supabase.table('verification_jobs').select('job_id', count='exact').eq('status', 'completed').execute()
                    total_verified = verify_response.count if verify_response.count else 0
                    
                    print(f"📊 Daily stats - Users: {total_users}, Verified: {total_verified}")
                else:
                    print("❌ Supabase client not available for daily stats")
            except Exception as e:
                print(f"❌ Error getting daily stats from Supabase: {e}")
        
        # Fallback to SQLite if Supabase fails
        if not SUPABASE_AVAILABLE or total_users == 0:
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # Get total users
                cursor.execute('SELECT COUNT(*) FROM users')
                total_users = cursor.fetchone()[0]
                
                # Get total verified jobs (only those with result data)
                cursor.execute('SELECT COUNT(*) FROM verification_jobs WHERE result IS NOT NULL')
                total_verified = cursor.fetchone()[0]
                
                conn.close()
                print(f"📊 Daily stats (SQLite) - Users: {total_users}, Verified: {total_verified}")
            except Exception as e:
                print(f"❌ Error getting daily stats from SQLite: {e}")
        
        return {
            'total_users': total_users,
            'successful_verifications': total_verified,
            'date': format_vietnam_time()
        }
        
    except Exception as e:
        print(f"❌ Error in get_daily_stats: {e}")
        return {
            'total_users': 0,
            'successful_verifications': 0,
            'date': format_vietnam_time()
        }

def send_daily_notification():
    """Send daily notification to all users (reentrancy-safe).
    Returns: dict with success_count, failed_count, total_count"""
    try:
        global BROADCAST_IN_PROGRESS
        # Block if a broadcast is already in progress
        if BROADCAST_IN_PROGRESS:
            print("⏳ Daily notification is already running. Abort duplicate.")
            return {'success': False, 'error': 'Broadcast already in progress'}
        # EMERGENCY STOP - DỪNG NGAY LẬP TỨC
        if EMERGENCY_STOP:
            print("🚨 EMERGENCY STOP: Không gửi thông báo hằng ngày!")
            return {'success': False, 'error': 'Emergency stop activated'}
        # Cooldown: prevent multiple sends within 5 minutes
        try:
            last_sent = BOT_CONFIG.get('daily_last_sent_at')
            if last_sent:
                from datetime import datetime, timedelta
                last_dt = datetime.fromisoformat(str(last_sent))
                if datetime.now() - last_dt < timedelta(minutes=5):
                    print("⏳ Daily notification cooldown active. Abort.")
                    return {'success': False, 'error': 'Cooldown active (5 minutes)'}
        except Exception:
            pass
            
        # 🚨 NUCLEAR: Disabled maintenance check
        if False:
            print("🔧 Bot đang trong chế độ bảo trì! Không gửi thông báo hằng ngày.")
            return {'success': False, 'error': 'Bot in maintenance mode'}
            
        import traceback
        print("🔍 DEBUG: send_daily_notification function called!")
        print("🔍 DEBUG: Call stack:")
        traceback.print_stack()
        print("🌅 Sending daily notification...")
        BROADCAST_IN_PROGRESS = True
        
        # Get statistics
        stats = get_daily_stats()
        
        # Send VIP expiry warnings (2 times per day max)
        try:
            print("🔔 Sending VIP expiry warnings...")
            send_vip_expiry_warnings()
        except Exception as e:
            print(f"❌ Error sending VIP warnings: {e}")
        
        # Create notification message
        message = f"""🌅 THÔNG BÁO HẰNG NGÀY 🌅

📢 Nhắc nhở quan trọng:
• Đừng quên /checkin hoặc /diemdanh để nhận xu mỗi ngày nhé! (1 xu/ngày) 💰

📊 THỐNG KÊ HỆ THỐNG:
• 👥 Tổng số USER hiện tại: {stats['total_users']:,}
• ✅ Tổng lượt VERIFY thành công: {stats['successful_verifications']:,}

🎯 Lời khuyên:
• Hãy checkin hàng ngày để tích lũy xu (1 xu/ngày)
• Sử dụng xu để verify và nhận lợi ích từ GG Student
• VIP members được verify không giới hạn!

Chúc bạn một ngày tốt lành! 🚀

❓ Hỗ trợ: @meepzizhere"""
        
        # Get all users from Supabase
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    # Get all users with telegram_id
                    response = supabase.table('users').select('telegram_id').execute()
                    users = response.data if response.data else []
                    
                    print(f"📤 Sending daily notification to {len(users)} users...")
                    
                    success_count = 0
                    failed_count = 0
                    admin_id = 7162256181  # Admin telegram ID
                    total_users = len([u for u in users if u.get('telegram_id') != admin_id])
                    
                    for user in users:
                        try:
                            telegram_id = user.get('telegram_id')
                            if telegram_id and telegram_id != admin_id:  # Skip admin
                                if EMERGENCY_STOP:
                                    print("🚨 Emergency stop toggled mid-send. Aborting daily notification.")
                                    break
                                result = send_telegram_message(telegram_id, message)
                                if result:
                                    success_count += 1
                                else:
                                    failed_count += 1
                                # Small delay to avoid rate limiting
                                import time
                                time.sleep(0.1)
                            elif telegram_id == admin_id:
                                print(f"🚫 Skipping admin {admin_id} in daily notification to prevent loop")
                        except Exception as e:
                            print(f"❌ Error sending to user {telegram_id}: {e}")
                            failed_count += 1
                    
                    print(f"✅ Daily notification sent to {success_count}/{total_users} users (failed: {failed_count})")
                    # Save last sent time
                    try:
                        from datetime import datetime
                        BOT_CONFIG['daily_last_sent_at'] = datetime.now().isoformat()
                        save_bot_config('daily_last_sent_at', BOT_CONFIG['daily_last_sent_at'])
                    except Exception:
                        pass
                    return {
                        'success': True,
                        'success_count': success_count,
                        'failed_count': failed_count,
                        'total_count': total_users
                    }
                else:
                    print("❌ Supabase client not available for daily notification")
            except Exception as e:
                print(f"❌ Error sending daily notification via Supabase: {e}")
        
        # Fallback to SQLite
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT telegram_id FROM users')
            users = cursor.fetchall()
            conn.close()
            
            print(f"📤 Sending daily notification to {len(users)} users (SQLite)...")
            
            success_count = 0
            failed_count = 0
            admin_id = 7162256181  # Admin telegram ID
            total_users = len([u for u in users if u[0] != admin_id])
            
            for user in users:
                try:
                    telegram_id = user[0]
                    if telegram_id and telegram_id != admin_id:  # Skip admin
                        if EMERGENCY_STOP:
                            print("🚨 Emergency stop toggled mid-send. Aborting daily notification (SQLite loop).")
                            break
                        result = send_telegram_message(telegram_id, message)
                        if result:
                            success_count += 1
                        else:
                            failed_count += 1
                        # Small delay to avoid rate limiting
                        import time
                        time.sleep(0.1)
                    elif telegram_id == admin_id:
                        print(f"🚫 Skipping admin {admin_id} in daily notification to prevent loop")
                except Exception as e:
                    print(f"❌ Error sending to user {telegram_id}: {e}")
                    failed_count += 1
            
            print(f"✅ Daily notification sent to {success_count}/{total_users} users (failed: {failed_count})")
            try:
                from datetime import datetime
                BOT_CONFIG['daily_last_sent_at'] = datetime.now().isoformat()
                save_bot_config('daily_last_sent_at', BOT_CONFIG['daily_last_sent_at'])
            except Exception:
                pass
            return {
                'success': True,
                'success_count': success_count,
                'failed_count': failed_count,
                'total_count': total_users
            }
            
        except Exception as e:
            print(f"❌ Error sending daily notification via SQLite: {e}")
        return {'success': False, 'error': 'Failed to send daily notification'}
        
    except Exception as e:
        print(f"❌ Error in send_daily_notification: {e}")
        return False
    finally:
        BROADCAST_IN_PROGRESS = False

def handle_admin_daily_notification(chat_id):
    """Test daily notification for admin - chỉ test thống kê, không gửi thông báo thực sự"""
    try:
        send_telegram_message(chat_id, "🌅 Đang kiểm tra thống kê hằng ngày...")
        
        # Chỉ lấy thống kê, không gửi thông báo thực sự
        stats = get_daily_stats()
        
        if stats:
            message = f"""📊 THỐNG KÊ HỆ THỐNG (TEST):

👥 Tổng số USER hiện tại: {stats['total_users']}
✅ Tổng lượt VERIFY thành công: {stats['successful_verifications']}
📅 Ngày: {stats['date']}

⚠️ Đây chỉ là test, không gửi thông báo thực sự!"""
            send_telegram_message(chat_id, message)
        else:
            send_telegram_message(chat_id, "❌ Không thể lấy thống kê!")
            
    except Exception as e:
        print(f"❌ Error in handle_admin_daily_notification: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_config(chat_id):
    """Show bot configuration"""
    try:
        message = f"""⚙️ CẤU HÌNH BOT

📝 Tin nhắn chào mừng:
{BOT_CONFIG['welcome_message']}

💰 Giá verify: {BOT_CONFIG['verify_price']} xu
🎁 Xu checkin hàng ngày: {BOT_CONFIG['daily_bonus']} xu
🔧 Chế độ bảo trì: {'BẬT' if BOT_CONFIG['maintenance_mode'] else 'TẮT'}
📅 Cập nhật lần cuối: {BOT_CONFIG['last_updated'] or 'Chưa có'}

Sử dụng các lệnh sau để thay đổi:
• /admin setwelcome <message>
• /admin setprice <amount>
• /admin setbonus <amount>
• /admin maintenance on/off/force/status"""
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"❌ Error in handle_admin_config: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_set_welcome(chat_id, message):
    """Set welcome message"""
    try:
        # Save to Supabase instead of file
        save_bot_config('welcome_message', message)
        save_bot_config('last_updated', format_vietnam_time())
        
        send_telegram_message(chat_id, f"✅ Đã cập nhật tin nhắn chào mừng:\n\n{message}")
        
    except Exception as e:
        print(f"❌ Error in handle_admin_set_welcome: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_set_price(chat_id, amount):
    """Set verify price"""
    try:
        price = int(amount)
        if price < 0:
            send_telegram_message(chat_id, "❌ Giá verify phải >= 0!")
            return
            
        # Save to Supabase instead of file
        save_bot_config('verify_price', price)
        save_bot_config('last_updated', format_vietnam_time())
        
        send_telegram_message(chat_id, f"✅ Đã cập nhật giá verify: {price} xu")
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Giá verify phải là số nguyên!")
    except Exception as e:
        print(f"❌ Error in handle_admin_set_price: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_set_bonus(chat_id, amount):
    """Set daily bonus"""
    try:
        bonus = int(amount)
        if bonus < 0:
            send_telegram_message(chat_id, "❌ Xu checkin phải >= 0!")
            return
            
        # Save to Supabase instead of file
        save_bot_config('daily_bonus', bonus)
        save_bot_config('last_updated', format_vietnam_time())
        
        send_telegram_message(chat_id, f"✅ Đã cập nhật xu checkin hàng ngày: {bonus} xu")
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Xu checkin phải là số nguyên!")
    except Exception as e:
        print(f"❌ Error in handle_admin_set_bonus: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_maintenance(chat_id, mode):
    """Toggle verify maintenance mode with improved error handling"""
    global BOT_CONFIG, CONFIG_LOADED
    try:
        print(f"🔍 DEBUG: Admin maintenance called with mode: {mode}")
        print(f"🔍 DEBUG: Current BOT_CONFIG maintenance_mode: {BOT_CONFIG.get('maintenance_mode')}")
        print(f"🔍 DEBUG: Current BOT_CONFIG verify_maintenance: {BOT_CONFIG.get('verify_maintenance')}")
        print(f"🔍 DEBUG: Current ENV VERIFY_MAINTENANCE: {os.environ.get('VERIFY_MAINTENANCE', 'NOT_SET')}")
        
        if mode.lower() == 'on':
            # Turn ON maintenance
            BOT_CONFIG['verify_maintenance'] = True
            BOT_CONFIG['maintenance_mode'] = True
            BOT_CONFIG['last_updated'] = format_vietnam_time()
            
            # Set environment variable
            os.environ['VERIFY_MAINTENANCE'] = 'true'
            
            # Try to save to database with error handling
            try:
                save_bot_config('verify_maintenance', True)
                save_bot_config('maintenance_mode', True)
                print("✅ Saved maintenance=ON to database")
            except Exception as e:
                print(f"⚠️ Database save failed, but in-memory config updated: {e}")
            
            print(f"🔍 DEBUG: Maintenance turned ON - BOT_CONFIG: {BOT_CONFIG.get('verify_maintenance')}, ENV: {os.environ.get('VERIFY_MAINTENANCE')}")
            
            message = """🔧 **Đã BẬT chế độ bảo trì Verify!**

⚠️ Lệnh /verify hiện đã bị vô hiệu hóa
✅ Các lệnh khác vẫn hoạt động bình thường:
• /me - Xem thông tin tài khoản
• /checkin - Nhận xu hàng ngày
• /shop - Mua sắm
• /crypto - Nạp crypto
• /lsgd - Lịch sử giao dịch

📢 User sẽ nhận thông báo bảo trì khi dùng /verify
🔗 Kênh thông báo: https://t.me/channel_sheerid_vip_bot"""
            send_telegram_message(chat_id, message)
            
        elif mode.lower() == 'off':
            # Turn OFF maintenance - NUCLEAR DISABLE
            print("🚨 NUCLEAR: Completely disabling maintenance...")
            print(f"🔍 DEBUG: BEFORE - maintenance_mode: {BOT_CONFIG.get('maintenance_mode')}")
            print(f"🔍 DEBUG: BEFORE - verify_maintenance: {BOT_CONFIG.get('verify_maintenance')}")
            print(f"🔍 DEBUG: BEFORE - ENV: {os.environ.get('VERIFY_MAINTENANCE', 'NOT_SET')}")
            
            # NUCLEAR: Clear everything multiple times
            for i in range(5):
                BOT_CONFIG['verify_maintenance'] = False
                BOT_CONFIG['maintenance_mode'] = False
                print(f"  🔄 Nuclear clear attempt {i+1}")
            
            BOT_CONFIG['last_updated'] = format_vietnam_time()
            
            # Clear ALL environment variables related to maintenance
            env_keys_to_clear = []
            for key in list(os.environ.keys()):
                if 'MAINTENANCE' in key.upper() or 'VERIFY' in key.upper():
                    env_keys_to_clear.append(key)
            
            for key in env_keys_to_clear:
                try:
                    del os.environ[key]
                    print(f"  ✅ Cleared env var: {key}")
                except:
                    print(f"  ⚠️ Could not clear env var: {key}")
            
            # Force save to database multiple times with different approaches
            for i in range(5):
                try:
                    save_bot_config('verify_maintenance', False)
                    save_bot_config('maintenance_mode', False)
                    print(f"  ✅ Nuclear save attempt {i+1} successful")
                    break
                except Exception as e:
                    print(f"  ❌ Nuclear save attempt {i+1} failed: {e}")
            
            # Force reload config multiple times
            for i in range(3):
                try:
                    CONFIG_LOADED = False
                    load_bot_config(force_reload=True)
                    print(f"  ✅ Config reload attempt {i+1} successful")
                    break
                except Exception as e:
                    print(f"  ❌ Config reload attempt {i+1} failed: {e}")
            
            print(f"🔍 DEBUG: AFTER - maintenance_mode: {BOT_CONFIG.get('maintenance_mode')}")
            print(f"🔍 DEBUG: AFTER - verify_maintenance: {BOT_CONFIG.get('verify_maintenance')}")
            print(f"🔍 DEBUG: AFTER - ENV: {os.environ.get('VERIFY_MAINTENANCE', 'NOT_SET')}")
            print(f"🔍 DEBUG: is_maintenance_mode() returns: {is_maintenance_mode()}")
            
            message = """🚨 **NUCLEAR TẮT bảo trì thành công!**

✅ Đã xóa TẤT CẢ trạng thái maintenance (5 lần)
✅ Đã clear TẤT CẢ environment variables
✅ Đã reload config hoàn toàn (3 lần)
🔄 Lệnh /verify đã được kích hoạt lại
👥 User có thể sử dụng verify bình thường

🔍 Debug: maintenance_mode = {BOT_CONFIG.get('maintenance_mode')}
🔍 Debug: verify_maintenance = {BOT_CONFIG.get('verify_maintenance')}"""
            send_telegram_message(chat_id, message)
            
        elif mode.lower() == 'force':
            # FORCE turn off maintenance - nuclear option
            print("🚨 FORCE turning off maintenance...")
            
            # Clear everything
            BOT_CONFIG['verify_maintenance'] = False
            BOT_CONFIG['maintenance_mode'] = False
            BOT_CONFIG['last_updated'] = format_vietnam_time()
            
            # Clear all maintenance-related environment variables
            maintenance_env_vars = [key for key in os.environ.keys() if 'MAINTENANCE' in key.upper()]
            for key in maintenance_env_vars:
                del os.environ[key]
                print(f"  Cleared env var: {key}")
            
            # Force save to database multiple times
            for i in range(3):
                try:
                    save_bot_config('verify_maintenance', False)
                    save_bot_config('maintenance_mode', False)
                    print(f"  ✅ Force save attempt {i+1} successful")
                    break
                except Exception as e:
                    print(f"  ❌ Force save attempt {i+1} failed: {e}")
            
            # Force reload config
            CONFIG_LOADED = False
            load_bot_config(force_reload=True)
            
            message = """🚨 **FORCE TẮT bảo trì thành công!**

✅ Đã xóa tất cả trạng thái maintenance
✅ Đã reload config hoàn toàn
🔄 Verify function đã được kích hoạt"""
            send_telegram_message(chat_id, message)
            
        elif mode.lower() == 'status':
            # Check current maintenance status with detailed info
            env_maintenance = os.environ.get('VERIFY_MAINTENANCE', 'false').lower() == 'true'
            config_verify_maintenance = BOT_CONFIG.get('verify_maintenance', False)
            config_maintenance_mode = BOT_CONFIG.get('maintenance_mode', False)
            
            any_maintenance = env_maintenance or config_verify_maintenance or config_maintenance_mode
            
            status_icon = "🔧" if any_maintenance else "✅"
            status_text = "BẬT" if any_maintenance else "TẮT"
            
            message = f"""📊 **Trạng thái Bảo trì Chi tiết**

{status_icon} **Trạng thái tổng:** {status_text}

🔧 **Chi tiết từng loại:**
• Environment VERIFY_MAINTENANCE: {os.environ.get('VERIFY_MAINTENANCE', 'not set')}
• BOT_CONFIG verify_maintenance: {config_verify_maintenance}
• BOT_CONFIG maintenance_mode: {config_maintenance_mode}
• Last Updated: {BOT_CONFIG.get('last_updated', 'N/A')}

💡 **Lệnh khả dụng:**
• /admin maintenance on - Bật bảo trì
• /admin maintenance off - Tắt bảo trì  
• /admin maintenance force - FORCE tắt (nuclear option)
• /admin maintenance status - Xem trạng thái"""
            send_telegram_message(chat_id, message)
            
        else:
            send_telegram_message(chat_id, "❌ Sử dụng: /admin maintenance on/off/force/status")
            
    except Exception as e:
        print(f"❌ Error in handle_admin_maintenance: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_broadcast(chat_id, message):
    """Broadcast message to all users"""
    try:
        global BROADCAST_IN_PROGRESS
        if BROADCAST_IN_PROGRESS:
            send_telegram_message(chat_id, "⏳ Hệ thống đang gửi broadcast khác. Vui lòng thử lại sau.")
            return
        BROADCAST_IN_PROGRESS = True
        # EMERGENCY STOP - DỪNG NGAY LẬP TỨC
        if EMERGENCY_STOP:
            print("🚨 EMERGENCY STOP: Không gửi broadcast!")
            send_telegram_message(chat_id, "🚨 Bot đã được dừng khẩn cấp!")
            return
            
        # Check maintenance mode
        if False:  # 🚨 NUCLEAR: Disabled maintenance check
            send_telegram_message(chat_id, "🔧 Bot đang trong chế độ bảo trì! Không thể gửi thông báo.")
            return
            
        send_telegram_message(chat_id, "📢 Đang gửi thông báo đến tất cả user...")
        
        # Get all users from Supabase
        print(f"🔍 DEBUG: SUPABASE_AVAILABLE = {SUPABASE_AVAILABLE}")
        if SUPABASE_AVAILABLE:
            try:
                print("🔍 DEBUG: Importing supabase_client...")
                from supabase_client import get_supabase_client
                print("🔍 DEBUG: Getting supabase client...")
                supabase = get_supabase_client()
                print(f"🔍 DEBUG: Supabase client = {supabase is not None}")
                if supabase:
                    print("🔍 DEBUG: Starting pagination...")
                    # Get ALL users without limit - use pagination if needed
                    all_users = []
                    page_size = 1000  # Supabase default limit is 1000
                    offset = 0
                    
                    while True:
                        response = supabase.table('users').select('telegram_id').range(offset, offset + page_size - 1).execute()
                        batch_users = response.data if response.data else []
                        
                        if not batch_users:
                            break
                            
                        all_users.extend(batch_users)
                        print(f"📊 Loaded {len(batch_users)} users (total: {len(all_users)})")
                        
                        if len(batch_users) < page_size:
                            break  # Last page
                            
                        offset += page_size
                    
                    users = all_users
                    print(f"📢 Broadcasting to {len(users)} total users")
                    
                    # Debug: Check users data structure
                    print(f"🔍 DEBUG: First user sample: {users[0] if users else 'No users'}")
                    print(f"🔍 DEBUG: Users type: {type(users)}")
                    
                    success_count = 0
                    failed_count = 0
                    skipped_count = 0
                    admin_ids = [7162256181]  # Admin telegram IDs to skip
                    total_users = len(users)
                    
                    print(f"🚀 Starting broadcast loop for {total_users} users...")
                    print(f"🔍 DEBUG: About to enter for loop...")
                    
                    # Test first user before loop
                    if users:
                        test_user = users[0]
                        test_telegram_id = test_user.get('telegram_id') if test_user else None
                        print(f"🧪 TEST: First user telegram_id: {test_telegram_id}")
                    
                    loop_started = False
                    
                    for i, user in enumerate(users, 1):
                        if not loop_started:
                            print(f"🔥 LOOP STARTED! Processing user {i}")
                            loop_started = True
                            
                        try:
                            print(f"🔍 DEBUG: Processing user {i}: {user}")
                            telegram_id = user.get('telegram_id') if user else None
                            print(f"🔍 DEBUG: Extracted telegram_id: {telegram_id}")
                            
                            if not telegram_id:
                                print(f"⚠️ SKIPPING user {i} - no telegram_id: {user}")
                                skipped_count += 1
                                continue
                            
                            # Skip admin to prevent loop
                            if int(telegram_id) in admin_ids:
                                print(f"🚫 SKIPPING admin {telegram_id} to prevent loop")
                                skipped_count += 1
                                continue
                            
                            if EMERGENCY_STOP:
                                print("🚨 Emergency stop toggled mid-send. Aborting broadcast.")
                                break
                            
                            print(f"📤 SENDING to user {i}/{total_users}: {telegram_id}")
                            
                            try:
                                result = send_telegram_message(telegram_id, f"📢 THÔNG BÁO TỪ ADMIN:\n\n{message}")
                                print(f"📤 SEND RESULT for {telegram_id}: {result}")
                                
                                if result:
                                    success_count += 1
                                    print(f"✅ SUCCESS! Count now: {success_count}")
                                else:
                                    failed_count += 1
                                    print(f"❌ FAILED to send to {telegram_id}")
                                    
                            except Exception as send_error:
                                failed_count += 1
                                print(f"💥 SEND ERROR for {telegram_id}: {send_error}")
                            
                            import time
                            time.sleep(0.03)  # Fast rate limiting
                            
                            # Progress tracking every 50 users
                            if i % 50 == 0:
                                progress_msg = f"📊 Tiến độ: {i}/{total_users}\n✅ Thành công: {success_count}\n❌ Thất bại: {failed_count}\n⏭️ Bỏ qua: {skipped_count}"
                                send_telegram_message(chat_id, progress_msg)
                                print(f"📊 PROGRESS: {progress_msg}")
                        except Exception as e:
                            failed_count += 1
                            print(f"💥 LOOP ERROR for user {i}: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
                    
                    print(f"🏁 BROADCAST COMPLETED! Final results:")
                    print(f"📊 Total users: {total_users}")
                    print(f"✅ Successful: {success_count}")
                    print(f"❌ Failed: {failed_count}")
                    print(f"⏭️ Skipped: {skipped_count}")
                    
                    # Send detailed summary to admin
                    summary_msg = f"""🎉 BROADCAST HOÀN THÀNH!

📊 Tổng số users: {total_users}
✅ Gửi thành công: {success_count}
❌ Gửi thất bại: {failed_count}
⏭️ Bỏ qua (admin): {skipped_count}

📈 Tỷ lệ thành công: {(success_count/(total_users-skipped_count)*100):.1f}%""" if (total_users - skipped_count) > 0 else "0%"
                    
                    send_telegram_message(chat_id, summary_msg)
                    return
            except Exception as e:
                print(f"💥 MAJOR SUPABASE ERROR: {e}")
                import traceback
                traceback.print_exc()
                print("🔄 Falling back to SQLite...")
        else:
            print("⚠️ SUPABASE_AVAILABLE is False, using SQLite fallback")
        
        # Fallback to SQLite
        print("🔍 DEBUG: Using SQLite fallback for broadcast")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT telegram_id FROM users')
        users = cursor.fetchall()
        conn.close()
        print(f"📊 SQLite: Loaded {len(users)} users from local database")
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        admin_ids = [7162256181]  # Admin telegram IDs to skip
        total_users = len(users)
        
        for i, user in enumerate(users, 1):
            try:
                telegram_id = user[0]
                
                if not telegram_id:
                    skipped_count += 1
                    continue
                
                # Skip admin to prevent loop
                if int(telegram_id) in admin_ids:
                    print(f"🚫 Skipping admin {telegram_id} to prevent loop")
                    skipped_count += 1
                    continue
                
                if EMERGENCY_STOP:
                    print("🚨 Emergency stop toggled mid-send. Aborting broadcast (SQLite loop).")
                    break
                
                try:
                    result = send_telegram_message(telegram_id, f"📢 THÔNG BÁO TỪ ADMIN:\n\n{message}")
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as send_error:
                    failed_count += 1
                    print(f"❌ Error sending to user {telegram_id}: {send_error}")
                
                import time
                time.sleep(0.1)  # Rate limiting
                
                # Progress tracking every 50 users
                if i % 50 == 0:
                    progress_msg = f"📊 Tiến độ: {i}/{total_users}\n✅ Thành công: {success_count}\n❌ Thất bại: {failed_count}\n⏭️ Bỏ qua: {skipped_count}"
                    send_telegram_message(chat_id, progress_msg)
                    
            except Exception as e:
                failed_count += 1
                print(f"❌ Error processing user: {e}")
        
        # Send detailed summary
        summary_msg = f"""🎉 BROADCAST HOÀN THÀNH!

📊 Tổng số users: {total_users}
✅ Gửi thành công: {success_count}
❌ Gửi thất bại: {failed_count}
⏭️ Bỏ qua (admin): {skipped_count}

📈 Tỷ lệ thành công: {(success_count/(total_users-skipped_count)*100):.1f}%""" if (total_users - skipped_count) > 0 else "0%"
        
        send_telegram_message(chat_id, summary_msg)
        
    except Exception as e:
        print(f"❌ Error in handle_admin_broadcast: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")
    finally:
        BROADCAST_IN_PROGRESS = False

def handle_admin_broadcast_vip(chat_id, message):
    """Broadcast message to VIP users only"""
    try:
        global BROADCAST_IN_PROGRESS
        if BROADCAST_IN_PROGRESS:
            send_telegram_message(chat_id, "⏳ Hệ thống đang gửi broadcast khác. Vui lòng thử lại sau.")
            return
        BROADCAST_IN_PROGRESS = True
        # EMERGENCY STOP - DỪNG NGAY LẬP TỨC
        if EMERGENCY_STOP:
            print("🚨 EMERGENCY STOP: Không gửi VIP broadcast!")
            send_telegram_message(chat_id, "🚨 Bot đã được dừng khẩn cấp!")
            return
            
        # Check maintenance mode
        if False:  # 🚨 NUCLEAR: Disabled maintenance check
            send_telegram_message(chat_id, "🔧 Bot đang trong chế độ bảo trì! Không thể gửi thông báo.")
            return
            
        send_telegram_message(chat_id, "👑 Đang gửi thông báo đến VIP user...")
        
        # Get VIP users from Supabase
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    # Get ALL VIP users without limit - use pagination if needed
                    all_vip_users = []
                    page_size = 1000  # Supabase default limit is 1000
                    offset = 0
                    
                    while True:
                        response = supabase.table('users').select('telegram_id').eq('is_vip', True).range(offset, offset + page_size - 1).execute()
                        batch_users = response.data if response.data else []
                        
                        if not batch_users:
                            break
                            
                        all_vip_users.extend(batch_users)
                        print(f"👑 Loaded {len(batch_users)} VIP users (total: {len(all_vip_users)})")
                        
                        if len(batch_users) < page_size:
                            break  # Last page
                            
                        offset += page_size
                    
                    users = all_vip_users
                    print(f"👑 Broadcasting to {len(users)} total VIP users")
                    
                    success_count = 0
                    admin_id = 7162256181  # Admin telegram ID
                    for user in users:
                        try:
                            telegram_id = user.get('telegram_id')
                            if telegram_id and telegram_id != admin_id:  # Skip admin
                                if EMERGENCY_STOP:
                                    print("🚨 Emergency stop toggled mid-send. Aborting VIP broadcast.")
                                    break
                                send_telegram_message(telegram_id, f"👑 THÔNG BÁO VIP:\n\n{message}")
                                success_count += 1
                                import time
                                time.sleep(0.1)  # Rate limiting
                            elif telegram_id == admin_id:
                                print(f"🚫 Skipping admin {admin_id} in VIP broadcast to prevent loop")
                        except Exception as e:
                            print(f"❌ Error sending to VIP user {telegram_id}: {e}")
                    
                    send_telegram_message(chat_id, f"✅ Đã gửi thông báo đến {success_count} VIP user!")
                    return
            except Exception as e:
                print(f"❌ Supabase error: {e}")
        
        # Fallback to SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT telegram_id FROM users WHERE is_vip = 1')
        users = cursor.fetchall()
        conn.close()
        
        success_count = 0
        admin_id = 7162256181  # Admin telegram ID
        for user in users:
            try:
                telegram_id = user[0]
                if telegram_id and telegram_id != admin_id:  # Skip admin
                    if EMERGENCY_STOP:
                        print("🚨 Emergency stop toggled mid-send. Aborting VIP broadcast (SQLite loop).")
                        break
                    send_telegram_message(telegram_id, f"👑 THÔNG BÁO VIP:\n\n{message}")
                    success_count += 1
                    import time
                    time.sleep(0.1)  # Rate limiting
                elif telegram_id == admin_id:
                    print(f"🚫 Skipping admin {admin_id} in VIP broadcast to prevent loop")
            except Exception as e:
                print(f"❌ Error sending to VIP user {telegram_id}: {e}")
        
        send_telegram_message(chat_id, f"✅ Đã gửi thông báo đến {success_count} VIP user!")
        
    except Exception as e:
        print(f"❌ Error in handle_admin_broadcast_vip: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")
    finally:
        BROADCAST_IN_PROGRESS = False

def handle_admin_transactions(chat_id):
    """Show recent payment transactions (deposits, refunds, etc.)"""
    try:
        # Get recent payment transactions from Supabase
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    # Filter for payment-related transactions only
                    response = supabase.table('transactions').select('*').in_('type', ['deposit', 'refund', 'admin_add', 'admin_set', 'checkin', 'admin_vip']).order('created_at', desc=True).limit(20).execute()
                    transactions = response.data if response.data else []
                    
                    if not transactions:
                        send_telegram_message(chat_id, "📊 Chưa có giao dịch chuyển tiền nào")
                        return
                    
                    message = "💰 GIAO DỊCH CHUYỂN TIỀN GẦN ĐÂY:\n\n"
                    
                    for i, tx in enumerate(transactions, 1):
                        amount = tx.get('amount', 0)
                        coins = tx.get('coins', 0)
                        tx_type = tx.get('type', 'unknown')
                        description = tx.get('description', 'N/A')
                        created_at = tx.get('created_at', 'N/A')
                        status = tx.get('status', 'completed')
                        
                        # Format amount and coins
                        if amount > 0:
                            amount_str = f"+{amount:,} VNĐ"
                        else:
                            amount_str = f"{amount:,} VNĐ"
                        
                        if coins > 0:
                            coins_str = f"+{coins} xu"
                        else:
                            coins_str = f"{coins} xu"
                        
                        # Transaction type emoji
                        type_emoji = {
                            'deposit': '💳',
                            'refund': '↩️',
                            'admin_add': '➕',
                            'admin_set': '⚙️',
                            'checkin': '🎁',
                            'admin_vip': '👑'
                        }.get(tx_type, '❓')
                        
                        # Status emoji
                        status_emoji = '✅' if status == 'completed' else '⏳' if status == 'pending' else '❌'
                        
                        message += f"{i}. {type_emoji} {tx_type.upper()}\n"
                        message += f"   💰 {amount_str} | 🪙 {coins_str}\n"
                        message += f"   📝 {description}\n"
                        message += f"   {status_emoji} {status.upper()} | ⏰ {created_at[:16]}\n\n"
                    
                    send_telegram_message(chat_id, message)
                    return
            except Exception as e:
                print(f"❌ Supabase error: {e}")
        
        # Fallback to SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT amount, coins, type, description, created_at, status
            FROM transactions 
            WHERE type IN ('deposit', 'refund', 'admin_add', 'admin_set', 'checkin', 'admin_vip')
            ORDER BY created_at DESC 
            LIMIT 20
        ''')
        transactions = cursor.fetchall()
        conn.close()
        
        if not transactions:
            send_telegram_message(chat_id, "📊 Chưa có giao dịch chuyển tiền nào")
            return
        
        message = "💰 GIAO DỊCH CHUYỂN TIỀN GẦN ĐÂY:\n\n"
        
        for i, tx in enumerate(transactions, 1):
            amount, coins, tx_type, description, created_at, status = tx
            
            # Format amount and coins
            if amount > 0:
                amount_str = f"+{amount:,} VNĐ"
            else:
                amount_str = f"{amount:,} VNĐ"
            
            if coins > 0:
                coins_str = f"+{coins} xu"
            else:
                coins_str = f"{coins} xu"
            
            # Transaction type emoji
            type_emoji = {
                'deposit': '💳',
                'refund': '↩️',
                'admin_add': '➕',
                'admin_set': '⚙️',
                'checkin': '🎁',
                'admin_vip': '👑'
            }.get(tx_type, '❓')
            
            # Status emoji
            status_emoji = '✅' if status == 'completed' else '⏳' if status == 'pending' else '❌'
            
            message += f"{i}. {type_emoji} {tx_type.upper()}\n"
            message += f"   💰 {amount_str} | 🪙 {coins_str}\n"
            message += f"   📝 {description}\n"
            message += f"   {status_emoji} {status.upper()} | ⏰ {created_at[:16]}\n\n"
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"❌ Error in handle_admin_transactions: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_refund(chat_id, telegram_id, amount):
    """Refund coins to user"""
    try:
        user_id = int(telegram_id)
        refund_amount = int(amount)
        
        if refund_amount <= 0:
            send_telegram_message(chat_id, "❌ Số xu hoàn phải > 0!")
            return
        
        # Get user from Supabase
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    # Get user
                    user_response = supabase.table('users').select('*').eq('telegram_id', user_id).execute()
                    if not user_response.data:
                        send_telegram_message(chat_id, f"❌ Không tìm thấy user với ID: {user_id}")
                        return
                    
                    user = user_response.data[0]
                    current_coins = user.get('coins', 0)
                    new_coins = current_coins + refund_amount
                    
                    # Update coins
                    supabase.table('users').update({'coins': new_coins}).eq('telegram_id', user_id).execute()
                    
                    # Add transaction record
                    supabase.table('transactions').insert({
                        'user_id': user.get('id'),
                        'amount': refund_amount,
                        'type': 'refund',
                        'description': f'Admin hoàn xu: {refund_amount} xu',
                        'status': 'completed',
                        'created_at': datetime.now().isoformat()
                    }).execute()
                    
                    send_telegram_message(chat_id, f"✅ Đã hoàn {refund_amount} xu cho user {user_id}\n💰 Số xu hiện tại: {new_coins}")
                    
                    # Notify user
                    send_telegram_message(user_id, f"💰 Bạn đã được hoàn {refund_amount} xu từ admin!\n💰 Số xu hiện tại: {new_coins}")
                    return
            except Exception as e:
                print(f"❌ Supabase error: {e}")
        
        # Fallback to SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get user
        cursor.execute('SELECT id, coins FROM users WHERE telegram_id = ?', (user_id,))
        user = cursor.fetchone()
        if not user:
            send_telegram_message(chat_id, f"❌ Không tìm thấy user với ID: {user_id}")
            conn.close()
            return
        
        db_user_id = user[0]
        current_coins = user[1]
        new_coins = current_coins + refund_amount
        
        # Update coins
        cursor.execute('UPDATE users SET coins = ? WHERE telegram_id = ?', (new_coins, user_id))
        
        # Add transaction record
        cursor.execute('''
            INSERT INTO transactions (user_id, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (db_user_id, refund_amount, 'refund', f'Admin hoàn xu: {refund_amount} xu', datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        send_telegram_message(chat_id, f"✅ Đã hoàn {refund_amount} xu cho user {user_id}\n💰 Số xu hiện tại: {new_coins}")
        
        # Notify user
        send_telegram_message(user_id, f"💰 Bạn đã được hoàn {refund_amount} xu từ admin!\n💰 Số xu hiện tại: {new_coins}")
        
    except ValueError:
        send_telegram_message(chat_id, "❌ ID user và số xu phải là số nguyên!")
    except Exception as e:
        print(f"❌ Error in handle_admin_refund: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_clear_users(chat_id):
    """Clear all users for admin"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear all data
    cursor.execute('DELETE FROM users')
    cursor.execute('DELETE FROM verification_jobs')
    cursor.execute('DELETE FROM transactions')
    
    # Reset auto increment
    cursor.execute('DELETE FROM sqlite_sequence WHERE name IN ("users", "verification_jobs", "transactions")')
    
    conn.commit()
    conn.close()
    
    send_telegram_message(chat_id, "✅ Đã xóa toàn bộ user và dữ liệu!")
def handle_admin_add_user(chat_id, telegram_id, username, first_name, last_name=""):
    """Add new user for admin"""
    try:
        telegram_id = int(telegram_id)
        
        # Check if user exists first
        user = None
        if SUPABASE_AVAILABLE:
            print(f"🔄 Using Supabase: Checking if user exists: {telegram_id}")
            try:
                from supabase_client import get_user_by_telegram_id
                user = get_user_by_telegram_id(str(telegram_id))
                if user:
                    print(f"✅ User already exists in Supabase: {user}")
                    send_telegram_message(chat_id, f"❌ User với ID {telegram_id} đã tồn tại!")
                    return
                else:
                    print(f"✅ User {telegram_id} not found in Supabase, can create new")
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                print("🔄 Falling back to SQLite")
        
        if not SUPABASE_AVAILABLE or not user:
            # Fallback to SQLite check
            print(f"🔄 Fallback: Checking user in SQLite: {telegram_id}")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            if cursor.fetchone():
                send_telegram_message(chat_id, f"❌ User với ID {telegram_id} đã tồn tại!")
                conn.close()
                return
            conn.close()
        
        # Add user
        if SUPABASE_AVAILABLE:
            # Add to Supabase
            print(f"🔄 Using Supabase: Adding user: {telegram_id}")
            try:
                from supabase_client import create_user
                user_data = create_user(telegram_id, username, first_name, last_name)
                if user_data:
                    print(f"✅ User added to Supabase: {user_data}")
                else:
                    print(f"❌ Failed to add user to Supabase")
                    send_telegram_message(chat_id, f"❌ Lỗi thêm user vào Supabase!")
                    return
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                send_telegram_message(chat_id, f"❌ Lỗi thêm user: {str(e)}")
                return
        else:
            # Fallback to SQLite
            print(f"🔄 Fallback: Adding user to SQLite: {telegram_id}")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Add user
            cursor.execute('''
                INSERT INTO users (telegram_id, username, first_name, last_name, coins, is_vip)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (telegram_id, username, first_name, last_name, 0, False))
            
            conn.commit()
            conn.close()
        
        message = f"✅ Đã thêm user mới:\nID: `{telegram_id}`\nUsername: @{username}\nTên: {first_name} {last_name}"
        send_telegram_message(chat_id, message)
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Telegram ID phải là số!")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_delete_user(chat_id, telegram_id):
    """Delete user for admin"""
    try:
        telegram_id = int(telegram_id)
        
        # Try to get user from Supabase first
        user = None
        if SUPABASE_AVAILABLE:
            print(f"🔄 Using Supabase: Getting user for deletion: {telegram_id}")
            try:
                from supabase_client import get_user_by_telegram_id
                user = get_user_by_telegram_id(str(telegram_id))
                if user:
                    print(f"✅ Found user in Supabase: {user}")
                else:
                    print(f"❌ User {telegram_id} not found in Supabase")
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                print("🔄 Falling back to SQLite")
        
        if not user:
            # Fallback to SQLite
            print(f"🔄 Fallback: Getting user from SQLite: {telegram_id}")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute('SELECT id, username, first_name FROM users WHERE telegram_id = ?', (telegram_id,))
            user_data = cursor.fetchone()
            conn.close()
            
            if not user_data:
                send_telegram_message(chat_id, f"❌ Không tìm thấy user với ID {telegram_id}!")
                return
            
            user_id, username, first_name = user_data
        else:
            # User from Supabase
            user_id = user.get('id')
            username = user.get('username', 'N/A')
            first_name = user.get('first_name', 'N/A')
        
        # Delete user and related data
        if SUPABASE_AVAILABLE and user:
            # Delete from Supabase
            print(f"🔄 Using Supabase: Deleting user: {telegram_id}")
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    # Delete related data first
                    supabase.table('transactions').delete().eq('user_id', user_id).execute()
                    supabase.table('verification_jobs').delete().eq('user_id', user_id).execute()
                    
                    # Delete user
                    response = supabase.table('users').delete().eq('telegram_id', str(telegram_id)).execute()
                    
                    if response.data:
                        print(f"✅ User deleted from Supabase: {telegram_id}")
                    else:
                        print(f"❌ Failed to delete user from Supabase")
                        send_telegram_message(chat_id, f"❌ Lỗi xóa user trong Supabase!")
                        return
                else:
                    print(f"❌ Supabase client not available")
                    send_telegram_message(chat_id, f"❌ Lỗi kết nối Supabase!")
                    return
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                send_telegram_message(chat_id, f"❌ Lỗi xóa user: {str(e)}")
                return
        else:
            # Fallback to SQLite
            print(f"🔄 Fallback: Deleting user from SQLite: {telegram_id}")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Delete user and related data
            cursor.execute('DELETE FROM verification_jobs WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM users WHERE telegram_id = ?', (telegram_id,))
            
            conn.commit()
            conn.close()
        
        message = f"✅ Đã xóa user:\nID: `{telegram_id}`\nUsername: @{username}\nTên: {first_name}"
        send_telegram_message(chat_id, message)
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Telegram ID phải là số!")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_set_coins(chat_id, telegram_id, amount, reason=""):
    """Set coins for user for admin"""
    try:
        telegram_id = int(telegram_id)
        amount = int(amount)
        
        # Try to get user from Supabase first
        user = None
        if SUPABASE_AVAILABLE:
            print(f"🔄 Using Supabase: Getting user for coins update: {telegram_id}")
            try:
                from supabase_client import get_user_by_telegram_id
                user = get_user_by_telegram_id(str(telegram_id))
                if user:
                    print(f"✅ Found user in Supabase: {user}")
                else:
                    print(f"❌ User {telegram_id} not found in Supabase")
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                print("🔄 Falling back to SQLite")
        
        if not user:
            # Fallback to SQLite
            print(f"🔄 Fallback: Getting user from SQLite: {telegram_id}")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute('SELECT id, username, first_name, coins FROM users WHERE telegram_id = ?', (telegram_id,))
            user_data = cursor.fetchone()
            conn.close()
            
            if not user_data:
                send_telegram_message(chat_id, f"❌ Không tìm thấy user với ID {telegram_id}!")
                return
            
            user_id, username, first_name, old_coins = user_data
        else:
            # User from Supabase
            user_id = user.get('id')
            username = user.get('username', 'N/A')
            first_name = user.get('first_name', 'N/A')
            old_coins = user.get('coins', 0)
        
        # Update coins
        if SUPABASE_AVAILABLE and user:
            # Update in Supabase
            print(f"🔄 Using Supabase: Updating coins for user: {telegram_id}")
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    response = supabase.table('users').update({
                        'coins': amount,
                        'updated_at': datetime.now().isoformat()
                    }).eq('telegram_id', str(telegram_id)).execute()
                    
                    if response.data:
                        # Add transaction record
                        description = f'Admin set coins: {old_coins} -> {amount}'
                        if reason:
                            description += f' | Lý do: {reason}'
                        transaction_data = {
                            'user_id': user_id,
                            'type': 'admin_set',
                            'amount': (amount - old_coins) * 1000,  # VNĐ
                            'coins': amount - old_coins,
                            'description': description,
                            'status': 'completed',
                            'created_at': datetime.now().isoformat()
                        }
                        supabase.table('transactions').insert(transaction_data).execute()
                        print(f"✅ Coins updated in Supabase for user {telegram_id}")
                    else:
                        print(f"❌ Failed to update coins in Supabase")
                        send_telegram_message(chat_id, f"❌ Lỗi cập nhật coins trong Supabase!")
                        return
                else:
                    print(f"❌ Supabase client not available")
                    send_telegram_message(chat_id, f"❌ Lỗi kết nối Supabase!")
                    return
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                send_telegram_message(chat_id, f"❌ Lỗi cập nhật coins: {str(e)}")
                return
        else:
            # Fallback to SQLite
            print(f"🔄 Fallback: Updating coins in SQLite: {telegram_id}")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Update coins
            cursor.execute('UPDATE users SET coins = ? WHERE telegram_id = ?', (amount, telegram_id))
            
            # Add transaction record
            description = f'Admin set coins: {old_coins} -> {amount}'
            if reason:
                description += f' | Lý do: {reason}'
            cursor.execute('''
                INSERT INTO transactions (user_id, type, amount, description)
                VALUES (?, ?, ?, ?)
            ''', (user_id, 'admin_set', amount - old_coins, description))
            
            conn.commit()
            conn.close()
        
        message = f"✅ Đã cập nhật xu cho user:\nID: `{telegram_id}`\nUsername: @{username}\nTên: {first_name}\nXu cũ: {old_coins}\nXu mới: {amount}"
        if reason:
            message += f"\n📝 Lý do: {reason}"
        send_telegram_message(chat_id, message)
        
        # Send notification to user
        try:
            coin_change = amount - old_coins
            if coin_change > 0:
                user_message = f"""💰 **BẠN ĐÃ ĐƯỢC ADMIN CỘNG XU**

🆔 User ID: `{telegram_id}`
👤 Tên: {first_name}
📈 Thay đổi: +{coin_change} xu
🪙 Xu cũ: {old_coins} xu
🪙 Xu mới: {amount} xu

---
_SheerID VIP Bot_"""
            elif coin_change < 0:
                user_message = f"""💰 **BẠN ĐÃ BỊ ADMIN TRỪ XU**

🆔 User ID: `{telegram_id}`
👤 Tên: {first_name}
📉 Thay đổi: {coin_change} xu
🪙 Xu cũ: {old_coins} xu
🪙 Xu mới: {amount} xu

---
_SheerID VIP Bot_"""
            else:
                user_message = f"""💰 **ADMIN ĐÃ SET XU CHO BẠN**

🆔 User ID: `{telegram_id}`
👤 Tên: {first_name}
🪙 Xu: {amount} xu

---
_SheerID VIP Bot_"""
            if reason:
                user_message = user_message.replace("\n---", f"\n📝 Lý do: {reason}\n---")
            
            send_telegram_message(telegram_id, user_message)
            print(f"✅ Sent coin notification to user {telegram_id}")
        except Exception as e:
            print(f"❌ Failed to send coin notification to user {telegram_id}: {e}")
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Telegram ID và amount phải là số!")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_set_vip_days(chat_id, telegram_id, days):
    """Set VIP status for user for admin with number of days"""
    try:
        telegram_id = int(telegram_id)
        
        # Try to get user from Supabase first
        user = None
        if SUPABASE_AVAILABLE:
            print(f"🔄 Using Supabase: Getting user for VIP update: {telegram_id}")
            try:
                from supabase_client import get_user_by_telegram_id
                user = get_user_by_telegram_id(str(telegram_id))
                if user:
                    print(f"✅ Found user in Supabase: {user}")
                else:
                    print(f"❌ User {telegram_id} not found in Supabase")
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                print("🔄 Falling back to SQLite")
        
        if not user:
            # Fallback to SQLite
            print(f"🔄 Fallback: Getting user from SQLite: {telegram_id}")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute('SELECT id, username, first_name, last_name FROM users WHERE telegram_id = ?', (telegram_id,))
            user_data = cursor.fetchone()
            conn.close()
            
            if not user_data:
                send_telegram_message(chat_id, f"❌ Không tìm thấy user với ID {telegram_id}!")
                return
            
            user_id, username, first_name, last_name = user_data
        else:
            # User from Supabase
            user_id = user.get('id')
            username = user.get('username', 'N/A')
            first_name = user.get('first_name', 'N/A')
            last_name = user.get('last_name', 'N/A')
        
        # Calculate expiry date - Use Vietnam timezone (UTC+7)
        from datetime import datetime, timedelta, timezone
        vietnam_tz = timezone(timedelta(hours=7))  # Vietnam timezone UTC+7
        current_vietnam_time = datetime.now(vietnam_tz)
        
        if days > 0:
            expiry_date_vietnam = current_vietnam_time + timedelta(days=days)
            is_vip = True
        else:
            expiry_date_vietnam = None
            is_vip = False
        
        # Store in UTC for database consistency
        expiry_date_utc = expiry_date_vietnam.astimezone(timezone.utc) if expiry_date_vietnam else None
        
        # Update VIP status and expiry
        if SUPABASE_AVAILABLE and user:
            # Update in Supabase
            print(f"🔄 Using Supabase: Updating VIP for user: {telegram_id}")
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    response = supabase.table('users').update({
                        'is_vip': is_vip,
                        'vip_expiry': expiry_date_utc.isoformat() if expiry_date_utc else None,
                        'updated_at': datetime.now().isoformat()
                    }).eq('telegram_id', str(telegram_id)).execute()
                    
                    if response.data:
                        # Add transaction record
                        transaction_data = {
                            'user_id': user_id,
                            'type': 'admin_vip',
                            'amount': 0,
                            'coins': 0,
                            'description': f'Admin set VIP: {days} ngày',
                            'status': 'completed',
                            'created_at': datetime.now().isoformat()
                        }
                        supabase.table('transactions').insert(transaction_data).execute()
                        print(f"✅ VIP updated in Supabase for user {telegram_id}")
                    else:
                        print(f"❌ Failed to update VIP in Supabase")
                        send_telegram_message(chat_id, f"❌ Lỗi cập nhật VIP trong Supabase!")
                        return
                else:
                    print(f"❌ Supabase client not available")
                    send_telegram_message(chat_id, f"❌ Lỗi kết nối Supabase!")
                    return
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                send_telegram_message(chat_id, f"❌ Lỗi cập nhật VIP: {str(e)}")
                return
        else:
            # Fallback to SQLite
            print(f"🔄 Fallback: Updating VIP in SQLite: {telegram_id}")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Update VIP status and expiry
            cursor.execute('UPDATE users SET is_vip = ?, vip_expiry = ? WHERE telegram_id = ?', (is_vip, expiry_date_utc.isoformat() if expiry_date_utc else None, telegram_id))
            
            # Add transaction record
            cursor.execute('''
                INSERT INTO transactions (user_id, type, amount, description)
                VALUES (?, ?, ?, ?)
            ''', (user_id, 'admin_vip', 0, f'Admin set VIP: {days} ngày'))
            
            conn.commit()
            conn.close()
        
        if days > 0:
            message = f"✅ Đã cập nhật VIP cho user:\nID: `{telegram_id}`\nUsername: @{username}\nTên: {first_name}\nVIP: ✅ Có\nHết hạn: {expiry_date_vietnam.strftime('%d/%m/%Y %H:%M')} (VN)\nSố ngày: {days} ngày"
        else:
            message = f"✅ Đã tắt VIP cho user:\nID: `{telegram_id}`\nUsername: @{username}\nTên: {first_name}\nVIP: ❌ Không"
        
        send_telegram_message(chat_id, message)
        
        # Send notification to user
        try:
            if days > 0:
                user_message = f"""👑 **BẠN ĐÃ ĐƯỢC ADMIN SET VIP**

🆔 User ID: `{telegram_id}`
👤 Tên: {first_name}
👑 VIP: ✅ Có
⏰ Hết hạn: {expiry_date_vietnam.strftime('%d/%m/%Y %H:%M')} (VN)
📅 Số ngày: {days} ngày

🎉 Hãy tận hưởng các quyền lợi VIP!

---
_SheerID VIP Bot_"""
            else:
                user_message = f"""👑 **ADMIN ĐÃ TẮT VIP CỦA BẠN**

🆔 User ID: `{telegram_id}`
👤 Tên: {first_name}
👑 VIP: ❌ Không

💡 Liên hệ admin để được hỗ trợ!

---
_SheerID VIP Bot_"""
            
            send_telegram_message(telegram_id, user_message)
            print(f"✅ Sent VIP notification to user {telegram_id}")
        except Exception as e:
            print(f"❌ Failed to send VIP notification to user {telegram_id}: {e}")
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Telegram ID và days phải là số!")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_set_vip_expiry(chat_id, telegram_id, expiry_str):
    """Set VIP expiry for user for admin"""
    try:
        telegram_id = int(telegram_id)
        
        # Parse expiry date
        from datetime import datetime
        try:
            expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d %H:%M')
            expiry_iso = expiry_date.isoformat()
        except ValueError:
            send_telegram_message(chat_id, "❌ Định dạng ngày không đúng! Sử dụng: YYYY-MM-DD HH:MM\nVí dụ: 2024-12-31 * 23:59")
            return
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT id, username, first_name, is_vip, vip_expiry FROM users WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        
        if not user:
            send_telegram_message(chat_id, f"❌ Không tìm thấy user với ID {telegram_id}!")
            conn.close()
            return
        
        user_id, username, first_name, is_vip, old_expiry = user
        
        # Update VIP expiry
        cursor.execute('UPDATE users SET vip_expiry = ? WHERE telegram_id = ?', (expiry_iso, telegram_id))
        
        # Add transaction record
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, 'admin_vip_expiry', 0, f'Admin set VIP expiry: {old_expiry or "None"} -> {expiry_iso}'))
        
        conn.commit()
        conn.close()
        
        message = f"✅ Đã cập nhật VIP expiry cho user:\nID: `{telegram_id}`\nUsername: @{username}\nTên: {first_name}\nVIP: {'✅' if is_vip else '❌'}\nHết hạn: {expiry_date.strftime('%d/%m/%Y %H:%M')}"
        send_telegram_message(chat_id, message)
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Telegram ID phải là số!")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_user_jobs(chat_id, telegram_id):
    """Get jobs for specific user for admin"""
    try:
        telegram_id = int(telegram_id)
        
        # Try to get user from Supabase first
        user = None
        if SUPABASE_AVAILABLE:
            print(f"🔄 Using Supabase: Getting user for jobs: {telegram_id}")
            try:
                from supabase_client import get_user_by_telegram_id
                user = get_user_by_telegram_id(str(telegram_id))
                if user:
                    print(f"✅ Found user in Supabase: {user}")
                else:
                    print(f"❌ User {telegram_id} not found in Supabase")
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                print("🔄 Falling back to SQLite")
        
        if not user:
            # Fallback to SQLite
            print(f"🔄 Fallback: Getting user from SQLite: {telegram_id}")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute('SELECT id, username, first_name, last_name FROM users WHERE telegram_id = ?', (telegram_id,))
            user_data = cursor.fetchone()
            conn.close()
            
            if not user_data:
                send_telegram_message(chat_id, f"❌ Không tìm thấy user với ID {telegram_id}!")
                return
            
            user_id, username, first_name, last_name = user_data
        else:
            # User from Supabase
            user_id = user.get('id')
            username = user.get('username', 'N/A')
            first_name = user.get('first_name', 'N/A')
            last_name = user.get('last_name', 'N/A')
        
        # Get user's jobs: prefer Supabase, fallback to SQLite
        jobs = []
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    resp = supabase.table('verification_jobs').select('job_id, sheerid_url, status, created_at, result, student_info, card_filename').eq('user_id', user_id).order('created_at', desc=True).limit(20).execute()
                    jobs = resp.data if resp.data else []
                    print(f"📊 Found {len(jobs)} jobs in Supabase for admin view user {telegram_id}")
            except Exception as e:
                print(f"❌ Supabase error getting jobs for admin view: {e}")
        
        if not jobs:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT job_id, sheerid_url, status, created_at, result, student_info, card_filename
                FROM verification_jobs 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 20
            ''', (user_id,))
            jobs = cursor.fetchall()
            conn.close()
        
        if not jobs:
            message = f"📝 User {first_name} {last_name if last_name and last_name != 'User' else ''} chưa có job nào."
        else:
            message = f"📋 JOBS CỦA USER:\n"
            message += f"👤 Tên: {first_name} {last_name if last_name and last_name != 'User' else ''}\n"
            message += f"📱 Username: @{username or 'N/A'}\n"
            message += f"🆔 ID: `{telegram_id}`\n\n"
            
            for i, job in enumerate(jobs, 1):
                if isinstance(job, dict):
                    job_id = job.get('job_id')
                    url = job.get('sheerid_url')
                    status = job.get('status')
                    created = job.get('created_at')
                    student_info = job.get('student_info')
                    card_filename = job.get('card_filename')
                    completed = None
                else:
                    job_id, url, status, created, _result, student_info, card_filename = job
                    completed = None
                status_emoji = {
                    'pending': '⏳',
                    'processing': '🔄', 
                    'completed': '✅',
                    'failed': '❌'
                }.get(status, '❓')
                
                message += f"""
{i}. Job ID: `{job_id}`
{status_emoji} Trạng thái: {status.upper()}
🔗 URL: {url[:50]}...
📅 Tạo: {created[:16]}
"""
                
                # Not showing completed time because Supabase stores completion in `result`
                
                if student_info:
                    try:
                        import json
                        student_data = json.loads(student_info)
                        email = student_data.get('email', 'N/A')
                        school = student_data.get('school', 'N/A')
                        message += f"📧 Email: {email}\n"
                        message += f"🏫 Trường: {school}\n"
                    except:
                        pass
                
                if card_filename:
                    message += f"📄 Thẻ: {card_filename}\n"
                
                message += f"🌐 Xem chi tiết: https://dqsheerid.vercel.app/job-status?job_id={job_id}\n"
                message += "---\n"
        
        send_telegram_message(chat_id, message)
        
    except ValueError:
        send_telegram_message(chat_id, "❌ Telegram ID phải là số!")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_user_info(chat_id, telegram_id):
    """Show comprehensive user information"""
    try:
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        
        # Get user basic info
        user_resp = supabase.table('users').select('*').eq('telegram_id', telegram_id).limit(1).execute()
        if not user_resp.data:
            send_telegram_message(chat_id, f"❌ Không tìm thấy user với telegram_id: {telegram_id}")
            return
        
        user = user_resp.data[0]
        user_id = user['id']
        
        # Get wallet info
        wallets = supabase_get_wallets_by_user_id(user_id)
        cash = wallets[0] if wallets else 0
        coins = wallets[1] if wallets else 0
        
        # Get verification jobs count
        jobs_resp = supabase.table('verification_jobs').select('id', count='exact').eq('user_id', user_id).execute()
        total_jobs = jobs_resp.count or 0
        
        completed_jobs_resp = supabase.table('verification_jobs').select('id', count='exact').eq('user_id', user_id).eq('status', 'completed').execute()
        completed_jobs = completed_jobs_resp.count or 0
        
        # Get transactions summary
        transactions_resp = supabase.table('transactions').select('type,amount').eq('user_id', user_id).execute()
        total_spent = 0
        total_earned = 0
        for tx in transactions_resp.data:
            amount = float(tx.get('amount', 0))
            if tx['type'] in ['verify', 'purchase']:
                total_spent += amount
            elif tx['type'] in ['checkin', 'quest', 'refund']:
                total_earned += amount
        
        # Get streak info (handle missing table gracefully)
        current_streak = 0
        best_streak = 0
        try:
            streak_resp = supabase.table('user_streaks').select('*').eq('user_id', user_id).limit(1).execute()
            if streak_resp.data:
                current_streak = streak_resp.data[0].get('current_streak', 0)
                best_streak = streak_resp.data[0].get('best_streak', 0)
        except Exception:
            # Table doesn't exist or other error, use defaults
            pass
        
        # Get quest progress (handle missing table gracefully)
        quests_claimed = 0
        try:
            quest_resp = supabase.table('user_quests').select('*').eq('user_id', user_id).execute()
            quests_claimed = len(quest_resp.data) if quest_resp.data else 0
        except Exception:
            # Table doesn't exist or other error, use defaults
            pass
        
        # Check ban status
        ban_status = is_user_banned(telegram_id)
        
        # Format VIP expiry
        vip_expiry = user.get('vip_expiry')
        vip_status = "✅" if user.get('is_vip') else "❌"
        if vip_expiry:
            try:
                from datetime import datetime
                expiry_dt = datetime.fromisoformat(vip_expiry.replace('Z', '+00:00'))
                vip_expiry_str = expiry_dt.strftime('%Y-%m-%d %H:%M')
            except:
                vip_expiry_str = str(vip_expiry)[:16]
        else:
            vip_expiry_str = "N/A"
        
        # Escape special characters for plain text (no Markdown)
        username = user.get('username', 'N/A')
        if username != 'N/A':
            username = f"@{username}"
        
        message = f"""👤 THÔNG TIN USER

📋 Cơ bản:
• ID: {user_id}
• Telegram ID: {telegram_id}
• Username: {username}
• Tên: {user.get('first_name', 'N/A')} {user.get('last_name', '')}
• Tạo: {user.get('created_at', 'N/A')[:19]}
• Cập nhật: {user.get('updated_at', 'N/A')[:19]}

💰 Ví:
• �I Cash: {cash}
• 🪙 Xu: {coins}
• 💸 Đã chi: {total_spent:.1f}
• 💰 Đã kiếm: {total_earned:.1f}

👑 VIP:
• Trạng thái: {vip_status}
• Hết hạn: {vip_expiry_str}

📊 Hoạt động:
• Jobs tổng: {total_jobs}
• Jobs hoàn thành: {completed_jobs}
• Streak hiện tại: {current_streak}
• Streak tốt nhất: {best_streak}
• Quests đã nhận: {quests_claimed}

🚫 Trạng thái:
• Bị khóa: {'✅ CÓ' if ban_status else '❌ KHÔNG'}

❓ Hỗ trợ: @meepzizhere"""
        
        # Send without parse_mode to avoid entity parsing errors
        send_telegram_message(chat_id, message, parse_mode=None)
        
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi xem thông tin user: {str(e)}")

def handle_admin_user_purchases(chat_id, telegram_id):
    """Show user's purchase history from shop"""
    try:
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        
        # Get user basic info
        user_resp = supabase.table('users').select('*').eq('telegram_id', telegram_id).limit(1).execute()
        if not user_resp.data:
            send_telegram_message(chat_id, f"❌ Không tìm thấy user với telegram_id: {telegram_id}")
            return
        
        user = user_resp.data[0]
        user_id = user['id']
        username = user.get('username', 'N/A')
        first_name = user.get('first_name', 'N/A')
        
        # Get purchase transactions
        purchases_resp = supabase.table('transactions').select('*').eq('user_id', user_id).eq('type', 'purchase').order('created_at', desc=True).limit(20).execute()
        
        if not purchases_resp.data:
            message = f"""🛒 LỊCH SỬ MUA HÀNG

👤 User: {first_name} (@{username})
🆔 ID: {telegram_id}

📝 Chưa có giao dịch mua hàng nào."""
        else:
            message = f"""🛒 LỊCH SỬ MUA HÀNG

👤 User: {first_name} (@{username})
🆔 ID: {telegram_id}

📊 Tổng giao dịch: {len(purchases_resp.data)}

"""
            
            total_spent = 0
            for i, purchase in enumerate(purchases_resp.data, 1):
                amount = float(purchase.get('amount', 0))
                description = purchase.get('description', 'N/A')
                created_at = purchase.get('created_at', 'N/A')
                total_spent += amount
                
                # Format date
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    date_str = created_at[:16] if created_at != 'N/A' else 'N/A'
                
                message += f"{i}. 💰 {amount} Cash - {description}\n"
                message += f"   📅 {date_str}\n\n"
            
            message += f"💸 Tổng đã chi: {total_spent} Cash"
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi xem lịch sử mua hàng: {str(e)}")

def handle_admin_lsgd(chat_id, page=1):
    """Show deposit history only with pagination"""
    try:
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        
        # Pagination settings
        per_page = 5
        offset = (page - 1) * per_page
        
        # Get total count for deposits only
        count_resp = supabase.table('transactions').select('id', count='exact').in_('type', ['deposit', 'nap']).execute()
        total_deposits = count_resp.count if count_resp.count else 0
        total_pages = (total_deposits + per_page - 1) // per_page
        
        if page < 1 or page > total_pages:
            send_telegram_message(chat_id, f"❌ Trang không hợp lệ! Trang {page}/{total_pages}")
            return
        
        # Get deposit transactions only with pagination
        deposits_resp = supabase.table('transactions').select('*').in_('type', ['deposit', 'nap']).order('created_at', desc=True).range(offset, offset + per_page - 1).execute()
        
        if not deposits_resp.data:
            message = f"""💰 LỊCH SỬ NẠP TIỀN

📝 Chưa có giao dịch nạp tiền nào."""
        else:
            message = f"""💰 LỊCH SỬ NẠP TIỀN

📊 Trang {page}/{total_pages} | Tổng: {total_deposits} giao dịch nạp tiền

"""
            
            total_amount = 0
            for i, deposit in enumerate(deposits_resp.data, offset + 1):
                amount = float(deposit.get('amount', 0))
                description = deposit.get('description', 'N/A')
                created_at = deposit.get('created_at', 'N/A')
                user_id = deposit.get('user_id', 'N/A')
                total_amount += amount
                
                # Get user info
                user_info = "Unknown"
                try:
                    user_resp = supabase.table('users').select('username, first_name, telegram_id').eq('id', user_id).limit(1).execute()
                    if user_resp.data:
                        user = user_resp.data[0]
                        username = user.get('username', 'N/A')
                        first_name = user.get('first_name', 'N/A')
                        telegram_id = user.get('telegram_id', 'N/A')
                        user_info = f"@{username} ({first_name}) - ID: {telegram_id}"
                except Exception:
                    user_info = f"User ID: {user_id}"
                
                # Format date
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    date_str = created_at[:16] if created_at != 'N/A' else 'N/A'
                
                message += f"{i}. 💰 +{amount} Xu\n"
                message += f"   👤 {user_info}\n"
                message += f"   📝 {description}\n"
                message += f"   📅 {date_str}\n\n"
            
            message += f"💸 Tổng nạp: {total_amount} Xu"
            
            # Pagination info
            if total_pages > 1:
                message += f"\n\n📄 Sử dụng: /admin lsgd [trang]\n"
                message += f"📄 Ví dụ: /admin lsgd {page + 1 if page < total_pages else page}"
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi xem lịch sử nạp tiền: {str(e)}")

def handle_admin_activities(chat_id, page=1):
    """Show all transaction history with pagination"""
    try:
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        
        # Pagination settings
        per_page = 5
        offset = (page - 1) * per_page
        
        # Get total count first
        count_resp = supabase.table('transactions').select('id', count='exact').execute()
        total_transactions = count_resp.count if count_resp.count else 0
        total_pages = (total_transactions + per_page - 1) // per_page
        
        if page < 1 or page > total_pages:
            send_telegram_message(chat_id, f"❌ Trang không hợp lệ! Trang {page}/{total_pages}")
            return
        
        # Get all transactions with pagination
        transactions_resp = supabase.table('transactions').select('*').order('created_at', desc=True).range(offset, offset + per_page - 1).execute()
        
        if not transactions_resp.data:
            message = f"""🔍 HOẠT ĐỘNG SERVER

📝 Chưa có giao dịch nào."""
        else:
            message = f"""🔍 HOẠT ĐỘNG SERVER

📊 Trang {page}/{total_pages} | Tổng: {total_transactions} giao dịch

"""
            
            for i, transaction in enumerate(transactions_resp.data, offset + 1):
                amount = float(transaction.get('amount', 0))
                description = transaction.get('description', 'N/A')
                created_at = transaction.get('created_at', 'N/A')
                user_id = transaction.get('user_id', 'N/A')
                transaction_type = transaction.get('type', 'unknown')
                job_id = transaction.get('job_id', '')
                
                # Get user info
                user_info = "Unknown"
                try:
                    user_resp = supabase.table('users').select('username, first_name, telegram_id').eq('id', user_id).limit(1).execute()
                    if user_resp.data:
                        user = user_resp.data[0]
                        username = user.get('username', 'N/A')
                        first_name = user.get('first_name', 'N/A')
                        telegram_id = user.get('telegram_id', 'N/A')
                        user_info = f"@{username} ({first_name}) - ID: {telegram_id}"
                except Exception:
                    user_info = f"User ID: {user_id}"
                
                # Format date
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    date_str = created_at[:16] if created_at != 'N/A' else 'N/A'
                
                # Transaction type emoji and sign
                type_emoji = {
                    'deposit': '💰',
                    'nap': '💰', 
                    'verify': '🔍',
                    'purchase': '🛒',
                    'bonus': '🎁',
                    'admin': '⚙️'
                }.get(transaction_type, '📝')
                
                sign = '+' if transaction_type in ['deposit', 'nap', 'bonus'] else '-'
                
                message += f"{i}. {type_emoji} {sign}{amount} Xu ({transaction_type})\n"
                message += f"   👤 {user_info}\n"
                message += f"   📝 {description}\n"
                if job_id:
                    message += f"   🆔 Job: {job_id}\n"
                message += f"   📅 {date_str}\n\n"
            
            # Pagination info
            if total_pages > 1:
                message += f"📄 Sử dụng: /admin activities [trang]\n"
                message += f"📄 Ví dụ: /admin activities {page + 1 if page < total_pages else page}"
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi xem hoạt động server: {str(e)}")

def handle_admin_pending_jobs(chat_id):
    """Show pending verification jobs"""
    try:
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        
        # Get pending jobs with user info
        jobs_resp = supabase.table('verification_jobs').select('id, user_id, status, created_at, sheerid_url').in_('status', ['pending', 'processing']).order('created_at', desc=True).limit(10).execute()
        
        if not jobs_resp.data:
            send_telegram_message(chat_id, "✅ Không có job verify nào đang chờ xử lý")
            return
        
        message = "⏳ JOBS VERIFY ĐANG CHỜ XỬ LÝ\n\n"
        
        for i, job in enumerate(jobs_resp.data, 1):
            job_id = job.get('id')
            user_id = job.get('user_id')
            status = job.get('status')
            created_at = job.get('created_at', '')
            sheerid_url = job.get('sheerid_url', '')
            
            # Get user info
            user_resp = supabase.table('users').select('telegram_id, username, first_name').eq('id', user_id).execute()
            user_info = user_resp.data[0] if user_resp.data else {}
            
            telegram_id = user_info.get('telegram_id', 'N/A')
            username = user_info.get('username', 'N/A')
            first_name = user_info.get('first_name', 'N/A')
            
            # Extract verification ID from URL
            verification_id = 'N/A'
            if 'verificationId=' in sheerid_url:
                verification_id = sheerid_url.split('verificationId=')[-1].split('&')[0]
            
            message += f"{i}. 🆔 Job: `{job_id}`\n"
            message += f"   👤 User: {first_name} (@{username})\n"
            message += f"   📱 Telegram ID: {telegram_id}\n"
            message += f"   🔗 Verification ID: {verification_id}\n"
            message += f"   📅 Tạo lúc: {created_at[:19] if created_at else 'N/A'}\n"
            message += f"   ⚡ Trạng thái: {status.upper()}\n\n"
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi xem pending jobs: {str(e)}")

def process_completed_verification(job_id, job_data, verification_result):
    """Process payment and send notification for completed verification - DISABLED to prevent duplicates"""
    try:
        print(f"🔇 DISABLED: Webhook charging blocked for job {job_id} to prevent duplicates")
        print(f"� Crharging will be handled by main API system in index.py")
        return
        
        # DISABLED CODE BELOW - All charging is now handled by index.py to prevent duplicates
        from datetime import datetime, timezone, timedelta
        print(f"🔄 Processing completed verification for job {job_id}")
        print(f"🔍 DEBUG: job_data = {job_data}")
        print(f"🔍 DEBUG: verification_result = {verification_result}")
        
        if not SUPABASE_AVAILABLE:
            print("❌ Supabase not available for payment processing")
            return
            
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            print("❌ Could not get Supabase client")
            return
            
        user_id = job_data.get('user_id')
        telegram_id = job_data.get('telegram_id')  # Get directly from verification_jobs
        
        if not user_id or not telegram_id:
            print(f"❌ Missing user_id ({user_id}) or telegram_id ({telegram_id}) in job data")
            return
            
        # Get user data
        user_resp = supabase.table('users').select('*').eq('id', user_id).execute()
        if not user_resp.data:
            print(f"❌ User not found for user_id {user_id}")
            return
            
        user = user_resp.data[0]
        coins = user.get('coins', 0)
        cash = user.get('cash', 0)
        is_vip = user.get('is_vip', False)
        
        print(f"🔍 User {telegram_id} - coins: {coins}, cash: {cash}, is_vip: {is_vip}")
        
        # Check if job is already processed (prevent double charging)
        # Since this function is only called once per job completion, we can skip duplicate check
        # The job status in verification_jobs ensures this function runs only once per job
        print(f"🔍 Processing payment for job {job_id} - no duplicate check needed")
            
        # Determine payment method (VIP: xu first, fallback cash; Non-VIP: quota-based or insufficient xu)
        if is_vip:
            use_cash = coins < 2
        else:
            # Check daily quota for non-VIP
            vietnam_tz = timezone(timedelta(hours=7))
            today_start = datetime.now(vietnam_tz).replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now(vietnam_tz).replace(hour=23, minute=59, second=59, microsecond=999999)
            
            verify_count_today = 0
            try:
                # Count completed jobs for this user today (excluding current job)
                verify_resp = supabase.table('verification_jobs').select('id', count='exact').eq('user_id', user_id).eq('status', 'completed').gte('created_at', today_start.isoformat()).lte('created_at', today_end.isoformat()).neq('job_id', job_id).execute()
                verify_count_today = verify_resp.count or 0
            except Exception as e:
                print(f"Error counting daily verifications: {e}")
                verify_count_today = 0
            
            # Use cash if: exceeded daily quota (2/day) OR insufficient xu
            use_cash = (verify_count_today >= 2) or (coins < 5)
            
        print(f"🔍 Payment method: {'cash' if use_cash else 'xu'}")
        
        # Process payment
        if use_cash:
            # Deduct cash
            new_cash = max(0, cash - 3)
            update_result = supabase.table('users').update({'cash': new_cash, 'updated_at': datetime.now().isoformat()}).eq('id', user_id).execute()
            
            if update_result.data:
                # Log transaction 
                # job_id in transactions table is integer (verification_jobs.id)
                # job_id parameter is UUID string (verification_jobs.job_id)
                verification_job_id = job_data.get('id')  # Integer ID for transactions table
                supabase.table('transactions').insert({
                    'user_id': user_id,
                    'type': 'verify',
                    'amount': -3000,
                    'coins': -3,
                    'job_id': verification_job_id,  # Use integer ID
                    'description': f'Verify SheerID (Cash) - Job {job_id}',  # Include UUID for reference
                    'status': 'completed',
                    'created_at': datetime.now().isoformat()
                }).execute()
                
                print(f"✅ Deducted 3 cash from user {telegram_id}: {cash} -> {new_cash}")
                send_success_notification(telegram_id, job_id, f"3 cash (còn lại: {new_cash})", new_cash, coins, is_vip)
            else:
                print(f"❌ Failed to deduct cash from user {telegram_id}")
        else:
            # Deduct xu
            new_coins = max(0, coins - 3)
            update_result = supabase.table('users').update({'coins': new_coins, 'updated_at': datetime.now().isoformat()}).eq('id', user_id).execute()
            
            if update_result.data:
                # Log transaction
                # job_id in transactions table is integer (verification_jobs.id)  
                # job_id parameter is UUID string (verification_jobs.job_id)
                verification_job_id = job_data.get('id')  # Integer ID for transactions table
                supabase.table('transactions').insert({
                    'user_id': user_id,
                    'type': 'verify',
                    'amount': -3000,
                    'coins': -3,
                    'job_id': verification_job_id,  # Use integer ID
                    'description': f'Verify SheerID (Xu) - Job {job_id}',  # Include UUID for reference
                    'status': 'completed',
                    'created_at': datetime.now().isoformat()
                }).execute()
                
                print(f"✅ Deducted 3 xu from user {telegram_id}: {coins} -> {new_coins}")
                send_success_notification(telegram_id, job_id, f"3 xu (còn lại: {new_coins})", cash, new_coins, is_vip)
            else:
                print(f"❌ Failed to deduct xu from user {telegram_id}")
                
    except Exception as e:
        print(f"❌ Error in process_completed_verification: {e}")
        import traceback
        traceback.print_exc()

def is_notification_already_sent(job_id):
    """Check if notification already sent for this job"""
    try:
        # Check in-memory set first
        if job_id in NOTIFIED_JOBS:
            print(f"🔍 DEBUG: Job {job_id} already in NOTIFIED_JOBS")
            return True
        
        # Check database for notification records
        if SUPABASE_AVAILABLE:
            from supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                # Check if there's a transaction record for this job
                response = supabase.table('transactions').select('id').eq('job_id', job_id).limit(1).execute()
                if response.data:
                    print(f"🔍 DEBUG: Job {job_id} has transaction record, notification already sent")
                    return True
                else:
                    print(f"🔍 DEBUG: Job {job_id} has no transaction record, notification not sent yet")
        
        print(f"🔍 DEBUG: Job {job_id} notification not sent yet")
        return False
    except Exception as e:
        print(f"⚠️ Error checking notification status: {e}")
        return False

def mark_notification_sent(job_id):
    """Mark notification as sent for this job"""
    try:
        NOTIFIED_JOBS.add(job_id)
        print(f"✅ Marked notification as sent for job {job_id}")
    except Exception as e:
        print(f"⚠️ Error marking notification: {e}")

def send_success_notification(telegram_id, job_id, payment_message, cash, coins, is_vip, user_lang='vi'):
    """Send success notification to user with duplicate prevention"""
    try:
        # Check if notification already sent for this job (in-memory check)
        notification_key = f"notif_{job_id}"
        if hasattr(send_success_notification, '_sent_notifications'):
            if notification_key in send_success_notification._sent_notifications:
                print(f"🔇 Notification already sent for job {job_id}")
                return
        else:
            send_success_notification._sent_notifications = set()
        
        print(f"📤 Sending success notification to user {telegram_id} for job {job_id}")
        
        # Multilingual success messages
        vip_text = {'vi': 'Có', 'en': 'Yes', 'zh': '是'}.get(user_lang, 'Có')
        no_vip_text = {'vi': 'Không', 'en': 'No', 'zh': '否'}.get(user_lang, 'Không')
        
        success_msgs = {
            'vi': f"""✅ VERIFY THÀNH CÔNG!

🆔 Job ID: `{job_id}`
💰 Đã trừ: {payment_message}
💎 VIP: {vip_text if is_vip else no_vip_text} | 💰 Cash: {cash} | 🪙 Xu: {coins}

🎉 Chúc mừng! Bạn đã verify thành công!
📢 Tham gia kênh thông báo: https://t.me/channel_sheerid_vip_bot""",
            'en': f"""✅ VERIFICATION SUCCESSFUL!

🆔 Job ID: `{job_id}`
💰 Deducted: {payment_message}
💎 VIP: {vip_text if is_vip else no_vip_text} | 💰 Cash: {cash} | 🪙 Xu: {coins}

🎉 Congratulations! Verification completed!
📢 Join notification channel: https://t.me/channel_sheerid_vip_bot""",
            'zh': f"""✅ 验证成功！

🆔 Job ID: `{job_id}`
💰 已扣除: {payment_message}
💎 VIP: {vip_text if is_vip else no_vip_text} | 💰 Cash: {cash} | 🪙 Xu: {coins}

🎉 恭喜！验证完成！
📢 加入通知频道: https://t.me/channel_sheerid_vip_bot"""
        }
        message = success_msgs.get(user_lang, success_msgs['vi'])

        result = send_telegram_message(telegram_id, message)
        if result:
            send_success_notification._sent_notifications.add(notification_key)
            print(f"✅ Success notification sent to user {telegram_id}")
        else:
            print(f"❌ Failed to send success notification to user {telegram_id}")
        
    except Exception as e:
        print(f"❌ Error sending success notification: {e}")

def handle_cancel_job_command(chat_id, user):
    """Allow user to cancel their pending verification job"""
    try:
        if not user:
            send_telegram_message(chat_id, "❌ Vui lòng /start trước")
            return
        
        # Get user ID
        if isinstance(user, dict):
            user_id = user.get('id')
            telegram_id = user.get('telegram_id')
        else:
            user_id = user[0]
            telegram_id = user[1]
        
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        
        # Find user's latest pending job from NEW sheerid_bot_jobs table
        from datetime import datetime, timezone, timedelta
        
        pending_jobs = supabase.table('sheerid_bot_jobs').select('job_id, status, created_at, verification_type, cost').eq('user_id', user_id).in_('status', ['pending', 'processing']).order('created_at', desc=True).limit(1).execute()
        
        if not pending_jobs.data:
            send_telegram_message(chat_id, "✅ Bạn không có job nào đang chờ xử lý")
            return
        
        # Cancel the most recent pending job
        job_to_cancel = pending_jobs.data[0]
        job_id = job_to_cancel.get('job_id')
        created_at = job_to_cancel.get('created_at', '')
        verification_type = job_to_cancel.get('verification_type', 'gemini')
        cost = job_to_cancel.get('cost', 10)
        
        # Prevent instant cancel to bypass charges: require a waiting period after creation
        try:
            from datetime import datetime, timezone, timedelta
            created_dt = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
            now_dt = datetime.now(timezone.utc)
            
            # All jobs require minimum 5 minutes wait before cancellation
            min_wait = timedelta(minutes=5)
            
            if (now_dt - created_dt) < min_wait:
                remaining = min_wait - (now_dt - created_dt)
                mins = int(remaining.total_seconds() // 60)
                secs = int(remaining.total_seconds() % 60)
                job_type = verification_type.capitalize()
                send_telegram_message(chat_id, f"⏳ Job {job_type} vừa tạo, phải đợi ít nhất 5 phút mới được hủy để tránh gian lận.\n\n⏰ Còn lại: {mins} phút {secs} giây")
                return
        except Exception:
            # If parsing time fails, still allow cancel fallback below
            pass
        
        # Update job status to failed (cancelled by user) and REFUND the upfront payment
        try:
            # Update job status
            update_result = supabase.table('sheerid_bot_jobs').update({
                'status': 'failed',
                'result_details': {'error_message': 'Cancelled by user'},
                'updated_at': datetime.now().isoformat()
            }).eq('job_id', job_id).execute()
            
            # REFUND the upfront payment
            user_result = supabase.table('users').select('cash').eq('id', user_id).execute()
            if user_result.data:
                current_cash = user_result.data[0].get('cash', 0)
                new_cash = current_cash + cost
                supabase.table('users').update({'cash': new_cash}).eq('id', user_id).execute()
                print(f"💰 REFUND: Returned {cost} cash to user {user_id} due to cancellation. New balance: {new_cash}")
            
            if update_result.data:
                message = f"""✅ Đã hủy job verify thành công!

🆔 Job ID: `{job_id}`
🎯 Loại: {verification_type.capitalize()}
📅 Tạo lúc: {created_at[:19] if created_at else 'N/A'}
🔄 Trạng thái: Đã hủy

💰 Hoàn: +{cost} cash
💵 Số dư: {new_cash} cash

💡 Bây giờ bạn có thể tạo job verify mới bằng lệnh /verify"""
                
                send_telegram_message(chat_id, message)
                print(f"✅ User {telegram_id} cancelled job {job_id}")
            else:
                send_telegram_message(chat_id, "❌ Không thể hủy job. Vui lòng thử lại sau.")
                
        except Exception as e:
            print(f"Error cancelling job {job_id}: {e}")
            import traceback
            traceback.print_exc()
            send_telegram_message(chat_id, "❌ Lỗi khi hủy job. Vui lòng liên hệ admin.")
        
    except Exception as e:
        print(f"Error in handle_cancel_job_command: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi hủy job: {str(e)}")

def handle_admin_fix_stuck_jobs(chat_id):
    """Fix stuck verification jobs (older than 1 hour)"""
    try:
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            return
        
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        
        # Find jobs older than 1 hour that are still pending/processing
        from datetime import datetime, timedelta
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        
        stuck_jobs = supabase.table('verification_jobs').select('id, user_id, status, created_at').in_('status', ['pending', 'processing']).lt('created_at', one_hour_ago).execute()
        
        if not stuck_jobs.data:
            send_telegram_message(chat_id, "✅ Không có job nào bị stuck")
            return
        
        fixed_count = 0
        for job in stuck_jobs.data:
            job_id = job.get('id')
            user_id = job.get('user_id')
            created_at = job.get('created_at')
            
            # Update job status to failed
            try:
                update_verification_job(job_id, 'failed', 'Job timeout - automatically marked as failed')
                fixed_count += 1
                print(f"Fixed stuck job {job_id} for user {user_id}")
            except Exception as e:
                print(f"Error fixing job {job_id}: {e}")
        
        message = f"✅ Đã sửa {fixed_count} job bị stuck\n\n"
        message += f"📊 Chi tiết:\n"
        for job in stuck_jobs.data:
            job_id = job.get('id')
            user_id = job.get('user_id')
            created_at = job.get('created_at')
            message += f"• Job {job_id} (User {user_id}) - {created_at[:19]}\n"
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi fix stuck jobs: {str(e)}")

def handle_admin_gift_coins(chat_id, amount, reason):
    """Gift coins to all users"""
    global GIFT_IN_PROGRESS
    
    try:
        # Chặn re-entrant calls
        if GIFT_IN_PROGRESS:
            send_telegram_message(chat_id, "⏳ Đang xử lý lệnh tặng xu trước đó, vui lòng chờ...")
            return
        
        GIFT_IN_PROGRESS = True
        
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            GIFT_IN_PROGRESS = False
            return
        
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            GIFT_IN_PROGRESS = False
            return
        
        if amount <= 0:
            send_telegram_message(chat_id, "❌ Số xu phải lớn hơn 0")
            GIFT_IN_PROGRESS = False
            return
        
        # Get all users
        users_resp = supabase.table('users').select('id, telegram_id, username, first_name, coins').execute()
        if not users_resp.data:
            send_telegram_message(chat_id, "❌ Không có user nào trong hệ thống")
            GIFT_IN_PROGRESS = False
            return
        
        users = users_resp.data
        success_count = 0
        failed_count = 0
        
        # Send progress message
        send_telegram_message(chat_id, f"🔄 Bắt đầu tặng {amount} xu cho {len(users)} users...")
        
        # Process users in batches to avoid timeout
        batch_size = 50
        total_users = len(users)
        
        for i in range(0, total_users, batch_size):
            batch = users[i:i + batch_size]
            batch_success = 0
            batch_failed = 0
            
            for user in batch:
                user_id = user.get('id')
                telegram_id = user.get('telegram_id')
                
                try:
                    # Get current coins from the user data we already have
                    current_coins = int(user.get('coins') or 0)
                    new_coins = current_coins + amount
                    
                    # Update coins
                    supabase.table('users').update({
                        'coins': new_coins,
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', user_id).execute()
                    
                    # Add transaction record
                    transaction_data = {
                        'user_id': user_id,
                        'type': 'bonus',
                        'amount': amount,
                        'description': f"Admin gift: {reason}",
                        'status': 'completed',
                        'created_at': datetime.now().isoformat()
                    }
                    supabase.table('transactions').insert(transaction_data).execute()
                    
                    batch_success += 1
                    success_count += 1
                    
                except Exception as e:
                    batch_failed += 1
                    failed_count += 1
                    # Only log first few errors to avoid log spam
                    if failed_count <= 5:
                        print(f"❌ Error gifting coins to user {telegram_id}: {e}")
            
            # Send progress update every batch
            progress = min(i + batch_size, total_users)
            send_telegram_message(chat_id, f"📊 Tiến độ: {progress}/{total_users} users | ✅ {batch_success} | ❌ {batch_failed}")
            
            # Small delay to prevent rate limiting
            import time
            time.sleep(0.1)
        
        # Send final summary
        success_rate = (success_count / len(users) * 100) if len(users) > 0 else 0
        message = f"🎉 HOÀN THÀNH TẶNG XU!\n\n"
        message += f"💰 Số xu: {amount}\n"
        message += f"📝 Lý do: {reason}\n"
        message += f"✅ Thành công: {success_count} user\n"
        message += f"❌ Thất bại: {failed_count} user\n"
        message += f"👥 Tổng user: {len(users)}\n"
        message += f"📈 Tỷ lệ thành công: {success_rate:.1f}%"
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi tặng xu: {str(e)}")
    finally:
        # Luôn reset flag khi kết thúc
        GIFT_IN_PROGRESS = False

def handle_admin_gift_cash(chat_id, amount, reason):
    """Gift cash to all users"""
    global GIFT_IN_PROGRESS
    
    try:
        # Chặn re-entrant calls
        if GIFT_IN_PROGRESS:
            send_telegram_message(chat_id, "⏳ Đang xử lý lệnh tặng cash trước đó, vui lòng chờ...")
            return
        
        GIFT_IN_PROGRESS = True
        
        if not SUPABASE_AVAILABLE:
            send_telegram_message(chat_id, "❌ Supabase không khả dụng")
            GIFT_IN_PROGRESS = False
            return
        
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            GIFT_IN_PROGRESS = False
            return
        
        if amount <= 0:
            send_telegram_message(chat_id, "❌ Số cash phải lớn hơn 0")
            GIFT_IN_PROGRESS = False
            return
        
        # Get all users
        users_resp = supabase.table('users').select('id, telegram_id, username, first_name, cash').execute()
        if not users_resp.data:
            send_telegram_message(chat_id, "❌ Không có user nào trong hệ thống")
            GIFT_IN_PROGRESS = False
            return
        
        users = users_resp.data
        success_count = 0
        failed_count = 0
        
        # Send progress message
        send_telegram_message(chat_id, f"🔄 Bắt đầu tặng {amount} cash cho {len(users)} users...")
        
        # Process users in batches to avoid timeout
        batch_size = 50
        total_users = len(users)
        
        for i in range(0, total_users, batch_size):
            batch = users[i:i + batch_size]
            batch_success = 0
            batch_failed = 0
            
            for user in batch:
                user_id = user.get('id')
                telegram_id = user.get('telegram_id')
                
                try:
                    # Get current cash from the user data we already have
                    current_cash = int(user.get('cash') or 0)
                    new_cash = current_cash + amount
                    
                    # Update cash
                    supabase.table('users').update({
                        'cash': new_cash,
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', user_id).execute()
                    
                    # Add transaction record
                    transaction_data = {
                        'user_id': user_id,
                        'type': 'bonus',
                        'amount': amount * 1000,  # Cash is stored as VND
                        'description': f"Admin gift: {reason}",
                        'status': 'completed',
                        'created_at': datetime.now().isoformat()
                    }
                    supabase.table('transactions').insert(transaction_data).execute()
                    
                    batch_success += 1
                    success_count += 1
                    
                except Exception as e:
                    batch_failed += 1
                    failed_count += 1
                    # Only log first few errors to avoid log spam
                    if failed_count <= 5:
                        print(f"❌ Error gifting cash to user {telegram_id}: {e}")
            
            # Send progress update every batch
            progress = min(i + batch_size, total_users)
            send_telegram_message(chat_id, f"📊 Tiến độ: {progress}/{total_users} users | ✅ {batch_success} | ❌ {batch_failed}")
            
            # Small delay to prevent rate limiting
            import time
            time.sleep(0.1)
        
        # Send final summary
        success_rate = (success_count / len(users) * 100) if len(users) > 0 else 0
        message = f"🎉 HOÀN THÀNH TẶNG CASH!\n\n"
        message += f"💵 Số cash: {amount}\n"
        message += f"📝 Lý do: {reason}\n"
        message += f"✅ Thành công: {success_count} user\n"
        message += f"❌ Thất bại: {failed_count} user\n"
        message += f"👥 Tổng user: {len(users)}\n"
        message += f"📈 Tỷ lệ thành công: {success_rate:.1f}%"
        
        send_telegram_message(chat_id, message)
        
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Lỗi tặng cash: {str(e)}")
    finally:
        # Luôn reset flag khi kết thúc
        GIFT_IN_PROGRESS = False

# ==================== GIFTCODE HANDLERS ====================

def handle_admin_create_giftcode(chat_id, code, reward_type, reward_amount, max_uses):
    """Admin: Tạo giftcode mới"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(__file__))
        from supabase_client import get_supabase_client
        from giftcode_system import create_giftcode
        
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        
        # Validate reward_type
        if reward_type not in ['coins', 'cash', 'xu']:
            send_telegram_message(chat_id, "❌ Loại phần thưởng phải là: xu hoặc cash")
            return
        
        # Normalize reward_type
        if reward_type == 'xu':
            reward_type = 'coins'
        
        # Validate amounts
        if reward_amount <= 0:
            send_telegram_message(chat_id, "❌ Số lượng phần thưởng phải lớn hơn 0")
            return
        
        if max_uses <= 0:
            send_telegram_message(chat_id, "❌ Số lượt sử dụng phải lớn hơn 0")
            return
        
        # Create giftcode
        result = create_giftcode(
            supabase=supabase,
            code=code,
            reward_type=reward_type,
            reward_amount=reward_amount,
            max_uses=max_uses,
            created_by_admin_id=chat_id
        )
        
        if result and 'error' in result:
            send_telegram_message(chat_id, f"❌ {result['error']}")
            return
        
        if result:
            reward_text = f"{reward_amount} xu" if reward_type == 'coins' else f"{reward_amount} cash"
            vietnam_time = get_vietnam_time().strftime('%d/%m/%Y %H:%M:%S')
            message = f"""Tao giftcode thanh cong!

Ma: {code.upper()}
Phan thuong: {reward_text}
So luot: {max_uses}
Thoi gian: {vietnam_time}

Huong dan: /giftcode {code.upper()}"""
            
            print(f"📤 Sending giftcode success message to {chat_id}")
            result = send_telegram_message(chat_id, message, parse_mode=None)
            print(f"📤 Send result: {result}")
        else:
            send_telegram_message(chat_id, "❌ Không thể tạo giftcode")
            
    except Exception as e:
        print(f"❌ Error in handle_admin_create_giftcode: {e}")
        send_telegram_message(chat_id, f"❌ Lỗi: {str(e)}")

def handle_admin_list_giftcodes(chat_id):
    """Admin: Liệt kê tất cả giftcodes"""
    try:
        from supabase_client import get_supabase_client
        from giftcode_system import list_all_giftcodes
        
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        
        giftcodes = list_all_giftcodes(supabase)
        
        if not giftcodes:
            send_telegram_message(chat_id, "Chua co giftcode nao trong he thong", parse_mode=None)
            return
        
        message = "📋 DANH SÁCH GIFTCODES:\n\n"
        
        for gc in giftcodes[:20]:  # Giới hạn 20 giftcodes
            code = gc.get('code', 'N/A')
            reward_type = gc.get('reward_type', 'N/A')
            reward_amount = gc.get('reward_amount', 0)
            current_uses = gc.get('current_uses', 0)
            max_uses = gc.get('max_uses', 0)
            is_active = gc.get('is_active', False)
            
            reward_text = f"{reward_amount} xu" if reward_type == 'coins' else f"{reward_amount} cash"
            status = "✅ Hoạt động" if is_active else "❌ Đã tắt"
            
            message += f"🎟️ `{code}`\n"
            message += f"   💰 {reward_text} | 🔢 {current_uses}/{max_uses} | {status}\n\n"
        
        if len(giftcodes) > 20:
            message += f"\n... và {len(giftcodes) - 20} giftcode khác"
        
        send_telegram_message(chat_id, message, parse_mode=None)
        
    except Exception as e:
        print(f"❌ Error in handle_admin_list_giftcodes: {e}")
        send_telegram_message(chat_id, f"Loi: {str(e)}", parse_mode=None)

def handle_admin_giftcode_info(chat_id, code):
    """Admin: Xem thông tin chi tiết giftcode"""
    try:
        from supabase_client import get_supabase_client
        from giftcode_system import get_giftcode_usage_stats
        
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        
        stats = get_giftcode_usage_stats(supabase, code)
        
        if not stats:
            send_telegram_message(chat_id, f"Khong tim thay giftcode: {code}", parse_mode=None)
            return
        
        gc = stats['giftcode']
        usage_list = stats['usage_list']
        
        reward_type = gc.get('reward_type', 'N/A')
        reward_amount = gc.get('reward_amount', 0)
        reward_text = f"{reward_amount} xu" if reward_type == 'coins' else f"{reward_amount} cash"
        
        created_time = convert_utc_to_vietnam(gc.get('created_at', 'N/A'))
        
        message = f"""📊 THÔNG TIN GIFTCODE

🎟️ Mã: `{gc.get('code', 'N/A')}`
💰 Phần thưởng: {reward_text}
🔢 Đã dùng: {gc.get('current_uses', 0)}/{gc.get('max_uses', 0)}
📊 Trạng thái: {"✅ Hoạt động" if gc.get('is_active') else "❌ Đã tắt"}
📅 Tạo lúc: {created_time}

👥 DANH SÁCH ĐÃ SỬ DỤNG ({len(usage_list)} người):
"""
        
        if usage_list:
            for i, usage in enumerate(usage_list[:10], 1):
                user_info = usage.get('users', {})
                username = user_info.get('username', 'N/A')
                first_name = user_info.get('first_name', 'N/A')
                telegram_id = usage.get('telegram_id', 'N/A')
                used_at = usage.get('used_at', 'N/A')[:19]
                
                message += f"\n{i}. @{username} ({first_name})"
                message += f"\n   ID: {telegram_id} | {used_at}"
            
            if len(usage_list) > 10:
                message += f"\n\n... và {len(usage_list) - 10} người khác"
        else:
            message += "\n(Chưa có ai sử dụng)"
        
        send_telegram_message(chat_id, message, parse_mode=None)
        
    except Exception as e:
        print(f"❌ Error in handle_admin_giftcode_info: {e}")
        send_telegram_message(chat_id, f"Loi: {str(e)}", parse_mode=None)

def handle_admin_deactivate_giftcode(chat_id, code):
    """Admin: Vô hiệu hóa giftcode"""
    try:
        from supabase_client import get_supabase_client
        from giftcode_system import deactivate_giftcode
        
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "❌ Không thể kết nối Supabase")
            return
        
        success = deactivate_giftcode(supabase, code)
        
        if success:
            send_telegram_message(chat_id, f"Da vo hieu hoa giftcode: {code.upper()}", parse_mode=None)
        else:
            send_telegram_message(chat_id, f"Khong the vo hieu hoa giftcode: {code}", parse_mode=None)
            
    except Exception as e:
        print(f"❌ Error in handle_admin_deactivate_giftcode: {e}")
        send_telegram_message(chat_id, f"Loi: {str(e)}", parse_mode=None)

def handle_user_use_giftcode(chat_id, user, code):
    """User: Sử dụng giftcode"""
    try:
        from supabase_client import get_supabase_client
        from giftcode_system import use_giftcode
        
        supabase = get_supabase_client()
        if not supabase:
            send_telegram_message(chat_id, "He thong tam thoi khong kha dung", parse_mode=None)
            return
        
        user_id = user.get('id')
        telegram_id = user.get('telegram_id')
        
        if not user_id or not telegram_id:
            send_telegram_message(chat_id, "Khong tim thay thong tin user", parse_mode=None)
            return
        
        result = use_giftcode(
            supabase=supabase,
            code=code,
            user_id=user_id,
            telegram_id=telegram_id
        )
        
        print(f"📤 Sending giftcode use result to {chat_id}: {result.get('message', 'No message')[:50]}")
        send_result = send_telegram_message(chat_id, result.get('message', 'Loi khong xac dinh'), parse_mode=None)
        print(f"📤 Send result: {send_result}")
        
    except Exception as e:
        print(f"❌ Error in handle_user_use_giftcode: {e}")
        send_telegram_message(chat_id, f"Loi: {str(e)}", parse_mode=None)

# ==================== END GIFTCODE HANDLERS ====================

def get_referral_count(user_id):
    """Get referral count for a user"""
    try:
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    response = supabase.table('referrals').select('id', count='exact').eq('referrer_id', user_id).eq('status', 'completed').execute()
                    return response.count or 0
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                return 0
        
        # Fallback to SQLite (only if Supabase is not available)
        print("⚠️ Supabase not available, using SQLite fallback for referrals")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND status = "completed"', (user_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"❌ Error getting referral count: {e}")
        return 0

def get_referrer_info(user_id):
    """Get referrer information for a user"""
    try:
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    response = supabase.table('referrals').select('referrer_id').eq('referred_id', user_id).eq('status', 'completed').execute()
                    if response.data:
                        referrer_id = response.data[0]['referrer_id']
                        referrer = get_user_by_id(referrer_id)
                        return referrer
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                return None
        
        # Fallback to SQLite (only if Supabase is not available)
        print("⚠️ Supabase not available, using SQLite fallback for referrals")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT referrer_id FROM referrals WHERE referred_id = ? AND status = "completed"', (user_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            referrer_id = result[0]
            return get_user_by_id(referrer_id)
        return None
    except Exception as e:
        print(f"❌ Error getting referrer info: {e}")
        return None

def get_referral_list(user_id, page=1, limit=5):
    """Get list of users referred by a user with pagination"""
    try:
        offset = (page - 1) * limit
        
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    # Get referrals first
                    response = supabase.table('referrals').select('id, referred_id, created_at').eq('referrer_id', user_id).eq('status', 'completed').order('created_at', desc=True).range(offset, offset + limit - 1).execute()
                    
                    print(f"🔍 DEBUG: Found {len(response.data)} referrals for user {user_id}")
                    print(f"🔍 DEBUG: Referrals data: {response.data}")
                    
                    referrals = []
                    for ref in response.data:
                        referred_id = ref.get('referred_id')
                        if referred_id:
                            # Get user info separately
                            try:
                                user_response = supabase.table('users').select('id, telegram_id, first_name, username').eq('id', referred_id).execute()
                                if user_response.data:
                                    user_info = user_response.data[0]
                                    referrals.append({
                                        'id': user_info.get('id', 'N/A'),
                                        'telegram_id': user_info.get('telegram_id', 'N/A'),
                                        'first_name': user_info.get('first_name', 'N/A'),
                                        'username': user_info.get('username', 'N/A'),
                                        'created_at': ref.get('created_at', 'N/A')
                                    })
                                    print(f"✅ DEBUG: Added referral: {user_info.get('first_name')} ({user_info.get('telegram_id')})")
                                else:
                                    print(f"⚠️ DEBUG: No user found for referred_id: {referred_id}")
                            except Exception as e:
                                print(f"❌ Error getting user info for {referred_id}: {e}")
                                # Add with basic info if user lookup fails
                                referrals.append({
                                    'id': referred_id,
                                    'telegram_id': 'N/A',
                                    'first_name': 'Unknown',
                                    'username': 'N/A',
                                    'created_at': ref.get('created_at', 'N/A')
                                })
                    print(f"🔍 DEBUG: Final referrals list: {len(referrals)} items")
                    return referrals
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                return []
        
        # Fallback to SQLite
        print("⚠️ Supabase not available, using SQLite fallback for referrals")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.referred_id, r.created_at, u.telegram_id, u.first_name, u.username
            FROM referrals r
            JOIN users u ON r.referred_id = u.id
            WHERE r.referrer_id = ? AND r.status = "completed"
            ORDER BY r.created_at DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset))
        
        referrals = []
        for row in cursor.fetchall():
            referrals.append({
                'id': row[0],
                'telegram_id': row[1],
                'first_name': row[2],
                'username': row[3],
                'created_at': row[4]
            })
        
        conn.close()
        return referrals
    except Exception as e:
        print(f"❌ Error getting referral list: {e}")
        return []

def process_referral(telegram_id, user, referral_code):
    """Process referral when new user joins"""
    try:
        # Get user info
        if isinstance(user, dict):
            user_id = user.get('id', 0)
        else:
            user_id = user[0]
        
        # Extract referrer_id from referral code
        if not referral_code.startswith('REF'):
            print(f"❌ Invalid referral code format: {referral_code}")
            return
        
        try:
            referrer_id = int(referral_code[3:])  # Remove 'REF' prefix
        except ValueError:
            print(f"❌ Invalid referral code: {referral_code}")
            return
        
        # Check if referrer exists
        referrer = get_user_by_id(referrer_id)
        if not referrer:
            print(f"❌ Referrer not found: {referrer_id}")
            return
        
        # Check if user was already referred
        if is_user_referred(user_id):
            print(f"❌ User {user_id} was already referred")
            return
        
        # Create referral record
        create_referral_record(referrer_id, user_id, referral_code)
        
        # Give rewards
        give_referral_rewards(referrer_id, user_id, referral_code)
        
        print(f"✅ Referral processed: {referrer_id} -> {user_id}")
        
    except Exception as e:
        print(f"❌ Error processing referral: {e}")

def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    response = supabase.table('users').select('*').eq('id', user_id).execute()
                    if response.data:
                        return response.data[0]
            except Exception as e:
                print(f"❌ Supabase error: {e}")
        
        # Fallback to SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    except Exception as e:
        print(f"❌ Error getting user by ID: {e}")
        return None

def is_user_referred(user_id):
    """Check if user was already referred"""
    try:
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    response = supabase.table('referrals').select('id').eq('referred_id', user_id).execute()
                    return len(response.data) > 0
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                return False
        
        # Fallback to SQLite (only if Supabase is not available)
        print("⚠️ Supabase not available, using SQLite fallback for referrals")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM referrals WHERE referred_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        print(f"❌ Error checking if user referred: {e}")
        return False

def create_referral_record(referrer_id, referred_id, referral_code):
    """Create referral record in database"""
    try:
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    supabase.table('referrals').insert({
                        'referrer_id': referrer_id,
                        'referred_id': referred_id,
                        'referral_code': referral_code,
                        'status': 'completed',
                        'reward_given': True,
                        'completed_at': datetime.now().isoformat()
                    }).execute()
                    print(f"✅ Referral record created in Supabase: {referral_code}")
                    return
            except Exception as e:
                print(f"❌ Supabase error: {e}")
                return
        
        # Fallback to SQLite (only if Supabase is not available)
        print("⚠️ Supabase not available, using SQLite fallback for referrals")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO referrals (referrer_id, referred_id, referral_code, status, reward_given, completed_at)
            VALUES (?, ?, ?, 'completed', 1, ?)
        ''', (referrer_id, referred_id, referral_code, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        print(f"✅ Referral record created in SQLite: {referral_code}")
    except Exception as e:
        print(f"❌ Error creating referral record: {e}")

def give_referral_rewards(referrer_id, referred_id, referral_code):
    """Give rewards to both referrer and referred user"""
    try:
        # Give 2 xu to referred user (new user) - referral bonus
        add_coins_to_user_by_id(referred_id, 2, 'referral', f'Referral bonus - joined via {referral_code}')
        
        # Give 3 xu to referrer
        add_coins_to_user_by_id(referrer_id, 3, 'referral', f'Referral reward - invited user {referred_id}')
        
        # Check for milestone rewards
        check_milestone_rewards(referrer_id)
        
        print(f"✅ Referral rewards given: {referrer_id} (+3 xu), {referred_id} (+2 xu)")
        
    except Exception as e:
        print(f"❌ Error giving referral rewards: {e}")

def add_coins_to_user_by_id(user_id, coins, transaction_type, description):
    """Add coins to user by ID"""
    try:
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    # Get current coins
                    user_resp = supabase.table('users').select('coins').eq('id', user_id).execute()
                    if user_resp.data:
                        current_coins = user_resp.data[0].get('coins', 0)
                        new_coins = current_coins + coins
                        
                        # Update coins
                        supabase.table('users').update({'coins': new_coins}).eq('id', user_id).execute()
                        
                        # Log transaction
                        supabase.table('transactions').insert({
                            'user_id': user_id,
                            'type': transaction_type,
                            'amount': coins * 1000,  # Convert to VND equivalent
                            'coins': coins,
                            'description': description,
                            'status': 'completed'
                        }).execute()
                        return
            except Exception as e:
                print(f"❌ Supabase error: {e}")
        
        # Fallback to SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current coins
        cursor.execute('SELECT coins FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        if result:
            current_coins = result[0] or 0
            new_coins = current_coins + coins
            
            # Update coins
            cursor.execute('UPDATE users SET coins = ? WHERE id = ?', (new_coins, user_id))
            
            # Log transaction
            cursor.execute('''
                INSERT INTO transactions (user_id, type, amount, coins, description, status)
                VALUES (?, ?, ?, ?, ?, 'completed')
            ''', (user_id, transaction_type, coins * 1000, coins, description))
            
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Error adding coins to user: {e}")

def check_milestone_rewards(user_id):
    """Check and give milestone rewards"""
    try:
        referral_count = get_referral_count(user_id)
        
        # Define milestones
        milestones = {
            5: 10,   # 5 referrals = 10 xu bonus
            10: 15,  # 10 referrals = 15 xu bonus
            20: 20,  # 20 referrals = 20 xu bonus
        }
        
        for milestone, bonus in milestones.items():
            if referral_count == milestone:
                add_coins_to_user_by_id(user_id, bonus, 'milestone', f'Milestone reward - {milestone} referrals')
                print(f"🎉 Milestone reward given: {user_id} reached {milestone} referrals (+{bonus} xu)")
                break
                
    except Exception as e:
        print(f"❌ Error checking milestone rewards: {e}")

def handle_invite_command(chat_id, user):
    """Handle invite command to create referral link"""
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    
    try:
        # Get user info
        if isinstance(user, dict):
            user_id = user.get('id', 0)
            username = user.get('username', 'user')
            first_name = user.get('first_name', 'User')
        else:
            user_id = user[0]
            username = user[2] if len(user) > 2 else 'user'
            first_name = user[3] if len(user) > 3 else 'User'
        
        # Create referral code
        referral_code = f"REF{user_id:06d}"
        
        # Create invite link
        bot_username = "SheerID_VIP_Bot"  # Correct bot username
        invite_link = f"https://t.me/{bot_username}?start=ref_{referral_code}"
        
        # Get referral stats
        referral_count = get_referral_count(user_id)
        
        # Create message with inline keyboard
        message = f"""🎉 LINK MỜI BẠN BÈ

👤 Người mời: {first_name}
🔗 Link mời: {invite_link}

📊 Thống kê:
• Đã mời: {referral_count} người
• Xu nhận được: {referral_count * 3} xu

💰 Phần thưởng:
• Người mời: 3 xu/người
• Người được mời: 2 xu (lần đầu)

🏆 Mốc thưởng:
• 5 người: +10 xu bonus
• 10 người: +15 xu bonus
• 20 người: +20 xu bonus

💡 Cách sử dụng:
1. Gửi link cho bạn bè
2. Bạn bè nhấn link và /start
3. Cả 2 người đều nhận xu!

📝 Lưu ý: Mỗi người chỉ có thể được mời 1 lần"""
        
        # Create inline keyboard
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📋 Xem danh sách đã mời",
                        "callback_data": f"referral_list_{user_id}_1"
                    }
                ]
            ]
        }
        
        # Send message with keyboard
        print(f"🔍 DEBUG: Sending invite message to {chat_id}")
        result = send_telegram_message_with_keyboard(chat_id, message, keyboard)
        print(f"🔍 DEBUG: Send result: {result}")
        
        if not result:
            print(f"❌ Failed to send invite message, trying fallback")
            send_telegram_message(chat_id, message)
        
    except Exception as e:
        print(f"❌ Error in handle_invite_command: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        send_telegram_message(chat_id, "❌ Lỗi tạo link mời!")

def handle_referral_list_callback(chat_id, user_id, page=1):
    """Handle referral list callback query"""
    try:
        referrals = get_referral_list(user_id, page, 5)
        
        if not referrals:
            message = "📋 Danh sách đã mời\n\n❌ Chưa có ai tham gia qua link mời của bạn."
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🔙 Quay lại",
                            "callback_data": f"back_to_invite_{user_id}"
                        }
                    ]
                ]
            }
        else:
            message = f"📋 Danh sách đã mời (Trang {page})\n\n"
            
            for i, ref in enumerate(referrals, 1):
                # Format time
                try:
                    from datetime import datetime
                    if ref['created_at'] != 'N/A':
                        if isinstance(ref['created_at'], str):
                            dt = datetime.fromisoformat(ref['created_at'].replace('Z', '+00:00'))
                        else:
                            dt = ref['created_at']
                        time_str = dt.strftime("%d/%m/%Y %H:%M")
                    else:
                        time_str = "N/A"
                except:
                    time_str = "N/A"
                
                message += f"""👤 **{i}. {ref['first_name']}**
🆔 ID: `{ref['id']}`
📱 Telegram ID: `{ref['telegram_id']}`
🏷️ Username: @{ref['username'] if ref['username'] != 'N/A' else 'Không có'}
⏰ Thời gian: {time_str}

"""
            
            # Create pagination keyboard
            keyboard_buttons = []
            
            # Previous page button
            if page > 1:
                keyboard_buttons.append({
                    "text": "⬅️ Trang trước",
                    "callback_data": f"referral_list_{user_id}_{page-1}"
                })
            
            # Next page button (check if there are more items)
            if len(referrals) == 5:  # If we got 5 items, there might be more
                keyboard_buttons.append({
                    "text": "Trang sau ➡️",
                    "callback_data": f"referral_list_{user_id}_{page+1}"
                })
            
            # Back button
            keyboard_buttons.append({
                "text": "🔙 Quay lại",
                "callback_data": f"back_to_invite_{user_id}"
            })
            
            keyboard = {
                "inline_keyboard": [keyboard_buttons]
            }
        
        send_telegram_message_with_keyboard(chat_id, message, keyboard)
        
    except Exception as e:
        print(f"❌ Error handling referral list callback: {e}")
        send_telegram_message(chat_id, "❌ Lỗi hiển thị danh sách!")

def handle_link_command(chat_id, user, text):
    """Handle manual link command to connect with referrer"""
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    
    try:
        # Parse command: /link REF123456
        parts = text.split()
        if len(parts) < 2:
            send_telegram_message(chat_id, "❌ Cú pháp: /link <mã_mời>\n\nVí dụ: /link REF000001")
            return
        
        referral_code = parts[1].upper()
        
        # Get user info
        if isinstance(user, dict):
            user_id = user.get('id', 0)
            first_name = user.get('first_name', 'User')
            username = user.get('username', 'N/A')
            telegram_id = user.get('telegram_id', 'N/A')
        else:
            user_id = user[0]
            first_name = user[3] if len(user) > 3 else 'User'
            username = user[2] if len(user) > 2 else 'N/A'
            telegram_id = user[1] if len(user) > 1 else 'N/A'
        
        # Check if user was already referred
        if is_user_referred(user_id):
            # Get referrer information
            referrer = get_referrer_info(user_id)
            if referrer:
                if isinstance(referrer, dict):
                    referrer_id = referrer.get('id', 'N/A')
                    referrer_telegram_id = referrer.get('telegram_id', 'N/A')
                    referrer_name = referrer.get('first_name', 'N/A')
                    referrer_username = referrer.get('username', 'N/A')
                else:
                    referrer_id = referrer[0] if len(referrer) > 0 else 'N/A'
                    referrer_telegram_id = referrer[1] if len(referrer) > 1 else 'N/A'
                    referrer_name = referrer[3] if len(referrer) > 3 else 'N/A'
                    referrer_username = referrer[2] if len(referrer) > 2 else 'N/A'
                
                message = f"""❌ Bạn đã được mời bởi:

🆔 ID: {referrer_id}
📱 Telegram ID: {referrer_telegram_id}
👤 Name: {referrer_name}
🏷️ Username: @{referrer_username if referrer_username != 'N/A' else 'Không có'}

⚠️ Mỗi người chỉ có thể được mời 1 lần."""
            else:
                message = "❌ Bạn đã được mời bởi ai đó rồi! Mỗi người chỉ có thể được mời 1 lần."
            
            send_telegram_message(chat_id, message)
            return
        
        # Extract referrer_id from referral code
        if not referral_code.startswith('REF'):
            send_telegram_message(chat_id, "❌ Mã mời không hợp lệ! Mã mời phải bắt đầu bằng 'REF'")
            return
        
        try:
            referrer_id = int(referral_code[3:])  # Remove 'REF' prefix
        except ValueError:
            send_telegram_message(chat_id, "❌ Mã mời không hợp lệ! Ví dụ: REF000001")
            return
        
        # Check if referrer exists
        referrer = get_user_by_id(referrer_id)
        if not referrer:
            send_telegram_message(chat_id, "❌ Mã mời không tồn tại! Vui lòng kiểm tra lại.")
            return
        
        # Check if user is trying to refer themselves
        if referrer_id == user_id:
            send_telegram_message(chat_id, "❌ Bạn không thể mời chính mình!")
            return
        
        # Process referral
        create_referral_record(referrer_id, user_id, referral_code)
        give_referral_rewards(referrer_id, user_id, referral_code)
        
        # Get referrer name
        referrer_name = referrer.get('first_name', 'User') if isinstance(referrer, dict) else referrer[3] if len(referrer) > 3 else 'User'
        
        # Send success message
        message = f"""🎉 LIÊN KẾT THÀNH CÔNG!

👤 Bạn đã được mời bởi: {referrer_name}
🔗 Mã mời: {referral_code}

💰 Phần thưởng:
• Bạn nhận được: 2 xu (thưởng tham gia)
• {referrer_name} nhận được: 3 xu (thưởng mời)

✅ Giao dịch đã được ghi nhận!
Bạn có thể sử dụng /me để xem số xu hiện tại."""
        
        send_telegram_message(chat_id, message)
        
        # Notify referrer
        try:
            if isinstance(referrer, dict):
                referrer_telegram_id = referrer.get('telegram_id')
            else:
                referrer_telegram_id = referrer[1] if len(referrer) > 1 else None
            
            if referrer_telegram_id:
                # Get current time in Vietnam timezone
                current_time = format_vietnam_time("%d/%m/%Y %H:%M")
                
                notify_message = f"""🎉 CÓ NGƯỜI THAM GIA QUA LINK MỜI!

👤 Tên: {first_name}
🏷️ Username: @{username if username != 'N/A' else 'Không có'}
📱 Telegram ID: {telegram_id}
🔗 Mã mời: {referral_code}
⏰ Thời gian: {current_time}

💰 Bạn nhận được: 3 xu (thưởng mời)

📊 Tổng số người đã mời: {get_referral_count(referrer_id)} người"""
                
                send_telegram_message(referrer_telegram_id, notify_message)
        except Exception as e:
            print(f"❌ Error notifying referrer: {e}")
        
    except Exception as e:
        print(f"❌ Error in handle_link_command: {e}")
        send_telegram_message(chat_id, "❌ Lỗi xử lý liên kết!")

def start_verification_process(job_id, sheerid_url):
    """Start verification process (call main API)"""
    try:
        print(f"🚀 DEBUG: Starting verification process for job {job_id}")
        print(f"🔗 DEBUG: URL: {sheerid_url}")
        print(f"🔍 DEBUG: Function start_verification_process called successfully")
        
        # Check if job is already completed or failed - if so, skip processing
        try:
            if SUPABASE_AVAILABLE:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    job_status = (
                        supabase.table('verification_jobs')
                        .select('status')
                        .eq('job_id', str(job_id))
                        .limit(1)
                        .execute()
                    )
                    if job_status and getattr(job_status, 'data', None):
                        status = job_status.data[0].get('status')
                        print(f"DEBUG: Job {job_id} current status: {status}")
                        if status in ['failed', 'error']:
                            print(f"Job {job_id} already failed with status: {status}, skipping")
                            return
                        if status == 'completed':
                            print(f"Job {job_id} already completed, skipping duplicate API call")
                            return
        except Exception as _:
            # Soft-fail the early guard; we still have later guards
            pass
        
        # Call main verification API
        # Use production domain where webhook is running
        api_url = "https://dqsheerid.vercel.app/start-verification"
        payload = {"url": sheerid_url, "job_id": job_id}
        
        print(f"DEBUG: Calling API: {api_url}")
        print(f"DEBUG: Payload: {payload}")
        # Use optimized session (connection pooling + retry)
        try:
            response = TELEGRAM_SESSION.post(api_url, json=payload, timeout=30)
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response text: {response.text}")
            
            result = response.json()
            print(f"DEBUG: Successfully parsed JSON response")
        except Exception as e:
            print(f"DEBUG: Exception during API call or JSON parsing: {e}")
            import traceback
            traceback.print_exc()
            return
        print(f"DEBUG: Parsed result: {result}")
        print(f"DEBUG: Success status: {result.get('success')}")
        print(f"DEBUG: Success type: {type(result.get('success'))}")
        print(f"DEBUG: Success == True: {result.get('success') == True}")
        print(f"DEBUG: Success is True: {result.get('success') is True}")
        print(f"DEBUG: Result type after parsing: {type(result)}")
        print(f"DEBUG: Result is dict: {isinstance(result, dict)}")
        early_success = False
        try:
            if isinstance(result, dict):
                stage_val = str(result.get('stage') or '').lower()
                early_success = stage_val in ('success','complete','verified') and not result.get('upload_result')
        except Exception:
            early_success = False
        
        # Get user info for notification (prefer Supabase, fallback SQLite)
        user = None
        if SUPABASE_AVAILABLE:
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    vj_resp = supabase.table('verification_jobs').select('user_id').eq('job_id', job_id).limit(1).execute()
                    if vj_resp.data:
                        sb_user_id = vj_resp.data[0]['user_id']
                        u_resp = supabase.table('users').select('id, telegram_id, username, first_name, last_name, coins, is_vip, vip_expiry, created_at').eq('id', sb_user_id).limit(1).execute()
                        if u_resp.data:
                            u = u_resp.data[0]
                            user = (
                                u.get('id'),
                                u.get('telegram_id'),
                                u.get('username'),
                                u.get('first_name'),
                                u.get('last_name'),
                                u.get('coins'),
                                u.get('is_vip'),
                                u.get('vip_expiry'),
                                u.get('created_at')
                            )
            except Exception as e:
                print(f"Supabase lookup failed in start_verification_process: {e}")
        
        if not user:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.id, u.telegram_id, u.username, u.first_name, u.last_name, u.coins, u.is_vip, u.vip_expiry, u.created_at
                FROM verification_jobs vj
                JOIN users u ON vj.user_id = u.id
                WHERE vj.job_id = ?
            ''', (job_id,))
            user = cursor.fetchone()
            conn.close()
        
        if not user:
            print(f"No user found for job {job_id}")
            return
        
        chat_id = user[1]
        username = user[2]
        first_name = user[3]
        last_name = user[4]
        
        # Update job status and send notification
        print(f"DEBUG: Checking success: {result.get('success')}")
        if result.get('success'):
            print(f"DEBUG: Success is True, processing success case")
            print(f"DEBUG: About to call update_verification_job with student_info type: {type(result.get('student_info'))}")
            update_verification_job(
                job_id, 
                'completed',
                result.get('student_info'),
                result.get('card_filename'),
                result.get('upload_result')
            )
            print(f"DEBUG: update_verification_job completed successfully")
            # Always send a single detailed success message later
            sent_early_message = False
            
            print(f"DEBUG: About to process payment deduction...")
            
            # Deduct only on success: VIP free; else try 2 bonus else 2 cash
            print(f"DEBUG: user type: {type(user)}, user value: {user}")
            is_vip = is_vip_active(user)
            print(f"DEBUG: is_vip: {is_vip}")
            coins_now = None
            cash_now = None
            
            # VIP users still pay but have unlimited verifications
            if is_vip:
                print(f"👑 VIP user {user[0]} - Still pays 3 xu/cash but unlimited verifications")
            
            # All users (VIP and non-VIP) pay 3 xu/cash
            if True:  # Changed from elif not is_vip
                # Guard against double charge: in-memory + DB checks
                already_charged = str(job_id) in CHARGED_JOBS
                if SUPABASE_AVAILABLE:
                    try:
                        from supabase_client import get_supabase_client
                        supabase = get_supabase_client()
                        if supabase:
                            q = (
                                supabase.table('transactions')
                                .select('id')
                                .eq('user_id', user[0])
                                .eq('type', 'verify')
                                .eq('job_id', str(job_id))
                                .limit(1)
                                .execute()
                            )
                            if q and getattr(q, 'data', None):
                                already_charged = True
                    except Exception:
                        already_charged = False

                if not already_charged:
                    # Check local SQLite as fallback in case transaction was written there
                    try:
                        conn_chk = sqlite3.connect(DB_PATH)
                        cur_chk = conn_chk.cursor()
                        cur_chk.execute(
                            """
                            SELECT COUNT(1) FROM transactions
                            WHERE user_id = ? AND type = 'verify' AND job_id = ?
                            """,
                            (user[0], str(job_id))
                        )
                        already_charged = (cur_chk.fetchone() or [0])[0] > 0
                        conn_chk.close()
                    except Exception:
                        pass

                if not already_charged:
                    # DISABLED: Polling charging blocked to prevent duplicates
                    print(f"🔇 DISABLED: Polling charging blocked for job {job_id} to prevent duplicates")
                    print(f"🔇 Charging will be handled by main API system in index.py")
                    charged_successfully = True  # Mark as successful to continue with notification
                    was_coin_deducted = False
                    
                    # DISABLED: All charging logic removed to prevent duplicates
                    # Charging is now handled exclusively by index.py API system
                    pass
            # All users (VIP and non-VIP) get current balances after payment
            wallets_after = supabase_get_wallets_by_user_id(user[0])
            if wallets_after:
                cash_now, coins_now = wallets_after
            else:
                # fallback to original values
                coins_now = user[5] if len(user) > 5 else 0
                cash_now = user[6] if len(user) > 6 else 0
            
            # Send success notification
            print(f"DEBUG: About to extract student_info and card_filename")
            print(f"DEBUG: result type: {type(result)}")
            print(f"DEBUG: result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
            print(f"DEBUG: result value: {result}")
            
            # Check if result is still a dict
            if not isinstance(result, dict):
                print(f"❌ ERROR: result is not a dict! Type: {type(result)}, Value: {result}")
                raise Exception(f"Result is not a dict: {type(result)}")
            
            student_info = result.get('student_info') or {}
            print(f"DEBUG: student_info extracted successfully")
            card_filename = result.get('card_filename') or ''
            print(f"DEBUG: card_filename extracted successfully")
            
            # Debug logs
            print(f"DEBUG: student_info type: {type(student_info)}, value: {student_info}")
            print(f"DEBUG: card_filename type: {type(card_filename)}, value: {card_filename}")
            
            # Build success message with updated balances
            balances_line = ""
            if coins_now is not None or cash_now is not None:
                balances_line = f"🪙 Xu còn: {coins_now if coins_now is not None else '?'} | 💵 Cash: {cash_now if cash_now is not None else '?'}\n"
            
            try:
                used_label = "10 Xu (ưu tiên Xu)" if was_coin_deducted else "10 CASH"
            except Exception:
                used_label = "10 CASH"
            
            # DISABLED: Polling notification blocked to prevent duplicates
            print(f"🔇 DISABLED: Polling notification blocked for job {job_id} to prevent duplicates")
            print(f"🔇 Notification will be sent by main API system in index.py")
            
            # DISABLED CODE BELOW - All notifications are now handled by index.py to prevent duplicates
            if False:  # is_vip:
                message = f"""
✅ VERIFY THÀNH CÔNG! (VIP)

🆔 Job ID: `{job_id}`
💰 Đã trừ: {used_label}
👑 VIP: Không giới hạn lần verify
{balances_line}
🎉 Chúc mừng! Bạn đã verify thành công!
                """
            else:
                message = f"""
✅ VERIFY THÀNH CÔNG!

🆔 Job ID: `{job_id}`
💰 Đã trừ: {used_label}
{balances_line}
🎉 Chúc mừng! Bạn đã verify thành công!
                """
            
            # DISABLED: Send success notification (always send one detailed message)
            print(f"🔇 DISABLED: About to send success notification to {chat_id} - BLOCKED")
            if False:  # Disabled notification sending
                try:
                    print(f"DEBUG: Sending success notification to {chat_id}")
                    print(f"DEBUG: Message: {message[:200]}...")
                    send_result = send_telegram_message(chat_id, message)
                    print(f"DEBUG: Send result: {send_result}")
                except Exception as e:
                    print(f"WARN: Failed to send detailed success message: {e}")
                    import traceback
                    traceback.print_exc()
            
        else:
            print(f"DEBUG: Success is False, processing failure case")
            # Guard: ensure result is a dict before using .get in failure path
            if not isinstance(result, dict):
                print(f"WARN: result is not dict in failure path. Coercing. Type={type(result)} Value={result}")
                try:
                    result = {"error": str(result) if result is not None else "Unknown error"}
                except Exception:
                    result = {"error": "Unknown error"}
            # Send failure notification with friendly mapping
            system_error = result.get('systemErrorMessage', '') or ''
            error_ids = str(result.get('errorIds', ''))
            error_msg = result.get('error', 'Không xác định')
            is_fraud = False
            # Map additional cases from response_data
            try:
                resp_data = result.get('response_data') or {}
                cur_step = str((resp_data or {}).get('currentStep','') or '').lower()
                sys_msg = str((resp_data or {}).get('systemErrorMessage','') or '')
                if cur_step == 'pending' or 'reviewing' in error_msg.lower():
                    error_msg = "Tài khoản của bạn đã verify từ trước và đang bị trạng thái Reviewing (đang xem xét), Vui lòng đợi 30p-2 tiếng sau thử lại với Link SheerID mới."
                elif cur_step == 'error' and 'fraud prevention rules' in sys_msg:
                    error_msg = "Bạn phải fake IP qua 🇺🇸 United States 🇺🇸 để lấy link mới rồi quay lại Bot Verify nhé!"
                    is_fraud = True
                elif cur_step == 'sso':
                    error_msg = "Liên kết SheerID đang yêu cầu SSO (đăng nhập). Vui lòng mở link để đăng nhập SSO hoặc lấy link SheerID mới rồi thử lại trong Bot Verify."
            except Exception:
                pass
            if "exceeded the maximum number of verifications" in system_error:
                error_msg = "Tài khoản đã xác minh quá nhiều lần - hoặc đang cố gắng lấy ưu đãi không có."
            elif "noVerification" in error_ids or "noVerification" in error_msg:
                error_msg = """❌ Link đã bị lỗi: noVerification

📋 Nguyên nhân: Link SheerID không tồn tại hoặc đã hết hạn.

🔄 Cách khắc phục:
1. Mở lại trang ChatGPT/Gemini để lấy link mới
2. Đảm bảo link có dạng: services.sheerid.com/verify/...
3. Quay lại bot verify với link mới"""
            elif "rejected due to fraud prevention rules" in system_error or "fraudRulesReject" in error_ids:
                is_fraud = True
                error_msg = """Yêu cầu bị hệ thống SheerID từ chối (Fraud Prevention).

📖 Hướng dẫn khắc phục: https://t.me/channel_sheerid_vip_bot/135

🔄 Nếu vẫn fail, hãy:
1. Mở lại link SheerID trên trình duyệt
2. Submit blank image 3 lần để lấy link mới
3. Quay lại bot để verify với link mới"""
            elif "can not perform step 'COLLECT_PERSONAL_INFO'" in system_error or "invalidStep" in error_ids:
                error_msg = "Hệ thống không thể xác minh bước Sinh viên, vui lòng kiểm tra lại tài khoản, hoặc VPN khi đăng nhập tài khoản."
            
            # Update job status based on fraud detection
            job_status = 'fraud_reject' if is_fraud else 'failed'
            update_verification_job(job_id, job_status)
            print(f"✅ Updated job {job_id} status to {job_status}")
            
            if isinstance(user, dict):
                coins_now = user.get('coins', 0)
            else:
                coins_now = user[5] if len(user) > 5 else 0
            
            # Get user language
            user_lang = 'vi'
            try:
                from supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    user_lang = get_user_language(supabase, chat_id)
            except:
                pass
            
            current_time = format_vietnam_time()
            
            # Multilingual failure messages
            fail_msgs = {
                'vi': f"""❌ VERIFY THẤT BẠI!

🆔 Job ID: {job_id}
⏰ Thời gian: {current_time}
💰 Không trừ xu (thất bại)
🪙 Xu hiện tại: {coins_now} xu

❌ Lỗi: {error_msg}

📖 Hướng dẫn: https://t.me/channel_sheerid_vip_bot/135

🔄 Nếu vẫn fail:
1️⃣ Mở link SheerID trên trình duyệt
2️⃣ Submit blank image 3 lần để lấy link mới
3️⃣ Quay lại bot verify với link mới

📞 Hỗ trợ: @meepzizhere""",
                'en': f"""❌ VERIFICATION FAILED!

🆔 Job ID: {job_id}
⏰ Time: {current_time}
💰 No coins deducted (failed)
🪙 Current coins: {coins_now} xu

❌ Error: {error_msg}

📖 Guide: https://t.me/channel_sheerid_vip_bot/135

🔄 If still failing:
1️⃣ Open SheerID link in browser
2️⃣ Submit blank image 3 times to get new link
3️⃣ Return to bot and verify with new link

📞 Support: @meepzizhere""",
                'zh': f"""❌ 验证失败！

🆔 Job ID: {job_id}
⏰ 时间: {current_time}
💰 未扣除xu（失败）
🪙 当前xu: {coins_now} xu

❌ 错误: {error_msg}

📖 指南: https://t.me/channel_sheerid_vip_bot/135

🔄 如果仍然失败:
1️⃣ 在浏览器中打开SheerID链接
2️⃣ 提交空白图片3次以获取新链接
3️⃣ 返回机器人使用新链接验证

📞 支持: @meepzizhere"""
            }
            message = fail_msgs.get(user_lang, fail_msgs['vi'])
            
            # Send failure notification to user - use plain text to avoid Markdown errors
            print(f"📤 Sending failure notification for job {job_id} to chat_id {chat_id}")
            result = send_telegram_message_plain(chat_id, message)
            print(f"📤 Failure notification send result: {result}")
            
    except Exception as e:
        print(f"Verification process error: {e}")
        update_verification_job(job_id, 'failed')
        
        # Send error notification
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.telegram_id, u.username, u.first_name, u.last_name
                FROM verification_jobs vj
                JOIN users u ON vj.user_id = u.id
                WHERE vj.job_id = ?
            ''', (job_id,))
            user_info = cursor.fetchone()
            conn.close()
            
            if user_info:
                chat_id = user_info[0]
                first_name = user_info[2]
                last_name = user_info[3]
                
                # Get user language
                user_lang = 'vi'
                try:
                    from supabase_client import get_supabase_client
                    supabase = get_supabase_client()
                    if supabase:
                        user_lang = get_user_language(supabase, chat_id)
                except:
                    pass
                
                current_time = format_vietnam_time()
                error_str = str(e)[:200]
                
                # Multilingual error messages
                error_msgs = {
                    'vi': f"""❌ VERIFY LỖI!

🆔 Job ID: {job_id}
⏰ Thời gian: {current_time}
❌ Lỗi: {error_str}

💰 Không bị trừ xu/cash
🔄 Bạn có thể thử lại với link mới

📞 Hỗ trợ: @meepzizhere""",
                    'en': f"""❌ VERIFICATION ERROR!

🆔 Job ID: {job_id}
⏰ Time: {current_time}
❌ Error: {error_str}

💰 No xu/cash deducted
🔄 You can try again with a new link

📞 Support: @meepzizhere""",
                    'zh': f"""❌ 验证错误！

🆔 Job ID: {job_id}
⏰ 时间: {current_time}
❌ 错误: {error_str}

💰 未扣除 xu/cash
🔄 您可以使用新链接重试

📞 支持: @meepzizhere"""
                }
                error_message = error_msgs.get(user_lang, error_msgs['vi'])
                
                print(f"📤 Sending error notification for job {job_id} to chat_id {chat_id}")
                send_telegram_message_plain(chat_id, error_message)
        except Exception as notify_error:
            print(f"⚠️ Failed to send error notification: {notify_error}")

def handle_admin_send_notification(chat_id, notification_text):
    """Send notification to all users from Supabase only"""
    print(f"🚀 BROADCAST THREAD STARTED for chat_id: {chat_id}")
    print(f"📝 Message: {notification_text[:100]}...")
    
    try:
        global BROADCAST_IN_PROGRESS
        
        print(f"🔍 Checking BROADCAST_IN_PROGRESS: {BROADCAST_IN_PROGRESS}")
        if BROADCAST_IN_PROGRESS:
            print(f"⏳ Broadcast already in progress, aborting")
            send_telegram_message(chat_id, "⏳ Hệ thống đang gửi thông báo khác. Vui lòng thử lại sau.")
            return
        
        print(f"✅ Setting BROADCAST_IN_PROGRESS = True")
        BROADCAST_IN_PROGRESS = True
        # EMERGENCY STOP - DỪNG NGAY LẬP TỨC
        if EMERGENCY_STOP:
            print("🚨 EMERGENCY STOP: Không gửi thông báo!")
            send_telegram_message(chat_id, "🚨 Bot đã được dừng khẩn cấp!")
            return
            
        # Check maintenance mode
        if False:  # 🚨 NUCLEAR: Disabled maintenance check
            send_telegram_message(chat_id, "🔧 Bot đang trong chế độ bảo trì! Không thể gửi thông báo.")
            return
            
        # Get all users from Supabase only
        print(f"🔍 Getting users from Supabase...")
        users = []
        
        if not SUPABASE_AVAILABLE:
            print(f"❌ SUPABASE_AVAILABLE is False")
            send_telegram_message(chat_id, "❌ Supabase không khả dụng! Không thể gửi thông báo.")
            BROADCAST_IN_PROGRESS = False
            return
            
        try:
            print(f"📡 Importing supabase_client...")
            from supabase_client import get_supabase_client
            
            print(f"📡 Getting supabase client...")
            supabase = get_supabase_client()
            
            if not supabase:
                print(f"❌ Supabase client is None")
                send_telegram_message(chat_id, "❌ Không thể kết nối Supabase!")
                BROADCAST_IN_PROGRESS = False
                return
            
            print(f"📡 Querying users table...")
            response = supabase.table('users').select('telegram_id, username, first_name').order('created_at', desc=True).execute()
            users = response.data if response.data else []
            print(f"📊 Found {len(users)} users in Supabase")
            
        except Exception as e:
            print(f"❌ Supabase error: {e}")
            import traceback
            traceback.print_exc()
            send_telegram_message(chat_id, f"❌ Lỗi Supabase: {str(e)}")
            BROADCAST_IN_PROGRESS = False
            return
        
        if not users:
            print(f"❌ No users found")
            send_telegram_message(chat_id, "❌ Không có user nào trong hệ thống!")
            BROADCAST_IN_PROGRESS = False
            return
        
        print(f"✅ Ready to send to {len(users)} users")
        
        # Send confirmation to admin
        print(f"📤 Sending confirmation to admin...")
        send_telegram_message(chat_id, f"📢 Đang gửi thông báo cho {len(users)} user...")
        print(f"✅ Confirmation sent")
        
        # Prepare notification message
        notification_message = f"""📢 THÔNG BÁO TỪ ADMIN

{notification_text}

---
SheerID VIP Bot"""
        
        # Send to all users (EXCEPT ADMIN to prevent infinite loop)
        print(f"🔄 Starting broadcast loop...")
        success_count = 0
        failed_count = 0
        skipped_count = 0
        admin_ids = [7162256181]  # Admin telegram IDs to skip
        total_users = len(users)
        
        print(f"📊 Total users to process: {total_users}")
        
        for i, user in enumerate(users, 1):
            if i == 1:
                print(f"🔥 Loop started! Processing first user...")
            # Handle both dict (Supabase) and tuple (SQLite) formats
            if isinstance(user, dict):
                user_telegram_id = user.get('telegram_id')
            else:
                user_telegram_id = user[0]
            
            # Skip admin to prevent infinite loop
            if int(user_telegram_id) in admin_ids:
                print(f"🚫 Skipping admin {user_telegram_id} to prevent infinite loop")
                skipped_count += 1
                continue
            
            # Check emergency stop
            if EMERGENCY_STOP:
                print("🚨 Emergency stop toggled mid-send. Aborting notification.")
                break
                
            try:
                if send_telegram_message(user_telegram_id, notification_message):
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"Failed to send to user {user_telegram_id}: {e}")
                failed_count += 1
            
            # Rate limiting
            import time
            time.sleep(0.03)
            
            # Progress tracking every 50 users
            if i % 50 == 0:
                progress_msg = f"📊 Tiến độ: {i}/{total_users}\n✅ Thành công: {success_count}\n❌ Thất bại: {failed_count}\n⏭️ Bỏ qua: {skipped_count}"
                send_telegram_message(chat_id, progress_msg)
                print(f"📊 PROGRESS: {progress_msg}")
        
        # Send detailed summary to admin
        result_message = f"""🎉 HOÀN THÀNH GỬI THÔNG BÁO!

📊 Tổng số users: {total_users}
✅ Gửi thành công: {success_count}
❌ Gửi thất bại: {failed_count}
⏭️ Bỏ qua (admin): {skipped_count}

📈 Tỷ lệ thành công: {(success_count/(total_users-skipped_count)*100):.1f}%

📝 Nội dung: {notification_text[:100]}{'...' if len(notification_text) > 100 else ''}""" if (total_users - skipped_count) > 0 else "0%"
        
        send_telegram_message(chat_id, result_message)
        
    except Exception as e:
        print(f"Error sending notification: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi gửi thông báo: {str(e)}")
    finally:
        BROADCAST_IN_PROGRESS = False
        print("🏁 Notification broadcast completed, flag reset")


# ============================================
# LOCKET GOLD COMMAND HANDLER
# ============================================
def handle_locket_command(chat_id, user, text):
    """
    Handle /locket command - Locket Gold activation
    Packages:
    - /locket 4m <username> - 4 months (30 cash)
    - /locket 1y <username> - 1 year (50 cash)
    - /locket <username> - Default 1 year (50 cash)
    """
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    
    try:
        # Get user info
        if isinstance(user, dict):
            user_id = user.get('id', 0)
            telegram_id = user.get('telegram_id', 0)
            coins = user.get('coins', 0)
            cash = user.get('cash', 0)
            first_name = user.get('first_name', 'User')
        else:
            user_id = user[0]
            telegram_id = user[1]
            coins = user[4] if len(user) > 4 else 0
            cash = user[8] if len(user) > 8 else 0
            first_name = user[3] if len(user) > 3 else 'User'
        
        # Parse command
        parts = text.split()
        
        # If no username provided, show instructions
        if len(parts) < 2:
            message = """🎁 <b>LOCKET GOLD PREMIUM</b>

✨ Tính năng:
• Unlimited widgets
• Custom themes & fonts
• No ads
• Priority support

📦 <b>Gói dịch vụ:</b>
• Gói 4 tháng: 30 Cash
• Gói 1 năm: 50 Cash ⭐

📝 Cách dùng:
/locket 4m <username>  (4 tháng - 30 Cash)
/locket 1y <username>  (1 năm - 50 Cash)
/locket <username>     (mặc định 1 năm)

Ví dụ:
/locket 4m john_doe123
/locket 1y locket.cam/john_doe123
/locket john_doe123

💡 Lưu ý: Sau khi kích hoạt, bạn PHẢI cài DNS profile để giữ Gold!"""
            
            send_telegram_message(chat_id, message)
            return
        
        # Determine package type and username
        package_type = '1year'  # Default
        price = 50  # Default
        username = None
        
        if len(parts) == 2:
            # /locket <username> - default 1 year
            username = parts[1].strip()
            package_type = '1year'
            price = 50
        elif len(parts) >= 3:
            # /locket 4m <username> or /locket 1y <username>
            package_arg = parts[1].lower()
            username = parts[2].strip()
            
            if package_arg == '4m':
                package_type = '4months'
                price = 30
            elif package_arg == '1y':
                package_type = '1year'
                price = 50
            else:
                # Invalid package, treat as username
                username = parts[1].strip()
                package_type = '1year'
                price = 50
        
        if not username:
            send_telegram_message(chat_id, "❌ Vui lòng nhập username Locket")
            return
        
        # Extract username from link if provided
        if "locket.cam/" in username:
            username = username.split("locket.cam/")[-1].split("?")[0]
        
        # Package display names
        package_names = {
            '4months': 'Gói 4 tháng',
            '1year': 'Gói 1 năm'
        }
        package_display = package_names.get(package_type, 'Gói 1 năm')
        
        # Check balance - ONLY cash, no coins
        if cash < price:
            message = f"""❌ Không đủ Cash!

💵 CASH hiện tại: {cash}
💰 Cần: {price} Cash ({package_display})

💡 Dùng /nap để nạp thêm
🌍 Dùng /crypto để nạp crypto

⚠️ Lưu ý: Locket Gold chỉ thanh toán bằng Cash, không dùng Xu được."""
            send_telegram_message(chat_id, message)
            return
        
        # Send processing message
        processing_msg = f"""⏳ <b>Đang xử lý...</b>

👤 Username: <code>{username}</code>
📦 Gói: {package_display} ({price} Cash)
🔍 Đang phân giải UID..."""
        
        msg_id = send_telegram_message(chat_id, processing_msg, parse_mode='HTML')
        
        # Resolve UID (sync wrapper for async function)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        uid = loop.run_until_complete(locket.resolve_uid(username))
        
        if not uid:
            edit_telegram_message(chat_id, msg_id, "❌ Không tìm thấy user Locket này!")
            return
        
        # Check current status
        edit_telegram_message(chat_id, msg_id, f"""⏳ <b>Đang kiểm tra trạng thái...</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>
🔍 Đang kiểm tra Gold...""")
        
        status = loop.run_until_complete(locket.check_status(uid))
        
        if status and status.get('active'):
            edit_telegram_message(chat_id, msg_id, f"""✅ <b>User đã có Gold rồi!</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>
⏰ Hết hạn: {status.get('expires', 'N/A')}

💡 Không cần kích hoạt lại.""")
            return
        
        # Check if user has purchased this username before
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        previous_activation = supabase.table('locket_activations').select('*').eq('telegram_id', telegram_id).eq('locket_username', username).eq('status', 'success').order('created_at', desc=True).limit(1).execute()
        
        # Determine if this is a re-activation (FREE) or new purchase (20 cash)
        is_reactivation = previous_activation.data and len(previous_activation.data) > 0
        
        if is_reactivation:
            # FREE re-activation
            payment_type = 'free_reactivation'
            amount = 0
            
            edit_telegram_message(chat_id, msg_id, f"""🔄 <b>KÍCH HOẠT LẠI MIỄN PHÍ</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>
📦 Gói: {package_display}

✅ Bạn đã từng mua username này trước đó
💰 Phí: <b>MIỄN PHÍ</b>

🔍 Đang kích hoạt lại...""")
            
            # No payment deduction
            # No transaction log
        else:
            # New purchase - check balance
            if cash < price:
                message = f"""❌ Không đủ Cash!

💵 CASH hiện tại: {cash}
💰 Cần: {price} Cash ({package_display})

💡 Dùng /nap để nạp thêm
🌍 Dùng /crypto để nạp crypto

⚠️ Lưu ý: Locket Gold chỉ thanh toán bằng Cash, không dùng Xu được."""
                edit_telegram_message(chat_id, msg_id, message)
                return
            
            # Deduct payment
            payment_type = 'cash'
            amount = price
            
            new_cash = cash - amount
            supabase.table('users').update({'cash': new_cash}).eq('telegram_id', telegram_id).execute()
            
            # Log transaction
            supabase.table('transactions').insert({
                'user_id': user_id,
                'type': 'locket_gold_purchase',
                'amount': -amount,
                'description': f"Locket Gold {package_display} - {username}"
            }).execute()
        
        # Create activation record
        activation = supabase.table('locket_activations').insert({
            'telegram_id': telegram_id,
            'locket_username': username,
            'locket_uid': uid,
            'status': 'processing',
            'payment_type': payment_type,
            'amount_charged': amount,
            'package_type': package_type
        }).execute()
        
        activation_id = activation.data[0]['id']
        
        # Update message
        if is_reactivation:
            edit_telegram_message(chat_id, msg_id, f"""⚡ <b>ĐANG KÍCH HOẠT LẠI GOLD...</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>
📦 Gói: {package_display}
💰 Phí: <b>MIỄN PHÍ</b>

🔄 Đang inject receipt vào RevenueCat...""")
        else:
            edit_telegram_message(chat_id, msg_id, f"""⚡ <b>ĐANG KÍCH HOẠT GOLD...</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>
📦 Gói: {package_display}
💰 Đã trừ: {price} Cash

🔄 Đang inject receipt vào RevenueCat...""")
        
        # Get token config and inject Gold
        token_config = locket.get_token_config()
        success, msg_result = loop.run_until_complete(locket.inject_gold(uid, token_config))
        
        if success:
            # Create NextDNS profile
            edit_telegram_message(chat_id, msg_id, f"""✅ <b>Gold đã active!</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>

🛡️ Đang tạo Anti-Revoke DNS...""")
            
            pid, link = loop.run_until_complete(nextdns.create_profile())
            
            # Update activation record
            supabase.table('locket_activations').update({
                'status': 'success',
                'nextdns_profile_id': pid,
                'nextdns_link': link,
                'completed_at': 'now()'
            }).eq('id', activation_id).execute()
            
            # Send success message
            dns_instructions = ""
            if link and pid:
                dns_instructions = f"""
🛡️ <b>HƯỚNG DẪN QUAN TRỌNG</b>:

1️⃣ Vào App Locket kiểm tra đã có <b>Gold</b> chưa.
2️⃣ Nếu đã có, tiến hành <b>CÀI DNS NGAY</b>:

📱 <b>iOS</b>: <a href="{link}">Bấm vào đây để cài</a>
(Mở link bằng <b>Safari</b> → Cho phép → Cài đặt Profile)

🤖 <b>Android</b>: <code>{pid}.dns.nextdns.io</code>
(Cài đặt → Mạng → Private DNS)

💡 <b>Lưu ý</b>: Bắt buộc cài DNS để không bị mất Gold!"""
            else:
                dns_instructions = "\n⚠️ Không thể tạo DNS profile. Vui lòng liên hệ admin."
            
            # Different success message based on payment type
            if is_reactivation:
                final_message = f"""🎉 <b>KÍCH HOẠT LẠI THÀNH CÔNG!</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>
📦 Gói: {package_display}

💰 <b>Thanh toán:</b>
• Phí kích hoạt lại: <b>MIỄN PHÍ</b> ✅
• (Đã mua trước đó)
{dns_instructions}

⚠️ <b>LẦN NÀY PHẢI CÀI DNS</b> nếu không sẽ mất Gold lại!"""
            else:
                final_message = f"""🎉 <b>KÍCH HOẠT THÀNH CÔNG!</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>
📦 Gói: {package_display}

💰 <b>Thanh toán:</b>
• Số dư ban đầu: {cash} Cash
• Phí kích hoạt: -{price} Cash
• Số dư còn lại: {cash - price} Cash
{dns_instructions}

💡 <b>Lưu ý:</b> Nếu quên cài DNS và mất Gold, dùng lại /locket {username} để kích hoạt lại <b>MIỄN PHÍ</b>!"""
            
            edit_telegram_message(chat_id, msg_id, final_message)
            
        else:
            # Failed
            if not is_reactivation:
                # Refund only if it was a paid purchase
                new_cash = cash
                supabase.table('users').update({'cash': new_cash}).eq('telegram_id', telegram_id).execute()
            
            # Update activation record
            supabase.table('locket_activations').update({
                'status': 'failed',
                'error_message': msg_result,
                'completed_at': 'now()'
            }).eq('id', activation_id).execute()
            
            # Send error message
            if is_reactivation:
                error_message = f"""❌ <b>Kích hoạt lại thất bại</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>
📦 Gói: {package_display}

🔍 Lý do: {msg_result}

 Vui lòng thử lại sau hoặc liên hệ admin."""
            else:
                error_message = f"""❌ <b>Kích hoạt thất bại</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>
📦 Gói: {package_display}

🔍 Lý do: {msg_result}

💰 Đã hoàn tiền: {price} Cash

💡 Vui lòng thử lại sau hoặc liên hệ admin."""
            
            edit_telegram_message(chat_id, msg_id, error_message)
        
        loop.close()
        
    except Exception as e:
        print(f"❌ Error in handle_locket_command: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi xử lý lệnh /locket: {str(e)}")


# ============================================
# RELOCKET COMMAND HANDLER - FREE RE-ACTIVATION
# ============================================
def handle_relocket_command(chat_id, user, text):
    """
    Handle /relocket command - Free re-activation for previously purchased usernames
    
    Logic:
    - Check if user has successfully activated this username before
    - If yes, re-activate for FREE (no charge)
    - If no, show error message
    """
    if not user:
        send_telegram_message(chat_id, "❌ Vui lòng /start trước")
        return
    
    try:
        # Get user info
        if isinstance(user, dict):
            telegram_id = user.get('telegram_id', 0)
        else:
            telegram_id = user[1]
        
        # Parse command
        parts = text.split(maxsplit=1)
        
        # If no username provided, show instructions
        if len(parts) < 2:
            message = """🔄 <b>KÍCH HOẠT LẠI LOCKET GOLD</b>

💡 Dành cho user đã mua nhưng quên cài DNS và bị mất Gold.

📝 Cách dùng:
/relocket <username>

Ví dụ:
/relocket john_doe123
/relocket locket.cam/john_doe123

✅ <b>Miễn phí</b> nếu bạn đã từng mua username này trước đó!
❌ Nếu chưa từng mua, vui lòng dùng /locket"""
            
            send_telegram_message(chat_id, message)
            return
        
        username = parts[1].strip()
        
        # Extract username from link if provided
        if "locket.cam/" in username:
            username = username.split("locket.cam/")[-1].split("?")[0]
        
        # Check if user has purchased this username before
        from supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        # Query locket_activations table for successful activations
        previous_activation = supabase.table('locket_activations').select('*').eq('telegram_id', telegram_id).eq('locket_username', username).eq('status', 'success').order('created_at', desc=True).limit(1).execute()
        
        if not previous_activation.data or len(previous_activation.data) == 0:
            message = f"""❌ <b>Không tìm thấy lịch sử mua</b>

👤 Username: <code>{username}</code>

💡 Bạn chưa từng mua Locket Gold cho username này.
Vui lòng dùng /locket để mua lần đầu (20 cash).

📋 Lệnh /relocket chỉ dành cho user đã mua nhưng quên cài DNS."""
            
            send_telegram_message(chat_id, message)
            return
        
        # User has purchased before - proceed with FREE re-activation
        prev_data = previous_activation.data[0]
        uid = prev_data.get('locket_uid')
        
        # Send processing message
        processing_msg = f"""🔄 <b>ĐANG KÍCH HOẠT LẠI...</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>
💰 Phí: <b>MIỄN PHÍ</b> (đã mua trước đó)

🔍 Đang kiểm tra trạng thái..."""
        
        msg_id = send_telegram_message(chat_id, processing_msg, parse_mode='HTML')
        
        # Check current status
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        status = loop.run_until_complete(locket.check_status(uid))
        
        if status and status.get('active'):
            edit_telegram_message(chat_id, msg_id, f"""✅ <b>User vẫn còn Gold!</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>
⏰ Hết hạn: {status.get('expires', 'N/A')}

💡 Không cần kích hoạt lại. Hãy đảm bảo đã cài DNS profile!""")
            loop.close()
            return
        
        # Create re-activation record
        activation = supabase.table('locket_activations').insert({
            'telegram_id': telegram_id,
            'locket_username': username,
            'locket_uid': uid,
            'status': 'processing',
            'payment_type': 'free_reactivation',
            'amount_charged': 0
        }).execute()
        
        activation_id = activation.data[0]['id']
        
        # Update message
        edit_telegram_message(chat_id, msg_id, f"""⚡ <b>ĐANG KÍCH HOẠT LẠI GOLD...</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>
💰 Phí: <b>MIỄN PHÍ</b>

🔄 Đang inject receipt vào RevenueCat...""")
        
        # Get token config and inject Gold
        token_config = locket.get_token_config()
        success, msg_result = loop.run_until_complete(locket.inject_gold(uid, token_config))
        
        if success:
            # Create NextDNS profile
            edit_telegram_message(chat_id, msg_id, f"""✅ <b>Gold đã active lại!</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>

🛡️ Đang tạo Anti-Revoke DNS mới...""")
            
            pid, link = loop.run_until_complete(nextdns.create_profile())
            
            # Update activation record
            supabase.table('locket_activations').update({
                'status': 'success',
                'nextdns_profile_id': pid,
                'nextdns_link': link,
                'completed_at': 'now()'
            }).eq('id', activation_id).execute()
            
            # Send success message
            dns_instructions = ""
            if link and pid:
                dns_instructions = f"""
🛡️ <b>HƯỚNG DẪN QUAN TRỌNG</b>:

1️⃣ Vào App Locket kiểm tra đã có <b>Gold</b> chưa.
2️⃣ Nếu đã có, tiến hành <b>CÀI DNS NGAY</b>:

📱 <b>iOS</b>: <a href="{link}">Bấm vào đây để cài</a>
(Mở link bằng <b>Safari</b> → Cho phép → Cài đặt Profile)

🤖 <b>Android</b>: <code>{pid}.dns.nextdns.io</code>
(Cài đặt → Mạng → Private DNS)

⚠️ <b>LẦN NÀY PHẢI CÀI DNS</b> nếu không sẽ mất Gold lại!"""
            else:
                dns_instructions = "\n⚠️ Không thể tạo DNS profile. Vui lòng liên hệ admin."
            
            final_message = f"""🎉 <b>KÍCH HOẠT LẠI THÀNH CÔNG!</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>
📅 Gói: GOLD (1 năm)

💰 <b>Thanh toán:</b>
• Phí kích hoạt lại: <b>MIỄN PHÍ</b> ✅
• (Đã mua trước đó)
{dns_instructions}"""
            
            edit_telegram_message(chat_id, msg_id, final_message)
            
        else:
            # Failed
            supabase.table('locket_activations').update({
                'status': 'failed',
                'error_message': msg_result,
                'completed_at': 'now()'
            }).eq('id', activation_id).execute()
            
            # Send error message
            error_message = f"""❌ <b>Kích hoạt lại thất bại</b>

👤 Username: <code>{username}</code>
🆔 UID: <code>{uid}</code>

🔍 Lý do: {msg_result}

💡 Vui lòng thử lại sau hoặc liên hệ admin."""
            
            edit_telegram_message(chat_id, msg_id, error_message)
        
        loop.close()
        
    except Exception as e:
        print(f"❌ Error in handle_relocket_command: {e}")
        import traceback
        traceback.print_exc()
        send_telegram_message(chat_id, f"❌ Lỗi xử lý lệnh /locket: {str(e)}")


# Initialize database on startup
init_database()

# Load bot configuration from Supabase on startup
load_bot_config()

if __name__ == '__main__':
    # Load configuration on startup from Supabase
    load_bot_config()
    app.run(debug=True)





