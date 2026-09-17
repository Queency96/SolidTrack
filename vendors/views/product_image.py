from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated

from vendors.models import Product, ProductImage
from vendors.serializers.product import ProductImageSerializer
from vendors.services import ProductImageService


class ProductImageListCreateView(
    generics.ListCreateAPIView
):
    """
    List and create images for a vendor-owned product.

    GET:
        Return all images belonging to the specified product.

    POST:
        Create a new image for the specified product.

    Image lifecycle rules such as:
        - primary image handling
        - ensuring a primary image exists
        - primary image replacement

    are delegated to ProductImageService.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = ProductImageSerializer

    # ----------------------------------------------------------
    # Product
    # ----------------------------------------------------------

    def get_product(self):
        """
        Return the requested product only if it belongs to
        the authenticated vendor.
        """

        if not hasattr(self, "_product"):
            self._product = (
                Product.objects
                .select_related(
                    "vendor",
                    "store",
                    "category",
                )
                .filter(
                    pk=self.kwargs["product_id"],
                    vendor__user=self.request.user,
                )
                .first()
            )

        return self._product

    # ----------------------------------------------------------
    # Queryset
    # ----------------------------------------------------------

    def get_queryset(self):
        """
        Return images belonging to the vendor-owned product.
        """

        product = self.get_product()

        if product is None:
            return ProductImage.objects.none()

        return (
            ProductImage.objects
            .filter(
                product_id=product.pk,
            )
            .select_related("product")
            .order_by(
                "display_order",
                "created_at",
            )
        )

    # ----------------------------------------------------------
    # Create
    # ----------------------------------------------------------

    def perform_create(self, serializer):
        """
        Delegate image creation and primary-image management
        to ProductImageService.
        """

        product = self.get_product()

        if product is None:
            raise NotFound("Product not found.")

        image = ProductImageService.create_image(
            product=product,
            validated_data=dict(
                serializer.validated_data
            ),
        )

        serializer.instance = image


class ProductImageDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    """
    Retrieve, update, or delete an image belonging to a
    vendor-owned product.

    Image lifecycle operations are delegated to
    ProductImageService.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = ProductImageSerializer

    # ----------------------------------------------------------
    # Queryset
    # ----------------------------------------------------------

    def get_queryset(self):
        """
        Restrict image access to images belonging to products
        owned by the authenticated vendor.
        """

        return (
            ProductImage.objects
            .filter(
                product_id=self.kwargs["product_id"],
                product__vendor__user=self.request.user,
            )
            .select_related(
                "product",
                "product__vendor",
                "product__store",
            )
            .order_by(
                "display_order",
                "created_at",
            )
        )

    # ----------------------------------------------------------
    # Update
    # ----------------------------------------------------------

    def perform_update(self, serializer):
        """
        Delegate update and primary-image lifecycle handling
        to ProductImageService.
        """

        image = ProductImageService.update_image(
            image=self.get_object(),
            validated_data=dict(
                serializer.validated_data
            ),
        )

        serializer.instance = image

    # ----------------------------------------------------------
    # Delete
    # ----------------------------------------------------------

    def perform_destroy(self, instance):
        """
        Delegate deletion and primary-image replacement handling
        to ProductImageService.
        """

        ProductImageService.delete_image(
            image=instance,
        )