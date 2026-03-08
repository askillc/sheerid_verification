"""
Monitoring Service - Track Gold retention and schedule checks
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase_client import get_supabase_client


class MonitoringService:
    """Service for monitoring Gold retention and scheduling checks"""
    
    # Check intervals in hours/days
    CHECK_INTERVALS = {
        '1h': timedelta(hours=1),
        '6h': timedelta(hours=6),
        '24h': timedelta(hours=24),
        '7d': timedelta(days=7),
        '30d': timedelta(days=30)
    }
    
    async def schedule_checks(self, activation_id: int) -> bool:
        """
        Schedule retention checks at 1h, 6h, 24h, 7d, 30d intervals
        
        Args:
            activation_id: ID of the activation to monitor
            
        Returns:
            True if checks were scheduled successfully, False otherwise
        """
        try:
            client = get_supabase_client()
            if not client:
                print("❌ Failed to get Supabase client")
                return False
            
            # Get activation to determine when it was created
            activation_result = client.table('locket_activations').select('created_at').eq('id', activation_id).limit(1).execute()
            
            if not activation_result.data:
                print(f"❌ Activation {activation_id} not found")
                return False
            
            activation = activation_result.data[0]
            created_at = datetime.fromisoformat(activation['created_at'].replace('Z', '+00:00')).replace(tzinfo=None)
            
            # Create scheduled checks for each interval
            checks_to_insert = []
            
            for interval_name, interval_delta in self.CHECK_INTERVALS.items():
                scheduled_at = created_at + interval_delta
                
                check_data = {
                    'activation_id': activation_id,
                    'check_interval': interval_name,
                    'scheduled_at': scheduled_at.isoformat(),
                    'checked_at': None,
                    'gold_active': None,
                    'error_message': None,
                    'recovery_attempted': False,
                    'recovery_successful': None
                }
                
                checks_to_insert.append(check_data)
            
            # Insert all checks
            result = client.table('locket_retention_checks').insert(checks_to_insert).execute()
            
            if result.data:
                print(f"✅ Scheduled {len(checks_to_insert)} retention checks for activation {activation_id}")
                return True
            else:
                print(f"❌ Failed to schedule retention checks for activation {activation_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error scheduling checks: {e}")
            return False
    
    async def check_gold_status(self, activation_id: int) -> Optional[Dict[str, Any]]:
        """
        Check if user still has Gold and record result
        
        Args:
            activation_id: ID of the activation to check
            
        Returns:
            RetentionCheck dictionary with results, or None if error
        """
        try:
            client = get_supabase_client()
            if not client:
                return None
            
            # Get activation details
            activation_result = client.table('locket_activations').select('uid, user_id').eq('id', activation_id).limit(1).execute()
            
            if not activation_result.data:
                print(f"❌ Activation {activation_id} not found")
                return None
            
            activation = activation_result.data[0]
            uid = activation['uid']
            
            # Check Gold status via RevenueCat API
            from services.locket import check_status
            
            status_result = await check_status(uid)
            
            if status_result is None:
                # API error
                return {
                    'activation_id': activation_id,
                    'gold_active': None,
                    'error_message': 'RevenueCat API error',
                    'checked_at': datetime.now().isoformat()
                }
            
            gold_active = status_result.get('active', False)
            
            return {
                'activation_id': activation_id,
                'gold_active': gold_active,
                'error_message': None,
                'checked_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error checking Gold status: {e}")
            return {
                'activation_id': activation_id,
                'gold_active': None,
                'error_message': str(e),
                'checked_at': datetime.now().isoformat()
            }
    
    async def process_scheduled_checks(self) -> List[Dict[str, Any]]:
        """
        Process all due retention checks
        
        Returns:
            List of processed retention check results
        """
        try:
            client = get_supabase_client()
            if not client:
                return []
            
            # Get all checks that are due (scheduled_at <= now and not yet checked)
            now = datetime.now()
            
            checks_result = client.table('locket_retention_checks').select('*').lte('scheduled_at', now.isoformat()).is_('checked_at', 'null').execute()
            
            if not checks_result.data:
                print("ℹ️ No scheduled checks due")
                return []
            
            due_checks = checks_result.data
            print(f"📋 Processing {len(due_checks)} due retention checks")
            
            processed_checks = []
            
            for check in due_checks:
                check_id = check['id']
                activation_id = check['activation_id']
                check_interval = check['check_interval']
                
                print(f"🔍 Checking activation {activation_id} at interval {check_interval}")
                
                # Check Gold status
                status_result = await self.check_gold_status(activation_id)
                
                if status_result:
                    # Record check result with timestamp
                    update_data = {
                        'checked_at': status_result['checked_at'],
                        'gold_active': status_result['gold_active'],
                        'error_message': status_result['error_message']
                    }
                    
                    client.table('locket_retention_checks').update(update_data).eq('id', check_id).execute()
                    
                    # If Gold is lost (gold_active=False), trigger recovery
                    if status_result['gold_active'] is False:
                        print(f"⚠️ Gold lost for activation {activation_id} at interval {check_interval}")
                        
                        # Mark that recovery should be attempted
                        # The RecoveryService will be triggered by a separate process
                        # For now, we just flag it
                        client.table('locket_retention_checks').update({
                            'recovery_attempted': False
                        }).eq('id', check_id).execute()
                        
                        # TODO: Trigger RecoveryService.attempt_recovery(activation_id)
                        # This will be implemented when RecoveryService is created
                    
                    processed_checks.append({
                        'check_id': check_id,
                        'activation_id': activation_id,
                        'check_interval': check_interval,
                        'gold_active': status_result['gold_active'],
                        'checked_at': status_result['checked_at'],
                        'gold_lost': status_result['gold_active'] is False
                    })
            
            print(f"✅ Processed {len(processed_checks)} retention checks")
            
            # Count Gold losses
            gold_losses = sum(1 for c in processed_checks if c.get('gold_lost'))
            if gold_losses > 0:
                print(f"⚠️ Detected {gold_losses} Gold losses that need recovery")
            
            return processed_checks
            
        except Exception as e:
            print(f"❌ Error processing scheduled checks: {e}")
            return []
    
    async def detect_gold_losses(self) -> List[Dict[str, Any]]:
        """
        Detect all recent Gold losses that need recovery
        
        Returns:
            List of activations with Gold loss that need recovery
        """
        try:
            client = get_supabase_client()
            if not client:
                return []
            
            # Get all checks where Gold was lost and recovery hasn't been attempted
            checks_result = client.table('locket_retention_checks').select('*').eq('gold_active', False).eq('recovery_attempted', False).execute()
            
            if not checks_result.data:
                return []
            
            gold_losses = []
            
            for check in checks_result.data:
                gold_losses.append({
                    'check_id': check['id'],
                    'activation_id': check['activation_id'],
                    'check_interval': check['check_interval'],
                    'checked_at': check['checked_at']
                })
            
            print(f"🔍 Detected {len(gold_losses)} Gold losses needing recovery")
            return gold_losses
            
        except Exception as e:
            print(f"❌ Error detecting Gold losses: {e}")
            return []
    
    async def calculate_retention_rates(self) -> Dict[str, Any]:
        """
        Calculate retention rates across all intervals
        
        Returns:
            Dictionary with overall retention metrics
        """
        try:
            client = get_supabase_client()
            if not client:
                return {}
            
            retention_metrics = {}
            
            # Calculate retention rate for each interval
            for interval_name in self.CHECK_INTERVALS.keys():
                # Get all checks for this interval that have been completed
                checks_result = client.table('locket_retention_checks').select('gold_active').eq('check_interval', interval_name).not_.is_('checked_at', 'null').execute()
                
                if not checks_result.data:
                    retention_metrics[interval_name] = {
                        'total_checks': 0,
                        'active_count': 0,
                        'retention_rate': 0.0
                    }
                    continue
                
                checks = checks_result.data
                total_checks = len(checks)
                active_count = sum(1 for c in checks if c.get('gold_active') is True)
                retention_rate = (active_count / total_checks * 100) if total_checks > 0 else 0.0
                
                retention_metrics[interval_name] = {
                    'total_checks': total_checks,
                    'active_count': active_count,
                    'retention_rate': retention_rate
                }
            
            print(f"✅ Calculated retention rates: {retention_metrics}")
            return retention_metrics
            
        except Exception as e:
            print(f"❌ Error calculating retention rates: {e}")
            return {}
    
    async def calculate_retention_by_provider(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate retention rates grouped by DNS provider
        
        Returns:
            Dictionary with retention metrics per DNS provider
        """
        try:
            client = get_supabase_client()
            if not client:
                return {}
            
            # Get all activations with their DNS provider info
            activations_result = client.table('locket_activations').select('id, dns_provider').execute()
            
            if not activations_result.data:
                return {}
            
            # Group activations by DNS provider
            provider_activations = {}
            for activation in activations_result.data:
                provider = activation.get('dns_provider', 'unknown')
                if provider not in provider_activations:
                    provider_activations[provider] = []
                provider_activations[provider].append(activation['id'])
            
            # Calculate retention rates for each provider
            provider_metrics = {}
            
            for provider, activation_ids in provider_activations.items():
                provider_metrics[provider] = {}
                
                for interval_name in self.CHECK_INTERVALS.keys():
                    # Get checks for these activations at this interval
                    checks_result = client.table('locket_retention_checks').select('gold_active').in_('activation_id', activation_ids).eq('check_interval', interval_name).not_.is_('checked_at', 'null').execute()
                    
                    if not checks_result.data:
                        provider_metrics[provider][interval_name] = {
                            'total_checks': 0,
                            'active_count': 0,
                            'retention_rate': 0.0
                        }
                        continue
                    
                    checks = checks_result.data
                    total_checks = len(checks)
                    active_count = sum(1 for c in checks if c.get('gold_active') is True)
                    retention_rate = (active_count / total_checks * 100) if total_checks > 0 else 0.0
                    
                    provider_metrics[provider][interval_name] = {
                        'total_checks': total_checks,
                        'active_count': active_count,
                        'retention_rate': retention_rate
                    }
            
            print(f"✅ Calculated retention rates by provider: {len(provider_metrics)} providers")
            return provider_metrics
            
        except Exception as e:
            print(f"❌ Error calculating retention by provider: {e}")
            return {}
    
    async def calculate_retention_by_token(self) -> Dict[int, Dict[str, Any]]:
        """
        Calculate retention rates grouped by token
        
        Returns:
            Dictionary with retention metrics per token ID
        """
        try:
            client = get_supabase_client()
            if not client:
                return {}
            
            # Get all activations with their token info
            activations_result = client.table('locket_activations').select('id, token_id').not_.is_('token_id', 'null').execute()
            
            if not activations_result.data:
                return {}
            
            # Group activations by token
            token_activations = {}
            for activation in activations_result.data:
                token_id = activation.get('token_id')
                if token_id:
                    if token_id not in token_activations:
                        token_activations[token_id] = []
                    token_activations[token_id].append(activation['id'])
            
            # Calculate retention rates for each token
            token_metrics = {}
            
            for token_id, activation_ids in token_activations.items():
                token_metrics[token_id] = {}
                
                for interval_name in self.CHECK_INTERVALS.keys():
                    # Get checks for these activations at this interval
                    checks_result = client.table('locket_retention_checks').select('gold_active').in_('activation_id', activation_ids).eq('check_interval', interval_name).not_.is_('checked_at', 'null').execute()
                    
                    if not checks_result.data:
                        token_metrics[token_id][interval_name] = {
                            'total_checks': 0,
                            'active_count': 0,
                            'retention_rate': 0.0
                        }
                        continue
                    
                    checks = checks_result.data
                    total_checks = len(checks)
                    active_count = sum(1 for c in checks if c.get('gold_active') is True)
                    retention_rate = (active_count / total_checks * 100) if total_checks > 0 else 0.0
                    
                    token_metrics[token_id][interval_name] = {
                        'total_checks': total_checks,
                        'active_count': active_count,
                        'retention_rate': retention_rate
                    }
            
            print(f"✅ Calculated retention rates by token: {len(token_metrics)} tokens")
            return token_metrics
            
        except Exception as e:
            print(f"❌ Error calculating retention by token: {e}")
            return {}
    
    async def calculate_retention_by_package(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate retention rates grouped by package type
        
        Returns:
            Dictionary with retention metrics per package type
        """
        try:
            client = get_supabase_client()
            if not client:
                return {}
            
            # Get all activations with their package info
            activations_result = client.table('locket_activations').select('id, package_type').execute()
            
            if not activations_result.data:
                return {}
            
            # Group activations by package type
            package_activations = {}
            for activation in activations_result.data:
                package_type = activation.get('package_type', 'unknown')
                if package_type not in package_activations:
                    package_activations[package_type] = []
                package_activations[package_type].append(activation['id'])
            
            # Calculate retention rates for each package type
            package_metrics = {}
            
            for package_type, activation_ids in package_activations.items():
                package_metrics[package_type] = {}
                
                for interval_name in self.CHECK_INTERVALS.keys():
                    # Get checks for these activations at this interval
                    checks_result = client.table('locket_retention_checks').select('gold_active').in_('activation_id', activation_ids).eq('check_interval', interval_name).not_.is_('checked_at', 'null').execute()
                    
                    if not checks_result.data:
                        package_metrics[package_type][interval_name] = {
                            'total_checks': 0,
                            'active_count': 0,
                            'retention_rate': 0.0
                        }
                        continue
                    
                    checks = checks_result.data
                    total_checks = len(checks)
                    active_count = sum(1 for c in checks if c.get('gold_active') is True)
                    retention_rate = (active_count / total_checks * 100) if total_checks > 0 else 0.0
                    
                    package_metrics[package_type][interval_name] = {
                        'total_checks': total_checks,
                        'active_count': active_count,
                        'retention_rate': retention_rate
                    }
            
            print(f"✅ Calculated retention rates by package: {len(package_metrics)} package types")
            return package_metrics
            
        except Exception as e:
            print(f"❌ Error calculating retention by package: {e}")
            return {}
    
    async def generate_alerts(self) -> List[Dict[str, Any]]:
        """
        Generate alerts for low retention rates
        
        Returns:
            List of alert dictionaries
        """
        try:
            ALERT_THRESHOLD = 85.0
            alerts = []
            
            # Check overall retention rates
            overall_metrics = await self.calculate_retention_rates()
            
            for interval, metrics in overall_metrics.items():
                retention_rate = metrics['retention_rate']
                
                if retention_rate < ALERT_THRESHOLD and metrics['total_checks'] > 0:
                    alert = {
                        'type': 'low_retention_overall',
                        'severity': 'warning',
                        'interval': interval,
                        'retention_rate': retention_rate,
                        'threshold': ALERT_THRESHOLD,
                        'total_checks': metrics['total_checks'],
                        'active_count': metrics['active_count'],
                        'message': f'Low overall retention rate {retention_rate:.2f}% at interval {interval} (threshold: {ALERT_THRESHOLD}%)',
                        'created_at': datetime.now().isoformat()
                    }
                    alerts.append(alert)
                    print(f"⚠️ Alert: Low overall retention {retention_rate:.2f}% at {interval}")
            
            # Check retention rates by DNS provider
            provider_metrics = await self.calculate_retention_by_provider()
            
            for provider, intervals in provider_metrics.items():
                for interval, metrics in intervals.items():
                    retention_rate = metrics['retention_rate']
                    
                    if retention_rate < ALERT_THRESHOLD and metrics['total_checks'] > 0:
                        alert = {
                            'type': 'low_retention_provider',
                            'severity': 'warning',
                            'provider': provider,
                            'interval': interval,
                            'retention_rate': retention_rate,
                            'threshold': ALERT_THRESHOLD,
                            'total_checks': metrics['total_checks'],
                            'active_count': metrics['active_count'],
                            'message': f'Low retention rate {retention_rate:.2f}% for provider {provider} at interval {interval} (threshold: {ALERT_THRESHOLD}%)',
                            'created_at': datetime.now().isoformat()
                        }
                        alerts.append(alert)
                        print(f"⚠️ Alert: Low retention {retention_rate:.2f}% for provider {provider} at {interval}")
            
            # Check retention rates by token
            token_metrics = await self.calculate_retention_by_token()
            
            for token_id, intervals in token_metrics.items():
                for interval, metrics in intervals.items():
                    retention_rate = metrics['retention_rate']
                    
                    if retention_rate < ALERT_THRESHOLD and metrics['total_checks'] > 0:
                        alert = {
                            'type': 'low_retention_token',
                            'severity': 'warning',
                            'token_id': token_id,
                            'interval': interval,
                            'retention_rate': retention_rate,
                            'threshold': ALERT_THRESHOLD,
                            'total_checks': metrics['total_checks'],
                            'active_count': metrics['active_count'],
                            'message': f'Low retention rate {retention_rate:.2f}% for token {token_id} at interval {interval} (threshold: {ALERT_THRESHOLD}%)',
                            'created_at': datetime.now().isoformat()
                        }
                        alerts.append(alert)
                        print(f"⚠️ Alert: Low retention {retention_rate:.2f}% for token {token_id} at {interval}")
            
            if alerts:
                print(f"🚨 Generated {len(alerts)} alerts for low retention rates")
            else:
                print(f"✅ No alerts - all retention rates above {ALERT_THRESHOLD}%")
            
            return alerts
            
        except Exception as e:
            print(f"❌ Error generating alerts: {e}")
            return []
