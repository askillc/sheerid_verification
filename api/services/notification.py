"""
Notification Service - Send notifications to users and admins
Requirements: 4.4, 4.5, 6.1, 6.2, 6.3, 6.4, 6.5
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import sys
import os
import requests

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_client import get_supabase_client


class NotificationService:
    """Service for sending notifications to users and admins"""
    
    def __init__(self):
        self.max_notifications_per_day = 3
        self.rate_limit_window = timedelta(hours=24)
        self.notification_delay_minutes = 5  # Max 5 minutes delay for Gold loss notifications
        
        # Get Telegram bot token from environment
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_chat_id = os.getenv('ADMIN_TELEGRAM_CHAT_ID')
    
    async def notify_gold_loss(self, user_id: int, activation_id: int, reason: Optional[str] = None) -> bool:
        """
        Notify user that Gold was lost
        
        Args:
            user_id: Telegram user ID
            activation_id: ID of the activation
            reason: Reason for Gold loss (optional)
            
        Returns:
            True if notification was sent successfully
        """
        try:
            # Check rate limiting
            if not await self._can_send_notification(user_id):
                print(f"⚠️ Notification rate limited for user {user_id}")
                return False
            
            # Build message
            message = "🚨 Locket Gold Status Lost\n\n"
            message += "❌ Your Locket Gold subscription has been deactivated.\n\n"
            
            if reason:
                message += f"🔍 Reason: {reason}\n\n"
            
            message += "🔄 We are attempting to automatically recover your Gold status.\n"
            message += "⏰ You will receive a notification once recovery is complete.\n\n"
            message += "💡 If automatic recovery fails, please contact support."
            
            # Send notification
            success = await self._send_telegram_notification(user_id, message)
            
            # Record notification in database
            if success:
                await self._record_notification(
                    user_id=user_id,
                    activation_id=activation_id,
                    notification_type='gold_loss',
                    message=message
                )
            
            return success
            
        except Exception as e:
            print(f"❌ Error sending Gold loss notification: {e}")
            return False
    
    async def notify_recovery_success(self, user_id: int, activation_id: int, token_id: int) -> bool:
        """
        Notify user that Gold was successfully recovered
        
        Args:
            user_id: Telegram user ID
            activation_id: ID of the activation
            token_id: ID of the token used for recovery
            
        Returns:
            True if notification was sent successfully
        """
        try:
            # Check rate limiting
            if not await self._can_send_notification(user_id):
                print(f"⚠️ Notification rate limited for user {user_id}")
                return False
            
            # Build message
            message = "✅ Locket Gold Recovered Successfully!\n\n"
            message += "🎉 Your Locket Gold subscription has been automatically restored.\n\n"
            message += "✨ You can continue enjoying all Gold features.\n"
            message += "🔒 Make sure your DNS profile remains installed.\n\n"
            message += "💡 Tip: Verify your DNS profile regularly to prevent future issues."
            
            # Send notification
            success = await self._send_telegram_notification(user_id, message)
            
            # Record notification in database
            if success:
                await self._record_notification(
                    user_id=user_id,
                    activation_id=activation_id,
                    notification_type='recovery_success',
                    message=message
                )
            
            return success
            
        except Exception as e:
            print(f"❌ Error sending recovery success notification: {e}")
            return False
    
    async def notify_recovery_failed(self, user_id: int, activation_id: int, attempts_count: int) -> bool:
        """
        Notify user that automatic recovery failed
        
        Args:
            user_id: Telegram user ID
            activation_id: ID of the activation
            attempts_count: Number of failed recovery attempts
            
        Returns:
            True if notification was sent successfully
        """
        try:
            # Check rate limiting
            if not await self._can_send_notification(user_id):
                print(f"⚠️ Notification rate limited for user {user_id}")
                return False
            
            # Build message
            message = "⚠️ Locket Gold Recovery Failed\n\n"
            message += f"❌ Automatic recovery failed after {attempts_count} attempts.\n\n"
            message += "📋 Manual Recovery Instructions:\n"
            message += "1. Verify your DNS profile is installed\n"
            message += "2. Check your internet connection\n"
            message += "3. Contact support if the issue persists\n\n"
            message += "💬 Support: @meepzizhere"
            
            # Send notification
            success = await self._send_telegram_notification(user_id, message)
            
            # Record notification in database
            if success:
                await self._record_notification(
                    user_id=user_id,
                    activation_id=activation_id,
                    notification_type='recovery_failed',
                    message=message
                )
            
            return success
            
        except Exception as e:
            print(f"❌ Error sending recovery failed notification: {e}")
            return False
    
    async def notify_admin_recovery_failure(self, activation_id: int, user_id: int, attempts_count: int) -> bool:
        """
        Notify admin about recovery failure after max attempts
        
        Args:
            activation_id: ID of the activation
            user_id: Telegram user ID
            attempts_count: Number of failed recovery attempts
            
        Returns:
            True if notification was sent successfully
        """
        try:
            if not self.admin_chat_id:
                print("⚠️ Admin chat ID not configured")
                return False
            
            # Build admin message
            message = "🚨 ADMIN ALERT: Recovery Failure\n\n"
            message += f"❌ Maximum recovery attempts reached\n\n"
            message += f"📊 Details:\n"
            message += f"• Activation ID: {activation_id}\n"
            message += f"• User ID: {user_id}\n"
            message += f"• Failed Attempts: {attempts_count}\n\n"
            message += f"⚠️ Manual intervention required"
            
            # Send to admin
            success = await self._send_telegram_notification(int(self.admin_chat_id), message)
            
            # Record admin notification in database
            if success:
                await self._record_notification(
                    user_id=int(self.admin_chat_id),
                    activation_id=activation_id,
                    notification_type='admin_alert',
                    message=message
                )
            
            return success
            
        except Exception as e:
            print(f"❌ Error sending admin notification: {e}")
            return False
    
    async def notify_dns_warning(self, user_id: int, activation_id: int) -> bool:
        """
        Warn user about DNS profile issues
        
        Args:
            user_id: Telegram user ID
            activation_id: ID of the activation
            
        Returns:
            True if notification was sent successfully
        """
        try:
            # Check rate limiting
            if not await self._can_send_notification(user_id):
                print(f"⚠️ Notification rate limited for user {user_id}")
                return False
            
            # Build message
            message = "⚠️ DNS Profile Warning\n\n"
            message += "🔒 Your DNS profile is not properly installed or verified.\n\n"
            message += "📋 This may cause your Gold status to be revoked.\n\n"
            message += "✅ Please reinstall your DNS profile:\n"
            message += "1. Download the profile again\n"
            message += "2. Install it on your device\n"
            message += "3. Verify the installation\n\n"
            message += "💡 Contact support if you need help: @meepzizhere"
            
            # Send notification
            success = await self._send_telegram_notification(user_id, message)
            
            # Record notification in database
            if success:
                await self._record_notification(
                    user_id=user_id,
                    activation_id=activation_id,
                    notification_type='dns_warning',
                    message=message
                )
            
            return success
            
        except Exception as e:
            print(f"❌ Error sending DNS warning notification: {e}")
            return False
    
    async def _can_send_notification(self, user_id: int) -> bool:
        """
        Check if notification can be sent (rate limiting)
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if notification can be sent, False if rate limited
        """
        try:
            client = get_supabase_client()
            if not client:
                return True  # Allow if database unavailable
            
            # Count notifications sent in the last 24 hours
            cutoff_time = datetime.now() - self.rate_limit_window
            
            notifications_result = client.table('locket_notifications').select('id').eq('user_id', user_id).gte('sent_at', cutoff_time.isoformat()).execute()
            
            notifications_count = len(notifications_result.data) if notifications_result.data else 0
            
            can_send = notifications_count < self.max_notifications_per_day
            
            if not can_send:
                print(f"⚠️ Rate limit reached: {notifications_count} notifications in last 24h for user {user_id}")
            
            return can_send
            
        except Exception as e:
            print(f"❌ Error checking notification rate limit: {e}")
            return True  # Allow if error checking
    
    async def _send_telegram_notification(self, chat_id: int, message: str) -> bool:
        """
        Send notification via Telegram
        
        Args:
            chat_id: Telegram chat ID
            message: Message to send
            
        Returns:
            True if sent successfully
        """
        try:
            if not self.bot_token:
                print("⚠️ Telegram bot token not configured")
                return False
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Notification sent to user {chat_id}")
                return True
            else:
                print(f"❌ Failed to send notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending Telegram notification: {e}")
            return False
    
    async def _record_notification(self, user_id: int, activation_id: Optional[int], 
                                   notification_type: str, message: str) -> bool:
        """
        Record notification in database
        
        Args:
            user_id: Telegram user ID
            activation_id: ID of the activation (optional)
            notification_type: Type of notification
            message: Message content
            
        Returns:
            True if recorded successfully
        """
        try:
            client = get_supabase_client()
            if not client:
                return False
            
            notification_data = {
                'user_id': user_id,
                'activation_id': activation_id,
                'notification_type': notification_type,
                'message': message,
                'sent_at': datetime.now().isoformat()
            }
            
            client.table('locket_notifications').insert(notification_data).execute()
            
            print(f"✅ Notification recorded: {notification_type} for user {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error recording notification: {e}")
            return False
    
    async def get_user_notifications(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent notifications for a user
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of notifications to return
            
        Returns:
            List of notification records
        """
        try:
            client = get_supabase_client()
            if not client:
                return []
            
            notifications_result = client.table('locket_notifications').select('*').eq('user_id', user_id).order('sent_at', desc=True).limit(limit).execute()
            
            return notifications_result.data if notifications_result.data else []
            
        except Exception as e:
            print(f"❌ Error getting user notifications: {e}")
            return []
    
    async def mark_notification_read(self, notification_id: int) -> bool:
        """
        Mark a notification as read
        
        Args:
            notification_id: ID of the notification
            
        Returns:
            True if marked successfully
        """
        try:
            client = get_supabase_client()
            if not client:
                return False
            
            client.table('locket_notifications').update({
                'read_at': datetime.now().isoformat()
            }).eq('id', notification_id).execute()
            
            print(f"✅ Notification {notification_id} marked as read")
            return True
            
        except Exception as e:
            print(f"❌ Error marking notification as read: {e}")
            return False
