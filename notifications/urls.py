from django.urls import path

from .views import (
    NotificationListView,
    NotificationCountView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
)

urlpatterns = [
    path("", NotificationListView.as_view(),),
    path("count/", NotificationCountView.as_view(),),
    path("<int:pk>/read/", MarkNotificationReadView.as_view(),),
    path("read-all/", MarkAllNotificationsReadView.as_view(),),
]