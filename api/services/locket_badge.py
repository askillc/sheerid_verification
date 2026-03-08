"""
Locket Badge Setting Service - Locket API Integration

This service handles automatic Gold badge setting via Locket API's changeProfileInfo endpoint.
Critical: Analytics object field order must be preserved to avoid "invalid badge" errors.
"""
import aiohttp
from collections import OrderedDict


async def set_gold_badge(
    uid: str,
    firebase_jwt: str,
    firebase_appcheck: str,
    firebase_fcm: str
) -> tuple[bool, str]:
    """
    Set locket_gold badge via Locket API
    
    Args:
        uid: Locket user ID
        firebase_jwt: Firebase JWT token for authorization
        firebase_appcheck: Firebase AppCheck token
        firebase_fcm: Firebase FCM token
    
    Returns:
        (success: bool, message: str)
    """
    
    # Construct analytics object with EXACT field order
    # Order is critical: ios_version, experiments, amplitude, google_analytics, platform
    analytics = OrderedDict([
        ("ios_version", "2.33.0.2"),
        ("experiments", {}),
        ("amplitude", {}),
        ("google_analytics", {}),
        ("platform", "ios")
    ])
    
    # Build request body
    body = {
        "data": {
            "badge": "locket_gold",
            "analytics": analytics
        }
    }
    
    # Build request headers with Firebase tokens
    headers = {
        "authorization": f"Bearer {firebase_jwt}",
        "x-firebase-appcheck": firebase_appcheck,
        "content-type": "application/json",
        "user-agent": "com.locket.Locket/2.33.0 iPhone/26.2.1 hw/iPhone16_2",
        "firebase-instance-id-token": firebase_fcm
    }
    
    url = "https://api.locketcamera.com/changeProfileInfo"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body, timeout=15) as res:
                status_code = res.status
                
                # Success response
                if 200 <= status_code < 300:
                    try:
                        response_data = await res.json()
                        return True, "Badge set successfully"
                    except:
                        # Success but non-JSON response
                        return True, "Badge set successfully (non-JSON response)"
                
                # Error responses
                elif status_code == 401:
                    return False, "Unauthorized: Invalid Firebase tokens"
                
                elif status_code == 400:
                    try:
                        error_data = await res.json()
                        error_msg = error_data.get('message', 'Bad Request')
                        return False, f"Bad Request: {error_msg}"
                    except:
                        return False, "Bad Request: Invalid badge or analytics format"
                
                elif status_code >= 500:
                    return False, f"Server Error: {status_code}"
                
                else:
                    return False, f"API Error: {status_code}"
    
    except aiohttp.ClientTimeout:
        return False, "Network timeout calling Locket API"
    
    except aiohttp.ClientConnectionError:
        return False, "Connection error calling Locket API"
    
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
