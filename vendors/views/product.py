from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsVendor
from vendors.models.product import Product
from vendors.serializers.product import ProductListSerializer
from vendors.serializers.product import ProductDetailsSerializer
from vendors.serializers.product import ProductCreateSerializer
from vendors.serializers.product import ProductUpdateSerializer
from vendors.serializers.product import ProductDetailSerializer
from vendors.views.product_availability import (
    ProductAvailabilityCheckView,
    ProductAvailabilityView,
)


class ProductListCreateView(generics.ListCreateAPIView):
    """
    GET:
        List products belonging to the authenticated vendor.

    POST:
        Create a new product for the authenticated vendor.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Product.objects
            .select_related(
                "vendor",
                "category",
            )
            .filter(
                vendor=self.request.user.vendor_profile
            )
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProductCreateSerializer

        return ProductListSerializer

    def perform_create(self, serializer):
        serializer.save(
            vendor=self.request.user.vendor_profile
        )


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET:
        Retrieve a single product with all options and variants.

    PATCH/PUT:
        Update a product.

    DELETE:
        Delete a product.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Product.objects
            .select_related(
                "vendor",
                "category",
            )
            .prefetch_related(
                "options",
                "options__values",
                "variants",
                "variants__option_values",
                "variants__option_values__option_value",
                "variants__option_values__option_value__option",
            )
            .filter(
                vendor=self.request.user.vendor_profile
            )
        )

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ProductUpdateSerializer
        
        if self.request.method == "GET":
            return ProductDetailSerializer

        return ProductDetailsSerializer


