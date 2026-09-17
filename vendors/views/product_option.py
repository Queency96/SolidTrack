from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated

from vendors.models import (
    Product,
    ProductOption,
    ProductOptionValue,
)
from vendors.serializers.product_option import (
    ProductOptionSerializer,
    ProductOptionValueSerializer,
)
from vendors.services import ProductOptionService


# ==========================================================
# Vendor Product Option
# ==========================================================

class VendorProductOptionListCreateView(
    generics.ListCreateAPIView,
):
    """
    List and create ProductOption objects belonging to the
    authenticated vendor's products.

    GET:
        Lists product options.

        Optional:
            ?product=<product_uuid>

    POST:
        Creates a product option for a vendor-owned product.

    The product relationship is resolved by the view instead
    of trusting a client-supplied ProductOption.product object.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = ProductOptionSerializer

    def get_queryset(self):
        queryset = (
            ProductOption.objects
            .filter(
                product__vendor__user=self.request.user,
            )
            .select_related(
                "product",
                "product__vendor",
                "product__store",
            )
            .prefetch_related(
                "values",
            )
            .order_by(
                "sort_order",
                "name",
            )
        )

        product_id = self.request.query_params.get(
            "product",
        )

        if product_id:
            queryset = queryset.filter(
                product_id=product_id,
            )

        return queryset

    def perform_create(self, serializer):
        """
        Resolve the product from the authenticated vendor's
        products before creating the option.
        """

        product_id = serializer.validated_data.get(
            "product",
        )

        if product_id is None:
            raise NotFound(
                "Product is required."
            )

        product = (
            Product.objects
            .filter(
                pk=product_id,
                vendor__user=self.request.user,
            )
            .first()
        )

        if product is None:
            raise NotFound(
                "Product not found."
            )

        serializer.save(
            product=product,
        )


# ==========================================================
# Vendor Product Option Detail
# ==========================================================

class VendorProductOptionDetailView(
    generics.RetrieveUpdateDestroyAPIView,
):
    """
    Retrieve, update, or delete a ProductOption belonging
    to a product owned by the authenticated vendor.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = ProductOptionSerializer

    def get_queryset(self):
        return (
            ProductOption.objects
            .filter(
                product__vendor__user=self.request.user,
            )
            .select_related(
                "product",
                "product__vendor",
                "product__store",
            )
            .prefetch_related(
                "values",
            )
            .order_by(
                "sort_order",
                "name",
            )
        )

    def perform_update(self, serializer):
        """
        Product ownership cannot be changed through an update.

        The queryset already guarantees that the instance belongs
        to the authenticated vendor.
        """

        serializer.save(
            product=serializer.instance.product,
        )


# ==========================================================
# Vendor Product Option Value
# ==========================================================

class VendorProductOptionValueListCreateView(
    generics.ListCreateAPIView,
):
    """
    List and create ProductOptionValue objects.

    Example:

        Color
            ├── Black
            ├── White
            └── Blue

    Optional filtering:

        ?option=<option_uuid>

    Only values belonging to the authenticated vendor's
    products are returned.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = ProductOptionValueSerializer

    def get_queryset(self):
        queryset = (
            ProductOptionValue.objects
            .filter(
                option__product__vendor__user=self.request.user,
            )
            .select_related(
                "option",
                "option__product",
                "option__product__vendor",
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
        """
        Resolve the ProductOption through the authenticated
        vendor's products.
        """

        option_id = serializer.validated_data.get(
            "option",
        )

        if option_id is None:
            raise NotFound(
                "Product option is required."
            )

        option = (
            ProductOption.objects
            .filter(
                pk=option_id,
                product__vendor__user=self.request.user,
            )
            .first()
        )

        if option is None:
            raise NotFound(
                "Product option not found."
            )

        serializer.save(
            option=option,
        )


# ==========================================================
# Vendor Product Option Value Detail
# ==========================================================

class VendorProductOptionValueDetailView(
    generics.RetrieveUpdateDestroyAPIView,
):
    """
    Retrieve, update, or delete a ProductOptionValue.

    The value must belong to an option belonging to a
    product owned by the authenticated vendor.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = ProductOptionValueSerializer

    def get_queryset(self):
        return (
            ProductOptionValue.objects
            .filter(
                option__product__vendor__user=self.request.user,
            )
            .select_related(
                "option",
                "option__product",
                "option__product__vendor",
            )
            .order_by(
                "sort_order",
                "name",
            )
        )

    def perform_update(self, serializer):
        """
        Prevent moving a ProductOptionValue to another
        ProductOption during an update.

        The existing option remains authoritative.
        """

        serializer.save(
            option=serializer.instance.option,
        )