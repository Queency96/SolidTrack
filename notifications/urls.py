from django.urls import path

from .views import (
    MarkAllNotificationsReadView,
    MarkNotificationReadView,
    NotificationCountView,
    NotificationListView,
)


urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("count/", NotificationCountView.as_view(), name="notification-count"),

    # Notification.id is a UUIDField — use the UUID converter.
    path(
        "<uuid:pk>/read/",
        MarkNotificationReadView.as_view(),
        name="notification-mark-read",
    ),

    path(
        "read-all/",
        MarkAllNotificationsReadView.as_view(),
        name="notification-mark-all-read",
    ),
]