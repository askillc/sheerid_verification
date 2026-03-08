"""
Red Envelope Spawn Scheduler Module
Generates 30 random spawn times per day with cryptographically secure randomness

Features:
- Generate exactly 30 spawn times per 24-hour period
- Use secrets.SystemRandom() for cryptographically secure randomness
- Ensure minimum 5-second spacing between spawns
- Store schedule in spawn_schedules table for audit trail
- Distribute spawns uniformly across all 24 hours

Validates Requirements: 1.1, 1.2, 1.5, 8.1, 8.3, 8.4
"""

import os
import secrets
import requests
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional


# Supabase credentials
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

# Constants
SPAWNS_PER_DAY = 30
MIN_SPACING_SECONDS = 5
SECONDS_PER_DAY = 86400


def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None):
    """Make request to Supabase REST API"""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    
    if method == 'GET':
        response = requests.get(url, headers=headers, params=params)
    elif method == 'POST':
        response = requests.post(url, headers=headers, json=data)
    elif method == 'PATCH':
        response = requests.patch(url, headers=headers, json=data, params=params)
    elif method == 'DELETE':
        response = requests.delete(url, headers=headers, params=params)
    
    return response


def get_unclaimed_count() -> int:
    """
    Get the count of unclaimed envelopes for today.
    
    Returns:
        Number of unclaimed envelopes
    """
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        response = supabase_request('GET', 'red_envelopes', params={
            'claimed_by': 'is.null',
            'spawn_time': f'gte.{today_start.isoformat()}',
            'spawn_time': f'lt.{today_end.isoformat()}',
            'select': 'id'
        })
        
        if response.status_code == 200:
            return len(response.json())
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to get unclaimed count: {e}")
        return 0


def calculate_dynamic_spawn_times(remaining_envelopes: int) -> List[datetime]:
    """
    Dynamically calculate spawn times based on remaining unclaimed envelopes.
    
    This intelligent algorithm distributes remaining spawns evenly across the remaining time in the day,
    preventing users from reverse-engineering spawn patterns via F12 inspection.
    
    Algorithm:
    1. Calculate remaining time until midnight
    2. Distribute remaining envelopes evenly across remaining time
    3. Add random jitter (±10%) to each spawn time for unpredictability
    4. Ensure minimum 5-second spacing between spawns
    
    Args:
        remaining_envelopes: Number of envelopes left to spawn today
        
    Returns:
        List of datetime objects for upcoming spawn times
    """
    if remaining_envelopes <= 0:
        return []
    
    now = datetime.utcnow()
    midnight_tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    remaining_seconds = (midnight_tomorrow - now).total_seconds()
    
    # If less than 1 minute remaining, spawn all immediately
    if remaining_seconds < 60:
        return [now + timedelta(seconds=i * MIN_SPACING_SECONDS) for i in range(remaining_envelopes)]
    
    # Calculate base interval between spawns
    base_interval = remaining_seconds / remaining_envelopes
    
    # Ensure minimum spacing is respected
    if base_interval < MIN_SPACING_SECONDS:
        base_interval = MIN_SPACING_SECONDS
    
    secure_random = secrets.SystemRandom()
    spawn_times = []
    current_time = now
    
    for i in range(remaining_envelopes):
        # Add random jitter (±10% of base interval) for unpredictability
        jitter_range = int(base_interval * 0.1)
        jitter = secure_random.randint(-jitter_range, jitter_range) if jitter_range > 0 else 0
        
        # Calculate next spawn time
        next_spawn = current_time + timedelta(seconds=base_interval + jitter)
        
        # Ensure we don't exceed midnight
        if next_spawn >= midnight_tomorrow:
            next_spawn = midnight_tomorrow - timedelta(seconds=(remaining_envelopes - i) * MIN_SPACING_SECONDS)
        
        spawn_times.append(next_spawn)
        current_time = next_spawn + timedelta(seconds=MIN_SPACING_SECONDS)
    
    return spawn_times


def generate_daily_schedule(target_date: Optional[datetime] = None) -> List[datetime]:
    """
    Generate 30 random spawn times for a 24-hour period using cryptographically secure randomness.
    
    IMPORTANT: This function is now DEPRECATED in favor of dynamic spawn calculation.
    It is kept for backward compatibility and initial schedule generation only.
    
    The new system uses calculate_dynamic_spawn_times() which:
    - Prevents F12 inspection of spawn patterns
    - Automatically adjusts spawn frequency based on remaining envelopes
    - Distributes spawns evenly across remaining time
    
    Algorithm:
    1. Use secrets.SystemRandom() for cryptographically secure random number generation
    2. Generate 30 random timestamps within the 24-hour period
    3. Sort timestamps chronologically
    4. Apply minimum 5-second spacing constraint by adjusting overlapping times forward
    5. Validate all times fall within the target 24-hour period
    
    Args:
        target_date: The date to generate schedule for (defaults to tomorrow)
        
    Returns:
        List of 30 datetime objects representing spawn times, sorted chronologically
        
    Validates:
        - Requirement 1.1: Exactly 30 spawn events per 24-hour period
        - Requirement 1.2: Random distribution across 24 hours
        - Requirement 1.5: Minimum 5-second spacing between spawns
        - Requirement 8.1: Cryptographically secure random number generator
        - Requirement 8.4: All spawn times fall within target 24-hour period
    """
    # Default to tomorrow if no date specified
    if target_date is None:
        target_date = datetime.utcnow().date() + timedelta(days=1)
    elif isinstance(target_date, datetime):
        target_date = target_date.date()
    
    # Calculate midnight UTC for the target date
    midnight_utc = datetime.combine(target_date, time(0, 0, 0))
    
    # Use secrets.SystemRandom() for cryptographically secure randomness
    secure_random = secrets.SystemRandom()
    
    # Generate 30 random seconds within the 24-hour period (0 to 86399)
    random_seconds = [secure_random.randint(0, SECONDS_PER_DAY - 1) for _ in range(SPAWNS_PER_DAY)]
    
    # Sort the random seconds
    random_seconds.sort()
    
    # Apply minimum spacing constraint (5 seconds)
    adjusted_seconds = []
    for i, seconds in enumerate(random_seconds):
        if i == 0:
            # First spawn time - no adjustment needed
            adjusted_seconds.append(seconds)
        else:
            # Ensure at least MIN_SPACING_SECONDS from previous spawn
            min_allowed = adjusted_seconds[-1] + MIN_SPACING_SECONDS
            if seconds < min_allowed:
                # Adjust forward to maintain minimum spacing
                adjusted_seconds.append(min_allowed)
            else:
                adjusted_seconds.append(seconds)
    
    # Convert adjusted seconds to datetime objects
    spawn_times = []
    for seconds in adjusted_seconds:
        # Ensure we don't exceed 24-hour boundary
        if seconds >= SECONDS_PER_DAY:
            # Cap at last second of the day
            seconds = SECONDS_PER_DAY - 1
        
        spawn_time = midnight_utc + timedelta(seconds=seconds)
        spawn_times.append(spawn_time)
    
    # Validate: Ensure all times fall within the target 24-hour period
    next_midnight = midnight_utc + timedelta(days=1)
    for spawn_time in spawn_times:
        assert midnight_utc <= spawn_time < next_midnight, \
            f"Spawn time {spawn_time} falls outside target period {midnight_utc} to {next_midnight}"
    
    # Validate: Ensure exactly 30 spawn times
    assert len(spawn_times) == SPAWNS_PER_DAY, \
        f"Expected {SPAWNS_PER_DAY} spawn times, got {len(spawn_times)}"
    
    # Validate: Ensure minimum spacing
    for i in range(1, len(spawn_times)):
        spacing = (spawn_times[i] - spawn_times[i-1]).total_seconds()
        assert spacing >= MIN_SPACING_SECONDS, \
            f"Spawn times {i-1} and {i} are only {spacing} seconds apart (minimum: {MIN_SPACING_SECONDS})"
    
    return spawn_times


def store_schedule(schedule_date: datetime, spawn_times: List[datetime]) -> bool:
    """
    Store the generated spawn schedule in the database for audit trail.
    
    Args:
        schedule_date: The date this schedule is for
        spawn_times: List of spawn times to store
        
    Returns:
        True if successfully stored, False otherwise
        
    Validates:
        - Requirement 8.3: Store schedule at midnight UTC
        - Requirement 8.5: Log all generated spawn times for audit purposes
    """
    try:
        # Convert datetime objects to ISO format strings for JSON storage
        spawn_times_iso = [st.isoformat() for st in spawn_times]
        
        # Prepare data for database
        data = {
            'schedule_date': schedule_date.date().isoformat(),
            'spawn_times': spawn_times_iso,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Store in spawn_schedules table
        response = supabase_request('POST', 'spawn_schedules', data=data)
        
        if response.status_code in [200, 201]:
            print(f"[INFO] Successfully stored spawn schedule for {schedule_date.date()}")
            print(f"[INFO] Generated {len(spawn_times)} spawn times")
            return True
        else:
            print(f"[ERROR] Failed to store spawn schedule: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Exception while storing spawn schedule: {e}")
        return False


def get_schedule(schedule_date: datetime) -> Optional[List[datetime]]:
    """
    Retrieve a stored spawn schedule from the database.
    
    Args:
        schedule_date: The date to retrieve schedule for
        
    Returns:
        List of spawn times if found, None otherwise
    """
    try:
        date_str = schedule_date.date().isoformat()
        response = supabase_request('GET', 'spawn_schedules', 
                                   params={'schedule_date': f'eq.{date_str}'})
        
        if response.status_code == 200:
            schedules = response.json()
            if schedules and len(schedules) > 0:
                # Parse ISO format strings back to datetime objects
                spawn_times_iso = schedules[0]['spawn_times']
                spawn_times = [datetime.fromisoformat(st) for st in spawn_times_iso]
                return spawn_times
        
        return None
        
    except Exception as e:
        print(f"[ERROR] Exception while retrieving spawn schedule: {e}")
        return None


def generate_and_store_schedule(target_date: Optional[datetime] = None) -> Optional[List[datetime]]:
    """
    Generate a new spawn schedule and store it in the database.
    
    This is the main entry point for schedule generation, typically called at midnight UTC.
    
    Args:
        target_date: The date to generate schedule for (defaults to tomorrow)
        
    Returns:
        List of spawn times if successful, None otherwise
        
    Validates:
        - Requirement 1.4: Generate new schedule at midnight UTC for next 24-hour period
        - Requirement 8.3: Calculate and store all 30 spawn times at midnight UTC
    """
    try:
        # Generate the schedule
        spawn_times = generate_daily_schedule(target_date)
        
        # Determine the schedule date
        if target_date is None:
            schedule_date = datetime.utcnow() + timedelta(days=1)
        else:
            schedule_date = target_date
        
        # Store in database
        success = store_schedule(schedule_date, spawn_times)
        
        if success:
            print(f"[SUCCESS] Generated and stored schedule for {schedule_date.date()}")
            print(f"[INFO] First spawn: {spawn_times[0]}")
            print(f"[INFO] Last spawn: {spawn_times[-1]}")
            return spawn_times
        else:
            print(f"[ERROR] Failed to store schedule")
            return None
            
    except Exception as e:
        print(f"[ERROR] Exception in generate_and_store_schedule: {e}")
        return None


def execute_spawn(spawn_time: datetime) -> Optional[str]:
    """
    Execute a spawn event by creating a new red envelope in the database.
    
    This function is called by the scheduler at each scheduled spawn time.
    It creates a new envelope record with a random reward amount.
    
    Args:
        spawn_time: The scheduled time for this spawn
        
    Returns:
        Envelope ID if successful, None otherwise
        
    Validates:
        - Requirement 1.3: Create envelope record when spawn event occurs
        - Requirement 7.1: Store envelope with all required fields
    """
    try:
        # Generate random reward amount (1 to 5 cash)
        # Use secrets.randbelow(5) + 1 for uniform distribution
        reward_amount = secrets.randbelow(5) + 1
        
        # Generate unique envelope ID
        envelope_id = f"env_{int(spawn_time.timestamp())}_{secrets.randbelow(10000)}"
        
        # Prepare envelope data
        envelope_data = {
            'id': envelope_id,
            'spawn_time': spawn_time.isoformat(),
            'claimed_by': None,
            'claimed_at': None,
            'reward_amount': reward_amount,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Insert into red_envelopes table
        response = supabase_request('POST', 'red_envelopes', data=envelope_data)
        
        if response.status_code in [200, 201]:
            print(f"[SUCCESS] Spawned envelope {envelope_id} with reward {reward_amount} at {spawn_time}")
            return envelope_id
        else:
            print(f"[ERROR] Failed to spawn envelope: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Exception during spawn execution: {e}")
        return None


def get_unclaimed_count() -> int:
    """
    Get the count of unclaimed envelopes for today.
    
    Returns:
        Number of unclaimed envelopes
    """
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        response = supabase_request('GET', 'red_envelopes', params={
            'claimed_by': 'is.null',
            'spawn_time': f'gte.{today_start.isoformat()}',
            'spawn_time': f'lt.{today_end.isoformat()}',
            'select': 'id'
        })
        
        if response.status_code == 200:
            return len(response.json())
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to get unclaimed count: {e}")
        return 0


if __name__ == "__main__":
    # Test the scheduler
    print("Testing Red Envelope Spawn Scheduler")
    print("=" * 50)
    
    # Generate schedule for tomorrow
    tomorrow = datetime.utcnow() + timedelta(days=1)
    spawn_times = generate_daily_schedule(tomorrow)
    
    print(f"\nGenerated {len(spawn_times)} spawn times for {tomorrow.date()}")
    print(f"First spawn: {spawn_times[0]}")
    print(f"Last spawn: {spawn_times[-1]}")
    
    # Check spacing
    min_spacing = min((spawn_times[i] - spawn_times[i-1]).total_seconds() 
                     for i in range(1, len(spawn_times)))
    max_spacing = max((spawn_times[i] - spawn_times[i-1]).total_seconds() 
                     for i in range(1, len(spawn_times)))
    avg_spacing = sum((spawn_times[i] - spawn_times[i-1]).total_seconds() 
                     for i in range(1, len(spawn_times))) / (len(spawn_times) - 1)
    
    print(f"\nSpacing statistics:")
    print(f"  Minimum: {min_spacing:.1f} seconds")
    print(f"  Maximum: {max_spacing:.1f} seconds")
    print(f"  Average: {avg_spacing:.1f} seconds")
    print(f"  Expected average: {SECONDS_PER_DAY / SPAWNS_PER_DAY:.1f} seconds")
