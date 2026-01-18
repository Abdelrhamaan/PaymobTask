from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class Company(models.Model):
    """
    Represents a company in the multi-tenant system.
    """
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True, help_text="Unique domain identifier for multi-tenancy")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['name']

    def __str__(self):
        return self.name


class Profile(models.Model):
    """
    User profile linked to a company with role-based access.
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('operator', 'Operator'),
        ('viewer', 'Viewer'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='profiles')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    is_blocked = models.BooleanField(default=False, help_text="Whether the user is blocked from accessing the system")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.company.name} ({self.role})"


class Product(models.Model):
    """
    Product catalog for each company.
    """
    sku = models.CharField(max_length=100, unique=True, help_text="Unique product identifier")
    name = models.CharField(max_length=255)
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products')
    is_active = models.BooleanField(default=True, help_text="Whether the product is available for ordering")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.sku} - {self.name}"


class Order(models.Model):
    """
    Order placed by users for products.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('approved', 'Approved'),
        ('failed', 'Failed'),
    ]

    reference_code = models.CharField(max_length=100, unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='orders')
    has_been_processed = models.BooleanField(default=False, help_text="Whether this order has gone through processing")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference_code} - {self.product.name} ({self.status})"


class Export(models.Model):
    """
    Export requests for order data.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]

    requested_by = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='exports')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file = models.FileField(upload_to='exports/', null=True, blank=True)
    note = models.TextField(blank=True, help_text="Optional comments related to the export")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Export {self.id} by {self.requested_by.user.username} - {self.status}"


class CompanyFeatureToggle(models.Model):
    """
    Feature toggles for companies to enable/disable specific features.
    """
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='feature_toggle')
    bulk_orders_enabled = models.BooleanField(default=True, help_text="Allow bulk order creation")
    exports_enabled = models.BooleanField(default=True, help_text="Allow order exports")
    api_access_enabled = models.BooleanField(default=True, help_text="Allow API access")
    csv_upload_enabled = models.BooleanField(default=True, help_text="Allow CSV product uploads")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company Feature Toggle"
        verbose_name_plural = "Company Feature Toggles"

    def __str__(self):
        return f"Feature Toggles for {self.company.name}"


class ProductUpload(models.Model):
    """
    Track CSV product upload history.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='product_uploads')
    file = models.FileField(upload_to='product_uploads/')
    uploaded_by = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='product_uploads')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_count = models.IntegerField(default=0, help_text="Number of products successfully processed")
    error_count = models.IntegerField(default=0, help_text="Number of rows with errors")
    errors_log = models.TextField(blank=True, help_text="Log of errors encountered during processing")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Product Upload"
        verbose_name_plural = "Product Uploads"

    def __str__(self):
        return f"Upload {self.id} by {self.uploaded_by.user.username} - {self.status}"
