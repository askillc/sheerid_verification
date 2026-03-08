"""
Red Envelope Production API
Integrates all production modules for the red envelope system

Features:
- 30 spawns per day (automated by scheduler)
- Atomic claim processing with race condition protection
- Daily limit enforcement (1 claim per user per day)
- Multi-language support (vi, en, zh)
- Leaderboard with top 5 recent claims
- Authentication and rate limiting
"""

from flask import Blueprint, request, jsonify
from api.claim_handler import claim_handler
from api.leaderboard_manager import get_recent_claims
from api.spawn_scheduler import get_schedule, get_unclaimed_count
from api.auth_middleware import require_auth
from api.rate_limiter import rate_limit
from datetime import datetime, timedelta

red_envelope_prod_bp = Blueprint('red_envelope_production', __name__)


@red_envelope_prod_bp.route('/api/red-envelope/claim', methods=['POST'])
@require_auth
@rate_limit
def claim_envelope():
    """
    Claim a red envelope with full production features:
    - Authentication required
    - Rate limiting (10 attempts/min)
    - Atomic claim processing
    - Daily limit enforcement
    - Multi-language support
    - Leaderboard update
    """
    try:
        data = request.json
        user_id = str(data.get('telegram_id') or data.get('user_id'))
        envelope_id = data.get('envelope_id')
        language = data.get('lang', 'vi')
        
        if not envelope_id:
            return jsonify({
                'success': False,
                'error': 'Missing envelope_id',
                'code': 'INVALID_REQUEST'
            }), 400
        
        # Use claim handler for atomic operation
        result = claim_handler.attempt_claim(user_id, envelope_id, language)
        
        if result.success:
            return jsonify({
                'success': True,
                'amount': result.reward,
                'new_balance': result.new_balance,
                'message': result.message,
                'code': result.code
            })
        else:
            status_code = 400
            if result.code == 'DAILY_LIMIT_REACHED':
                status_code = 429
            elif result.code == 'ALREADY_CLAIMED':
                status_code = 409
            elif result.code == 'ENVELOPE_NOT_FOUND':
                status_code = 404
            
            return jsonify({
                'success': False,
                'error': result.message,
                'code': result.code
            }), status_code
        
    except Exception as e:
        print(f"[ERROR] Claim endpoint failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'SERVER_ERROR'
        }), 500


@red_envelope_prod_bp.route('/api/red-envelope/unclaimed', methods=['GET'])
def get_unclaimed_envelopes():
    """
    Get all unclaimed envelopes
    No authentication required (public view)
    
    SECURITY: Does NOT expose spawn times or patterns to prevent F12 inspection
    """
    try:
        envelopes = claim_handler.get_unclaimed_envelopes()
        
        # Remove sensitive spawn time information
        safe_envelopes = []
        for env in envelopes:
            safe_envelopes.append({
                'id': env['id']
                # reward_amount and spawn_time intentionally hidden
                # Users should not know the amount before claiming
            })
        
        return jsonify({
            'success': True,
            'envelopes': safe_envelopes,
            'count': len(safe_envelopes)
        })
        
    except Exception as e:
        print(f"[ERROR] Get unclaimed envelopes failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve envelopes',
            'code': 'SERVER_ERROR'
        }), 500


@red_envelope_prod_bp.route('/api/red-envelope/leaderboard', methods=['GET'])
def get_leaderboard():
    """
    Get leaderboard with top 5 recent claims
    User IDs are masked for privacy
    """
    try:
        language = request.args.get('lang', 'vi')
        limit = int(request.args.get('limit', 5))
        
        claims = get_recent_claims(limit=min(limit, 10))  # Max 10
        
        return jsonify({
            'success': True,
            'claims': claims,
            'count': len(claims)
        })
        
    except Exception as e:
        print(f"[ERROR] Get leaderboard failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve leaderboard',
            'code': 'SERVER_ERROR'
        }), 500


@red_envelope_prod_bp.route('/api/red-envelope/stats', methods=['GET'])
def get_stats():
    """
    Get red envelope statistics:
    - Unclaimed count
    - Leaderboard
    - System status
    
    SECURITY: Does NOT expose spawn schedule or timing patterns
    """
    try:
        # Get unclaimed count
        unclaimed_count = get_unclaimed_count()
        
        # Get leaderboard
        recent_claims = get_recent_claims(limit=5)
        
        # Get service status (admin only info, not exposed to client)
        from api.dynamic_spawn_service import get_service_status
        service_status = get_service_status()
        
        return jsonify({
            'success': True,
            'stats': {
                'unclaimed_available': unclaimed_count,
                'recent_claims': recent_claims,
                'system_status': 'operational' if service_status['running'] else 'maintenance'
                # Spawn schedule and timing info intentionally hidden
            }
        })
        
    except Exception as e:
        print(f"[ERROR] Get stats failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve stats',
            'code': 'SERVER_ERROR'
        }), 500


@red_envelope_prod_bp.route('/api/red-envelope/check-user-claimed', methods=['GET'])
@require_auth
def check_user_claimed():
    """
    Check if user already claimed today
    Requires authentication
    """
    try:
        user_id = str(request.args.get('telegram_id') or request.args.get('user_id'))
        
        has_claimed = claim_handler.check_user_daily_limit(user_id)
        
        return jsonify({
            'success': True,
            'already_claimed': has_claimed
        })
        
    except Exception as e:
        print(f"[ERROR] Check user claimed failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to check claim status',
            'code': 'SERVER_ERROR'
        }), 500


# Health check endpoint
@red_envelope_prod_bp.route('/api/red-envelope/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })
