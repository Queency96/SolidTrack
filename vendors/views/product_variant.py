from django.db import transaction

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from vendors.models import (
    Product,
    ProductOptionValue,
    ProductVariant,
    ProductVariantOptionValue,
)

from vendors.serializers.product import (
    ProductVariantSerializer,
)


class ProductVariantListCreateView(
    generics.ListCreateAPIView
):
    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = ProductVariantSerializer

    def get_product(self):
        return Product.objects.filter(
            pk=self.kwargs["product_id"],
            vendor__user=self.request.user,
        ).first()

    def get_queryset(self):
        product = self.get_product()

        if product is None:
            return ProductVariant.objects.none()

        return (
            ProductVariant.objects
            .filter(product=product)
            .prefetch_related(
                "option_values",
                "option_values__option",
                "images",
            )
        )

    @transaction.atomic
    def perform_create(self, serializer):
        product = self.get_product()

        if product is None:
            from rest_framework.exceptions import NotFound

            raise NotFound(
                "Product not found."
            )

        variant = serializer.save(
            product=product
        )

        # --------------------------------------------------
        # Ensure only one default variant.
        # --------------------------------------------------

        if variant.is_default:
            ProductVariant.objects.filter(
                product=product,
                is_default=True,
            ).exclude(
                pk=variant.pk
            ).update(
                is_default=False
            )

        # --------------------------------------------------
        # If this is the first variant, make it default.
        # --------------------------------------------------

        if not ProductVariant.objects.filter(
            product=product,
            is_default=True,
        ).exists():
            variant.is_default = True

            variant.save(
                update_fields=[
                    "is_default",
                    "updated_at",
                ]
            )


class ProductVariantDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = ProductVariantSerializer

    def get_queryset(self):
        return (
            ProductVariant.objects
            .filter(
                product__vendor__user=self.request.user,
                product_id=self.kwargs["product_id"],
            )
            .prefetch_related(
                "option_values",
                "option_values__option",
                "images",
            )
        )

    @transaction.atomic
    def perform_update(self, serializer):
        variant = self.get_object()

        requested_default = serializer.validated_data.get(
            "is_default",
            variant.is_default,
        )

        serializer.save()

        if requested_default:
            ProductVariant.objects.filter(
                product=variant.product,
                is_default=True,
            ).exclude(
                pk=variant.pk
            ).update(
                is_default=False
            )

        elif not ProductVariant.objects.filter(
            product=variant.product,
            is_default=True,
        ).exists():
            variant.is_default = True

            variant.save(
                update_fields=[
                    "is_default",
                    "updated_at",
                ]
            )

    @transaction.atomic
    def perform_destroy(self, instance):
        product = instance.product
        was_default = instance.is_default

        instance.delete()

        if was_default:
            replacement = (
                ProductVariant.objects
                .filter(
                    product=product,
                    is_active=True,
                )
                .order_by(
                    "sort_order",
                    "created_at",
                )
                .first()
            )

            if replacement:
                replacement.is_default = True

                replacement.save(
                    update_fields=[
                        "is_default",
                        "updated_at",
                    ]
                )