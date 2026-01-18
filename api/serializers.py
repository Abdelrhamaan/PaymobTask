from rest_framework import serializers
from core.models import Product, Order, Export, Profile
from django.contrib.auth.models import User
import uuid


class ProductSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'sku', 'name', 'stock_quantity', 'company', 'company_name', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at', 'company']


class OrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    created_by_username = serializers.CharField(source='created_by.user.username', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'reference_code', 'product', 'product_name', 'product_sku',
            'quantity', 'status', 'created_by', 'created_by_username',
            'has_been_processed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reference_code', 'status', 'created_by', 'has_been_processed', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Auto-generate reference code
        validated_data['reference_code'] = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        # Set created_by from request context
        validated_data['created_by'] = self.context['request'].user.profile
        return super().create(validated_data)

    def validate_product(self, value):
        """Ensure product belongs to user's company."""
        user = self.context['request'].user
        if hasattr(user, 'profile'):
            if value.company != user.profile.company:
                raise serializers.ValidationError("Product does not belong to your company.")
        return value


class BulkOrderSerializer(serializers.Serializer):
    """Serializer for bulk order creation."""
    orders = OrderSerializer(many=True)

    def create(self, validated_data):
        orders_data = validated_data['orders']
        created_orders = []
        for order_data in orders_data:
            order_data['reference_code'] = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            order_data['created_by'] = self.context['request'].user.profile
            created_orders.append(Order.objects.create(**order_data))
        return created_orders


class ExportSerializer(serializers.ModelSerializer):
    requested_by_username = serializers.CharField(source='requested_by.user.username', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Export
        fields = ['id', 'requested_by', 'requested_by_username', 'status', 'file_url', 'note', 'created_at']
        read_only_fields = ['id', 'requested_by', 'status', 'file_url', 'created_at']

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None
