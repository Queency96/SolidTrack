"""
Customer-facing order tracking serializers.

NOTE: The delivery OTP itself is NEVER exposed to the customer
through this serializer. It is delivered to the customer via SMS,
push notification, and email when the fulfillment enters
OUT_FOR_DELIVERY.

OTP timestamps are exposed per-fulfillment so a customer with
multiple stores can see each delivery's handover timeline
separately.
"""

from rest_framework import serializers

from order.models import (
    Order,
    OrderFulfillment,
    OrderItem,
    OrderAddress,
)


# ==========================================================
# Order item summary
# ==========================================================

class TrackingOrderItemSerializer(serializers.ModelSerializer):

    is_unavailable = serializers.BooleanField(read_only=True)
    is_perishable = serializers.BooleanField(read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_name",
            "variant_name",
            "option_summary",
            "quantity",
            "unit_price",
            "subtotal",
            "currency",
            "fulfillment_status",
            "is_unavailable",
            "is_perishable",
        )
        read_only_fields = fields


# ==========================================================
# Delivery assignment
# ==========================================================

class TrackingDeliveryAssignmentSerializer(serializers.Serializer):

    id = serializers.UUIDField()
    status = serializers.CharField()
    assigned_at = serializers.DateTimeField(allow_null=True)
    accepted_at = serializers.DateTimeField(allow_null=True)
    picked_up_at = serializers.DateTimeField(allow_null=True)
    delivered_at = serializers.DateTimeField(allow_null=True)

    rider_name = serializers.SerializerMethodField()
    rider_phone = serializers.SerializerMethodField()
    rider_latitude = serializers.SerializerMethodField()
    rider_longitude = serializers.SerializerMethodField()

    def get_rider_name(self, obj):
        rider = getattr(obj, "rider", None)
        if rider is None:
            return None
        return rider.get_full_name() or rider.email

    def get_rider_phone(self, obj):
        rider = getattr(obj, "rider", None)
        if rider is None:
            return None
        return getattr(rider, "phone_number", None)

    def _rider_location(self, obj):
        rider = getattr(obj, "rider", None)
        if rider is None:
            return None
        return getattr(rider, "location", None)

    def get_rider_latitude(self, obj):
        location = self._rider_location(obj)
        if location is None:
            return None
        return str(location.latitude)

    def get_rider_longitude(self, obj):
        location = self._rider_location(obj)
        if location is None:
            return None
        return str(location.longitude)


# ==========================================================
# Delivery
# ==========================================================

class TrackingDeliverySerializer(serializers.Serializer):

    id = serializers.UUIDField()
    tracking_number = serializers.CharField()
    status = serializers.CharField()
    distance_km = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True,
    )
    estimated_duration_minutes = serializers.IntegerField(
        allow_null=True,
    )

    pickup_store_name = serializers.CharField(allow_null=True)
    pickup_address = serializers.SerializerMethodField()
    destination_address = serializers.SerializerMethodField()

    assignment = TrackingDeliveryAssignmentSerializer(
        allow_null=True,
    )

    def get_pickup_address(self, obj):
        address = obj.addresses.filter(address_type="PICKUP").first()
        if address is None:
            return None
        return {
            "contact_name": address.contact_name,
            "contact_phone": address.contact_phone,
            "line_1": address.address_line_1,
            "line_2": address.address_line_2,
            "city": address.city,
            "state": address.state,
            "landmark": address.landmark,
            "latitude": str(address.latitude),
            "longitude": str(address.longitude),
        }

    def get_destination_address(self, obj):
        address = obj.addresses.filter(address_type="DELIVERY").first()
        if address is None:
            return None
        return {
            "contact_name": address.contact_name,
            "contact_phone": address.contact_phone,
            "line_1": address.address_line_1,
            "line_2": address.address_line_2,
            "city": address.city,
            "state": address.state,
            "landmark": address.landmark,
            "latitude": str(address.latitude),
            "longitude": str(address.longitude),
        }


# ==========================================================
# Fulfillment
# ==========================================================

class TrackingFulfillmentSerializer(serializers.ModelSerializer):
    """
    One fulfillment's slice of the order.

    OTP timestamps are exposed here (per-store) rather than on
    the order, since each store's delivery has its own OTP.
    The OTP itself is never exposed.
    """

    store_name = serializers.CharField(read_only=True)
    items = TrackingOrderItemSerializer(many=True, read_only=True)
    delivery = serializers.SerializerMethodField()

    class Meta:
        model = OrderFulfillment
        fields = (
            "id",
            "store",
            "store_name",
            "status",

            "subtotal",
            "delivery_fee",
            "service_fee",
            "insurance_fee",
            "discount_amount",
            "total_amount",
            "currency",

            "items",
            "delivery",

            # --------------------------------------------------
            # OTP timestamps — per-fulfillment.
            #
            # Exposed so the customer can see when the code was
            # generated and when the handover was confirmed.
            # The OTP itself is never returned.
            # --------------------------------------------------
            "delivery_otp_generated_at",
            "delivery_otp_verified_at",

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

    def get_delivery(self, obj):
        delivery = getattr(obj, "delivery", None)
        if delivery is None:
            return None
        try:
            return TrackingDeliverySerializer(
                delivery,
                context=self.context,
            ).data
        except Exception:
            return None


# ==========================================================
# Order list
# ==========================================================

class TrackingOrderListSerializer(serializers.ModelSerializer):

    fulfillment_count = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    store_names = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "status",
            "payment_status",
            "subtotal",
            "delivery_fee",
            "service_fee",
            "insurance_fee",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "currency",
            "customer_note",
            "created_at",
            "confirmed_at",
            "paid_at",
            "delivered_at",
            "cancelled_at",

            "fulfillment_count",
            "item_count",
            "store_names",
        )
        read_only_fields = fields

    def get_fulfillment_count(self, obj):
        return obj.fulfillments.count()

    def get_item_count(self, obj):
        return obj.items.count()

    def get_store_names(self, obj):
        return list(
            obj.fulfillments
            .values_list("store_name", flat=True)
            .distinct()
        )


# ==========================================================
# Order detail (tracking)
# ==========================================================

class TrackingOrderDetailSerializer(serializers.ModelSerializer):
    """
    Full tracking representation.

    IMPORTANT: The delivery OTP itself is NEVER exposed here.
    OTP timestamps live on each fulfillment in the `fulfillments`
    array so a multi-store order shows per-store handover timing.
    """

    fulfillments = TrackingFulfillmentSerializer(
        many=True,
        read_only=True,
    )

    shipping_address = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "status",
            "payment_status",
            "payment_method",

            "subtotal",
            "delivery_fee",
            "service_fee",
            "insurance_fee",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "currency",

            "customer_note",
            "shipping_address",

            "fulfillments",

            "created_at",
            "confirmed_at",
            "paid_at",
            "delivered_at",
            "cancelled_at",
        )
        read_only_fields = fields

    def get_shipping_address(self, obj):
        address = (
            obj.addresses
            .filter(address_type=OrderAddress.AddressType.SHIPPING)
            .first()
        )
        if address is None:
            return None
        return {
            "recipient_name": address.recipient_name,
            "phone_number": address.phone_number,
            "address_line_1": address.address_line_1,
            "address_line_2": address.address_line_2,
            "city": address.city,
            "state": address.state,
            "country": address.country,
            "postal_code": address.postal_code,
            "landmark": address.landmark,
            "latitude": str(address.latitude),
            "longitude": str(address.longitude),
        }