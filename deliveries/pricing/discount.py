from decimal import Decimal

from .base import PricingStrategy


class DiscountPricingStrategy(PricingStrategy):

    def calculate(
        self,
        customer=None,
        subtotal=None,
        coupon=None,
    ):

        return Decimal("0.00")