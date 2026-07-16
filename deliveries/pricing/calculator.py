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
        config,
        distance,
        package_size,
        vehicle_type,
        insurance,
        declared_value,
        customer=None,
        coupon=None,
    ):

        base_price = config.base_price

        distance_price = self.distance.calculate(
            config,
            distance,
        )

        package_fee = self.package.calculate(
            config,
            package_size,
        )

        multiplier = self.vehicle.calculate(
            config,
            vehicle_type,
        )

        subtotal = (
            base_price
            + distance_price
            + package_fee
        )

        subtotal *= multiplier

        subtotal = subtotal.quantize(
            Decimal("0.01")
        )

        surge = self.surge.calculate(
            config,
            subtotal,
        )

        insurance_fee = self.insurance.calculate(
            config,
            insurance,
            declared_value,
        )

        service_fee = self.service_fee.calculate(
            config,
        )

        discount = self.discount.calculate(
            customer,
            subtotal,
            coupon,
        )

        total = (
            subtotal
            + surge
            + insurance_fee
            + service_fee
            - discount
        ).quantize(
            Decimal("0.01")
        )

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