from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated

from vendors.models import (
    ProductVariant,
    ProductVariantImage,
)
from vendors.serializers.product import ProductVariantImageSerializer
from vendors.services import ProductVariantImageService


class ProductVariantImageListCreateView(
    generics.ListCreateAPIView
):
    """
    List and create images belonging to a product variant.

    Ownership:
        Only the vendor who owns the parent product can access
        the variant's images.

    GET:
        Returns 404 when the variant is missing or not owned
        by the authenticated vendor.

    POST:
        Delegates image creation and primary-image handling
        to ProductVariantImageService.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ProductVariantImageSerializer

    def get_variant(self):
        if not hasattr(self, "_variant"):
            self._variant = (
                ProductVariant.objects
                .select_related("product", "product__vendor")
                .filter(
                    pk=self.kwargs["variant_id"],
                    product__vendor__user=self.request.user,
                )
                .first()
            )

        return self._variant

    def get_queryset(self):
        variant = self.get_variant()

        if variant is None:
            return ProductVariantImage.objects.none()

        return (
            ProductVariantImage.objects
            .filter(variant_id=variant.pk)
            .select_related("variant", "variant__product")
            .order_by("display_order", "created_at")
        )

    def list(self, request, *args, **kwargs):
        """
        Return 404 when the parent variant is missing or not
        owned by the authenticated vendor.
        """

        if self.get_variant() is None:
            raise NotFound("Product variant not found.")

        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        variant = self.get_variant()

        if variant is None:
            raise NotFound("Product variant not found.")

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

    permission_classes = [IsAuthenticated]
    serializer_class = ProductVariantImageSerializer

    def get_queryset(self):
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
            .order_by("display_order", "created_at")
        )

    def perform_update(self, serializer):
        image = ProductVariantImageService.update_image(
            image=self.get_object(),
            validated_data=dict(serializer.validated_data),
        )

        serializer.instance = image

    def perform_destroy(self, instance):
        ProductVariantImageService.delete_image(image=instance)