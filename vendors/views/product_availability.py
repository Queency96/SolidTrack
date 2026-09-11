from uuid import UUID

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsVendor
from vendors.models import Product, VendorProfile


class ProductAvailabilityView(APIView):
    """Check products owned by the authenticated vendor."""

    permission_classes = [IsVendor]

    @staticmethod
    def _normalise_id_value(value):
        if isinstance(value, dict):
            value = value.get("id", value.get("product_id"))

        if value is None:
            return None

        try:
            return UUID(str(value).strip())
        except (AttributeError, TypeError, ValueError):
            return None

    def _get_requested_ids(self, request):
        if getattr(self, "kwargs", {}).get("pk"):
            return [self.kwargs["pk"]], None

        if request.method == "POST":
            payload = request.data

            if isinstance(payload, list):
                raw_ids = payload
            elif isinstance(payload, dict):
                raw_ids = payload.get(
                    "product_ids",
                    payload.get("products", payload.get("ids")),
                )

                if raw_ids is None and "product_id" in payload:
                    raw_ids = [payload["product_id"]]
            else:
                raw_ids = None
        else:
            raw_ids = (
                request.query_params.get("product_ids")
                or request.query_params.get("ids")
            )

            if raw_ids is None:
                raw_ids = request.query_params.get("product_id")

        if raw_ids is None:
            return None, None

        if isinstance(raw_ids, str):
            raw_ids = [
                item.strip()
                for item in raw_ids.split(",")
                if item.strip()
            ]
        elif isinstance(raw_ids, (list, tuple, set)):
            raw_ids = list(raw_ids)
        else:
            return None, "product_ids must be a list of UUID values."

        ids = []

        for value in raw_ids:
            product_id = self._normalise_id_value(value)

            if product_id is None:
                return None, "product_ids must contain valid UUID values."

            if product_id not in ids:
                ids.append(product_id)

        if len(ids) > 100:
            return None, "A maximum of 100 products can be checked at once."

        return ids, None

    @staticmethod
    def _variant_payload(variant):
        return {
            "id": str(variant.pk),
            "name": variant.name,
            "sku": variant.sku,
            "is_available": variant.is_available,
            "is_in_stock": variant.is_in_stock,
            "can_be_purchased": variant.can_be_purchased,
        }

    @staticmethod
    def _product_payload(product):
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
                ProductAvailabilityView._variant_payload(variant)
                for variant in product.variants.all()
            ],
        }

    def _build_response(self, request, product_ids):
        try:
            vendor_profile = request.user.vendor_profile
        except VendorProfile.DoesNotExist:
            return Response(
                {"detail": "Vendor profile not found."},
                status=403,
            )

        queryset = (
            Product.objects
            .select_related("vendor", "store", "category")
            .prefetch_related("variants__option_values__option")
            .filter(vendor=vendor_profile)
            .order_by("name")
        )

        if product_ids is not None:
            queryset = queryset.filter(pk__in=product_ids)

        products = list(queryset)
        product_payloads = [
            self._product_payload(product)
            for product in products
        ]

        response = {
            "products": product_payloads,
            "missing_product_ids": [],
        }

        if product_ids is not None:
            found_ids = {product.pk for product in products}
            response["missing_product_ids"] = [
                str(product_id)
                for product_id in product_ids
                if product_id not in found_ids
            ]

            if len(product_ids) == 1 and product_payloads:
                response["product"] = product_payloads[0]

        return response

    def _handle_request(self, request, *args, **kwargs):
        product_ids, error = self._get_requested_ids(request)

        if error:
            return Response({"detail": error}, status=400)

        response = self._build_response(request, product_ids)

        if isinstance(response, Response):
            return response

        return Response(response)

    def get(self, request, *args, **kwargs):
        return self._handle_request(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self._handle_request(request, *args, **kwargs)


class ProductAvailabilityCheckView(ProductAvailabilityView):
    """Backward-compatible name for the availability view."""
