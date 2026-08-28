from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from cart.models import Cart
from checkout.services import (
    CheckoutService,
)
from checkout.serializers import (
    CheckoutSerializer,
)


class CheckoutView(
    APIView,
):
    """
    Create an Order from the authenticated customer's
    active cart.

    Checkout mutations are delegated entirely to
    CheckoutService.

    The view is responsible only for:

        • Authentication
        • Serializer validation
        • Obtaining the customer's active cart
        • Calling CheckoutService
        • Formatting the response
    """

    permission_classes = [
        IsAuthenticated,
    ]

    # ==================================================
    # POST
    # ==================================================

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        """
        Create an order from the customer's active cart.
        """

        customer = request.user

        # --------------------------------------------------
        # Serializer
        # --------------------------------------------------

        serializer = CheckoutSerializer(
            data=request.data,
            context={
                "request": request,
                "customer": customer,
            },
        )

        serializer.is_valid(
            raise_exception=True,
        )

        validated_data = (
            serializer.validated_data
        )

        # --------------------------------------------------
        # Active Cart
        # --------------------------------------------------

        cart = (
            Cart.objects
            .filter(
                customer=customer,
                is_active=True,
            )
            .first()
        )

        if cart is None:

            return Response(
                {
                    "detail": (
                        "No active cart was found."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --------------------------------------------------
        # Checkout
        # --------------------------------------------------

        try:

            result = (
                CheckoutService.create_order(
                    customer=customer,

                    cart=cart,

                    shipping_address=(
                        validated_data[
                            "shipping_address"
                        ]
                    ),

                    billing_address=(
                        validated_data.get(
                            "billing_address"
                        )
                    ),

                    payment_method=(
                        validated_data[
                            "payment_method"
                        ]
                    ),

                    customer_note=(
                        validated_data.get(
                            "customer_note",
                            "",
                        )
                    ),
                )
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --------------------------------------------------
        # Response
        # --------------------------------------------------

        order = result["order"]
        payment = result["payment"]
        order_items = result["order_items"]
        fulfillments = result["fulfillments"]

        return Response(
            {
                "detail": (
                    "Checkout completed successfully."
                ),

                "order": {
                    "id": str(order.id),

                    "order_number": (
                        order.order_number
                    ),

                    "status": (
                        order.status
                    ),

                    "payment_status": (
                        order.payment_status
                    ),

                    "payment_method": (
                        order.payment_method
                    ),

                    "subtotal": str(
                        order.subtotal
                    ),

                    "delivery_fee": str(
                        order.delivery_fee
                    ),

                    "service_fee": str(
                        order.service_fee
                    ),

                    "insurance_fee": str(
                        order.insurance_fee
                    ),

                    "discount_amount": str(
                        order.discount_amount
                    ),

                    "tax_amount": str(
                        order.tax_amount
                    ),

                    "total_amount": str(
                        order.total_amount
                    ),

                    "currency": (
                        order.currency
                    ),

                    "customer_note": (
                        order.customer_note
                    ),

                    "items_count": (
                        len(order_items)
                    ),

                    "fulfillments_count": (
                        len(fulfillments)
                    ),
                },

                "payment": {
                    "id": str(payment.id),

                    "status": (
                        payment.status
                    ),

                    "payment_method": (
                        payment.payment_method
                    ),

                    "provider": (
                        payment.provider
                    ),

                    "amount": str(
                        payment.amount
                    ),

                    "currency": (
                        payment.currency
                    ),
                },

                "fulfillments": [
                    {
                        "id": str(
                            fulfillment.id
                        ),

                        "store_id": str(
                            fulfillment.store_id
                        ),

                        "status": (
                            fulfillment.status
                        ),
                    }
                    for fulfillment
                    in fulfillments
                ],
            },
            status=status.HTTP_201_CREATED,
        )