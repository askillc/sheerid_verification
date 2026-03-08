"""
Binance API Client for querying transaction details
Handles authentication and API requests to Binance Pay API
"""

import os
import time
import hmac
import hashlib
import json
import requests
from typing import Optional, Dict, Any
from urllib.parse import urlencode


class BinanceAPIClient:
    """
    Client for interacting with Binance Pay API
    
    Handles authentication using API key and secret with HMAC-SHA256 signatures.
    Provides methods to query transaction details by order_id.
    
    Requirements: 3.1, 3.2
    """
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize Binance API client with credentials
        
        Args:
            api_key: Binance API key (defaults to BINANCE_API_KEY env var)
            api_secret: Binance API secret (defaults to BINANCE_API_SECRET env var)
        
        Raises:
            ValueError: If API credentials are not provided
        """
        self.api_key = api_key or os.getenv('BINANCE_API_KEY')
        self.api_secret = api_secret or os.getenv('BINANCE_API_SECRET')
        
        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Binance API credentials not found. "
                "Please set BINANCE_API_KEY and BINANCE_API_SECRET environment variables."
            )
        
        # Binance Pay API base URL
        self.base_url = "https://bpay.binanceapi.com"
        
        print(f"✅ BinanceAPIClient initialized with API key: {self.api_key[:10]}...")
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Generate HMAC-SHA256 signature for API request
        
        Args:
            params: Request parameters as dictionary
        
        Returns:
            Hex-encoded signature string
        
        Requirements: 3.1, 3.2
        """
        # Sort parameters and create query string
        query_string = urlencode(sorted(params.items()))
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            key=self.api_secret.encode('utf-8'),
            msg=query_string.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "POST"
    ) -> Optional[Dict[str, Any]]:
        """
        Make authenticated request to Binance API
        
        Args:
            endpoint: API endpoint path (e.g., "/binancepay/openapi/v2/order/query")
            params: Request parameters
            method: HTTP method (POST or GET)
        
        Returns:
            Response data as dictionary, or None on error
        
        Requirements: 3.1, 3.2, 3.3
        """
        try:
            # Add timestamp to parameters
            if params is None:
                params = {}
            
            timestamp = str(int(time.time() * 1000))
            nonce = str(int(time.time() * 1000000))  # More unique nonce
            
            # Prepare request body for POST
            import json
            request_body = json.dumps(params)
            
            # Create payload for signature: timestamp + nonce + body
            payload = timestamp + "\n" + nonce + "\n" + request_body + "\n"
            
            # Generate signature
            signature = hmac.new(
                key=self.api_secret.encode('utf-8'),
                msg=payload.encode('utf-8'),
                digestmod=hashlib.sha512
            ).hexdigest().upper()
            
            # Prepare headers for Binance Pay API
            headers = {
                'Content-Type': 'application/json',
                'BinancePay-Timestamp': timestamp,
                'BinancePay-Nonce': nonce,
                'BinancePay-Certificate-SN': self.api_key,
                'BinancePay-Signature': signature
            }
            
            # Make request
            url = f"{self.base_url}{endpoint}"
            
            print(f"🔍 Making Binance API request: {endpoint}")
            print(f"   Method: {method}")
            print(f"   Body: {request_body}")
            
            if method.upper() == "POST":
                response = requests.post(url, data=request_body, headers=headers, timeout=10)
            else:
                response = requests.get(url, params=params, headers=headers, timeout=10)
            
            print(f"   Response status: {response.status_code}")
            
            # Check response status
            if response.status_code != 200:
                print(f"❌ Binance API error: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return None
            
            # Parse JSON response
            data = response.json()
            
            # Check for API-level errors
            if data.get('status') != 'SUCCESS':
                print(f"❌ Binance API returned error status: {data.get('status')}")
                print(f"   Error code: {data.get('code')}")
                print(f"   Error message: {data.get('errorMessage')}")
                return None
            
            print(f"✅ Binance API request successful")
            return data
            
        except requests.exceptions.Timeout:
            print(f"❌ Binance API request timeout")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Binance API request error: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error in Binance API request: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_transaction_by_order_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Query Binance Pay API for transaction details by order_id
        
        Args:
            order_id: Binance Pay order ID from transaction history
        
        Returns:
            Transaction details dictionary with keys:
                - transaction_id: Unique transaction ID
                - amount: Transaction amount
                - currency: Currency code (e.g., "VND")
                - content: Transaction note/content (e.g., "BN1234567890")
                - status: Transaction status
                - timestamp: Transaction timestamp
            Returns None if order_id not found or on error
        
        Examples:
            client = BinanceAPIClient()
            tx = client.get_transaction_by_order_id("123456789")
            if tx:
                print(f"Amount: {tx['amount']} {tx['currency']}")
                print(f"Content: {tx['content']}")
        
        Requirements: 1.1, 3.3
        """
        try:
            if not order_id:
                print(f"❌ Invalid order_id: empty")
                return None
            
            print(f"🔍 Querying Binance transaction: {order_id}")
            
            # Binance Pay order query endpoint
            endpoint = "/binancepay/openapi/v3/order/query"
            
            params = {
                'merchantTradeNo': order_id
            }
            
            response_data = self._make_request(endpoint, params, method="POST")
            
            if not response_data:
                print(f"❌ Failed to get transaction data for order_id: {order_id}")
                return None
            
            # Extract transaction data from response
            # Binance Pay API response structure:
            # {
            #   "status": "SUCCESS",
            #   "code": "000000",
            #   "data": {
            #     "merchantTradeNo": "...",
            #     "transactionId": "...",
            #     "totalFee": "100.00",
            #     "currency": "VND",
            #     "buyerInfo": {...},
            #     "orderInfo": "BN1234567890",  # This is the content/note
            #     "transactTime": 1234567890000
            #   }
            # }
            
            data = response_data.get('data', {})
            
            if not data:
                print(f"❌ No data in response for order_id: {order_id}")
                return None
            
            # Extract fields
            transaction_id = data.get('transactionId')
            amount = float(data.get('totalFee', 0))
            currency = data.get('currency', 'VND')
            content = data.get('orderInfo', '')  # This contains the BN+telegram_id note
            status = data.get('status', 'unknown')
            timestamp = data.get('transactTime')
            
            # Validate required fields
            if not transaction_id:
                print(f"❌ Missing transaction_id in response")
                return None
            
            transaction_details = {
                'transaction_id': transaction_id,
                'amount': amount,
                'currency': currency,
                'content': content,
                'status': status,
                'timestamp': timestamp,
                'order_id': order_id
            }
            
            print(f"✅ Retrieved transaction details:")
            print(f"   Transaction ID: {transaction_id}")
            print(f"   Amount: {amount} {currency}")
            print(f"   Content: {content}")
            print(f"   Status: {status}")
            
            return transaction_details
            
        except Exception as e:
            print(f"❌ Error getting transaction by order_id: {e}")
            return None
