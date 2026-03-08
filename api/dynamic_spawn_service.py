"""
Dynamic Red Envelope Spawn Service
Intelligently spawns envelopes based on remaining unclaimed count

Features:
- Prevents F12 inspection by hiding spawn logic server-side
- Automatically adjusts spawn frequency based on remaining envelopes
- Distributes spawns evenly across remaining time in the day
- Uses cryptographically secure randomness with jitter for unpredictability

Security:
- No client-side exposure of spawn times
- Dynamic calculation prevents pattern recognition
- Server-side only execution
"""

import os
import time
import threading
from datetime import datetime, timedelta
from api.spawn_scheduler import (
    calculate_dynamic_spawn_times,
    execute_spawn,
    get_unclaimed_count,
    SPAWNS_PER_DAY
)


class DynamicSpawnService:
    """
    Service that dynamically spawns red envelopes throughout the day.
    
    Unlike the old static scheduler, this service:
    1. Checks remaining unclaimed envelopes every minute
    2. Calculates optimal spawn times for remaining envelopes
    3. Spawns envelopes at calculated times
    4. Adjusts frequency automatically as envelopes are claimed
    
    This prevents users from reverse-engineering spawn patterns via F12.
    """
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.last_check = None
        self.next_spawn_time = None
        self.total_spawned_today = 0
        
    def start(self):
        """Start the dynamic spawn service"""
        if self.running:
            print("[WARN] Dynamic spawn service already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_service, daemon=True)
        self.thread.start()
        print("[INFO] Dynamic spawn service started")
    
    def stop(self):
        """Stop the dynamic spawn service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[INFO] Dynamic spawn service stopped")
    
    def _run_service(self):
        """Main service loop"""
        print("[INFO] Dynamic spawn service loop started")
        
        while self.running:
            try:
                self._check_and_spawn()
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                print(f"[ERROR] Dynamic spawn service error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def _check_and_spawn(self):
        """Check if we need to spawn and execute spawn if needed"""
        now = datetime.utcnow()
        
        # Reset counter at midnight
        if self.last_check and now.date() > self.last_check.date():
            self.total_spawned_today = 0
            print(f"[INFO] New day started, reset spawn counter")
        
        self.last_check = now
        
        # Check if we've reached daily limit
        if self.total_spawned_today >= SPAWNS_PER_DAY:
            return
        
        # Get current unclaimed count
        unclaimed_count = get_unclaimed_count()
        
        # Calculate how many more we need to spawn today
        remaining_to_spawn = SPAWNS_PER_DAY - self.total_spawned_today
        
        # If we have unclaimed envelopes, wait before spawning more
        # This prevents flooding the system with too many unclaimed envelopes
        if unclaimed_count > 10:
            # Too many unclaimed, slow down spawning
            return
        
        # Calculate next spawn time if we don't have one
        if self.next_spawn_time is None or now >= self.next_spawn_time:
            # Calculate dynamic spawn times for remaining envelopes
            spawn_times = calculate_dynamic_spawn_times(remaining_to_spawn)
            
            if spawn_times and len(spawn_times) > 0:
                # Get the next spawn time
                self.next_spawn_time = spawn_times[0]
                
                # If it's time to spawn now
                if now >= self.next_spawn_time:
                    # Execute spawn
                    envelope_id = execute_spawn(now)
                    
                    if envelope_id:
                        self.total_spawned_today += 1
                        print(f"[SUCCESS] Spawned envelope {envelope_id} ({self.total_spawned_today}/{SPAWNS_PER_DAY})")
                        print(f"[INFO] Remaining to spawn today: {SPAWNS_PER_DAY - self.total_spawned_today}")
                        print(f"[INFO] Current unclaimed: {unclaimed_count + 1}")
                    
                    # Reset next spawn time to recalculate
                    self.next_spawn_time = None
    
    def get_status(self):
        """Get current service status"""
        return {
            'running': self.running,
            'total_spawned_today': self.total_spawned_today,
            'remaining_to_spawn': SPAWNS_PER_DAY - self.total_spawned_today,
            'next_spawn_time': self.next_spawn_time.isoformat() if self.next_spawn_time else None,
            'last_check': self.last_check.isoformat() if self.last_check else None
        }


# Global service instance
_spawn_service = None


def get_spawn_service() -> DynamicSpawnService:
    """Get or create the global spawn service instance"""
    global _spawn_service
    if _spawn_service is None:
        _spawn_service = DynamicSpawnService()
    return _spawn_service


def start_spawn_service():
    """Start the global spawn service"""
    service = get_spawn_service()
    service.start()
    return service


def stop_spawn_service():
    """Stop the global spawn service"""
    service = get_spawn_service()
    service.stop()


def get_service_status():
    """Get the status of the spawn service"""
    service = get_spawn_service()
    return service.get_status()


if __name__ == "__main__":
    # Test the service
    print("Testing Dynamic Spawn Service")
    print("=" * 50)
    
    service = start_spawn_service()
    
    try:
        # Run for 5 minutes
        print("Service running... (Press Ctrl+C to stop)")
        time.sleep(300)
    except KeyboardInterrupt:
        print("\nStopping service...")
    finally:
        stop_spawn_service()
        print("Service stopped")
