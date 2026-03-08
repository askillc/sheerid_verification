"""
Admin API Routes for Dashboard - Full Featured
"""
import os
import jwt
import hashlib
import requests
from datetime import datetime, timedelta
from functools import wraps
from flask import jsonify, request
from .supabase_client import get_supabase_client

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')


def mask_telegram_id(telegram_id):
    """
    Mask telegram ID for privacy protection.
    Shows only last 4 digits.
    
    Examples:
        8447325764 -> "******5764"
        123 -> "***123"
    
    Args:
        telegram_id: Telegram user ID (int or str)
        
    Returns:
        Masked ID string
    """
    if telegram_id is None:
        return "****"
    
    id_str = str(telegram_id)
    
    if len(id_str) <= 4:
        return "*" * 3 + id_str
    else:
        mask_length = len(id_str) - 4
        return "*" * mask_length + id_str[-4:]


def send_telegram_notification(chat_id, message):
    """Send notification to user via Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not set")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram notification error: {e}")
        return False

# Admin credentials - UPDATED
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'quangmanuel')
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', 'b1614847b0c72c32a8abb868de617e949d27488d443fc3e072194f1c9d34e655')
JWT_SECRET = os.environ.get('JWT_SECRET', 'sheerid-admin-secret-key-2024')

def verify_admin_token(f):
    """Decorator to verify admin JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Token missing'}), 401
        try:
            jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
    return decorated

def register_admin_routes(app):
    
    @app.route('/api/admin/login', methods=['POST'])
    def admin_login():
        """Admin login endpoint"""
        data = request.json
        username = data.get('username')
        password = data.get('password')
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if username == ADMIN_USERNAME and password_hash == ADMIN_PASSWORD_HASH:
            token = jwt.encode({
                'username': username,
                'exp': datetime.utcnow() + timedelta(days=7)
            }, JWT_SECRET, algorithm='HS256')
            return jsonify({'token': token})
        return jsonify({'error': 'Sai tên đăng nhập hoặc mật khẩu'}), 401
    
    @app.route('/api/admin/stats', methods=['GET'])
    @verify_admin_token
    def get_stats():
        """Get dashboard statistics"""
        try:
            print("[DEBUG] /api/admin/stats called")
            supabase = get_supabase_client()
            
            if not supabase:
                print("[ERROR] Supabase client is None in get_stats!")
                return jsonify({
                    'totalUsers': 0,
                    'vipUsers': 0,
                    'totalJobs': 0,
                    'totalTransactions': 0,
                    'blockedUsers': 0,
                    'error': 'Database connection failed'
                }), 500
            
            # Get total users
            total_users = 0
            try:
                print("[DEBUG] Querying users count...")
                users_resp = supabase.table('users').select('id').execute()
                total_users = (len(users_resp.data) if users_resp.data else 0) if (len(users_resp.data) if users_resp.data else 0) else len(users_resp.data or [])
                print(f"[DEBUG] Total users: {total_users}")
            except Exception as e:
                print(f"[ERROR] Stats users error: {e}")
            
            # Get VIP users (handle if column doesn't exist)
            vip_users = 0
            try:
                print("[DEBUG] Querying VIP users count...")
                vip_resp = supabase.table('users').select('id').eq('is_vip', True).execute()
                vip_users = (len(vip_resp.data) if vip_resp.data else 0) if (len(vip_resp.data) if vip_resp.data else 0) else len(vip_resp.data or [])
                print(f"[DEBUG] VIP users: {vip_users}")
            except Exception as e:
                print(f"[ERROR] Stats VIP error: {e}")
            
            # Get jobs count from BOTH tables
            total_jobs = 0
            try:
                print("[DEBUG] Querying jobs count from verification_jobs...")
                jobs_resp = supabase.table('verification_jobs').select('id').execute()
                jobs_count_old = (len(jobs_resp.data) if jobs_resp.data else 0) if (len(jobs_resp.data) if jobs_resp.data else 0) else len(jobs_resp.data or [])
                print(f"[DEBUG] verification_jobs count: {jobs_count_old}")
                
                print("[DEBUG] Querying jobs count from sheerid_bot_jobs...")
                jobs_resp_new = supabase.table('sheerid_bot_jobs').select('job_id', count='exact').execute()
                jobs_count_new = jobs_resp_new.count if jobs_resp_new.count else len(jobs_resp_new.data or [])
                print(f"[DEBUG] sheerid_bot_jobs count: {jobs_count_new}")
                
                total_jobs = jobs_count_old + jobs_count_new
                print(f"[DEBUG] Total jobs: {total_jobs}")
            except Exception as e:
                print(f"[ERROR] Stats jobs error: {e}")
            
            # Get transactions count
            total_tx = 0
            try:
                print("[DEBUG] Querying transactions count...")
                tx_resp = supabase.table('transactions').select('id').execute()
                total_tx = (len(tx_resp.data) if tx_resp.data else 0) if (len(tx_resp.data) if tx_resp.data else 0) else len(tx_resp.data or [])
                print(f"[DEBUG] Total transactions: {total_tx}")
            except Exception as e:
                print(f"[ERROR] Stats transactions error: {e}")
            
            # Get blocked users count
            blocked_users = 0
            try:
                print("[DEBUG] Querying blocked users count...")
                blocked_resp = supabase.table('users').select('id').eq('is_blocked', True).execute()
                blocked_users = (len(blocked_resp.data) if blocked_resp.data else 0) if (len(blocked_resp.data) if blocked_resp.data else 0) else len(blocked_resp.data or [])
                print(f"[DEBUG] Blocked users: {blocked_users}")
            except Exception as e:
                print(f"[ERROR] Stats blocked error: {e}")
            
            result = {
                'totalUsers': total_users,
                'vipUsers': vip_users,
                'totalJobs': total_jobs,
                'totalTransactions': total_tx,
                'blockedUsers': blocked_users
            }
            print(f"[DEBUG] Returning stats: {result}")
            return jsonify(result)
        except Exception as e:
            print(f"[ERROR] Stats general error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/stats/revenue', methods=['GET'])
    @verify_admin_token
    def get_revenue_stats():
        """Get verification revenue statistics
        
        Vốn (Cost):
        - Gemini: 5,000 VND
        - Perplexity: 12,500 VND
        - Spotify: 5,000 VND
        
        Giá bán:
        - Gemini: 10 cash = 10,000 VND
        - Perplexity: 25 cash = 25,000 VND
        - Spotify: 10 cash = 10,000 VND
        """
        try:
            import json
            supabase = get_supabase_client()
            
            # Cost per verification type (VND)
            COST = {
                'gemini': 5000,
                'perplexity': 12500,
                'spotify': 5000
            }
            
            # Sell price per verification type (VND)
            SELL_PRICE = {
                'gemini': 10000,      # 10 cash = 10k
                'perplexity': 25000,  # 25 cash = 25k
                'spotify': 10000      # 10 cash = 10k
            }
            
            stats = {
                'perplexity': {'success': 0, 'failed': 0, 'pending': 0, 'jobs': []},
                'gemini': {'success': 0, 'failed': 0, 'pending': 0, 'jobs': []},
                'spotify': {'success': 0, 'failed': 0, 'pending': 0, 'jobs': []}
            }
            
            # 1. Get from sheerid_bot_jobs table (new API - gemini, perplexity)
            try:
                response = supabase.table('sheerid_bot_jobs').select('*').order('created_at', desc=True).execute()
                if response.data:
                    for job in response.data:
                        v_type = (job.get('verification_type') or '').lower()
                        status = (job.get('status') or '').lower()
                        
                        if v_type in stats:
                            if status in ['success', 'completed']:
                                stats[v_type]['success'] += 1
                                stats[v_type]['jobs'].append({
                                    'job_id': job.get('job_id', '')[:16],
                                    'telegram_id': mask_telegram_id(job.get('telegram_id')),  # Masked for privacy
                                    'created_at': job.get('created_at'),
                                    'status': 'success'
                                })
                            elif status in ['failed', 'failure', 'fraud_reject']:
                                stats[v_type]['failed'] += 1
                            else:
                                stats[v_type]['pending'] += 1
            except Exception as e:
                print(f"Error loading sheerid_bot_jobs: {e}")
            
            # 2. Get from verification_jobs table (legacy - spotify)
            try:
                response = supabase.table('verification_jobs').select('*').order('created_at', desc=True).execute()
                if response.data:
                    for job in response.data:
                        v_type = (job.get('verification_type') or '').lower()
                        status = (job.get('status') or '').lower()
                        
                        # Check for spotify type
                        if 'spotify' in v_type or v_type == 'vs':
                            if status in ['success', 'completed']:
                                stats['spotify']['success'] += 1
                                stats['spotify']['jobs'].append({
                                    'job_id': job.get('job_id', '')[:16],
                                    'telegram_id': mask_telegram_id(job.get('telegram_id')),  # Masked for privacy
                                    'created_at': job.get('created_at'),
                                    'status': 'success'
                                })
                            elif status in ['failed', 'failure']:
                                stats['spotify']['failed'] += 1
                            else:
                                stats['spotify']['pending'] += 1
            except Exception as e:
                print(f"Error loading verification_jobs: {e}")
            
            # 3. Calculate revenue for each type
            result = {
                'types': {},
                'total': {
                    'success': 0,
                    'revenue': 0,
                    'cost': 0,
                    'profit': 0
                }
            }
            
            for v_type, data in stats.items():
                success = data['success']
                failed = data['failed']
                pending = data['pending']
                total = success + failed + pending
                
                # Calculate money - use type-specific sell price
                sell_price = SELL_PRICE[v_type]
                revenue = success * sell_price
                cost = success * COST[v_type]
                profit = revenue - cost
                
                # Success rate
                success_rate = round((success / total) * 100, 1) if total > 0 else 0
                
                result['types'][v_type] = {
                    'success': success,
                    'failed': failed,
                    'pending': pending,
                    'total': total,
                    'success_rate': success_rate,
                    'revenue': revenue,
                    'cost': cost,
                    'profit': profit,
                    'cost_per_unit': COST[v_type],
                    'sell_price': sell_price,
                    'recent_jobs': data['jobs'][:10]  # Last 10 successful jobs
                }
                
                # Add to totals
                result['total']['success'] += success
                result['total']['revenue'] += revenue
                result['total']['cost'] += cost
                result['total']['profit'] += profit
            
            # Calculate profit margin
            if result['total']['revenue'] > 0:
                result['total']['profit_margin'] = round((result['total']['profit'] / result['total']['revenue']) * 100, 1)
            else:
                result['total']['profit_margin'] = 0
            
            return jsonify(result)
            
        except Exception as e:
            print(f"Revenue stats error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/stats/today', methods=['GET'])
    @verify_admin_token
    def get_today_stats():
        """Get today's statistics for dashboard - using Vietnam timezone (UTC+7) and last 24 hours"""
        try:
            supabase = get_supabase_client()
            from datetime import timezone, timedelta
            
            # Vietnam timezone (UTC+7)
            vietnam_tz = timezone(timedelta(hours=7))
            now_vietnam = datetime.now(vietnam_tz)
            
            # Get start of today in Vietnam timezone (00:00:00 Vietnam time)
            today_start_vietnam = now_vietnam.replace(hour=0, minute=0, second=0, microsecond=0)
            # Convert to UTC for database query
            today_start_utc = today_start_vietnam.astimezone(timezone.utc)
            today_iso = today_start_utc.isoformat()
            
            # Get last 24 hours for success rate calculation
            twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
            twenty_four_hours_iso = twenty_four_hours_ago.isoformat()
            
            # Last 24 hours verification jobs (for success rate)
            today_verify = 0
            today_completed = 0
            today_failed = 0
            try:
                # Count jobs in last 24 hours from BOTH tables
                # New table: sheerid_bot_jobs (Gemini, Perplexity, Teacher)
                verify_resp_new = supabase.table('sheerid_bot_jobs').select('job_id', count='exact').gte('created_at', twenty_four_hours_iso).execute()
                today_verify_new = verify_resp_new.count if verify_resp_new.count else len(verify_resp_new.data or [])
                
                completed_resp_new = supabase.table('sheerid_bot_jobs').select('job_id', count='exact').gte('created_at', twenty_four_hours_iso).eq('status', 'success').execute()
                today_completed_new = completed_resp_new.count if completed_resp_new.count else len(completed_resp_new.data or [])
                
                failed_resp_new = supabase.table('sheerid_bot_jobs').select('job_id', count='exact').gte('created_at', twenty_four_hours_iso).eq('status', 'failed').execute()
                today_failed_new = failed_resp_new.count if failed_resp_new.count else len(failed_resp_new.data or [])
                
                # Old table: verification_jobs (Spotify)
                verify_resp_old = supabase.table('verification_jobs').select('id').gte('created_at', twenty_four_hours_iso).execute()
                today_verify_old = verify_resp_old.count if verify_resp_old.count else len(verify_resp_old.data or [])
                
                completed_resp_old = supabase.table('verification_jobs').select('id').gte('created_at', twenty_four_hours_iso).eq('status', 'completed').execute()
                today_completed_old = completed_resp_old.count if completed_resp_old.count else len(completed_resp_old.data or [])
                
                failed_resp_old = supabase.table('verification_jobs').select('id').gte('created_at', twenty_four_hours_iso).eq('status', 'failed').execute()
                today_failed_old = failed_resp_old.count if failed_resp_old.count else len(failed_resp_old.data or [])
                
                # Combine counts from both tables
                today_verify = today_verify_new + today_verify_old
                today_completed = today_completed_new + today_completed_old
                today_failed = today_failed_new + today_failed_old
            except Exception as e:
                print(f"Last 24h verify stats error: {e}")
            
            # Today's new users
            today_new_users = 0
            try:
                users_resp = supabase.table('users').select('id').gte('created_at', today_iso).execute()
                today_new_users = (len(users_resp.data) if users_resp.data else 0) if (len(users_resp.data) if users_resp.data else 0) else len(users_resp.data or [])
            except Exception as e:
                print(f"Today new users error: {e}")
            
            # Today's transactions
            today_transactions = 0
            try:
                tx_resp = supabase.table('transactions').select('id').gte('created_at', today_iso).execute()
                today_transactions = (len(tx_resp.data) if tx_resp.data else 0) if (len(tx_resp.data) if tx_resp.data else 0) else len(tx_resp.data or [])
            except Exception as e:
                print(f"Today transactions error: {e}")
            
            # Today's revenue from SePay deposits (in VND)
            today_revenue = 0
            try:
                # Get all deposit transactions today (type contains 'deposit' or 'sepay' or 'bank')
                deposit_resp = supabase.table('transactions').select('amount, coins, type').gte('created_at', today_iso).or_('type.ilike.%deposit%,type.ilike.%sepay%,type.ilike.%bank%,type.ilike.%nap%').execute()
                if deposit_resp.data:
                    for tx in deposit_resp.data:
                        amount = tx.get('amount', 0) or 0
                        coins = tx.get('coins', 0) or 0
                        
                        # Skip negative amounts (deductions)
                        if amount < 0 or coins < 0:
                            continue
                        
                        # If amount is small (likely stored as coins), convert to VND
                        # Coins are stored as xu, 1 xu = 1000 VND
                        if amount > 0 and amount < 10000:
                            # Amount is likely in coins/xu, convert to VND
                            today_revenue += amount * 1000
                        elif amount >= 10000:
                            # Amount is already in VND
                            today_revenue += amount
                        elif coins > 0:
                            # Use coins field and convert to VND
                            today_revenue += coins * 1000
            except Exception as e:
                print(f"Today revenue error: {e}")
            
            return jsonify({
                'todayVerify': today_verify,
                'todayCompleted': today_completed,
                'todayFailed': today_failed,
                'todayNewUsers': today_new_users,
                'todayTransactions': today_transactions,
                'todayRevenue': today_revenue
            })
        except Exception as e:
            print(f"Today stats error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/stats/gemini-daily', methods=['GET'])
    def get_gemini_daily_stats():
        """Get Gemini verification statistics for today (Vietnam timezone)
        
        Returns:
        - Total verifications today
        - Total successful verifications
        - Total failed + cancelled verifications
        """
        try:
            supabase = get_supabase_client()
            from datetime import timezone, timedelta
            
            # Vietnam timezone (UTC+7)
            vietnam_tz = timezone(timedelta(hours=7))
            now_vietnam = datetime.now(vietnam_tz)
            
            # Get start of today in Vietnam timezone (00:00:00 Vietnam time)
            today_start_vietnam = now_vietnam.replace(hour=0, minute=0, second=0, microsecond=0)
            # Convert to UTC for database query
            today_start_utc = today_start_vietnam.astimezone(timezone.utc)
            today_iso = today_start_utc.isoformat()
            
            print(f"[GEMINI_DAILY] Querying from: {today_iso} (Vietnam: {today_start_vietnam})")
            
            # Query sheerid_bot_jobs table for Gemini verifications today
            total_verifications = 0
            total_success = 0
            total_failed_cancelled = 0
            
            try:
                # Get all Gemini jobs today
                response = supabase.table('sheerid_bot_jobs').select('status').eq('verification_type', 'gemini').gte('created_at', today_iso).execute()
                
                if response.data:
                    total_verifications = len(response.data)
                    
                    for job in response.data:
                        status = (job.get('status') or '').lower()
                        
                        if status in ['success', 'completed']:
                            total_success += 1
                        elif status in ['failed', 'failure', 'cancelled', 'fraud_reject', 'rejected', 'reject']:
                            total_failed_cancelled += 1
                
                print(f"[GEMINI_DAILY] Total: {total_verifications}, Success: {total_success}, Failed/Cancelled: {total_failed_cancelled}")
                
            except Exception as e:
                print(f"[GEMINI_DAILY] Error querying: {e}")
            
            return jsonify({
                'success': True,
                'date': today_start_vietnam.strftime('%Y-%m-%d'),
                'timezone': 'Asia/Ho_Chi_Minh (UTC+7)',
                'total_verifications': total_verifications,
                'total_success': total_success,
                'total_failed_cancelled': total_failed_cancelled,
                'success_rate': round((total_success / total_verifications * 100), 1) if total_verifications > 0 else 0
            })
            
        except Exception as e:
            print(f"[GEMINI_DAILY] General error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/admin/users', methods=['GET'])
    @verify_admin_token
    def get_users():
        """Get users with pagination, search and filter"""
        try:
            supabase = get_supabase_client()
            
            # Get pagination params
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 20))
            search = request.args.get('search', '').strip()
            user_filter = request.args.get('filter', 'all').strip()
            offset = (page - 1) * limit
            
            # Build query
            query = supabase.table('users').select('*')
            
            # Apply search filter if provided
            if search:
                # Search by telegram_id, username, or first_name
                if search.isdigit():
                    query = query.eq('telegram_id', int(search))
                else:
                    query = query.or_(f'username.ilike.%{search}%,first_name.ilike.%{search}%')
            
            # Apply user filter
            if user_filter == 'vip':
                query = query.eq('is_vip', True)
            elif user_filter == 'blocked':
                query = query.eq('is_blocked', True)
            elif user_filter == 'active':
                query = query.eq('is_blocked', False)
            elif user_filter == 'has_coins':
                query = query.gt('coins', 0)
            elif user_filter == 'has_cash':
                query = query.gt('cash', 0)
            
            # Apply pagination and ordering
            try:
                response = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
            except Exception:
                response = query.range(offset, offset + limit - 1).execute()
            
            total = (len(response.data) if response.data else 0) if (len(response.data) if response.data else 0) else len(response.data or [])
            total_pages = (total + limit - 1) // limit
            
            return jsonify({
                'users': response.data,
                'total': total,
                'page': page,
                'limit': limit,
                'totalPages': total_pages,
                'filter': user_filter
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/users/<int:telegram_id>', methods=['GET'])
    @verify_admin_token
    def get_user_detail(telegram_id):
        """Get detailed user info including referrals and transactions"""
        try:
            supabase = get_supabase_client()
            
            # Get user info
            user_resp = supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
            if not user_resp.data:
                return jsonify({'error': 'User not found'}), 404
            user = user_resp.data[0]
            
            # Get user's referrals (handle if table doesn't exist)
            referrals = []
            try:
                refs_resp = supabase.table('referrals').select('*').eq('referrer_id', telegram_id).execute()
                referrals = refs_resp.data if refs_resp.data else []
            except Exception as e:
                print(f"Referrals query error: {e}")
            
            # Get user's transactions - use internal user_id from user record
            transactions = []
            user_internal_id = user.get('id')  # Get internal database ID
            try:
                # Query with internal user_id (how transactions are stored)
                if user_internal_id:
                    tx_resp = supabase.table('transactions').select('*').eq('user_id', user_internal_id).order('created_at', desc=True).limit(50).execute()
                    transactions = tx_resp.data if tx_resp.data else []
                
                # If no results, also try with telegram_id as fallback
                if not transactions:
                    tx_resp = supabase.table('transactions').select('*').eq('user_id', telegram_id).order('created_at', desc=True).limit(50).execute()
                    transactions = tx_resp.data if tx_resp.data else []
            except Exception as e:
                print(f"Transactions query error: {e}")
                try:
                    # Fallback to telegram_id column
                    tx_resp = supabase.table('transactions').select('*').eq('telegram_id', telegram_id).order('created_at', desc=True).limit(50).execute()
                    transactions = tx_resp.data if tx_resp.data else []
                except Exception as e2:
                    print(f"Transactions telegram_id error: {e2}")
            
            # Get user's verification jobs
            jobs = []
            try:
                jobs_resp = supabase.table('verification_jobs').select('*').eq('telegram_id', telegram_id).order('created_at', desc=True).limit(50).execute()
                jobs = jobs_resp.data if jobs_resp.data else []
            except Exception as e:
                print(f"Jobs query error: {e}")
                try:
                    jobs_resp = supabase.table('verification_jobs').select('*').eq('telegram_id', telegram_id).limit(50).execute()
                    jobs = jobs_resp.data if jobs_resp.data else []
                except Exception as e2:
                    print(f"Jobs fallback error: {e2}")
            
            return jsonify({
                'user': user,
                'referrals': referrals,
                'referralCount': len(referrals),
                'transactions': transactions,
                'jobs': jobs,
                'totalVerifications': len(jobs),
                'successfulVerifications': len([j for j in jobs if j.get('status') == 'completed'])
            })
        except Exception as e:
            print(f"User detail error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/users/<int:telegram_id>', methods=['PATCH'])
    @verify_admin_token
    def update_user(telegram_id):
        """Update user data - full featured"""
        try:
            data = request.json
            supabase = get_supabase_client()
            
            update_data = {}
            
            # Basic fields
            if 'coins' in data:
                update_data['coins'] = int(data['coins'])
            if 'cash' in data:
                update_data['cash'] = int(data['cash'])
            if 'is_vip' in data:
                update_data['is_vip'] = bool(data['is_vip'])
            if 'vip_expiry' in data:
                update_data['vip_expiry'] = data['vip_expiry']
            
            # Block/unblock user
            if 'is_blocked' in data:
                update_data['is_blocked'] = bool(data['is_blocked'])
            
            # Verify limit
            if 'verify_limit' in data:
                update_data['verify_limit'] = int(data['verify_limit']) if data['verify_limit'] else None
            
            # Language
            if 'language' in data:
                update_data['language'] = data['language']
            
            if update_data:
                update_data['updated_at'] = datetime.utcnow().isoformat()
                response = supabase.table('users').update(update_data).eq('telegram_id', telegram_id).execute()
                return jsonify({'success': True, 'data': response.data})
            
            return jsonify({'success': True, 'message': 'No changes'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/users/<int:telegram_id>/add-balance', methods=['POST'])
    @verify_admin_token
    def add_user_balance(telegram_id):
        """Add coins or cash to user"""
        try:
            data = request.json
            supabase = get_supabase_client()
            
            # Get current user
            user_resp = supabase.table('users').select('coins, cash').eq('telegram_id', telegram_id).execute()
            if not user_resp.data:
                return jsonify({'error': 'User not found'}), 404
            
            user = user_resp.data[0]
            # Handle None values
            current_coins = user.get('coins') or 0
            current_cash = user.get('cash') or 0
            coins_to_add = int(data.get('coins', 0) or 0)
            cash_to_add = int(data.get('cash', 0) or 0)
            reason = data.get('reason', 'Admin adjustment')
            
            new_coins = current_coins + coins_to_add
            new_cash = current_cash + cash_to_add
            
            # Update user balance
            supabase.table('users').update({
                'coins': new_coins,
                'cash': new_cash,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('telegram_id', telegram_id).execute()
            
            # Create transaction record - skip if insert fails
            try:
                if coins_to_add != 0:
                    supabase.table('transactions').insert({
                        'user_id': telegram_id,
                        'type': 'admin_add' if coins_to_add > 0 else 'admin_deduct',
                        'amount': abs(coins_to_add),
                        'coins': coins_to_add,
                        'description': f'Admin: {reason} (coins)',
                        'created_at': datetime.utcnow().isoformat()
                    }).execute()
                
                if cash_to_add != 0:
                    supabase.table('transactions').insert({
                        'user_id': telegram_id,
                        'type': 'admin_add' if cash_to_add > 0 else 'admin_deduct',
                        'amount': abs(cash_to_add),
                        'coins': 0,
                        'description': f'Admin: {reason} (cash)',
                        'created_at': datetime.utcnow().isoformat()
                    }).execute()
            except Exception as tx_err:
                print(f"Transaction log error (non-critical): {tx_err}")
            
            # Send Telegram notification to user
            try:
                notification_parts = []
                if coins_to_add > 0:
                    notification_parts.append(f"➕ <b>+{coins_to_add} Coins</b>")
                elif coins_to_add < 0:
                    notification_parts.append(f"➖ <b>{coins_to_add} Coins</b>")
                
                if cash_to_add > 0:
                    notification_parts.append(f"➕ <b>+{cash_to_add} Cash</b>")
                elif cash_to_add < 0:
                    notification_parts.append(f"➖ <b>{cash_to_add} Cash</b>")
                
                if notification_parts:
                    message = f"🔔 <b>Admin Notification</b>\n\n"
                    message += "\n".join(notification_parts)
                    message += f"\n\n📝 Reason: {reason}"
                    message += f"\n\n💰 Current Balance:\n• Coins: <b>{new_coins}</b>\n• Cash: <b>{new_cash}</b>"
                    send_telegram_notification(telegram_id, message)
            except Exception as notif_err:
                print(f"Notification error (non-critical): {notif_err}")
            
            return jsonify({
                'success': True,
                'newCoins': new_coins,
                'newCash': new_cash
            })
        except Exception as e:
            print(f"Add balance error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/users/<int:telegram_id>/block', methods=['POST'])
    @verify_admin_token
    def block_user(telegram_id):
        """Block or unblock user"""
        try:
            data = request.json
            blocked = data.get('blocked', True)
            reason = data.get('reason', '')
            
            supabase = get_supabase_client()
            
            # Only update fields that exist - block_reason may not exist
            update_data = {
                'is_blocked': blocked,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            try:
                update_data['block_reason'] = reason if blocked else None
                supabase.table('users').update(update_data).eq('telegram_id', telegram_id).execute()
            except Exception:
                # If block_reason column doesn't exist, try without it
                del update_data['block_reason']
                supabase.table('users').update(update_data).eq('telegram_id', telegram_id).execute()
            
            # Send Telegram notification
            try:
                if blocked:
                    message = f"🚫 <b>Account Blocked</b>\n\nYour account has been blocked by Admin."
                    if reason:
                        message += f"\n\n📝 Reason: {reason}"
                    message += "\n\nContact @meepzizhere if you believe this is a mistake."
                else:
                    message = f"✅ <b>Account Unblocked</b>\n\nYour account has been unblocked. You can use the bot normally."
                send_telegram_notification(telegram_id, message)
            except Exception as notif_err:
                print(f"Block notification error: {notif_err}")
            
            return jsonify({'success': True, 'blocked': blocked})
        except Exception as e:
            print(f"Block user error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/users/<int:telegram_id>/set-vip', methods=['POST'])
    @verify_admin_token
    def set_user_vip(telegram_id):
        """Set VIP status for user with tier support"""
        try:
            data = request.json
            is_vip = data.get('is_vip', False)
            days = int(data.get('days', 30) or 30)
            vip_type = data.get('vip_type', 'basic')  # basic, pro, business
            concurrent_links = int(data.get('concurrent_links', 1) or 1)
            
            # Validate vip_type
            if vip_type not in ['basic', 'pro', 'business']:
                vip_type = 'basic'
                concurrent_links = 1
            
            supabase = get_supabase_client()
            
            update_data = {
                'is_vip': is_vip,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Add VIP tier fields
            if is_vip:
                update_data['vip_type'] = vip_type
                update_data['concurrent_links'] = concurrent_links
            else:
                update_data['vip_type'] = None
                update_data['concurrent_links'] = 1
            
            # Try with vip_expiry, fallback without if column doesn't exist
            try:
                if is_vip:
                    expiry = datetime.utcnow() + timedelta(days=days)
                    update_data['vip_expiry'] = expiry.isoformat()
                else:
                    update_data['vip_expiry'] = None
                supabase.table('users').update(update_data).eq('telegram_id', telegram_id).execute()
            except Exception as e:
                print(f"VIP update with all fields failed: {e}")
                # vip_expiry or vip_type columns may not exist - try without them
                fallback_data = {
                    'is_vip': is_vip,
                    'updated_at': datetime.utcnow().isoformat()
                }
                supabase.table('users').update(fallback_data).eq('telegram_id', telegram_id).execute()
            
            # Send Telegram notification
            try:
                if is_vip:
                    tier_name = {'basic': 'Basic (1 link)', 'pro': 'Pro (3 link)', 'business': 'Business (5 link)'}.get(vip_type, 'Basic')
                    message = f"🎉 <b>Congratulations!</b>\n\nYou have been granted <b>VIP {tier_name}</b> for <b>{days} days</b> by Admin!\n\n⭐ Enjoy your VIP privileges!"
                else:
                    message = f"ℹ️ <b>Notice</b>\n\nYour VIP status has been revoked by Admin."
                send_telegram_notification(telegram_id, message)
            except Exception as notif_err:
                print(f"VIP notification error: {notif_err}")
            
            return jsonify({'success': True, 'is_vip': is_vip, 'vip_type': vip_type, 'concurrent_links': concurrent_links})
        except Exception as e:
            print(f"Set VIP error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/cleanup-expired-vips', methods=['POST'])
    @verify_admin_token
    def cleanup_expired_vips():
        """Remove VIP status from all users with expired VIP"""
        try:
            supabase = get_supabase_client()
            now = datetime.utcnow().isoformat()
            
            # Find all expired VIP users
            expired_resp = supabase.table('users').select('telegram_id, username, vip_expiry').eq('is_vip', True).lt('vip_expiry', now).execute()
            expired_users = expired_resp.data or []
            
            count = 0
            for user in expired_users:
                try:
                    # Update user to remove VIP
                    supabase.table('users').update({
                        'is_vip': False,
                        'vip_expiry': None,
                        'updated_at': now
                    }).eq('telegram_id', user['telegram_id']).execute()
                    
                    # Send notification to user
                    try:
                        message = "⏰ <b>VIP Hết Hạn</b>\n\nVIP của bạn đã hết hạn. Cảm ơn bạn đã sử dụng dịch vụ VIP!\n\n💎 Nạp thêm để gia hạn VIP."
                        send_telegram_notification(user['telegram_id'], message)
                    except Exception:
                        pass
                    
                    count += 1
                    print(f"Removed expired VIP from user {user['telegram_id']} (@{user.get('username', 'N/A')})")
                except Exception as e:
                    print(f"Error removing VIP from {user['telegram_id']}: {e}")
            
            return jsonify({'success': True, 'count': count, 'message': f'Removed VIP from {count} expired users'})
        except Exception as e:
            print(f"Cleanup expired VIPs error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/users/<int:telegram_id>/set-verify-limit', methods=['POST'])
    @verify_admin_token
    def set_verify_limit(telegram_id):
        """Set verification limit for user"""
        try:
            data = request.json
            limit = data.get('limit')  # None = unlimited
            
            supabase = get_supabase_client()
            supabase.table('users').update({
                'verify_limit': int(limit) if limit else None,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('telegram_id', telegram_id).execute()
            
            return jsonify({'success': True, 'limit': limit})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/users/<int:telegram_id>/send-message', methods=['POST'])
    @verify_admin_token
    def send_user_message(telegram_id):
        """Send direct message to user via Telegram - DISABLED DUE TO SECURITY INCIDENT"""
        # 🚨 EMERGENCY: Disabled due to hack - hacker using this to spam users
        # Date: 2026-03-02
        # Re-enable after security audit
        return jsonify({
            'error': 'This endpoint has been temporarily disabled for security reasons',
            'code': 'ENDPOINT_DISABLED'
        }), 403
    
    @app.route('/api/admin/users/<int:telegram_id>/set-daily-limit', methods=['POST'])
    @verify_admin_token
    def set_daily_verify_limit(telegram_id):
        """Set daily verification limit for user - uses verify_limit column"""
        try:
            data = request.json
            daily_limit = int(data.get('daily_limit', 0) or 0)
            
            supabase = get_supabase_client()
            
            # Update user with daily limit (0 = unlimited)
            # Use verify_limit column which already exists
            update_data = {
                'verify_limit': daily_limit if daily_limit > 0 else None,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            try:
                supabase.table('users').update(update_data).eq('telegram_id', telegram_id).execute()
            except Exception as col_err:
                print(f"Column error, trying alternative: {col_err}")
                # Fallback - just update timestamp
                supabase.table('users').update({
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('telegram_id', telegram_id).execute()
            
            # Notify user
            try:
                if daily_limit > 0:
                    message = f"⚠️ <b>Thông báo</b>\n\nAdmin đã giới hạn số lượt verify của bạn: <b>{daily_limit} lượt/ngày</b>"
                else:
                    message = f"✅ <b>Thông báo</b>\n\nAdmin đã gỡ giới hạn verify của bạn. Bạn có thể verify không giới hạn."
                send_telegram_notification(telegram_id, message)
            except Exception:
                pass
            
            return jsonify({'success': True, 'daily_limit': daily_limit})
        except Exception as e:
            print(f"Set daily limit error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/users/<int:telegram_id>/set-cash-verify-limit', methods=['POST'])
    @verify_admin_token
    def set_cash_verify_limit(telegram_id):
        """Set daily cash verification limit for user"""
        try:
            data = request.json
            cash_verify_limit = int(data.get('cash_verify_limit', 0) or 0)
            
            supabase = get_supabase_client()
            
            # Update user with cash_verify_limit (0 = unlimited)
            update_data = {
                'cash_verify_limit': cash_verify_limit if cash_verify_limit > 0 else None,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            try:
                supabase.table('users').update(update_data).eq('telegram_id', telegram_id).execute()
            except Exception as col_err:
                print(f"Column cash_verify_limit may not exist: {col_err}")
                return jsonify({'error': 'Column cash_verify_limit not found. Please add it to users table.'}), 500
            
            # Notify user
            try:
                if cash_verify_limit > 0:
                    message = f"⚠️ <b>Thông báo</b>\n\nAdmin đã giới hạn verify bằng CASH của bạn: <b>{cash_verify_limit} lượt/ngày</b>\n\n💡 Liên hệ @meepzizhere nếu cần hỗ trợ."
                else:
                    message = f"✅ <b>Thông báo</b>\n\nAdmin đã gỡ giới hạn verify bằng CASH của bạn.\n\n💰 Bạn có thể verify bằng CASH không giới hạn."
                send_telegram_notification(telegram_id, message)
            except Exception:
                pass
            
            return jsonify({'success': True, 'cash_verify_limit': cash_verify_limit})
        except Exception as e:
            print(f"Set cash verify limit error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/users/<int:telegram_id>', methods=['DELETE'])
    @verify_admin_token
    def delete_user(telegram_id):
        """Delete user and all related data"""
        try:
            supabase = get_supabase_client()
            
            # Delete related data first - ignore errors if tables don't exist
            try:
                supabase.table('transactions').delete().eq('user_id', telegram_id).execute()
            except Exception as e:
                print(f"Delete transactions error (non-critical): {e}")
            
            try:
                supabase.table('verification_jobs').delete().eq('telegram_id', telegram_id).execute()
            except Exception as e:
                print(f"Delete jobs error (non-critical): {e}")
            
            try:
                supabase.table('referrals').delete().eq('referrer_id', telegram_id).execute()
                supabase.table('referrals').delete().eq('referred_id', telegram_id).execute()
            except Exception as e:
                print(f"Delete referrals error (non-critical): {e}")
            
            # Delete user
            supabase.table('users').delete().eq('telegram_id', telegram_id).execute()
            
            return jsonify({'success': True})
        except Exception as e:
            print(f"Delete user error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/jobs', methods=['GET'])
    @verify_admin_token
    def get_jobs():
        """Get all verification jobs (both legacy and SheerID Bot API) from last 24 hours"""
        try:
            supabase = get_supabase_client()
            jobs = []
            
            # Calculate 24 hours ago timestamp
            from datetime import timezone
            twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
            time_filter = twenty_four_hours_ago.isoformat()
            
            # Get legacy verification jobs from last 24 hours
            try:
                legacy_response = supabase.table('verification_jobs').select('*').gte('created_at', time_filter).order('created_at', desc=True).limit(500).execute()
                if legacy_response.data:
                    for job in legacy_response.data:
                        jobs.append({
                            'job_id': job.get('job_id'),
                            'status': job.get('status'),
                            'verification_type': job.get('verification_type', 'legacy'),
                            'university': job.get('university'),
                            'created_at': job.get('created_at')
                        })
            except Exception as e:
                print(f"Error loading legacy jobs: {e}")
            
            # Get SheerID Bot API jobs from last 24 hours
            try:
                sheerid_response = supabase.table('sheerid_bot_jobs').select('*').gte('created_at', time_filter).order('created_at', desc=True).limit(500).execute()
                if sheerid_response.data:
                    for job in sheerid_response.data:
                        # Check if this is a fraud rejection
                        result_details = job.get('result_details') or {}
                        if isinstance(result_details, str):
                            try:
                                import json
                                result_details = json.loads(result_details)
                            except:
                                result_details = {}
                        
                        # Map status for display
                        display_status = job.get('status')
                        if display_status == 'failed' and result_details.get('fraud_rejection'):
                            display_status = 'fraud_reject'
                        
                        jobs.append({
                            'job_id': job.get('job_id'),
                            'status': display_status,
                            'verification_type': job.get('verification_type', 'gemini'),
                            'university': 'SheerID Bot API',
                            'created_at': job.get('created_at')
                        })
            except Exception as e:
                print(f"Error loading SheerID Bot jobs: {e}")
            
            # Sort all jobs by created_at descending
            jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Return all jobs from last 24 hours (up to 1000)
            return jsonify(jobs[:1000])
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/jobs/recent', methods=['GET'])
    @verify_admin_token
    def get_recent_jobs():
        """Get recent verification jobs with optional type filter for status monitor"""
        try:
            supabase = get_supabase_client()
            
            # Get query parameters
            limit = int(request.args.get('limit', 200))
            job_type = request.args.get('type', None)  # 'gemini', 'perplexity', 'teacher', etc.
            
            jobs = []
            
            # Calculate time filter (last 10 minutes for real-time monitoring)
            from datetime import timezone
            ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
            time_filter = ten_minutes_ago.isoformat()
            
            # Get SheerID Bot API jobs from last 10 minutes
            try:
                query = supabase.table('sheerid_bot_jobs').select('*').gte('created_at', time_filter)
                
                # Filter by verification type if specified
                if job_type:
                    query = query.eq('verification_type', job_type)
                
                sheerid_response = query.order('created_at', desc=True).limit(limit).execute()
                
                if sheerid_response.data:
                    for job in sheerid_response.data:
                        # Check if this is a fraud rejection
                        result_details = job.get('result_details') or {}
                        if isinstance(result_details, str):
                            try:
                                import json
                                result_details = json.loads(result_details)
                            except:
                                result_details = {}
                        
                        # Map status for display
                        display_status = job.get('status')
                        if display_status == 'failed' and result_details.get('fraud_rejection'):
                            display_status = 'fraud_reject'
                        
                        jobs.append({
                            'job_id': job.get('job_id'),
                            'status': display_status,
                            'verification_type': job.get('verification_type', 'gemini'),
                            'verification_link': job.get('verification_link', ''),
                            'created_at': job.get('created_at'),
                            'completed_at': job.get('completed_at')
                        })
            except Exception as e:
                print(f"Error loading SheerID Bot jobs: {e}")
            
            # Sort by created_at descending
            jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return jsonify({'jobs': jobs[:limit], 'count': len(jobs)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/status-monitor/jobs', methods=['GET'])
    def get_status_monitor_jobs():
        """Public endpoint for status monitor - Get recent verification jobs from sheerid_bot_jobs table"""
        try:
            supabase = get_supabase_client()
            
            if not supabase:
                print("[ERROR] Supabase client is None!")
                return jsonify({'jobs': [], 'count': 0, 'error': 'Database connection failed'}), 500
            
            # Get query parameters
            limit = int(request.args.get('limit', 200))
            job_type = request.args.get('type', 'gemini')  # Default to gemini
            
            jobs = []
            
            # Calculate time filter (last 30 minutes)
            from datetime import timezone
            thirty_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
            time_filter = thirty_minutes_ago.isoformat()
            
            # Get from sheerid_bot_jobs table (where Gemini/Perplexity/Teacher jobs are stored)
            try:
                print(f"[DEBUG] Querying sheerid_bot_jobs table with limit={limit}, type={job_type}")
                
                # Build query - select all needed columns (without verification_link)
                query = supabase.table('sheerid_bot_jobs').select(
                    'job_id, telegram_id, status, verification_type, created_at, completed_at, result_details'
                ).gte('created_at', time_filter)
                
                # Filter by verification type
                if job_type:
                    print(f"[DEBUG] Filtering by verification_type = {job_type}")
                    query = query.eq('verification_type', job_type)
                
                # Execute query
                print(f"[DEBUG] Executing query...")
                response = query.order('created_at', desc=True).limit(limit).execute()
                
                print(f"[DEBUG] Response type: {type(response)}")
                
                if response is None:
                    print("[ERROR] Response is None!")
                    return jsonify({'jobs': [], 'count': 0, 'error': 'Query returned None'}), 500
                
                data = getattr(response, 'data', None)
                print(f"[DEBUG] Response.data type: {type(data)}")
                print(f"[DEBUG] Query response: {len(data if data else [])} jobs found")
                
                if data:
                    for job in data:
                        # Check if this is a fraud rejection
                        result_details = job.get('result_details') or {}
                        if isinstance(result_details, str):
                            try:
                                import json
                                result_details = json.loads(result_details)
                            except:
                                result_details = {}
                        
                        # Map status for display
                        display_status = job.get('status', 'pending')
                        
                        # Check for fraud rejection
                        if display_status == 'failed' and result_details.get('fraud_rejection'):
                            display_status = 'fraud_reject'
                        elif display_status == 'completed':
                            display_status = 'success'
                        elif display_status == 'canceled':
                            display_status = 'cancelled'
                        
                        job_data = {
                            'job_id': job.get('job_id', 'N/A'),
                            'status': display_status,
                            'verification_type': job.get('verification_type') or job_type,
                            'verification_link': '',  # Not available in sheerid_bot_jobs table
                            'created_at': job.get('created_at'),
                            'completed_at': job.get('completed_at'),
                            'job_type': 'sheerid_bot'
                        }
                        jobs.append(job_data)
                        print(f"[DEBUG] Added job: {job_data['job_id']} - {job_data['status']}")
                else:
                    print("[DEBUG] No data returned from query - response.data is empty or None")
            except Exception as e:
                print(f"[ERROR] Error loading sheerid_bot_jobs: {e}")
                import traceback
                traceback.print_exc()
            
            # Sort by created_at descending
            if jobs:
                jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            print(f"[DEBUG] Returning {len(jobs)} jobs")
            return jsonify({'jobs': jobs[:limit], 'count': len(jobs)})
        except Exception as e:
            print(f"[ERROR] Status monitor endpoint error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'jobs': [], 'count': 0, 'error': str(e)}), 500
    
    @app.route('/api/status-monitor/locket-activations', methods=['GET'])
    def get_locket_activations():
        """Public endpoint for status monitor - Get recent Locket Gold activations"""
        try:
            supabase = get_supabase_client()
            
            if not supabase:
                return jsonify({'activations': [], 'count': 0, 'error': 'Database connection failed'}), 500
            
            # Get query parameters
            limit = int(request.args.get('limit', 100))
            
            # Calculate time filter (last 30 minutes)
            from datetime import timezone
            thirty_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
            time_filter = thirty_minutes_ago.isoformat()
            
            # Query locket_activations table
            response = supabase.table('locket_activations').select(
                'id, telegram_id, locket_username, locket_uid, status, payment_type, amount_charged, '
                'nextdns_profile_id, nextdns_link, error_message, created_at, completed_at'
            ).gte('created_at', time_filter).order('created_at', desc=True).limit(limit).execute()
            
            activations = []
            if response.data:
                for activation in response.data:
                    # Calculate duration if completed
                    duration_seconds = None
                    if activation.get('completed_at') and activation.get('created_at'):
                        try:
                            completed = datetime.fromisoformat(activation['completed_at'].replace('Z', '+00:00'))
                            created = datetime.fromisoformat(activation['created_at'].replace('Z', '+00:00'))
                            duration_seconds = (completed - created).total_seconds()
                        except:
                            pass
                    
                    activation_data = {
                        'id': activation.get('id'),
                        'telegram_id': mask_telegram_id(activation.get('telegram_id')),
                        'locket_username': activation.get('locket_username'),
                        'locket_uid': activation.get('locket_uid'),
                        'status': activation.get('status'),
                        'payment_type': activation.get('payment_type'),
                        'amount_charged': activation.get('amount_charged'),
                        'has_dns': bool(activation.get('nextdns_profile_id')),
                        'error_message': activation.get('error_message'),
                        'created_at': activation.get('created_at'),
                        'completed_at': activation.get('completed_at'),
                        'duration_seconds': duration_seconds
                    }
                    activations.append(activation_data)
            
            # Calculate statistics
            stats = {
                'total': len(activations),
                'success': sum(1 for a in activations if a['status'] == 'success'),
                'failed': sum(1 for a in activations if a['status'] == 'failed'),
                'processing': sum(1 for a in activations if a['status'] == 'processing'),
                'cash_revenue': sum(a['amount_charged'] for a in activations if a['payment_type'] == 'cash' and a['status'] == 'success'),
                'coins_revenue': sum(a['amount_charged'] for a in activations if a['payment_type'] == 'coins' and a['status'] == 'success')
            }
            
            return jsonify({
                'activations': activations,
                'count': len(activations),
                'stats': stats
            })
            
        except Exception as e:
            print(f"[ERROR] Locket activations endpoint error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'activations': [], 'count': 0, 'error': str(e)}), 500
    
    @app.route('/api/admin/maintenance-status', methods=['GET'])
    def get_maintenance_status():
        """Get maintenance status for status monitor (public endpoint)"""
        try:
            supabase = get_supabase_client()
            
            # Get maintenance settings
            maintenance_mode = False
            verify_maintenance = False
            
            try:
                response = supabase.table('bot_config').select('*').execute()
                if response.data:
                    for item in response.data:
                        key = item.get('config_key') or item.get('key') or item.get('name')
                        value = item.get('config_value') or item.get('value')
                        
                        if key == 'maintenance_mode':
                            maintenance_mode = str(value).lower() in ['true', '1', 'yes']
                        elif key == 'verify_maintenance':
                            verify_maintenance = str(value).lower() in ['true', '1', 'yes']
            except Exception as e:
                print(f"Error getting maintenance status: {e}")
            
            # If either maintenance mode is on, system is in maintenance
            is_maintenance = maintenance_mode or verify_maintenance
            
            return jsonify({
                'is_maintenance': is_maintenance,
                'maintenance_mode': maintenance_mode,
                'verify_maintenance': verify_maintenance
            })
        except Exception as e:
            return jsonify({'error': str(e), 'is_maintenance': False}), 500
    
    @app.route('/api/admin/transactions', methods=['GET'])
    @verify_admin_token
    def get_transactions():
        """Get all transactions"""
        try:
            supabase = get_supabase_client()
            try:
                response = supabase.table('transactions').select('*').order('created_at', desc=True).limit(200).execute()
            except Exception:
                # Fallback without order
                response = supabase.table('transactions').select('*').limit(200).execute()
            return jsonify(response.data if response.data else [])
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/referrals', methods=['GET'])
    @verify_admin_token
    def get_referrals():
        """Get all referrals"""
        try:
            supabase = get_supabase_client()
            response = supabase.table('referrals').select('*').order('created_at', desc=True).limit(200).execute()
            return jsonify(response.data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/settings', methods=['GET'])
    @verify_admin_token
    def get_settings():
        """Get system settings"""
        try:
            supabase = get_supabase_client()
            
            settings = {}
            try:
                response = supabase.table('bot_config').select('*').execute()
                if response.data:
                    for item in response.data:
                        # Handle different column names - prioritize config_key/config_value
                        key = item.get('config_key') or item.get('key') or item.get('name')
                        value = item.get('config_value') or item.get('value')
                        if key and value is not None:
                            settings[key] = value
            except Exception as e:
                print(f"Settings bot_config error: {e}")
                # Return defaults if table doesn't exist or has issues
            
            return jsonify({
                'maintenance_mode': str(settings.get('maintenance_mode', 'false')).lower() == 'true',
                'verify_maintenance': str(settings.get('verify_maintenance', 'false')).lower() == 'true',
                'vc_maintenance': str(settings.get('vc_maintenance', 'false')).lower() == 'true',
                'binance_maintenance': str(settings.get('binance_maintenance', 'false')).lower() == 'true',
                'fast_mode': str(settings.get('fast_mode', 'true')).lower() == 'true',
                'welcome_bonus': 0,
                'verify_cost': 5,
                'referral_bonus': 1
            })
        except Exception as e:
            print(f"Settings general error: {e}")
            # Return defaults on any error
            return jsonify({
                'maintenance_mode': False,
                'verify_maintenance': False,
                'vc_maintenance': False,
                'binance_maintenance': False,
                'fast_mode': True,
                'welcome_bonus': 0,
                'verify_cost': 5,
                'referral_bonus': 1
            })
    
    @app.route('/api/admin/settings/maintenance', methods=['POST'])
    @verify_admin_token
    def update_maintenance():
        """Update maintenance mode"""
        try:
            data = request.json
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            enabled = data.get('enabled', False)
            print(f"🔧 Setting maintenance_mode to: {enabled}")
            
            supabase = get_supabase_client()
            if not supabase:
                print("❌ Supabase client is None")
                return jsonify({'error': 'Database connection failed'}), 500
            
            config_value = 'true' if enabled else 'false'
            config_key = 'maintenance_mode'
            
            try:
                # Use upsert with correct column names (config_key, config_value)
                result = supabase.table('bot_config').upsert(
                    {'config_key': config_key, 'config_value': config_value},
                    on_conflict='config_key'
                ).execute()
                print(f"✅ Upsert result: {result}")
            except Exception as upsert_err:
                print(f"Upsert failed: {upsert_err}, trying select then update/insert")
                # Fallback: check if exists first
                try:
                    check = supabase.table('bot_config').select('*').eq('config_key', config_key).execute()
                    if check.data:
                        result = supabase.table('bot_config').update({'config_value': config_value}).eq('config_key', config_key).execute()
                    else:
                        result = supabase.table('bot_config').insert({'config_key': config_key, 'config_value': config_value}).execute()
                except Exception as fallback_err:
                    print(f"Fallback also failed: {fallback_err}")
                    return jsonify({'error': str(fallback_err)}), 500
            
            print(f"✅ Maintenance mode set to: {enabled}")
            return jsonify({'success': True, 'enabled': enabled})
        except Exception as e:
            import traceback
            print(f"❌ Error updating maintenance mode: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/settings/verify-maintenance', methods=['POST'])
    @verify_admin_token
    def update_verify_maintenance():
        """Update verify maintenance mode"""
        try:
            data = request.json
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            enabled = data.get('enabled', False)
            config_value = 'true' if enabled else 'false'
            config_key = 'verify_maintenance'
            print(f"🔧 Setting verify_maintenance to: {config_value}")
            
            supabase = get_supabase_client()
            if not supabase:
                print("❌ Supabase client is None")
                return jsonify({'error': 'Database connection failed'}), 500
            
            try:
                # Use upsert with correct column names (config_key, config_value)
                result = supabase.table('bot_config').upsert(
                    {'config_key': config_key, 'config_value': config_value},
                    on_conflict='config_key'
                ).execute()
                print(f"✅ Upsert result: {result}")
            except Exception as upsert_err:
                print(f"Upsert failed: {upsert_err}, trying select then update/insert")
                # Fallback: check if exists first
                try:
                    check = supabase.table('bot_config').select('*').eq('config_key', config_key).execute()
                    if check.data:
                        result = supabase.table('bot_config').update({'config_value': config_value}).eq('config_key', config_key).execute()
                    else:
                        result = supabase.table('bot_config').insert({'config_key': config_key, 'config_value': config_value}).execute()
                except Exception as fallback_err:
                    print(f"Fallback also failed: {fallback_err}")
                    return jsonify({'error': str(fallback_err)}), 500
            
            print(f"✅ Verify maintenance set to: {enabled}")
            return jsonify({'success': True, 'enabled': enabled})
        except Exception as e:
            import traceback
            print(f"❌ Error updating verify maintenance: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/settings/vc-maintenance', methods=['POST'])
    @verify_admin_token
    def update_vc_maintenance():
        """Update VC (Teacher) maintenance mode"""
        try:
            data = request.json
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            enabled = data.get('enabled', False)
            config_value = 'true' if enabled else 'false'
            config_key = 'vc_maintenance'
            print(f"🎓 Setting vc_maintenance to: {config_value}")
            
            supabase = get_supabase_client()
            if not supabase:
                print("❌ Supabase client is None")
                return jsonify({'error': 'Database connection failed'}), 500
            
            try:
                result = supabase.table('bot_config').upsert(
                    {'config_key': config_key, 'config_value': config_value},
                    on_conflict='config_key'
                ).execute()
                print(f"✅ Upsert result: {result}")
            except Exception as upsert_err:
                print(f"Upsert failed: {upsert_err}, trying select then update/insert")
                try:
                    check = supabase.table('bot_config').select('*').eq('config_key', config_key).execute()
                    if check.data:
                        result = supabase.table('bot_config').update({'config_value': config_value}).eq('config_key', config_key).execute()
                    else:
                        result = supabase.table('bot_config').insert({'config_key': config_key, 'config_value': config_value}).execute()
                except Exception as fallback_err:
                    print(f"Fallback also failed: {fallback_err}")
                    return jsonify({'error': str(fallback_err)}), 500
            
            print(f"🎓 VC maintenance set to: {enabled}")
            return jsonify({'success': True, 'enabled': enabled})
        except Exception as e:
            import traceback
            print(f"❌ Error updating VC maintenance: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/settings/binance-maintenance', methods=['POST'])
    @verify_admin_token
    def update_binance_maintenance():
        """Update Binance/USDT maintenance mode"""
        try:
            data = request.json
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            enabled = data.get('enabled', False)
            config_value = 'true' if enabled else 'false'
            config_key = 'binance_maintenance'
            print(f"💰 Setting binance_maintenance to: {config_value}")
            
            supabase = get_supabase_client()
            if not supabase:
                print("❌ Supabase client is None")
                return jsonify({'error': 'Database connection failed'}), 500
            
            try:
                result = supabase.table('bot_config').upsert(
                    {'config_key': config_key, 'config_value': config_value},
                    on_conflict='config_key'
                ).execute()
                print(f"✅ Upsert result: {result}")
            except Exception as upsert_err:
                print(f"Upsert failed: {upsert_err}, trying select then update/insert")
                try:
                    check = supabase.table('bot_config').select('*').eq('config_key', config_key).execute()
                    if check.data:
                        result = supabase.table('bot_config').update({'config_value': config_value}).eq('config_key', config_key).execute()
                    else:
                        result = supabase.table('bot_config').insert({'config_key': config_key, 'config_value': config_value}).execute()
                except Exception as fallback_err:
                    print(f"Fallback also failed: {fallback_err}")
                    return jsonify({'error': str(fallback_err)}), 500
            
            print(f"💰 Binance maintenance set to: {enabled}")
            return jsonify({'success': True, 'enabled': enabled})
        except Exception as e:
            import traceback
            print(f"❌ Error updating Binance maintenance: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/settings/fast-mode', methods=['POST'])
    @verify_admin_token
    def update_fast_mode():
        """Update fast mode setting"""
        try:
            data = request.json
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            enabled = data.get('enabled', False)
            config_value = 'true' if enabled else 'false'
            config_key = 'fast_mode'
            print(f"⚡ Setting fast_mode to: {config_value}")
            
            supabase = get_supabase_client()
            if not supabase:
                print("❌ Supabase client is None")
                return jsonify({'error': 'Database connection failed'}), 500
            
            try:
                result = supabase.table('bot_config').upsert(
                    {'config_key': config_key, 'config_value': config_value},
                    on_conflict='config_key'
                ).execute()
                print(f"✅ Upsert result: {result}")
            except Exception as upsert_err:
                print(f"Upsert failed: {upsert_err}, trying select then update/insert")
                try:
                    check = supabase.table('bot_config').select('*').eq('config_key', config_key).execute()
                    if check.data:
                        result = supabase.table('bot_config').update({'config_value': config_value}).eq('config_key', config_key).execute()
                    else:
                        result = supabase.table('bot_config').insert({'config_key': config_key, 'config_value': config_value}).execute()
                except Exception as fallback_err:
                    print(f"Fallback also failed: {fallback_err}")
                    return jsonify({'error': str(fallback_err)}), 500
            
            print(f"⚡ Fast mode set to: {enabled}")
            return jsonify({'success': True, 'enabled': enabled})
        except Exception as e:
            import traceback
            print(f"❌ Error updating fast mode: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/settings/maintenance-message', methods=['GET', 'POST'])
    @verify_admin_token
    def maintenance_message_settings():
        """Get or update maintenance message settings"""
        try:
            supabase = get_supabase_client()
            if not supabase:
                return jsonify({'error': 'Database connection failed'}), 500
            
            if request.method == 'GET':
                # Get current maintenance message settings
                result = {}
                keys = ['maintenance_reason', 'maintenance_time', 'maintenance_channel']
                for key in keys:
                    try:
                        resp = supabase.table('bot_config').select('config_value').eq('config_key', key).execute()
                        if resp.data:
                            result[key.replace('maintenance_', '')] = resp.data[0]['config_value']
                    except:
                        pass
                return jsonify(result)
            
            else:  # POST
                data = request.json
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                
                reason = data.get('reason', 'Cập nhật hệ thống')
                time = data.get('time', '30 phút')
                channel = data.get('channel', 'https://t.me/channel_sheerid_vip_bot')
                
                # Save individual settings
                settings = {
                    'maintenance_reason': reason,
                    'maintenance_time': time,
                    'maintenance_channel': channel
                }
                
                for key, value in settings.items():
                    try:
                        supabase.table('bot_config').upsert(
                            {'config_key': key, 'config_value': value},
                            on_conflict='config_key'
                        ).execute()
                    except Exception as e:
                        print(f"Error saving {key}: {e}")
                
                # Build and save full maintenance message
                full_message = (
                    f"🔧 Bot đang trong chế độ bảo trì\n\n"
                    f"📝 Lý do: {reason}\n"
                    f"⏰ Thời gian bảo trì dự kiến: {time}\n"
                    f"📢 Sẽ thông báo khi hoàn tất bảo trì tại kênh thông báo: {channel}!\n\n"
                    f"Cảm ơn bạn đã kiên nhẫn chờ đợi! 🙏"
                )
                
                try:
                    supabase.table('bot_config').upsert(
                        {'config_key': 'maintenance_message', 'config_value': full_message},
                        on_conflict='config_key'
                    ).execute()
                except Exception as e:
                    print(f"Error saving maintenance_message: {e}")
                
                print(f"✅ Maintenance message updated: reason={reason}, time={time}")
                return jsonify({'success': True, 'message': full_message})
                
        except Exception as e:
            import traceback
            print(f"❌ Error in maintenance_message_settings: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/broadcast', methods=['POST'])
    @verify_admin_token
    def send_broadcast():
        """Send broadcast message to all users - fast concurrent sending"""
        try:
            import concurrent.futures
            import threading
            
            data = request.json
            message = data.get('message', '').strip()
            
            if not message:
                return jsonify({'error': 'Message required'}), 400
            
            supabase = get_supabase_client()
            
            # Get all users (not blocked)
            users_resp = supabase.table('users').select('telegram_id').eq('is_blocked', False).execute()
            users = users_resp.data or []
            
            if not users:
                return jsonify({'error': 'No users found'}), 400
            
            total = len(users)
            success_count = 0
            failed_count = 0
            failed_users = []
            lock = threading.Lock()
            
            # Format message with admin header
            formatted_message = f"📢 <b>Thông báo từ Admin</b>\n\n{message}"
            
            print(f"📢 Starting broadcast to {total} users (concurrent)...")
            
            def send_to_user(telegram_id):
                nonlocal success_count, failed_count
                try:
                    result = send_telegram_notification(telegram_id, formatted_message)
                    with lock:
                        if result:
                            success_count += 1
                        else:
                            failed_count += 1
                            if len(failed_users) < 10:
                                failed_users.append(telegram_id)
                    return result
                except Exception as e:
                    with lock:
                        failed_count += 1
                        if len(failed_users) < 10:
                            failed_users.append(telegram_id)
                    return False
            
            # Use ThreadPoolExecutor for concurrent sending (max 20 threads)
            telegram_ids = [u.get('telegram_id') for u in users if u.get('telegram_id')]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                executor.map(send_to_user, telegram_ids)
            
            print(f"📢 Broadcast completed: {success_count}/{total} success, {failed_count} failed")
            
            return jsonify({
                'success': True,
                'total': total,
                'sent': success_count,
                'failed': failed_count,
                'failed_users': failed_users,
                'message': f'Đã gửi {success_count}/{total} users thành công'
            })
        except Exception as e:
            print(f"Broadcast error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/verify-config', methods=['GET'])
    @verify_admin_token
    def get_verify_config():
        """Get current verify configuration"""
        try:
            supabase = get_supabase_client()
            
            # Get config from bot_config table
            config = {}
            try:
                resp = supabase.table('bot_config').select('*').execute()
                if resp.data:
                    for item in resp.data:
                        # Support both column naming conventions
                        key = item.get('config_key') or item.get('key')
                        value = item.get('config_value') or item.get('value')
                        if key:
                            config[key] = value
            except Exception as e:
                print(f"Error loading config: {e}")
            
            # Default values if not in database
            return jsonify({
                'student': {
                    'organization_id': config.get('student_org_id', '3720'),
                    'organization_name': config.get('student_org_name', 'University of Utah'),
                    'email_domain': config.get('student_email_domain', 'utah.edu'),
                    'card_template': config.get('student_card_template', 'uk')
                },
                'teacher': {
                    'organization_id': config.get('teacher_org_id', '642'),
                    'organization_name': config.get('teacher_org_name', 'College of DuPage (Glen Ellyn, IL)'),
                    'email_domain': config.get('teacher_email_domain', 'gmail.com'),
                    'card_template': config.get('teacher_card_template', 'teacher')
                }
            })
        except Exception as e:
            print(f"Get verify config error: {e}")
            return jsonify({'error': str(e)}), 500
    
    def upsert_config(supabase, config_key, config_value):
        """Helper function to upsert config with correct column names"""
        try:
            # Try upsert with config_key/config_value columns
            result = supabase.table('bot_config').upsert(
                {'config_key': config_key, 'config_value': str(config_value)},
                on_conflict='config_key'
            ).execute()
            return result
        except Exception as e:
            print(f"Upsert error for {config_key}: {e}")
            # Fallback: check if exists then update/insert
            try:
                check = supabase.table('bot_config').select('*').eq('config_key', config_key).execute()
                if check.data:
                    return supabase.table('bot_config').update({'config_value': str(config_value)}).eq('config_key', config_key).execute()
                else:
                    return supabase.table('bot_config').insert({'config_key': config_key, 'config_value': str(config_value)}).execute()
            except Exception as fallback_err:
                print(f"Fallback upsert error: {fallback_err}")
                raise fallback_err
    
    @app.route('/api/admin/verify-config', methods=['POST'])
    @verify_admin_token
    def update_verify_config():
        """Update verify configuration"""
        try:
            data = request.json
            supabase = get_supabase_client()
            
            # Update student config
            if 'student' in data:
                student = data['student']
                if 'organization_id' in student:
                    upsert_config(supabase, 'student_org_id', student['organization_id'])
                if 'organization_name' in student:
                    upsert_config(supabase, 'student_org_name', student['organization_name'])
                if 'email_domain' in student:
                    upsert_config(supabase, 'student_email_domain', student['email_domain'])
                if 'card_template' in student:
                    upsert_config(supabase, 'student_card_template', student['card_template'])
            
            # Update teacher config
            if 'teacher' in data:
                teacher = data['teacher']
                if 'organization_id' in teacher:
                    upsert_config(supabase, 'teacher_org_id', teacher['organization_id'])
                if 'organization_name' in teacher:
                    upsert_config(supabase, 'teacher_org_name', teacher['organization_name'])
                if 'email_domain' in teacher:
                    upsert_config(supabase, 'teacher_email_domain', teacher['email_domain'])
                if 'card_template' in teacher:
                    upsert_config(supabase, 'teacher_card_template', teacher['card_template'])
            
            return jsonify({'success': True, 'message': 'Config updated'})
        except Exception as e:
            print(f"Update verify config error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/upload-card-template', methods=['POST'])
    @verify_admin_token
    def upload_card_template():
        """Upload card template image"""
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            template_type = request.form.get('type', 'uk')  # uk, teacher, germany, etc.
            
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg'}
            file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if file_ext not in allowed_extensions:
                return jsonify({'error': 'Only PNG, JPG, JPEG files allowed'}), 400
            
            # Save file with standardized name in api/ folder
            filename = f'card-template-{template_type}.png'
            api_dir = os.path.dirname(__file__)  # api/ folder
            filepath = os.path.join(api_dir, filename)
            
            file.save(filepath)
            print(f"✅ Card template saved: {filepath}")
            
            return jsonify({
                'success': True,
                'filename': filename,
                'message': f'Card template {template_type} uploaded successfully'
            })
        except Exception as e:
            print(f"Upload card template error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/card-templates', methods=['GET'])
    @verify_admin_token
    def list_card_templates():
        """List available card templates"""
        try:
            import glob
            api_dir = os.path.dirname(__file__)  # api/ folder
            templates = []
            
            # Find all card-template-*.png files in api/ folder
            pattern = os.path.join(api_dir, 'card-template-*.png')
            for filepath in glob.glob(pattern):
                filename = os.path.basename(filepath)
                # Extract template name from filename
                template_name = filename.replace('card-template-', '').replace('.png', '')
                templates.append({
                    'name': template_name,
                    'filename': filename,
                    'path': filepath
                })
            
            return jsonify({'templates': templates})
        except Exception as e:
            print(f"List templates error: {e}")
            return jsonify({'error': str(e)}), 500
    
    # ==================== GIFTCODE MANAGEMENT ====================
    
    @app.route('/api/admin/giftcodes', methods=['GET'])
    @verify_admin_token
    def list_giftcodes():
        """List all giftcodes"""
        try:
            supabase = get_supabase_client()
            result = supabase.table('giftcodes').select('*').order('created_at', desc=True).execute()
            return jsonify({'giftcodes': result.data or []})
        except Exception as e:
            print(f"List giftcodes error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/giftcodes', methods=['POST'])
    @verify_admin_token
    def create_giftcode():
        """Create new giftcode"""
        try:
            data = request.json
            code = data.get('code', '').upper().strip()
            reward_type = data.get('reward_type', 'coins')  # coins or cash
            reward_amount = int(data.get('reward_amount', 0))
            max_uses = int(data.get('max_uses', 1))
            
            if not code:
                return jsonify({'error': 'Code is required'}), 400
            if reward_amount <= 0:
                return jsonify({'error': 'Reward amount must be positive'}), 400
            if max_uses <= 0:
                return jsonify({'error': 'Max uses must be positive'}), 400
            
            supabase = get_supabase_client()
            
            # Check if code exists
            existing = supabase.table('giftcodes').select('id').eq('code', code).execute()
            if existing.data:
                return jsonify({'error': 'Giftcode already exists'}), 400
            
            # Create giftcode
            giftcode_data = {
                'code': code,
                'reward_type': reward_type,
                'reward_amount': reward_amount,
                'max_uses': max_uses,
                'current_uses': 0,
                'is_active': True,
                'created_at': datetime.now().isoformat()
            }
            
            result = supabase.table('giftcodes').insert(giftcode_data).execute()
            
            if result.data:
                return jsonify({'success': True, 'giftcode': result.data[0]})
            return jsonify({'error': 'Failed to create giftcode'}), 500
        except Exception as e:
            print(f"Create giftcode error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/giftcodes/<int:giftcode_id>', methods=['DELETE'])
    @verify_admin_token
    def delete_giftcode(giftcode_id):
        """Delete/deactivate giftcode"""
        try:
            supabase = get_supabase_client()
            
            # Soft delete - just deactivate
            result = supabase.table('giftcodes').update({
                'is_active': False,
                'updated_at': datetime.now().isoformat()
            }).eq('id', giftcode_id).execute()
            
            if result.data:
                return jsonify({'success': True, 'message': 'Giftcode deactivated'})
            return jsonify({'error': 'Giftcode not found'}), 404
        except Exception as e:
            print(f"Delete giftcode error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/giftcodes/<int:giftcode_id>/usage', methods=['GET'])
    @verify_admin_token
    def get_giftcode_usage(giftcode_id):
        """Get giftcode usage history"""
        try:
            supabase = get_supabase_client()
            
            # Get usage records with user info
            result = supabase.table('giftcode_usage').select(
                '*, users(telegram_id, username, first_name)'
            ).eq('giftcode_id', giftcode_id).order('used_at', desc=True).execute()
            
            return jsonify({'usage': result.data or []})
        except Exception as e:
            print(f"Get giftcode usage error: {e}")
            return jsonify({'error': str(e)}), 500
    
    # ==================== VERIFY STATISTICS ====================
    
    @app.route('/api/admin/stats/verify-daily', methods=['GET'])
    @verify_admin_token
    def get_verify_daily_stats():
        """Get daily verification statistics for chart"""
        try:
            supabase = get_supabase_client()
            days = int(request.args.get('days', 7))  # Default 7 days
            
            # Get verification jobs grouped by date
            from datetime import timezone
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            result = supabase.table('verification_jobs').select(
                'id, status, created_at'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).execute()
            
            # Group by date
            daily_stats = {}
            for job in (result.data or []):
                try:
                    created_at = job.get('created_at', '')
                    if created_at:
                        date_str = created_at[:10]  # YYYY-MM-DD
                        if date_str not in daily_stats:
                            daily_stats[date_str] = {'total': 0, 'completed': 0, 'failed': 0, 'pending': 0}
                        daily_stats[date_str]['total'] += 1
                        status = job.get('status', 'pending')
                        if status == 'completed':
                            daily_stats[date_str]['completed'] += 1
                        elif status == 'failed':
                            daily_stats[date_str]['failed'] += 1
                        else:
                            daily_stats[date_str]['pending'] += 1
                except Exception:
                    pass
            
            # Convert to sorted list
            stats_list = []
            for date_str in sorted(daily_stats.keys()):
                stats_list.append({
                    'date': date_str,
                    **daily_stats[date_str]
                })
            
            return jsonify({'stats': stats_list})
        except Exception as e:
            print(f"Get verify daily stats error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/stats/verify-summary', methods=['GET'])
    @verify_admin_token
    def get_verify_summary():
        """Get verification summary statistics - using Vietnam timezone (UTC+7) and last 24 hours"""
        try:
            supabase = get_supabase_client()
            
            # Vietnam timezone (UTC+7)
            from datetime import timezone, timedelta
            vietnam_tz = timezone(timedelta(hours=7))
            now_vietnam = datetime.now(vietnam_tz)
            
            # Get start of today in Vietnam timezone
            today_start_vietnam = now_vietnam.replace(hour=0, minute=0, second=0, microsecond=0)
            today_start_utc = today_start_vietnam.astimezone(timezone.utc)
            
            # Last 24 hours for success rate
            twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Last 24 hours stats
            today_jobs = supabase.table('verification_jobs').select(
                'id, status', count='exact'
            ).gte('created_at', twenty_four_hours_ago.isoformat()).execute()
            
            today_completed = supabase.table('verification_jobs').select(
                'id', count='exact'
            ).gte('created_at', twenty_four_hours_ago.isoformat()).eq('status', 'completed').execute()
            
            # Get failed count for success rate calculation (exclude fraud_reject, skipped, pending)
            today_failed = supabase.table('verification_jobs').select(
                'id', count='exact'
            ).gte('created_at', twenty_four_hours_ago.isoformat()).eq('status', 'failed').execute()
            
            # Total stats
            total_jobs = supabase.table('verification_jobs').select('id').execute()
            total_completed = supabase.table('verification_jobs').select('id').eq('status', 'completed').execute()
            total_failed = supabase.table('verification_jobs').select('id').eq('status', 'failed').execute()
            
            # Calculate success rate from last 24 hours
            # Only count completed and failed (exclude fraud_reject, skipped, pending, etc.)
            today_total = len(today_jobs.data) if today_jobs.data else 0
            today_success = len(today_completed.data) if today_completed.data else 0
            today_fail = len(today_failed.data) if today_failed.data else 0
            
            # Success rate = completed / (completed + failed)
            success_rate_denominator = today_success + today_fail
            success_rate_24h = round(today_success / max(success_rate_denominator, 1) * 100, 1)
            
            return jsonify({
                'today': {
                    'total': today_total,
                    'completed': today_success
                },
                'all_time': {
                    'total': len(total_jobs.data) if total_jobs.data else 0,
                    'completed': len(total_completed.data) if total_completed.data else 0
                },
                'success_rate': success_rate_24h
            })
        except Exception as e:
            print(f"Get verify summary error: {e}")
            return jsonify({'error': str(e)}), 500

    
    # ==================== SELLER MANAGEMENT ====================
    
    @app.route('/api/admin/sellers', methods=['GET'])
    @verify_admin_token
    def list_sellers():
        """List all sellers"""
        try:
            supabase = get_supabase_client()
            result = supabase.table('sellers').select('*').order('created_at', desc=True).execute()
            return jsonify({'sellers': result.data or []})
        except Exception as e:
            print(f"List sellers error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/sellers', methods=['POST'])
    @verify_admin_token
    def create_seller():
        """Create new seller"""
        try:
            import secrets
            
            data = request.json
            name = data.get('name', '').strip()
            email = data.get('email', '').strip()
            credits = int(data.get('credits', 0))
            exchange_rate = int(data.get('exchange_rate', 1000))
            webhook_url = data.get('webhook_url', '').strip()
            telegram_id = data.get('telegram_id')
            
            if not name:
                return jsonify({'error': 'Name is required'}), 400
            
            if exchange_rate < 1:
                return jsonify({'error': 'Exchange rate must be at least 1'}), 400
            
            # Generate API key
            api_key = f"sk_{secrets.token_hex(24)}"
            
            supabase = get_supabase_client()
            
            seller_data = {
                'name': name,
                'email': email if email else None,
                'api_key': api_key,
                'credits': credits,
                'exchange_rate': exchange_rate,
                'total_used': 0,
                'webhook_url': webhook_url if webhook_url else None,
                'rate_limit': 10,
                'is_active': True,
                'created_at': datetime.now().isoformat()
            }
            
            # Add telegram_id if provided
            if telegram_id:
                seller_data['telegram_id'] = int(telegram_id)
            
            result = supabase.table('sellers').insert(seller_data).execute()
            
            if result.data:
                # Send notification to seller via Telegram if telegram_id provided
                if telegram_id:
                    try:
                        from .telegram import send_telegram_message_plain
                        
                        # Get user language
                        user_lang = 'vi'
                        try:
                            user_result = supabase.table('users').select('language').eq('telegram_id', int(telegram_id)).execute()
                            if user_result.data:
                                user_lang = user_result.data[0].get('language', 'vi') or 'vi'
                        except:
                            pass
                        
                        # Build message based on language
                        seller_id_val = result.data[0]['id']
                        if user_lang == 'en':
                            seller_msg = (
                                "🎉 Welcome! You are now a Seller!\n\n"
                                "✅ Your Seller API account has been created successfully.\n\n"
                                "📋 Account Info:\n"
                                f"🆔 Seller ID: {seller_id_val}\n"
                                f"🔑 API Key: {api_key}\n"
                                f"💰 Credits: {credits}\n\n"
                                "📚 API Guide: https://dqsheerid.vercel.app/docs\n\n"
                                "💳 Buy more credits: /buycredits [amount]\n"
                                "💱 Rate: 3 cash = 1 credit\n\n"
                                "⚠️ Note: Please save this API Key carefully!\n"
                                "📞 Support: @meepzizhere"
                            )
                        elif user_lang == 'zh':
                            seller_msg = (
                                "🎉 欢迎！您现在是卖家了！\n\n"
                                "✅ 您的卖家API账户已成功创建。\n\n"
                                "📋 账户信息：\n"
                                f"🆔 卖家ID: {seller_id_val}\n"
                                f"🔑 API密钥: {api_key}\n"
                                f"💰 积分: {credits}\n\n"
                                "📚 API指南: https://dqsheerid.vercel.app/docs\n\n"
                                "💳 购买更多积分: /buycredits [数量]\n"
                                "💱 汇率: 3 cash = 1 credit\n\n"
                                "⚠️ 注意：请妥善保存此API密钥！\n"
                                "📞 支持: @meepzizhere"
                            )
                        else:  # Vietnamese default
                            seller_msg = (
                                "🎉 Chào mừng bạn đã trở thành Seller!\n\n"
                                "✅ Tài khoản Seller API của bạn đã được tạo thành công.\n\n"
                                "📋 Thông tin tài khoản:\n"
                                f"🆔 Seller ID: {seller_id_val}\n"
                                f"🔑 API Key: {api_key}\n"
                                f"💰 Credits: {credits}\n\n"
                                "📚 Hướng dẫn API: https://dqsheerid.vercel.app/docs\n\n"
                                "💳 Mua thêm credits: /buycredits [số_lượng]\n"
                                "💱 Tỷ giá: 3 cash = 1 credit\n\n"
                                "⚠️ Lưu ý: Hãy lưu API Key này cẩn thận!\n"
                                "📞 Hỗ trợ: @meepzizhere"
                            )
                        
                        send_telegram_message_plain(int(telegram_id), seller_msg)
                    except Exception as notify_err:
                        print(f"Failed to notify seller: {notify_err}")
                
                return jsonify({'success': True, 'seller': result.data[0]})
            return jsonify({'error': 'Failed to create seller'}), 500
        except Exception as e:
            print(f"Create seller error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/sellers/<int:seller_id>', methods=['GET'])
    @verify_admin_token
    def get_seller(seller_id):
        """Get seller details"""
        try:
            supabase = get_supabase_client()
            result = supabase.table('sellers').select('*').eq('id', seller_id).execute()
            
            if result.data:
                return jsonify({'seller': result.data[0]})
            return jsonify({'error': 'Seller not found'}), 404
        except Exception as e:
            print(f"Get seller error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/sellers/<int:seller_id>', methods=['DELETE'])
    @verify_admin_token
    def delete_seller(seller_id):
        """Delete seller"""
        try:
            supabase = get_supabase_client()
            
            # Delete seller jobs first
            try:
                supabase.table('seller_jobs').delete().eq('seller_id', seller_id).execute()
            except Exception as e:
                print(f"Delete seller jobs error (non-critical): {e}")
            
            # Delete seller
            result = supabase.table('sellers').delete().eq('id', seller_id).execute()
            
            return jsonify({'success': True, 'message': 'Seller deleted'})
        except Exception as e:
            print(f"Delete seller error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/sellers/<int:seller_id>/credits', methods=['POST'])
    @verify_admin_token
    def add_seller_credits(seller_id):
        """Add credits to seller"""
        try:
            data = request.json
            credits = int(data.get('credits', 0))
            
            if credits <= 0:
                return jsonify({'error': 'Credits must be positive'}), 400
            
            supabase = get_supabase_client()
            
            # Get current credits
            seller = supabase.table('sellers').select('credits').eq('id', seller_id).execute()
            if not seller.data:
                return jsonify({'error': 'Seller not found'}), 404
            
            current_credits = seller.data[0].get('credits', 0)
            new_balance = current_credits + credits
            
            # Update credits
            result = supabase.table('sellers').update({
                'credits': new_balance,
                'updated_at': datetime.now().isoformat()
            }).eq('id', seller_id).execute()
            
            if result.data:
                return jsonify({
                    'success': True,
                    'added': credits,
                    'new_balance': new_balance
                })
            return jsonify({'error': 'Failed to update credits'}), 500
        except Exception as e:
            print(f"Add seller credits error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/sellers/<int:seller_id>/toggle', methods=['POST'])
    @verify_admin_token
    def toggle_seller(seller_id):
        """Toggle seller active status"""
        try:
            data = request.json
            is_active = data.get('is_active', True)
            
            supabase = get_supabase_client()
            
            result = supabase.table('sellers').update({
                'is_active': is_active,
                'updated_at': datetime.now().isoformat()
            }).eq('id', seller_id).execute()
            
            if result.data:
                return jsonify({'success': True, 'is_active': is_active})
            return jsonify({'error': 'Seller not found'}), 404
        except Exception as e:
            print(f"Toggle seller error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/sellers/<int:seller_id>/exchange-rate', methods=['POST'])
    @verify_admin_token
    def update_seller_exchange_rate(seller_id):
        """Update seller exchange rate (VND per credit)"""
        try:
            data = request.json
            exchange_rate = data.get('exchange_rate', 1000)
            
            if exchange_rate < 1:
                return jsonify({'error': 'Exchange rate must be at least 1'}), 400
            
            supabase = get_supabase_client()
            
            result = supabase.table('sellers').update({
                'exchange_rate': int(exchange_rate),
                'updated_at': datetime.now().isoformat()
            }).eq('id', seller_id).execute()
            
            if result.data:
                return jsonify({'success': True, 'exchange_rate': exchange_rate})
            return jsonify({'error': 'Seller not found'}), 404
        except Exception as e:
            print(f"Update seller exchange rate error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/seller-jobs', methods=['GET'])
    @verify_admin_token
    def list_seller_jobs():
        """List seller jobs"""
        try:
            limit = int(request.args.get('limit', 50))
            seller_id = request.args.get('seller_id')
            
            supabase = get_supabase_client()
            
            query = supabase.table('seller_jobs').select('*').order('created_at', desc=True).limit(limit)
            
            if seller_id:
                query = query.eq('seller_id', int(seller_id))
            
            result = query.execute()
            
            return jsonify({'jobs': result.data or []})
        except Exception as e:
            print(f"List seller jobs error: {e}")
            return jsonify({'error': str(e)}), 500

    # ==================== PROXY MANAGEMENT ====================
    
    @app.route('/api/admin/proxy/status', methods=['GET'])
    @verify_admin_token
    def get_proxy_status():
        """Get current proxy configuration and status"""
        try:
            # Current proxy config (hardcoded in index.py) - Updated Dec 2024
            return jsonify({
                'status': 'Active',
                'host': 'rp.scrapegw.com',
                'port': '6060',
                'user': 'n2aygeuavdsf1js-odds-5+100-country-us',
                'protocol': 'SOCKS5',
                'rotation': 'Per Request',
                'ip': 'Rotating',
                'latency': None
            })
        except Exception as e:
            print(f"Get proxy status error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/proxy/test', methods=['POST'])
    @verify_admin_token
    def test_proxy():
        """Test proxy connection by getting IP"""
        try:
            import time
            
            # Proxy config - Updated Dec 2024
            scrape_host = 'rp.scrapegw.com'
            scrape_port = '6060'
            scrape_user = 'n2aygeuavdsf1js-odds-5+100-country-us'
            scrape_pass = 'xek0ebuosn68k4o'
            proxy_url = f"socks5://{scrape_user}:{scrape_pass}@{scrape_host}:{scrape_port}"
            
            start_time = time.time()
            
            # Try curl_cffi first (better SOCKS5 support)
            try:
                from curl_cffi.requests import Session as CurlSession
                with CurlSession() as session:
                    ip_response = session.get(
                        "https://api.ipify.org?format=json",
                        proxies={"http": proxy_url, "https": proxy_url},
                        timeout=15
                    )
                    latency = int((time.time() - start_time) * 1000)
                    
                    if ip_response.status_code == 200:
                        ip_data = ip_response.json()
                        proxy_ip = ip_data.get('ip', 'Unknown')
                        
                        # Try to get location
                        location = 'Unknown'
                        try:
                            loc_response = session.get(
                                f"http://ip-api.com/json/{proxy_ip}",
                                proxies={"http": proxy_url, "https": proxy_url},
                                timeout=10
                            )
                            if loc_response.status_code == 200:
                                loc_data = loc_response.json()
                                location = f"{loc_data.get('city', '')}, {loc_data.get('country', '')}"
                        except:
                            pass
                        
                        return jsonify({
                            'success': True,
                            'ip': proxy_ip,
                            'location': location,
                            'latency': latency,
                            'protocol': 'SOCKS5'
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'error': f'HTTP {ip_response.status_code}'
                        })
            except ImportError:
                # Fallback to requests with socks
                import requests as req
                proxies = {"http": proxy_url, "https": proxy_url}
                ip_response = req.get(
                    "https://api.ipify.org?format=json",
                    proxies=proxies,
                    timeout=15
                )
                latency = int((time.time() - start_time) * 1000)
                
                if ip_response.status_code == 200:
                    return jsonify({
                        'success': True,
                        'ip': ip_response.json().get('ip', 'Unknown'),
                        'latency': latency,
                        'protocol': 'SOCKS5'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'HTTP {ip_response.status_code}'
                    })
                    
        except Exception as e:
            print(f"Test proxy error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/admin/proxy/test-sheerid', methods=['POST'])
    @verify_admin_token
    def test_proxy_sheerid():
        """Test proxy with SheerID link"""
        try:
            import time
            import re
            
            data = request.json
            url = data.get('url', '')
            
            if not url:
                return jsonify({'success': False, 'error': 'URL required'}), 400
            
            # Extract verification ID
            verification_id = None
            if 'verificationId=' in url:
                verification_id = url.split('verificationId=')[-1].split('&')[0]
            else:
                # Try to extract from path
                match = re.search(r'/verify/([a-f0-9]+)/', url)
                if match:
                    verification_id = match.group(1)
                else:
                    # Try direct ID format
                    match = re.search(r'([a-f0-9]{24})', url)
                    if match:
                        verification_id = match.group(1)
            
            if not verification_id:
                return jsonify({'success': False, 'error': 'Could not extract verification ID from URL'}), 400
            
            # Proxy config - Updated Dec 2024
            scrape_host = 'rp.scrapegw.com'
            scrape_port = '6060'
            scrape_user = 'n2aygeuavdsf1js-odds-5+100-country-us'
            scrape_pass = 'xek0ebuosn68k4o'
            proxy_url = f"socks5://{scrape_user}:{scrape_pass}@{scrape_host}:{scrape_port}"
            
            start_time = time.time()
            
            # Get proxy IP first
            proxy_ip = 'Unknown'
            try:
                from curl_cffi.requests import Session as CurlSession
                with CurlSession() as session:
                    ip_response = session.get(
                        "https://api.ipify.org?format=json",
                        proxies={"http": proxy_url, "https": proxy_url},
                        timeout=10
                    )
                    if ip_response.status_code == 200:
                        proxy_ip = ip_response.json().get('ip', 'Unknown')
            except:
                pass
            
            # Test SheerID API
            sheerid_url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            try:
                from curl_cffi.requests import Session as CurlSession
                with CurlSession() as session:
                    response = session.get(
                        sheerid_url,
                        headers=headers,
                        proxies={"http": proxy_url, "https": proxy_url},
                        timeout=30
                    )
                    latency = int((time.time() - start_time) * 1000)
                    
                    if response.status_code == 200:
                        data = response.json()
                        current_step = data.get('currentStep', 'Unknown')
                        
                        return jsonify({
                            'success': True,
                            'proxy_ip': proxy_ip,
                            'verification_id': verification_id,
                            'current_step': current_step,
                            'latency': latency,
                            'status_code': response.status_code
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'error': f'SheerID returned HTTP {response.status_code}',
                            'proxy_ip': proxy_ip,
                            'verification_id': verification_id
                        })
            except ImportError:
                import requests as req
                proxies = {"http": proxy_url, "https": proxy_url}
                response = req.get(sheerid_url, headers=headers, proxies=proxies, timeout=30)
                latency = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    data = response.json()
                    return jsonify({
                        'success': True,
                        'proxy_ip': proxy_ip,
                        'verification_id': verification_id,
                        'current_step': data.get('currentStep', 'Unknown'),
                        'latency': latency
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'SheerID returned HTTP {response.status_code}',
                        'proxy_ip': proxy_ip
                    })
                    
        except Exception as e:
            print(f"Test SheerID proxy error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500

    
    @app.route('/api/admin/proxy/settings', methods=['GET'])
    @verify_admin_token
    def get_proxy_settings():
        """Get proxy settings from database"""
        try:
            supabase = get_supabase_client()
            
            # Try to get settings from bot_config table
            result = supabase.table('bot_config').select('value').eq('key', 'proxy_settings').execute()
            
            if result.data:
                import json
                settings = json.loads(result.data[0].get('value', '{}'))
                return jsonify({'settings': settings})
            else:
                # Return default settings
                return jsonify({'settings': {
                    'enabled': True,
                    'autoHealthChecks': True,
                    'checkInterval': 120,
                    'usageLimit': 50,
                    'cooldownPeriod': 30,
                    'fallbackRetryLimit': 3,
                    'concurrentChecks': 200,
                    'testTimeout': 15,
                    'maxRetries': 3,
                    'retryDelay': 1
                }})
        except Exception as e:
            print(f"Get proxy settings error: {e}")
            return jsonify({'settings': {
                'enabled': True,
                'autoHealthChecks': True,
                'checkInterval': 120,
                'usageLimit': 50,
                'cooldownPeriod': 30,
                'fallbackRetryLimit': 3,
                'concurrentChecks': 200,
                'testTimeout': 15,
                'maxRetries': 3,
                'retryDelay': 1
            }})
    
    @app.route('/api/admin/proxy/settings', methods=['POST'])
    @verify_admin_token
    def save_proxy_settings():
        """Save proxy settings to database"""
        try:
            import json
            data = request.json
            
            supabase = get_supabase_client()
            
            settings = {
                'enabled': data.get('enabled', True),
                'autoHealthChecks': data.get('autoHealthChecks', True),
                'checkInterval': data.get('checkInterval', 120),
                'usageLimit': data.get('usageLimit', 50),
                'cooldownPeriod': data.get('cooldownPeriod', 30),
                'fallbackRetryLimit': data.get('fallbackRetryLimit', 3),
                'concurrentChecks': data.get('concurrentChecks', 200),
                'testTimeout': data.get('testTimeout', 15),
                'maxRetries': data.get('maxRetries', 3),
                'retryDelay': data.get('retryDelay', 1)
            }
            
            # Check if settings exist
            existing = supabase.table('bot_config').select('key').eq('key', 'proxy_settings').execute()
            
            if existing.data:
                # Update existing
                result = supabase.table('bot_config').update({
                    'value': json.dumps(settings),
                    'updated_at': datetime.now().isoformat()
                }).eq('key', 'proxy_settings').execute()
            else:
                # Insert new
                result = supabase.table('bot_config').insert({
                    'key': 'proxy_settings',
                    'value': json.dumps(settings)
                }).execute()
            
            print(f"✅ Proxy settings saved: {settings}")
            return jsonify({'success': True, 'settings': settings})
        except Exception as e:
            print(f"Save proxy settings error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    # ============================================
    # UNIVERSITY FRAUD & FRAUD IPS TRACKING
    # ============================================
    
    @app.route('/api/admin/university-fraud', methods=['GET'])
    @verify_admin_token
    def get_university_fraud_list():
        """Get list of universities with fraud tracking data"""
        try:
            supabase = get_supabase_client()
            
            # Get all university fraud tracking records
            result = supabase.table('university_fraud_tracking').select('*').order('total_fraud_count', desc=True).limit(100).execute()
            
            universities = result.data if result.data else []
            
            # Count blocked universities
            blocked_count = len([u for u in universities if u.get('is_blocked')])
            
            return jsonify({
                'universities': universities,
                'total': len(universities),
                'blocked_count': blocked_count
            })
        except Exception as e:
            print(f"Get university fraud error: {e}")
            return jsonify({'universities': [], 'total': 0, 'blocked_count': 0, 'error': str(e)})
    
    @app.route('/api/admin/university-fraud/<university_id>/unblock', methods=['POST'])
    @verify_admin_token
    def unblock_university_fraud(university_id):
        """Unblock a university from fraud tracking"""
        try:
            supabase = get_supabase_client()
            
            result = supabase.table('university_fraud_tracking').update({
                'is_blocked': False,
                'consecutive_fraud_count': 0,
                'unblocked_at': datetime.utcnow().isoformat()
            }).eq('university_id', str(university_id)).execute()
            
            if result.data:
                return jsonify({'success': True, 'message': f'University {university_id} unblocked'})
            return jsonify({'success': False, 'error': 'University not found'}), 404
        except Exception as e:
            print(f"Unblock university error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/admin/university-fraud/<university_id>/reset', methods=['POST'])
    @verify_admin_token
    def reset_university_fraud(university_id):
        """Reset fraud count for a university"""
        try:
            supabase = get_supabase_client()
            
            result = supabase.table('university_fraud_tracking').update({
                'consecutive_fraud_count': 0,
                'total_fraud_count': 0,
                'is_blocked': False,
                'unblocked_at': datetime.utcnow().isoformat()
            }).eq('university_id', str(university_id)).execute()
            
            if result.data:
                return jsonify({'success': True, 'message': f'University {university_id} reset'})
            return jsonify({'success': False, 'error': 'University not found'}), 404
        except Exception as e:
            print(f"Reset university fraud error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/admin/fraud-ips', methods=['GET'])
    @verify_admin_token
    def get_fraud_ips_list():
        """Get list of fraud IPs"""
        try:
            supabase = get_supabase_client()
            
            # Get all fraud IPs, ordered by fraud count
            result = supabase.table('fraud_ips').select('*').order('fraud_count', desc=True).limit(200).execute()
            
            ips = result.data if result.data else []
            
            # Count active (still in cooldown) IPs
            now = datetime.utcnow()
            active_count = 0
            for ip in ips:
                cooldown = ip.get('cooldown_until')
                if cooldown:
                    try:
                        cooldown_dt = datetime.fromisoformat(cooldown.replace('Z', '+00:00').replace('+00:00', ''))
                        if cooldown_dt > now:
                            active_count += 1
                    except:
                        pass
            
            return jsonify({
                'ips': ips,
                'total': len(ips),
                'active_count': active_count
            })
        except Exception as e:
            print(f"Get fraud IPs error: {e}")
            return jsonify({'ips': [], 'total': 0, 'active_count': 0, 'error': str(e)})
    
    @app.route('/api/admin/fraud-ips/<ip_address>/remove', methods=['DELETE'])
    @verify_admin_token
    def remove_fraud_ip(ip_address):
        """Remove an IP from fraud list"""
        try:
            supabase = get_supabase_client()
            
            result = supabase.table('fraud_ips').delete().eq('ip_address', ip_address).execute()
            
            return jsonify({'success': True, 'message': f'IP {ip_address} removed from fraud list'})
        except Exception as e:
            print(f"Remove fraud IP error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/admin/fraud-ips/clear-expired', methods=['POST'])
    @verify_admin_token
    def clear_expired_fraud_ips():
        """Clear expired fraud IPs (cooldown passed)"""
        try:
            supabase = get_supabase_client()
            
            now = datetime.utcnow().isoformat()
            
            # Delete IPs where cooldown has passed
            result = supabase.table('fraud_ips').delete().lt('cooldown_until', now).execute()
            
            deleted_count = len(result.data) if result.data else 0
            
            return jsonify({'success': True, 'deleted_count': deleted_count, 'message': f'Cleared {deleted_count} expired IPs'})
        except Exception as e:
            print(f"Clear expired fraud IPs error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    # ============================================
    # CONFIG MANAGEMENT ENDPOINTS
    # ============================================
    
    @app.route('/api/admin/config/verification-prices', methods=['GET'])
    @verify_admin_token
    def get_verification_prices():
        """Get verification prices configuration"""
        try:
            supabase = get_supabase_client()
            if not supabase:
                return jsonify({'error': 'Database not available'}), 500
            
            result = supabase.table('bot_config').select('config_value').eq('config_key', 'verification_prices').single().execute()
            
            if result.data:
                return jsonify({'prices': result.data['config_value']}), 200
            else:
                # Return default prices if not found
                return jsonify({'prices': {'gemini': 10, 'perplexity': 25, 'teacher': 120, 'spotify': 10}}), 200
        except Exception as e:
            print(f"Error getting verification prices: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/config/verification-prices', methods=['PUT'])
    @verify_admin_token
    def update_verification_prices():
        """Update verification prices configuration"""
        try:
            data = request.get_json()
            prices = data.get('prices', {})
            
            # Validate prices
            required_types = ['gemini', 'perplexity', 'teacher', 'spotify']
            for vtype in required_types:
                if vtype not in prices:
                    return jsonify({'error': f'Missing price for {vtype}'}), 400
                if not isinstance(prices[vtype], (int, float)) or prices[vtype] < 0:
                    return jsonify({'error': f'Invalid price for {vtype}'}), 400
            
            supabase = get_supabase_client()
            if not supabase:
                return jsonify({'error': 'Database not available'}), 500
            
            # Update or insert
            supabase.table('bot_config').upsert({
                'config_key': 'verification_prices',
                'config_value': prices
            }).execute()
            
            return jsonify({'message': 'Verification prices updated successfully', 'prices': prices}), 200
        except Exception as e:
            print(f"Error updating verification prices: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/config/shop-products', methods=['GET'])
    @verify_admin_token
    def get_shop_products():
        """Get shop products configuration"""
        try:
            supabase = get_supabase_client()
            if not supabase:
                return jsonify({'error': 'Database not available'}), 500
            
            result = supabase.table('bot_config').select('config_value').eq('config_key', 'shop_products').single().execute()
            
            if result.data:
                return jsonify({'products': result.data['config_value']}), 200
            else:
                # Return default products if not found
                return jsonify({'products': {}}), 200
        except Exception as e:
            print(f"Error getting shop products: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/config/shop-products', methods=['PUT'])
    @verify_admin_token
    def update_shop_products():
        """Update shop products configuration"""
        try:
            data = request.get_json()
            products = data.get('products', {})
            
            # Validate products structure
            for product_id, product_data in products.items():
                required_fields = ['name', 'price', 'stock', 'enabled']
                for field in required_fields:
                    if field not in product_data:
                        return jsonify({'error': f'Missing field {field} in product {product_id}'}), 400
            
            supabase = get_supabase_client()
            if not supabase:
                return jsonify({'error': 'Database not available'}), 500
            
            # Update or insert
            supabase.table('bot_config').upsert({
                'config_key': 'shop_products',
                'config_value': products
            }).execute()
            
            return jsonify({'message': 'Shop products updated successfully', 'products': products}), 200
        except Exception as e:
            print(f"Error updating shop products: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/config/shop-products/<product_id>', methods=['DELETE'])
    @verify_admin_token
    def delete_shop_product(product_id):
        """Delete a shop product"""
        try:
            supabase = get_supabase_client()
            if not supabase:
                return jsonify({'error': 'Database not available'}), 500
            
            # Get current products
            result = supabase.table('bot_config').select('config_value').eq('config_key', 'shop_products').single().execute()
            
            if result.data:
                products = result.data['config_value']
                if product_id in products:
                    del products[product_id]
                    
                    # Update
                    supabase.table('bot_config').update({
                        'config_value': products
                    }).eq('config_key', 'shop_products').execute()
                    
                    return jsonify({'message': f'Product {product_id} deleted successfully'}), 200
                else:
                    return jsonify({'error': 'Product not found'}), 404
            else:
                return jsonify({'error': 'Shop products config not found'}), 404
        except Exception as e:
            print(f"Error deleting shop product: {e}")
            return jsonify({'error': str(e)}), 500
    
    # ===== STATUS ANNOUNCEMENT ENDPOINTS =====
    
    @app.route('/api/status-announcement', methods=['GET'])
    def get_status_announcement():
        """Get active status announcement (public endpoint)"""
        try:
            supabase = get_supabase_client()
            if not supabase:
                return jsonify({'announcement': None}), 200
            
            # Get the most recent active announcement
            result = supabase.table('status_announcements').select('*').eq('is_active', True).order('created_at', desc=True).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return jsonify({'announcement': result.data[0]}), 200
            else:
                return jsonify({'announcement': None}), 200
        except Exception as e:
            print(f"Error getting status announcement: {e}")
            return jsonify({'announcement': None}), 200
    
    @app.route('/api/admin/status-announcement', methods=['GET'])
    @verify_admin_token
    def get_admin_status_announcement():
        """Get all status announcements (admin only)"""
        try:
            supabase = get_supabase_client()
            if not supabase:
                return jsonify({'error': 'Database not available'}), 500
            
            result = supabase.table('status_announcements').select('*').order('created_at', desc=True).execute()
            
            return jsonify({'announcements': result.data or []}), 200
        except Exception as e:
            print(f"Error getting announcements: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/status-announcement', methods=['POST'])
    @verify_admin_token
    def create_status_announcement():
        """Create or update status announcement (admin only)"""
        try:
            data = request.get_json()
            message = data.get('message', '').strip()
            announcement_type = data.get('type', 'info')
            is_active = data.get('is_active', True)
            
            if not message:
                return jsonify({'error': 'Message is required'}), 400
            
            if announcement_type not in ['info', 'warning', 'success', 'error']:
                return jsonify({'error': 'Invalid type. Must be: info, warning, success, or error'}), 400
            
            supabase = get_supabase_client()
            if not supabase:
                return jsonify({'error': 'Database not available'}), 500
            
            # If setting this announcement as active, deactivate all others
            if is_active:
                supabase.table('status_announcements').update({'is_active': False}).eq('is_active', True).execute()
            
            # Create new announcement
            result = supabase.table('status_announcements').insert({
                'message': message,
                'type': announcement_type,
                'is_active': is_active,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }).execute()
            
            return jsonify({'message': 'Announcement created successfully', 'announcement': result.data[0] if result.data else None}), 201
        except Exception as e:
            print(f"Error creating announcement: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/status-announcement/<int:announcement_id>', methods=['PUT'])
    @verify_admin_token
    def update_status_announcement(announcement_id):
        """Update status announcement (admin only)"""
        try:
            data = request.get_json()
            
            update_data = {}
            
            if 'message' in data:
                message = data['message'].strip()
                if not message:
                    return jsonify({'error': 'Message cannot be empty'}), 400
                update_data['message'] = message
            
            if 'type' in data:
                announcement_type = data['type']
                if announcement_type not in ['info', 'warning', 'success', 'error']:
                    return jsonify({'error': 'Invalid type'}), 400
                update_data['type'] = announcement_type
            
            if 'is_active' in data:
                is_active = data['is_active']
                update_data['is_active'] = is_active
                
                # If activating this announcement, deactivate all others
                supabase = get_supabase_client()
                if is_active:
                    supabase.table('status_announcements').update({'is_active': False}).eq('is_active', True).execute()
            
            if not update_data:
                return jsonify({'error': 'No fields to update'}), 400
            
            update_data['updated_at'] = datetime.utcnow().isoformat()
            
            supabase = get_supabase_client()
            if not supabase:
                return jsonify({'error': 'Database not available'}), 500
            
            result = supabase.table('status_announcements').update(update_data).eq('id', announcement_id).execute()
            
            if not result.data:
                return jsonify({'error': 'Announcement not found'}), 404
            
            return jsonify({'message': 'Announcement updated successfully', 'announcement': result.data[0]}), 200
        except Exception as e:
            print(f"Error updating announcement: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/status-announcement/<int:announcement_id>', methods=['DELETE'])
    @verify_admin_token
    def delete_status_announcement(announcement_id):
        """Delete status announcement (admin only)"""
        try:
            supabase = get_supabase_client()
            if not supabase:
                return jsonify({'error': 'Database not available'}), 500
            
            result = supabase.table('status_announcements').delete().eq('id', announcement_id).execute()
            
            if not result.data:
                return jsonify({'error': 'Announcement not found'}), 404
            
            return jsonify({'message': 'Announcement deleted successfully'}), 200
        except Exception as e:
            print(f"Error deleting announcement: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/admin')
    def fake_admin_honeypot():
        """Fake admin page honeypot to catch attackers"""
        try:
            # Try multiple paths for fake-admin.html
            import os
            possible_paths = [
                'fake-admin.html',  # Root directory
                '../fake-admin.html',  # Parent directory
                os.path.join(os.path.dirname(__file__), '..', 'fake-admin.html')  # Relative to api folder
            ]
            
            html_content = None
            for path in possible_paths:
                try:
                    if os.path.exists(path):
                        with open(path, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        print(f"✅ Loaded fake-admin.html from: {path}")
                        break
                except Exception as e:
                    continue
            
            if html_content:
                return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
            else:
                print(f"❌ fake-admin.html not found in any path")
                # Return inline HTML as fallback
                return """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
    <style>
        body { font-family: Arial; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); max-width: 400px; }
        h1 { text-align: center; color: #333; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #e0e0e0; border-radius: 5px; }
        button { width: 100%; padding: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
        .troll { display: none; text-align: center; }
        .troll.active { display: block; }
    </style>
</head>
<body>
    <div class="container" id="loginForm">
        <h1>🔐 Admin Panel</h1>
        <form onsubmit="event.preventDefault(); if(document.getElementById('user').value==='admin' && document.getElementById('pass').value==='admin') { document.getElementById('loginForm').style.display='none'; document.getElementById('trollPage').classList.add('active'); } else { alert('Invalid credentials!'); }">
            <input type="text" id="user" placeholder="Username" required>
            <input type="password" id="pass" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
    <div class="container troll" id="trollPage">
        <h1 style="color: #e74c3c;">🎉 TROLLED! 🎉</h1>
        <p style="font-size: 24px;">You've been caught! 😂</p>
        <p style="color: #666; margin-top: 20px;">Your attempt has been logged.</p>
    </div>
</body>
</html>
                """, 200, {'Content-Type': 'text/html; charset=utf-8'}
        except Exception as e:
            print(f"Error serving fake admin page: {e}")
            import traceback
            traceback.print_exc()
            return "Admin page not found", 404
    
    @app.route('/api/log-honeypot', methods=['POST'])
    def log_honeypot_attempt():
        """Log honeypot login attempts to database"""
        try:
            data = request.json
            username = data.get('username', '')
            password = data.get('password', '')
            success = data.get('success', False)
            timestamp = data.get('timestamp', '')
            user_agent = data.get('userAgent', '')
            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
            
            # Log to console
            print(f"🍯 HONEYPOT TRIGGERED!")
            print(f"   IP: {ip_address}")
            print(f"   Username: {username}")
            print(f"   Password: {password}")
            print(f"   Success: {success}")
            print(f"   Time: {timestamp}")
            print(f"   User-Agent: {user_agent}")
            
            # Optional: Save to database
            supabase = get_supabase_client()
            if supabase:
                try:
                    supabase.table('honeypot_logs').insert({
                        'ip_address': ip_address,
                        'username': username,
                        'password': password,
                        'success': success,
                        'timestamp': timestamp,
                        'user_agent': user_agent,
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }).execute()
                except Exception as db_error:
                    print(f"⚠️ Could not save to database (table may not exist): {db_error}")
            
            return jsonify({'success': True, 'message': 'Logged'}), 200
        except Exception as e:
            print(f"Error logging honeypot attempt: {e}")
            return jsonify({'error': str(e)}), 500