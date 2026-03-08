"""
Authentication Middleware for Red Envelope Production System

Verifies user authentication before allowing claim attempts.
Validates Requirements: 9.2
"""

from functools import wraps
from flask import request, jsonify
import os
import requests

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')


def require_auth(f):
    """
    Decorator to require authentication for API endpoints.
    
    Checks for user_id in request and verifies user exists in database.
    
    Usage:
        @app.route('/api/endpoint')
        @require_auth
        def my_endpoint():
            user_id = request.json.get('user_id')
            # ... endpoint logic
    
    Validates:
        - Requirement 9.2: Verify user authentication before claim attempts
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get user_id from request
        if request.method == 'POST':
            data = request.json or {}
        else:
            data = request.args or {}
        
        user_id = data.get('user_id')
        
        if not user_id:
            from .multi_language import get_message
            language = data.get('language', 'en')
            return jsonify({
                'success': False,
                'message': get_message(language, 'auth_required'),
                'code': 'AUTH_REQUIRED'
            }), 401
        
        # Verify user exists in database
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/users",
                headers={
                    'apikey': SUPABASE_KEY,
                    'Authorization': f'Bearer {SUPABASE_KEY}'
                },
                params={'telegram_id': f'eq.{user_id}'}
            )
            
            if response.status_code == 200:
                users = response.json()
                if not users or len(users) == 0:
                    from .multi_language import get_message
                    language = data.get('language', 'en')
                    return jsonify({
                        'success': False,
                        'message': get_message(language, 'user_not_found'),
                        'code': 'USER_NOT_FOUND'
                    }), 401
            else:
                return jsonify({
                    'success': False,
                    'message': 'Authentication verification failed',
                    'code': 'AUTH_ERROR'
                }), 500
                
        except Exception as e:
            print(f"[ERROR] Authentication check failed: {e}")
            return jsonify({
                'success': False,
                'message': 'Authentication error',
                'code': 'AUTH_ERROR'
            }), 500
        
        # User authenticated, proceed with request
        return f(*args, **kwargs)
    
    return decorated_function


def validate_telegram_id(telegram_id: str) -> bool:
    """
    Validate that a Telegram ID is in the correct format.
    
    Args:
        telegram_id: Telegram user ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not telegram_id:
        return False
    
    # Telegram IDs are numeric strings
    try:
        int(telegram_id)
        return True
    except ValueError:
        return False
