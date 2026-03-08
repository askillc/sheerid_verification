"""
Rate Limiter for Red Envelope Production System

Prevents abuse by limiting claim attempts per user.
Validates Requirements: 11.5
"""

from functools import wraps
from flask import request, jsonify
import redis
import os
from datetime import datetime

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    print(f"[WARNING] Redis connection failed: {e}. Rate limiting disabled.")
    redis_client = None

# Rate limit: 10 attempts per minute per user
RATE_LIMIT_ATTEMPTS = 10
RATE_LIMIT_WINDOW = 60  # seconds


def rate_limit(f):
    """
    Decorator to apply rate limiting to API endpoints.
    
    Limits users to 10 claim attempts per minute.
    
    Usage:
        @app.route('/api/endpoint')
        @rate_limit
        def my_endpoint():
            # ... endpoint logic
    
    Validates:
        - Requirement 11.5: Maximum 10 claim attempts per user per minute
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not redis_client:
            # Rate limiting disabled if Redis unavailable
            return f(*args, **kwargs)
        
        # Get user_id from request
        if request.method == 'POST':
            data = request.json or {}
        else:
            data = request.args or {}
        
        user_id = data.get('user_id')
        
        if not user_id:
            # No user_id, skip rate limiting (auth middleware will handle)
            return f(*args, **kwargs)
        
        # Rate limit key
        rate_key = f"rate_limit:claim:{user_id}"
        
        try:
            # Get current attempt count
            current_attempts = redis_client.get(rate_key)
            
            if current_attempts is None:
                # First attempt in this window
                redis_client.setex(rate_key, RATE_LIMIT_WINDOW, 1)
            else:
                attempts = int(current_attempts)
                
                if attempts >= RATE_LIMIT_ATTEMPTS:
                    # Rate limit exceeded
                    from .multi_language import get_message
                    language = data.get('language', 'en')
                    
                    # Get TTL to tell user when they can try again
                    ttl = redis_client.ttl(rate_key)
                    
                    return jsonify({
                        'success': False,
                        'message': get_message(language, 'rate_limit'),
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'retry_after': ttl
                    }), 429
                
                # Increment attempt count
                redis_client.incr(rate_key)
            
        except Exception as e:
            print(f"[ERROR] Rate limiting check failed: {e}")
            # On error, allow request (fail open)
        
        # Rate limit not exceeded, proceed with request
        return f(*args, **kwargs)
    
    return decorated_function


def get_rate_limit_status(user_id: str) -> dict:
    """
    Get current rate limit status for a user.
    
    Args:
        user_id: User identifier
        
    Returns:
        Dictionary with attempts, limit, and reset time
    """
    if not redis_client:
        return {
            'attempts': 0,
            'limit': RATE_LIMIT_ATTEMPTS,
            'remaining': RATE_LIMIT_ATTEMPTS,
            'reset_in': 0
        }
    
    rate_key = f"rate_limit:claim:{user_id}"
    
    try:
        attempts = redis_client.get(rate_key)
        ttl = redis_client.ttl(rate_key)
        
        if attempts is None:
            attempts = 0
        else:
            attempts = int(attempts)
        
        if ttl < 0:
            ttl = 0
        
        return {
            'attempts': attempts,
            'limit': RATE_LIMIT_ATTEMPTS,
            'remaining': max(0, RATE_LIMIT_ATTEMPTS - attempts),
            'reset_in': ttl
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to get rate limit status: {e}")
        return {
            'attempts': 0,
            'limit': RATE_LIMIT_ATTEMPTS,
            'remaining': RATE_LIMIT_ATTEMPTS,
            'reset_in': 0
        }


def reset_rate_limit(user_id: str):
    """
    Reset rate limit for a user (admin function).
    
    Args:
        user_id: User identifier
    """
    if not redis_client:
        return
    
    rate_key = f"rate_limit:claim:{user_id}"
    
    try:
        redis_client.delete(rate_key)
        print(f"[INFO] Rate limit reset for user {user_id}")
    except Exception as e:
        print(f"[ERROR] Failed to reset rate limit: {e}")
