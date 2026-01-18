from django.test import TestCase
from django.contrib.auth.models import User
from core.models import Company, Profile, Product, Order


class CompanyModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name='Test Company',
            domain='test-company',
            is_active=True
        )

    def test_company_creation(self):
        self.assertEqual(self.company.name, 'Test Company')
        self.assertEqual(self.company.domain, 'test-company')
        self.assertTrue(self.company.is_active)

    def test_company_str(self):
        self.assertEqual(str(self.company), 'Test Company')


class ProfileModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name='Test Company',
            domain='test-company'
        )
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            company=self.company,
            role='operator'
        )

    def test_profile_creation(self):
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.company, self.company)
        self.assertEqual(self.profile.role, 'operator')
        self.assertFalse(self.profile.is_blocked)


class ProductModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name='Test Company',
            domain='test-company'
        )
        self.product = Product.objects.create(
            sku='TEST-001',
            name='Test Product',
            stock_quantity=100,
            company=self.company
        )

    def test_product_creation(self):
        self.assertEqual(self.product.sku, 'TEST-001')
        self.assertEqual(self.product.stock_quantity, 100)
        self.assertTrue(self.product.is_active)


class OrderModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name='Test Company',
            domain='test-company'
        )
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            company=self.company,
            role='operator'
        )
        self.product = Product.objects.create(
            sku='TEST-001',
            name='Test Product',
            stock_quantity=100,
            company=self.company
        )
        self.order = Order.objects.create(
            reference_code='ORD-TEST-001',
            product=self.product,
            quantity=10,
            created_by=self.profile
        )

    def test_order_creation(self):
        self.assertEqual(self.order.reference_code, 'ORD-TEST-001')
        self.assertEqual(self.order.quantity, 10)
        self.assertEqual(self.order.status, 'pending')
        self.assertFalse(self.order.has_been_processed)
