"""
Audit logging utilities for GameReady.

This module provides structured logging for critical user actions and data modifications
to create an audit trail for security, compliance, and debugging purposes.
"""

import logging
from typing import Optional, Dict, Any
from django.contrib.auth.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)


def log_user_action(
    action_type: str,
    user: Optional[User],
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
):
    """
    Log user actions (login, logout, etc.) for audit trail.
    
    Args:
        action_type: Type of action (e.g., 'user_login', 'user_logout', 'report_submitted')
        user: User instance (can be None for anonymous actions)
        success: Whether the action was successful
        details: Additional details about the action
        error_message: Error message if action failed
    """
    log_data = {
        'action_type': action_type,
        'timestamp': timezone.now().isoformat(),
        'success': success,
    }
    
    if user and user.is_authenticated:
        log_data['user_id'] = user.id
        log_data['username'] = user.username
        log_data['user_email'] = user.email
        try:
            if hasattr(user, 'profile'):
                log_data['user_role'] = user.profile.role
        except Exception:
            pass
    else:
        log_data['user_id'] = None
        log_data['username'] = 'anonymous'
    
    if details:
        log_data.update(details)
    
    if error_message:
        log_data['error'] = error_message
    
    if success:
        logger.info(f"User action: {log_data}")
    else:
        logger.warning(f"User action (FAILED): {log_data}")


def log_team_action(
    action_type: str,
    user: User,
    team_id: int,
    team_name: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
):
    """
    Log team management actions (create, update, join, leave) for audit trail.
    
    Args:
        action_type: Type of action (e.g., 'team_created', 'team_updated', 'team_joined', 'team_left')
        user: User instance performing the action
        team_id: Team ID
        team_name: Team name (optional, for convenience)
        success: Whether the action was successful
        details: Additional details about the action
        error_message: Error message if action failed
    """
    log_data = {
        'action_type': action_type,
        'timestamp': timezone.now().isoformat(),
        'user_id': user.id if user and user.is_authenticated else None,
        'username': user.username if user and user.is_authenticated else 'anonymous',
        'user_email': user.email if user and user.is_authenticated else None,
        'team_id': team_id,
        'team_name': team_name,
        'success': success,
    }
    
    if user and user.is_authenticated:
        try:
            if hasattr(user, 'profile'):
                log_data['user_role'] = user.profile.role
        except Exception:
            pass
    
    if details:
        log_data.update(details)
    
    if error_message:
        log_data['error'] = error_message
    
    if success:
        logger.info(f"Team action: {log_data}")
    else:
        logger.warning(f"Team action (FAILED): {log_data}")


def log_data_modification(
    action_type: str,
    user: User,
    model_name: str,
    object_id: Optional[int] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
):
    """
    Log data modifications (create, update, delete) for audit trail.
    
    Args:
        action_type: Type of action ('create', 'update', 'delete')
        user: User instance performing the action
        model_name: Name of the model being modified (e.g., 'ReadinessReport', 'TeamTag')
        object_id: ID of the object being modified
        success: Whether the action was successful
        details: Additional details about the action
        error_message: Error message if action failed
    """
    log_data = {
        'action_type': f'{model_name}_{action_type}',
        'timestamp': timezone.now().isoformat(),
        'user_id': user.id if user and user.is_authenticated else None,
        'username': user.username if user and user.is_authenticated else 'anonymous',
        'user_email': user.email if user and user.is_authenticated else None,
        'model_name': model_name,
        'object_id': object_id,
        'success': success,
    }
    
    if user and user.is_authenticated:
        try:
            if hasattr(user, 'profile'):
                log_data['user_role'] = user.profile.role
        except Exception:
            pass
    
    if details:
        log_data.update(details)
    
    if error_message:
        log_data['error'] = error_message
    
    if success:
        logger.info(f"Data modification: {log_data}")
    else:
        logger.warning(f"Data modification (FAILED): {log_data}")


def log_report_submission(
    user: User,
    report_id: int,
    readiness_score: int,
    date: str,
    success: bool = True,
    error_message: Optional[str] = None
):
    """
    Log readiness report submission for audit trail.
    
    Args:
        user: User instance submitting the report
        report_id: ReadinessReport ID
        readiness_score: Calculated readiness score
        date: Date of the report (YYYY-MM-DD format)
        success: Whether the submission was successful
        error_message: Error message if submission failed
    """
    log_data = {
        'action_type': 'report_submitted',
        'timestamp': timezone.now().isoformat(),
        'user_id': user.id,
        'username': user.username,
        'user_email': user.email,
        'report_id': report_id,
        'readiness_score': readiness_score,
        'report_date': date,
        'success': success,
    }
    
    try:
        if hasattr(user, 'profile'):
            log_data['user_role'] = user.profile.role
    except Exception:
        pass
    
    if error_message:
        log_data['error'] = error_message
    
    if success:
        logger.info(f"Report submission: {log_data}")
    else:
        logger.warning(f"Report submission (FAILED): {log_data}")

