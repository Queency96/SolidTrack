from decimal import Decimal
from deliveries.services.pricing_service import PricingService


@staticmethod
def _delivery_fee_calculator(store_group, destination):
    """
    Compute fulfillment-level fees for one store group.

    Uses the store's location as the pickup point and the
    customer's destination address as the dropoff.
    """

    store = store_group["store"]

    if destination is None:
        # No destination yet: return zero fees and let
        # checkout recompute once an address is chosen.
        return {
            "delivery_fee": Decimal("0.00"),
            "service_fee": Decimal("0.00"),
            "insurance_fee": Decimal("0.00"),
            "tax_amount": Decimal("0.00"),
        }

    # Derive package size from the items in the group.
    # This is a placeholder; replace with your real
    # PackageSizingService.
    total_weight = sum(
        (
            (item["unit_weight"] or Decimal("0.000"))
            * item["quantity"]
            for item in store_group["items"]
        ),
        Decimal("0.000"),
    )

    if total_weight <= Decimal("1.000"):
        package_size = "SMALL"
    elif total_weight <= Decimal("5.000"):
        package_size = "MEDIUM"
    else:
        package_size = "LARGE"

    pricing = PricingService.estimate(
        data={
            "pickup_latitude": float(store.latitude),
            "pickup_longitude": float(store.longitude),
            "destination_latitude": float(
                destination["latitude"]
            ),
            "destination_longitude": float(
                destination["longitude"]
            ),
            "package_size": package_size,
            "vehicle_type": None,
            "insurance": False,
            "declared_value": Decimal("0.00"),
        },
        customer=None,
    )

    # The fulfillment's delivery_fee is the sum of the
    # vehicle components + surge.
    delivery_fee = (
        pricing["base_price"]
        + pricing["distance_price"]
        + pricing["package_fee"]
        + pricing["surge_fee"]
    )

    return {
        "delivery_fee": delivery_fee,
        "service_fee": pricing["service_fee"],
        "insurance_fee": pricing["insurance_fee"],
        "tax_amount": Decimal("0.00"),
    }