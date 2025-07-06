# utils.py for projects app

from datetime import datetime
from django.utils import timezone

def get_client_ip(request):
    """
    Get the client's IP address from Django request object
    """
    # Check the X-Forwarded-For header first (it can contain multiple IP addresses, take the first one)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    # Fallback to the X-Real-IP header
    elif request.META.get('HTTP_X_REAL_IP'):
        ip = request.META.get('HTTP_X_REAL_IP')
    # If neither header is present, use the remote address directly from the request
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def calculate_elapsed_time(start_date):
    """
    Calculate elapsed time from a start date to now
    Returns formatted string like "1y:30d:12:34:56"
    """
    if not start_date:
        return "N/A"
    
    try:
        # If start_date is a string, try to parse it
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        
        # Make sure we're working with timezone-aware datetime
        if timezone.is_naive(start_date):
            start_date = timezone.make_aware(start_date)
        
        # Get the current date and time
        now = timezone.now()

        # Calculate the difference between now and the start date
        delta = now - start_date

        # Extract total days
        total_days = delta.days

        # Calculate years, remaining days, hours, minutes, and seconds
        years = total_days // 365
        days = total_days % 365
        seconds = delta.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60

        # Format the elapsed time as a string
        elapsed_time_parts = []
        if years > 0:
            elapsed_time_parts.append(f"{years}y")
        if days > 0:
            elapsed_time_parts.append(f"{days}d")
        elapsed_time_parts.append(f"{hours:02}:{minutes:02}:{remaining_seconds:02}")

        elapsed_time_str = ':'.join(elapsed_time_parts)
        return elapsed_time_str

    except (ValueError, TypeError) as e:
        return "Invalid date"

def calculate_elapsed_time_ago(start_date):
    """
    Calculate elapsed time from a start date to now
    Returns human-readable string like "2 hours ago"
    """
    if not start_date:
        return "N/A"
    
    try:
        # If start_date is a string, try to parse it
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        
        # Make sure we're working with timezone-aware datetime
        if timezone.is_naive(start_date):
            start_date = timezone.make_aware(start_date)

        # Get the current date and time
        now = timezone.now()

        # Calculate the difference between now and the start date
        delta = now - start_date

        # Extract total seconds
        total_seconds = int(delta.total_seconds())
        
        # Calculate time components
        years = total_seconds // (365 * 24 * 3600)
        days = total_seconds // (24 * 3600)
        hours = total_seconds // 3600
        minutes = total_seconds // 60
        seconds = total_seconds

        if years > 0:
            return f"{years} year{'s' if years != 1 else ''} ago"
        elif days > 0:
            return f"{days} day{'s' if days != 1 else ''} ago"
        elif hours > 0:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif minutes > 0:
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return f"{seconds} second{'s' if seconds != 1 else ''} ago"

    except (ValueError, TypeError):
        return "none"

def get_user_agent(request):
    """
    Get the user agent string from Django request object
    """
    return request.META.get('HTTP_USER_AGENT', '')

def format_user_agent(user_agent, max_length=80):
    """
    Format user agent string to a specified maximum length
    """
    if not user_agent:
        return "Unknown"
    
    if len(user_agent) > max_length:
        return user_agent[:max_length-3] + "..."
    
    return user_agent