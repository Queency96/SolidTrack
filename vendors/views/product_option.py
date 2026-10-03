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

class VendorProductOptionListCreateView(generics.ListCreateAPIView):
    """
    List and create ProductOption objects belonging to the
    authenticated vendor's products.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ProductOptionSerializer

    def get_queryset(self):
        queryset = (
            ProductOption.objects
            .filter(product__vendor__user=self.request.user)
            .select_related("product", "product__vendor", "product__store")
            .prefetch_related("values")
            .order_by("sort_order", "name")
        )

        product_id = self.request.query_params.get("product")

        if product_id:
            queryset = queryset.filter(product_id=product_id)

        return queryset

    def perform_create(self, serializer):
        """
        Resolve the product from the authenticated vendor's
        products before creating the option.
        """

        product_value = serializer.validated_data.get("product")

        if product_value is None:
            raise NotFound("Product is required.")

        # Normalize instance or PK to a raw PK value.
        product_pk = getattr(product_value, "pk", product_value)

        product = (
            Product.objects
            .filter(
                pk=product_pk,
                vendor__user=self.request.user,
            )
            .first()
        )

        if product is None:
            raise NotFound("Product not found.")

        serializer.save(product=product)


# ==========================================================
# Vendor Product Option Detail
# ==========================================================

class VendorProductOptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a ProductOption belonging
    to a product owned by the authenticated vendor.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ProductOptionSerializer

    def get_queryset(self):
        return (
            ProductOption.objects
            .filter(product__vendor__user=self.request.user)
            .select_related("product", "product__vendor", "product__store")
            .prefetch_related("values")
            .order_by("sort_order", "name")
        )

    def perform_update(self, serializer):
        serializer.save(product=serializer.instance.product)


# ==========================================================
# Vendor Product Option Value
# ==========================================================

class VendorProductOptionValueListCreateView(generics.ListCreateAPIView):
    """
    List and create ProductOptionValue objects.

    Optional filtering: ?option=<option_uuid>
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ProductOptionValueSerializer

    def get_queryset(self):
        queryset = (
            ProductOptionValue.objects
            .filter(option__product__vendor__user=self.request.user)
            .select_related("option", "option__product", "option__product__vendor")
            .order_by("sort_order", "name")
        )

        option_id = self.request.query_params.get("option")

        if option_id:
            queryset = queryset.filter(option_id=option_id)

        return queryset

    def perform_create(self, serializer):
        """
        Resolve the ProductOption through the authenticated
        vendor's products.
        """

        option_value = serializer.validated_data.get("option")

        if option_value is None:
            raise NotFound("Product option is required.")

        # Normalize instance or PK to a raw PK value.
        option_pk = getattr(option_value, "pk", option_value)

        option = (
            ProductOption.objects
            .filter(
                pk=option_pk,
                product__vendor__user=self.request.user,
            )
            .first()
        )

        if option is None:
            raise NotFound("Product option not found.")

        serializer.save(option=option)


# ==========================================================
# Vendor Product Option Value Detail
# ==========================================================

class VendorProductOptionValueDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a ProductOptionValue.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ProductOptionValueSerializer

    def get_queryset(self):
        return (
            ProductOptionValue.objects
            .filter(option__product__vendor__user=self.request.user)
            .select_related("option", "option__product", "option__product__vendor")
            .order_by("sort_order", "name")
        )

    def perform_update(self, serializer):
        serializer.save(option=serializer.instance.option)