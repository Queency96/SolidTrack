from django.urls import path

from .views import (
    DispatchDeliveryCreatedView,
    DispatchDeliveryView,
    RetryDispatchView,
    DeliveryOfferResponseView,
    ExpireDeliveryOfferView,
    DeliveryAssignmentDetailView,
    RiderCurrentAssignmentView,
    RiderAssignmentsView,
    DeliveryOffersView,
    DeliveryOfferDetailView,
    AcceptAssignmentView,
    StartPickupView,
    ArrivePickupView,
    PickupCompletedView,
    StartDeliveryView,
    ArriveDestinationView,
    CompleteDeliveryView,
    CancelAssignmentView,
)

urlpatterns = [

    # ==========================================
    # Dispatch
    # ==========================================

    path(
        "deliveries/<uuid:pk>/dispatch/",
        DispatchDeliveryView.as_view(),
        name="dispatch-delivery",
    ),

    path(
        "deliveries/<uuid:pk>/dispatch/retry/",
        RetryDispatchView.as_view(),
        name="retry-dispatch",
    ),

    path(
        "deliveries/<uuid:pk>/dispatch/create/",
        DispatchDeliveryCreatedView.as_view(),
        name="dispatch-created",
    ),

    # ==========================================
    # Offers
    # ==========================================

    path(
        "offers/",
        DeliveryOffersView.as_view(),
        name="delivery-offers",
    ),

    path(
        "offers/<uuid:pk>/",
        DeliveryOfferDetailView.as_view(),
        name="delivery-offer-detail",
    ),

    path(
        "offers/<uuid:pk>/respond/",
        DeliveryOfferResponseView.as_view(),
        name="delivery-offer-response",
    ),

    path(
        "offers/<uuid:pk>/expire/",
        ExpireDeliveryOfferView.as_view(),
        name="expire-delivery-offer",
    ),

    # ==========================================
    # Assignments
    # ==========================================

    path(
        "assignments/current/",
        RiderCurrentAssignmentView.as_view(),
        name="current-assignment",
    ),

    path(
        "assignments/",
        RiderAssignmentsView.as_view(),
        name="assignment-list",
    ),

    path(
        "assignments/<uuid:pk>/",
        DeliveryAssignmentDetailView.as_view(),
        name="assignment-detail",
    ),

    path(
        "assignments/<uuid:pk>/accept/",
        AcceptAssignmentView.as_view(),
        name="assignment-accept",
    ),

    path(
        "assignments/<uuid:pk>/start-pickup/",
        StartPickupView.as_view(),
        name="assignment-start-pickup",
    ),

    path(
        "assignments/<uuid:pk>/arrive-pickup/",
        ArrivePickupView.as_view(),
        name="assignment-arrive-pickup",
    ),

    path(
        "assignments/<uuid:pk>/pickup-completed/",
        PickupCompletedView.as_view(),
        name="assignment-pickup-completed",
    ),

    path(
        "assignments/<uuid:pk>/start-delivery/",
        StartDeliveryView.as_view(),
        name="assignment-start-delivery",
    ),

    path(
        "assignments/<uuid:pk>/arrive-destination/",
        ArriveDestinationView.as_view(),
        name="assignment-arrive-destination",
    ),

    path(
        "assignments/<uuid:pk>/complete/",
        CompleteDeliveryView.as_view(),
        name="assignment-complete",
    ),

    path(
        "assignments/<uuid:pk>/cancel/",
        CancelAssignmentView.as_view(),
        name="assignment-cancel",
    ),

]