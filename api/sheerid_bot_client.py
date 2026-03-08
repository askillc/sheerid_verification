"""
SheerID Bot API Client for verification services
Handles authentication and API requests to api.sheeridbot.com

Requirements: 1.1, 2.1, 3.1, 4.1-4.5, 5.1
"""

import os
import hmac
import hashlib
import json
import time
import requests
from typing import Optional, Dict, Any


class SheerIDAPIError(Exception):
    """Custom exception for SheerID Bot API errors"""
    
    def __init__(self, code: str, message: str, status_code: int = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"{code}: {message}")


class SheerIDBotClient:
    """
    Client for interacting with SheerID Bot API
    
    Handles authentication using X-API-Key header.
    Provides methods to submit verifications, check job status, and verify webhooks.
    
    Requirements: 1.1, 2.1, 3.1, 4.1-4.5, 5.1
    """
    
    # Default API base URL
    DEFAULT_BASE_URL = "https://api.sheeridbot.com/api/v1"
    
    # Verification types and their costs
    VERIFICATION_TYPES = {
        'gemini': {'cost': 10, 'display_name': 'Gemini'},
        'perplexity': {'cost': 25, 'display_name': 'Perplexity'},
        'teacher': {'cost': 50, 'display_name': 'Teacher'}
    }
    
    # Error code mappings
    ERROR_CODES = {
        401: 'INVALID_API_KEY',
        402: 'INSUFFICIENT_CREDITS',
        429: 'RATE_LIMITED',
        400: 'INVALID_REQUEST',
        404: 'JOB_NOT_FOUND',
        503: 'MAINTENANCE_MODE',
        500: 'INTERNAL_ERROR'
    }
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize SheerID Bot API client with credentials
        
        Args:
            api_key: SheerID Bot API key (defaults to SHEERID_BOT_API_KEY env var)
            base_url: API base URL (defaults to SHEERID_BOT_API_URL env var or DEFAULT_BASE_URL)
        
        Raises:
            ValueError: If API key is not provided
        """
        self.api_key = api_key or os.getenv('SHEERID_BOT_API_KEY')
        self.base_url = base_url or os.getenv('SHEERID_BOT_API_URL', self.DEFAULT_BASE_URL)
        
        # Remove trailing slash from base URL
        self.base_url = self.base_url.rstrip('/')
        
        if not self.api_key:
            raise ValueError(
                "SheerID Bot API key not found. "
                "Please set SHEERID_BOT_API_KEY environment variable."
            )
        
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        print(f"✅ SheerIDBotClient initialized with API key: {self.api_key[:10]}...")

    def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make authenticated request to SheerID Bot API
        
        Args:
            endpoint: API endpoint path (e.g., "/verify")
            method: HTTP method (POST or GET)
            data: Request body data for POST requests
            params: Query parameters for GET requests
            retry_count: Current retry attempt (for exponential backoff)
        
        Returns:
            Response data as dictionary
        
        Raises:
            SheerIDAPIError: On API errors with appropriate error code
        
        Requirements: 4.1-4.5
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            print(f"🔍 Making SheerID Bot API request: {method} {endpoint}")
            if data:
                print(f"   Body: {json.dumps(data)}")
            
            if method.upper() == "POST":
                response = requests.post(
                    url,
                    json=data,
                    headers=self.headers,
                    timeout=30
                )
            else:
                response = requests.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=30
                )
            
            print(f"   Response status: {response.status_code}")
            
            # Handle error responses (accept 200 and 202 as success)
            if response.status_code not in [200, 201, 202]:
                return self._handle_error_response(
                    response, endpoint, method, data, params, retry_count
                )
            
            # Parse successful response
            response_data = response.json()
            print(f"✅ SheerID Bot API request successful")
            return response_data
            
        except requests.exceptions.Timeout:
            print(f"❌ SheerID Bot API request timeout")
            raise SheerIDAPIError('TIMEOUT', 'Request timed out', 408)
        except requests.exceptions.RequestException as e:
            print(f"❌ SheerID Bot API request error: {e}")
            raise SheerIDAPIError('CONNECTION_ERROR', str(e), 0)
        except json.JSONDecodeError as e:
            print(f"❌ SheerID Bot API invalid JSON response: {e}")
            raise SheerIDAPIError('INVALID_RESPONSE', 'Invalid JSON response', 0)
    
    def _handle_error_response(
        self,
        response: requests.Response,
        endpoint: str,
        method: str,
        data: Optional[Dict[str, Any]],
        params: Optional[Dict[str, Any]],
        retry_count: int
    ) -> Dict[str, Any]:
        """
        Handle error responses from API with retry logic for transient errors
        
        Args:
            response: HTTP response object
            endpoint: API endpoint
            method: HTTP method
            data: Request body data
            params: Query parameters
            retry_count: Current retry attempt
        
        Returns:
            Response data if retry succeeds
        
        Raises:
            SheerIDAPIError: On non-recoverable errors or max retries exceeded
        
        Requirements: 4.1-4.5
        """
        status_code = response.status_code
        error_code = self.ERROR_CODES.get(status_code, 'UNKNOWN_ERROR')
        
        # Try to get error message from response body
        try:
            error_data = response.json()
            error_message = error_data.get('message', error_data.get('error', response.text))
            # Check for specific error codes in response
            if 'code' in error_data:
                error_code = error_data['code']
        except:
            error_message = response.text or f"HTTP {status_code}"
        
        print(f"❌ SheerID Bot API error: {error_code} - {error_message}")
        
        # Handle retryable errors (429, 500, 503)
        if status_code in [429, 500, 503] and retry_count < 3:
            # Exponential backoff: 1s, 4s, 16s
            delay = 4 ** retry_count
            print(f"⏳ Retrying in {delay} seconds (attempt {retry_count + 1}/3)...")
            time.sleep(delay)
            return self._make_request(
                endpoint, method, data, params, retry_count + 1
            )
        
        # Raise appropriate error
        raise SheerIDAPIError(error_code, error_message, status_code)

    def submit_verification(
        self,
        url: str,
        verification_type: str = 'gemini',
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a verification job to SheerID Bot API
        
        Args:
            url: SheerID verification URL from user
            verification_type: Type of verification ('gemini', 'perplexity', 'teacher')
            webhook_url: Optional webhook URL for completion callback
        
        Returns:
            Dictionary with job details
        
        Raises:
            SheerIDAPIError: On API errors
            ValueError: If verification_type is invalid
        
        Requirements: 1.1, 2.1, 3.1
        """
        # Validate verification type
        if verification_type not in self.VERIFICATION_TYPES:
            raise ValueError(
                f"Invalid verification type: {verification_type}. "
                f"Must be one of: {list(self.VERIFICATION_TYPES.keys())}"
            )
        
        # Validate URL
        if not url or not url.strip():
            raise SheerIDAPIError('INVALID_URL', 'URL cannot be empty', 400)
        
        full_url = url.strip()
        print(f"🔗 URL: {full_url}")
        
        # Send full URL as-is (including query params)
        data = {
            'url': full_url
        }
        
        # Add webhook URL if provided
        if webhook_url:
            data['webhook_url'] = webhook_url
        elif os.getenv('SHEERID_BOT_WEBHOOK_URL'):
            data['webhook_url'] = os.getenv('SHEERID_BOT_WEBHOOK_URL')
        
        print(f"📤 Submitting {verification_type} verification...")
        print(f"📤 Request data: {data}")
        
        response = self._make_request('/verify', method='POST', data=data)
        
        print(f"✅ Verification job submitted: {response.get('job_id')}")
        return response
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a verification job
        
        Args:
            job_id: Job ID returned from submit_verification
        
        Returns:
            Dictionary with job status:
                - job_id: Job identifier
                - status: Current status ('pending', 'processing', 'success', 'failed')
                - result_details: Additional details (if completed)
                - error_message: Error message (if failed)
        
        Raises:
            SheerIDAPIError: On API errors (including JOB_NOT_FOUND)
        
        Examples:
            client = SheerIDBotClient()
            status = client.get_job_status("job_123456")
            print(f"Status: {status['status']}")
        
        Requirements: 6.1-6.5
        """
        if not job_id or not job_id.strip():
            raise SheerIDAPIError('INVALID_REQUEST', 'Job ID cannot be empty', 400)
        
        print(f"🔍 Checking job status: {job_id}")
        
        response = self._make_request(
            f'/job/{job_id}',
            method='GET'
        )
        
        print(f"📋 Job {job_id} status: {response.get('status')}")
        return response
    
    def get_balance(self) -> Dict[str, Any]:
        """
        Get API credit balance
        
        Returns:
            Dictionary with balance info:
                - balance: Current credit balance
                - currency: Currency code
        
        Raises:
            SheerIDAPIError: On API errors
        
        Examples:
            client = SheerIDBotClient()
            balance = client.get_balance()
            print(f"Balance: {balance['balance']} {balance['currency']}")
        
        Requirements: 4.2
        """
        print(f"💰 Checking API balance...")
        
        response = self._make_request('/balance', method='GET')
        
        print(f"💰 API balance: {response.get('balance')}")
        return response

    def verify_webhook_signature(
        self,
        payload: Dict[str, Any],
        signature: str
    ) -> bool:
        """
        Verify webhook signature using HMAC-SHA256
        
        The signature is computed as:
        HMAC-SHA256(JSON.stringify(payload, sorted_keys), api_key)
        
        Args:
            payload: Webhook payload dictionary
            signature: X-Webhook-Signature header value
        
        Returns:
            True if signature is valid, False otherwise
        
        Examples:
            client = SheerIDBotClient()
            is_valid = client.verify_webhook_signature(
                payload={"job_id": "123", "status": "success"},
                signature="abc123..."
            )
            if is_valid:
                print("Webhook is authentic")
        
        Requirements: 5.1, 5.4
        """
        if not signature:
            print(f"❌ Webhook signature missing")
            return False
        
        try:
            # Serialize payload with sorted keys for consistent signature
            payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
            
            # Compute HMAC-SHA256 signature
            expected_signature = hmac.new(
                key=self.api_key.encode('utf-8'),
                msg=payload_str.encode('utf-8'),
                digestmod=hashlib.sha256
            ).hexdigest()
            
            # Compare signatures (constant-time comparison)
            is_valid = hmac.compare_digest(signature.lower(), expected_signature.lower())
            
            if is_valid:
                print(f"✅ Webhook signature verified")
            else:
                print(f"❌ Webhook signature mismatch")
                print(f"   Expected: {expected_signature}")
                print(f"   Received: {signature}")
            
            return is_valid
            
        except Exception as e:
            print(f"❌ Error verifying webhook signature: {e}")
            return False
    
    @classmethod
    def get_verification_cost(cls, verification_type: str) -> int:
        """
        Get the cost for a verification type
        
        Args:
            verification_type: Type of verification ('gemini', 'perplexity', 'teacher')
        
        Returns:
            Cost in cash units
        
        Raises:
            ValueError: If verification_type is invalid
        
        Requirements: 7.5
        """
        if verification_type not in cls.VERIFICATION_TYPES:
            raise ValueError(
                f"Invalid verification type: {verification_type}. "
                f"Must be one of: {list(cls.VERIFICATION_TYPES.keys())}"
            )
        
        return cls.VERIFICATION_TYPES[verification_type]['cost']
    
    @classmethod
    def get_display_name(cls, verification_type: str) -> str:
        """
        Get the display name for a verification type
        
        Args:
            verification_type: Type of verification ('gemini', 'perplexity', 'teacher')
        
        Returns:
            Display name string
        
        Raises:
            ValueError: If verification_type is invalid
        """
        if verification_type not in cls.VERIFICATION_TYPES:
            raise ValueError(
                f"Invalid verification type: {verification_type}. "
                f"Must be one of: {list(cls.VERIFICATION_TYPES.keys())}"
            )
        
        return cls.VERIFICATION_TYPES[verification_type]['display_name']
    
    @classmethod
    def is_configured(cls) -> bool:
        """
        Check if SheerID Bot API is properly configured
        
        Returns:
            True if API key is configured, False otherwise
        
        Requirements: 7.4
        """
        api_key = os.getenv('SHEERID_BOT_API_KEY')
        return bool(api_key and api_key.strip())


# Convenience function to create client instance
def get_sheerid_bot_client() -> Optional[SheerIDBotClient]:
    """
    Get a SheerID Bot API client instance
    
    Returns:
        SheerIDBotClient instance if configured, None otherwise
    """
    if not SheerIDBotClient.is_configured():
        print(f"⚠️ SheerID Bot API not configured")
        return None
    
    try:
        return SheerIDBotClient()
    except ValueError as e:
        print(f"❌ Failed to create SheerID Bot client: {e}")
        return None
