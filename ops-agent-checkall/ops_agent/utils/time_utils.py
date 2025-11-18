"""
Time utility functions for query time range calculation
"""

import re
from datetime import datetime, timedelta
from typing import Tuple, Optional


def parse_time_range(time_range_str: str) -> timedelta:
    """
    Parse time range string into timedelta
    
    Args:
        time_range_str: Time range string (e.g., "10m", "1h", "30s", "2d")
    
    Returns:
        timedelta object
    
    Raises:
        ValueError: If time range format is invalid
    """
    match = re.match(r'^(\d+)([smhd])$', time_range_str)
    if not match:
        raise ValueError(f"Invalid time range format: {time_range_str}. Expected format like '30s', '10m', '1h', '2d'.")
    
    value, unit = match.groups()
    value = int(value)
    
    if unit == 's':
        return timedelta(seconds=value)
    elif unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    
    raise ValueError(f"Invalid time range unit: {unit}")


def calculate_time_range(time_range_str: str) -> Tuple[str, str]:
    """
    Calculate start_time and end_time based on time range string
    
    Args:
        time_range_str: Time range string (e.g., "10m" for last 10 minutes)
    
    Returns:
        Tuple of (start_time, end_time) in ISO format
    """
    delta = parse_time_range(time_range_str)
    end_time = datetime.utcnow()
    start_time = end_time - delta
    
    # Format as ISO 8601 strings
    start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    return start_time_str, end_time_str


def calculate_time_range_timestamp(time_range_str: str) -> Tuple[str, str]:
    """
    Calculate start_time and end_time as timestamps (Unix timestamp as string)
    
    Args:
        time_range_str: Time range string (e.g., "10m" for last 10 minutes)
    
    Returns:
        Tuple of (start_timestamp, end_timestamp) as string integers
    """
    delta = parse_time_range(time_range_str)
    end_time = datetime.utcnow()
    start_time = end_time - delta
    
    # Convert to Unix timestamps (seconds since epoch)
    start_timestamp = str(int(start_time.timestamp()))
    end_timestamp = str(int(end_time.timestamp()))
    
    return start_timestamp, end_timestamp


def add_time_params_to_query(
    query: dict,
    time_range_str: str,
    time_param_names: Optional[str] = None
) -> dict:
    """
    Add time parameters to a query if not already present
    
    Args:
        query: Query dictionary with 'tool_name' and 'args'
        time_range_str: Time range string (e.g., "10m")
        time_param_names: Optional comma-separated parameter names (e.g., "start_time,end_time")
    
    Returns:
        Modified query dictionary
    """
    # Create a copy to avoid modifying the original
    modified_query = query.copy()
    
    if 'args' not in modified_query:
        modified_query['args'] = {}
    
    args = modified_query['args']
    
    # Check if time parameters already exist
    time_param_keys = ['start_time', 'end_time', 'since', 'duration', 'time_range', 'from', 'to']
    has_time_params = any(key in args for key in time_param_keys)
    
    if has_time_params:
        # Time parameters already exist, don't override
        return modified_query
    
    # Determine parameter names and format based on tool type
    tool_name = modified_query.get('tool_name', '').lower()
    
    # For event queries, use timestamp format and only start_time
    if 'event' in tool_name and 'get-events' in tool_name:
        # Events use timestamp format (Unix timestamp as string)
        start_timestamp, _ = calculate_time_range_timestamp(time_range_str)
        args['start_time'] = start_timestamp
        # Don't add end_time for events, they typically only need start_time
    else:
        # For other queries, use ISO format
        start_time, end_time = calculate_time_range(time_range_str)
        
        # Determine parameter names to use
        if time_param_names:
            # Use specified parameter names
            param_names = [name.strip() for name in time_param_names.split(',')]
            if len(param_names) == 2:
                args[param_names[0]] = start_time
                args[param_names[1]] = end_time
            elif len(param_names) == 1:
                # Single parameter - use duration or since
                if param_names[0].lower() in ['duration', 'time_range']:
                    args[param_names[0]] = time_range_str
                else:
                    # Assume it's a "since" parameter
                    args[param_names[0]] = start_time
            else:
                # Fallback to default
                args['start_time'] = start_time
                args['end_time'] = end_time
        else:
            # Default: use start_time and end_time
            args['start_time'] = start_time
            args['end_time'] = end_time
    
    return modified_query

