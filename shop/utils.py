from django.shortcuts import get_object_or_404
from decimal import Decimal
from .models import Cart, Product

def get_or_create_cart(request):
    """Get or create cart for user or session - simplified version"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Merge session cart if exists and is new user cart
        if created and hasattr(request, 'session') and request.session.session_key:
            merge_session_cart_to_user(request.session.session_key, cart)
        
        return cart
    else:
        # Anonymous user - use session
        if not request.session.session_key:
            request.session.create()
        
        cart, _ = Cart.objects.get_or_create(
            session_key=request.session.session_key,
            user=None
        )
        return cart

def merge_session_cart_to_user(session_key, user_cart):
    """Merge anonymous session cart to user cart"""
    try:
        session_cart = Cart.objects.get(session_key=session_key, user=None)
        
        # Move items from session cart to user cart
        for item in session_cart.items.all():
            user_item, created = user_cart.items.get_or_create(
                product=item.product,
                defaults={'quantity': item.quantity}
            )
            if not created:
                # Add quantities together, respecting stock limits
                new_quantity = min(
                    user_item.quantity + item.quantity,
                    item.product.stock_quantity
                )
                user_item.quantity = new_quantity
                user_item.save()
        
        # Delete the session cart
        session_cart.delete()
        
    except Cart.DoesNotExist:
        pass

def calculate_shipping_cost(subtotal, country='Belgium'):
    """Calculate shipping cost based on subtotal and country"""
    free_shipping_threshold = Decimal('100.00')
    default_shipping = Decimal('15.00')
    
    if subtotal >= free_shipping_threshold:
        return Decimal('0.00')
    
    # Different rates for different countries could be added here
    shipping_rates = {
        'Belgium': default_shipping,
        'Netherlands': Decimal('20.00'),
        'Germany': Decimal('25.00'),
        'France': Decimal('25.00'),
    }
    
    return shipping_rates.get(country, Decimal('30.00'))  # Default international rate

def calculate_tax_amount(subtotal, country='Belgium'):
    """Calculate tax amount based on country"""
    tax_rates = {
        'Belgium': Decimal('0.21'),  # 21% VAT
        'Netherlands': Decimal('0.21'),
        'Germany': Decimal('0.19'),
        'France': Decimal('0.20'),
    }
    
    tax_rate = tax_rates.get(country, Decimal('0.21'))
    return subtotal * tax_rate

def format_currency(amount, currency='EUR'):
    """Format currency for display"""
    symbols = {
        'EUR': '€',
        'USD': '$',
        'GBP': '£',
    }
    
    symbol = symbols.get(currency, '€')
    return f"{symbol}{amount:,.2f}"

def get_cart_context(request):
    """Get cart context for templates - simplified"""
    try:
        cart = get_or_create_cart(request)
        return {
            'cart': cart,
            'cart_total_items': cart.total_items,
            'cart_total_price': cart.total_price,
            'cart_shipping_cost': cart.shipping_cost,
            'cart_final_total': cart.final_total,
        }
    except:
        return {
            'cart': None,
            'cart_total_items': 0,
            'cart_total_price': Decimal('0.00'),
            'cart_shipping_cost': Decimal('0.00'),
            'cart_final_total': Decimal('0.00'),
        }

def check_stock_availability(product_id, quantity):
    """Check if requested quantity is available"""
    try:
        product = Product.objects.get(id=product_id, is_active=True)
        return {
            'available': product.stock_quantity >= quantity,
            'max_available': product.stock_quantity,
            'product': product
        }
    except Product.DoesNotExist:
        return {
            'available': False,
            'max_available': 0,
            'product': None
        }

def get_recommended_products(product, limit=4):
    """Get recommended products based on category and type"""
    return Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(
        id=product.id
    ).select_related('category').prefetch_related('images')[:limit]

def validate_cart_items(cart):
    """Validate all cart items against current stock and prices"""
    issues = []
    
    for item in cart.items.all():
        # Check if product is still active
        if not item.product.is_active:
            issues.append({
                'item': item,
                'issue': 'Product no longer available',
                'action': 'remove'
            })
            continue
            
        # Check stock availability
        if item.quantity > item.product.stock_quantity:
            issues.append({
                'item': item,
                'issue': f'Only {item.product.stock_quantity} available',
                'action': 'adjust_quantity',
                'max_quantity': item.product.stock_quantity
            })
            
        # Check if price has changed significantly (more than 10%)
        current_price = item.product.price
        cart_price = item.product.price  # This would be stored in cart in a real app
        if abs(current_price - cart_price) / cart_price > 0.1:
            issues.append({
                'item': item,
                'issue': f'Price changed from €{cart_price} to €{current_price}',
                'action': 'price_update',
                'new_price': current_price
            })
    
    return issues

def apply_discount_code(cart, discount_code):
    """Apply discount code to cart (placeholder for future implementation)"""
    # This is a placeholder for future discount functionality
    valid_codes = {
        'WELCOME10': {'type': 'percentage', 'value': 10, 'min_amount': 50},
        'FREESHIP': {'type': 'free_shipping', 'value': 0, 'min_amount': 25},
        'SAVE20': {'type': 'percentage', 'value': 20, 'min_amount': 100},
    }
    
    code = discount_code.upper()
    if code in valid_codes:
        discount = valid_codes[code]
        if cart.total_price >= discount['min_amount']:
            return {
                'valid': True,
                'discount': discount,
                'message': f'Discount "{code}" applied!'
            }
        else:
            return {
                'valid': False,
                'message': f'Minimum order of €{discount["min_amount"]} required for this code'
            }
    
    return {
        'valid': False,
        'message': 'Invalid discount code'
    }
