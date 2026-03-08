"""
API endpoint tracking real-time web visitors
"""
from flask import request, jsonify
from datetime import datetime, timedelta
import uuid
from .supabase_client import get_supabase_client

def track_visitor():
    """Track visitor entering/staying on page"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        
        data = request.json
        session_id = data.get('session_id') or str(uuid.uuid4())
        page_url = data.get('page_url', '')
        page_title = data.get('page_title', '')
        telegram_id = data.get('telegram_id')
        leaving = data.get('leaving', False)  # User is leaving the page
        
        # If user is leaving, mark as inactive immediately
        if leaving:
            try:
                supabase.table('web_visitors')\
                    .update({'is_active': False})\
                    .eq('session_id', session_id)\
                    .execute()
                return jsonify({'success': True, 'message': 'Marked as inactive'})
            except Exception as e:
                print(f"Error marking visitor as inactive: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # Get visitor info
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        referrer = request.headers.get('Referer', '')
        
        # Upsert visitor
        visitor_data = {
            'session_id': session_id,
            'page_url': page_url,
            'page_title': page_title,
            'user_agent': user_agent,
            'ip_address': ip_address,
            'telegram_id': telegram_id,
            'referrer': referrer,
            'last_seen': datetime.utcnow().isoformat(),
            'is_active': True
        }
        
        supabase.table('web_visitors').upsert(
            visitor_data,
            on_conflict='session_id'
        ).execute()
        
        return jsonify({
            'success': True,
            'session_id': session_id
        })
        
    except Exception as e:
        print(f"Error tracking visitor: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_active_visitors():
    """Get count and list of active visitors"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        
        # Mark inactive visitors (older than 60 seconds)
        try:
            inactive_threshold = (datetime.utcnow() - timedelta(seconds=60)).isoformat()
            supabase.table('web_visitors')\
                .update({'is_active': False})\
                .lt('last_seen', inactive_threshold)\
                .eq('is_active', True)\
                .execute()
        except Exception as e:
            print(f"Warning: Could not mark inactive visitors: {e}")
        
        # Get active visitors
        response = supabase.table('web_visitors')\
            .select('*')\
            .eq('is_active', True)\
            .order('last_seen', desc=True)\
            .execute()
        
        visitors = response.data or []
        
        # Group by page
        pages = {}
        for visitor in visitors:
            page = visitor['page_url']
            if page not in pages:
                pages[page] = {
                    'url': page,
                    'title': visitor.get('page_title', ''),
                    'count': 0,
                    'visitors': []
                }
            pages[page]['count'] += 1
            pages[page]['visitors'].append({
                'session_id': visitor['session_id'][:8],
                'telegram_id': visitor.get('telegram_id'),
                'last_seen': visitor['last_seen'],
                'duration': get_duration(visitor.get('entered_at'), visitor['last_seen'])
            })
        
        return jsonify({
            'success': True,
            'total_active': len(visitors),
            'pages': list(pages.values()),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"Error getting active visitors: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_visitor_stats():
    """Get visitor statistics"""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return jsonify({'success': False, 'error': 'Database not available'}), 500
        
        # Mark inactive visitors (older than 60 seconds) before counting
        try:
            inactive_threshold = (datetime.utcnow() - timedelta(seconds=60)).isoformat()
            supabase.table('web_visitors')\
                .update({'is_active': False})\
                .lt('last_seen', inactive_threshold)\
                .eq('is_active', True)\
                .execute()
        except Exception as e:
            print(f"Warning: Could not mark inactive visitors: {e}")
        
        # Active now (updated within last 60 seconds)
        active_response = supabase.table('web_visitors')\
            .select('id', count='exact')\
            .eq('is_active', True)\
            .execute()
        
        active_count = active_response.count or 0
        
        # Last hour
        one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        hour_response = supabase.table('web_visitors')\
            .select('id', count='exact')\
            .gte('last_seen', one_hour_ago)\
            .execute()
        
        hour_count = hour_response.count or 0
        
        # Today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat()
        today_response = supabase.table('web_visitors')\
            .select('id', count='exact')\
            .gte('entered_at', today_start)\
            .execute()
        
        today_count = today_response.count or 0
        
        return jsonify({
            'success': True,
            'stats': {
                'active_now': active_count,
                'last_hour': hour_count,
                'today': today_count
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"Error getting visitor stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_duration(entered_at, last_seen):
    """Calculate duration in seconds"""
    try:
        if not entered_at:
            return 0
        entered = datetime.fromisoformat(entered_at.replace('Z', '+00:00'))
        last = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
        return int((last - entered).total_seconds())
    except:
        return 0
