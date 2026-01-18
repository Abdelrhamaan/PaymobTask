from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Company, Profile, Product, Order


class APIPermissionTest(TestCase):
    def setUp(self):
        # Create companies
        self.company1 = Company.objects.create(name='Company 1', domain='company1')
        self.company2 = Company.objects.create(name='Company 2', domain='company2')

        # Create users for company 1
        self.operator1 = User.objects.create_user(username='operator1', password='pass123')
        self.operator1_profile = Profile.objects.create(
            user=self.operator1,
            company=self.company1,
            role='operator'
        )

        # Create users for company 2
        self.operator2 = User.objects.create_user(username='operator2', password='pass123')
        self.operator2_profile = Profile.objects.create(
            user=self.operator2,
            company=self.company2,
            role='operator'
        )

        # Create products
        self.product1 = Product.objects.create(
            sku='PROD-1',
            name='Product 1',
            stock_quantity=100,
            company=self.company1
        )
        self.product2 = Product.objects.create(
            sku='PROD-2',
            name='Product 2',
            stock_quantity=100,
            company=self.company2
        )

        self.client = APIClient()

    def test_operator_can_only_see_own_company_products(self):
        """Test that operators can only see their company's products."""
        self.client.force_authenticate(user=self.operator1)
        response = self.client.get('/api/products/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['sku'], 'PROD-1')

    def test_operator_cannot_see_other_company_products(self):
        """Test that operators cannot see other company's products."""
        self.client.force_authenticate(user=self.operator1)
        response = self.client.get(f'/api/products/{self.product2.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_order(self):
        """Test order creation via API."""
        self.client.force_authenticate(user=self.operator1)
        data = {
            'product': self.product1.id,
            'quantity': 5
        }
        response = self.client.post('/api/orders/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('reference_code', response.data)
        self.assertEqual(response.data['quantity'], 5)

    def test_blocked_user_cannot_access_api(self):
        """Test that blocked users cannot access API."""
        self.operator1_profile.is_blocked = True
        self.operator1_profile.save()
        
        self.client.force_authenticate(user=self.operator1)
        response = self.client.get('/api/products/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
