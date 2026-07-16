from ..services import NotificationService



class DispatchNotifier:
    @staticmethod
    def notify(assignment):
        NotificationService.create_notification(
            user=assignment.rider,
            title="New Delivery",
            message=(
                f"You've been assigned "
                f"{assignment.delivery.tracking_number}"
            ),
            notification_type="DELIVERY",
        )