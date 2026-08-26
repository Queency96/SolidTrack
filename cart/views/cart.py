from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from ..serializers.cart import CartSerializer
from ..serializers.cart_item import CartItemSerializer
from ..services.cart_service import CartService




# ==================================================
# Get Active Cart
# ==================================================

class CartDetailView(APIView):
    """
    Return the authenticated customer's active cart.

    GET /cart/
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):

        try:

            cart = CartService.get_active_cart(
                customer=request.user,
            )

            serializer = CartSerializer(
                cart,
                context={
                    "request": request,
                },
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==================================================
# Cart Summary
# ==================================================

class CartSummaryView(APIView):
    """
    Return a lightweight summary of the active cart.

    GET /cart/summary/
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):

        try:

            summary = CartService.get_summary(
                customer=request.user,
            )

            return Response(
                summary,
                status=status.HTTP_200_OK,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==================================================
# Add Cart Item
# ==================================================

class CartItemCreateView(APIView):
    """
    Add a product or product variant to the
    authenticated customer's active cart.

    POST /cart/items/

    Product without variant:

        {
            "product_id": 10,
            "quantity": 2
        }

    Product with variant:

        {
            "product_id": 10,
            "variant_id": 25,
            "quantity": 2
        }
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):

        product_id = request.data.get(
            "product_id",
        )

        variant_id = request.data.get(
            "variant_id",
        )

        quantity = request.data.get(
            "quantity",
            1,
        )

        try:

            cart_item = CartService.add_item(
                customer=request.user,
                product_id=product_id,
                variant_id=variant_id,
                quantity=quantity,
            )

            serializer = CartItemSerializer(
                cart_item,
                context={
                    "request": request,
                },
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==================================================
# Cart Item Detail
# ==================================================

class CartItemDetailView(APIView):
    """
    Retrieve, update, or delete a cart item.

    GET:

        /cart/items/<id>/

    PATCH:

        /cart/items/<id>/

        {
            "quantity": 3
        }

    DELETE:

        /cart/items/<id>/
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(
        self,
        request,
        pk,
    ):

        try:

            cart_item = CartService.get_item(
                customer=request.user,
                item_id=pk,
            )

            serializer = CartItemSerializer(
                cart_item,
                context={
                    "request": request,
                },
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    def patch(
        self,
        request,
        pk,
    ):

        quantity = request.data.get(
            "quantity",
        )

        if quantity is None:

            return Response(
                {
                    "quantity": (
                        "Quantity is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:

            cart_item = CartService.update_item(
                customer=request.user,
                item_id=pk,
                quantity=quantity,
            )

            serializer = CartItemSerializer(
                cart_item,
                context={
                    "request": request,
                },
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def delete(
        self,
        request,
        pk,
    ):

        try:

            CartService.remove_item(
                customer=request.user,
                item_id=pk,
            )

            return Response(
                status=status.HTTP_204_NO_CONTENT,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_404_NOT_FOUND,
            )


# ==================================================
# Increase Cart Item Quantity
# ==================================================

class CartItemIncreaseView(APIView):
    """
    Increase the quantity of a cart item.

    POST /cart/items/<id>/increase/

    Optional body:

        {
            "quantity": 2
        }

    Default:

        quantity = 1
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def post(
        self,
        request,
        pk,
    ):

        quantity = request.data.get(
            "quantity",
            1,
        )

        try:

            cart_item = (
                CartService.increase_quantity(
                    customer=request.user,
                    item_id=pk,
                    quantity=quantity,
                )
            )

            serializer = CartItemSerializer(
                cart_item,
                context={
                    "request": request,
                },
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==================================================
# Decrease Cart Item Quantity
# ==================================================

class CartItemDecreaseView(APIView):
    """
    Decrease the quantity of a cart item.

    POST /cart/items/<id>/decrease/

    Optional body:

        {
            "quantity": 2
        }

    Default:

        quantity = 1

    If the resulting quantity is zero or less,
    the cart item is removed.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def post(
        self,
        request,
        pk,
    ):

        quantity = request.data.get(
            "quantity",
            1,
        )

        try:

            cart_item = (
                CartService.decrease_quantity(
                    customer=request.user,
                    item_id=pk,
                    quantity=quantity,
                )
            )

            if cart_item is None:

                return Response(
                    {
                        "detail": (
                            "Cart item removed."
                        )
                    },
                    status=status.HTTP_200_OK,
                )

            serializer = CartItemSerializer(
                cart_item,
                context={
                    "request": request,
                },
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==================================================
# Clear Cart
# ==================================================

class CartClearView(APIView):
    """
    Remove all items from the active cart.

    DELETE /cart/clear/
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def delete(
        self,
        request,
    ):

        try:

            deleted_count = (
                CartService.clear_cart(
                    customer=request.user,
                )
            )

            return Response(
                {
                    "detail": (
                        "Cart cleared successfully."
                    ),
                    "deleted_items": deleted_count,
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==================================================
# Validate Cart
# ==================================================

class CartValidateView(APIView):
    """
    Validate the active cart before checkout.

    POST /cart/validate/

    Returns an empty errors list when the cart
    is ready for checkout.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def post(
        self,
        request,
    ):

        try:

            errors = CartService.validate_cart(
                customer=request.user,
            )

            return Response(
                {
                    "valid": not bool(errors),
                    "errors": errors,
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==================================================
# Require Valid Cart
# ==================================================

class CartCheckoutValidationView(APIView):
    """
    Require the customer's cart to be valid
    before proceeding to checkout.

    POST /cart/checkout-validation/
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def post(
        self,
        request,
    ):

        try:

            cart = CartService.require_valid_cart(
                customer=request.user,
            )

            serializer = CartSerializer(
                cart,
                context={
                    "request": request,
                },
            )

            return Response(
                {
                    "valid": True,
                    "cart": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as exc:

            detail = exc.args[0]

            if isinstance(
                detail,
                dict,
            ):

                return Response(
                    {
                        "valid": False,
                        **detail,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {
                    "valid": False,
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class CartAddItemView(APIView):
    """
    Add a product or product variant to the
    authenticated customer's active cart.

    The actual cart business logic is handled by
    CartService.add_item().
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):
        """
        Add an item to the customer's cart.
        """

        product_id = request.data.get(
            "product_id",
        )

        variant_id = request.data.get(
            "variant_id",
        )

        quantity = request.data.get(
            "quantity",
            1,
        )

        # ------------------------------------------
        # Required product
        # ------------------------------------------

        if product_id is None:

            return Response(
                {
                    "product_id": (
                        "Product ID is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ------------------------------------------
        # Add item through service
        # ------------------------------------------

        try:

            cart_item = CartService.add_item(
                customer=request.user,
                product_id=product_id,
                quantity=quantity,
                variant_id=variant_id,
            )

        except ValueError as exc:

            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ------------------------------------------
        # Serialize response
        # ------------------------------------------

        serializer = CartItemSerializer(
            cart_item,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )