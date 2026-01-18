from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, Q
from django.utils.html import format_html
from .models import Company, Profile, Product, Order, Export, CompanyFeatureToggle, ProductUpload
from .tasks import process_order, generate_export, process_product_upload


# Inline for Profile in User admin
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


# Extend User admin to include Profile
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_company', 'get_role')

    def get_company(self, obj):
        return obj.profile.company.name if hasattr(obj, 'profile') else '-'
    get_company.short_description = 'Company'

    def get_role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, 'profile') else '-'
    get_role.short_description = 'Role'


# Unregister the default User admin and register the new one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'domain')
    readonly_fields = ('created_at', 'updated_at')

    def has_module_permission(self, request):
        """Hide Company model from operators."""
        if hasattr(request.user, 'profile') and request.user.profile.role == 'operator':
            return False
        return super().has_module_permission(request)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'role', 'is_blocked', 'created_at')
    list_filter = ('role', 'is_blocked', 'company')
    search_fields = ('user__username', 'user__email', 'company__name')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['deactivate_profiles_with_failed_orders']

    def has_module_permission(self, request):
        """Hide Profile model from operators."""
        if hasattr(request.user, 'profile') and request.user.profile.role == 'operator':
            return False
        return super().has_module_permission(request)

    def get_queryset(self, request):
        """Filter profiles by company if user is not superuser."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            return qs.filter(company=request.user.profile.company)
        return qs.none()

    def deactivate_profiles_with_failed_orders(self, request, queryset):
        """Deactivate profiles with 3 or more failed orders."""
        for profile in queryset:
            failed_count = profile.orders.filter(status='failed').count()
            if failed_count >= 3:
                profile.is_blocked = True
                profile.save()
        self.message_user(request, f"Profiles with 3+ failed orders have been blocked.")
    deactivate_profiles_with_failed_orders.short_description = "Block profiles with 3+ failed orders"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'stock_quantity', 'company', 'is_active', 'created_at')
    list_filter = ('is_active', 'company', 'created_at')
    search_fields = ('sku', 'name')
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        """Filter products by company if user is not superuser."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            return qs.filter(company=request.user.profile.company)
        return qs.none()


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('reference_code', 'product', 'quantity', 'status', 'created_by', 'has_been_processed', 'created_at')
    list_filter = ('status', 'has_been_processed', 'product__company', 'created_at')
    search_fields = ('reference_code', 'product__name', 'created_by__user__username')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['export_selected_orders', 'approve_orders', 'retry_failed_orders']

    def get_queryset(self, request):
        """
        Filter orders:
        - Superusers see all
        - Admins see all company orders
        - Operators see only their own orders
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            if profile.role == 'admin':
                return qs.filter(product__company=profile.company)
            elif profile.role == 'operator':
                return qs.filter(created_by=profile)
        return qs.none()

    def export_selected_orders(self, request, queryset):
        """Export selected orders to CSV via Celery task."""
        if not hasattr(request.user, 'profile'):
            self.message_user(request, "You must have a profile to export orders.", level='error')
            return

        # Create Export record
        export = Export.objects.create(
            requested_by=request.user.profile,
            status='pending'
        )

        # Get order IDs
        order_ids = list(queryset.values_list('id', flat=True))

        # Trigger Celery task
        generate_export.delay(export.id, order_ids)

        self.message_user(request, f"Export task started. Export ID: {export.id}")
    export_selected_orders.short_description = "Export selected orders (Celery)"

    def approve_orders(self, request, queryset):
        """Manually approve selected orders."""
        updated = queryset.filter(status='pending').update(status='approved')
        self.message_user(request, f"{updated} orders approved.")
    approve_orders.short_description = "Approve selected orders"

    def retry_failed_orders(self, request, queryset):
        """Retry failed orders that have been processed."""
        orders = queryset.filter(status='failed', has_been_processed=True)
        count = 0
        for order in orders:
            order.status = 'pending'
            order.has_been_processed = False
            order.save()
            # Trigger processing
            process_order.delay(order.id)
            count += 1
        self.message_user(request, f"{count} failed orders queued for retry.")
    retry_failed_orders.short_description = "Retry failed orders"


@admin.register(Export)
class ExportAdmin(admin.ModelAdmin):
    list_display = ('id', 'requested_by', 'status', 'created_at', 'download_link')
    list_filter = ('status', 'requested_by__company', 'created_at')
    search_fields = ('requested_by__user__username',)
    readonly_fields = ('created_at', 'file')

    def download_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" download>Download</a>', obj.file.url)
        return '-'
    download_link.short_description = 'File'

    def get_queryset(self, request):
        """Filter exports: operators see only their own, admins see company exports."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            if profile.role == 'operator':
                # Operators only see their own exports
                return qs.filter(requested_by=profile)
            else:
                # Admins and viewers see all company exports
                return qs.filter(requested_by__company=profile.company)
        return qs.none()


# Inline for CompanyFeatureToggle in Company admin
class FeatureToggleInline(admin.StackedInline):
    model = CompanyFeatureToggle
    can_delete = False
    verbose_name_plural = 'Feature Toggles'
    fields = ('bulk_orders_enabled', 'exports_enabled', 'api_access_enabled', 'csv_upload_enabled')


# Update CompanyAdmin to include inline
@admin.register(CompanyFeatureToggle)
class CompanyFeatureToggleAdmin(admin.ModelAdmin):
    list_display = ('company', 'bulk_orders_enabled', 'exports_enabled', 'api_access_enabled', 'csv_upload_enabled')
    list_filter = ('company', 'bulk_orders_enabled', 'exports_enabled', 'api_access_enabled', 'csv_upload_enabled')
    search_fields = ('company__name',)

    def has_module_permission(self, request):
        """Hide CompanyFeatureToggle model from operators."""
        if hasattr(request.user, 'profile') and request.user.profile.role == 'operator':
            return False
        return super().has_module_permission(request)


@admin.register(ProductUpload)
class ProductUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'uploaded_by', 'status', 'processed_count', 'error_count', 'created_at')
    list_filter = ('status', 'company', 'created_at')
    search_fields = ('uploaded_by__user__username', 'company__name')
    readonly_fields = ('uploaded_by', 'company', 'status', 'processed_count', 'error_count', 'errors_log', 'created_at', 'updated_at')
    fields = ('file', 'uploaded_by', 'company', 'status', 'processed_count', 'error_count', 'errors_log', 'created_at', 'updated_at')

    def get_queryset(self, request):
        """Filter uploads: operators see only their own, admins see company uploads."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            if profile.role == 'operator':
                # Operators only see their own uploads
                return qs.filter(uploaded_by=profile)
            else:
                # Admins and viewers see all company uploads
                return qs.filter(company=profile.company)
        return qs.none()

    def save_model(self, request, obj, form, change):
        """Set uploaded_by and company, then trigger Celery task."""
        if not change:  # Only on creation
            if hasattr(request.user, 'profile'):
                obj.uploaded_by = request.user.profile
                obj.company = request.user.profile.company
                obj.save()
                # Trigger Celery task
                process_product_upload.delay(obj.id)
                self.message_user(request, f"Product upload queued for processing. Upload ID: {obj.id}")
            else:
                self.message_user(request, "You must have a profile to upload products.", level='error')
        else:
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        """Only allow upload if user has profile and CSV upload is enabled."""
        if not hasattr(request.user, 'profile'):
            return False
        profile = request.user.profile
        # Check if feature is enabled
        if hasattr(profile.company, 'feature_toggle'):
            return profile.company.feature_toggle.csv_upload_enabled
        return True  # Default to True if no toggle exists

    def get_form(self, request, obj=None, **kwargs):
        """Customize form to only show file field on creation."""
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # Creating new upload
            form.base_fields['file'].help_text = "Upload CSV file with columns: SKU, Name, Stock Quantity"
        return form
