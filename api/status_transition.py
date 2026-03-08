"""
Status Transition Module for Student Browserless Verification

This module handles the mapping of SheerID polling results to job statuses.
It provides a centralized, testable way to determine the final job status
based on polling results.

Requirements:
- 3.2: Map success statuses (success, complete, verified) to "completed"
- 3.3: Map failure statuses (failed, rejected, error) to "failed"
- 3.4: Handle timeout case
"""

from enum import Enum
from typing import Tuple, Optional, Dict, Any


class JobStatus(Enum):
    """Job status enum matching the design document"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"
    DOC_UPLOAD = "docUpload"
    FRAUD_REJECT = "fraud_reject"


# Success statuses from SheerID that should map to "completed"
SUCCESS_STATUSES = frozenset(['success', 'complete', 'verified'])

# Failure statuses from SheerID that should map to "failed"
FAILURE_STATUSES = frozenset(['failed', 'rejected', 'error'])

# Timeout indicators
TIMEOUT_INDICATORS = frozenset(['timeout'])


def map_polling_result_to_job_status(
    poll_ok: bool,
    poll_data: Optional[Dict[str, Any]]
) -> Tuple[JobStatus, str]:
    """
    Map polling result to job status.
    
    Args:
        poll_ok: Boolean indicating if polling was successful
        poll_data: Dictionary containing polling result data
        
    Returns:
        Tuple of (JobStatus, reason_string)
        
    Requirements:
        - 3.2: WHEN polling returns success status THEN the System SHALL update job status to completed
        - 3.3: WHEN polling returns failure status THEN the System SHALL update job status to failed
        - 3.4: WHEN polling times out THEN the System SHALL update job status to timeout
    """
    if poll_data is None:
        poll_data = {}
    
    # Extract current step and status from poll_data
    current_step = poll_data.get('currentStep', '').lower().strip()
    status = poll_data.get('status', '').lower().strip()
    error = poll_data.get('error', '')
    reason = poll_data.get('reason', '').lower().strip()
    rejection_reasons = poll_data.get('rejectionReasons', [])
    
    # Check for timeout first (Requirements 3.4)
    if status in TIMEOUT_INDICATORS or reason in TIMEOUT_INDICATORS:
        return JobStatus.TIMEOUT, f"Verification timeout: {error or 'Max polling attempts reached'}"
    
    # If polling was successful, check the current step
    if poll_ok:
        # Check for success statuses (Requirements 3.2)
        if current_step in SUCCESS_STATUSES:
            return JobStatus.COMPLETED, f"Verification completed successfully (step: {current_step})"
        
        # If poll_ok is True but step is not in success statuses, 
        # still treat as completed (poll_ok=True means success)
        return JobStatus.COMPLETED, f"Verification completed (poll_ok=True, step: {current_step})"
    
    # Polling failed - determine the reason
    
    # Check for rejection reasons (Requirements 3.3)
    if rejection_reasons:
        rejection_str = ', '.join(rejection_reasons) if isinstance(rejection_reasons, list) else str(rejection_reasons)
        return JobStatus.FAILED, f"Document rejected: {rejection_str}"
    
    # Check for failure statuses (Requirements 3.3)
    if current_step in FAILURE_STATUSES:
        return JobStatus.FAILED, f"Verification failed (step: {current_step})"
    
    # Check for error in poll_data
    if error:
        error_lower = str(error).lower()
        
        # Check if error indicates timeout
        if 'timeout' in error_lower:
            return JobStatus.TIMEOUT, f"Verification timeout: {error}"
        
        # Check if error indicates rejection
        if 'reject' in error_lower:
            return JobStatus.FAILED, f"Verification rejected: {error}"
        
        # Generic error
        return JobStatus.FAILED, f"Verification failed: {error}"
    
    # Default to failed if poll_ok is False and no specific reason found
    return JobStatus.FAILED, f"Verification failed (unknown reason, step: {current_step})"


def is_success_status(status: str) -> bool:
    """
    Check if a status string indicates success.
    
    Args:
        status: Status string from SheerID
        
    Returns:
        True if status indicates success, False otherwise
    """
    return status.lower().strip() in SUCCESS_STATUSES


def is_failure_status(status: str) -> bool:
    """
    Check if a status string indicates failure.
    
    Args:
        status: Status string from SheerID
        
    Returns:
        True if status indicates failure, False otherwise
    """
    return status.lower().strip() in FAILURE_STATUSES


def is_timeout_status(status: str) -> bool:
    """
    Check if a status string indicates timeout.
    
    Args:
        status: Status string from SheerID
        
    Returns:
        True if status indicates timeout, False otherwise
    """
    return status.lower().strip() in TIMEOUT_INDICATORS


def get_status_string(job_status: JobStatus) -> str:
    """
    Get the string value of a JobStatus for database storage.
    
    Args:
        job_status: JobStatus enum value
        
    Returns:
        String value for database storage
    """
    return job_status.value
