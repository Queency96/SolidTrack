from rest_framework import serializers

from order.models import Order
from accounts.models import Address


# ==================================================
# Inline Checkout Address
# ==================================================

class CheckoutAddressSerializer(
    serializers.Serializer,
):
    """
    Address supplied directly during checkout.

    The customer does not need to have this address
    saved in their address book.

    The address is used only for this checkout and
    is copied into OrderAddress as an immutable
    historical snapshot.
    """

    recipient_name = serializers.CharField(
        required=True,
        max_length=255,
    )

    phone_number = serializers.CharField(
        required=True,
        max_length=30,
    )

    address_line_1 = serializers.CharField(
        required=True,
        max_length=255,
    )

    address_line_2 = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=255,
    )

    city = serializers.CharField(
        required=True,
        max_length=100,
    )

    state = serializers.CharField(
        required=True,
        max_length=100,
    )

    country = serializers.CharField(
        required=False,
        allow_blank=True,
        default="Nigeria",
        max_length=100,
    )

    postal_code = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=20,
    )

    landmark = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=255,
    )

    latitude = serializers.DecimalField(
        required=True,
        max_digits=10,
        decimal_places=7,
    )

    longitude = serializers.DecimalField(
        required=True,
        max_digits=10,
        decimal_places=7,
    )

    # ==================================================
    # Latitude
    # ==================================================

    def validate_latitude(
        self,
        value,
    ):
        if not (
            -90 <= value <= 90
        ):
            raise serializers.ValidationError(
                "Latitude must be between -90 and 90."
            )

        return value

    # ==================================================
    # Longitude
    # ==================================================

    def validate_longitude(
        self,
        value,
    ):
        if not (
            -180 <= value <= 180
        ):
            raise serializers.ValidationError(
                "Longitude must be between -180 and 180."
            )

        return value


# ==================================================
# Checkout Serializer
# ==================================================

class CheckoutSerializer(
    serializers.Serializer,
):
    """
    Validate checkout data.

    Shipping address
    ----------------

    Customer must provide exactly one:

        shipping_address_id
        OR
        shipping_address

    Billing address
    ---------------

    Customer may provide:

        billing_address_id
        OR
        billing_address

    Billing address is optional.

    A saved address is resolved against the authenticated
    customer.

    An inline address remains a plain validated dictionary.

    Before returning validated_data, both are normalized
    into:

        shipping_address
        billing_address

    This allows CheckoutView / CheckoutService to receive
    a consistent structure.
    """

    # ==================================================
    # Saved Shipping Address
    # ==================================================

    shipping_address_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        default=None,
    )

    # ==================================================
    # Inline Shipping Address
    # ==================================================

    shipping_address = CheckoutAddressSerializer(
        required=False,
        allow_null=True,
        default=None,
    )

    # ==================================================
    # Saved Billing Address
    # ==================================================

    billing_address_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        default=None,
    )

    # ==================================================
    # Inline Billing Address
    # ==================================================

    billing_address = CheckoutAddressSerializer(
        required=False,
        allow_null=True,
        default=None,
    )

    # ==================================================
    # Payment Method
    # ==================================================

    payment_method = serializers.ChoiceField(
        choices=Order.PaymentMethod.choices,
        required=True,
    )

    # ==================================================
    # Customer Note
    # ==================================================

    customer_note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=2000,
    )

    # ==================================================
    # Main Validation
    # ==================================================

    def validate(
        self,
        attrs,
    ):
        """
        Validate and normalize checkout addresses.
        """

        customer = self.context.get(
            "customer"
        )

        if customer is None:

            raise serializers.ValidationError(
                {
                    "customer": (
                        "Customer is required."
                    )
                }
            )

        # ==================================================
        # Shipping Address
        # ==================================================

        shipping_address_id = attrs.get(
            "shipping_address_id"
        )

        shipping_address = attrs.get(
            "shipping_address"
        )

        # --------------------------------------------------
        # Exactly one shipping address
        # --------------------------------------------------

        if (
            shipping_address_id is None
            and shipping_address is None
        ):

            raise serializers.ValidationError(
                {
                    "shipping_address": (
                        "Provide either "
                        "shipping_address_id or "
                        "shipping_address."
                    )
                }
            )

        if (
            shipping_address_id is not None
            and shipping_address is not None
        ):

            raise serializers.ValidationError(
                {
                    "shipping_address": (
                        "Provide either "
                        "shipping_address_id or "
                        "shipping_address, "
                        "not both."
                    )
                }
            )

        # --------------------------------------------------
        # Resolve saved shipping address
        # --------------------------------------------------

        if shipping_address_id is not None:

            shipping_address = (
                Address.objects
                .filter(
                    pk=shipping_address_id,
                    user=customer,
                )
                .first()
            )

            if shipping_address is None:

                raise serializers.ValidationError(
                    {
                        "shipping_address_id": (
                            "Shipping address was "
                            "not found."
                        )
                    }
                )

        # ==================================================
        # Billing Address
        # ==================================================

        billing_address_id = attrs.get(
            "billing_address_id"
        )

        billing_address = attrs.get(
            "billing_address"
        )

        # --------------------------------------------------
        # Both billing forms supplied
        # --------------------------------------------------

        if (
            billing_address_id is not None
            and billing_address is not None
        ):

            raise serializers.ValidationError(
                {
                    "billing_address": (
                        "Provide either "
                        "billing_address_id or "
                        "billing_address, "
                        "not both."
                    )
                }
            )

        # --------------------------------------------------
        # Resolve saved billing address
        # --------------------------------------------------

        if billing_address_id is not None:

            billing_address = (
                Address.objects
                .filter(
                    pk=billing_address_id,
                    user=customer,
                )
                .first()
            )

            if billing_address is None:

                raise serializers.ValidationError(
                    {
                        "billing_address_id": (
                            "Billing address was "
                            "not found."
                        )
                    }
                )

        # ==================================================
        # Normalize
        # ==================================================

        attrs[
            "shipping_address"
        ] = shipping_address

        attrs[
            "billing_address"
        ] = billing_address

        return attrs