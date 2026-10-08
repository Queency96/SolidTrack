from django.urls import path

from .web_hook_view import paystack_webhook


urlpatterns = [
    path(
        "webhooks/paystack/",
        paystack_webhook,
        name="paystack-webhook",
    ),
]