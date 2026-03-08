"""
Multi-Language Handler for Red Envelope Production System

Provides translations for all user-facing messages in:
- Vietnamese (vi)
- English (en)
- Chinese (zh)

Validates Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

from typing import Dict, List

# Translation dictionary with all supported languages
MESSAGES: Dict[str, Dict[str, str]] = {
    'vi': {
        'too_slow': 'Chúc may mắn lần sau, bạn chậm tay một xíu!',
        'already_claimed_today': 'Bạn đã nhận bao lì xì hôm nay rồi. Quay lại vào ngày mai!',
        'claim_success': 'Chúc mừng! Bạn đã nhận được {amount} cash!',
        'auth_required': 'Vui lòng đăng nhập để nhận bao lì xì',
        'error_occurred': 'Đã xảy ra lỗi. Vui lòng thử lại.',
        'envelope_available': 'Bao lì xì mới xuất hiện!',
        'recent_claims': 'Người nhận gần đây',
        'not_found': 'Không tìm thấy bao lì xì này',
        'user_not_found': 'Không tìm thấy tài khoản. Vui lòng /start bot trước!',
        'invalid_id': 'Telegram ID không hợp lệ',
        'rate_limit': 'Bạn đang thử quá nhanh. Vui lòng đợi một chút.',
        'claim_success_with_balance': 'Chúc mừng! Bạn đã nhận được {amount} cash!\n\n💰 Số dư hiện tại: {balance} cash'
    },
    'en': {
        'too_slow': 'Better luck next time, you were a bit slow!',
        'already_claimed_today': "You've already claimed an envelope today. Come back tomorrow!",
        'claim_success': 'Congratulations! You received {amount} cash!',
        'auth_required': 'Please log in to claim envelopes',
        'error_occurred': 'An error occurred. Please try again.',
        'envelope_available': 'New red envelope appeared!',
        'recent_claims': 'Recent Claims',
        'not_found': 'Red envelope not found',
        'user_not_found': 'User not found. Please /start the bot first!',
        'invalid_id': 'Invalid Telegram ID',
        'rate_limit': "You're trying too fast. Please wait a moment.",
        'claim_success_with_balance': 'Congratulations! You received {amount} cash!\n\n💰 Current balance: {balance} cash'
    },
    'zh': {
        'too_slow': '祝你下次好运，你慢了一点！',
        'already_claimed_today': '你今天已经领取过红包了。明天再来！',
        'claim_success': '恭喜！你获得了 {amount} 现金！',
        'auth_required': '请登录以领取红包',
        'error_occurred': '发生错误。请重试。',
        'envelope_available': '新红包出现了！',
        'recent_claims': '最近领取',
        'not_found': '找不到红包',
        'user_not_found': '找不到用户。请先 /start 机器人！',
        'invalid_id': '无效的 Telegram ID',
        'rate_limit': '你尝试得太快了。请稍等片刻。',
        'claim_success_with_balance': '恭喜！你获得了 {amount} 现金！\n\n💰 当前余额：{balance} 现金'
    }
}


def get_message(language: str, key: str, **kwargs) -> str:
    """
    Get translated message for given key and language
    
    Args:
        language: Language code (vi, en, zh)
        key: Message key
        **kwargs: Format parameters for message
        
    Returns:
        Translated and formatted message
    """
    # Default to English if language not supported
    lang = language if language in MESSAGES else 'en'
    
    # Get message, fallback to English if key not found
    message = MESSAGES[lang].get(key, MESSAGES['en'].get(key, key))
    
    # Format message with parameters if provided
    if kwargs:
        try:
            return message.format(**kwargs)
        except KeyError:
            # If formatting fails, return unformatted message
            return message
    
    return message


def get_supported_languages() -> List[str]:
    """
    Get list of supported language codes
    
    Returns:
        List of language codes
    """
    return list(MESSAGES.keys())


def translate(key: str, language: str, **kwargs) -> str:
    """
    Alias for get_message for consistency with design document
    
    Args:
        key: Message key
        language: Language code (vi, en, zh)
        **kwargs: Format parameters for message
        
    Returns:
        Translated and formatted message
    """
    return get_message(language, key, **kwargs)
