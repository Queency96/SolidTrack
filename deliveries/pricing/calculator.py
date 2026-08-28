from decimal import Decimal

from .distance import DistancePricingStrategy
from .package import PackagePricingStrategy
from .vehicle import VehiclePricingStrategy
from .insurance import InsurancePricingStrategy
from .surge import SurgePricingStrategy
from .discount import DiscountPricingStrategy
from .service_fee import ServiceFeeStrategy


class PricingCalculator:

    def __init__(self):

        self.distance = DistancePricingStrategy()
        self.package = PackagePricingStrategy()
        self.vehicle = VehiclePricingStrategy()
        self.insurance = InsurancePricingStrategy()
        self.surge = SurgePricingStrategy()
        self.discount = DiscountPricingStrategy()
        self.service_fee = ServiceFeeStrategy()

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

        Returns a complete pricing breakdown.
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
        # Base
        # ==================================================

        base_price = Decimal(
            str(config.base_price)
        )

        # ==================================================
        # Distance
        # ==================================================

        distance_price = self.distance.calculate(
            config,
            distance,
        )

        distance_price = Decimal(
            str(distance_price)
        )

        # ==================================================
        # Package
        # ==================================================

        package_fee = self.package.calculate(
            config,
            package_size,
        )

        package_fee = Decimal(
            str(package_fee)
        )

        # ==================================================
        # Vehicle
        # ==================================================

        multiplier = self.vehicle.calculate(
            config,
            vehicle_type,
        )

        multiplier = Decimal(
            str(multiplier)
        )

        # ==================================================
        # Delivery Subtotal
        # ==================================================

        subtotal = (
            base_price
            + distance_price
            + package_fee
        )

        subtotal *= multiplier

        subtotal = subtotal.quantize(
            Decimal("0.01")
        )

        # ==================================================
        # Surge
        # ==================================================

        surge = self.surge.calculate(
            config,
            subtotal,
        )

        surge = Decimal(
            str(surge)
        ).quantize(
            Decimal("0.01")
        )

        # ==================================================
        # Insurance
        # ==================================================

        insurance_fee = self.insurance.calculate(
            config,
            insurance,
            declared_value,
        )

        insurance_fee = Decimal(
            str(insurance_fee)
        ).quantize(
            Decimal("0.01")
        )

        # ==================================================
        # Service Fee
        # ==================================================

        service_fee = self.service_fee.calculate(
            config,
        )

        service_fee = Decimal(
            str(service_fee)
        ).quantize(
            Decimal("0.01")
        )

        # ==================================================
        # Discount
        # ==================================================

        discount = self.discount.calculate(
            customer,
            subtotal,
            coupon,
        )

        discount = Decimal(
            str(discount)
        ).quantize(
            Decimal("0.01")
        )

        if discount < Decimal("0.00"):
            discount = Decimal("0.00")

        # Never allow discount to exceed subtotal
        # unless your discount strategy explicitly
        # supports discounting additional charges.

        if discount > subtotal:
            discount = subtotal

        # ==================================================
        # Total
        # ==================================================

        total = (
            subtotal
            + surge
            + insurance_fee
            + service_fee
            - discount
        )

        if total < Decimal("0.00"):
            total = Decimal("0.00")

        total = total.quantize(
            Decimal("0.01")
        )

        # ==================================================
        # Result
        # ==================================================

        return {
            "base_price": base_price.quantize(
                Decimal("0.01")
            ),

            "distance_price": distance_price.quantize(
                Decimal("0.01")
            ),

            "package_fee": package_fee.quantize(
                Decimal("0.01")
            ),

            "vehicle_multiplier": multiplier,

            "subtotal": subtotal,

            "surge_fee": surge,

            "insurance_fee": insurance_fee,

            "service_fee": service_fee,

            "discount": discount,

            "total": total,
        }