from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse, Http404
from core.models import Product, Order, Export
from .serializers import ProductSerializer, OrderSerializer, BulkOrderSerializer, ExportSerializer
from .permissions import IsCompanyMember, IsOperator, HasFeatureEnabled
from .throttling import ProductsThrottle, OrdersThrottle, ExportsThrottle
from core.tasks import process_order
import logging

logger = logging.getLogger(__name__)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing products.
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]
    throttle_classes = [ProductsThrottle]

    def get_queryset(self):
        """Filter products by user's company."""
        if hasattr(self.request.user, 'profile'):
            return Product.objects.filter(
                company=self.request.user.profile.company,
                is_active=True
            )
        return Product.objects.none()


class OrderViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing orders.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember, IsOperator]
    throttle_classes = [OrdersThrottle]

    def get_queryset(self):
        """
        Filter orders:
        - Admins see all company orders
        - Operators see only their own orders
        """
        if not hasattr(self.request.user, 'profile'):
            return Order.objects.none()

        profile = self.request.user.profile
        
        if profile.role == 'admin':
            return Order.objects.filter(product__company=profile.company)
        elif profile.role == 'operator':
            return Order.objects.filter(created_by=profile)
        
        return Order.objects.none()

    def perform_create(self, serializer):
        """Create order and trigger processing task."""
        order = serializer.save()
        # Trigger Celery task for processing
        process_order.delay(order.id)
        logger.info(f"Order {order.reference_code} created and queued for processing")

    @action(detail=False, methods=['post'], url_path='bulk', permission_classes=[IsAuthenticated, IsCompanyMember, IsOperator, HasFeatureEnabled])
    def bulk_create(self, request):
        """
        Bulk create orders.
        POST /api/orders/bulk/
        Body: {"orders": [{"product": 1, "quantity": 10}, ...]}
        """
        # Set feature name for HasFeatureEnabled permission
        self.feature_name = 'bulk_orders'
        
        # Check feature toggle
        if hasattr(request.user, 'profile'):
            company = request.user.profile.company
            if hasattr(company, 'feature_toggle') and not company.feature_toggle.bulk_orders_enabled:
                return Response(
                    {'error': 'Bulk orders are disabled for your company'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = BulkOrderSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            orders = serializer.save()
            # Trigger processing for each order
            for order in orders:
                process_order.delay(order.id)
            
            logger.info(f"Bulk created {len(orders)} orders")
            return Response(
                OrderSerializer(orders, many=True, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='retry')
    def retry(self, request, pk=None):
        """
        Retry a failed order.
        POST /api/orders/<id>/retry/
        """
        order = self.get_object()
        
        if order.status != 'failed':
            return Response(
                {'error': 'Only failed orders can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not order.has_been_processed:
            return Response(
                {'error': 'Order has not been processed yet'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset order status
        order.status = 'pending'
        order.has_been_processed = False
        order.save()
        
        # Trigger processing
        process_order.delay(order.id)
        
        logger.info(f"Order {order.reference_code} queued for retry")
        
        return Response(
            {'message': f'Order {order.reference_code} queued for retry'},
            status=status.HTTP_200_OK
        )


class ExportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing and downloading exports.
    """
    serializer_class = ExportSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]
    throttle_classes = [ExportsThrottle]

    def get_queryset(self):
        """Filter exports by user's company."""
        if hasattr(self.request.user, 'profile'):
            return Export.objects.filter(requested_by__company=self.request.user.profile.company)
        return Export.objects.none()

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        """
        Download export file.
        GET /api/exports/<id>/download/
        """
        export = self.get_object()
        
        # Check feature toggle
        if hasattr(request.user, 'profile'):
            company = request.user.profile.company
            if hasattr(company, 'feature_toggle') and not company.feature_toggle.exports_enabled:
                return Response(
                    {'error': 'Exports are disabled for your company'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        if export.status != 'ready':
            return Response(
                {'error': f'Export is not ready. Current status: {export.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not export.file:
            return Response(
                {'error': 'Export file not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            response = FileResponse(export.file.open('rb'), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="export_{export.id}.csv"'
            logger.info(f"Export {export.id} downloaded by {request.user.username}")
            return response
        except Exception as e:
            logger.error(f"Error downloading export {export.id}: {str(e)}")
            raise Http404("Export file not found")
