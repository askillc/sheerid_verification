"""
BSC RPC Client for querying USDT BEP20 transactions
Using Binance's free public RPC endpoint - NO API KEY NEEDED!

RPC Endpoint: https://bsc-dataseed.binance.org/
"""
import requests
from datetime import datetime

class BSCRPCClient:
    """Client for interacting with BSC via RPC (no API key needed)"""
    
    def __init__(self):
        """Initialize BSC RPC client"""
        # Binance's official public RPC endpoints
        self.rpc_urls = [
            "https://bsc-dataseed.binance.org/",
            "https://bsc-dataseed1.binance.org/",
            "https://bsc-dataseed2.binance.org/",
        ]
        self.current_rpc = 0
        
        # USDT Contract on BSC (BEP20)
        self.usdt_contract = "0x55d398326f99059fF775485246999027B3197955"
        
        # Transfer event signature
        self.transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        
        print("✅ BSC RPC Client initialized (FREE - no API key needed)")
    
    def _rpc_call(self, method, params):
        """Make RPC call to BSC node"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        # Try each RPC endpoint
        for i in range(len(self.rpc_urls)):
            rpc_url = self.rpc_urls[self.current_rpc]
            try:
                response = requests.post(rpc_url, json=payload, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'result' in data:
                        return data['result']
                    elif 'error' in data:
                        print(f"❌ RPC error: {data['error']}")
                        return None
            except Exception as e:
                print(f"⚠️ RPC endpoint {rpc_url} failed: {e}")
                # Try next endpoint
                self.current_rpc = (self.current_rpc + 1) % len(self.rpc_urls)
                continue
        
        return None
    
    def get_transaction_by_hash(self, tx_hash):
        """
        Get transaction details by hash using RPC
        
        Args:
            tx_hash: Transaction hash (0x...)
        
        Returns:
            dict: Transaction details or None if not found
        """
        try:
            print(f"🔍 Querying BSC RPC: {tx_hash}")
            
            # Ensure hash starts with 0x
            if not tx_hash.startswith('0x'):
                tx_hash = '0x' + tx_hash
            
            # Step 1: Get transaction
            tx = self._rpc_call('eth_getTransactionByHash', [tx_hash])
            if not tx:
                print(f"❌ Transaction not found: {tx_hash}")
                return None
            
            # Step 2: Get transaction receipt
            receipt = self._rpc_call('eth_getTransactionReceipt', [tx_hash])
            if not receipt:
                print(f"❌ Receipt not found: {tx_hash}")
                return None
            
            # Check if transaction was successful
            status = receipt.get('status', '0x0')
            if status != '0x1':
                print(f"❌ Transaction failed or pending")
                return None
            
            # Step 3: Parse logs for USDT transfer
            logs = receipt.get('logs', [])
            usdt_transfer = None
            
            for log in logs:
                # Check if this is USDT contract
                if log.get('address', '').lower() != self.usdt_contract.lower():
                    continue
                
                # Check if this is Transfer event
                topics = log.get('topics', [])
                if len(topics) < 3 or topics[0] != self.transfer_topic:
                    continue
                
                # Parse Transfer event
                from_address = '0x' + topics[1][-40:]
                to_address = '0x' + topics[2][-40:]
                amount_hex = log.get('data', '0x0')
                
                # Convert hex to decimal and adjust for 18 decimals
                amount_wei = int(amount_hex, 16)
                amount_usdt = amount_wei / (10 ** 18)
                
                usdt_transfer = {
                    'from': from_address,
                    'to': to_address,
                    'amount': amount_usdt
                }
                break
            
            if not usdt_transfer:
                print(f"❌ No USDT transfer found in transaction")
                return None
            
            # Step 4: Get block timestamp
            block_number = receipt.get('blockNumber', '0x0')
            block = self._rpc_call('eth_getBlockByNumber', [block_number, False])
            
            timestamp = 0
            if block:
                timestamp = int(block.get('timestamp', '0x0'), 16) * 1000  # Convert to ms
            
            # Build result
            result = {
                'transaction_id': tx_hash,
                'amount': usdt_transfer['amount'],
                'currency': 'USDT',
                'content': '',  # BSC doesn't have memo
                'to_address': usdt_transfer['to'],
                'from_address': usdt_transfer['from'],
                'status': 'SUCCESS',
                'timestamp': timestamp,
                'confirmed': True,
                'block_number': int(block_number, 16)
            }
            
            print(f"✅ Retrieved BSC transaction:")
            print(f"   TX: {result['transaction_id']}")
            print(f"   Amount: {result['amount']} USDT")
            print(f"   From: {result['from_address']}")
            print(f"   To: {result['to_address']}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error querying BSC RPC: {e}")
            import traceback
            traceback.print_exc()
            return None
