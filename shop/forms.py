from django import forms
from django.core.validators import RegexValidator
from .models import Review, Order, MaintenanceQuote


class ReviewForm(forms.ModelForm):
    """Enhanced product review form with better mobile UX"""
    
    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment']
        widgets = {
            'rating': forms.Select(
                choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
                attrs={
                    'class': 'select select-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                    'required': True
                }
            ),
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Summarize your experience...',
                'maxlength': '200',
                'autocomplete': 'off'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none',
                'rows': 4,
                'placeholder': 'Tell us more about your experience with this product. What did you like? How was the quality?',
                'maxlength': '1000'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add character counters for mobile
        self.fields['title'].help_text = "Max 200 characters"
        self.fields['comment'].help_text = "Max 1000 characters"


class CheckoutForm(forms.Form):
    """Enhanced checkout form with better mobile experience and validation"""
    
    # Phone number validator
    phone_validator = RegexValidator(
        regex=r'^\+?[1-9]\d{1,14}$',
        message="Enter a valid phone number (e.g., +32499890237 or 0499890237)"
    )
    
    # Customer Information
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'your@email.com',
            'autocomplete': 'email',
            'inputmode': 'email'
        })
    )
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'First name',
            'autocomplete': 'given-name'
        })
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Last name',
            'autocomplete': 'family-name'
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        validators=[phone_validator],
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': '+32 499 89 02 37',
            'autocomplete': 'tel',
            'inputmode': 'tel'
        })
    )
    
    # Shipping Address
    shipping_address_line1 = forms.CharField(
        max_length=200,
        label='Street Address',
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Street address',
            'autocomplete': 'address-line1'
        })
    )
    shipping_address_line2 = forms.CharField(
        max_length=200,
        required=False,
        label='Apartment, suite, etc. (optional)',
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Apartment, suite, etc.',
            'autocomplete': 'address-line2'
        })
    )
    shipping_city = forms.CharField(
        max_length=100,
        label='City',
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'City',
            'autocomplete': 'address-level2'
        })
    )
    shipping_state = forms.CharField(
        max_length=100,
        label='State/Province',
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'State or Province',
            'autocomplete': 'address-level1'
        })
    )
    shipping_postal_code = forms.CharField(
        max_length=20,
        label='Postal Code',
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': '2018',
            'autocomplete': 'postal-code',
            'inputmode': 'numeric'
        })
    )
    shipping_country = forms.CharField(
        max_length=100,
        initial='Belgium',
        label='Country',
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full bg-gray-50 dark:bg-gray-700',
            'readonly': True,
            'autocomplete': 'country'
        })
    )
    
    # Billing Address Toggle
    billing_same_as_shipping = forms.BooleanField(
        initial=True,
        required=False,
        label='Billing address is the same as shipping address',
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox checkbox-primary',
            'onchange': 'toggleBillingAddress(this.checked)'
        })
    )
    
    # Billing Address Fields (hidden by default)
    billing_address_line1 = forms.CharField(
        max_length=200,
        required=False,
        label='Billing Street Address',
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Street address',
            'autocomplete': 'billing address-line1'
        })
    )
    billing_address_line2 = forms.CharField(
        max_length=200,
        required=False,
        label='Apartment, suite, etc.',
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Apartment, suite, etc.',
            'autocomplete': 'billing address-line2'
        })
    )
    billing_city = forms.CharField(
        max_length=100,
        required=False,
        label='City',
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'City',
            'autocomplete': 'billing address-level2'
        })
    )
    billing_state = forms.CharField(
        max_length=100,
        required=False,
        label='State/Province',
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'State or Province',
            'autocomplete': 'billing address-level1'
        })
    )
    billing_postal_code = forms.CharField(
        max_length=20,
        required=False,
        label='Postal Code',
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': '2018',
            'autocomplete': 'billing postal-code',
            'inputmode': 'numeric'
        })
    )
    billing_country = forms.CharField(
        max_length=100,
        required=False,
        initial='Belgium',
        label='Country',
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'autocomplete': 'billing country'
        })
    )
    
    # Special Instructions
    special_instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none',
            'rows': 3,
            'placeholder': 'Any special delivery instructions? (optional)',
            'maxlength': '500'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        billing_same_as_shipping = cleaned_data.get('billing_same_as_shipping')
        
        if not billing_same_as_shipping:
            # Validate billing address fields when different from shipping
            required_billing_fields = [
                'billing_address_line1', 'billing_city', 
                'billing_state', 'billing_postal_code', 'billing_country'
            ]
            
            for field in required_billing_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, 'This field is required when billing address is different.')
        
        return cleaned_data


class MaintenanceQuoteForm(forms.ModelForm):
    """Enhanced maintenance quote form with better mobile UX"""
    
    class Meta:
        model = MaintenanceQuote
        fields = [
            'full_name', 'email', 'phone', 'vehicle_type', 'vehicle_brand', 
            'vehicle_model', 'purchase_year', 'problem_description', 
            'urgency', 'preferred_contact_method', 'service_location', 'customer_address'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'placeholder': 'Your full name',
                'autocomplete': 'name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'placeholder': 'your@email.com',
                'autocomplete': 'email',
                'inputmode': 'email'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'input input-bordered w-full focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'placeholder': '+32 499 89 02 37',
                'autocomplete': 'tel',
                'inputmode': 'tel'
            }),
            'vehicle_type': forms.Select(attrs={
                'class': 'select select-bordered w-full focus:ring-2 focus:ring-purple-500 focus:border-purple-500'
            }),
            'vehicle_brand': forms.TextInput(attrs={
                'class': 'input input-bordered w-full focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'placeholder': 'e.g., Trek, Specialized, Xiaomi, Cowboy',
                'list': 'vehicle-brands'
            }),
            'vehicle_model': forms.TextInput(attrs={
                'class': 'input input-bordered w-full focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'placeholder': 'Model name (if known)'
            }),
            'purchase_year': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'placeholder': '2023',
                'min': '1990',
                'max': '2025',
                'inputmode': 'numeric'
            }),
            'problem_description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none',
                'rows': 5,
                'placeholder': 'Please describe the issue or maintenance service you need. Be as detailed as possible to help us provide an accurate quote.',
                'maxlength': '2000'
            }),
            'urgency': forms.Select(attrs={
                'class': 'select select-bordered w-full focus:ring-2 focus:ring-purple-500 focus:border-purple-500'
            }),
            'preferred_contact_method': forms.Select(attrs={
                'class': 'select select-bordered w-full focus:ring-2 focus:ring-purple-500 focus:border-purple-500'
            }),
            'service_location': forms.Select(attrs={
                'class': 'select select-bordered w-full focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'onchange': 'toggleAddressField(this.value)'
            }),
            'customer_address': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none',
                'rows': 3,
                'placeholder': 'Your address for pickup or on-site service',
                'style': 'display: none;'  # Hidden by default
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add help text for mobile users
        self.fields['problem_description'].help_text = "Max 2000 characters"
        self.fields['customer_address'].help_text = "Required for pickup and on-site service"
        
        # Make customer_address required conditionally
        if self.data.get('service_location') in ['pickup', 'onsite']:
            self.fields['customer_address'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        service_location = cleaned_data.get('service_location')
        customer_address = cleaned_data.get('customer_address')
        
        if service_location in ['pickup', 'onsite'] and not customer_address:
            self.add_error('customer_address', 'Address is required for pickup and on-site service.')
        
        return cleaned_data


class ContactForm(forms.Form):
    """Enhanced contact form with better categorization and mobile UX"""
    
    SUBJECT_CHOICES = [
        ('general', 'General Inquiry'),
        ('order', 'Order Support'),
        ('product', 'Product Question'),
        ('return', 'Return/Exchange'),
        ('maintenance', 'Maintenance Service'),
        ('parts', 'Parts Availability'),
        ('quote', 'Request Quote'),
        ('complaint', 'Complaint'),
        ('suggestion', 'Suggestion'),
        ('technical', 'Technical Support'),
        ('partnership', 'Business Partnership'),
        ('other', 'Other'),
    ]
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Your full name',
            'autocomplete': 'name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'your@email.com',
            'autocomplete': 'email',
            'inputmode': 'email'
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': '+32 499 89 02 37 (optional)',
            'autocomplete': 'tel',
            'inputmode': 'tel'
        })
    )
    subject = forms.ChoiceField(
        choices=SUBJECT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
        })
    )
    order_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'ALJ-12345678 (if applicable)',
            'pattern': 'ALJ-[A-Z0-9]{8}',
            'title': 'Order number format: ALJ-12345678'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none',
            'rows': 6,
            'placeholder': 'How can we help you? Please provide as much detail as possible.',
            'maxlength': '2000'
        })
    )
    
    # Priority field for internal use
    priority = forms.ChoiceField(
        choices=[('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')],
        initial='normal',
        required=False,
        widget=forms.HiddenInput()
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['message'].help_text = "Max 2000 characters"
        
        # Auto-set priority based on subject
        if self.data.get('subject') in ['complaint', 'order']:
            self.fields['priority'].initial = 'high'
        elif self.data.get('subject') == 'technical':
            self.fields['priority'].initial = 'urgent'


class NewsletterSignupForm(forms.Form):
    """Enhanced newsletter signup with preferences"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'input input-bordered flex-1 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Enter your email',
            'autocomplete': 'email',
            'inputmode': 'email'
        })
    )
    
    # Newsletter preferences
    interests = forms.MultipleChoiceField(
        choices=[
            ('new_products', 'New Products'),
            ('promotions', 'Special Offers'),
            ('maintenance_tips', 'Maintenance Tips'),
            ('events', 'Events & Workshops'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'checkbox checkbox-primary'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Add email validation or duplicate checking here
        return email


class ProductSearchForm(forms.Form):
    """Enhanced product search with filters"""
    
    q = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Search spare parts, brands, models...',
            'autocomplete': 'off',
            'list': 'search-suggestions'
        })
    )
    
    category = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.HiddenInput()
    )
    
    product_type = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.HiddenInput()
    )
    
    vehicle = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.HiddenInput()
    )
    
    min_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Min €',
            'step': '0.01',
            'min': '0'
        })
    )
    
    max_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'input input-bordered w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Max €',
            'step': '0.01',
            'min': '0'
        })
    )
