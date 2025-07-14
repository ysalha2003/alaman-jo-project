from django.core.management.base import BaseCommand
from django.utils.text import slugify
from shop.models import Category, Product
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create sample data for Alamana-jo bike shop'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating sample data for Alamana-jo...'))
        
        # Create categories
        categories_data = [
            {
                'name': 'Brake Parts',
                'description': 'Brake pads, discs, cables and complete brake systems for all vehicle types',
                'sort_order': 1
            },
            {
                'name': 'Drive Train',
                'description': 'Chains, gears, derailleurs and drive components',
                'sort_order': 2
            },
            {
                'name': 'Wheels & Tires',
                'description': 'Wheels, tires, tubes and related accessories',
                'sort_order': 3
            },
            {
                'name': 'Lighting',
                'description': 'LED lights, reflectors and visibility accessories',
                'sort_order': 4
            },
            {
                'name': 'Batteries & Charging',
                'description': 'E-bike batteries, chargers and power management',
                'sort_order': 5
            },
            {
                'name': 'Electronics',
                'description': 'Displays, controllers and electronic components',
                'sort_order': 6
            },
        ]
        
        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'slug': slugify(cat_data['name']),
                    'description': cat_data['description'],
                    'sort_order': cat_data['sort_order'],
                    'is_active': True
                }
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(f'Created category: {category.name}')
        
        # Create sample products
        products_data = [
            {
                'name': 'Hydraulic Disc Brake Set',
                'brand': 'Shimano',
                'category': 'Brake Parts',
                'product_type': 'brake_parts',
                'vehicle_compatibility': 'universal',
                'price': Decimal('89.99'),
                'compare_price': Decimal('119.99'),
                'stock_quantity': 25,
                'short_description': 'Professional hydraulic disc brake system with excellent stopping power',
                'description': 'High-quality Shimano hydraulic disc brake set suitable for bikes, e-bikes, and e-scooters. Features reliable stopping power in all weather conditions.',
                'model_number': 'SH-HDB-001',
                'sku': 'SH-HDB-001',
                'is_featured': True,
                'is_bestseller': True,
            },
            {
                'name': 'E-Bike Battery 48V 15Ah',
                'brand': 'Bosch',
                'category': 'Batteries & Charging',
                'product_type': 'batteries',
                'vehicle_compatibility': 'e_bike',
                'price': Decimal('499.99'),
                'stock_quantity': 12,
                'short_description': 'High-capacity lithium battery for e-bikes with 80km range',
                'description': 'Professional Bosch e-bike battery with 48V 15Ah capacity. Provides up to 80km range depending on riding conditions.',
                'model_number': 'BS-BAT-48V15',
                'sku': 'BS-BAT-48V15',
                'is_featured': True,
                'is_new_arrival': True,
            },
            {
                'name': 'LED Front Light 1200 Lumen',
                'brand': 'Cateye',
                'category': 'Lighting',
                'product_type': 'lighting',
                'vehicle_compatibility': 'universal',
                'price': Decimal('34.99'),
                'compare_price': Decimal('49.99'),
                'stock_quantity': 45,
                'short_description': 'Powerful LED front light with USB charging',
                'description': 'Ultra-bright 1200 lumen LED front light with multiple modes and USB charging capability.',
                'model_number': 'CE-LED-1200',
                'sku': 'CE-LED-1200',
                'is_bestseller': True,
            },
            {
                'name': '26" Mountain Bike Tire',
                'brand': 'Continental',
                'category': 'Wheels & Tires',
                'product_type': 'wheels_tires',
                'vehicle_compatibility': 'bike',
                'price': Decimal('28.99'),
                'stock_quantity': 60,
                'short_description': 'Durable mountain bike tire for all terrains',
                'description': 'High-quality Continental mountain bike tire with excellent grip and puncture resistance.',
                'model_number': 'CT-MTB-26',
                'sku': 'CT-MTB-26',
            },
            {
                'name': 'E-Scooter Motor Controller',
                'brand': 'Xiaomi',
                'category': 'Electronics',
                'product_type': 'electronics',
                'vehicle_compatibility': 'e_scooter',
                'price': Decimal('79.99'),
                'stock_quantity': 8,
                'short_description': 'Replacement motor controller for Xiaomi e-scooters',
                'description': 'Original Xiaomi motor controller compatible with M365 and Pro models.',
                'model_number': 'XM-CTRL-001',
                'sku': 'XM-CTRL-001',
                'is_new_arrival': True,
            },
            {
                'name': '9-Speed Chain',
                'brand': 'SRAM',
                'category': 'Drive Train',
                'product_type': 'drive_train',
                'vehicle_compatibility': 'bike',
                'price': Decimal('19.99'),
                'stock_quantity': 35,
                'short_description': 'High-performance 9-speed bicycle chain',
                'description': 'SRAM 9-speed chain with quick-link for easy installation and maintenance.',
                'model_number': 'SR-CH9-001',
                'sku': 'SR-CH9-001',
            },
        ]
        
        for product_data in products_data:
            category = categories[product_data.pop('category')]
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                brand=product_data['brand'],
                defaults={
                    'category': category,
                    'slug': slugify(f"{product_data['brand']}-{product_data['name']}"),
                    **product_data,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created product: {product.brand} {product.name}')
        
        self.stdout.write(
            self.style.SUCCESS('Sample data created successfully!')
        )
        self.stdout.write('You can now browse products at: http://localhost:8004')
