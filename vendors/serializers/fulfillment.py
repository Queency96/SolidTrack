"""
Vendor-facing fulfillment serializers.
"""

from rest_framework import serializers

from order.models import OrderFulfillment, Package


class VendorFulfillmentItemSerializer(serializers.Serializer):
    """
    Compact item representation for the vendor fulfillment view.
    """

    id = serializers.UUIDField()
    product_name = serializers.CharField()
    variant_name = serializers.CharField(allow_blank=True)
    sku = serializers.CharField(allow_blank=True)
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(
        max_digits=12, decimal_places=2,
    )
    subtotal = serializers.DecimalField(
        max_digits=12, decimal_places=2,
    )


class VendorFulfillmentPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = (
            "id",
            "package_number",
            "tracking_number",
            "package_type",
            "status",
            "weight",
            "description",
            "created_at",
        )
        read_only_fields = fields


class VendorFulfillmentListSerializer(serializers.ModelSerializer):
    """
    List representation for the vendor pending-fulfillments view.
    """

    order_number = serializers.CharField(
        source="order.order_number",
        read_only=True,
    )
    store_name = serializers.CharField(
        source="store.name",
        read_only=True,
    )
    item_count = serializers.IntegerField(
        source="items_count",
        read_only=True,
    )
    package_count = serializers.IntegerField(
        source="packages_count",
        read_only=True,
    )
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderFulfillment
        fields = (
            "id",
            "order_number",
            "store",
            "store_name",
            "status",
            "subtotal",
            "delivery_fee",
            "total_amount",
            "currency",
            "item_count",
            "package_count",
            "customer_name",
            "created_at",
            "processing_at",
            "packing_at",
            "ready_for_dispatch_at",
        )
        read_only_fields = fields

    def get_customer_name(self, obj):
        customer = obj.order.customer
        return customer.get_full_name() or customer.email


class VendorFulfillmentDetailSerializer(serializers.ModelSerializer):
    """
    Detail representation for a single vendor fulfillment.
    """

    order_number = serializers.CharField(
        source="order.order_number",
        read_only=True,
    )
    store_name = serializers.CharField(
        source="store.name",
        read_only=True,
    )
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.CharField(
        source="order.customer.email",
        read_only=True,
    )
    customer_phone = serializers.CharField(
        source="order.customer.phone_number",
        read_only=True,
    )
    items = VendorFulfillmentItemSerializer(
        many=True,
        read_only=True,
    )
    packages = VendorFulfillmentPackageSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = OrderFulfillment
        fields = (
            "id",
            "order",
            "order_number",
            "store",
            "store_name",
            "status",
            "subtotal",
            "delivery_fee",
            "service_fee",
            "insurance_fee",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "currency",
            "delivery_address_line_1",
            "delivery_address_line_2",
            "delivery_city",
            "delivery_state",
            "delivery_country",
            "delivery_postal_code",
            "delivery_latitude",
            "delivery_longitude",
            "delivery_instructions",
            "customer_name",
            "customer_email",
            "customer_phone",
            "items",
            "packages",
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

    def get_customer_name(self, obj):
        customer = obj.order.customer
        return customer.get_full_name() or customer.email




# ==========================================================
# Vendor cannot-fulfill input
# ==========================================================

class VendorCannotFulfillSerializer(serializers.Serializer):
    """
    Input for POST /api/vendors/fulfillments/<uuid>/cannot-fulfill/.

    Fields
    ------
    reason:
        Required. Human-readable explanation.

    item_ids:
        Optional. When omitted or null, every PENDING item on
        the fulfillment is marked UNAVAILABLE (full failure).

        When provided, only those items are marked UNAVAILABLE
        (partial failure). Items not in this list continue
        through normal packing and dispatch.
    """

    reason = serializers.CharField(
        max_length=1000,
        allow_blank=False,
        trim_whitespace=True,
    )

    item_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        default=None,
    )

    def validate_reason(self, value):
        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError(
                "Please provide a more descriptive reason."
            )

        return value

    def validate_item_ids(self, value):
        # Collapse duplicates while preserving order.
        seen = set()
        cleaned = []

        for item_id in value or []:
            if item_id in seen:
                continue
            seen.add(item_id)
            cleaned.append(item_id)

        return cleaned


# ==========================================================
# Vendor cannot-fulfill response
# ==========================================================

class VendorCannotFulfillResultSerializer(serializers.Serializer):
    """
    Output for POST /api/vendors/fulfillments/<uuid>/cannot-fulfill/.

    Fields
    ------
    fulfillment_status:
        The current status of the fulfillment after the call.

    items_marked_unavailable:
        Count of items newly marked UNAVAILABLE by this call.

    refund_amount:
        Total credited to the customer wallet, as a string
        decimal. Null when no refund was issued (e.g. all
        failed items were perishable and no fees applied).

    refund_reference:
        WalletTransaction.reference when a refund was issued.

    is_full_failure:
        True when the fulfillment has no remaining
        FULFILLED or PENDING items and was transitioned
        to FAILED.
    """

    fulfillment_status = serializers.CharField()
    items_marked_unavailable = serializers.IntegerField()
    refund_amount = serializers.CharField(
        allow_null=True,
    )
    refund_reference = serializers.CharField(
        allow_null=True,
    )
    is_full_failure = serializers.BooleanField()