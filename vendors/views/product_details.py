from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from vendors.models.product_variant_option_value import ProductVariantOptionValue
from vendors.serializers.product_variant_option_value import (
    ProductVariantOptionValueSerializer,
)

class ProductVariantOptionValueDetailView(
    generics.RetrieveDestroyAPIView,
):
    """
    Retrieve or remove an option value assigned
    to a variant.
    """

    serializer_class = (
        ProductVariantOptionValueSerializer
    )

    permission_classes = [
        IsAuthenticated,
    ]

    queryset = (
        ProductVariantOptionValue.objects
        .select_related(
            "variant",
            "variant__product",
            "option_value",
            "option_value__option",
        )
    )