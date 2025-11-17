"""
Security logging utilities for GameReady.
Centralized logging for security-related events.
"""
import logging

logger = logging.getLogger(__name__)


def log_join_code_attempt(event_type, ip_address, user_id=None, join_code=None, success=False, team_id=None, error_message=None):
    """
    Log security events related to join code attempts for audit trail.
    
    Args:
        event_type: Type of event ('join_attempt', 'join_success', 'join_failed', 'join_rate_limited')
        ip_address: IP address of the requester
        user_id: User ID (if authenticated)
        join_code: Join code attempted (only log if failed for privacy)
        success: Whether operation was successful
        team_id: Team ID (if successful)
        error_message: Optional error message
    """
    log_data = {
        'event_type': event_type,
        'ip_address': ip_address,
        'success': success,
    }
    
    if user_id:
        log_data['user_id'] = user_id
    
    # Only log join code if failed (for security audit, not for successful joins)
    if not success and join_code:
        # Log partial code for security (first 2 chars only to detect patterns)
        log_data['join_code_prefix'] = join_code[:2] if len(join_code) >= 2 else 'XX'
        log_data['join_code_length'] = len(join_code)
    
    if team_id:
        log_data['team_id'] = team_id
    
    if error_message:
        log_data['error'] = error_message
    
    if success:
        logger.info(f"Join code security event: {log_data}")
    else:
        # Failed attempts are warnings for security monitoring
        logger.warning(f"Join code security event (FAILED): {log_data}")

