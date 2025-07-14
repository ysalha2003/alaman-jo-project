from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from decimal import Decimal
import uuid
import os

User = get_user_model()

def validate_image_size(image):
    """Validate image file size (max 5MB)"""
    if image.size > 5 * 1024 * 1024:
        raise ValidationError('Image file too large (max 5MB)')

def product_image_path(instance, filename):
    """Generate upload path for product images"""
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4()}.{ext}'
    return f'products/{instance.product.slug}/{filename}'

def maintenance_photo_path(instance, filename):
    """Generate upload path for maintenance photos"""
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4()}.{ext}'
    return f'maintenance/{instance.quote.id}/{filename}'

class Category(models.Model):
    """Product categories for spare parts and accessories"""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='categories/', 
        blank=True, 
        null=True,
        validators=[validate_image_size, FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])]
    )
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Categories'
        indexes = [
            models.Index(fields=['is_active', 'sort_order']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('shop:category_detail', kwargs={'slug': self.slug})
    
    @property
    def product_count(self):
        return self.products.filter(is_active=True).count()


class Product(models.Model):
    """Enhanced product model with better validation and performance"""
    
    PRODUCT_TYPES = [
        ('brake_parts', 'Brake Parts'),
        ('drive_train', 'Drive Train'),
        ('wheels_tires', 'Wheels & Tires'),
        ('lighting', 'Lighting'),
        ('batteries', 'Batteries & Charging'),
        ('electronics', 'Electronics'),
        ('frame_parts', 'Frame Parts'),
        ('handlebars', 'Handlebars & Grips'),
        ('saddles', 'Saddles & Seatposts'),
        ('tools', 'Tools & Maintenance'),
        ('safety', 'Safety & Protection'),
        ('accessories', 'Accessories'),
    ]
    
    VEHICLE_COMPATIBILITY = [
        ('bike', 'Traditional Bike'),
        ('e_bike', 'E-Bike'),
        ('e_scooter', 'E-Scooter'),
        ('universal', 'Universal'),
    ]
    
    AVAILABILITY_STATUS = [
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('pre_order', 'Pre-Order'),
    ]
    
    # Basic Info
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField()
    short_description = models.CharField(
        max_length=300, 
        help_text="Brief product summary for cards and listings"
    )
    
    # Categorization
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name='products',
        db_index=True
    )
    product_type = models.CharField(
        max_length=20, 
        choices=PRODUCT_TYPES, 
        default='accessories',
        db_index=True
    )
    vehicle_compatibility = models.CharField(
        max_length=20, 
        choices=VEHICLE_COMPATIBILITY, 
        default='universal',
        db_index=True
    )
    brand = models.CharField(max_length=100, db_index=True)
    model_number = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Manufacturer model number"
    )
    
    # Pricing with validation
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    compare_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Original price for sale display"
    )
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Cost for margin calculation"
    )
    
    # Inventory
    stock_quantity = models.PositiveIntegerField(default=0, db_index=True)
    low_stock_threshold = models.PositiveIntegerField(
        default=5,
        help_text="Alert when stock falls below this number"
    )
    availability_status = models.CharField(
        max_length=20, 
        choices=AVAILABILITY_STATUS, 
        default='in_stock',
        db_index=True
    )
    sku = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True,
        help_text="Stock Keeping Unit"
    )
    
    # Technical Specifications
    weight = models.DecimalField(
        max_digits=6, 
        decimal_places=1, 
        blank=True, 
        null=True, 
        validators=[MinValueValidator(Decimal('0.1'))],
        help_text="Weight in grams"
    )
    dimensions = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="L x W x H in mm"
    )
    material = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Primary material"
    )
    color = models.CharField(max_length=50, blank=True)
    
    # Compatibility
    compatibility_notes = models.TextField(
        blank=True, 
        help_text="Compatible models/brands"
    )
    
    # SEO & Marketing
    meta_title = models.CharField(max_length=160, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_bestseller = models.BooleanField(default=False, db_index=True)
    is_new_arrival = models.BooleanField(default=False, db_index=True)
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product_type', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['vehicle_compatibility', 'is_active']),
            models.Index(fields=['is_featured', 'is_active']),
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['price', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.brand} {self.name}"
    
    def clean(self):
        """Custom validation"""
        if self.compare_price and self.compare_price <= self.price:
            raise ValidationError('Compare price must be higher than regular price')
        
        if self.cost_price and self.cost_price >= self.price:
            raise ValidationError('Cost price should be lower than selling price')
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.brand}-{self.name}")
        
        # Auto-update availability status based on stock
        if self.stock_quantity == 0:
            self.availability_status = 'out_of_stock'
        elif self.stock_quantity <= self.low_stock_threshold:
            self.availability_status = 'low_stock'
        else:
            self.availability_status = 'in_stock'
        
        self.clean()
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('shop:product_detail', kwargs={'slug': self.slug})
    
    @property
    def primary_image(self):
        """Get the primary image for this product"""
        return self.images.filter(is_primary=True).first() or self.images.first()
    
    @property
    def is_on_sale(self):
        return self.compare_price and self.compare_price > self.price
    
    @property
    def sale_percentage(self):
        if self.is_on_sale:
            return int(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0
    
    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.low_stock_threshold
    
    @property
    def is_in_stock(self):
        return self.stock_quantity > 0 and self.availability_status == 'in_stock'
    
    @property
    def profit_margin(self):
        if self.cost_price:
            return ((self.price - self.cost_price) / self.price) * 100
        return None


class ProductImage(models.Model):
    """Enhanced product images with better organization"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to=product_image_path,
        validators=[validate_image_size, FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])]
    )
    alt_text = models.CharField(
        max_length=200, 
        help_text="Alt text for accessibility and SEO"
    )
    is_primary = models.BooleanField(default=False, db_index=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['sort_order', 'created_at']
        indexes = [
            models.Index(fields=['product', 'is_primary']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - Image {self.sort_order}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, 
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class ProductSpecification(models.Model):
    """Enhanced product specifications"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    name = models.CharField(max_length=100, help_text="e.g., Thread Size")
    value = models.CharField(max_length=200, help_text="e.g., M6 x 1.0")
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['sort_order', 'name']
        unique_together = ['product', 'name']
    
    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}"


class Cart(models.Model):
    """Enhanced cart with better session management"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    session_key = models.CharField(max_length=40, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_key']),
            models.Index(fields=['updated_at']),
        ]
    
    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Anonymous cart {self.session_key[:8]}..."
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())
    
    @property
    def total_weight(self):
        """Calculate total weight for shipping"""
        total = 0
        for item in self.items.all():
            if item.product.weight:
                total += (item.product.weight * item.quantity)
        return total
    
    def merge_with_cart(self, other_cart):
        """Merge another cart into this one"""
        for other_item in other_cart.items.all():
            cart_item, created = self.items.get_or_create(
                product=other_item.product,
                defaults={'quantity': other_item.quantity}
            )
            if not created:
                cart_item.quantity += other_item.quantity
                cart_item.save()
        other_cart.delete()


class CartItem(models.Model):
    """Enhanced cart items with better validation"""
    
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(
        default=1, 
        validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['cart', 'product']
        indexes = [
            models.Index(fields=['cart', 'updated_at']),
        ]
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
    
    def clean(self):
        """Validate quantity against stock"""
        if self.quantity > self.product.stock_quantity:
            raise ValidationError(f'Only {self.product.stock_quantity} items available')
    
    @property
    def total_price(self):
        return self.product.price * self.quantity
    
    @property
    def total_weight(self):
        if self.product.weight:
            return self.product.weight * self.quantity
        return 0


class Order(models.Model):
    """Enhanced order model with better tracking"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    # Order Info
    order_number = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='orders', 
        blank=True, 
        null=True
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        db_index=True
    )
    
    # Customer Info
    email = models.EmailField()
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True)
    
    # Shipping Address
    shipping_address_line1 = models.CharField(max_length=200)
    shipping_address_line2 = models.CharField(max_length=200, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100, default='Belgium')
    
    # Billing Address
    billing_same_as_shipping = models.BooleanField(default=True)
    billing_address_line1 = models.CharField(max_length=200, blank=True)
    billing_address_line2 = models.CharField(max_length=200, blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=100, blank=True)
    billing_postal_code = models.CharField(max_length=20, blank=True)
    billing_country = models.CharField(max_length=100, blank=True)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment
    payment_method = models.CharField(max_length=50, blank=True)
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    payment_intent_id = models.CharField(max_length=200, blank=True)
    transaction_id = models.CharField(max_length=200, blank=True)
    
    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    tracking_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['payment_status']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number"""
        import random
        import string
        while True:
            order_number = 'ALJ-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Order.objects.filter(order_number=order_number).exists():
                return order_number
    
    def get_absolute_url(self):
        return reverse('shop:order_detail', kwargs={'order_number': self.order_number})
    
    @property
    def customer_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def shipping_address(self):
        """Get formatted shipping address"""
        lines = [self.shipping_address_line1]
        if self.shipping_address_line2:
            lines.append(self.shipping_address_line2)
        lines.append(f"{self.shipping_postal_code} {self.shipping_city}")
        lines.append(self.shipping_country)
        return '\n'.join(lines)


class OrderItem(models.Model):
    """Enhanced order items with better tracking"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Product snapshot for historical record
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=50)
    product_brand = models.CharField(max_length=100)
    product_model = models.CharField(max_length=100, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['order', 'product']),
        ]
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name} (Order {self.order.order_number})"
    
    def save(self, *args, **kwargs):
        if not self.product_name:
            self.product_name = str(self.product)
        if not self.product_sku:
            self.product_sku = self.product.sku
        if not self.product_brand:
            self.product_brand = self.product.brand
        if not self.product_model:
            self.product_model = self.product.model_number
        if not self.unit_price:
            self.unit_price = self.product.price
        super().save(*args, **kwargs)
    
    @property
    def total_price(self):
        return self.unit_price * self.quantity


class Review(models.Model):
    """Enhanced product reviews with better moderation"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False, db_index=True)
    is_approved = models.BooleanField(default=True, db_index=True)
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['product', 'user']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'is_approved']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}/5)"


class Wishlist(models.Model):
    """Enhanced user wishlist"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlists')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'product']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class MaintenanceQuote(models.Model):
    """Enhanced maintenance quotation system"""
    
    VEHICLE_TYPES = [
        ('bike', 'Traditional Bike'),
        ('e_bike', 'E-Bike'),
        ('e_scooter', 'E-Scooter'),
    ]
    
    URGENCY_LEVELS = [
        ('low', 'Not Urgent'),
        ('medium', 'Moderate'),
        ('high', 'Urgent'),
        ('emergency', 'Emergency'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('reviewed', 'Under Review'),
        ('quoted', 'Quote Sent'),
        ('accepted', 'Quote Accepted'),
        ('in_progress', 'Service In Progress'),
        ('completed', 'Service Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Quote Expired'),
    ]
    
    # Customer Info
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='maintenance_quotes')
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # Vehicle Info
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    vehicle_brand = models.CharField(max_length=100)
    vehicle_model = models.CharField(max_length=100, blank=True)
    purchase_year = models.PositiveIntegerField(blank=True, null=True)
    
    # Service Request
    problem_description = models.TextField()
    urgency = models.CharField(
        max_length=10, 
        choices=URGENCY_LEVELS, 
        default='medium',
        db_index=True
    )
    preferred_contact_method = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('both', 'Both Email and Phone')
    ], default='email')
    
    # Service Location Preference
    service_location = models.CharField(max_length=20, choices=[
        ('shop', 'Bring to Shop'),
        ('pickup', 'Pickup Service'),
        ('onsite', 'On-site Service')
    ], default='shop')
    
    customer_address = models.TextField(
        blank=True,
        help_text="Required for pickup/on-site service"
    )
    
    # Internal Processing
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        db_index=True
    )
    admin_notes = models.TextField(blank=True)
    quoted_price = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        blank=True, 
        null=True
    )
    quote_notes = models.TextField(blank=True)
    estimated_completion = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    quoted_at = models.DateTimeField(blank=True, null=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['urgency', '-created_at']),
        ]
        verbose_name = 'Maintenance Quote'
        verbose_name_plural = 'Maintenance Quotes'
    
    def __str__(self):
        return f"Quote #{self.id} - {self.full_name} ({self.vehicle_type})"
    
    @property
    def is_urgent(self):
        return self.urgency in ['high', 'emergency']
    
    @property
    def days_since_created(self):
        from django.utils import timezone
        return (timezone.now() - self.created_at).days


class MaintenancePhoto(models.Model):
    """Enhanced maintenance photos"""
    
    quote = models.ForeignKey(MaintenanceQuote, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(
        upload_to=maintenance_photo_path,
        validators=[validate_image_size, FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])]
    )
    comment = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Photo for Quote #{self.quote.id}"


class ContactMessage(models.Model):
    """Enhanced contact messages"""
    
    SUBJECT_CHOICES = [
        ('general', 'General Inquiry'),
        ('order', 'Order Issue'),
        ('product', 'Product Question'),
        ('return', 'Return/Exchange'),
        ('maintenance', 'Maintenance Service'),
        ('parts', 'Parts Availability'),
        ('quote', 'Request Quote'),
        ('complaint', 'Complaint'),
        ('suggestion', 'Suggestion'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Contact Information
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    
    # Message Details
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES)
    order_number = models.CharField(
        max_length=20, 
        blank=True,
        help_text="If related to an order"
    )
    message = models.TextField()
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        db_index=True
    )
    
    # Internal Management
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='new',
        db_index=True
    )
    admin_notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_contacts'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['priority', '-created_at']),
            models.Index(fields=['assigned_to', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_subject_display()} ({self.created_at.strftime('%Y-%m-%d')})"
    
    @property
    def is_new(self):
        return self.status == 'new'
    
    @property
    def response_time(self):
        """Time since message was created"""
        from django.utils import timezone
        return timezone.now() - self.created_at


class ShopSetting(models.Model):
    """Enhanced shop settings"""
    
    # Notifications
    site_notification = models.TextField(
        blank=True, 
        help_text="Site-wide notification banner"
    )
    is_notification_active = models.BooleanField(default=False)
    
    # Business Info
    business_name = models.CharField(max_length=200, default="Alamana-jo")
    business_description = models.TextField(
        default="Your trusted source for quality spare parts and maintenance services"
    )
    
    # Contact Info
    email = models.EmailField(default="alamanajo@gmail.com")
    phone = models.CharField(max_length=20, default="+32 499 89 02 37")
    address_line1 = models.CharField(max_length=200, default="Quellinstraat 45")
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, default="Antwerpen")
    postal_code = models.CharField(max_length=20, default="2018")
    country = models.CharField(max_length=100, default="Belgium")
    
    # Social Media
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    
    # E-commerce Settings
    currency = models.CharField(max_length=3, default='EUR')
    currency_symbol = models.CharField(max_length=5, default='€')
    tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=4, 
        default=Decimal('0.2100'),
        help_text="VAT rate (e.g., 0.21 for 21%)"
    )
    free_shipping_threshold = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('100.00')
    )
    default_shipping_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('15.00')
    )
    
    # Maintenance Settings
    maintenance_booking_enabled = models.BooleanField(default=True)
    emergency_contact = models.CharField(max_length=20, blank=True)
    
    class Meta:
        verbose_name = "Shop Settings"
        verbose_name_plural = "Shop Settings"

    def __str__(self):
        return "Shop Settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            # Create business hours for each day
            for i, day in BusinessHour.WEEKDAYS:
                BusinessHour.objects.create(setting=self, weekday=i)

    def delete(self, *args, **kwargs):
        pass  # Prevent deletion

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def full_address(self):
        """Get formatted address"""
        lines = [self.address_line1]
        if self.address_line2:
            lines.append(self.address_line2)
        lines.append(f"{self.postal_code} {self.city}")
        lines.append(self.country)
        return '\n'.join(lines)

    @property
    def google_maps_url(self):
        """Generate Google Maps URL for the address"""
        address = f"{self.address_line1}, {self.postal_code} {self.city}, {self.country}"
        import urllib.parse
        return f"https://maps.google.com/?q={urllib.parse.quote(address)}"


class BusinessHour(models.Model):
    """Enhanced business hours"""
    
    WEEKDAYS = [
        (1, "Monday"),
        (2, "Tuesday"),
        (3, "Wednesday"),
        (4, "Thursday"),
        (5, "Friday"),
        (6, "Saturday"),
        (7, "Sunday"),
    ]
    
    setting = models.ForeignKey(
        ShopSetting, 
        on_delete=models.CASCADE, 
        related_name="business_hours"
    )
    weekday = models.IntegerField(choices=WEEKDAYS, unique=True)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    break_start = models.TimeField(null=True, blank=True, help_text="Lunch break start")
    break_end = models.TimeField(null=True, blank=True, help_text="Lunch break end")

    class Meta:
        ordering = ['weekday']

    def __str__(self):
        return self.get_weekday_display()

    @property
    def is_open_now(self):
        """Check if currently open"""
        from django.utils import timezone
        now = timezone.localtime()
        
        if now.isoweekday() != self.weekday or self.is_closed:
            return False
        
        if not self.open_time or not self.close_time:
            return False
        
        current_time = now.time()
        
        # Check if in break time
        if self.break_start and self.break_end:
            if self.break_start <= current_time <= self.break_end:
                return False
        
        return self.open_time <= current_time <= self.close_time


# Signal handlers for better data integrity
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

@receiver(post_save, sender=OrderItem)
def update_product_stock(sender, instance, created, **kwargs):
    """Update product stock when order item is created"""
    if created and instance.order.status in ['paid', 'processing']:
        product = instance.product
        if product.stock_quantity >= instance.quantity:
            product.stock_quantity -= instance.quantity
            product.save()

@receiver(post_save, sender=Order)
def handle_order_status_change(sender, instance, **kwargs):
    """Handle order status changes"""
    if instance.status == 'cancelled':
        # Restore stock for cancelled orders
        for item in instance.items.all():
            item.product.stock_quantity += item.quantity
            item.product.save()
