# Fixed middleware.py for projects app

from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

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

def get_user_agent(request):
    """
    Get the user agent string from Django request object
    """
    return request.META.get('HTTP_USER_AGENT', '')

class SessionTrackingMiddleware(MiddlewareMixin):
    """Enhanced session tracking middleware with Flask-like functionality"""

    def process_request(self, request):
        if request.user.is_authenticated:
            ip = get_client_ip(request)
            user_agent = get_user_agent(request)
            session_key = request.session.session_key

            # Update user tracking info (from Flask app functionality)
            try:
                # Check if the user has the new fields before updating
                user = User.objects.get(id=request.user.id)
                update_fields = {}
                
                # Only update fields that exist
                if hasattr(user, 'last_login_ip'):
                    update_fields['last_login_ip'] = ip
                if hasattr(user, 'last_user_agent'):
                    update_fields['last_user_agent'] = user_agent
                if hasattr(user, 'is_active_session'):
                    update_fields['is_active_session'] = True
                
                if update_fields:
                    User.objects.filter(id=request.user.id).update(**update_fields)
                    
                # Increment login count if field exists
                if hasattr(user, 'login_count'):
                    User.objects.filter(id=request.user.id).update(
                        login_count=models.F('login_count') + 1
                    )
                    
            except Exception as e:
                logger.error(f"Failed to update user tracking info: {e}")

            # Create or update session record if UserSession model exists
            if session_key:
                try:
                    from .models import UserSession
                    session, created = UserSession.objects.get_or_create(
                        user=request.user,
                        session_key=session_key,
                        defaults={
                            'ip_address': ip,
                            'user_agent': user_agent,
                            'is_active': True,
                            'last_activity': timezone.now()
                        }
                    )
                    
                    if not created:
                        # Update existing session
                        session.last_activity = timezone.now()
                        session.is_active = True
                        if session.ip_address != ip:
                            session.ip_address = ip
                        if session.user_agent != user_agent:
                            session.user_agent = user_agent
                        session.save(update_fields=['last_activity', 'is_active', 'ip_address', 'user_agent'])
                
                except ImportError:
                    # UserSession model doesn't exist yet, skip this part
                    pass
                except Exception as e:
                    logger.error(f"Failed to create/update session record: {e}")

    def process_response(self, request, response):
        # Mark sessions as inactive when user logs out
        if hasattr(request, 'user') and not request.user.is_authenticated:
            session_key = request.session.session_key
            if session_key:
                try:
                    from .models import UserSession
                    UserSession.objects.filter(
                        session_key=session_key,
                        is_active=True
                    ).update(
                        is_active=False,
                        logout_time=timezone.now()
                    )
                except ImportError:
                    # UserSession model doesn't exist yet, skip this part
                    pass
                except Exception as e:
                    logger.error(f"Failed to mark session as inactive: {e}")
        
        return response


class UserActivityTrackingMiddleware(MiddlewareMixin):
    """Track user activity for analytics"""
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # Update last seen timestamp
            try:
                User.objects.filter(id=request.user.id).update(
                    last_login=timezone.now()
                )
            except Exception as e:
                logger.error(f"Failed to update user last seen: {e}")


class SecurityMiddleware(MiddlewareMixin):
    """Enhanced security middleware"""
    
    def process_request(self, request):
        # Log suspicious activities
        ip = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        # Check for suspicious patterns (you can customize this)
        suspicious_patterns = [
            'bot', 'crawler', 'spider', 'scraper'
        ]
        
        if any(pattern in user_agent.lower() for pattern in suspicious_patterns):
            logger.warning(f"Suspicious user agent detected: {user_agent} from IP: {ip}")
        
        # You can add more security checks here
        return None