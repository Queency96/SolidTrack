from django.db import transaction
from vendors.models import ProductImage


class ProductImageService:

    @staticmethod
    @transaction.atomic
    def create_image(
        *,
        product,
        validated_data,
    ):
        """
        Create a product image and ensure the product
        has a valid primary image.
        """
        requested_primary = validated_data.pop(
            "is_primary",
            False,
        )

        image = ProductImage.objects.create(
            product=product,
            is_primary=False,
            **validated_data,
        )

        if requested_primary:
            ProductImageService.make_primary(
                image=image,
            )
        else:
            ProductImageService.ensure_primary(
                product_id=product.pk,
            )

        return image

    @staticmethod
    @transaction.atomic
    def update_image(
        *,
        image,
        validated_data,
    ):
        """
        Update a product image and maintain the
        primary-image invariant.
        """
        requested_primary = validated_data.pop(
            "is_primary",
            image.is_primary,
        )

        for field, value in validated_data.items():
            setattr(
                image,
                field,
                value,
            )

        image.save()

        if requested_primary:
            ProductImageService.make_primary(
                image=image,
            )
        elif image.is_primary:
            ProductImageService.ensure_primary(
                product_id=image.product_id,
            )

        return image

    @staticmethod
    @transaction.atomic
    def delete_image(
        *,
        image,
    ):
        """
        Delete an image.

        If the deleted image was primary, promote the
        first active image.
        """
        product_id = image.product_id
        was_primary = image.is_primary

        image.delete()

        if was_primary:
            ProductImageService.ensure_primary(
                product_id=product_id,
            )

    @staticmethod
    def make_primary(
        *,
        image,
    ):
        """
        Make one image the primary image for its product.
        """
        (
            ProductImage.objects
            .filter(
                product_id=image.product_id,
                is_primary=True,
            )
            .exclude(
                pk=image.pk,
            )
            .update(
                is_primary=False,
            )
        )

        if not image.is_primary:
            image.is_primary = True

            image.save(
                update_fields=[
                    "is_primary",
                    "updated_at",
                ]
            )

    @staticmethod
    def ensure_primary(
        *,
        product_id,
    ):
        """
        Ensure the product has an active primary image.

        If no primary image exists, the first active image
        by display order becomes primary.
        """
        primary_exists = (
            ProductImage.objects
            .filter(
                product_id=product_id,
                is_primary=True,
                is_active=True,
            )
            .exists()
        )

        if primary_exists:
            return

        replacement = (
            ProductImage.objects
            .filter(
                product_id=product_id,
                is_active=True,
            )
            .order_by(
                "display_order",
                "created_at",
            )
            .first()
        )

        if replacement is None:
            return

        (
            ProductImage.objects
            .filter(
                pk=replacement.pk,
            )
            .update(
                is_primary=True,
            )
        )