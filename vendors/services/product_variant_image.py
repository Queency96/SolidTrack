from django.db import transaction

from vendors.models import (
    ProductVariant,
    ProductVariantImage,
)


class ProductVariantImageService:
    """
    Service responsible for the complete lifecycle of
    ProductVariantImage objects.

    Responsibilities
    ----------------
    - Create variant images.
    - Update variant images.
    - Delete variant images.
    - Make an image primary.
    - Ensure a variant has a valid primary image.
    - Maintain the one-primary-image-per-variant invariant.

    Important
    ---------
    ProductVariantImage belongs to a ProductVariant.

    It does NOT belong directly to Product.

    Therefore:

        Product
            ↓
        ProductVariant
            ↓
        ProductVariantImage
    """

    # ==========================================================
    # CREATE
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_image(
        *,
        variant,
        validated_data,
    ):
        """
        Create an image for a product variant.

        If is_primary=True is requested, the new image
        becomes the primary image.

        If this is the first active image for the variant,
        it automatically becomes primary.
        """

        requested_primary = validated_data.pop(
            "is_primary",
            False,
        )

        image = ProductVariantImage.objects.create(
            variant=variant,
            is_primary=False,
            **validated_data,
        )

        if requested_primary:
            ProductVariantImageService.make_primary(
                image=image,
            )
        else:
            ProductVariantImageService.ensure_primary(
                variant_id=variant.pk,
            )

        return image

    # ==========================================================
    # UPDATE
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def update_image(
        *,
        image,
        validated_data,
    ):
        """
        Update an existing variant image.

        If is_primary=True is supplied, the image becomes
        the only primary image for the variant.

        If is_primary=False is explicitly supplied on the
        current primary image, another active image is
        promoted automatically.
        """

        requested_primary = validated_data.pop(
            "is_primary",
            image.is_primary,
        )

        was_primary = image.is_primary

        for field, value in validated_data.items():
            setattr(
                image,
                field,
                value,
            )

        image.save()

        if requested_primary:
            ProductVariantImageService.make_primary(
                image=image,
            )
            return image

        # If the current primary image was explicitly
        # changed to non-primary, ensure another image
        # becomes primary.
        if was_primary and not requested_primary:
            ProductVariantImageService.ensure_primary(
                variant_id=image.variant_id,
                exclude_image_id=image.pk,
            )

        return image

    # ==========================================================
    # DELETE
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def delete_image(
        *,
        image,
    ):
        """
        Delete a variant image.

        If the deleted image was primary, another active
        image is automatically promoted.
        """

        variant_id = image.variant_id
        was_primary = image.is_primary

        image.delete()

        if was_primary:
            ProductVariantImageService.ensure_primary(
                variant_id=variant_id,
            )

    # ==========================================================
    # MAKE PRIMARY
    # ==========================================================

    @staticmethod
    def make_primary(
        *,
        image,
    ):
        """
        Make an image the primary image for its variant.

        Any existing primary image belonging to the same
        variant is demoted.
        """

        (
            ProductVariantImage.objects
            .filter(
                variant_id=image.variant_id,
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

    # ==========================================================
    # ENSURE PRIMARY
    # ==========================================================

    @staticmethod
    def ensure_primary(
        *,
        variant_id,
        exclude_image_id=None,
    ):
        """
        Ensure that a variant has one active primary image.

        Selection priority:

        1. Existing active primary image.
        2. First active image by display_order.
        3. created_at as deterministic fallback.

        If there are no active images, nothing is promoted.
        """

        primary_queryset = (
            ProductVariantImage.objects
            .filter(
                variant_id=variant_id,
                is_primary=True,
                is_active=True,
            )
        )

        if exclude_image_id is not None:
            primary_queryset = primary_queryset.exclude(
                pk=exclude_image_id,
            )

        if primary_queryset.exists():
            return

        replacement_queryset = (
            ProductVariantImage.objects
            .filter(
                variant_id=variant_id,
                is_active=True,
            )
            .order_by(
                "display_order",
                "created_at",
            )
        )

        if exclude_image_id is not None:
            replacement_queryset = (
                replacement_queryset.exclude(
                    pk=exclude_image_id,
                )
            )

        replacement = replacement_queryset.first()

        if replacement is None:
            return

        (
            ProductVariantImage.objects
            .filter(
                pk=replacement.pk,
            )
            .update(
                is_primary=True,
            )
        )

    # ==========================================================
    # VARIANT VALIDATION
    # ==========================================================

    @staticmethod
    def validate_variant(
        *,
        variant,
    ):
        """
        Validate that the supplied variant is a valid
        ProductVariant instance.
        """

        if not isinstance(
            variant,
            ProductVariant,
        ):
            raise TypeError(
                "variant must be a ProductVariant instance."
            )

        return variant

    # ==========================================================
    # BULK CREATE
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_images(
        *,
        variant,
        images,
    ):
        """
        Create multiple images for a variant.

        `images` should be an iterable of dictionaries.

        Example:

            [
                {
                    "image": uploaded_file,
                    "alt_text": "Front view",
                    "display_order": 0,
                    "is_primary": True,
                },
                {
                    "image": uploaded_file,
                    "alt_text": "Back view",
                    "display_order": 1,
                },
            ]

        Only one image will ultimately be primary.
        """

        ProductVariantImageService.validate_variant(
            variant=variant,
        )

        created_images = []

        for image_data in images:
            image = ProductVariantImageService.create_image(
                variant=variant,
                validated_data=image_data,
            )

            created_images.append(image)

        ProductVariantImageService.ensure_primary(
            variant_id=variant.pk,
        )

        return created_images