from django.urls import path

from vendors.views.fulfillments import (
    PendingFulfillmentsView,
    VendorCannotFulfillView,
    VendorFulfillmentDetailView,
)


urlpatterns = [
    path(
        "pending/",
        PendingFulfillmentsView.as_view(),
        name="vendor-pending-fulfillments",
    ),

    path(
        "<uuid:pk>/",
        VendorFulfillmentDetailView.as_view(),
        name="vendor-fulfillment-detail",
    ),

    path(
        "<uuid:pk>/cannot-fulfill/",
        VendorCannotFulfillView.as_view(),
        name="vendor-fulfillment-cannot-fulfill",
    ),
]




# Behaviour recap

# Full failure — item_ids omitted or null:
# json

# POST /api/vendors/fulfillments/<uuid>/cannot-fulfill/
# {
#     "reason": "Store closed due to flooding."
# }


# Response:
# json

# {
#     "fulfillment_status": "failed",
#     "items_marked_unavailable": 4,
#     "refund_amount": "12500.00",
#     "refund_reference": "REF-FULFILLMENT-<fulfillment_uuid>",
#     "is_full_failure": true
# }

# Partial failure — item_ids provided:
# json

# POST /api/vendors/fulfillments/<uuid>/cannot-fulfill/
# {
#     "reason": "One item is out of stock.",
#     "item_ids": ["<order_item_uuid>"]
# }

# Response:
# json

# {
#     "fulfillment_status": "packing",
#     "items_marked_unavailable": 1,
#     "refund_amount": "1500.00",
#     "refund_reference": "REF-FULFILLMENT-<fulfillment_uuid>",
#     "is_full_failure": false
# }


