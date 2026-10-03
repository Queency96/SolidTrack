"""
Deprecated order service.

Order creation is owned by:

    order.services.checkout_service.CheckoutService

This module is retained only to raise a clear error for
any lingering caller of the previous OrderService.checkout
API.
"""


class OrderService:
    """
    Deprecated.

    See module docstring.
    """

    @classmethod
    def checkout(cls, *args, **kwargs):
        raise NotImplementedError(
            "OrderService.checkout has been removed. "
            "Use CheckoutService.create_order(...)."
        )