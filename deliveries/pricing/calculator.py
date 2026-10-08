from decimal import Decimal

from .distance import DistancePricingStrategy
from .package import PackagePricingStrategy
from .vehicle import VehiclePricingStrategy
from .insurance import InsurancePricingStrategy
from .surge import SurgePricingStrategy
from .discount import DiscountPricingStrategy
from .service_fee import ServiceFeeStrategy


class PricingCalculator:
    """
    Combine all pricing strategies into one breakdown.

    Vehicle multiplier semantics
    ----------------------------
    The vehicle multiplier scales each per-vehicle cost
    component (base, distance, package) *before* those
    components are summed. This makes the calculator's
    per-component outputs directly usable as the
    corresponding Delivery fields:

        base_price     -> base_price
        distance_price -> distance_price
        package_fee    -> weight_price

    so that Delivery.total_price, which is reconstructed
    as the sum of those fields, matches the calculator's
    total exactly.
    """

    def __init__(self):

        self.distance = DistancePricingStrategy()
        self.package = PackagePricingStrategy()
        self.vehicle = VehiclePricingStrategy()
        self.insurance = InsurancePricingStrategy()
        self.surge = SurgePricingStrategy()
        self.discount = DiscountPricingStrategy()
        self.service_fee = ServiceFeeStrategy()

    # ==================================================
    # Calculate
    # ==================================================

    def calculate(
        self,
        *,
        config,
        distance,
        package_size,
        vehicle_type,
        insurance=False,
        declared_value=Decimal("0.00"),
        customer=None,
        coupon=None,
    ):
        """
        Calculate delivery pricing.

        The calculator does not determine the route.
        Distance must already be supplied by the caller.
        """

        distance = Decimal(str(distance))
        declared_value = Decimal(str(declared_value))

        if distance < Decimal("0.00"):
            raise ValueError(
                "Distance cannot be negative."
            )

        if declared_value < Decimal("0.00"):
            raise ValueError(
                "Declared value cannot be negative."
            )

        # ==================================================
        # Vehicle multiplier
        # ==================================================

        multiplier = self._resolve_vehicle_multiplier(
            config=config,
            vehicle_type=vehicle_type,
        )

        # ==================================================
        # Per-vehicle components (scaled by multiplier)
        # ==================================================

        base_price = self._quantize(
            Decimal(str(config.base_price)) * multiplier
        )

        distance_price = self._quantize(
            Decimal(
                str(
                    self.distance.calculate(
                        config,
                        distance,
                    )
                )
            )
            * multiplier
        )

        package_fee = self._quantize(
            Decimal(
                str(
                    self.package.calculate(
                        config,
                        package_size,
                    )
                )
            )
            * multiplier
        )

        self._reject_negative(
            base_price=base_price,
            distance_price=distance_price,
            package_fee=package_fee,
        )

        # ==================================================
        # Subtotal
        # ==================================================

        subtotal = self._quantize(
            base_price
            + distance_price
            + package_fee
        )

        # ==================================================
        # Surge
        # ==================================================

        surge = self._quantize(
            Decimal(
                str(
                    self.surge.calculate(
                        config,
                        subtotal,
                    )
                )
            )
        )

        if surge < Decimal("0.00"):
            surge = Decimal("0.00")

        # ==================================================
        # Insurance
        # ==================================================

        insurance_fee = self._quantize(
            Decimal(
                str(
                    self.insurance.calculate(
                        config,
                        insurance,
                        declared_value,
                    )
                )
            )
        )

        if insurance_fee < Decimal("0.00"):
            insurance_fee = Decimal("0.00")

        # ==================================================
        # Service Fee
        # ==================================================

        service_fee = self._quantize(
            Decimal(
                str(
                    self.service_fee.calculate(
                        config,
                    )
                )
            )
        )

        if service_fee < Decimal("0.00"):
            service_fee = Decimal("0.00")

        # ==================================================
        # Discount
        # ==================================================

        discount = self._quantize(
            Decimal(
                str(
                    self.discount.calculate(
                        customer,
                        subtotal,
                        coupon,
                    )
                )
            )
        )

        if discount < Decimal("0.00"):
            discount = Decimal("0.00")

        # Discount never exceeds the subtotal.
        if discount > subtotal:
            discount = subtotal

        # ==================================================
        # Total
        # ==================================================

        total = (
            base_price
            + distance_price
            + package_fee
            + surge
            + insurance_fee
            + service_fee
            - discount
        )

        if total < Decimal("0.00"):
            total = Decimal("0.00")

        total = self._quantize(total)

        # ==================================================
        # Result
        # ==================================================

        return {
            "base_price": base_price,
            "distance_price": distance_price,
            "package_fee": package_fee,
            "vehicle_multiplier": multiplier,
            "subtotal": subtotal,
            "surge_fee": surge,
            "insurance_fee": insurance_fee,
            "service_fee": service_fee,
            "discount": discount,
            "total": total,
        }

    # ==================================================
    # Helpers
    # ==================================================

    @staticmethod
    def _quantize(value):
        return Decimal(value).quantize(Decimal("0.01"))

    @staticmethod
    def _reject_negative(**components):

        for name, value in components.items():
            if value < Decimal("0.00"):
                raise ValueError(
                    f"{name} cannot be negative."
                )

    @staticmethod
    def _resolve_vehicle_multiplier(
        *,
        config,
        vehicle_type,
    ):
        if vehicle_type is None:
            # Default to the cheapest supported class.
            return Decimal("1")

        multiplier = Decimal(
            str(
                VehiclePricingStrategy().calculate(
                    config,
                    vehicle_type,
                )
            )
        )

        if multiplier <= Decimal("0"):
            raise ValueError(
                "Vehicle multiplier must be positive."
            )

        return multiplier