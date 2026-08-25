from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from vendors.models import (
    ProductVariant,
    ProductVariantOptionValue,
)

from vendors.serializers.product_variant_option_value import (
    ProductVariantOptionValueSerializer,
)


class ProductVariantOptionValueListCreateView(
    generics.ListCreateAPIView
):
    """
    List and assign option values to a variant.

    GET:

        Returns all option values assigned to the variant.

    POST:

        Assigns an option value to the variant.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    # ==================================================
    # Queryset
    # ==================================================

    def get_queryset(self):
        """
        Return option values belonging to the selected
        variant and authenticated vendor.
        """

        return (
            ProductVariantOptionValue.objects
            .select_related(
                "variant",
                "variant__product",
                "option_value",
                "option_value__option",
            )
            .filter(
                variant_id=self.kwargs["variant_id"],
                variant__product__vendor=(
                    self.request.user.vendor_profile
                ),
            )
            .order_by(
                "option_value__option__sort_order",
                "option_value__sort_order",
                "option_value__name",
            )
        )

    # ==================================================
    # Create
    # ==================================================

    def perform_create(self, serializer):
        """
        Attach the option value to the selected variant.
        """

        variant = get_object_or_404(
            ProductVariant,
            pk=self.kwargs["variant_id"],
            product__vendor=(
                self.request.user.vendor_profile
            ),
        )

        serializer.save(
            variant=variant,
        )

    # ==================================================
    # Serializer
    # ==================================================

    def get_serializer_context(self):
        """
        Pass the variant into the serializer so that
        product ownership and duplicate-option validation
        can be performed.
        """

        context = super().get_serializer_context()

        variant = get_object_or_404(
            ProductVariant,
            pk=self.kwargs["variant_id"],
            product__vendor=(
                self.request.user.vendor_profile
            ),
        )

        context["variant"] = variant

        return context


class ProductVariantOptionValueDetailView(
    generics.RetrieveDestroyAPIView
):
    """
    Retrieve or remove a selected option value.

    GET:

        Retrieve one variant-option assignment.

    DELETE:

        Remove the option value from the variant.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = (
        ProductVariantOptionValueSerializer
    )

    # ==================================================
    # Queryset
    # ==================================================

    def get_queryset(self):
        return (
            ProductVariantOptionValue.objects
            .select_related(
                "variant",
                "variant__product",
                "option_value",
                "option_value__option",
            )
            .filter(
                variant__product__vendor=(
                    self.request.user.vendor_profile
                ),
            )
        )

    # ==================================================
    # Serializer Context
    # ==================================================

    def get_serializer_context(self):
        context = super().get_serializer_context()

        assignment = self.get_object()

        context["variant"] = assignment.variant

        return context