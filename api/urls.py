from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import ProductViewSet, OrderViewSet, ExportViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'exports', ExportViewSet, basename='export')

urlpatterns = [
    # JWT Authentication
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API endpoints
    path('', include(router.urls)),
]
