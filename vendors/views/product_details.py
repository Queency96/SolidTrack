from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from vendors.models.product_variant_option_value import (
    ProductVariantOptionValue,
)
from vendors.serializers.product_variant_option_value import (
    ProductVariantOptionValueSerializer,
)


class ProductVariantOptionValueDetailView(
    generics.RetrieveDestroyAPIView
):
    """
    Retrieve or remove an option value assigned to a product variant.

    GET:
        Retrieve a single ProductVariantOptionValue.

    DELETE:
        Remove the option value assignment from the variant.

    Important:
        Deleting this object only removes the relationship between
        the ProductVariant and ProductOptionValue.

        It does NOT delete:
            - the ProductOptionValue
            - the ProductOption
            - the ProductVariant
            - the Product
    """

    serializer_class = ProductVariantOptionValueSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    queryset = (
        ProductVariantOptionValue.objects
        .select_related(
            "variant",
            "variant__product",
            "variant__product__vendor",
            "option_value",
            "option_value__option",
            "option_value__option__product",
        )
    )

    def get_queryset(self):
        """
        Restrict access to assignments belonging to products
        owned by the authenticated vendor.

        The ownership check is performed at the database level.
        """

        queryset = super().get_queryset()

        return queryset.filter(
            variant__product__vendor__user=self.request.user,
        )