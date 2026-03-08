"""
Binance Auto Deposit System
Hỗ trợ 2 phương thức:
1. On-chain deposit (TRC20/BEP20/ERC20) - user gửi USDT trực tiếp vào ví Binance
2. Binance Pay internal transfer - user chuyển nội bộ Binance

Flow:
- Poll deposit history từ Binance API mỗi 30s
- Detect deposit mới → tìm user từ memo/txId
- Tự động cộng CASH cho user
"""

import os
import time
import hmac
import hashlib
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any, Tuple
from urllib.parse import urlencode


class BinanceAutoDeposit:
    """
    Auto deposit system using Binance Spot API
    Monitors deposit history and auto-credits users
    """
    
    def __init__(self):
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        self.base_url = "https://api.binance.com"
        
        # Deposit addresses (from env)
        self.trc20_address = os.getenv('TRON_WALLET_ADDRESS', '')
        self.bep20_address = os.getenv('BSC_WALLET_ADDRESS', '')
        self.erc20_address = os.getenv('ETH_WALLET_ADDRESS', '')
        
        # Exchange rate: 1 USDT = X CASH
        self.usdt_to_cash_rate = float(os.getenv('USDT_TO_CASH_RATE', '25'))
        
        # Track processed transactions to avoid duplicates
        self.processed_txids = set()
        
        # Last check timestamp (milliseconds) - only check last 10 minutes
        self.last_check_time = int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp() * 1000)
        
        print(f"✅ BinanceAutoDeposit initialized")
        print(f"   TRC20: {self.trc20_address[:10]}..." if self.trc20_address else "   TRC20: Not set")
        print(f"   BEP20: {self.bep20_address[:10]}..." if self.bep20_address else "   BEP20: Not set")
        print(f"   Rate: 1 USDT = {self.usdt_to_cash_rate} CASH")
    
    def _get_server_time(self) -> int:
        """Get Binance server time to avoid timestamp issues"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/time", timeout=5)
            if response.status_code == 200:
                return response.json()['serverTime']
        except:
            pass
        return int(time.time() * 1000)
    
    def _create_signature(self, params: dict) -> str:
        """Create HMAC SHA256 signature for API request"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(self, endpoint: str, params: dict = None) -> Optional[Any]:
        """Make authenticated request to Binance API"""
        if not self.api_key or not self.api_secret:
            print("❌ Binance API credentials not configured")
            return None
        
        try:
            if params is None:
                params = {}
            
            params['timestamp'] = self._get_server_time()
            params['signature'] = self._create_signature(params)
            
            headers = {'X-MBX-APIKEY': self.api_key}
            
            response = requests.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Binance API error: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Binance API request failed: {e}")
            return None
    
    def get_deposit_history(self, coin: str = 'USDT', limit: int = 50) -> List[Dict]:
        """
        Get deposit history from Binance
        Returns list of deposits sorted by time DESC
        """
        params = {
            'coin': coin,
            'limit': limit,
            'startTime': self.last_check_time
        }
        
        result = self._make_request('/sapi/v1/capital/deposit/hisrec', params)
        
        if result is None:
            return []
        
        return result
    
    def get_pay_transactions(self, limit: int = 50) -> List[Dict]:
        """
        Get Binance Pay internal transfer history
        This catches transfers from other Binance users via Pay
        Only returns transactions from last 10 minutes
        """
        # Only get transactions from last 10 minutes
        ten_min_ago = int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp() * 1000)
        
        params = {
            'limit': limit,
            'startTime': ten_min_ago
        }
        
        result = self._make_request('/sapi/v1/pay/transactions', params)
        
        if result is None:
            return []
        
        # API returns {"code": "000000", "data": [...]}
        if isinstance(result, dict):
            if result.get('code') == '000000':
                transactions = result.get('data', [])
                # Additional filter: only USDT with positive amount (incoming)
                filtered = [
                    tx for tx in transactions 
                    if tx.get('currency') == 'USDT' and float(tx.get('amount', 0)) > 0
                ]
                return filtered
        
        return []
    
    def process_pay_transaction(self, tx: Dict) -> Tuple[bool, str]:
        """
        Process a single Binance Pay transaction
        """
        order_id = tx.get('orderId', '')
        amount = float(tx.get('amount', 0))
        currency = tx.get('currency', 'USDT')
        note = tx.get('note', '')  # User's note/memo
        tx_time = tx.get('transactionTime', 0)
        
        # Skip if already processed (memory cache)
        if order_id in self.processed_txids:
            return (False, f"Already processed (cache): {order_id}")
        
        # Skip if already in database (persistent check)
        if self._is_transaction_processed(order_id):
            self.processed_txids.add(order_id)  # Add to cache
            return (False, f"Already processed (db): {order_id}")
        
        # Skip if not USDT
        if currency != 'USDT':
            return (False, f"Not USDT: {currency}")
        
        # Skip if amount is 0
        if amount <= 0:
            return (False, f"Invalid amount: {amount}")
        
        print(f"💳 Processing Pay transaction: {order_id}")
        print(f"   Amount: {amount} {currency}")
        print(f"   Note: {note}")
        
        # Try to find telegram_id from note
        telegram_id = None
        if note:
            import re
            match = re.match(r'^[Bb][Nn](\d+)$', note.strip())
            if match:
                telegram_id = match.group(1)
            elif note.strip().isdigit() and len(note.strip()) >= 6:
                telegram_id = note.strip()
        
        # If no telegram_id in note, try pending_user_deposits
        if not telegram_id:
            telegram_id = self._find_pending_user_deposit(amount, order_id)
        
        if not telegram_id:
            self._save_pending_pay_transaction(tx)
            self.processed_txids.add(order_id)
            return (False, f"No telegram_id found, saved to pending")
        
        # Calculate CASH amount
        cash_amount = int(amount * self.usdt_to_cash_rate)
        
        print(f"   Telegram ID: {telegram_id}")
        print(f"   CASH to add: {cash_amount}")
        
        # Add cash to user
        success = self._add_cash_to_user(telegram_id, cash_amount, order_id, amount, 'BINANCE_PAY')
        
        if success:
            self.processed_txids.add(order_id)
            self._notify_user(telegram_id, amount, cash_amount, order_id, 'Binance Pay')
            return (True, f"Added {cash_amount} CASH to user {telegram_id}")
        else:
            return (False, f"Failed to add cash to user {telegram_id}")
    
    def _is_transaction_processed(self, transaction_id: str) -> bool:
        """Check if transaction already exists in database (prevent duplicates)"""
        try:
            from .supabase_client import get_supabase_client
            client = get_supabase_client()
            if not client:
                return False
            
            result = client.table('binance_deposits').select('id, status').eq('transaction_id', transaction_id).execute()
            
            if result.data and len(result.data) > 0:
                status = result.data[0].get('status', '')
                # Consider processed if status is 'completed' or 'processing'
                if status in ['completed', 'processing']:
                    print(f"⚠️ Transaction {transaction_id} already processed (status: {status})")
                    return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Error checking transaction: {e}")
            return False
    
    def _save_pending_pay_transaction(self, tx: Dict):
        """Save Pay transaction to pending for manual processing"""
        try:
            from .supabase_client import get_supabase_client
            client = get_supabase_client()
            if not client:
                return
            
            order_id = tx.get('orderId', '')
            
            # Check if already exists
            existing = client.table('binance_deposits').select('id').eq('transaction_id', order_id).execute()
            if existing.data:
                return
            
            payer_info = tx.get('payerInfo', {})
            payer_name = payer_info.get('name', 'Unknown')
            
            data = {
                'transaction_id': order_id,
                'telegram_id': None,
                'amount': float(tx.get('amount', 0)),
                'currency': 'USDT',
                'content': f"Binance Pay from {payer_name} | Note: {tx.get('note', '')}",
                'status': 'pending_manual',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            client.table('binance_deposits').insert(data).execute()
            print(f"📝 Saved pending Pay transaction: {order_id}")
            
        except Exception as e:
            print(f"❌ Error saving pending Pay transaction: {e}")

    
    def parse_telegram_id_from_deposit(self, deposit: Dict) -> Optional[str]:
        """
        Parse telegram_id from deposit info
        
        Methods to identify user:
        1. Memo/Tag field (if user includes BN+telegram_id)
        2. Address tag for networks that support it
        3. Check pending_user_deposits table (user pre-registered their deposit)
        
        Returns telegram_id if found, None otherwise
        """
        import re
        
        # Check for tag/memo field
        tag = deposit.get('tag', '') or deposit.get('addressTag', '') or ''
        
        if tag:
            # Try to parse BN+telegram_id format
            match = re.match(r'^[Bb][Nn](\d+)$', tag.strip())
            if match:
                return match.group(1)
            
            # Try pure numeric (telegram_id directly)
            if tag.strip().isdigit() and len(tag.strip()) >= 6:
                return tag.strip()
        
        # Check if user pre-registered this deposit amount
        # (User sends /napusdt <amount> before depositing)
        amount = float(deposit.get('amount', 0))
        tx_id = deposit.get('txId', '')
        
        telegram_id = self._find_pending_user_deposit(amount, tx_id)
        if telegram_id:
            return telegram_id
        
        return None
    
    def _find_pending_user_deposit(self, amount: float, tx_id: str) -> Optional[str]:
        """
        Find user who pre-registered a deposit with matching amount
        Used when user can't include memo (e.g., internal transfer)
        """
        try:
            from .supabase_client import get_supabase_client
            client = get_supabase_client()
            if not client:
                return None
            
            # Look for pending user deposits with matching amount (within 5 minutes)
            from datetime import datetime, timezone, timedelta
            five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
            
            result = client.table('pending_user_deposits').select('*').eq('amount', amount).eq('status', 'waiting').gte('created_at', five_min_ago).order('created_at', desc=True).limit(1).execute()
            
            if result.data:
                pending = result.data[0]
                telegram_id = pending.get('telegram_id')
                
                # Mark as matched
                client.table('pending_user_deposits').update({
                    'status': 'matched',
                    'matched_tx_id': tx_id,
                    'matched_at': datetime.now(timezone.utc).isoformat()
                }).eq('id', pending['id']).execute()
                
                print(f"✅ Matched pending deposit: {amount} USDT -> user {telegram_id}")
                return telegram_id
            
            return None
            
        except Exception as e:
            # Table might not exist yet, that's ok
            print(f"⚠️ Could not check pending_user_deposits: {e}")
            return None
    
    def process_deposit(self, deposit: Dict) -> Tuple[bool, str]:
        """
        Process a single deposit
        
        Returns:
            (success, message)
        """
        tx_id = deposit.get('txId', deposit.get('id', ''))
        amount = float(deposit.get('amount', 0))
        network = deposit.get('network', 'UNKNOWN')
        status = deposit.get('status', 0)
        insert_time = deposit.get('insertTime', 0)
        
        # Skip if already processed (memory cache)
        if tx_id in self.processed_txids:
            return (False, f"Already processed (cache): {tx_id}")
        
        # Skip if already in database (persistent check)
        if self._is_transaction_processed(tx_id):
            self.processed_txids.add(tx_id)  # Add to cache
            return (False, f"Already processed (db): {tx_id}")
        
        # Skip if not successful (status 1 = success)
        if status != 1:
            return (False, f"Deposit not confirmed: status={status}")
        
        # Skip if amount is 0
        if amount <= 0:
            return (False, f"Invalid amount: {amount}")
        
        print(f"💰 Processing deposit: {tx_id[:30]}...")
        print(f"   Amount: {amount} USDT")
        print(f"   Network: {network}")
        
        # Try to find telegram_id
        telegram_id = self.parse_telegram_id_from_deposit(deposit)
        
        if not telegram_id:
            # Cannot auto-process without telegram_id
            # Save to pending_deposits for manual processing
            self._save_pending_deposit(deposit)
            self.processed_txids.add(tx_id)
            return (False, f"No telegram_id found, saved to pending")
        
        # Calculate CASH amount
        cash_amount = int(amount * self.usdt_to_cash_rate)
        
        print(f"   Telegram ID: {telegram_id}")
        print(f"   CASH to add: {cash_amount}")
        
        # Add cash to user
        success = self._add_cash_to_user(telegram_id, cash_amount, tx_id, amount, network)
        
        if success:
            self.processed_txids.add(tx_id)
            # Send notification to user
            self._notify_user(telegram_id, amount, cash_amount, tx_id, network)
            return (True, f"Added {cash_amount} CASH to user {telegram_id}")
        else:
            return (False, f"Failed to add cash to user {telegram_id}")
    
    def _save_pending_deposit(self, deposit: Dict):
        """Save deposit to pending_deposits table for manual processing"""
        try:
            from .supabase_client import get_supabase_client
            client = get_supabase_client()
            if not client:
                return
            
            tx_id = deposit.get('txId', deposit.get('id', ''))
            
            # Check if already exists
            existing = client.table('binance_deposits').select('id').eq('transaction_id', tx_id).execute()
            if existing.data:
                return
            
            data = {
                'transaction_id': tx_id,
                'telegram_id': None,  # Unknown
                'amount': float(deposit.get('amount', 0)),
                'currency': 'USDT',
                'content': f"Network: {deposit.get('network', 'UNKNOWN')}",
                'status': 'pending_manual',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            client.table('binance_deposits').insert(data).execute()
            print(f"📝 Saved pending deposit: {tx_id[:30]}...")
            
        except Exception as e:
            print(f"❌ Error saving pending deposit: {e}")
    
    def _add_cash_to_user(self, telegram_id: str, cash_amount: int, tx_id: str, usdt_amount: float, network: str) -> bool:
        """Add CASH to user account"""
        try:
            from .supabase_client import get_supabase_client
            client = get_supabase_client()
            if not client:
                return False
            
            # Get user
            user_result = client.table('users').select('id, cash').eq('telegram_id', str(telegram_id)).execute()
            if not user_result.data:
                print(f"❌ User not found: {telegram_id}")
                return False
            
            user = user_result.data[0]
            user_id = user['id']
            current_cash = user.get('cash', 0) or 0
            new_cash = current_cash + cash_amount
            
            # Update user cash
            client.table('users').update({
                'cash': new_cash,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', user_id).execute()
            
            # Create transaction record
            client.table('transactions').insert({
                'user_id': user_id,
                'type': 'binance_auto_deposit',
                'amount': cash_amount,
                'coins': 0,
                'description': f'Auto deposit: {usdt_amount} USDT via {network} | TxID: {tx_id[:30]}',
                'status': 'completed',
                'created_at': datetime.now(timezone.utc).isoformat()
            }).execute()
            
            # Record in binance_deposits
            client.table('binance_deposits').insert({
                'transaction_id': tx_id,
                'telegram_id': str(telegram_id),
                'amount': cash_amount,
                'currency': 'CASH',
                'content': f'{usdt_amount} USDT via {network}',
                'status': 'completed',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'processed_at': datetime.now(timezone.utc).isoformat()
            }).execute()
            
            print(f"✅ Added {cash_amount} CASH to user {telegram_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding cash: {e}")
            return False
    
    def _notify_user(self, telegram_id: str, usdt_amount: float, cash_amount: int, tx_id: str, network: str):
        """Send notification to user about successful deposit"""
        try:
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            if not bot_token:
                return
            
            # Get Vietnam time
            vietnam_tz = timezone(timedelta(hours=7))
            vietnam_time = datetime.now(vietnam_tz)
            timestamp = vietnam_time.strftime('%d/%m/%Y %H:%M:%S')
            
            message = f"""✅ NẠP TIỀN THÀNH CÔNG!

💰 Số tiền: {usdt_amount} USDT
💵 Nhận được: {cash_amount:,} CASH
🔗 Network: {network}
📝 TxID: {tx_id[:30]}...
⏰ Thời gian: {timestamp}

💱 Tỷ giá: 1 USDT = {int(self.usdt_to_cash_rate)} CASH

Cảm ơn bạn đã sử dụng dịch vụ!"""
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            requests.post(url, json={
                'chat_id': telegram_id,
                'text': message,
                'disable_web_page_preview': True
            }, timeout=10)
            
            print(f"📤 Sent notification to user {telegram_id}")
            
        except Exception as e:
            print(f"⚠️ Failed to send notification: {e}")
    
    def check_and_process_deposits(self) -> Dict:
        """
        Main function: Check for new deposits and process them
        Should be called periodically (e.g., every 30 seconds)
        
        Checks BOTH:
        1. On-chain deposits (TRC20/BEP20/ERC20)
        2. Binance Pay internal transfers
        
        Returns:
            {
                'checked': int,
                'processed': int,
                'pending': int,
                'errors': int
            }
        """
        result = {
            'checked': 0,
            'processed': 0,
            'pending': 0,
            'errors': 0
        }
        
        print(f"🔍 Checking Binance deposits...")
        
        # 1. Check on-chain deposits
        deposits = self.get_deposit_history()
        result['checked'] += len(deposits)
        
        if deposits:
            print(f"   Found {len(deposits)} on-chain deposits")
            for deposit in deposits:
                tx_id = deposit.get('txId', '')
                if tx_id in self.processed_txids:
                    continue
                
                success, message = self.process_deposit(deposit)
                
                if success:
                    result['processed'] += 1
                elif 'pending' in message.lower():
                    result['pending'] += 1
                else:
                    result['errors'] += 1
                
                print(f"   [ON-CHAIN] {tx_id[:20]}... -> {message}")
        
        # 2. Check Binance Pay internal transfers
        pay_transactions = self.get_pay_transactions()
        result['checked'] += len(pay_transactions)
        
        if pay_transactions:
            print(f"   Found {len(pay_transactions)} Pay transactions")
            for tx in pay_transactions:
                order_id = tx.get('orderId', '')
                if order_id in self.processed_txids:
                    continue
                
                success, message = self.process_pay_transaction(tx)
                
                if success:
                    result['processed'] += 1
                elif 'pending' in message.lower():
                    result['pending'] += 1
                else:
                    result['errors'] += 1
                
                print(f"   [PAY] {order_id[:20]}... -> {message}")
        
        # Update last check time
        self.last_check_time = self._get_server_time()
        
        print(f"✅ Deposit check complete: {result['processed']} processed, {result['pending']} pending")
        
        return result


# Global instance
_auto_deposit_instance = None

def get_auto_deposit() -> BinanceAutoDeposit:
    """Get or create global BinanceAutoDeposit instance"""
    global _auto_deposit_instance
    if _auto_deposit_instance is None:
        _auto_deposit_instance = BinanceAutoDeposit()
    return _auto_deposit_instance


def check_binance_deposits() -> Dict:
    """
    Convenience function to check and process deposits
    Can be called from cron job or webhook
    """
    auto_deposit = get_auto_deposit()
    return auto_deposit.check_and_process_deposits()


def get_deposit_addresses() -> Dict[str, str]:
    """Get all deposit addresses for display to users"""
    return {
        'TRC20': os.getenv('TRON_WALLET_ADDRESS', ''),
        'BEP20': os.getenv('BSC_WALLET_ADDRESS', ''),
        'ERC20': os.getenv('ETH_WALLET_ADDRESS', ''),
        'rate': os.getenv('USDT_TO_CASH_RATE', '25')
    }
