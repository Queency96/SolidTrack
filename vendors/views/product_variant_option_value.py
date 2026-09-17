from rest_framework import generics
from rest_framework.exceptions import NotFound
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
    List and assign option values to a product variant.

    GET:
        Returns all option values assigned to the selected variant.

    POST:
        Assigns an option value to the selected variant.

    Ownership:
        The authenticated user can only access variants belonging
        to their own vendor account.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = ProductVariantOptionValueSerializer

    # ============================================================
    # Variant Resolution
    # ============================================================

    def get_variant(self):
        """
        Resolve the requested variant once and cache it.

        Ownership is enforced through the product -> vendor -> user
        relationship.
        """

        if not hasattr(self, "_variant"):
            self._variant = (
                ProductVariant.objects
                .select_related(
                    "product",
                    "product__vendor",
                )
                .filter(
                    pk=self.kwargs["variant_id"],
                    product__vendor__user=self.request.user,
                )
                .first()
            )

        return self._variant

    # ============================================================
    # Queryset
    # ============================================================

    def get_queryset(self):
        """
        Return option-value assignments belonging to the selected
        variant and authenticated vendor.
        """

        variant = self.get_variant()

        if variant is None:
            return ProductVariantOptionValue.objects.none()

        return (
            ProductVariantOptionValue.objects
            .select_related(
                "variant",
                "variant__product",
                "option_value",
                "option_value__option",
            )
            .filter(
                variant_id=variant.pk,
            )
            .order_by(
                "option_value__option__sort_order",
                "option_value__option__name",
                "option_value__sort_order",
                "option_value__name",
            )
        )

    # ============================================================
    # Create
    # ============================================================

    def perform_create(self, serializer):
        """
        Attach the validated option value to the selected variant.

        The client does not control the variant relationship.
        The variant comes from the URL and authenticated vendor.
        """

        variant = self.get_variant()

        if variant is None:
            raise NotFound(
                "Product variant not found."
            )

        serializer.save(
            variant=variant,
        )

    # ============================================================
    # Serializer Context
    # ============================================================

    def get_serializer_context(self):
        """
        Pass the resolved variant to the serializer.

        ProductVariantOptionValueSerializer uses this context
        to validate that:

        - the option value belongs to the same product;
        - the option is active;
        - the option value is active;
        - the variant does not already have another value
          for the same option.
        """

        context = super().get_serializer_context()

        variant = self.get_variant()

        if variant is not None:
            context["variant"] = variant

        return context


class ProductVariantOptionValueDetailView(
    generics.RetrieveDestroyAPIView
):
    """
    Retrieve or remove an option-value assignment from a
    product variant.

    GET:
        Retrieve one variant-option assignment.

    DELETE:
        Remove the assignment.

    The underlying ProductOptionValue is never deleted.
    Only the ProductVariantOptionValue relationship is removed.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = ProductVariantOptionValueSerializer

    # ============================================================
    # Variant Resolution
    # ============================================================

    def get_variant(self):
        """
        Resolve the parent variant for this assignment.

        The variant must belong to the authenticated vendor.
        """

        if not hasattr(self, "_variant"):
            self._variant = (
                ProductVariant.objects
                .select_related(
                    "product",
                    "product__vendor",
                )
                .filter(
                    pk=self.kwargs["variant_id"],
                    product__vendor__user=self.request.user,
                )
                .first()
            )

        return self._variant

    # ============================================================
    # Queryset
    # ============================================================

    def get_queryset(self):
        """
        Return only assignments belonging to the requested
        variant and authenticated vendor.

        Scoping by variant_id is important because the URL identifies
        both the parent variant and the assignment.
        """

        variant = self.get_variant()

        if variant is None:
            return ProductVariantOptionValue.objects.none()

        return (
            ProductVariantOptionValue.objects
            .select_related(
                "variant",
                "variant__product",
                "option_value",
                "option_value__option",
            )
            .filter(
                variant_id=variant.pk,
            )
            .order_by(
                "option_value__option__sort_order",
                "option_value__option__name",
                "option_value__sort_order",
                "option_value__name",
            )
        )

    # ============================================================
    # Serializer Context
    # ============================================================

    def get_serializer_context(self):
        """
        Pass the assignment's variant to the serializer.

        The assignment itself is resolved through the ownership-
        restricted queryset.
        """

        context = super().get_serializer_context()

        assignment = self.get_object()

        context["variant"] = assignment.variant

        return context