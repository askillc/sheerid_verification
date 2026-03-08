"""
DNS Verification Service - Verify DNS profile installation and effectiveness
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_client import get_supabase_client


class DNSVerificationService:
    """Service for verifying DNS profile installation and effectiveness"""
    
    def __init__(self):
        self.verification_token_expiry = timedelta(hours=24)
        self.reverification_interval = timedelta(days=7)
    
    async def verify_dns_blocking(self, user_id: int, revenuecat_blocked: bool, control_accessible: bool) -> Dict[str, Any]:
        """
        Test if DNS blocking is working
        
        Args:
            user_id: ID of the user
            revenuecat_blocked: Whether api.revenuecat.com is blocked (connection fails)
            control_accessible: Whether google.com is accessible (connection succeeds)
            
        Returns:
            VerificationResult dictionary with success status and details
        """
        try:
            print(f"🔍 Verifying DNS blocking for user {user_id}")
            print(f"   - RevenueCat blocked: {revenuecat_blocked}")
            print(f"   - Control accessible: {control_accessible}")
            
            # DNS verification logic: success IF AND ONLY IF
            # api.revenuecat.com is blocked AND google.com is accessible
            success = revenuecat_blocked and control_accessible
            
            if success:
                print(f"✅ DNS verification successful for user {user_id}")
                reason = "DNS profile is working correctly"
            else:
                print(f"❌ DNS verification failed for user {user_id}")
                
                if not revenuecat_blocked and not control_accessible:
                    reason = "No internet connection detected"
                elif not revenuecat_blocked:
                    reason = "DNS profile not blocking RevenueCat (api.revenuecat.com is accessible)"
                elif not control_accessible:
                    reason = "Control domain not accessible (google.com is blocked)"
                else:
                    reason = "Unknown verification error"
            
            result = {
                'success': success,
                'user_id': user_id,
                'revenuecat_blocked': revenuecat_blocked,
                'control_accessible': control_accessible,
                'reason': reason,
                'verified_at': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            print(f"❌ Error verifying DNS blocking: {e}")
            return {
                'success': False,
                'user_id': user_id,
                'revenuecat_blocked': False,
                'control_accessible': False,
                'reason': f'Verification error: {str(e)}',
                'verified_at': datetime.now().isoformat()
            }
    
    async def generate_verification_token(self, user_id: int) -> Optional[str]:
        """
        Generate unique token for verification
        
        Args:
            user_id: ID of the user
            
        Returns:
            Verification token string, or None if error
        """
        try:
            client = get_supabase_client()
            if not client:
                print("❌ Failed to get Supabase client")
                return None
            
            # Generate secure random token
            token = secrets.token_urlsafe(32)
            
            # Store token in database with expiry
            expires_at = datetime.now() + self.verification_token_expiry
            
            token_data = {
                'user_id': user_id,
                'token': token,
                'expires_at': expires_at.isoformat(),
                'used': False,
                'created_at': datetime.now().isoformat()
            }
            
            # Check if table exists, if not we'll create records in a simpler way
            # For now, we'll store in a verification_tokens table
            result = client.table('dns_verification_tokens').insert(token_data).execute()
            
            if result.data:
                print(f"✅ Generated verification token for user {user_id}: {token[:16]}...")
                return token
            else:
                print(f"❌ Failed to store verification token for user {user_id}")
                return None
                
        except Exception as e:
            print(f"❌ Error generating verification token: {e}")
            return None
    
    async def check_verification_status(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Check if verification was completed
        
        Args:
            token: Verification token
            
        Returns:
            Dictionary with token status and user info, or None if not found/expired
        """
        try:
            client = get_supabase_client()
            if not client:
                return None
            
            # Get token from database
            result = client.table('dns_verification_tokens').select('*').eq('token', token).limit(1).execute()
            
            if not result.data:
                print(f"❌ Verification token not found: {token[:16]}...")
                return None
            
            token_data = result.data[0]
            
            # Check if token is expired
            expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00')).replace(tzinfo=None)
            
            if datetime.now() > expires_at:
                print(f"❌ Verification token expired: {token[:16]}...")
                return {
                    'valid': False,
                    'reason': 'expired',
                    'user_id': token_data['user_id']
                }
            
            # Check if token was already used
            if token_data.get('used', False):
                print(f"⚠️ Verification token already used: {token[:16]}...")
                return {
                    'valid': False,
                    'reason': 'already_used',
                    'user_id': token_data['user_id']
                }
            
            print(f"✅ Verification token valid: {token[:16]}...")
            return {
                'valid': True,
                'user_id': token_data['user_id'],
                'created_at': token_data['created_at'],
                'expires_at': token_data['expires_at']
            }
            
        except Exception as e:
            print(f"❌ Error checking verification status: {e}")
            return None
    
    async def mark_token_used(self, token: str) -> bool:
        """
        Mark verification token as used
        
        Args:
            token: Verification token
            
        Returns:
            True if marked successfully, False otherwise
        """
        try:
            client = get_supabase_client()
            if not client:
                return False
            
            result = client.table('dns_verification_tokens').update({
                'used': True,
                'used_at': datetime.now().isoformat()
            }).eq('token', token).execute()
            
            if result.data:
                print(f"✅ Marked verification token as used: {token[:16]}...")
                return True
            else:
                print(f"❌ Failed to mark token as used: {token[:16]}...")
                return False
                
        except Exception as e:
            print(f"❌ Error marking token as used: {e}")
            return False
    
    async def update_activation_verification_status(self, activation_id: int, verified: bool) -> bool:
        """
        Update activation record with DNS verification status
        
        Args:
            activation_id: ID of the activation
            verified: Whether DNS is verified
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            client = get_supabase_client()
            if not client:
                return False
            
            update_data = {
                'dns_verified': verified,
                'dns_verified_at': datetime.now().isoformat() if verified else None
            }
            
            result = client.table('locket_activations').update(update_data).eq('id', activation_id).execute()
            
            if result.data:
                print(f"✅ Updated DNS verification status for activation {activation_id}: {verified}")
                return True
            else:
                print(f"❌ Failed to update DNS verification status for activation {activation_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating activation verification status: {e}")
            return False
    
    async def get_activations_needing_reverification(self) -> list:
        """
        Get activations that need re-verification (>7 days since last verification)
        
        Returns:
            List of activation IDs that need re-verification
        """
        try:
            client = get_supabase_client()
            if not client:
                return []
            
            # Calculate cutoff time (7 days ago)
            cutoff_time = datetime.now() - self.reverification_interval
            
            # Get activations where:
            # 1. dns_verified = true (was verified before)
            # 2. dns_verified_at < cutoff_time (more than 7 days ago)
            result = client.table('locket_activations').select('id, user_id, uid').eq('dns_verified', True).lt('dns_verified_at', cutoff_time.isoformat()).execute()
            
            if not result.data:
                print("ℹ️ No activations need re-verification")
                return []
            
            activations = result.data
            print(f"📋 Found {len(activations)} activations needing re-verification")
            
            return activations
            
        except Exception as e:
            print(f"❌ Error getting activations needing reverification: {e}")
            return []
    
    async def complete_verification(self, token: str, revenuecat_blocked: bool, control_accessible: bool) -> Dict[str, Any]:
        """
        Complete the verification process
        
        Args:
            token: Verification token
            revenuecat_blocked: Whether api.revenuecat.com is blocked
            control_accessible: Whether google.com is accessible
            
        Returns:
            Dictionary with verification result
        """
        try:
            # Check token validity
            token_status = await self.check_verification_status(token)
            
            if not token_status or not token_status.get('valid'):
                reason = token_status.get('reason', 'invalid') if token_status else 'invalid'
                return {
                    'success': False,
                    'reason': f'Invalid or expired token: {reason}'
                }
            
            user_id = token_status['user_id']
            
            # Verify DNS blocking
            verification_result = await self.verify_dns_blocking(user_id, revenuecat_blocked, control_accessible)
            
            # Mark token as used
            await self.mark_token_used(token)
            
            # If verification successful, update all activations for this user
            if verification_result['success']:
                client = get_supabase_client()
                if client:
                    # Get all activations for this user
                    activations_result = client.table('locket_activations').select('id').eq('user_id', user_id).execute()
                    
                    if activations_result.data:
                        for activation in activations_result.data:
                            await self.update_activation_verification_status(activation['id'], True)
                        
                        print(f"✅ Updated {len(activations_result.data)} activations for user {user_id}")
            
            return verification_result
            
        except Exception as e:
            print(f"❌ Error completing verification: {e}")
            return {
                'success': False,
                'reason': f'Verification error: {str(e)}'
            }
