"""
TronScan API Client for querying USDT TRC20 transaction details
Handles API requests to TronScan API to verify transactions
"""

import os
import requests
from typing import Optional, Dict, Any


class TronScanAPIClient:
    """
    Client for interacting with TronScan API
    
    Provides methods to query transaction details by transaction hash.
    Used for verifying USDT TRC20 deposits.
    
    Requirements: 1.1, 3.2
    """
    
    def __init__(self):
        """
        Initialize TronScan API client
        
        No authentication required for public TronScan API
        """
        # TronScan API base URL
        self.base_url = "https://apilist.tronscanapi.com/api"
        
        print(f"✅ TronScanAPIClient initialized")
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make request to TronScan API
        
        Args:
            endpoint: API endpoint path (e.g., "/transaction-info")
            params: Request parameters
        
        Returns:
            Response data as dictionary, or None on error
        
        Requirements: 3.2, 3.3
        """
        try:
            # Make request
            url = f"{self.base_url}{endpoint}"
            
            print(f"🔍 Making TronScan API request: {endpoint}")
            if params:
                print(f"   Parameters: {params}")
            
            response = requests.get(url, params=params, timeout=10)
            
            print(f"   Response status: {response.status_code}")
            
            # Check response status
            if response.status_code != 200:
                print(f"❌ TronScan API error: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return None
            
            # Parse JSON response
            data = response.json()
            
            print(f"✅ TronScan API request successful")
            return data
            
        except requests.exceptions.Timeout:
            print(f"❌ TronScan API request timeout")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ TronScan API request error: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error in TronScan API request: {e}")
            return None
    
    def get_transaction_by_hash(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """
        Query TronScan API for transaction details by transaction hash
        
        Args:
            tx_hash: TRON transaction hash (ID)
        
        Returns:
            Transaction details dictionary with keys:
                - transaction_id: Transaction hash
                - amount: Transaction amount in USDT
                - currency: Currency code ("USDT")
                - content: Transaction note/memo (if available)
                - to_address: Recipient address
                - from_address: Sender address
                - status: Transaction status
                - timestamp: Transaction timestamp
            Returns None if hash not found or on error
        
        Examples:
            client = TronScanAPIClient()
            tx = client.get_transaction_by_hash("abc123...")
            if tx:
                print(f"Amount: {tx['amount']} {tx['currency']}")
                print(f"To: {tx['to_address']}")
        
        Requirements: 1.1, 3.3
        """
        try:
            if not tx_hash:
                print(f"❌ Invalid tx_hash: empty")
                return None
            
            print(f"🔍 Querying TronScan transaction: {tx_hash}")
            
            # TronScan transaction info endpoint
            endpoint = "/transaction-info"
            
            params = {
                'hash': tx_hash
            }
            
            response_data = self._make_request(endpoint, params)
            
            if not response_data:
                print(f"❌ Failed to get transaction data for hash: {tx_hash}")
                return None
            
            # Extract transaction data from response
            # TronScan API response structure for TRC20 USDT:
            # {
            #   "hash": "...",
            #   "block": 12345,
            #   "timestamp": 1234567890000,
            #   "ownerAddress": "T...",
            #   "toAddress": "T...",
            #   "contractRet": "SUCCESS",
            #   "confirmed": true,
            #   "trc20TransferInfo": [
            #     {
            #       "symbol": "USDT",
            #       "from_address": "T...",
            #       "to_address": "T...",
            #       "amount_str": "100000000",  # Amount in smallest unit (6 decimals for USDT)
            #       "decimals": 6
            #     }
            #   ],
            #   "data": "..."  # May contain memo/note
            # }
            
            # Check if transaction exists
            if not response_data.get('hash'):
                print(f"❌ Transaction not found: {tx_hash}")
                return None
            
            # Check if transaction is confirmed
            confirmed = response_data.get('confirmed', False)
            contract_ret = response_data.get('contractRet', '')
            
            if not confirmed:
                print(f"⚠️ Transaction not confirmed yet: {tx_hash}")
                return None
            
            if contract_ret != 'SUCCESS':
                print(f"❌ Transaction failed: {contract_ret}")
                return None
            
            # Extract TRC20 transfer info (for USDT)
            trc20_info = response_data.get('trc20TransferInfo', [])
            
            if not trc20_info:
                print(f"❌ No TRC20 transfer info found (not a USDT transaction)")
                return None
            
            # Get first TRC20 transfer (usually only one)
            transfer = trc20_info[0]
            
            # Extract fields
            symbol = transfer.get('symbol', '')
            from_address = transfer.get('from_address', '')
            to_address = transfer.get('to_address', '')
            amount_str = transfer.get('amount_str', '0')
            decimals = transfer.get('decimals', 6)
            
            # Validate it's USDT
            if symbol != 'USDT':
                print(f"❌ Not a USDT transaction (symbol: {symbol})")
                return None
            
            # Convert amount from smallest unit to USDT
            # USDT has 6 decimals, so divide by 1,000,000
            amount = float(amount_str) / (10 ** decimals)
            
            # Extract timestamp
            timestamp = response_data.get('timestamp', 0)
            
            # Try to extract memo/note from data field
            data = response_data.get('data', '')
            content = self._extract_memo_from_data(data)
            
            transaction_details = {
                'transaction_id': tx_hash,
                'amount': amount,
                'currency': 'USDT',
                'content': content,
                'to_address': to_address,
                'from_address': from_address,
                'status': contract_ret,
                'timestamp': timestamp,
                'confirmed': confirmed
            }
            
            print(f"✅ Retrieved transaction details:")
            print(f"   Transaction ID: {tx_hash}")
            print(f"   Amount: {amount} USDT")
            print(f"   From: {from_address}")
            print(f"   To: {to_address}")
            print(f"   Content: {content}")
            print(f"   Status: {contract_ret}")
            
            return transaction_details
            
        except Exception as e:
            print(f"❌ Error getting transaction by hash: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_memo_from_data(self, data: str) -> str:
        """
        Extract memo/note from transaction data field
        
        Args:
            data: Hex-encoded data field from transaction
        
        Returns:
            Decoded memo string, or empty string if no memo
        """
        try:
            if not data:
                return ''
            
            # Try to decode hex data to string
            # Remove '0x' prefix if present
            if data.startswith('0x'):
                data = data[2:]
            
            # Convert hex to bytes
            data_bytes = bytes.fromhex(data)
            
            # Try to decode as UTF-8
            memo = data_bytes.decode('utf-8', errors='ignore').strip()
            
            # Remove null bytes and non-printable characters
            memo = ''.join(c for c in memo if c.isprintable())
            
            return memo
            
        except Exception as e:
            print(f"⚠️ Could not extract memo from data: {e}")
            return ''
