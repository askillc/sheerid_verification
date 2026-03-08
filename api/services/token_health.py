"""
Token Health Service - Monitor and manage token pool health
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_client import get_supabase_client


class TokenHealthService:
    """Service for tracking token health metrics and selecting optimal tokens"""
    
    def __init__(self):
        self.cooldown_period = timedelta(hours=1)
    
    async def track_activation(self, token_id: int, success: bool) -> None:
        """
        Record activation attempt and result for a token
        
        Args:
            token_id: ID of the token used
            success: Whether the activation was successful
        """
        try:
            client = get_supabase_client()
            if not client:
                print("❌ Failed to get Supabase client")
                return
            
            # Get current token data
            result = client.table('locket_tokens').select('*').eq('id', token_id).limit(1).execute()
            
            if not result.data:
                print(f"❌ Token {token_id} not found")
                return
            
            token = result.data[0]
            
            # Update metrics
            total_activations = token.get('total_activations', 0) + 1
            successful_activations = token.get('successful_activations', 0)
            
            if success:
                successful_activations += 1
            
            # Update token record
            update_data = {
                'total_activations': total_activations,
                'successful_activations': successful_activations,
                'last_used': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            client.table('locket_tokens').update(update_data).eq('id', token_id).execute()
            
            print(f"✅ Tracked activation for token {token_id}: success={success}, total={total_activations}")
            
        except Exception as e:
            print(f"❌ Error tracking activation: {e}")
    
    async def calculate_token_metrics(self, token_id: int) -> Optional[Dict[str, Any]]:
        """
        Calculate health metrics for a token
        
        Args:
            token_id: ID of the token
            
        Returns:
            Dictionary with metrics: success_rate, retention_rate_1h, retention_rate_24h, 
            retention_rate_7d, total_activations, last_used
        """
        try:
            client = get_supabase_client()
            if not client:
                return None
            
            # Get token data
            token_result = client.table('locket_tokens').select('*').eq('id', token_id).limit(1).execute()
            
            if not token_result.data:
                return None
            
            token = token_result.data[0]
            
            # Calculate success rate
            total = token.get('total_activations', 0)
            successful = token.get('successful_activations', 0)
            success_rate = (successful / total * 100) if total > 0 else 0.0
            
            # Get activations using this token
            activations_result = client.table('locket_activations').select('id, created_at').eq('token_id', token_id).execute()
            
            activation_ids = [a['id'] for a in activations_result.data] if activations_result.data else []
            
            # Calculate retention rates at different intervals
            retention_1h = await self._calculate_retention_rate(activation_ids, '1h')
            retention_24h = await self._calculate_retention_rate(activation_ids, '24h')
            retention_7d = await self._calculate_retention_rate(activation_ids, '7d')
            
            metrics = {
                'token_id': token_id,
                'success_rate': success_rate,
                'retention_rate_1h': retention_1h,
                'retention_rate_24h': retention_24h,
                'retention_rate_7d': retention_7d,
                'total_activations': total,
                'last_used': token.get('last_used')
            }
            
            return metrics
            
        except Exception as e:
            print(f"❌ Error calculating token metrics: {e}")
            return None
    
    async def _calculate_retention_rate(self, activation_ids: List[int], interval: str) -> float:
        """
        Calculate retention rate for given activations at a specific interval
        
        Args:
            activation_ids: List of activation IDs
            interval: Time interval ('1h', '6h', '24h', '7d', '30d')
            
        Returns:
            Retention rate as percentage (0-100)
        """
        try:
            if not activation_ids:
                return 0.0
            
            client = get_supabase_client()
            if not client:
                return 0.0
            
            # Get retention checks for these activations at this interval
            checks_result = client.table('locket_retention_checks').select('*').in_('activation_id', activation_ids).eq('check_interval', interval).execute()
            
            if not checks_result.data:
                return 0.0
            
            checks = checks_result.data
            total_checks = len(checks)
            successful_checks = sum(1 for c in checks if c.get('gold_active') is True)
            
            retention_rate = (successful_checks / total_checks * 100) if total_checks > 0 else 0.0
            
            return retention_rate
            
        except Exception as e:
            print(f"❌ Error calculating retention rate: {e}")
            return 0.0
    
    async def get_best_token(self, exclude_token_ids: Optional[List[int]] = None) -> Optional[Dict[str, Any]]:
        """
        Select the best token based on health metrics and cooldown
        
        Args:
            exclude_token_ids: List of token IDs to exclude from selection
            
        Returns:
            Token dictionary or None if no suitable token found
        """
        try:
            client = get_supabase_client()
            if not client:
                return None
            
            # Get all healthy tokens (not failed)
            result = client.table('locket_tokens').select('*').neq('status', 'failed').execute()
            
            if not result.data:
                print("❌ No healthy tokens available")
                return None
            
            tokens = result.data
            
            # Filter out excluded tokens
            if exclude_token_ids:
                tokens = [t for t in tokens if t['id'] not in exclude_token_ids]
            
            if not tokens:
                print("❌ No tokens available after exclusions")
                return None
            
            # Filter tokens not in cooldown
            now = datetime.now()
            available_tokens = []
            
            for token in tokens:
                last_used = token.get('last_used')
                if last_used:
                    last_used_dt = datetime.fromisoformat(last_used.replace('Z', '+00:00'))
                    if (now - last_used_dt.replace(tzinfo=None)) > self.cooldown_period:
                        available_tokens.append(token)
                else:
                    # Never used - available
                    available_tokens.append(token)
            
            # If no tokens available (all in cooldown), use the one with oldest last_used
            if not available_tokens:
                print("⚠️ All tokens in cooldown, selecting oldest")
                tokens_with_last_used = [t for t in tokens if t.get('last_used')]
                if tokens_with_last_used:
                    available_tokens = [min(tokens_with_last_used, key=lambda t: t['last_used'])]
                else:
                    available_tokens = tokens[:1]  # Fallback to first token
            
            # Calculate priority score for each available token
            # Score = retention_rate * 0.6 + success_rate * 0.3 - (usage_count / 1000) * 0.1
            scored_tokens = []
            
            for token in available_tokens:
                retention_rate = token.get('retention_rate_24h', 0.0)
                total = token.get('total_activations', 0)
                successful = token.get('successful_activations', 0)
                success_rate = (successful / total * 100) if total > 0 else 100.0  # New tokens get benefit
                
                score = (retention_rate * 0.6) + (success_rate * 0.3) - (total / 1000.0 * 0.1)
                
                scored_tokens.append((token, score))
            
            # Sort by score descending
            scored_tokens.sort(key=lambda x: x[1], reverse=True)
            
            best_token = scored_tokens[0][0]
            best_score = scored_tokens[0][1]
            
            print(f"✅ Selected token {best_token['id']} with score {best_score:.2f}")
            
            return best_token
            
        except Exception as e:
            print(f"❌ Error getting best token: {e}")
            return None
    
    async def mark_token_status(self, token_id: int, status: str, reason: Optional[str] = None) -> bool:
        """
        Mark token status (healthy, degraded, failed)
        
        Args:
            token_id: ID of the token
            status: New status ('healthy', 'degraded', 'failed')
            reason: Optional reason for status change
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = get_supabase_client()
            if not client:
                return False
            
            update_data = {
                'status': status,
                'updated_at': datetime.now().isoformat()
            }
            
            if reason:
                # Append reason to notes
                token_result = client.table('locket_tokens').select('notes').eq('id', token_id).limit(1).execute()
                if token_result.data:
                    existing_notes = token_result.data[0].get('notes', '')
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    new_note = f"[{timestamp}] Status changed to {status}: {reason}"
                    update_data['notes'] = f"{existing_notes}\n{new_note}" if existing_notes else new_note
            
            result = client.table('locket_tokens').update(update_data).eq('id', token_id).execute()
            
            if result.data or result is not None:
                print(f"✅ Marked token {token_id} as {status}")
                return True
            else:
                print(f"❌ Failed to mark token {token_id} as {status}")
                return False
                
        except Exception as e:
            print(f"❌ Error marking token status: {e}")
            return False
    
    async def get_token_health_report(self) -> List[Dict[str, Any]]:
        """
        Get health report for all tokens
        
        Returns:
            List of token health dictionaries
        """
        try:
            client = get_supabase_client()
            if not client:
                return []
            
            # Get all tokens
            result = client.table('locket_tokens').select('*').execute()
            
            if not result.data:
                return []
            
            tokens = result.data
            health_reports = []
            
            for token in tokens:
                metrics = await self.calculate_token_metrics(token['id'])
                if metrics:
                    health_report = {
                        'id': token['id'],
                        'status': token.get('status', 'unknown'),
                        'total_activations': token.get('total_activations', 0),
                        'successful_activations': token.get('successful_activations', 0),
                        'success_rate': metrics['success_rate'],
                        'retention_rate_1h': metrics['retention_rate_1h'],
                        'retention_rate_24h': metrics['retention_rate_24h'],
                        'retention_rate_7d': metrics['retention_rate_7d'],
                        'last_used': token.get('last_used'),
                        'notes': token.get('notes', '')
                    }
                    health_reports.append(health_report)
            
            return health_reports
            
        except Exception as e:
            print(f"❌ Error getting token health report: {e}")
            return []
