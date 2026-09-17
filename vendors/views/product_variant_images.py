from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated

from vendors.models import (
    ProductVariant,
    ProductVariantImage,
)
from vendors.serializers.product import (
    ProductVariantImageSerializer,
)
from vendors.services import ProductVariantImageService


class ProductVariantImageListCreateView(
    generics.ListCreateAPIView
):
    """
    List and create images belonging to a product variant.

    Ownership:
        Only the vendor who owns the parent product can access
        the variant's images.

    Business logic:
        Primary-image handling and image lifecycle are delegated
        to ProductVariantImageService.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = ProductVariantImageSerializer

    def get_variant(self):
        """
        Resolve the variant once and cache it for the request.
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

    def get_queryset(self):
        """
        Return only images belonging to the requested variant
        and owned by the authenticated vendor.
        """

        variant = self.get_variant()

        if variant is None:
            return ProductVariantImage.objects.none()

        return (
            ProductVariantImage.objects
            .filter(
                variant_id=variant.pk,
            )
            .select_related(
                "variant",
                "variant__product",
            )
            .order_by(
                "display_order",
                "created_at",
            )
        )

    def perform_create(self, serializer):
        """
        Delegate image creation and primary-image handling
        to the service layer.
        """

        variant = self.get_variant()

        if variant is None:
            raise NotFound(
                "Product variant not found."
            )

        image = ProductVariantImageService.create_image(
            variant=variant,
            validated_data=dict(serializer.validated_data),
        )

        serializer.instance = image


class ProductVariantImageDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    """
    Retrieve, update, or delete a product variant image.

    The image can only be accessed when its variant belongs
    to a product owned by the authenticated vendor.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = ProductVariantImageSerializer

    def get_queryset(self):
        """
        Scope the image queryset to the authenticated vendor.

        This is important because the image ID alone must never
        be sufficient to access another vendor's image.
        """

        return (
            ProductVariantImage.objects
            .filter(
                variant_id=self.kwargs["variant_id"],
                variant__product__vendor__user=self.request.user,
            )
            .select_related(
                "variant",
                "variant__product",
                "variant__product__vendor",
            )
            .order_by(
                "display_order",
                "created_at",
            )
        )

    def perform_update(self, serializer):
        """
        Delegate update and primary-image enforcement
        to the service layer.
        """

        image = ProductVariantImageService.update_image(
            image=self.get_object(),
            validated_data=dict(serializer.validated_data),
        )

        serializer.instance = image

    def perform_destroy(self, instance):
        """
        Delegate deletion and primary-image replacement
        to the service layer.
        """

        ProductVariantImageService.delete_image(
            image=instance,
        )