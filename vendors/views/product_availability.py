from uuid import UUID

from django.db.models import Prefetch
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsVendor
from vendors.models import Product, ProductVariant, VendorProfile


class ProductAvailabilityView(APIView):
    """
    Check product availability for the authenticated vendor.

    Supports:

        GET /products/availability/
        GET /products/availability/<product_id>/

        GET /products/availability/?product_id=<uuid>
        GET /products/availability/?product_ids=<uuid>,<uuid>

        POST /products/availability/
        {
            "product_ids": ["uuid1", "uuid2"]
        }

    A vendor can only inspect products belonging to their own
    VendorProfile.
    """

    permission_classes = [IsVendor]

    MAX_PRODUCTS = 100

    # ------------------------------------------------------------------
    # ID handling
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_id_value(value):
        """
        Convert supported ID input into a UUID instance.

        Supports:
            UUID
            string UUID
            {"id": "..."}
            {"product_id": "..."}
        """
        if isinstance(value, dict):
            value = value.get(
                "id",
                value.get("product_id"),
            )

        if value is None:
            return None

        try:
            return UUID(str(value).strip())
        except (AttributeError, TypeError, ValueError):
            return None

    def _get_requested_ids(self, request):
        """
        Extract and validate requested product IDs.

        Returns:
            (product_ids, error_message)
        """

        # --------------------------------------------------------------
        # /availability/<pk>/
        # --------------------------------------------------------------
        pk = self.kwargs.get("pk")

        if pk is not None:
            product_id = self._normalise_id_value(pk)

            if product_id is None:
                return None, "The product ID must be a valid UUID."

            return [product_id], None

        # --------------------------------------------------------------
        # POST body
        # --------------------------------------------------------------
        if request.method == "POST":
            payload = request.data

            if isinstance(payload, list):
                raw_ids = payload

            elif isinstance(payload, dict):
                raw_ids = payload.get(
                    "product_ids",
                    payload.get(
                        "products",
                        payload.get("ids"),
                    ),
                )

                if raw_ids is None and "product_id" in payload:
                    raw_ids = [payload["product_id"]]

            else:
                raw_ids = None

        # --------------------------------------------------------------
        # GET query parameters
        # --------------------------------------------------------------
        else:
            raw_ids = (
                request.query_params.get("product_ids")
                or request.query_params.get("ids")
            )

            if raw_ids is None:
                product_id = request.query_params.get("product_id")

                if product_id is not None:
                    raw_ids = [product_id]

        # No IDs means:
        # return all products belonging to this vendor.
        if raw_ids is None:
            return None, None

        # --------------------------------------------------------------
        # Normalize comma-separated query parameters.
        # --------------------------------------------------------------
        if isinstance(raw_ids, str):
            raw_ids = [
                item.strip()
                for item in raw_ids.split(",")
                if item.strip()
            ]

        elif isinstance(raw_ids, (list, tuple, set)):
            raw_ids = list(raw_ids)

        else:
            return None, (
                "product_ids must be a list of UUID values."
            )

        # --------------------------------------------------------------
        # Validate IDs and remove duplicates while preserving order.
        # --------------------------------------------------------------
        product_ids = []
        seen = set()

        for value in raw_ids:
            product_id = self._normalise_id_value(value)

            if product_id is None:
                return None, (
                    "product_ids must contain valid UUID values."
                )

            if product_id in seen:
                continue

            seen.add(product_id)
            product_ids.append(product_id)

        # --------------------------------------------------------------
        # Prevent excessively large availability requests.
        # --------------------------------------------------------------
        if len(product_ids) > self.MAX_PRODUCTS:
            return None, (
                f"A maximum of {self.MAX_PRODUCTS} products "
                "can be checked at once."
            )

        return product_ids, None

    # ------------------------------------------------------------------
    # Vendor
    # ------------------------------------------------------------------

    @staticmethod
    def _get_vendor_profile(request):
        """
        Return the authenticated user's VendorProfile.
        """
        try:
            return request.user.vendor_profile
        except VendorProfile.DoesNotExist:
            return None

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _variant_payload(variant):
        """
        Build the availability payload for a product variant.
        """

        return {
            "id": str(variant.pk),
            "name": variant.name,
            "sku": variant.sku,
            "is_available": variant.is_available,
            "is_in_stock": variant.is_in_stock,
            "can_be_purchased": variant.can_be_purchased,
        }

    @classmethod
    def _product_payload(cls, product):
        """
        Build the availability payload for a product.
        """

        availability = product.availability_status()
        store = product.store

        return {
            "id": str(product.pk),
            "name": product.name,
            "slug": product.slug,
            "sku": product.sku,
            "price": str(product.price),
            "stock_quantity": product.stock_quantity,
            "track_inventory": product.track_inventory,
            "is_available": availability["is_available"],
            "availability": availability,
            "store": {
                "id": str(store.pk),
                "name": store.name,
            },
            "variants": [
                cls._variant_payload(variant)
                for variant in product.variants.all()
            ],
        }

    # ------------------------------------------------------------------
    # Queryset
    # ------------------------------------------------------------------

    @staticmethod
    def _get_queryset(vendor_profile):
        """
        Return the optimized product queryset for this vendor.

        Product ownership is enforced at the queryset level.
        """

        variants_queryset = (
            ProductVariant.objects
            .only(
                "id",
                "product_id",
                "name",
                "sku",
                "is_available",
                "is_active",
                "stock_quantity",
                "track_inventory",
            )
            .order_by("sort_order", "name")
        )

        return (
            Product.objects
            .select_related(
                "vendor",
                "store",
                "category",
            )
            .prefetch_related(
                Prefetch(
                    "variants",
                    queryset=variants_queryset,
                )
            )
            .filter(
                vendor=vendor_profile,
            )
            .order_by("name")
        )

    # ------------------------------------------------------------------
    # Response construction
    # ------------------------------------------------------------------

    def _build_response(self, request, product_ids):
        """
        Build the availability response.

        Returns either:
            dict
        or:
            Response
        """

        vendor_profile = self._get_vendor_profile(request)

        if vendor_profile is None:
            return Response(
                {"detail": "Vendor profile not found."},
                status=403,
            )

        queryset = self._get_queryset(vendor_profile)

        if product_ids is not None:
            queryset = queryset.filter(
                pk__in=product_ids,
            )

        products = list(queryset)

        product_payloads = [
            self._product_payload(product)
            for product in products
        ]

        response = {
            "products": product_payloads,
            "missing_product_ids": [],
        }

        # --------------------------------------------------------------
        # When specific IDs were requested, report IDs that either:
        #
        # - do not exist, or
        # - exist but do not belong to this vendor.
        #
        # We deliberately do not expose whether an inaccessible UUID
        # belongs to another vendor.
        # --------------------------------------------------------------
        if product_ids is not None:
            found_ids = {
                product.pk
                for product in products
            }

            response["missing_product_ids"] = [
                str(product_id)
                for product_id in product_ids
                if product_id not in found_ids
            ]

            # Preserve convenient single-product response behavior.
            if len(product_ids) == 1:
                response["product"] = (
                    product_payloads[0]
                    if product_payloads
                    else None
                )

        return response

    # ------------------------------------------------------------------
    # Request handling
    # ------------------------------------------------------------------

    def _handle_request(self, request, *args, **kwargs):
        product_ids, error = self._get_requested_ids(request)

        if error:
            return Response(
                {"detail": error},
                status=400,
            )

        response = self._build_response(
            request,
            product_ids,
        )

        if isinstance(response, Response):
            return response

        return Response(response)

    # ------------------------------------------------------------------
    # HTTP methods
    # ------------------------------------------------------------------

    def get(self, request, *args, **kwargs):
        return self._handle_request(
            request,
            *args,
            **kwargs,
        )

    def post(self, request, *args, **kwargs):
        return self._handle_request(
            request,
            *args,
            **kwargs,
        )


class ProductAvailabilityCheckView(ProductAvailabilityView):
    """
    Backward-compatible alias for the product availability endpoint.
    """

    pass