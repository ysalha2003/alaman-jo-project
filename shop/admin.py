from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.decorators import display
from .models import (
    Category, Product, ProductImage, ProductSpecification,
    Cart, CartItem, Order, OrderItem, Review, Wishlist, 
    MaintenanceQuote, ContactMessage, MaintenancePhoto,
    ShopSetting, BusinessHour
)


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image_preview', 'image', 'alt_text', 'is_primary', 'sort_order']
    readonly_fields = ['image_preview']
    ordering = ['sort_order']
    
    @display(description="Preview")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="80" height="80" style="object-fit: cover; border-radius: 8px;" />',
                obj.image.url
            )
        return "No Image"


class ProductSpecificationInline(TabularInline):
    model = ProductSpecification
    extra = 1
    fields = ['name', 'value', 'sort_order']
    ordering = ['sort_order']


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name', 'slug', 'product_count', 'is_active', 'sort_order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['sort_order', 'name']
    list_editable = ['sort_order', 'is_active']
    
    @display(description="Products")
    def product_count(self, obj):
        count = obj.products.filter(is_active=True).count()
        if count > 0:
            url = reverse('admin:shop_product_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}" class="text-blue-600 hover:text-blue-800">{} products</a>', url, count)
        return format_html('<span class="text-gray-500">0 products</span>')


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    inlines = [ProductImageInline, ProductSpecificationInline]
    list_display = [
        'product_name', 'brand', 'category', 'product_type_display', 
        'price_display', 'stock_status', 'is_featured', 'is_active'
    ]
    list_filter = [
        'product_type', 'vehicle_compatibility', 'category', 'brand', 
        'is_featured', 'is_bestseller', 'is_new_arrival', 'is_active', 
        'availability_status', 'created_at'
    ]
    search_fields = ['name', 'brand', 'sku', 'description', 'model_number']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_featured', 'is_active']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'brand', 'model_number', 'category', 'product_type', 'vehicle_compatibility')
        }),
        ('Descriptions', {
            'fields': ('short_description', 'description'),
            'classes': ('collapse',)
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'compare_price', 'cost_price', 'sku', 'stock_quantity', 'low_stock_threshold', 'availability_status')
        }),
        ('Technical Specifications', {
            'fields': ('weight', 'dimensions', 'material', 'color', 'compatibility_notes'),
            'classes': ('collapse',)
        }),
        ('Marketing', {
            'fields': ('is_featured', 'is_bestseller', 'is_new_arrival'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Status & Timestamps', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'mark_as_featured', 'remove_featured', 'mark_as_bestseller', 
        'activate_products', 'deactivate_products'
    ]
    
    @display(description="Product", ordering="name")
    def product_name(self, obj):
        return f"{obj.brand} {obj.name}"
    
    @display(description="Type", ordering="product_type")
    def product_type_display(self, obj):
        return obj.get_product_type_display()
    
    @display(description="Price")
    def price_display(self, obj):
        if obj.is_on_sale:
            return format_html(
                '<div class="space-y-1">'
                '<div class="text-red-600 font-bold">€{}</div>'
                '<div class="text-gray-400 line-through text-sm">€{}</div>'
                '<div class="text-xs text-green-600">{} OFF</div>'
                '</div>',
                obj.price, obj.compare_price, f"{obj.sale_percentage}%"
            )
        return format_html('<div class="font-bold">€{}</div>', obj.price)
    
    @display(description="Stock Status")
    def stock_status(self, obj):
        if obj.stock_quantity == 0:
            return format_html(
                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">'
                'Out of Stock'
                '</span>'
            )
        elif obj.is_low_stock:
            return format_html(
                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">'
                'Low Stock ({})'
                '</span>',
                obj.stock_quantity
            )
        else:
            return format_html(
                '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">'
                'In Stock ({})'
                '</span>',
                obj.stock_quantity
            )
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} products marked as featured.')
    mark_as_featured.short_description = "Mark as featured"
    
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} products removed from featured.')
    remove_featured.short_description = "Remove from featured"
    
    def mark_as_bestseller(self, request, queryset):
        updated = queryset.update(is_bestseller=True)
        self.message_user(request, f'{updated} products marked as bestseller.')
    mark_as_bestseller.short_description = "Mark as bestseller"
    
    def activate_products(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} products activated.')
    activate_products.short_description = "Activate selected products"
    
    def deactivate_products(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} products deactivated.')
    deactivate_products.short_description = "Deactivate selected products"


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_name', 'product_sku', 'quantity', 'unit_price', 'total_price']
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    inlines = [OrderItemInline]
    list_display = [
        'order_number', 'customer_info', 'status_badge', 'payment_status_badge',
        'total_amount', 'created_at'
    ]
    list_filter = ['status', 'payment_status', 'created_at', 'shipping_country']
    search_fields = ['order_number', 'email', 'first_name', 'last_name', 'user__username']
    readonly_fields = [
        'order_number', 'created_at', 'updated_at', 
        'subtotal', 'shipping_cost', 'tax_amount', 'total_amount'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'payment_status', 'created_at', 'updated_at')
        }),
        ('Customer Information', {
            'fields': ('email', 'first_name', 'last_name', 'phone')
        }),
        ('Shipping Address', {
            'fields': (
                'shipping_address_line1', 'shipping_address_line2',
                'shipping_city', 'shipping_state', 'shipping_postal_code', 'shipping_country'
            )
        }),
        ('Billing Address', {
            'fields': (
                'billing_same_as_shipping',
                'billing_address_line1', 'billing_address_line2',
                'billing_city', 'billing_state', 'billing_postal_code', 'billing_country'
            ),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('subtotal', 'shipping_cost', 'tax_amount', 'total_amount')
        }),
        ('Payment & Fulfillment', {
            'fields': ('payment_method', 'payment_intent_id', 'tracking_number', 'tracking_url', 'notes'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_paid', 'mark_as_processing', 'mark_as_shipped', 'mark_as_delivered']
    
    @display(description="Customer")
    def customer_info(self, obj):
        name = f"{obj.first_name} {obj.last_name}"
        if obj.user:
            return format_html(
                '<div class="space-y-1">'
                '<div class="font-medium">{}</div>'
                '<div class="text-sm text-gray-600">{}</div>'
                '</div>',
                name, obj.email
            )
        return format_html(
            '<div class="space-y-1">'
            '<div class="font-medium">{}</div>'
            '<div class="text-sm text-gray-600">{}</div>'
            '<div class="text-xs text-gray-500">Guest</div>'
            '</div>',
            name, obj.email
        )
    
    @display(description="Status")
    def status_badge(self, obj):
        colors = {
            'pending': 'bg-yellow-100 text-yellow-800',
            'paid': 'bg-blue-100 text-blue-800',
            'processing': 'bg-purple-100 text-purple-800',
            'shipped': 'bg-indigo-100 text-indigo-800',
            'delivered': 'bg-green-100 text-green-800',
            'cancelled': 'bg-red-100 text-red-800',
            'refunded': 'bg-gray-100 text-gray-800',
        }
        color = colors.get(obj.status, 'bg-gray-100 text-gray-800')
        return format_html(
            '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {}">{}</span>',
            color, obj.get_status_display()
        )
    
    @display(description="Payment")
    def payment_status_badge(self, obj):
        colors = {
            'pending': 'bg-yellow-100 text-yellow-800',
            'processing': 'bg-blue-100 text-blue-800',
            'completed': 'bg-green-100 text-green-800',
            'failed': 'bg-red-100 text-red-800',
            'cancelled': 'bg-gray-100 text-gray-800',
            'refunded': 'bg-purple-100 text-purple-800',
        }
        color = colors.get(obj.payment_status, 'bg-gray-100 text-gray-800')
        return format_html(
            '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {}">{}</span>',
            color, obj.get_payment_status_display()
        )
    
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status='paid', payment_status='completed')
        self.message_user(request, f'{updated} orders marked as paid.')
    mark_as_paid.short_description = "Mark as paid"
    
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(status='processing')
        self.message_user(request, f'{updated} orders marked as processing.')
    mark_as_processing.short_description = "Mark as processing"
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(status='shipped', shipped_at=timezone.now())
        self.message_user(request, f'{updated} orders marked as shipped.')
    mark_as_shipped.short_description = "Mark as shipped"
    
    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(status='delivered', delivered_at=timezone.now())
        self.message_user(request, f'{updated} orders marked as delivered.')
    mark_as_delivered.short_description = "Mark as delivered"


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ['product_info', 'user_info', 'rating_stars', 'title', 'is_verified_purchase', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_verified_purchase', 'is_approved', 'created_at']
    search_fields = ['product__name', 'user__username', 'title', 'comment']
    readonly_fields = ['is_verified_purchase', 'created_at', 'helpful_count']
    list_editable = ['is_approved']
    
    fieldsets = (
        ('Review Information', {
            'fields': ('product', 'user', 'rating', 'title', 'comment')
        }),
        ('Status', {
            'fields': ('is_verified_purchase', 'is_approved', 'helpful_count', 'created_at')
        }),
    )
    
    actions = ['approve_reviews', 'unapprove_reviews']
    
    @display(description="Product")
    def product_info(self, obj):
        return obj.product.name
    
    @display(description="User")
    def user_info(self, obj):
        return obj.user.username
    
    @display(description="Rating")
    def rating_stars(self, obj):
        stars = '⭐' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span class="text-yellow-500 text-lg">{}</span>', stars)
    
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} reviews approved.')
    approve_reviews.short_description = "Approve selected reviews"
    
    def unapprove_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} reviews unapproved.')
    unapprove_reviews.short_description = "Unapprove selected reviews"


class MaintenancePhotoInline(TabularInline):
    model = MaintenancePhoto
    extra = 0
    fields = ['image_preview', 'image', 'comment', 'uploaded_at']
    readonly_fields = ['image_preview', 'uploaded_at']

    @display(description="Preview")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 8px;" />',
                obj.image.url
            )
        return "No Image"


@admin.register(MaintenanceQuote)
class MaintenanceQuoteAdmin(ModelAdmin):
    inlines = [MaintenancePhotoInline]
    list_display = ['quote_info', 'customer_info', 'vehicle_info', 'status_badge', 'urgency_badge', 'quoted_price', 'created_at']
    list_filter = ['status', 'vehicle_type', 'urgency', 'service_location', 'created_at']
    search_fields = ['full_name', 'email', 'phone', 'vehicle_brand', 'problem_description']
    readonly_fields = ['created_at', 'updated_at', 'days_since_created']
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'full_name', 'email', 'phone')
        }),
        ('Vehicle Information', {
            'fields': ('vehicle_type', 'vehicle_brand', 'vehicle_model', 'purchase_year')
        }),
        ('Service Request', {
            'fields': ('problem_description', 'urgency', 'preferred_contact_method', 'service_location', 'customer_address')
        }),
        ('Internal Processing', {
            'fields': ('status', 'admin_notes', 'quoted_price', 'quote_notes', 'estimated_completion')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'quoted_at', 'accepted_at', 'completed_at', 'days_since_created'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_reviewed', 'mark_as_quoted', 'mark_as_completed']
    
    @display(description="Quote")
    def quote_info(self, obj):
        return format_html(
            '<div class="space-y-1">'
            '<div class="font-medium">Quote #{}</div>'
            '<div class="text-sm text-gray-600">{} days old</div>'
            '</div>',
            obj.id, obj.days_since_created
        )
    
    @display(description="Customer")
    def customer_info(self, obj):
        return format_html(
            '<div class="space-y-1">'
            '<div class="font-medium">{}</div>'
            '<div class="text-sm text-gray-600">{}</div>'
            '<div class="text-sm text-gray-600">{}</div>'
            '</div>',
            obj.full_name, obj.email, obj.phone
        )
    
    @display(description="Vehicle")
    def vehicle_info(self, obj):
        return format_html(
            '<div class="space-y-1">'
            '<div class="font-medium">{}</div>'
            '<div class="text-sm text-gray-600">{} {}</div>'
            '</div>',
            obj.get_vehicle_type_display(),
            obj.vehicle_brand, obj.vehicle_model or ''
        )
    
    @display(description="Status")
    def status_badge(self, obj):
        colors = {
            'pending': 'bg-yellow-100 text-yellow-800',
            'reviewed': 'bg-blue-100 text-blue-800',
            'quoted': 'bg-purple-100 text-purple-800',
            'accepted': 'bg-green-100 text-green-800',
            'in_progress': 'bg-indigo-100 text-indigo-800',
            'completed': 'bg-green-100 text-green-800',
            'cancelled': 'bg-red-100 text-red-800',
            'expired': 'bg-gray-100 text-gray-800',
        }
        color = colors.get(obj.status, 'bg-gray-100 text-gray-800')
        return format_html(
            '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {}">{}</span>',
            color, obj.get_status_display()
        )
    
    @display(description="Urgency")
    def urgency_badge(self, obj):
        colors = {
            'low': 'bg-gray-100 text-gray-800',
            'medium': 'bg-yellow-100 text-yellow-800',
            'high': 'bg-orange-100 text-orange-800',
            'emergency': 'bg-red-100 text-red-800',
        }
        color = colors.get(obj.urgency, 'bg-gray-100 text-gray-800')
        return format_html(
            '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {}">{}</span>',
            color, obj.get_urgency_display()
        )
    
    def mark_as_reviewed(self, request, queryset):
        updated = queryset.update(status='reviewed')
        self.message_user(request, f'{updated} quotes marked as reviewed.')
    mark_as_reviewed.short_description = "Mark as reviewed"
    
    def mark_as_quoted(self, request, queryset):
        updated = queryset.update(status='quoted', quoted_at=timezone.now())
        self.message_user(request, f'{updated} quotes marked as quoted.')
    mark_as_quoted.short_description = "Mark as quoted"
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f'{updated} quotes marked as completed.')
    mark_as_completed.short_description = "Mark as completed"


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = ['name', 'subject_badge', 'priority_badge', 'status_badge', 'assigned_to', 'created_at']
    list_filter = ['status', 'subject', 'priority', 'created_at']
    search_fields = ['name', 'email', 'phone', 'message', 'order_number']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['assigned_to']
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Message Details', {
            'fields': ('subject', 'priority', 'order_number', 'message')
        }),
        ('Management', {
            'fields': ('status', 'assigned_to', 'admin_notes', 'resolved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_in_progress', 'mark_as_resolved', 'mark_as_closed']
    
    @display(description="Subject")
    def subject_badge(self, obj):
        return format_html(
            '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">{}</span>',
            obj.get_subject_display()
        )
    
    @display(description="Priority")
    def priority_badge(self, obj):
        colors = {
            'low': 'bg-gray-100 text-gray-800',
            'normal': 'bg-blue-100 text-blue-800',
            'high': 'bg-orange-100 text-orange-800',
            'urgent': 'bg-red-100 text-red-800',
        }
        color = colors.get(obj.priority, 'bg-gray-100 text-gray-800')
        return format_html(
            '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {}">{}</span>',
            color, obj.get_priority_display()
        )
    
    @display(description="Status")
    def status_badge(self, obj):
        colors = {
            'new': 'bg-yellow-100 text-yellow-800',
            'in_progress': 'bg-blue-100 text-blue-800',
            'resolved': 'bg-green-100 text-green-800',
            'closed': 'bg-gray-100 text-gray-800',
        }
        color = colors.get(obj.status, 'bg-gray-100 text-gray-800')
        return format_html(
            '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {}">{}</span>',
            color, obj.get_status_display()
        )
    
    def mark_as_in_progress(self, request, queryset):
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} messages marked as in progress.')
    mark_as_in_progress.short_description = "Mark as in progress"
    
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, f'{updated} messages marked as resolved.')
    mark_as_resolved.short_description = "Mark as resolved"
    
    def mark_as_closed(self, request, queryset):
        updated = queryset.update(status='closed')
        self.message_user(request, f'{updated} messages marked as closed.')
    mark_as_closed.short_description = "Mark as closed"


class BusinessHourInline(TabularInline):
    model = BusinessHour
    extra = 0
    max_num = 7
    fields = ['get_weekday_display', 'open_time', 'close_time', 'is_closed', 'break_start', 'break_end']
    readonly_fields = ['get_weekday_display']

    def get_weekday_display(self, obj):
        return obj.get_weekday_display()
    get_weekday_display.short_description = 'Day'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ShopSetting)
class ShopSettingAdmin(ModelAdmin):
    inlines = [BusinessHourInline]
    
    fieldsets = (
        ('Site Notifications', {
            'fields': ('is_notification_active', 'site_notification'),
            'description': 'Display banners for important announcements'
        }),
        ('Business Information', {
            'fields': ('business_name', 'business_description', 'email', 'phone', 'emergency_contact')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'postal_code', 'country')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'instagram_url', 'twitter_url'),
            'classes': ('collapse',)
        }),
        ('E-commerce Settings', {
            'fields': ('currency', 'currency_symbol', 'tax_rate', 'free_shipping_threshold', 'default_shipping_cost')
        }),
        ('Service Settings', {
            'fields': ('maintenance_booking_enabled',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        return not ShopSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CartItem)
class CartItemAdmin(ModelAdmin):
    list_display = ['cart_owner', 'product', 'quantity', 'total_price', 'added_at']
    list_filter = ['added_at', 'cart__user']
    search_fields = ['product__name', 'cart__user__username']
    
    def cart_owner(self, obj):
        if obj.cart.user:
            return obj.cart.user.username
        return f"Anonymous ({obj.cart.session_key[:8]}...)"


@admin.register(Wishlist)
class WishlistAdmin(ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'product__name']

@admin.register(MaintenancePhoto)
class MaintenancePhotoAdmin(ModelAdmin):
    list_display = ('quote_link', 'image_preview', 'comment', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('quote__full_name', 'quote__id', 'comment')
    raw_id_fields = ('quote',)

    @display(description="Image")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 8px;" />',
                obj.image.url
            )
        return "No Image"

    @display(description="Quote", ordering="quote")
    def quote_link(self, obj):
        link = reverse("admin:shop_maintenancequote_change", args=[obj.quote.id])
        return format_html('<a href="{}">Quote #{}</a>', link, obj.quote.id)
