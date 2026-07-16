from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer
from django.shortcuts import get_object_or_404



class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        notifications = (
            request.user.notifications
            .all()
            .order_by("-created_at")
        )

        serializer = NotificationSerializer(
            notifications,
            many=True
        )

        return Response(serializer.data)




class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        notification = get_object_or_404(
          Notification,
          id=pk,
          user=request.user
        )

        notification.is_read = True

        notification.save(update_fields=["is_read"])

        return Response(
            {
                "success": True
            }
        )



class MarkAllNotificationsReadView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        request.user.notifications.filter(
            is_read=False
        ).update(
            is_read=True
        )

        return Response(
            {
                "success": True
            }
        )


class NotificationCountView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        count = request.user.notifications.filter(
            is_read=False
        ).count()
        return Response(
            {
                "unread_notifications": count
            }
        )