from django.urls import path
from cart.views.cart import (
    CartDetailView,
    CartSummaryView,
    CartAddItemView,
    CartItemCreateView,
    CartItemDetailView,
    CartItemIncreaseView,
    CartItemDecreaseView,
    CartClearView,
    CartValidateView,
    CartCheckoutValidationView,
    CartItemUpdateView,
    CartItemRemoveView,
)


urlpatterns = [

    # ==============================================
    # Cart
    # ==============================================

    path(
        "cart/add-item/",
        CartAddItemView.as_view(),
        name="cart-add-item",
    ),


    path(
        "cart/",
        CartDetailView.as_view(),
        name="cart-detail",
    ),

    path(
        "cart/summary/",
        CartSummaryView.as_view(),
        name="cart-summary",
    ),

    # ==============================================
    # Cart Items
    # ==============================================

    path(
        "cart/items/<uuid:pk>/",
        CartItemCreateView.as_view(),
        name="cart-item-create",
    ),

    path(
        "cart/items/<uuid:pk>/",
        CartItemDetailView.as_view(),
        name="cart-item-detail",
    ),

    path(
        "cart/items/qunty-upd/<uuid:pk>/",
        CartItemUpdateView.as_view(),
        name="cart-item-quantity-update", #update one cart item quantity
    ),

    path(
        "cart/items/<uuid:pk>/increase/",
        CartItemIncreaseView.as_view(),
        name="cart-item-increase",
    ),

    path(
        "cart/items/<uuid:pk>/decrease/",
        CartItemDecreaseView.as_view(),
        name="cart-item-decrease",
    ),

    path(
        "cart/items/delete/<uuid:pk>/",
        CartItemRemoveView.as_view(),    #delete one item from cart items
        name="cart-item-remove",
    ),

    # ==============================================
    # Cart Management
    # ==============================================

    path(
        "cart/clear/",
        CartClearView.as_view(),
        name="cart-clear",
    ),

    # ==============================================
    # Cart Validation
    # ==============================================

    path(
        "cart/validate/",
        CartValidateView.as_view(),
        name="cart-validate",
    ),

    path(
        "cart/checkout-validation/",
        CartCheckoutValidationView.as_view(),
        name="cart-checkout-validation",
    ),

]