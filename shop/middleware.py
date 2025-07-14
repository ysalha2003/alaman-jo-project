from django.utils.deprecation import MiddlewareMixin
from .utils import get_or_create_cart


class CartMiddleware(MiddlewareMixin):
    """Middleware to ensure session and cart are available"""
    
    def process_request(self, request):
        # Ensure session is created for anonymous users
        if not request.session.session_key:
            request.session.create()
        
        # Attach cart to request for easy access
        request.cart = get_or_create_cart(request)
        
        return None
