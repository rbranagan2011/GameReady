"""
Input validation utilities for views.

This module provides centralized validation functions for common input types
to ensure data integrity and security across all endpoints.
"""

import re
import json
import logging
from datetime import datetime, date
from typing import Tuple, Optional, Dict, Any
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Team, TeamTag, Profile

logger = logging.getLogger(__name__)

# Date format constants
DATE_FORMAT = '%Y-%m-%d'
MONTH_FORMAT = '%Y-%m'

# Valid weekday names for TeamSchedule
VALID_WEEKDAYS = {'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'}


def validate_date_string(date_str: str, param_name: str = 'date') -> Tuple[bool, Optional[date], Optional[str]]:
    """
    Validate a date string in YYYY-MM-DD format.
    
    Args:
        date_str: The date string to validate
        param_name: Name of the parameter for error messages
        
    Returns:
        Tuple of (is_valid, parsed_date, error_message)
        - is_valid: True if date is valid
        - parsed_date: Parsed date object or None
        - error_message: Error message or None
    """
    if not date_str:
        return False, None, f"{param_name} parameter is required"
    
    if not isinstance(date_str, str):
        return False, None, f"{param_name} must be a string"
    
    # Check format with regex first (more strict)
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return False, None, f"{param_name} must be in YYYY-MM-DD format"
    
    try:
        parsed_date = datetime.strptime(date_str, DATE_FORMAT).date()
        return True, parsed_date, None
    except ValueError as e:
        return False, None, f"Invalid {param_name} format: must be YYYY-MM-DD"


def validate_month_string(month_str: str, param_name: str = 'month') -> Tuple[bool, Optional[int], Optional[int], Optional[str]]:
    """
    Validate a month string in YYYY-MM format.
    
    Args:
        month_str: The month string to validate (e.g., "2025-11")
        param_name: Name of the parameter for error messages
        
    Returns:
        Tuple of (is_valid, year, month, error_message)
        - is_valid: True if month string is valid
        - year: Parsed year or None
        - month: Parsed month or None
        - error_message: Error message or None
    """
    if not month_str:
        return False, None, None, f"{param_name} parameter is required"
    
    if not isinstance(month_str, str):
        return False, None, None, f"{param_name} must be a string"
    
    # Check format with regex
    if not re.match(r'^\d{4}-\d{2}$', month_str):
        return False, None, None, f"{param_name} must be in YYYY-MM format"
    
    try:
        parts = month_str.split('-')
        year = int(parts[0])
        month = int(parts[1])
        
        # Validate month range
        if month < 1 or month > 12:
            return False, None, None, f"{param_name} month must be between 01 and 12"
        
        # Validate year range (reasonable bounds)
        if year < 2000 or year > 2100:
            return False, None, None, f"{param_name} year must be between 2000 and 2100"
        
        return True, year, month, None
    except (ValueError, IndexError) as e:
        return False, None, None, f"Invalid {param_name} format: must be YYYY-MM"


def validate_team_id(team_id: Any, user, allow_management: bool = False) -> Tuple[bool, Optional[Team], Optional[str]]:
    """
    Validate team ID and check user ownership/access.
    
    Args:
        team_id: Team ID (can be int, string, or None)
        user: Django User object
        allow_management: If True, allow management users to access any team
        
    Returns:
        Tuple of (is_valid, team_object, error_message)
        - is_valid: True if team ID is valid and user has access
        - team_object: Team instance or None
        - error_message: Error message or None
    """
    if team_id is None:
        return False, None, "team_id parameter is required"
    
    # Convert to int
    try:
        team_id_int = int(team_id)
    except (ValueError, TypeError):
        return False, None, "team_id must be a valid integer"
    
    # Validate range
    if team_id_int <= 0:
        return False, None, "team_id must be a positive integer"
    
    # Get team
    try:
        team = Team.objects.get(id=team_id_int)
    except Team.DoesNotExist:
        return False, None, "Team not found"
    
    # Check access
    if allow_management:
        # Check if user has management access
        from .views import has_management_access
        if has_management_access(user):
            return True, team, None
    
    # Check if user is a coach of this team
    try:
        profile = user.profile
        if profile.role == Profile.Role.COACH:
            # Check if coach has access to this team
            user_teams = profile.get_teams()
            if team in user_teams:
                return True, team, None
            return False, None, "You do not have access to this team"
        return False, None, "Only coaches can access team data"
    except Profile.DoesNotExist:
        return False, None, "User profile not found"


def validate_athlete_id(athlete_id: Any, coach_team: Team) -> Tuple[bool, Optional[Any], Optional[str]]:
    """
    Validate athlete ID and check if athlete belongs to coach's team.
    
    Args:
        athlete_id: Athlete ID (can be int, string, or None)
        coach_team: Team object that the coach has access to
        
    Returns:
        Tuple of (is_valid, athlete_user, error_message)
        - is_valid: True if athlete ID is valid and belongs to team
        - athlete_user: User instance or None
        - error_message: Error message or None
    """
    if athlete_id is None:
        return False, None, "athlete_id parameter is required"
    
    # Convert to int
    try:
        athlete_id_int = int(athlete_id)
    except (ValueError, TypeError):
        return False, None, "athlete_id must be a valid integer"
    
    # Validate range
    if athlete_id_int <= 0:
        return False, None, "athlete_id must be a positive integer"
    
    # Get athlete
    from django.contrib.auth.models import User
    try:
        athlete = User.objects.get(id=athlete_id_int)
    except User.DoesNotExist:
        return False, None, "Athlete not found"
    
    # Check if athlete belongs to team
    try:
        profile = athlete.profile
        if profile.role != Profile.Role.ATHLETE:
            return False, None, "User is not an athlete"
        
        athlete_teams = profile.get_teams()
        if coach_team not in athlete_teams:
            return False, None, "Athlete does not belong to this team"
        
        return True, athlete, None
    except Profile.DoesNotExist:
        return False, None, "Athlete profile not found"


def validate_target_readiness(value: Any) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validate target readiness value (0-100).
    
    Args:
        value: Target readiness value to validate
        
    Returns:
        Tuple of (is_valid, parsed_value, error_message)
        - is_valid: True if value is valid
        - parsed_value: Parsed integer or None
        - error_message: Error message or None
    """
    if value is None:
        return False, None, "target_readiness is required"
    
    try:
        parsed_value = int(value)
    except (ValueError, TypeError):
        return False, None, "target_readiness must be a valid integer"
    
    if parsed_value < 0 or parsed_value > 100:
        return False, None, "target_readiness must be between 0 and 100"
    
    return True, parsed_value, None


def validate_weekday(weekday: str) -> Tuple[bool, Optional[str]]:
    """
    Validate weekday string (Mon, Tue, Wed, etc.).
    
    Args:
        weekday: Weekday string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if weekday is valid
        - error_message: Error message or None
    """
    if not weekday:
        return False, "weekday is required"
    
    if not isinstance(weekday, str):
        return False, "weekday must be a string"
    
    if weekday not in VALID_WEEKDAYS:
        return False, f"weekday must be one of: {', '.join(sorted(VALID_WEEKDAYS))}"
    
    return True, None


def validate_team_schedule_json(weekly_schedule: Dict[str, Any], team: Team) -> Tuple[bool, Optional[str]]:
    """
    Validate TeamSchedule weekly_schedule JSON structure.
    
    Expected format: {"Mon": 3, "Tue": 7, ...} where values are TeamTag IDs (int or None)
    
    Args:
        weekly_schedule: Dictionary to validate
        team: Team object to validate tag IDs against
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if structure is valid
        - error_message: Error message or None
    """
    if not isinstance(weekly_schedule, dict):
        return False, "weekly_schedule must be a dictionary"
    
    # Validate keys are valid weekdays
    for weekday in weekly_schedule.keys():
        is_valid, error_msg = validate_weekday(weekday)
        if not is_valid:
            return False, f"Invalid weekday in weekly_schedule: {error_msg}"
    
    # Validate values are valid tag IDs or None
    tag_ids = set(TeamTag.objects.filter(team=team).values_list('id', flat=True))
    
    for weekday, tag_id in weekly_schedule.items():
        if tag_id is None:
            continue  # None is allowed (cleared tag)
        
        try:
            tag_id_int = int(tag_id)
        except (ValueError, TypeError):
            return False, f"Invalid tag ID for {weekday}: must be an integer or None"
        
        if tag_id_int not in tag_ids:
            return False, f"Tag ID {tag_id_int} for {weekday} does not belong to this team"
    
    return True, None


def validate_date_overrides_json(date_overrides: Dict[str, Any], team: Team) -> Tuple[bool, Optional[str]]:
    """
    Validate TeamSchedule date_overrides JSON structure.
    
    Expected format: {"2025-10-26": 5, "2025-12-25": 9} where keys are dates (YYYY-MM-DD) and values are TeamTag IDs (int or None)
    
    Args:
        date_overrides: Dictionary to validate
        team: Team object to validate tag IDs against
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if structure is valid
        - error_message: Error message or None
    """
    if not isinstance(date_overrides, dict):
        return False, "date_overrides must be a dictionary"
    
    # Validate keys are valid dates
    for date_str in date_overrides.keys():
        is_valid, parsed_date, error_msg = validate_date_string(date_str, 'date')
        if not is_valid:
            return False, f"Invalid date in date_overrides: {error_msg}"
    
    # Validate values are valid tag IDs or None
    tag_ids = set(TeamTag.objects.filter(team=team).values_list('id', flat=True))
    
    for date_str, tag_id in date_overrides.items():
        if tag_id is None:
            continue  # None is allowed (cleared tag)
        
        try:
            tag_id_int = int(tag_id)
        except (ValueError, TypeError):
            return False, f"Invalid tag ID for {date_str}: must be an integer or None"
        
        if tag_id_int not in tag_ids:
            return False, f"Tag ID {tag_id_int} for {date_str} does not belong to this team"
    
    return True, None


def validate_tag_id(tag_id: Any, team: Team) -> Tuple[bool, Optional[TeamTag], Optional[str]]:
    """
    Validate TeamTag ID and check if it belongs to the team.
    
    Args:
        tag_id: Tag ID (can be int, string, or None)
        team: Team object to validate tag against
        
    Returns:
        Tuple of (is_valid, tag_object, error_message)
        - is_valid: True if tag ID is valid and belongs to team
        - tag_object: TeamTag instance or None
        - error_message: Error message or None
    """
    if tag_id is None:
        return True, None, None  # None is allowed (cleared tag)
    
    # Convert to int
    try:
        tag_id_int = int(tag_id)
    except (ValueError, TypeError):
        return False, None, "tag_id must be a valid integer or None"
    
    # Validate range
    if tag_id_int <= 0:
        return False, None, "tag_id must be a positive integer"
    
    # Get tag
    try:
        tag = TeamTag.objects.get(id=tag_id_int, team=team)
        return True, tag, None
    except TeamTag.DoesNotExist:
        return False, None, f"Tag ID {tag_id_int} does not belong to this team"


def validate_numeric_range(value: Any, min_value: int, max_value: int, param_name: str = 'value') -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validate a numeric value is within a specified range.
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        param_name: Name of the parameter for error messages
        
    Returns:
        Tuple of (is_valid, parsed_value, error_message)
        - is_valid: True if value is valid
        - parsed_value: Parsed integer or None
        - error_message: Error message or None
    """
    if value is None:
        return False, None, f"{param_name} is required"
    
    try:
        parsed_value = int(value)
    except (ValueError, TypeError):
        return False, None, f"{param_name} must be a valid integer"
    
    if parsed_value < min_value or parsed_value > max_value:
        return False, None, f"{param_name} must be between {min_value} and {max_value}"
    
    return True, parsed_value, None

