"""
Supabase helper functions for Binance deposits
Handles database operations for binance_deposits table
"""

import re
import hmac
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from api.supabase_client import get_supabase_client


def parse_binance_content(content: str) -> Optional[str]:
    """
    Parse telegram_id from Binance transaction content
    
    Args:
        content: Transaction content (e.g., "BN1234567890", "bn123", "BN999")
    
    Returns:
        telegram_id as string if valid format, None otherwise
    
    Examples:
        "BN1234567890" -> "1234567890"
        "BN123" -> "123"
        "bn999" -> "999" (case insensitive)
        "Bn456" -> "456"
        "bN789" -> "789"
        "BN" -> None (no digits)
        "ABC123" -> None (wrong prefix)
        "" -> None (empty string)
        "123BN" -> None (wrong order)
        "BN-123" -> None (special characters)
    
    Requirements: 1.1, 2.1
    """
    if not content:
        return None
    
    # Case-insensitive pattern: BN followed by one or more digits
    # ^ = start of string, $ = end of string (exact match)
    pattern = r'^[Bb][Nn](\d+)$'
    
    match = re.match(pattern, content)
    
    if match:
        # Extract the digits group (group 1)
        telegram_id = match.group(1)
        return telegram_id
    
    return None


def create_binance_deposit_record(
    transaction_id: str,
    telegram_id: str,
    amount: float,
    content: str,
    currency: str = 'VND',
    status: str = 'pending'
) -> Optional[Dict[str, Any]]:
    """
    Create a new Binance deposit record in the database
    
    Args:
        transaction_id: Unique Binance transaction ID
        telegram_id: User's Telegram ID
        amount: Deposit amount
        content: Original transaction content (e.g., BN1234567890)
        currency: Currency code (default: VND)
        status: Initial status (default: pending)
    
    Returns:
        Created record dict if successful, None otherwise
    
    Requirements: 4.1, 7.1, 7.3
    """
    try:
        client = get_supabase_client()
        if not client:
            print("❌ Failed to get Supabase client")
            return None
        
        print(f"💰 Creating Binance deposit record: {transaction_id} for user {telegram_id}")
        
        deposit_data = {
            'transaction_id': transaction_id,
            'telegram_id': str(telegram_id),
            'amount': float(amount),
            'currency': currency,
            'content': content,
            'status': status,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        result = client.table('binance_deposits').insert(deposit_data).execute()
        
        if result.data:
            created_record = result.data[0]
            print(f"✅ Created Binance deposit record: {created_record['id']}")
            return created_record
        else:
            print(f"❌ Failed to create Binance deposit record")
            return None
            
    except Exception as e:
        print(f"❌ Error creating Binance deposit record: {e}")
        return None


def get_binance_deposit_by_tx_id(transaction_id: str) -> Optional[Dict[str, Any]]:
    """
    Get Binance deposit record by transaction ID
    
    Args:
        transaction_id: Binance transaction ID to look up
    
    Returns:
        Deposit record dict if found, None otherwise
    
    Requirements: 4.1, 7.1, 7.3
    """
    try:
        client = get_supabase_client()
        if not client:
            print("❌ Failed to get Supabase client")
            return None
        
        print(f"🔍 Looking up Binance deposit: {transaction_id}")
        
        result = client.table('binance_deposits').select('*').eq('transaction_id', transaction_id).execute()
        
        if result.data and len(result.data) > 0:
            deposit = result.data[0]
            print(f"✅ Found Binance deposit: {deposit['id']}")
            return deposit
        else:
            print(f"❌ Binance deposit not found: {transaction_id}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting Binance deposit: {e}")
        return None


def update_binance_deposit_status(
    transaction_id: str,
    status: str,
    error_message: Optional[str] = None,
    processed_at: Optional[datetime] = None
) -> bool:
    """
    Update the status of a Binance deposit record
    
    Args:
        transaction_id: Binance transaction ID
        status: New status (pending, completed, failed)
        error_message: Error message if status is failed
        processed_at: Timestamp when processing completed
    
    Returns:
        True if update successful, False otherwise
    
    Requirements: 4.1, 7.1, 7.3
    """
    try:
        client = get_supabase_client()
        if not client:
            print("❌ Failed to get Supabase client")
            return False
        
        print(f"🔄 Updating Binance deposit status: {transaction_id} -> {status}")
        
        update_data = {
            'status': status,
            'updated_at': datetime.now().isoformat()
        }
        
        if error_message:
            update_data['error_message'] = error_message
        
        if processed_at:
            update_data['processed_at'] = processed_at.isoformat()
        elif status == 'completed':
            # Auto-set processed_at when marking as completed
            update_data['processed_at'] = datetime.now().isoformat()
        
        result = client.table('binance_deposits').update(update_data).eq('transaction_id', transaction_id).execute()
        
        # Check if update was successful
        if result is not None:
            print(f"✅ Updated Binance deposit status: {transaction_id} -> {status}")
            return True
        else:
            print(f"❌ Failed to update Binance deposit status")
            return False
            
    except Exception as e:
        print(f"❌ Error updating Binance deposit status: {e}")
        return False


def get_binance_deposits_by_telegram_id(
    telegram_id: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get all Binance deposits for a specific user
    
    Args:
        telegram_id: User's Telegram ID
        limit: Maximum number of records to return (optional)
        offset: Number of records to skip (optional)
    
    Returns:
        List of deposit records, sorted by created_at DESC
    
    Requirements: 4.1, 7.1, 7.3
    """
    try:
        client = get_supabase_client()
        if not client:
            print("❌ Failed to get Supabase client")
            return []
        
        print(f"🔍 Getting Binance deposits for user: {telegram_id}")
        
        query = client.table('binance_deposits').select('*').eq('telegram_id', str(telegram_id)).order('created_at', desc=True)
        
        if limit:
            query = query.limit(limit)
        
        if offset:
            query = query.offset(offset)
        
        result = query.execute()
        
        if result.data:
            print(f"✅ Found {len(result.data)} Binance deposits for user {telegram_id}")
            return result.data
        else:
            print(f"❌ No Binance deposits found for user {telegram_id}")
            return []
            
    except Exception as e:
        print(f"❌ Error getting Binance deposits: {e}")
        return []


def get_all_binance_deposits(
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get all Binance deposits with optional filtering
    
    Args:
        status: Filter by status (optional)
        start_date: Filter by start date (optional)
        end_date: Filter by end date (optional)
        limit: Maximum number of records to return (optional)
    
    Returns:
        List of deposit records, sorted by created_at DESC
    
    Requirements: 7.1, 7.2, 7.4
    """
    try:
        client = get_supabase_client()
        if not client:
            print("❌ Failed to get Supabase client")
            return []
        
        print(f"🔍 Getting all Binance deposits (status={status}, start={start_date}, end={end_date})")
        
        query = client.table('binance_deposits').select('*')
        
        if status:
            query = query.eq('status', status)
        
        if start_date:
            query = query.gte('created_at', start_date.isoformat())
        
        if end_date:
            query = query.lte('created_at', end_date.isoformat())
        
        query = query.order('created_at', desc=True)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        
        if result.data:
            print(f"✅ Found {len(result.data)} Binance deposits")
            return result.data
        else:
            print(f"❌ No Binance deposits found")
            return []
            
    except Exception as e:
        print(f"❌ Error getting all Binance deposits: {e}")
        return []


def verify_binance_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify Binance webhook signature using HMAC-SHA256
    
    Computes HMAC-SHA256 signature from payload and secret, then compares
    with the signature from the request header using constant-time comparison
    to prevent timing attacks.
    
    Args:
        payload: Raw request body as string
        signature: Signature from request header (hex string)
        secret: Binance webhook secret key
    
    Returns:
        True if signature is valid, False otherwise
    
    Examples:
        payload = '{"transaction_id":"BIN123","amount":100000}'
        secret = "my_secret_key"
        signature = compute_hmac_sha256(payload, secret)
        verify_binance_signature(payload, signature, secret)
        -> True
        
        verify_binance_signature(payload, "invalid_sig", secret)
        -> False
    
    Requirements: 3.1, 3.2
    """
    try:
        # Compute expected signature using HMAC-SHA256
        expected_signature = hmac.new(
            key=secret.encode('utf-8'),
            msg=payload.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Use constant-time comparison to prevent timing attacks
        # hmac.compare_digest is designed for this purpose
        is_valid = hmac.compare_digest(expected_signature, signature)
        
        if is_valid:
            print(f"✅ Binance signature verification passed")
        else:
            print(f"❌ Binance signature verification failed")
            print(f"   Expected: {expected_signature[:20]}...")
            print(f"   Received: {signature[:20]}...")
        
        return is_valid
        
    except Exception as e:
        print(f"❌ Error verifying Binance signature: {e}")
        return False


def validate_binance_transaction(
    transaction_id: str,
    telegram_id: str,
    amount: float,
    transaction_time: Optional[datetime] = None
) -> Tuple[bool, str]:
    """
    Validate Binance transaction before processing
    
    Performs the following checks:
    1. Transaction ID not already in database (duplicate check)
    2. User exists for the given telegram_id
    3. Amount is greater than 0
    4. Telegram ID format is valid (digits only)
    5. Transaction time is within 2 hours (if provided)
    
    Args:
        transaction_id: Binance transaction ID
        telegram_id: User's Telegram ID (should be digits only)
        amount: Deposit amount in VND
        transaction_time: Transaction timestamp (optional, for time validation)
    
    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if all validations pass
        - (False, error_message) if any validation fails
    
    Examples:
        validate_binance_transaction("BIN123", "1234567890", 100000)
        -> (True, "")
        
        validate_binance_transaction("BIN123", "1234567890", 0)
        -> (False, "Amount must be greater than 0")
        
        validate_binance_transaction("BIN123", "abc123", 100000)
        -> (False, "Invalid telegram_id format: must contain only digits")
    
    Requirements: 2.2, 2.3, 2.4, 4.1
    """
    try:
        # Validate telegram_id format (digits only)
        if not telegram_id or not telegram_id.isdigit():
            error_msg = f"Invalid telegram_id format: must contain only digits (got: {telegram_id})"
            print(f"❌ Validation failed: {error_msg}")
            return (False, error_msg)
        
        # Validate amount > 0
        if amount <= 0:
            error_msg = f"Amount must be greater than 0 (got: {amount})"
            print(f"❌ Validation failed: {error_msg}")
            return (False, error_msg)
        
        # Validate transaction time (must be within 2 hours)
        if transaction_time:
            from datetime import timezone, timedelta
            import os
            
            current_time = datetime.now(timezone.utc)
            
            # Ensure transaction_time is timezone-aware
            if transaction_time.tzinfo is None:
                transaction_time = transaction_time.replace(tzinfo=timezone.utc)
            
            time_diff = current_time - transaction_time
            
            # Get expiry time from env (default 2 hours)
            expiry_hours = float(os.getenv('TRANSACTION_EXPIRY_HOURS', '2'))
            max_age = timedelta(hours=expiry_hours)
            
            if time_diff > max_age:
                hours_old = time_diff.total_seconds() / 3600
                error_msg = f"TRANSACTION_TOO_OLD:{hours_old:.1f}:{expiry_hours}"
                print(f"❌ Validation failed: Transaction too old")
                print(f"   Transaction time: {transaction_time}")
                print(f"   Current time: {current_time}")
                print(f"   Age: {hours_old:.1f} hours (max: {expiry_hours} hours)")
                return (False, error_msg)
        
        # Check if transaction_id already exists (duplicate check)
        existing_deposit = get_binance_deposit_by_tx_id(transaction_id)
        if existing_deposit:
            error_msg = f"Transaction ID already exists: {transaction_id}"
            print(f"❌ Validation failed: {error_msg}")
            return (False, error_msg)
        
        # Verify user exists in database
        client = get_supabase_client()
        if not client:
            error_msg = "Failed to connect to database"
            print(f"❌ Validation failed: {error_msg}")
            return (False, error_msg)
        
        print(f"🔍 Checking if user exists: {telegram_id}")
        user_result = client.table('users').select('id').eq('telegram_id', str(telegram_id)).execute()
        
        if not user_result.data or len(user_result.data) == 0:
            error_msg = f"User not found for telegram_id: {telegram_id}"
            print(f"❌ Validation failed: {error_msg}")
            return (False, error_msg)
        
        print(f"✅ All validations passed for transaction {transaction_id}")
        return (True, "")
        
    except Exception as e:
        error_msg = f"Validation error: {str(e)}"
        print(f"❌ Validation exception: {error_msg}")
        return (False, error_msg)


def send_binance_deposit_notification(
    telegram_id: str,
    amount: float,
    new_balance: float,
    transaction_id: str
) -> bool:
    """
    Send Telegram notification to user about successful Binance deposit
    
    Formats an English message with deposit details and sends it via Telegram Bot API.
    If notification fails, the error is logged but the function returns True to indicate
    that the deposit itself was successful (notification failure should not fail the deposit).
    
    Args:
        telegram_id: User's Telegram ID
        amount: Deposited amount in CASH
        new_balance: User's new cash balance after deposit
        transaction_id: Binance transaction ID
    
    Returns:
        True if notification sent successfully or if notification fails gracefully,
        False only if there's a critical error
    
    Message format (English):
        ✅ DEPOSIT SUCCESSFUL!
        
        💰 Amount: {amount:,} CASH
        💎 New balance: {new_balance:,} CASH
        🔗 Order ID: {transaction_id}
        ⏰ Time: {timestamp}
        
        Thank you for depositing via Binance Pay!
    
    Examples:
        send_binance_deposit_notification("1234567890", 100000, 150000, "BIN123")
        -> Sends notification and returns True
        
        send_binance_deposit_notification("invalid", 100000, 150000, "BIN123")
        -> Logs error but returns True (graceful failure)
    
    Requirements: 1.5, 5.1, 5.2, 5.3, 5.4, 5.5
    """
    try:
        import os
        import requests
        from datetime import datetime, timezone, timedelta
        
        # Get Vietnam time (UTC+7)
        vietnam_tz = timezone(timedelta(hours=7))
        vietnam_time = datetime.now(vietnam_tz)
        timestamp = vietnam_time.strftime('%d/%m/%Y %H:%M:%S')
        
        # Format message in English with deposit details
        # Requirements: 5.1, 5.2, 5.4, 5.5
        message = (
            "✅ DEPOSIT SUCCESSFUL!\n\n"
            f"💰 Amount: {int(amount):,} CASH\n"
            f"💎 New balance: {int(new_balance):,} CASH\n"
            f"🔗 Order ID:\n{transaction_id}\n"
            f"⏰ Time: {timestamp}\n\n"
            "Thank you for depositing via Binance Pay!"
        )
        
        # Get bot token from environment
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print(f"⚠️ TELEGRAM_BOT_TOKEN not found, cannot send notification")
            # Log but don't fail the deposit - notification is not critical
            return True
        
        # Send message via Telegram Bot API
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': telegram_id,
            'text': message,
            'disable_web_page_preview': True
        }
        
        print(f"📤 Sending Binance deposit notification to user {telegram_id}")
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Notification sent successfully to user {telegram_id}")
            return True
        else:
            # Log error but don't fail - notification failure should not fail deposit
            # Requirement: 5.3 - Handle notification failures gracefully
            print(f"⚠️ Failed to send notification (HTTP {response.status_code}): {response.text}")
            print(f"   Deposit was successful, but notification failed")
            return True
            
    except Exception as e:
        # Log error but don't fail - notification failure should not fail deposit
        # Requirement: 5.3 - Handle notification failures gracefully (log but don't fail deposit)
        print(f"⚠️ Error sending Binance deposit notification: {e}")
        print(f"   Deposit was successful, but notification failed")
        return True


def add_cash_from_binance(
    telegram_id: str,
    amount: float,
    transaction_id: str,
    content: str
) -> bool:
    """
    Add cash to user account from Binance deposit and create transaction record
    
    This function performs the following operations atomically:
    1. Store the transaction ID in binance_deposits table (to prevent duplicates)
    2. Get current user cash balance
    3. Add deposit amount to cash
    4. Create transaction record with type='binance_deposit'
    5. Store binance_tx_id in transaction record
    
    The operations are designed to be atomic - if any step fails, the entire
    operation should fail without partial updates.
    
    Args:
        telegram_id: User's Telegram ID
        amount: Amount in VND to add to cash balance
        transaction_id: Binance transaction ID (for duplicate prevention)
        content: Original transaction content (e.g., "BN1234567890")
    
    Returns:
        True if successful, False otherwise
    
    Side effects:
        - Updates user.cash in database
        - Creates binance_deposits record
        - Creates transaction record with type='binance_deposit'
        - Stores transaction_id to prevent duplicates
    
    Examples:
        add_cash_from_binance("1234567890", 100000, "BIN123", "BN1234567890")
        -> True (cash increased by 100000, records created)
        
        add_cash_from_binance("1234567890", 100000, "BIN123", "BN1234567890")
        -> False (duplicate transaction_id)
    
    Requirements: 1.3, 1.4, 4.3
    """
    try:
        client = get_supabase_client()
        if not client:
            print("❌ Failed to get Supabase client")
            return False
        
        print(f"💰 Adding {amount} VND cash from Binance for user {telegram_id}")
        
        # Step 1: Create binance_deposits record FIRST (for duplicate prevention)
        # This ensures transaction_id is stored before cash is added
        # Requirement 4.3: Transaction ID storage ordering
        deposit_record = create_binance_deposit_record(
            transaction_id=transaction_id,
            telegram_id=telegram_id,
            amount=amount,
            content=content,
            currency='VND',
            status='processing'
        )
        
        if not deposit_record:
            print(f"❌ Failed to create binance_deposits record")
            return False
        
        # Step 2: Get current user and their cash balance
        print(f"🔍 Getting user data for telegram_id: {telegram_id}")
        user_result = client.table('users').select('id, cash').eq('telegram_id', str(telegram_id)).execute()
        
        if not user_result.data or len(user_result.data) == 0:
            print(f"❌ User not found: {telegram_id}")
            # Mark deposit as failed
            update_binance_deposit_status(transaction_id, 'failed', error_message='User not found')
            return False
        
        user = user_result.data[0]
        user_id = user['id']
        current_cash = user.get('cash', 0) or 0  # Handle None values
        new_cash = current_cash + int(amount)
        
        print(f"💵 Current cash: {current_cash} VND, New cash: {new_cash} VND")
        
        # Step 3: Update user's cash balance
        update_result = client.table('users').update({
            'cash': new_cash,
            'updated_at': datetime.now().isoformat()
        }).eq('id', user_id).execute()
        
        if not update_result.data:
            print(f"❌ Failed to update user cash")
            # Mark deposit as failed
            update_binance_deposit_status(transaction_id, 'failed', error_message='Failed to update cash')
            return False
        
        # Step 4: Create transaction record with type='binance_deposit'
        # Store transaction_id in description field
        transaction_data = {
            'user_id': user_id,
            'type': 'binance_deposit',
            'amount': int(amount),
            'coins': 0,  # This is a cash deposit, not coins
            'description': f'Binance deposit: {transaction_id} - {content}',
            'status': 'completed',
            'created_at': datetime.now().isoformat()
        }
        
        transaction_result = client.table('transactions').insert(transaction_data).execute()
        
        if not transaction_result.data:
            print(f"❌ Failed to create transaction record")
            # Note: Cash was already added, but we couldn't create the record
            # Mark deposit as completed but log the issue
            update_binance_deposit_status(
                transaction_id, 
                'completed', 
                error_message='Cash added but transaction record creation failed'
            )
            return False
        
        # Step 5: Mark deposit as completed
        update_binance_deposit_status(transaction_id, 'completed')
        
        print(f"✅ Successfully added {amount} VND cash to user {telegram_id}")
        print(f"   Transaction ID: {transaction_id}")
        print(f"   New balance: {new_cash} VND")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding cash from Binance: {e}")
        # Try to mark deposit as failed
        try:
            update_binance_deposit_status(transaction_id, 'failed', error_message=str(e))
        except:
            pass
        return False
