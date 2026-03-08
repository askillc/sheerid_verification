"""
Token Price Decoder Service - Extract price information from JWT tokens
"""
import base64
import json
from typing import Optional, Dict, Any


class TokenPriceDecoder:
    """Service for decoding JWT fetch_token to extract price, currency, and storefront"""
    
    # Fallback values when decoding fails
    FALLBACK_PRICE = "16.00"
    FALLBACK_CURRENCY = "USD"
    FALLBACK_STOREFRONT = "VNM"
    
    @staticmethod
    def decode_fetch_token(fetch_token: str) -> Optional[Dict[str, Any]]:
        """
        Decode JWT fetch_token to extract real price, currency, and store info
        This prevents price mismatch that triggers RevenueCat fraud detection
        
        Args:
            fetch_token: JWT token string to decode
            
        Returns:
            Dictionary with price, currency, storefront, product_id or None if decoding fails
        """
        try:
            if not fetch_token or not isinstance(fetch_token, str):
                print("⚠️ Invalid fetch_token: empty or not a string")
                return None
            
            # JWT format: header.payload.signature
            parts = fetch_token.split('.')
            if len(parts) != 3:
                print(f"⚠️ Invalid JWT format: expected 3 parts, got {len(parts)}")
                return None
            
            # Decode payload (base64url)
            payload = parts[1]
            
            # Add padding if needed (base64 requires length % 4 == 0)
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            # Decode
            decoded_bytes = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded_bytes)
            
            # Extract fields
            result = {
                'price': data.get('price'),
                'currency': data.get('currency'),
                'storefront': data.get('storefront'),
                'product_id': data.get('productId')
            }
            
            print(f"✅ Decoded token data: price={result['price']}, currency={result['currency']}, storefront={result['storefront']}")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Error decoding fetch_token JSON: {e}")
            return None
        except Exception as e:
            print(f"⚠️ Error decoding fetch_token: {e}")
            return None
    
    @staticmethod
    def decode_with_fallback(fetch_token: str) -> Dict[str, Any]:
        """
        Decode fetch_token with fallback to default values on error
        
        Args:
            fetch_token: JWT token string to decode
            
        Returns:
            Dictionary with price, currency, storefront, product_id (uses fallback values on error)
        """
        decoded = TokenPriceDecoder.decode_fetch_token(fetch_token)
        
        if decoded is None:
            print(f"⚠️ Using fallback values: price={TokenPriceDecoder.FALLBACK_PRICE}, currency={TokenPriceDecoder.FALLBACK_CURRENCY}")
            return {
                'price': TokenPriceDecoder.FALLBACK_PRICE,
                'currency': TokenPriceDecoder.FALLBACK_CURRENCY,
                'storefront': TokenPriceDecoder.FALLBACK_STOREFRONT,
                'product_id': None
            }
        
        # Fill in missing fields with fallback values
        result = {
            'price': decoded.get('price') or TokenPriceDecoder.FALLBACK_PRICE,
            'currency': decoded.get('currency') or TokenPriceDecoder.FALLBACK_CURRENCY,
            'storefront': decoded.get('storefront') or TokenPriceDecoder.FALLBACK_STOREFRONT,
            'product_id': decoded.get('product_id')
        }
        
        return result
    
    @staticmethod
    def validate_price_currency(price: str, currency: str) -> bool:
        """
        Validate that price is numeric and currency is a valid 3-letter code
        
        Args:
            price: Price string to validate
            currency: Currency code to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate price is numeric
            if not price:
                return False
            
            try:
                float(price)
            except ValueError:
                print(f"⚠️ Invalid price format: {price} is not numeric")
                return False
            
            # Validate currency is 3-letter code
            if not currency or not isinstance(currency, str):
                return False
            
            if len(currency) != 3:
                print(f"⚠️ Invalid currency format: {currency} is not 3 letters")
                return False
            
            if not currency.isalpha():
                print(f"⚠️ Invalid currency format: {currency} contains non-alphabetic characters")
                return False
            
            return True
            
        except Exception as e:
            print(f"⚠️ Error validating price/currency: {e}")
            return False
    
    @staticmethod
    def prepare_revenuecat_data(fetch_token: str) -> Dict[str, Any]:
        """
        Prepare complete data for RevenueCat API request with decoded price/currency
        
        Args:
            fetch_token: JWT token to decode
            
        Returns:
            Dictionary with price, currency, storefront ready for API request
        """
        decoded = TokenPriceDecoder.decode_with_fallback(fetch_token)
        
        # Validate before returning
        if not TokenPriceDecoder.validate_price_currency(decoded['price'], decoded['currency']):
            print(f"⚠️ Validation failed, using fallback values")
            decoded['price'] = TokenPriceDecoder.FALLBACK_PRICE
            decoded['currency'] = TokenPriceDecoder.FALLBACK_CURRENCY
        
        return decoded
