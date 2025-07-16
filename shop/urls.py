from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    # Home and main pages
    path('', views.shop_home, name='home'),
    
    # Product pages
    path('products/', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    
    # AJAX endpoints
    path('product/quick-view/<int:product_id>/', views.product_quick_view, name='product_quick_view'),
    
    # Cart functionality
    path('cart/', views.cart_detail, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    
    # Checkout and orders
    path('checkout/', views.checkout, name='checkout'),
    path('payment/<str:order_number>/', views.payment, name='payment'),
    path('order/success/<str:order_number>/', views.order_success, name='order_success'),
    path('orders/', views.order_history, name='order_history'),
    path('order/<str:order_number>/', views.order_detail, name='order_detail'),
    
    # User features (require login)
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/toggle/', views.add_to_wishlist, name='add_to_wishlist'),
    
    # Maintenance services
    path('maintenance/', views.maintenance_quote_request, name='maintenance_quote'),
    path('maintenance/success/', views.maintenance_quote_success, name='maintenance_quote_success'),
    path('maintenance/quotes/', views.maintenance_quotes_list, name='maintenance_quotes_list'),
    
    # Contact
    path('contact/', views.contact_form, name='contact'),
    path('contact/success/', views.contact_success, name='contact_success'),
]
