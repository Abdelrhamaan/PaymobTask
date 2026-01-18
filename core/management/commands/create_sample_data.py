from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import Company, Profile, Product, Order, CompanyFeatureToggle, ProductUpload, Export


class Command(BaseCommand):
    help = 'Create sample data for testing'

    def assign_permissions(self, user, role):
        """Assign permissions based on role."""
        models = [Company, Profile, Product, Order, Export, CompanyFeatureToggle, ProductUpload]
        
        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            
            if role == 'admin':
                # Admins get all permissions
                permissions = Permission.objects.filter(content_type=content_type)
                user.user_permissions.add(*permissions)
            elif role == 'operator':
                # Operators get add, change, view for most models
                perms = ['view', 'add', 'change']
                for perm in perms:
                    try:
                        permission = Permission.objects.get(
                            codename=f'{perm}_{model._meta.model_name}',
                            content_type=content_type
                        )
                        user.user_permissions.add(permission)
                    except Permission.DoesNotExist:
                        pass
            elif role == 'viewer':
                # Viewers only get view permissions
                try:
                    permission = Permission.objects.get(
                        codename=f'view_{model._meta.model_name}',
                        content_type=content_type
                    )
                    user.user_permissions.add(permission)
                except Permission.DoesNotExist:
                    pass

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating sample data...'))

        # Create companies
        company1, _ = Company.objects.get_or_create(
            domain='acme-corp',
            defaults={'name': 'Acme Corporation', 'is_active': True}
        )
        company2, _ = Company.objects.get_or_create(
            domain='tech-solutions',
            defaults={'name': 'Tech Solutions Inc', 'is_active': True}
        )

        self.stdout.write(f'Created companies: {company1.name}, {company2.name}')

        # Create users and profiles for Company 1
        # Admin user
        admin_user, created = User.objects.get_or_create(
            username='admin1',
            defaults={
                'email': 'admin1@acme.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
        
        admin_profile, _ = Profile.objects.get_or_create(
            user=admin_user,
            defaults={'company': company1, 'role': 'admin'}
        )
        
        # Assign permissions
        self.assign_permissions(admin_user, 'admin')

        # Operator user
        operator_user, created = User.objects.get_or_create(
            username='operator1',
            defaults={
                'email': 'operator1@acme.com',
                'first_name': 'Operator',
                'last_name': 'One',
                'is_staff': True  # Allow access to admin panel
            }
        )
        if created:
            operator_user.set_password('operator123')
            operator_user.save()
        else:
            # Update existing user to have is_staff
            operator_user.is_staff = True
            operator_user.save()
        
        operator_profile, _ = Profile.objects.get_or_create(
            user=operator_user,
            defaults={'company': company1, 'role': 'operator'}
        )
        
        # Assign permissions
        self.assign_permissions(operator_user, 'operator')

        # Viewer user
        viewer_user, created = User.objects.get_or_create(
            username='viewer1',
            defaults={
                'email': 'viewer1@acme.com',
                'first_name': 'Viewer',
                'last_name': 'One',
                'is_staff': True  # Allow access to admin panel
            }
        )
        if created:
            viewer_user.set_password('viewer123')
            viewer_user.save()
        else:
            # Update existing user to have is_staff
            viewer_user.is_staff = True
            viewer_user.save()
        
        viewer_profile, _ = Profile.objects.get_or_create(
            user=viewer_user,
            defaults={'company': company1, 'role': 'viewer'}
        )
        
        # Assign permissions
        self.assign_permissions(viewer_user, 'viewer')

        self.stdout.write(f'Created users for {company1.name}')

        # Create users for Company 2
        admin2_user, created = User.objects.get_or_create(
            username='admin2',
            defaults={
                'email': 'admin2@techsolutions.com',
                'first_name': 'Admin',
                'last_name': 'Two',
                'is_staff': True
            }
        )
        if created:
            admin2_user.set_password('admin123')
            admin2_user.save()
        
        admin2_profile, _ = Profile.objects.get_or_create(
            user=admin2_user,
            defaults={'company': company2, 'role': 'admin'}
        )
        
        # Assign permissions
        self.assign_permissions(admin2_user, 'admin')

        self.stdout.write(f'Created users for {company2.name}')

        # Create products for Company 1
        products1 = [
            {'sku': 'ACME-001', 'name': 'Widget A', 'stock_quantity': 100},
            {'sku': 'ACME-002', 'name': 'Widget B', 'stock_quantity': 50},
            {'sku': 'ACME-003', 'name': 'Gadget X', 'stock_quantity': 75},
        ]

        for prod_data in products1:
            Product.objects.get_or_create(
                sku=prod_data['sku'],
                defaults={
                    'name': prod_data['name'],
                    'stock_quantity': prod_data['stock_quantity'],
                    'company': company1,
                    'is_active': True
                }
            )

        # Create products for Company 2
        products2 = [
            {'sku': 'TECH-001', 'name': 'Server Rack', 'stock_quantity': 20},
            {'sku': 'TECH-002', 'name': 'Network Switch', 'stock_quantity': 30},
        ]

        for prod_data in products2:
            Product.objects.get_or_create(
                sku=prod_data['sku'],
                defaults={
                    'name': prod_data['name'],
                    'stock_quantity': prod_data['stock_quantity'],
                    'company': company2,
                    'is_active': True
                }
            )

        # Create feature toggles for companies
        toggle1, _ = CompanyFeatureToggle.objects.get_or_create(
            company=company1,
            defaults={
                'bulk_orders_enabled': True,
                'exports_enabled': True,
                'api_access_enabled': True,
                'csv_upload_enabled': True
            }
        )
        
        toggle2, _ = CompanyFeatureToggle.objects.get_or_create(
            company=company2,
            defaults={
                'bulk_orders_enabled': True,
                'exports_enabled': True,
                'api_access_enabled': True,
                'csv_upload_enabled': True
            }
        )

        # Create orders for Company 1
        self.stdout.write('Creating sample orders...')
        
        # Get products
        prod1 = Product.objects.get(sku='ACME-001')
        prod2 = Product.objects.get(sku='ACME-002')
        prod3 = Product.objects.get(sku='ACME-003')
        
        # Operator 1 orders
        orders_data = [
            {'ref': 'ORD-OP1-001', 'prod': prod1, 'qty': 5, 'status': 'approved', 'processed': True},
            {'ref': 'ORD-OP1-002', 'prod': prod2, 'qty': 10, 'status': 'pending', 'processed': False},
            {'ref': 'ORD-OP1-003', 'prod': prod1, 'qty': 1000, 'status': 'failed', 'processed': True}, # Simulate failed due to stock
        ]
        
        for data in orders_data:
            Order.objects.get_or_create(
                reference_code=data['ref'],
                defaults={
                    'product': data['prod'],
                    'quantity': data['qty'],
                    'status': data['status'],
                    'created_by': operator_profile,
                    'has_been_processed': data['processed']
                }
            )

        # Admin 1 orders
        Order.objects.get_or_create(
            reference_code='ORD-ADM1-001',
            defaults={
                'product': prod3,
                'quantity': 2,
                'status': 'processing',
                'created_by': admin_profile,
                'has_been_processed': False
            }
        )

        # Create orders for Company 2
        prod_tech1 = Product.objects.get(sku='TECH-001')
        
        Order.objects.get_or_create(
            reference_code='ORD-ADM2-001',
            defaults={
                'product': prod_tech1,
                'quantity': 1,
                'status': 'approved',
                'created_by': admin2_profile,
                'has_been_processed': True
            }
        )

        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write('\nSample credentials:')
        self.stdout.write('  Company 1 (Acme Corporation):')
        self.stdout.write('    Admin: admin1 / admin123')
        self.stdout.write('    Operator: operator1 / operator123')
        self.stdout.write('    Viewer: viewer1 / viewer123')
        self.stdout.write('  Company 2 (Tech Solutions):')
        self.stdout.write('    Admin: admin2 / admin123')
