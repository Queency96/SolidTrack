from django.utils import timezone
from notifications.services import NotificationService


class AdminApprovalService:

    @staticmethod
    def approve_vendor(admin, vendor):

        vendor.verification_status = (
            vendor.VerificationStatus.APPROVED
        )

        vendor.approved_by = admin

        vendor.approved_at = timezone.now()

        vendor.rejection_reason = ""

        vendor.save()

        NotificationService.create_notification(
            user=vendor.user,
            title="Vendor Approved",
            message="Your business account has been approved.",
            notification_type="SYSTEM",
        )

    @staticmethod
    def reject_vendor(
        admin,
        vendor,
        reason,
    ):

        vendor.verification_status = (
            vendor.VerificationStatus.REJECTED
        )

        vendor.approved_by = admin

        vendor.approved_at = timezone.now()

        vendor.rejection_reason = reason

        vendor.save()

        NotificationService.create_notification(
            user=vendor.user,
            title="Vendor Verification Rejected",
            message=reason,
            notification_type="SYSTEM",
        )

    @staticmethod
    def approve_rider(
        admin,
        rider,
    ):

        rider.verification_status = (
            rider.VerificationStatus.APPROVED
        )

        rider.approved_by = admin

        rider.approved_at = timezone.now()

        rider.rejection_reason = ""

        rider.save()

        NotificationService.create_notification(
            user=rider.user,
            title="Rider Approved",
            message="You can now start accepting deliveries.",
            notification_type="SYSTEM",
        )

    @staticmethod
    def reject_rider(
        admin,
        rider,
        reason,
    ):

        rider.verification_status = (
            rider.VerificationStatus.REJECTED
        )

        rider.approved_by = admin

        rider.approved_at = timezone.now()

        rider.rejection_reason = reason

        rider.save()

        NotificationService.create_notification(
            user=rider.user,
            title="Rider Verification Rejected",
            message=reason,
            notification_type="SYSTEM",
        )