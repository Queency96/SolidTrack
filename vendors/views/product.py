from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from vendors.models.product import Product
from vendors.serializers.product import ProductListSerializer
from vendors.serializers.product import ProductDetailsSerializer
from vendors.serializers.product import ProductCreateSerializer
from vendors.serializers.product import ProductUpdateSerializer


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
        Retrieve a single product.

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
                "variants__option_values__option_value__option"
            )
            .filter(
                vendor=self.request.user.vendor_profile
            )
        )

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ProductUpdateSerializer

        return ProductDetailsSerializer