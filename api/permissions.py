from rest_framework import permissions


class IsCompanyMember(permissions.BasePermission):
    """
    Ensures user accesses only their company's data.
    """
    def has_permission(self, request, view):
        return hasattr(request.user, 'profile') and not request.user.profile.is_blocked

    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'profile'):
            return False
        
        user_company = request.user.profile.company
        
        # Check based on object type
        if hasattr(obj, 'company'):
            return obj.company == user_company
        elif hasattr(obj, 'product'):
            return obj.product.company == user_company
        elif hasattr(obj, 'created_by'):
            return obj.created_by.company == user_company
        elif hasattr(obj, 'requested_by'):
            return obj.requested_by.company == user_company
        
        return False


class IsOperator(permissions.BasePermission):
    """
    Checks if user has operator role.
    """
    def has_permission(self, request, view):
        if not hasattr(request.user, 'profile'):
            return False
        return request.user.profile.role in ['operator', 'admin'] and not request.user.profile.is_blocked


class IsViewer(permissions.BasePermission):
    """
    Checks if user has viewer role (read-only access).
    """
    def has_permission(self, request, view):
        if not hasattr(request.user, 'profile'):
            return False
        
        # Viewers can only perform safe methods (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return not request.user.profile.is_blocked
        
        return False


class IsAdmin(permissions.BasePermission):
    """
    Checks if user has admin role.
    """
    def has_permission(self, request, view):
        if not hasattr(request.user, 'profile'):
            return False
        return request.user.profile.role == 'admin' and not request.user.profile.is_blocked


class HasFeatureEnabled(permissions.BasePermission):
    """
    Checks if a specific feature is enabled for the user's company.
    Usage: Set feature_name attribute on the view.
    """
    message = "This feature is disabled for your company."
    
    def has_permission(self, request, view):
        if not hasattr(request.user, 'profile'):
            return False
        
        company = request.user.profile.company
        
        # Get feature toggle, create if doesn't exist
        if not hasattr(company, 'feature_toggle'):
            from core.models import CompanyFeatureToggle
            CompanyFeatureToggle.objects.create(company=company)
            company.refresh_from_db()
        
        feature_toggle = company.feature_toggle
        
        # Check specific feature based on view's feature_name attribute
        feature_name = getattr(view, 'feature_name', None)
        
        if feature_name == 'bulk_orders':
            return feature_toggle.bulk_orders_enabled
        elif feature_name == 'exports':
            return feature_toggle.exports_enabled
        elif feature_name == 'api_access':
            return feature_toggle.api_access_enabled
        elif feature_name == 'csv_upload':
            return feature_toggle.csv_upload_enabled
        
        # Default to True if no specific feature specified
        return True
