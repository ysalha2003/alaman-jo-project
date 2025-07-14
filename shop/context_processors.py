from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q
from .utils import get_or_create_cart
from .models import Category, Product
import logging

logger = logging.getLogger(__name__)


def cart_context(request):
    """Enhanced cart context with better error handling"""
    try:
        cart = get_or_create_cart(request)
        cart_items = cart.items.select_related('product').prefetch_related('product__images')[:5]  # Limit for performance
        
        return {
            'cart': cart,
            'cart_items': cart_items,
            'cart_total_items': cart.total_items,
            'cart_total_price': cart.total_price,
            'cart_item_count': cart.total_items,  # Alternative naming
        }
    except Exception as e:
        logger.error(f"Error in cart_context: {e}")
        return {
            'cart': None,
            'cart_items': [],
            'cart_total_items': 0,
            'cart_total_price': 0,
            'cart_item_count': 0,
        }


def shop_context(request):
    """Enhanced shop-wide context with caching"""
    cache_key = 'shop_categories_nav'
    categories = cache.get(cache_key)
    
    if not categories:
        try:
            # Use a different name for the annotation to avoid conflict with the property
            categories = Category.objects.filter(
                is_active=True
            ).annotate(
                active_products_count=Count('products', filter=Q(products__is_active=True))
            ).order_by('sort_order')[:8]  # Limit to 8 for navigation
            
            # Cache for 1 hour
            cache.set(cache_key, categories, 60 * 60)
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            categories = []
    
    # Get featured categories for mega menu
    featured_categories = categories[:6] if categories else []
    
    return {
        'shop_categories': categories,
        'featured_categories': featured_categories,
    }


def global_shop_settings(request):
    """Enhanced shop settings with better organization"""
    try:
        # Try to import and get shop settings
        from .models import ShopSetting
        shop_settings = ShopSetting.load()
        business_hours = shop_settings.business_hours.all().order_by('weekday') if shop_settings else []
        
        # Get current business status
        current_status = 'closed'
        if business_hours:
            from django.utils import timezone
            now = timezone.localtime()
            today_hours = business_hours.filter(weekday=now.isoweekday()).first()
            if today_hours and today_hours.is_open_now:
                current_status = 'open'
        
        # Company information with fallbacks
        company_info = {
            'name': getattr(shop_settings, 'business_name', None) or getattr(settings, 'COMPANY_NAME', 'Alamana-jo'),
            'email': getattr(shop_settings, 'email', None) or getattr(settings, 'COMPANY_EMAIL', 'alamanajo@gmail.com'),
            'phone': getattr(shop_settings, 'phone', None) or getattr(settings, 'COMPANY_PHONE', '+32 499 89 02 37'),
            'address': getattr(shop_settings, 'full_address', None) or getattr(settings, 'COMPANY_ADDRESS', 'Quellinstraat 45, 2018 Antwerpen, Belgium'),
            'google_maps_url': getattr(shop_settings, 'google_maps_url', None) or 'https://maps.google.com/?q=Quellinstraat+45,+2018+Antwerpen,+Belgium',
        }
        
        # E-commerce settings
        ecommerce_settings = {
            'currency': getattr(shop_settings, 'currency', 'EUR'),
            'currency_symbol': getattr(shop_settings, 'currency_symbol', '€'),
            'tax_rate': float(getattr(shop_settings, 'tax_rate', 0.21)),
            'free_shipping_threshold': getattr(shop_settings, 'free_shipping_threshold', 100.00),
            'default_shipping_cost': getattr(shop_settings, 'default_shipping_cost', 15.00),
        }
        
        return {
            'shop_settings': shop_settings,
            'business_hours': business_hours,
            'current_business_status': current_status,
            'company_info': company_info,
            'ecommerce_settings': ecommerce_settings,
            # Legacy support
            'COMPANY_NAME': company_info['name'],
            'COMPANY_ADDRESS': company_info['address'],
            'COMPANY_PHONE': company_info['phone'],
            'COMPANY_EMAIL': company_info['email'],
        }
        
    except Exception as e:
        logger.error(f"Error in global_shop_settings: {e}")
        
        # Fallback to settings.py values
        return {
            'shop_settings': None,
            'business_hours': [],
            'current_business_status': 'unknown',
            'company_info': {
                'name': getattr(settings, 'COMPANY_NAME', 'Alamana-jo'),
                'email': getattr(settings, 'COMPANY_EMAIL', 'alamanajo@gmail.com'),
                'phone': getattr(settings, 'COMPANY_PHONE', '+32 499 89 02 37'),
                'address': getattr(settings, 'COMPANY_ADDRESS', 'Quellinstraat 45, 2018 Antwerpen, Belgium'),
                'google_maps_url': 'https://maps.google.com/?q=Quellinstraat+45,+2018+Antwerpen,+Belgium',
            },
            'ecommerce_settings': {
                'currency': 'EUR',
                'currency_symbol': '€',
                'tax_rate': 0.21,
                'free_shipping_threshold': 100.00,
                'default_shipping_cost': 15.00,
            },
            'COMPANY_NAME': getattr(settings, 'COMPANY_NAME', 'Alamana-jo'),
            'COMPANY_ADDRESS': getattr(settings, 'COMPANY_ADDRESS', 'Quellinstraat 45, 2018 Antwerpen, Belgium'),
            'COMPANY_PHONE': getattr(settings, 'COMPANY_PHONE', '+32 499 89 02 37'),
            'COMPANY_EMAIL': getattr(settings, 'COMPANY_EMAIL', 'alamanajo@gmail.com'),
        }


def user_context(request):
    """User-specific context for better personalization"""
    context = {}
    
    if request.user.is_authenticated:
        try:
            # Get user's recent activity
            from .models import Order, Wishlist, MaintenanceQuote
            
            # Recent orders
            recent_orders = Order.objects.filter(
                user=request.user
            ).order_by('-created_at')[:3]
            
            # Wishlist count
            wishlist_count = Wishlist.objects.filter(user=request.user).count()
            
            # Pending quotes
            pending_quotes = MaintenanceQuote.objects.filter(
                user=request.user,
                status__in=['pending', 'reviewed']
            ).count()
            
            context.update({
                'user_recent_orders': recent_orders,
                'user_wishlist_count': wishlist_count,
                'user_pending_quotes': pending_quotes,
                'has_recent_activity': recent_orders.exists() or wishlist_count > 0 or pending_quotes > 0,
            })
            
        except Exception as e:
            logger.error(f"Error in user_context: {e}")
            context.update({
                'user_recent_orders': [],
                'user_wishlist_count': 0,
                'user_pending_quotes': 0,
                'has_recent_activity': False,
            })
    
    return context


def mobile_context(request):
    """Mobile-specific context"""
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    is_mobile = any(device in user_agent.lower() for device in [
        'mobile', 'android', 'iphone', 'ipad', 'tablet'
    ])
    
    is_touch_device = 'touch' in user_agent.lower() or is_mobile
    
    return {
        'is_mobile_device': is_mobile,
        'is_touch_device': is_touch_device,
        'mobile_optimized': is_mobile,  # Can be used in templates
    }


def performance_context(request):
    """Performance and analytics context"""
    return {
        'enable_analytics': not settings.DEBUG,
        'enable_compression': not settings.DEBUG,
        'cache_version': getattr(settings, 'CACHE_VERSION', 1),
    }
