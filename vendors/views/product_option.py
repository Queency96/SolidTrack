from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from ..models import (
    ProductOption,
    ProductOptionValue,
)

from ..serializers.product_option import (
    ProductOptionSerializer,
    ProductOptionValueSerializer,
)


# ==================================================
# Vendor Product Option
# ==================================================

class VendorProductOptionListCreateView(
    generics.ListCreateAPIView,
):
    """
    List and create product options.

    Vendors can only access options belonging
    to their own products.
    """

    serializer_class = ProductOptionSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        return (
            ProductOption.objects
            .filter(
                product__vendor__user=self.request.user,
            )
            .select_related(
                "product",
            )
            .prefetch_related(
                "values",
            )
            .order_by(
                "sort_order",
                "name",
            )
        )

    def perform_create(self, serializer):

        product_id = self.request.data.get(
            "product",
        )

        if not product_id:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {
                    "product": (
                        "Product is required."
                    )
                }
            )

        from ..models import Product

        product = Product.objects.filter(
            pk=product_id,
            vendor__user=self.request.user,
        ).first()

        if product is None:
            from rest_framework.exceptions import NotFound

            raise NotFound(
                "Product not found."
            )

        serializer.save(
            product=product,
        )


class VendorProductOptionDetailView(
    generics.RetrieveUpdateDestroyAPIView,
):
    """
    Retrieve, update, or delete a product option.
    """

    serializer_class = ProductOptionSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        return (
            ProductOption.objects
            .filter(
                product__vendor__user=self.request.user,
            )
            .select_related(
                "product",
            )
            .prefetch_related(
                "values",
            )
        )


# ==================================================
# Vendor Product Option Value
# ==================================================

class VendorProductOptionValueListCreateView(
    generics.ListCreateAPIView,
):
    """
    List and create values for a ProductOption.

    Example:

        Color
            ├── Black
            ├── White
            └── Blue
    """

    serializer_class = ProductOptionValueSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        queryset = (
            ProductOptionValue.objects
            .filter(
                option__product__vendor__user=(
                    self.request.user
                ),
            )
            .select_related(
                "option",
                "option__product",
            )
            .order_by(
                "sort_order",
                "name",
            )
        )

        option_id = self.request.query_params.get(
            "option",
        )

        if option_id:
            queryset = queryset.filter(
                option_id=option_id,
            )

        return queryset

    def perform_create(self, serializer):

        option_id = self.request.data.get(
            "option",
        )

        if not option_id:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {
                    "option": (
                        "Product option is required."
                    )
                }
            )

        option = (
            ProductOption.objects
            .filter(
                pk=option_id,
                product__vendor__user=(
                    self.request.user
                ),
            )
            .first()
        )

        if option is None:
            from rest_framework.exceptions import NotFound

            raise NotFound(
                "Product option not found."
            )

        serializer.save(
            option=option,
        )


class VendorProductOptionValueDetailView(
    generics.RetrieveUpdateDestroyAPIView,
):
    """
    Retrieve, update, or delete a ProductOptionValue.
    """

    serializer_class = ProductOptionValueSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        return (
            ProductOptionValue.objects
            .filter(
                option__product__vendor__user=(
                    self.request.user
                ),
            )
            .select_related(
                "option",
                "option__product",
            )
        )