"""
Etherscan API Client for querying USDT ERC20 transactions on Ethereum

API Documentation: https://docs.etherscan.io/
"""
import os
import requests
from datetime import datetime

class EtherscanAPIClient:
    """Client for interacting with Etherscan API"""
    
    def __init__(self):
        """Initialize Etherscan API client"""
        self.base_url = "https://api.etherscan.io/v2/api"  # V2 API
        self.api_key = os.getenv('ETHERSCAN_API_KEY', '')
        
        # USDT Contract on Ethereum (ERC20)
        self.usdt_contract = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
        
        if self.api_key:
            print("✅ EtherscanAPIClient initialized with API key (V2)")
        else:
            print("⚠️ EtherscanAPIClient initialized without API key")
            print("⚠️ Etherscan API requires an API key from https://etherscan.io/myapikey")
    
    def get_transaction_by_hash(self, tx_hash):
        """
        Get transaction details by hash
        
        Args:
            tx_hash: Transaction hash (0x...)
        
        Returns:
            dict: Transaction details or None if not found
        """
        try:
            print(f"🔍 Querying Etherscan transaction: {tx_hash}")
            
            # Ensure hash starts with 0x
            if not tx_hash.startswith('0x'):
                tx_hash = '0x' + tx_hash
            
            # Step 1: Get basic transaction info (V2 API format)
            params = {
                'chainid': '1',  # Ethereum mainnet
                'module': 'proxy',
                'action': 'eth_getTransactionByHash',
                'txhash': tx_hash,
                'apikey': self.api_key
            }
            
            print(f"🔍 Making Etherscan API V2 request")
            print(f"Parameters: {params}")
            
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Etherscan API error: {response.status_code}")
                return None
            
            data = response.json()
            
            if not data.get('result'):
                print(f"❌ Transaction not found: {tx_hash}")
                return None
            
            tx_data = data['result']
            
            # Check if tx_data is a string (error message)
            if isinstance(tx_data, str):
                print(f"❌ API returned error: {tx_data[:100]}")
                return None
            
            # Step 2: Get transaction receipt for status
            receipt_params = {
                'chainid': '1',  # Ethereum mainnet
                'module': 'proxy',
                'action': 'eth_getTransactionReceipt',
                'txhash': tx_hash,
                'apikey': self.api_key
            }
            
            receipt_response = requests.get(self.base_url, params=receipt_params, timeout=10)
            receipt_data = receipt_response.json()
            receipt = receipt_data.get('result')
            
            # Handle case where receipt is None, string, or invalid
            if not receipt or isinstance(receipt, str):
                if isinstance(receipt, str):
                    print(f"⚠️ Receipt returned as string: {receipt[:100]}")
                else:
                    print(f"⚠️ Receipt is None or empty")
                
                # Try to get logs using getLogs API instead
                print(f"🔄 Attempting to fetch logs using getLogs API...")
                logs_params = {
                    'chainid': '1',  # Ethereum mainnet
                    'module': 'logs',
                    'action': 'getLogs',
                    'fromBlock': tx_data.get('blockNumber', '0x0'),
                    'toBlock': tx_data.get('blockNumber', '0x0'),
                    'address': self.usdt_contract,
                    'topic0': '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef',
                    'apikey': self.api_key
                }
                logs_response = requests.get(self.base_url, params=logs_params, timeout=10)
                logs_data = logs_response.json()
                logs = logs_data.get('result', [])
                print(f"📋 Retrieved {len(logs)} logs using getLogs API")
                is_success = True  # Assume success if we got logs
            else:
                # Check if transaction is successful
                status = receipt.get('status', '0x0')
                is_success = status == '0x1'
                
                if not is_success:
                    print(f"❌ Transaction failed or pending")
                    return None
                
                # Step 3: Parse USDT transfer from logs
                logs = receipt.get('logs', [])
            usdt_transfer = None
            
            for log in logs:
                # Filter by transaction hash if using getLogs API
                if isinstance(receipt, str) and log.get('transactionHash', '').lower() != tx_hash.lower():
                    continue
                
                # Check if this is USDT contract
                if log.get('address', '').lower() == self.usdt_contract.lower():
                    # Parse Transfer event
                    topics = log.get('topics', [])
                    if len(topics) >= 3 and topics[0] == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':
                        # This is a Transfer event
                        from_address = '0x' + topics[1][-40:]
                        to_address = '0x' + topics[2][-40:]
                        amount_hex = log.get('data', '0x0')
                        
                        # Convert hex to decimal and adjust for 6 decimals (USDT ERC20 uses 6 decimals)
                        amount_wei = int(amount_hex, 16)
                        amount_usdt = amount_wei / (10 ** 6)
                        
                        usdt_transfer = {
                            'from': from_address,
                            'to': to_address,
                            'amount': amount_usdt
                        }
                        break
            
            if not usdt_transfer:
                print(f"❌ No USDT transfer found in transaction")
                return None
            
            # Get block timestamp
            block_number = int(tx_data.get('blockNumber', '0x0'), 16)
            block_params = {
                'chainid': '1',  # Ethereum mainnet
                'module': 'proxy',
                'action': 'eth_getBlockByNumber',
                'tag': hex(block_number),
                'boolean': 'false',
                'apikey': self.api_key
            }
            
            block_response = requests.get(self.base_url, params=block_params, timeout=10)
            block_data = block_response.json()
            block = block_data.get('result', {})
            timestamp = int(block.get('timestamp', '0x0'), 16) * 1000  # Convert to milliseconds
            
            # Build result
            result = {
                'transaction_id': tx_hash,
                'amount': usdt_transfer['amount'],
                'currency': 'USDT',
                'content': '',  # Ethereum doesn't have memo field
                'to_address': usdt_transfer['to'],
                'from_address': usdt_transfer['from'],
                'status': 'SUCCESS',
                'timestamp': timestamp,
                'confirmed': True,
                'block_number': block_number
            }
            
            print(f"✅ Retrieved transaction details:")
            print(f"   Transaction ID: {result['transaction_id']}")
            print(f"   Amount: {result['amount']} USDT")
            print(f"   From: {result['from_address']}")
            print(f"   To: {result['to_address']}")
            print(f"   Status: {result['status']}")
            
            return result
            
        except requests.exceptions.Timeout:
            print(f"❌ Etherscan API timeout")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Etherscan API request error: {e}")
            return None
        except Exception as e:
            print(f"❌ Error parsing Etherscan transaction: {e}")
            import traceback
            traceback.print_exc()
            return None
