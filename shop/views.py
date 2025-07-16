from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from django.db.models import Q, Avg, Count, Min, Max, Prefetch
from django.core.paginator import Paginator
from django.urls import reverse
from django.core.cache import cache
from django.utils import timezone
from decimal import Decimal
import json
import logging

from .models import (
    Product, Category, Cart, CartItem, Order, OrderItem,
    Review, Wishlist, ProductImage, MaintenanceQuote, ContactMessage, MaintenancePhoto
)
from .forms import ReviewForm, CheckoutForm, MaintenanceQuoteForm, ContactForm
from .utils import get_or_create_cart

logger = logging.getLogger(__name__)


@cache_page(60 * 15)  # Cache for 15 minutes
def shop_home(request):
    """Enhanced shop homepage with better performance"""
    try:
        # Use select_related and prefetch_related for better performance
        featured_products = Product.objects.filter(
            is_active=True,
            is_featured=True,
            stock_quantity__gt=0
        ).select_related('category').prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
        ).order_by('-created_at')[:8]

        new_arrivals = Product.objects.filter(
            is_active=True,
            is_new_arrival=True,
            stock_quantity__gt=0
        ).select_related('category').prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
        ).order_by('-created_at')[:6]

        bestsellers = Product.objects.filter(
            is_active=True,
            is_bestseller=True,
            stock_quantity__gt=0
        ).select_related('category').prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
        ).order_by('-created_at')[:6]

        categories = Category.objects.filter(
            is_active=True
        ).order_by('sort_order')[:8]  # Limit to top 8 categories

        # Get featured category with product count
        featured_category = categories.first()

        context = {
            'featured_products': featured_products,
            'new_arrivals': new_arrivals,
            'bestsellers': bestsellers,
            'categories': categories,
            'featured_category': featured_category,
        }

    except Exception as e:
        logger.error(f"Error in shop_home view: {e}")
        context = {
            'featured_products': [],
            'new_arrivals': [],
            'bestsellers': [],
            'categories': [],
            'featured_category': None,
        }

    return render(request, 'shop/home.html', context)


def product_list(request):
    """Enhanced product listing with better filtering and performance"""
    # Get base queryset with optimizations
    products = Product.objects.filter(
        is_active=True
    ).select_related('category').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True)),
        'reviews'
    )

    # Apply filters
    filters = {}
    category_slug = request.GET.get('category')
    product_type = request.GET.get('type')
    vehicle_compatibility = request.GET.get('vehicle')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    search = request.GET.get('search', '').strip()
    sort = request.GET.get('sort', 'newest')
    in_stock_only = request.GET.get('in_stock', 'false') == 'true'

    # Build filters dictionary for template
    current_filters = {
        'category': category_slug,
        'type': product_type,
        'vehicle': vehicle_compatibility,
        'min_price': min_price,
        'max_price': max_price,
        'search': search,
        'sort': sort,
        'in_stock_only': in_stock_only,
    }

    # Apply category filter
    if category_slug:
        try:
            category = Category.objects.get(slug=category_slug, is_active=True)
            products = products.filter(category=category)
            filters['category'] = category
        except Category.DoesNotExist:
            pass

    # Apply product type filter
    if product_type:
        products = products.filter(product_type=product_type)

    # Apply vehicle compatibility filter
    if vehicle_compatibility:
        products = products.filter(vehicle_compatibility=vehicle_compatibility)

    # Apply price filters
    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except (ValueError, TypeError):
            pass

    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except (ValueError, TypeError):
            pass

    # Apply stock filter
    if in_stock_only:
        products = products.filter(stock_quantity__gt=0)

    # Apply search filter
    if search:
        search_query = Q(name__icontains=search) | \
                      Q(brand__icontains=search) | \
                      Q(description__icontains=search) | \
                      Q(model_number__icontains=search) | \
                      Q(category__name__icontains=search)
        products = products.filter(search_query)

    # Apply sorting
    if sort == 'price_low':
        products = products.order_by('price', 'name')
    elif sort == 'price_high':
        products = products.order_by('-price', 'name')
    elif sort == 'name':
        products = products.order_by('name')
    elif sort == 'rating':
        products = products.annotate(
            avg_rating=Avg('reviews__rating')
        ).order_by('-avg_rating', '-created_at')
    elif sort == 'popularity':
        products = products.order_by('-is_bestseller', '-created_at')
    else:  # newest
        products = products.order_by('-created_at')

    # Pagination with better mobile experience (simple detection)
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad'])
    paginate_by = 8 if is_mobile else 12
    
    paginator = Paginator(products, paginate_by)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get filter options (cached for better performance)
    cache_key = 'product_filter_options'
    filter_options = cache.get(cache_key)

    if not filter_options:
        categories = Category.objects.filter(is_active=True).order_by('name')
        product_types = Product.PRODUCT_TYPES
        vehicle_types = Product.VEHICLE_COMPATIBILITY

        # Calculate price range
        price_range = Product.objects.filter(is_active=True).aggregate(
            min_price=Min('price'),
            max_price=Max('price')
        )

        filter_options = {
            'categories': categories,
            'product_types': product_types,
            'vehicle_types': vehicle_types,
            'price_range': price_range,
        }

        # Cache for 1 hour
        cache.set(cache_key, filter_options, 60 * 60)

    context = {
        'page_obj': page_obj,
        'current_filters': current_filters,
        'applied_filters': filters,
        **filter_options,
    }

    return render(request, 'shop/product_list.html', context)


def product_detail(request, slug):
    """Enhanced product detail with better related products and reviews"""
    try:
        product = get_object_or_404(
            Product.objects.select_related('category').prefetch_related(
                'images',
                'specifications',
                Prefetch('reviews', queryset=Review.objects.filter(
                    is_approved=True
                ).select_related('user').order_by('-created_at'))
            ),
            slug=slug,
            is_active=True
        )
    except Http404:
        messages.error(request, 'Product not found.')
        return redirect('shop:product_list')

    # Get related products (same category, different product)
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True,
        stock_quantity__gt=0
    ).exclude(id=product.id).select_related('category').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
    )[:4]

    # Alternative products (same type, different category)
    alternative_products = Product.objects.filter(
        product_type=product.product_type,
        is_active=True,
        stock_quantity__gt=0
    ).exclude(id=product.id).select_related('category').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
    )[:4]

    # Review statistics
    reviews = product.reviews.filter(is_approved=True)
    review_stats = reviews.aggregate(
        avg_rating=Avg('rating'),
        total_reviews=Count('id'),
        five_star=Count('id', filter=Q(rating=5)),
        four_star=Count('id', filter=Q(rating=4)),
        three_star=Count('id', filter=Q(rating=3)),
        two_star=Count('id', filter=Q(rating=2)),
        one_star=Count('id', filter=Q(rating=1)),
    )

    # Check if user can review
    can_review = False
    user_review = None
    if request.user.is_authenticated:
        # Check if user has purchased this product
        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            product=product,
            order__status__in=['delivered', 'paid']
        ).exists()

        # Check if user already reviewed
        try:
            user_review = Review.objects.get(user=request.user, product=product)
        except Review.DoesNotExist:
            can_review = has_purchased

    # Handle review form submission
    review_form = ReviewForm()
    if request.method == 'POST' and request.user.is_authenticated and can_review:
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.user = request.user
            review.product = product
            review.is_verified_purchase = True
            try:
                review.save()
                messages.success(request, 'Thank you for your review! It has been submitted.')
                return redirect('shop:product_detail', slug=slug)
            except Exception as e:
                logger.error(f"Error saving review: {e}")
                messages.error(request, 'There was an error submitting your review. Please try again.')

    # Check if product is in user's wishlist
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(
            user=request.user,
            product=product
        ).exists()

    context = {
        'product': product,
        'related_products': related_products,
        'alternative_products': alternative_products,
        'reviews': reviews[:10],  # Show first 10 reviews
        'review_stats': review_stats,
        'can_review': can_review,
        'user_review': user_review,
        'review_form': review_form,
        'in_wishlist': in_wishlist,
    }

    return render(request, 'shop/product_detail.html', context)


def category_detail(request, slug):
    """Enhanced category page with better organization"""
    try:
        category = get_object_or_404(Category, slug=slug, is_active=True)
    except Http404:
        messages.error(request, 'Category not found.')
        return redirect('shop:product_list')

    # Get products in this category
    products = Product.objects.filter(
        category=category,
        is_active=True
    ).select_related('category').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
    )

    # Apply additional filters
    product_type = request.GET.get('type')
    vehicle = request.GET.get('vehicle')
    in_stock_only = request.GET.get('in_stock', 'false') == 'true'

    if product_type:
        products = products.filter(product_type=product_type)

    if vehicle:
        products = products.filter(vehicle_compatibility=vehicle)

    if in_stock_only:
        products = products.filter(stock_quantity__gt=0)

    # Sorting
    sort = request.GET.get('sort', 'newest')
    if sort == 'price_low':
        products = products.order_by('price')
    elif sort == 'price_high':
        products = products.order_by('-price')
    elif sort == 'name':
        products = products.order_by('name')
    else:
        products = products.order_by('-created_at')

    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get category statistics
    category_stats = {
        'total_products': products.count(),
        'in_stock_products': products.filter(stock_quantity__gt=0).count(),
        'avg_price': products.aggregate(avg_price=Avg('price'))['avg_price'],
        'price_range': products.aggregate(
            min_price=Min('price'),
            max_price=Max('price')
        ),
    }

    context = {
        'category': category,
        'page_obj': page_obj,
        'category_stats': category_stats,
        'product_types': Product.PRODUCT_TYPES,
        'vehicle_types': Product.VEHICLE_COMPATIBILITY,
        'current_filters': {
            'type': product_type,
            'vehicle': vehicle,
            'sort': sort,
            'in_stock_only': in_stock_only,
        }
    }

    return render(request, 'shop/category_detail.html', context)


@require_POST
def add_to_cart(request):
    """Enhanced add to cart with better error handling and mobile optimization"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))

        # Validate inputs
        if not product_id or quantity <= 0:
            return JsonResponse({'error': 'Invalid product or quantity'}, status=400)

        if quantity > 99:  # Reasonable limit
            return JsonResponse({'error': 'Maximum quantity is 99'}, status=400)

        # Get product
        try:
            product = Product.objects.select_related('category').get(
                id=product_id,
                is_active=True
            )
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)

        # Check stock availability
        if not product.is_in_stock:
            return JsonResponse({'error': 'Product is out of stock'}, status=400)

        if quantity > product.stock_quantity:
            return JsonResponse({
                'error': f'Only {product.stock_quantity} items available'
            }, status=400)

        # Get or create cart
        cart = get_or_create_cart(request)

        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock_quantity:
                return JsonResponse({
                    'error': f'Cannot add more. Only {product.stock_quantity} items available'
                }, status=400)
            cart_item.quantity = new_quantity
            cart_item.save()

        # Log the action for analytics
        logger.info(f"Product {product.id} added to cart. User: {request.user.id if request.user.is_authenticated else 'Anonymous'}")

        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart',
            'cart_total_items': cart.total_items,
            'cart_total_price': str(cart.total_price),
            'item_quantity': cart_item.quantity,
            'item_total_price': str(cart_item.total_price),
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'Invalid quantity'}, status=400)
    except Exception as e:
        logger.error(f"Error in add_to_cart: {e}")
        return JsonResponse({'error': 'An error occurred. Please try again.'}, status=500)


def cart_detail(request):
    """Enhanced shopping cart with recommendations"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product__category').prefetch_related(
        'product__images'
    ).order_by('-added_at')

    # Calculate totals
    subtotal = cart.total_price
    free_shipping_threshold = Decimal('100.00')
    shipping_cost = Decimal('15.00') if subtotal < free_shipping_threshold else Decimal('0.00')
    tax_rate = Decimal('0.21')  # 21% VAT
    tax_amount = subtotal * tax_rate
    total_amount = subtotal + shipping_cost + tax_amount
    free_shipping_remaining = max(Decimal('0'), free_shipping_threshold - subtotal)
    free_shipping_progress = 0
    if free_shipping_threshold > 0:
        free_shipping_progress = min((subtotal / free_shipping_threshold) * 100, 100)


    # Get recommended products based on cart contents
    recommended_products = []
    if cart_items.exists():
        # Get products from same categories as cart items
        cart_categories = set(item.product.category for item in cart_items)
        recommended_products = Product.objects.filter(
            category__in=cart_categories,
            is_active=True,
            stock_quantity__gt=0
        ).exclude(
            id__in=[item.product.id for item in cart_items]
        ).select_related('category').prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
        )[:4]

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'tax_amount': tax_amount,
        'total_amount': total_amount,
        'recommended_products': recommended_products,
        'free_shipping_threshold': free_shipping_threshold,
        'free_shipping_remaining': free_shipping_remaining,
        'free_shipping_progress': free_shipping_progress,
    }

    return render(request, 'shop/cart.html', context)


@require_POST
def update_cart_item(request):
    """Enhanced cart item update with better validation"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity'))

        cart = get_or_create_cart(request)

        try:
            cart_item = CartItem.objects.select_related('product').get(
                id=item_id,
                cart=cart
            )
        except CartItem.DoesNotExist:
            return JsonResponse({'error': 'Cart item not found'}, status=404)

        # Remove item if quantity is 0 or negative
        if quantity <= 0:
            cart_item.delete()
            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart',
                'cart_total_items': cart.total_items,
                'cart_total_price': str(cart.total_price),
                'item_removed': True,
            })

        # Validate quantity
        if quantity > cart_item.product.stock_quantity:
            return JsonResponse({
                'error': f'Only {cart_item.product.stock_quantity} items available'
            }, status=400)

        if quantity > 99:
            return JsonResponse({'error': 'Maximum quantity is 99'}, status=400)

        # Update quantity
        cart_item.quantity = quantity
        cart_item.save()

        return JsonResponse({
            'success': True,
            'message': 'Cart updated',
            'item_total_price': str(cart_item.total_price),
            'cart_total_items': cart.total_items,
            'cart_total_price': str(cart.total_price),
        })

    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)
    except Exception as e:
        logger.error(f"Error in update_cart_item: {e}")
        return JsonResponse({'error': 'An error occurred'}, status=500)


@require_POST
def remove_from_cart(request):
    """Enhanced cart item removal"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')

        cart = get_or_create_cart(request)

        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            product_name = cart_item.product.name
            cart_item.delete()

            return JsonResponse({
                'success': True,
                'message': f'{product_name} removed from cart',
                'cart_total_items': cart.total_items,
                'cart_total_price': str(cart.total_price),
            })

        except CartItem.DoesNotExist:
            return JsonResponse({'error': 'Cart item not found'}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error in remove_from_cart: {e}")
        return JsonResponse({'error': 'An error occurred'}, status=500)


def checkout(request):
    """Enhanced checkout with better validation and mobile UX"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product').prefetch_related('product__images')

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('shop:cart')

    # Validate cart items (check stock availability)
    for item in cart_items:
        if not item.product.is_in_stock:
            messages.error(request, f'{item.product.name} is no longer available.')
            item.delete()
            return redirect('shop:cart')

        if item.quantity > item.product.stock_quantity:
            messages.error(request, f'Only {item.product.stock_quantity} of {item.product.name} available.')
            item.quantity = item.product.stock_quantity
            item.save()
            return redirect('shop:cart')

    # Calculate totals
    subtotal = cart.total_price
    shipping_cost = Decimal('15.00') if subtotal < Decimal('100.00') else Decimal('0.00')
    tax_rate = Decimal('0.21')
    tax_amount = subtotal * tax_rate
    total_amount = subtotal + shipping_cost + tax_amount

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                # Create order
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    email=form.cleaned_data['email'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    phone=form.cleaned_data['phone'],
                    shipping_address_line1=form.cleaned_data['shipping_address_line1'],
                    shipping_address_line2=form.cleaned_data['shipping_address_line2'],
                    shipping_city=form.cleaned_data['shipping_city'],
                    shipping_state=form.cleaned_data['shipping_state'],
                    shipping_postal_code=form.cleaned_data['shipping_postal_code'],
                    shipping_country=form.cleaned_data['shipping_country'],
                    billing_same_as_shipping=form.cleaned_data['billing_same_as_shipping'],
                    subtotal=subtotal,
                    shipping_cost=shipping_cost,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                )

                # Set billing address if different
                if not form.cleaned_data['billing_same_as_shipping']:
                    order.billing_address_line1 = form.cleaned_data['billing_address_line1']
                    order.billing_address_line2 = form.cleaned_data['billing_address_line2']
                    order.billing_city = form.cleaned_data['billing_city']
                    order.billing_state = form.cleaned_data['billing_state']
                    order.billing_postal_code = form.cleaned_data['billing_postal_code']
                    order.billing_country = form.cleaned_data['billing_country']
                    order.save()

                # Create order items
                for cart_item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        unit_price=cart_item.product.price,
                    )

                # Clear cart
                cart_items.delete()

                # Log successful order creation
                logger.info(f"Order {order.order_number} created successfully")

                # Redirect to payment
                messages.success(request, f'Order {order.order_number} created successfully!')
                return redirect('shop:payment', order_number=order.order_number)

            except Exception as e:
                logger.error(f"Error creating order: {e}")
                messages.error(request, 'There was an error processing your order. Please try again.')
    else:
        # Pre-fill form with user data
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            }
        form = CheckoutForm(initial=initial_data)

    context = {
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'tax_amount': tax_amount,
        'total_amount': total_amount,
        'free_shipping_threshold': Decimal('100.00'),
    }

    return render(request, 'shop/checkout.html', context)


@login_required
@require_POST
def add_to_wishlist(request):
    """Enhanced wishlist functionality"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)

        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )

        if created:
            return JsonResponse({
                'success': True,
                'message': f'{product.name} added to wishlist',
                'action': 'added',
                'in_wishlist': True
            })
        else:
            wishlist_item.delete()
            return JsonResponse({
                'success': True,
                'message': f'{product.name} removed from wishlist',
                'action': 'removed',
                'in_wishlist': False
            })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error in add_to_wishlist: {e}")
        return JsonResponse({'error': 'An error occurred'}, status=500)


@login_required
def wishlist(request):
    """Enhanced user wishlist with better organization"""
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related('product__category').prefetch_related(
        'product__images'
    ).order_by('-created_at')

    # Group by category for better organization
    wishlist_by_category = {}
    for item in wishlist_items:
        category = item.product.category.name
        if category not in wishlist_by_category:
            wishlist_by_category[category] = []
        wishlist_by_category[category].append(item)

    context = {
        'wishlist_items': wishlist_items,
        'wishlist_by_category': wishlist_by_category,
        'total_items': wishlist_items.count(),
    }

    return render(request, 'shop/wishlist.html', context)


@login_required
def maintenance_quote_request(request):
    """Enhanced maintenance quotation request with better mobile UX"""
    if request.method == 'POST':
        form = MaintenanceQuoteForm(request.POST)
        if form.is_valid():
            try:
                # Save the main quote object
                quote = form.save(commit=False)
                quote.user = request.user

                # Set priority based on urgency
                if quote.urgency in ['high', 'emergency']:
                    quote.priority = 'high'

                quote.save()

                # Handle photo uploads
                images = request.FILES.getlist('photos')
                comments = request.POST.getlist('photo_comments')

                for i, image in enumerate(images):
                    if image:  # Only process non-empty images
                        comment = comments[i] if i < len(comments) else ""
                        MaintenancePhoto.objects.create(
                            quote=quote,
                            image=image,
                            comment=comment
                        )

                # Log the quote request
                logger.info(f"Maintenance quote {quote.id} created by user {request.user.id}")

                messages.success(request, 'Your maintenance quote request has been submitted! We will contact you soon.')
                return redirect('shop:maintenance_quote_success')

            except Exception as e:
                logger.error(f"Error creating maintenance quote: {e}")
                messages.error(request, 'There was an error submitting your request. Please try again.')
    else:
        # Pre-fill form with user data
        initial_data = {
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip(),
            'email': request.user.email,
        }
        form = MaintenanceQuoteForm(initial=initial_data)

    context = {
        'form': form,
    }

    return render(request, 'shop/maintenance_quote.html', context)


@login_required
def maintenance_quote_success(request):
    """Maintenance quote request success page"""
    return render(request, 'shop/maintenance_quote_success.html')


@login_required
def maintenance_quotes_list(request):
    """Enhanced user's maintenance quote requests"""
    quotes = MaintenanceQuote.objects.filter(
        user=request.user
    ).prefetch_related('photos').order_by('-created_at')

    # Group quotes by status for better organization
    quotes_by_status = {}
    for quote in quotes:
        status = quote.get_status_display()
        if status not in quotes_by_status:
            quotes_by_status[status] = []
        quotes_by_status[status].append(quote)

    context = {
        'quotes': quotes,
        'quotes_by_status': quotes_by_status,
        'total_quotes': quotes.count(),
    }

    return render(request, 'shop/maintenance_quotes_list.html', context)


def contact_form(request):
    """Enhanced contact form with better categorization"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            try:
                # Determine priority based on subject
                priority = 'normal'
                subject = form.cleaned_data['subject']
                if subject in ['complaint', 'order']:
                    priority = 'high'
                elif subject == 'technical':
                    priority = 'urgent'

                ContactMessage.objects.create(
                    name=form.cleaned_data['name'],
                    email=form.cleaned_data['email'],
                    phone=form.cleaned_data['phone'],
                    subject=form.cleaned_data['subject'],
                    order_number=form.cleaned_data['order_number'],
                    message=form.cleaned_data['message'],
                    priority=priority
                )

                # Log the contact message
                logger.info(f"Contact message created: {form.cleaned_data['subject']} from {form.cleaned_data['email']}")

                messages.success(request, 'Your message has been sent! We will get back to you soon.')
                return redirect('shop:contact_success')

            except Exception as e:
                logger.error(f"Error creating contact message: {e}")
                messages.error(request, 'There was an error sending your message. Please try again.')
    else:
        # Pre-fill form with user data if authenticated
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'name': f"{request.user.first_name} {request.user.last_name}".strip(),
                'email': request.user.email,
            }
        form = ContactForm(initial=initial_data)

    context = {
        'form': form,
    }

    return render(request, 'shop/contact.html', context)


def contact_success(request):
    """Contact form success page"""
    return render(request, 'shop/contact_success.html')


@require_GET
def product_quick_view(request, product_id):
    """Quick view for product details (AJAX)"""
    try:
        product = get_object_or_404(
            Product.objects.select_related('category').prefetch_related('images'),
            id=product_id,
            is_active=True
        )

        context = {
            'product': product,
        }

        return render(request, 'shop/partials/product_quick_view.html', context)

    except Exception as e:
        logger.error(f"Error in product_quick_view: {e}")
        return JsonResponse({'error': 'Product not found'}, status=404)


@require_GET
def search_suggestions(request):
    """Search suggestions for autocomplete (AJAX)"""
    query = request.GET.get('q', '').strip()
    suggestions = []

    if len(query) >= 2:
        # Search in products
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(brand__icontains=query),
            is_active=True
        ).values_list('name', 'brand').distinct()[:5]

        for name, brand in products:
            suggestions.append({
                'type': 'product',
                'text': f"{brand} {name}",
                'url': reverse('shop:product_list') + f'?search={query}'
            })

        # Search in categories
        categories = Category.objects.filter(
            name__icontains=query,
            is_active=True
        ).values_list('name', 'slug')[:3]

        for name, slug in categories:
            suggestions.append({
                'type': 'category',
                'text': name,
                'url': reverse('shop:category_detail', kwargs={'slug': slug})
            })

    return JsonResponse({'suggestions': suggestions})


@login_required
def order_success(request, order_number):
    """Order success confirmation page"""
    try:
        order = get_object_or_404(
            Order, 
            order_number=order_number,
            user=request.user if request.user.is_authenticated else None
        )
    except Http404:
        messages.error(request, 'Order not found.')
        return redirect('shop:home')
    
    context = {
        'order': order,
    }
    
    return render(request, 'shop/order_success.html', context)


@login_required
def order_history(request):
    """User's order history page"""
    orders = Order.objects.filter(
        user=request.user
    ).prefetch_related('items__product').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
    }
    
    return render(request, 'shop/order_history.html', context)


@login_required 
def order_detail(request, order_number):
    """Detailed view of a specific order"""
    try:
        order = get_object_or_404(
            Order.objects.prefetch_related('items__product'),
            order_number=order_number,
            user=request.user
        )
    except Http404:
        messages.error(request, 'Order not found.')
        return redirect('shop:order_history')
    
    context = {
        'order': order,
    }
    
    return render(request, 'shop/order_detail.html', context)


def payment(request, order_number):
    """Payment processing page"""
    try:
        order = get_object_or_404(Order, order_number=order_number)
        
        # Check if user owns this order (if authenticated)
        if request.user.is_authenticated and order.user != request.user:
            messages.error(request, 'Order not found.')
            return redirect('shop:home')
            
    except Http404:
        messages.error(request, 'Order not found.')
        return redirect('shop:home')
    
    # If order is already paid, redirect to success
    if order.payment_status == 'completed':
        return redirect('shop:order_success', order_number=order.order_number)
    
    context = {
        'order': order,
    }
    
    return render(request, 'shop/payment.html', context)
