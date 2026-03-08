"""
Supabase Client - REST API với Publishable & Secret keys
"""

import os
import requests
from datetime import datetime
from typing import Optional, Dict, List, Any


class SupabaseRestClient:
    """Lightweight Supabase REST client supporting Publishable/Secret keys"""
    
    def __init__(self, url: str, key: str):
        self.url = url.rstrip('/')
        self.key = key.strip()
        self.headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    def table(self, table_name: str):
        """Return a table query builder"""
        return TableQueryBuilder(self, table_name)


class TableQueryBuilder:
    """Query builder for Supabase tables"""
    
    def __init__(self, client: SupabaseRestClient, table_name: str):
        self.client = client
        self.table_name = table_name
        self._select_cols = '*'
        self._filters = []
        self._order_by = None
        self._limit_val = None
        self._operation = 'select'
        self._insert_data = None
        self._update_data = None
    
    def select(self, columns: str = '*'):
        """Select columns"""
        self._select_cols = columns
        return self
    
    def eq(self, column: str, value):
        """Equal filter"""
        self._filters.append((column, 'eq', value))
        return self
    
    def gte(self, column: str, value):
        """Greater than or equal filter"""
        self._filters.append((column, 'gte', value))
        return self
    
    def lte(self, column: str, value):
        """Less than or equal filter"""
        self._filters.append((column, 'lte', value))
        return self
    
    def gt(self, column: str, value):
        """Greater than filter"""
        self._filters.append((column, 'gt', value))
        return self
    
    def lt(self, column: str, value):
        """Less than filter"""
        self._filters.append((column, 'lt', value))
        return self
    
    def neq(self, column: str, value):
        """Not equal filter"""
        self._filters.append((column, 'neq', value))
        return self
    
    def like(self, column: str, pattern):
        """LIKE filter (pattern matching)"""
        self._filters.append((column, 'like', pattern))
        return self
    
    def ilike(self, column: str, pattern):
        """ILIKE filter (case-insensitive pattern matching)"""
        self._filters.append((column, 'ilike', pattern))
        return self
    
    def is_(self, column: str, value):
        """IS filter (for null checks)"""
        self._filters.append((column, 'is', value))
        return self
    
    def in_(self, column: str, values):
        """IN filter (value in list)"""
        # Format: column=in.(value1,value2,value3)
        values_str = ','.join(str(v) for v in values)
        self._filters.append((column, 'in', f'({values_str})'))
        return self
    
    def order(self, column: str, desc: bool = False):
        """Order by column"""
        direction = 'desc' if desc else 'asc'
        self._order_by = f'{column}.{direction}'
        return self
    
    def limit(self, count: int):
        """Limit results"""
        self._limit_val = count
        return self
    
    def execute(self):
        """Execute the query"""
        if self._operation == 'insert':
            return self._execute_insert()
        elif self._operation == 'update':
            return self._execute_update()
        else:
            return self._execute_select()
    
    def _execute_select(self):
        """Execute select operation"""
        url = f"{self.client.url}/rest/v1/{self.table_name}"
        params = {'select': self._select_cols}
        
        # Add filters
        for col, op, val in self._filters:
            params[col] = f'{op}.{val}'
        
        # Add order
        if self._order_by:
            params['order'] = self._order_by
        
        # Add limit
        if self._limit_val:
            params['limit'] = self._limit_val
        
        try:
            response = requests.get(url, headers=self.client.headers, params=params, timeout=10)
            response.raise_for_status()
            return QueryResponse(response.json())
        except Exception as e:
            print(f"❌ Query error: {e}")
            return QueryResponse([])
    
    def insert(self, data: Dict):
        """Insert data - returns self for chaining, call execute() to run"""
        self._insert_data = data
        self._operation = 'insert'
        return self
    
    def update(self, data: Dict):
        """Update data - returns self for chaining, call execute() to run"""
        self._update_data = data
        self._operation = 'update'
        return self
    
    def _execute_insert(self):
        """Execute insert operation"""
        url = f"{self.client.url}/rest/v1/{self.table_name}"
        try:
            response = requests.post(url, headers=self.client.headers, json=self._insert_data, timeout=10)
            response.raise_for_status()
            return QueryResponse(response.json())
        except requests.exceptions.HTTPError as e:
            print(f"❌ Insert HTTP error: {e}")
            print(f"❌ Response status: {response.status_code}")
            print(f"❌ Response text: {response.text[:500]}")
            return QueryResponse([])
        except Exception as e:
            print(f"❌ Insert error: {e}")
            return QueryResponse([])
    
    def _execute_update(self):
        """Execute update operation"""
        url = f"{self.client.url}/rest/v1/{self.table_name}"
        params = {}
        
        # Add filters
        for col, op, val in self._filters:
            params[col] = f'{op}.{val}'
        
        try:
            response = requests.patch(url, headers=self.client.headers, params=params, json=self._update_data, timeout=10)
            response.raise_for_status()
            return QueryResponse(response.json())
        except requests.exceptions.HTTPError as e:
            print(f"❌ Update HTTP error: {e}")
            print(f"❌ Response status: {response.status_code}")
            print(f"❌ Response text: {response.text[:500]}")
            print(f"❌ URL: {response.url}")
            return QueryResponse([])
        except Exception as e:
            print(f"❌ Update error: {e}")
            return QueryResponse([])


class QueryResponse:
    """Response wrapper"""
    
    def __init__(self, data: List[Dict]):
        self.data = data if isinstance(data, list) else [data] if data else []


# Global client instance
_client: Optional[SupabaseRestClient] = None

def get_client() -> Optional[SupabaseRestClient]:
    """Get or create Supabase REST client"""
    global _client
    if _client is None:
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        if not url or not key:
            print(f"❌ Supabase credentials not found! URL: {bool(url)}, KEY: {bool(key)}")
            return None
        try:
            _client = SupabaseRestClient(url, key)
            print(f"✅ Supabase REST client created successfully")
        except Exception as e:
            print(f"❌ Error creating Supabase client: {e}")
            return None
    return _client


# Wrapper functions to maintain compatibility with existing code
def get_supabase_client():
    """Compatibility wrapper"""
    try:
        return get_client()
    except Exception as e:
        print(f"❌ Error creating Supabase client: {e}")
        return None


def get_user_by_telegram_id(telegram_id):
    """Get user by telegram_id"""
    try:
        client = get_client()
        if not client:
            return None
        result = client.table('users').select('*').eq('telegram_id', str(telegram_id)).limit(1).execute()
        if result.data:
            print(f"✅ Found user in Supabase: {result.data[0]}")
            return result.data[0]
        print(f"❌ User {telegram_id} not found in Supabase")
        return None
    except Exception as e:
        print(f"❌ Error getting user: {e}")
        return None


def create_user(telegram_id, username, first_name, last_name):
    """Create new user"""
    try:
        client = get_client()
        if not client:
            return None
        print(f"👤 Creating user in Supabase: {telegram_id}")
        
        user_data = {
            'telegram_id': str(telegram_id),
            'username': username or 'user',
            'first_name': first_name or 'User',
            'last_name': last_name or '',
            'is_vip': False,
            'vip_expiry': None,
            'coins': 0,
            'cash': 0,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        result = client.table('users').insert(user_data).execute()
        if result.data:
            print(f"✅ User created in Supabase: {result.data[0]}")
            return result.data[0]
        return None
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return None


def update_user_coins(telegram_id, coins_change, transaction_type, description):
    """Update coins and create transaction"""
    try:
        client = get_client()
        if not client:
            return False
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            return False
        
        current_coins = user.get('coins', 0)
        new_coins = current_coins + coins_change
        
        # Update user
        client.table('users').update({
            'coins': new_coins,
            'updated_at': datetime.now().isoformat()
        }).eq('telegram_id', str(telegram_id)).execute()
        
        # Create transaction
        transaction_data = {
            'user_id': user['id'],
            'type': transaction_type,
            'amount': coins_change * 1000,
            'coins': coins_change,
            'description': description,
            'status': 'completed',
            'created_at': datetime.now().isoformat()
        }
        client.table('transactions').insert(transaction_data).execute()
        
        print(f"✅ Updated coins: {current_coins} -> {new_coins}")
        return True
    except Exception as e:
        print(f"❌ Error updating coins: {e}")
        return False


def add_coins_to_user(telegram_id, coins, transaction_info=""):
    """Add coins to user"""
    return update_user_coins(telegram_id, coins, 'deposit', transaction_info)


def get_user_wallets_by_telegram_id(telegram_id):
    """Get user wallets (cash, coins, user_id)"""
    try:
        client = get_client()
        if not client:
            return None
        result = client.table('users').select('id,coins,cash').eq('telegram_id', str(telegram_id)).limit(1).execute()
        if result.data:
            row = result.data[0]
            return int(row.get('cash', 0)), int(row.get('coins', 0)), row['id']
        return None
    except Exception as e:
        print(f"❌ Error getting wallets: {e}")
        return None


def adjust_user_cash_by_telegram_id(telegram_id, cash_delta, tx_type='cash_update', description=''):
    """Adjust cash for user"""
    try:
        client = get_client()
        if not client:
            return None
        wallets = get_user_wallets_by_telegram_id(telegram_id)
        if not wallets:
            return None
        
        cash, coins, user_id = wallets
        new_cash = cash + int(cash_delta)
        if new_cash < 0:
            return None
        
        # Update cash
        client.table('users').update({
            'cash': new_cash,
            'updated_at': datetime.now().isoformat()
        }).eq('id', user_id).execute()
        
        # Create transaction
        client.table('transactions').insert({
            'user_id': user_id,
            'type': tx_type,
            'amount': int(cash_delta),
            'coins': 0,
            'description': description or f'Nạp tiền: {cash_delta:,}đ',
            'status': 'completed',
            'created_at': datetime.now().isoformat()
        }).execute()
        
        return new_cash
    except Exception as e:
        print(f"❌ Error adjusting cash: {e}")
        return None


def get_all_users():
    """Get all users"""
    try:
        client = get_client()
        if not client:
            return []
        result = client.table('users').select('*').order('created_at', desc=True).execute()
        print(f"✅ Found {len(result.data)} users")
        return result.data
    except Exception as e:
        print(f"❌ Error getting users: {e}")
        return []


def check_user_exists(telegram_id):
    """Check if user exists"""
    return get_user_by_telegram_id(telegram_id) is not None


def get_verification_job_by_id(job_id):
    """Get verification job by job_id"""
    try:
        client = get_client()
        if not client:
            return None
        result = client.table('verification_jobs').select('*').eq('job_id', job_id).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error getting job: {e}")
        return None


def get_job_with_user(job_id):
    """Get job and user info"""
    try:
        client = get_client()
        if not client:
            return None, None
        result = client.table('verification_jobs').select('*').eq('job_id', job_id).limit(1).execute()
        if not result.data:
            return None, None
        
        job = result.data[0]
        telegram_id = job.get('telegram_id')
        if not telegram_id:
            return job, None
        
        user = get_user_by_telegram_id(telegram_id)
        return job, user
    except Exception as e:
        print(f"❌ Error getting job with user: {e}")
        return None, None


def create_verification_job(job_id, user_id, telegram_id, sheerid_url, verification_id=None, verification_type='sheerid', payment_method=None):
    """Create verification job"""
    try:
        client = get_client()
        if not client:
            return False
        job_data = {
            'job_id': job_id,
            'user_id': user_id,
            'telegram_id': str(telegram_id),
            'sheerid_url': sheerid_url,
            'verification_id': verification_id,
            'status': 'pending',
            'verification_type': verification_type
        }
        if payment_method:
            job_data['payment_method'] = payment_method
        
        result = client.table('verification_jobs').insert(job_data).execute()
        print(f"✅ Created job: {job_id}")
        return bool(result.data)
    except Exception as e:
        print(f"❌ Error creating job: {e}")
        return False


def update_verification_job_status(job_id, status, student_info=None, card_filename=None, upload_result=None, result_data=None, return_job_info=False, university=None):
    """Update verification job status"""
    try:
        client = get_client()
        if not client:
            return (False, None) if return_job_info else False
        
        current_job = get_verification_job_by_id(job_id)
        if not current_job:
            return (False, None) if return_job_info else False
        
        update_data = {
            'status': status,
            'updated_at': datetime.now().isoformat()
        }
        
        if university:
            update_data['university'] = university
        if result_data is not None:
            update_data['result'] = result_data
        elif student_info:
            update_data['student_info'] = student_info
        if card_filename:
            update_data['card_filename'] = card_filename
        if upload_result:
            update_data['upload_result'] = upload_result
        
        client.table('verification_jobs').update(update_data).eq('job_id', job_id).execute()
        print(f"✅ Updated job {job_id} to {status}")
        
        if return_job_info:
            return (True, current_job)
        return True
    except Exception as e:
        print(f"❌ Error updating job: {e}")
        return (False, None) if return_job_info else False


def get_verification_jobs_by_telegram_id(telegram_id):
    """Get all jobs for user"""
    try:
        client = get_client()
        if not client:
            return []
        result = client.table('verification_jobs').select('*').eq('telegram_id', str(telegram_id)).order('created_at', desc=True).execute()
        print(f"✅ Found {len(result.data)} jobs for user {telegram_id}")
        return result.data
    except Exception as e:
        print(f"❌ Error getting jobs: {e}")
        return []


# University fraud tracking functions
def get_university_fraud_status(university_id):
    """Get fraud status for university"""
    try:
        client = get_client()
        if not client:
            return None
        result = client.table('university_fraud_tracking').select('*').eq('university_id', str(university_id)).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error getting fraud status: {e}")
        return None


def is_university_blocked(university_id):
    """Check if university is blocked"""
    try:
        status = get_university_fraud_status(university_id)
        if status and status.get('is_blocked'):
            print(f"🚫 University {university_id} is BLOCKED")
            return True
        return False
    except Exception as e:
        print(f"❌ Error checking blocked status: {e}")
        return False


def record_university_fraud(university_id, university_name=None):
    """Record fraud for university"""
    try:
        client = get_client()
        if not client:
            return False, 0
        status = get_university_fraud_status(university_id)
        
        if status:
            new_consecutive = status.get('consecutive_fraud_count', 0) + 1
            new_total = status.get('total_fraud_count', 0) + 1
            is_blocked = new_consecutive >= 3
            
            update_data = {
                'consecutive_fraud_count': new_consecutive,
                'total_fraud_count': new_total,
                'last_fraud_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            if is_blocked and not status.get('is_blocked'):
                update_data['is_blocked'] = True
                update_data['blocked_at'] = datetime.now().isoformat()
                print(f"🚫 BLOCKING university {university_id}")
            
            client.table('university_fraud_tracking').update(update_data).eq('university_id', str(university_id)).execute()
            return is_blocked, new_consecutive
        else:
            insert_data = {
                'university_id': str(university_id),
                'university_name': university_name or '',
                'consecutive_fraud_count': 1,
                'total_fraud_count': 1,
                'is_blocked': False,
                'last_fraud_at': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            client.table('university_fraud_tracking').insert(insert_data).execute()
            return False, 1
    except Exception as e:
        print(f"❌ Error recording fraud: {e}")
        return False, 0


def record_university_success(university_id, university_name=None):
    """Record success for university"""
    try:
        client = get_client()
        if not client:
            return
        status = get_university_fraud_status(university_id)
        
        if status:
            update_data = {
                'consecutive_fraud_count': 0,
                'last_success_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            client.table('university_fraud_tracking').update(update_data).eq('university_id', str(university_id)).execute()
        else:
            insert_data = {
                'university_id': str(university_id),
                'university_name': university_name or '',
                'consecutive_fraud_count': 0,
                'total_fraud_count': 0,
                'is_blocked': False,
                'last_success_at': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            client.table('university_fraud_tracking').insert(insert_data).execute()
    except Exception as e:
        print(f"❌ Error recording success: {e}")


def get_blocked_universities():
    """Get list of blocked universities"""
    try:
        client = get_client()
        if not client:
            return []
        result = client.table('university_fraud_tracking').select('university_id,university_name,consecutive_fraud_count,blocked_at').eq('is_blocked', True).execute()
        blocked = [row['university_id'] for row in result.data]
        print(f"🚫 Blocked universities: {blocked}")
        return blocked
    except Exception as e:
        print(f"❌ Error getting blocked universities: {e}")
        return []


def unblock_university(university_id):
    """Unblock university"""
    try:
        client = get_client()
        if not client:
            return False
        update_data = {
            'is_blocked': False,
            'consecutive_fraud_count': 0,
            'blocked_at': None,
            'updated_at': datetime.now().isoformat()
        }
        client.table('university_fraud_tracking').update(update_data).eq('university_id', str(university_id)).execute()
        print(f"🔓 Unblocked university: {university_id}")
        return True
    except Exception as e:
        print(f"❌ Error unblocking university: {e}")
        return False