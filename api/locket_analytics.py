"""
Locket Gold Analytics API
Provides analytics endpoints for Locket Gold dashboard
"""
from flask import Blueprint, jsonify
import asyncio
from datetime import datetime, timedelta

# Import services
try:
    from api.services.token_health import TokenHealthService
    from api.services.monitoring import MonitoringService
    from api.supabase_client import get_supabase_client
except ImportError:
    from .services.token_health import TokenHealthService
    from .services.monitoring import MonitoringService
    from .supabase_client import get_supabase_client

locket_analytics_bp = Blueprint('locket_analytics', __name__)

# Add CORS headers
@locket_analytics_bp.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@locket_analytics_bp.route('/api/locket/analytics/tokens', methods=['GET'])
def get_token_analytics():
    """Get token health analytics"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        token_service = TokenHealthService()
        health_report = loop.run_until_complete(token_service.get_token_health_report())
        
        loop.close()
        
        # Calculate average success rate
        avg_success_rate = 0
        if health_report:
            total_success = sum(t.get('success_rate', 0) for t in health_report)
            avg_success_rate = total_success / len(health_report) if len(health_report) > 0 else 0
        
        return jsonify({
            'success': True,
            'tokens': health_report,
            'avgSuccessRate': avg_success_rate
        })
        
    except Exception as e:
        print(f"❌ Error in get_token_analytics: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'tokens': [],
            'avgSuccessRate': 0
        }), 500


@locket_analytics_bp.route('/api/locket/analytics/retention', methods=['GET'])
def get_retention_analytics():
    """Get retention rate analytics"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        monitoring_service = MonitoringService()
        retention_metrics = loop.run_until_complete(monitoring_service.calculate_retention_rates())
        
        loop.close()
        
        return jsonify({
            'success': True,
            **retention_metrics
        })
        
    except Exception as e:
        print(f"❌ Error in get_retention_analytics: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            '1h': {'retention_rate': 0, 'total_checks': 0, 'active_count': 0},
            '6h': {'retention_rate': 0, 'total_checks': 0, 'active_count': 0},
            '24h': {'retention_rate': 0, 'total_checks': 0, 'active_count': 0},
            '7d': {'retention_rate': 0, 'total_checks': 0, 'active_count': 0},
            '30d': {'retention_rate': 0, 'total_checks': 0, 'active_count': 0}
        }), 500


@locket_analytics_bp.route('/api/locket/analytics/recovery', methods=['GET'])
def get_recovery_analytics():
    """Get recovery attempt analytics"""
    try:
        client = get_supabase_client()
        if not client:
            raise Exception("Supabase client not available")
        
        # Get recovery attempts from last 7 days
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        # Get all recovery attempts
        attempts_result = client.table('locket_recovery_attempts')\
            .select('*')\
            .gte('attempted_at', seven_days_ago)\
            .order('attempted_at', desc=True)\
            .execute()
        
        attempts = attempts_result.data if attempts_result.data else []
        
        # Calculate stats
        total = len(attempts)
        successful = sum(1 for a in attempts if a.get('success'))
        failed = total - successful
        success_rate = (successful / total * 100) if total > 0 else 0
        
        # Get recent attempts (last 10)
        recent = attempts[:10]
        
        return jsonify({
            'success': True,
            'total': total,
            'successful': successful,
            'failed': failed,
            'success_rate': success_rate,
            'recent': recent
        })
        
    except Exception as e:
        print(f"❌ Error in get_recovery_analytics: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'total': 0,
            'successful': 0,
            'failed': 0,
            'success_rate': 0,
            'recent': []
        }), 500


@locket_analytics_bp.route('/api/locket/analytics/dns-pool', methods=['GET'])
def get_dns_pool_analytics():
    """Get DNS pool statistics"""
    try:
        client = get_supabase_client()
        if not client:
            raise Exception("Supabase client not available")
        
        # Get DNS pool stats from dns_pool table
        # Note: This assumes dns_pool table exists with profile_id and user_count columns
        try:
            pool_result = client.table('dns_pool')\
                .select('profile_id, user_count, active')\
                .execute()
            
            profiles = pool_result.data if pool_result.data else []
            
            total_profiles = len(profiles)
            active_profiles = sum(1 for p in profiles if p.get('active', True))
            total_users = sum(p.get('user_count', 0) for p in profiles)
            avg_users = (total_users / total_profiles) if total_profiles > 0 else 0
            
        except Exception as pool_error:
            print(f"⚠️ DNS pool table not available: {pool_error}")
            # Fallback: count from locket_activations
            activations_result = client.table('locket_activations')\
                .select('dns_provider')\
                .execute()
            
            activations = activations_result.data if activations_result.data else []
            
            # Count unique DNS providers
            providers = set(a.get('dns_provider') for a in activations if a.get('dns_provider'))
            
            total_profiles = len(providers)
            active_profiles = total_profiles
            total_users = len(activations)
            avg_users = (total_users / total_profiles) if total_profiles > 0 else 0
        
        return jsonify({
            'success': True,
            'total_profiles': total_profiles,
            'active_profiles': active_profiles,
            'total_users': total_users,
            'avg_users_per_profile': avg_users
        })
        
    except Exception as e:
        print(f"❌ Error in get_dns_pool_analytics: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'total_profiles': 0,
            'active_profiles': 0,
            'total_users': 0,
            'avg_users_per_profile': 0
        }), 500


@locket_analytics_bp.route('/api/locket/analytics/alerts', methods=['GET'])
def get_alerts():
    """Get active alerts"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        monitoring_service = MonitoringService()
        alerts = loop.run_until_complete(monitoring_service.generate_alerts())
        
        loop.close()
        
        # Format alerts for frontend
        formatted_alerts = []
        for alert in alerts:
            formatted_alerts.append({
                'severity': 'critical' if alert.get('type') == 'low_retention_overall' else 'warning',
                'title': alert.get('message', '').split(':')[0],
                'message': alert.get('message', ''),
                'created_at': alert.get('created_at')
            })
        
        return jsonify({
            'success': True,
            'alerts': formatted_alerts
        })
        
    except Exception as e:
        print(f"❌ Error in get_alerts: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'alerts': []
        }), 500


@locket_analytics_bp.route('/api/locket/analytics/summary', methods=['GET'])
def get_summary():
    """Get overall summary statistics"""
    try:
        client = get_supabase_client()
        if not client:
            raise Exception("Supabase client not available")
        
        # Get total activations
        activations_result = client.table('locket_activations')\
            .select('id', count='exact')\
            .execute()
        total_activations = activations_result.count if activations_result.count else 0
        
        # Get active Gold users (from last 24h checks)
        twenty_four_hours_ago = (datetime.now() - timedelta(hours=24)).isoformat()
        active_checks_result = client.table('locket_retention_checks')\
            .select('activation_id', count='exact')\
            .eq('gold_active', True)\
            .gte('checked_at', twenty_four_hours_ago)\
            .execute()
        active_gold_users = active_checks_result.count if active_checks_result.count else 0
        
        # Get total tokens
        tokens_result = client.table('locket_tokens')\
            .select('id', count='exact')\
            .execute()
        total_tokens = tokens_result.count if tokens_result.count else 0
        
        return jsonify({
            'success': True,
            'total_activations': total_activations,
            'active_gold_users': active_gold_users,
            'total_tokens': total_tokens
        })
        
    except Exception as e:
        print(f"❌ Error in get_summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'total_activations': 0,
            'active_gold_users': 0,
            'total_tokens': 0
        }), 500
