"""
Admin-facing fulfillment and refund serializers.
"""

from rest_framework import serializers

from order.models import OrderFulfillment, OrderItem
from wallet.models import WalletTransaction


class AdminOrderItemSerializer(serializers.ModelSerializer):
    is_unavailable = serializers.BooleanField(read_only=True)
    is_perishable = serializers.BooleanField(read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_name",
            "variant_name",
            "quantity",
            "subtotal",
            "currency",
            "fulfillment_status",
            "unavailable_reason",
            "is_unavailable",
            "is_perishable",
        )
        read_only_fields = fields


class AdminFulfillmentListSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(
        source="order.order_number",
        read_only=True,
    )
    vendor_name = serializers.SerializerMethodField()
    customer_email = serializers.CharField(
        source="order.customer.email",
        read_only=True,
    )
    item_count = serializers.SerializerMethodField()
    unavailable_item_count = serializers.SerializerMethodField()

    class Meta:
        model = OrderFulfillment
        fields = (
            "id",
            "order",
            "order_number",
            "store",
            "store_name",
            "vendor_name",
            "customer_email",
            "status",
            "total_amount",
            "currency",
            "item_count",
            "unavailable_item_count",
            "created_at",
            "ready_for_dispatch_at",
            "dispatched_at",
            "delivered_at",
            "cancelled_at",
        )
        read_only_fields = fields

    def get_vendor_name(self, obj):
        vendor = getattr(obj.store, "vendor", None)
        if vendor is None:
            return None
        return getattr(vendor, "company_name", None) or str(vendor)

    def get_item_count(self, obj):
        return obj.items.count()

    def get_unavailable_item_count(self, obj):
        return obj.items.filter(
            fulfillment_status=OrderItem.FulfillmentStatus.UNAVAILABLE,
        ).count()


class AdminFulfillmentDetailSerializer(AdminFulfillmentListSerializer):
    items = AdminOrderItemSerializer(many=True, read_only=True)

    class Meta(AdminFulfillmentListSerializer.Meta):
        fields = AdminFulfillmentListSerializer.Meta.fields + (
            "items",
            "cancellation_reason" if False else "store_name",
        )
        # NOTE: keep this tuple deterministic; extras added below.

    # Override fields cleanly:
    class Meta:
        model = OrderFulfillment
        fields = (
            "id",
            "order",
            "order_number",
            "store",
            "store_name",
            "vendor_name",
            "customer_email",
            "status",
            "subtotal",
            "delivery_fee",
            "service_fee",
            "insurance_fee",
            "discount_amount",
            "total_amount",
            "currency",
            "items",
            "created_at",
            "processing_at",
            "packing_at",
            "ready_for_dispatch_at",
            "dispatched_at",
            "out_for_delivery_at",
            "delivered_at",
            "cancelled_at",
        )
        read_only_fields = fields


class AdminRefundSerializer(serializers.ModelSerializer):
    customer_email = serializers.CharField(
        source="wallet.user.email",
        read_only=True,
    )
    user_id = serializers.UUIDField(
        source="wallet.user.id",
        read_only=True,
    )
    wallet_id = serializers.UUIDField(
        source="wallet.id",
        read_only=True,
    )

    class Meta:
        model = WalletTransaction
        fields = (
            "id",
            "reference",
            "wallet_id",
            "user_id",
            "customer_email",
            "transaction_type",
            "amount",
            "balance_before",
            "balance_after",
            "description",
            "status",
            "created_at",
        )
        read_only_fields = fields