from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from vendors.models import (
    Product,
    ProductVariant,
)

from vendors.serializers.product_variant import (
    ProductVariantSerializer, ProductVariantCreateSerializer, ProductVariantUpdateSerializer,
)



class ProductVariantListCreateView(
    generics.ListCreateAPIView
):
    """
    List and create variants belonging to a product.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        return (
            ProductVariant.objects
            .select_related(
                "product",
                "product__store",
            )
            .prefetch_related(
                "variant_option_values__option_value__option",
                "option_values__option",
            )
            .filter(
                product_id=self.kwargs["product_id"],
                product__vendor=(
                    self.request.user.vendor_profile
                ),
            )
            .order_by(
                "sort_order",
                "created_at",
            )
        )

    def get_serializer_class(self):

        if self.request.method == "POST":
            return ProductVariantCreateSerializer

        return ProductVariantSerializer

    def perform_create(self, serializer):

        product = get_object_or_404(
            Product,
            pk=self.kwargs["product_id"],
            vendor=self.request.user.vendor_profile,
        )

        serializer.save(
            product=product,
        )


class ProductVariantDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    """
    Retrieve, update, or delete a product variant.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        return (
            ProductVariant.objects
            .select_related(
                "product",
                "product__store",
            )
            .prefetch_related(
                "variant_option_values__option_value__option",
                "option_values__option",
            )
            .filter(
                product__vendor=(
                    self.request.user.vendor_profile
                ),
            )
        )

    def get_serializer_class(self):

        if self.request.method in [
            "PUT",
            "PATCH",
        ]:
            return ProductVariantUpdateSerializer

        return ProductVariantSerializer