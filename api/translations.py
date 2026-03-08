# Multilingual support for Telegram Bot
# Supported languages: Vietnamese (vi), English (en), Chinese (zh)
# NOTE: This file is for reference/testing only. 
# The actual translations are embedded in telegram.py for Vercel deployment.

TRANSLATIONS = {
    # Welcome messages
    'welcome_message': {
        'vi': '🎉 Chào mừng bạn đến với SheerID VIP Bot!\n\n📋 Lệnh cơ bản:\n/me - Xem thông tin tài khoản\n/verify <link> - Xác minh sinh viên\n/checkin - Điểm danh nhận xu\n/shop - Cửa hàng sản phẩm\n/lang - Đổi ngôn ngữ\n\n💡 Gửi /help để xem hướng dẫn chi tiết\n📢 Kênh: https://t.me/channel_sheerid_vip_bot',
        'en': '🎉 Welcome to SheerID VIP Bot!\n\n📋 Basic commands:\n/me - View account info\n/verify <link> - Student verification\n/checkin - Daily check-in\n/shop - Product store\n/lang - Change language\n\n💡 Send /help for detailed guide\n📢 Channel: https://t.me/channel_sheerid_vip_bot',
        'zh': '🎉 欢迎使用 SheerID VIP 机器人！\n\n📋 基本命令：\n/me - 查看账户信息\n/verify <link> - 学生验证\n/checkin - 每日签到\n/shop - 产品商店\n/lang - 更改语言\n\n💡 发送 /help 查看详细指南\n📢 频道: https://t.me/channel_sheerid_vip_bot'
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
        'vi': '📋 Hướng dẫn sử dụng SheerID VIP Bot\n\n🔹 Lệnh cơ bản:\n/start - Khởi động bot\n/me - Xem thông tin tài khoản\n/verify <link> - Xác minh sinh viên\n/vc <link> - Xác minh giáo viên\n/shop - Cửa hàng sản phẩm\n/checkin - Điểm danh nhận xu\n/giftcode <code> - Sử dụng mã quà\n/nap - Hướng dẫn nạp tiền\n/crypto - Nạp tiền bằng crypto\n/lang - Đổi ngôn ngữ\n\n💰 Hệ thống tiền tệ:\n🪙 Xu: Dùng để verify\n💵 Cash: Dùng để mua VIP, sản phẩm\n\n📞 Hỗ trợ: @meepzizhere',
        'en': '📋 SheerID VIP Bot User Guide\n\n🔹 Basic Commands:\n/start - Start bot\n/me - View account info\n/verify <link> - Student verification\n/vc <link> - Teacher verification\n/shop - Product store\n/checkin - Daily check-in\n/giftcode <code> - Use gift code\n/nap - Top-up guide\n/crypto - Crypto deposit\n/lang - Change language\n\n💰 Currency System:\n🪙 Coins: Used for verification\n💵 Cash: Used for VIP, products\n\n📞 Support: @meepzizhere',
        'zh': '📋 SheerID VIP 机器人使用指南\n\n🔹 基本命令：\n/start - 启动机器人\n/me - 查看账户信息\n/verify <link> - 学生验证\n/vc <link> - 教师验证\n/shop - 产品商店\n/checkin - 每日签到\n/giftcode <code> - 使用礼品码\n/nap - 充值指南\n/crypto - 加密货币充值\n/lang - 更改语言\n\n💰 货币系统：\n🪙 金币：用于验证\n💵 现金：用于VIP、产品\n\n📞 支持：@meepzizhere'
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
        'vi': '❌ Không đủ Xu/Cash!\n\n💵 CASH: {cash} | 🪙 Xu: {coins}\n💰 Cần: 3 Xu/Cash\n\n💡 Dùng /nap để nạp thêm\n🌍 Dùng /crypto để nạp crypto',
        'en': '❌ Insufficient Coins/Cash!\n\n💵 CASH: {cash} | 🪙 Coins: {coins}\n💰 Need: 3 Coins/Cash\n\n💡 Use /nap to top up\n🌍 Use /crypto for crypto deposit',
        'zh': '❌ 金币/现金不足！\n\n💵 现金: {cash} | 🪙 金币: {coins}\n💰 需要: 3 金币/现金\n\n💡 使用 /nap 充值\n🌍 使用 /crypto 加密货币充值'
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
    'account_title': {'vi': '👤 Thông tin cá nhân:', 'en': '👤 Account Information:', 'zh': '👤 账户信息：'},
    'account_id': {'vi': '🆔 ID', 'en': '🆔 ID', 'zh': '🆔 ID'},
    'account_name': {'vi': '👤 Tên', 'en': '👤 Name', 'zh': '👤 姓名'},
    'account_username': {'vi': '📱 Username', 'en': '📱 Username', 'zh': '📱 用户名'},
    'account_coins': {'vi': '🪙 Số dư Xu', 'en': '🪙 Coins Balance', 'zh': '🪙 金币余额'},
    'account_cash': {'vi': '💵 Số dư CASH', 'en': '💵 Cash Balance', 'zh': '💵 现金余额'},
    'account_vip': {'vi': '👑 VIP', 'en': '👑 VIP', 'zh': '👑 VIP'},
    'account_joined': {'vi': '📅 Tham gia', 'en': '📅 Joined', 'zh': '📅 加入时间'},
    'account_rate': {'vi': '💰 Tỷ giá', 'en': '💰 Exchange Rate', 'zh': '💰 汇率'},
    'account_rate_info': {'vi': '• 1 xu = 1,000 VNĐ\n• 1 cash = 1,000 VNĐ', 'en': '• 1 coin = 1,000 VND\n• 1 cash = 1,000 VND', 'zh': '• 1 金币 = 1,000 越南盾\n• 1 现金 = 1,000 越南盾'},
    'account_deposit': {'vi': '🔗 Nạp cash: /nap', 'en': '🔗 Deposit: /nap', 'zh': '🔗 充值: /nap'},
    'account_verify_title': {'vi': '📊 Verify:', 'en': '📊 Verification:', 'zh': '📊 验证：'},
    'account_payment_title': {'vi': '💳 Nạp tiền:', 'en': '💳 Payments:', 'zh': '💳 充值记录：'},
    'account_recent_jobs': {'vi': '📝 5 job gần nhất:', 'en': '📝 Recent 5 jobs:', 'zh': '📝 最近5个任务：'},
    'account_tip': {'vi': '💡 Sử dụng /verify (URL) để xác minh SheerID', 'en': '💡 Use /verify (URL) to verify SheerID', 'zh': '💡 使用 /verify (URL) 进行 SheerID 验证'},
    'account_support': {'vi': '❓ Hỗ trợ: @meepzizhere', 'en': '❓ Support: @meepzizhere', 'zh': '❓ 支持: @meepzizhere'},
    'account_channel': {'vi': '📢 Kênh thông báo: https://t.me/channel_sheerid_vip_bot', 'en': '📢 Channel: https://t.me/channel_sheerid_vip_bot', 'zh': '📢 频道: https://t.me/channel_sheerid_vip_bot'},
    
    # Currency types
    'coins': {'vi': 'xu', 'en': 'coins', 'zh': '金币'},
    'cash': {'vi': 'cash', 'en': 'cash', 'zh': '现金'},
    
    # Seller notifications
    'seller_welcome': {
        'vi': '🎉 Chào mừng bạn đã trở thành Seller!\n\n✅ Tài khoản Seller API của bạn đã được tạo thành công.\n\n📋 Thông tin tài khoản:\n🆔 Seller ID: {seller_id}\n🔑 API Key: {api_key}\n💰 Credits: {credits}\n\n📚 Hướng dẫn API: https://dqsheerid.vercel.app/docs\n\n💳 Mua thêm credits: /buycredits [số_lượng]\n💱 Tỷ giá: 3 cash = 1 credit\n\n⚠️ Lưu ý: Hãy lưu API Key này cẩn thận!\n📞 Hỗ trợ: @meepzizhere',
        'en': '🎉 Welcome! You are now a Seller!\n\n✅ Your Seller API account has been created successfully.\n\n📋 Account Info:\n🆔 Seller ID: {seller_id}\n🔑 API Key: {api_key}\n💰 Credits: {credits}\n\n📚 API Guide: https://dqsheerid.vercel.app/docs\n\n💳 Buy more credits: /buycredits [amount]\n💱 Rate: 3 cash = 1 credit\n\n⚠️ Note: Please save this API Key carefully!\n📞 Support: @meepzizhere',
        'zh': '🎉 欢迎！您现在是卖家了！\n\n✅ 您的卖家API账户已成功创建。\n\n📋 账户信息：\n🆔 卖家ID: {seller_id}\n🔑 API密钥: {api_key}\n💰 积分: {credits}\n\n📚 API指南: https://dqsheerid.vercel.app/docs\n\n💳 购买更多积分: /buycredits [数量]\n💱 汇率: 3 cash = 1 credit\n\n⚠️ 注意：请妥善保存此API密钥！\n📞 支持: @meepzizhere'
    },
    'seller_admin_created': {
        'vi': '✅ Seller đã được tạo thành công!\n\n🆔 ID: {seller_id}\n👤 Tên: {name}\n🔑 API Key: {api_key}\n💰 Credits: {credits}\n📱 Telegram ID: {telegram_id}\n\n⚠️ Lưu API Key này, không thể xem lại!',
        'en': '✅ Seller created successfully!\n\n🆔 ID: {seller_id}\n👤 Name: {name}\n🔑 API Key: {api_key}\n💰 Credits: {credits}\n📱 Telegram ID: {telegram_id}\n\n⚠️ Save this API Key, cannot view again!',
        'zh': '✅ 卖家创建成功！\n\n🆔 ID: {seller_id}\n👤 名称: {name}\n🔑 API密钥: {api_key}\n💰 积分: {credits}\n📱 Telegram ID: {telegram_id}\n\n⚠️ 保存此API密钥，无法再次查看！'
    },
    'buycredits_help': {
        'vi': '📊 Mua Credits cho Seller API\n\nCú pháp: /buycredits <số_credits>\n\n💱 Tỷ giá: {rate} cash = 1 credit\n💵 Cash hiện tại: {cash}\n🎯 Có thể mua tối đa: {max_credits} credits\n\nVí dụ: /buycredits 10 - Mua 10 credits (tốn {example_cost} cash)',
        'en': '📊 Buy Credits for Seller API\n\nUsage: /buycredits <credits>\n\n💱 Rate: {rate} cash = 1 credit\n💵 Current cash: {cash}\n🎯 Max can buy: {max_credits} credits\n\nExample: /buycredits 10 - Buy 10 credits (costs {example_cost} cash)',
        'zh': '📊 购买卖家API积分\n\n用法: /buycredits <积分数>\n\n💱 汇率: {rate} cash = 1 credit\n💵 当前现金: {cash}\n🎯 最多可购买: {max_credits} 积分\n\n示例: /buycredits 10 - 购买10积分 (花费 {example_cost} cash)'
    },
    'buycredits_success': {
        'vi': '✅ Mua credits thành công!\n\n💰 Credits đã mua: +{amount}\n💵 Cash đã trừ: -{cost} (tỷ giá {rate}:1)\n\n📊 Số dư mới:\n• Cash: {new_cash}\n• Seller Credits: {new_credits}\n\n🔑 Seller ID: {seller_id}',
        'en': '✅ Credits purchased successfully!\n\n💰 Credits bought: +{amount}\n💵 Cash deducted: -{cost} (rate {rate}:1)\n\n📊 New balance:\n• Cash: {new_cash}\n• Seller Credits: {new_credits}\n\n🔑 Seller ID: {seller_id}',
        'zh': '✅ 积分购买成功！\n\n💰 购买积分: +{amount}\n💵 扣除现金: -{cost} (汇率 {rate}:1)\n\n📊 新余额:\n• 现金: {new_cash}\n• 卖家积分: {new_credits}\n\n🔑 卖家ID: {seller_id}'
    },
    'buycredits_insufficient': {
        'vi': '❌ Không đủ cash!\n\n💵 Cash hiện tại: {cash}\n💰 Cần: {needed} cash (cho {amount} credits)\n🎯 Có thể mua tối đa: {max_credits} credits\n\n💡 Nạp thêm cash bằng /nap hoặc /crypto',
        'en': '❌ Insufficient cash!\n\n💵 Current cash: {cash}\n💰 Need: {needed} cash (for {amount} credits)\n🎯 Max can buy: {max_credits} credits\n\n💡 Top up cash with /nap or /crypto',
        'zh': '❌ 现金不足！\n\n💵 当前现金: {cash}\n💰 需要: {needed} cash (购买 {amount} 积分)\n🎯 最多可购买: {max_credits} 积分\n\n💡 使用 /nap 或 /crypto 充值'
    },
    'buycredits_no_seller': {
        'vi': '❌ Bạn chưa có tài khoản Seller!\n\n📞 Liên hệ admin để đăng ký Seller API:\n@meepzizhere',
        'en': '❌ You don\'t have a Seller account!\n\n📞 Contact admin to register Seller API:\n@meepzizhere',
        'zh': '❌ 您还没有卖家账户！\n\n📞 联系管理员注册卖家API:\n@meepzizhere'
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
