"""
Leaderboard Manager Module for Red Envelope Production System

Tracks and displays recent successful claims with privacy protection:
- Maintains list of 5 most recent claims
- Masks user IDs (shows only last 4 characters)
- Uses Redis sorted set for fast retrieval
- Real-time updates on new claims

Validates Requirements: 10.1, 10.2, 10.3, 10.4
"""

import os
import redis
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import json

# Redis connection
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    print(f"[WARNING] Redis connection failed: {e}. Leaderboard disabled.")
    redis_client = None

# Constants
LEADERBOARD_KEY = 'red_envelope:recent_claims'
LEADERBOARD_SIZE = 5


@dataclass
class LeaderboardEntry:
    """Represents a single leaderboard entry"""
    masked_user_id: str
    reward_amount: int
    claimed_at: str  # ISO format timestamp
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


def mask_user_id(user_id: str) -> str:
    """
    Mask user ID showing only last 4 characters.
    
    Examples:
        "user123456" -> "******3456"
        "abc" -> "***abc" (if less than 4 chars, show all with prefix)
    
    Args:
        user_id: User identifier to mask
        
    Returns:
        Masked user ID string
        
    Validates:
        - Requirement 10.2: Mask all but last 4 characters with asterisks
    """
    if not user_id:
        return "****"
    
    if len(user_id) <= 4:
        return "*" * 3 + user_id
    else:
        mask_length = len(user_id) - 4
        return "*" * mask_length + user_id[-4:]


def add_claim(user_id: str, reward_amount: int, timestamp: Optional[datetime] = None):
    """
    Add a successful claim to the leaderboard.
    
    Stores claim in Redis sorted set with timestamp as score.
    Automatically maintains only the 5 most recent claims.
    
    Args:
        user_id: User who claimed the envelope
        reward_amount: Amount of cash received
        timestamp: When the claim occurred (defaults to now)
        
    Validates:
        - Requirement 10.1: Display fixed list of 5 most recent claims
        - Requirement 10.2: Mask user IDs
        - Requirement 10.3: Show masked ID and reward amount
    """
    if not redis_client:
        print("[WARNING] Redis not available, skipping leaderboard update")
        return
    
    try:
        # Use provided timestamp or current time
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Create leaderboard entry
        entry = LeaderboardEntry(
            masked_user_id=mask_user_id(user_id),
            reward_amount=reward_amount,
            claimed_at=timestamp.isoformat()
        )
        
        # Store in Redis sorted set
        # Score is timestamp (for sorting), value is JSON entry
        score = timestamp.timestamp()
        value = json.dumps(entry.to_dict())
        
        redis_client.zadd(LEADERBOARD_KEY, {value: score})
        
        # Keep only the 5 most recent claims
        # Remove all but the top 5 (highest scores = most recent)
        redis_client.zremrangebyrank(LEADERBOARD_KEY, 0, -(LEADERBOARD_SIZE + 1))
        
        print(f"[LEADERBOARD] Added claim: {entry.masked_user_id} received {reward_amount} cash")
        
    except Exception as e:
        print(f"[ERROR] Failed to add claim to leaderboard: {e}")


def get_recent_claims(limit: int = LEADERBOARD_SIZE) -> List[Dict]:
    """
    Get the most recent claims from the leaderboard.
    
    Args:
        limit: Maximum number of claims to return (default: 5)
        
    Returns:
        List of leaderboard entry dictionaries, sorted by most recent first
        
    Validates:
        - Requirement 10.1: Return exactly 5 most recent claims (or fewer if less exist)
        - Requirement 10.3: Each entry contains masked user ID and reward amount
    """
    if not redis_client:
        print("[WARNING] Redis not available, returning empty leaderboard")
        return []
    
    try:
        # Get top N claims (highest scores = most recent)
        # ZREVRANGE returns in descending order (most recent first)
        claims_json = redis_client.zrevrange(LEADERBOARD_KEY, 0, limit - 1)
        
        # Parse JSON entries
        claims = []
        for claim_json in claims_json:
            try:
                claim_dict = json.loads(claim_json)
                claims.append(claim_dict)
            except json.JSONDecodeError:
                print(f"[WARNING] Failed to parse leaderboard entry: {claim_json}")
                continue
        
        return claims
        
    except Exception as e:
        print(f"[ERROR] Failed to get recent claims: {e}")
        return []


def clear_leaderboard():
    """
    Clear all entries from the leaderboard.
    
    Useful for testing or maintenance.
    """
    if not redis_client:
        print("[WARNING] Redis not available, cannot clear leaderboard")
        return
    
    try:
        redis_client.delete(LEADERBOARD_KEY)
        print("[INFO] Leaderboard cleared")
    except Exception as e:
        print(f"[ERROR] Failed to clear leaderboard: {e}")


def get_leaderboard_size() -> int:
    """
    Get the current number of entries in the leaderboard.
    
    Returns:
        Number of entries (0-5)
    """
    if not redis_client:
        return 0
    
    try:
        return redis_client.zcard(LEADERBOARD_KEY)
    except Exception as e:
        print(f"[ERROR] Failed to get leaderboard size: {e}")
        return 0


# For testing
if __name__ == "__main__":
    print("Testing Leaderboard Manager")
    print("=" * 50)
    
    # Clear existing data
    clear_leaderboard()
    
    # Add some test claims
    test_claims = [
        ("user_123456789", 100),
        ("telegram_987654321", 250),
        ("abc", 50),
        ("verylongusername12345", 500),
        ("short", 75),
        ("another_user_999", 150),  # This should push out the oldest
    ]
    
    for i, (user_id, amount) in enumerate(test_claims):
        timestamp = datetime.utcnow()
        add_claim(user_id, amount, timestamp)
        print(f"Added claim {i+1}: {mask_user_id(user_id)} - {amount} cash")
    
    print(f"\nLeaderboard size: {get_leaderboard_size()}")
    print("\nRecent claims:")
    claims = get_recent_claims()
    for i, claim in enumerate(claims, 1):
        print(f"{i}. {claim['masked_user_id']} - {claim['reward_amount']} cash at {claim['claimed_at']}")
    
    # Test masking
    print("\nUser ID masking tests:")
    test_ids = ["user123456", "abc", "12345678", "x", ""]
    for test_id in test_ids:
        print(f"  {test_id:15} -> {mask_user_id(test_id)}")
