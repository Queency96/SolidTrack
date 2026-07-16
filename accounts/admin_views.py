from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdmin

from vendors.models import VendorProfile
from riders.models import RiderProfile

from .admin_services import AdminApprovalService



class ApproveVendorView(APIView):

    permission_classes = (
        IsAuthenticated,
        IsAdmin,
    )

    def post(self, request, pk):

        vendor = VendorProfile.objects.get(pk=pk)

        AdminApprovalService.approve_vendor(
            request.user,
            vendor,
        )

        return Response(
            {
                "success": True
            }
        )




class RejectVendorView(APIView):

    permission_classes = (
        IsAuthenticated,
        IsAdmin,
    )

    def post(self, request, pk):

        vendor = VendorProfile.objects.get(pk=pk)

        AdminApprovalService.reject_vendor(
            request.user,
            vendor,
            request.data.get(
                "reason",
                "",
            ),
        )

        return Response(
            {
                "success": True
            }
        )



class ApproveRiderView(APIView):

    permission_classes = (
        IsAuthenticated,
        IsAdmin,
    )

    def post(self, request, pk):

        rider = RiderProfile.objects.get(pk=pk)

        AdminApprovalService.approve_rider(
            request.user,
            rider,
        )

        return Response(
            {
                "success": True
            }
        )



class RejectRiderView(APIView):

    permission_classes = (
        IsAuthenticated,
        IsAdmin,
    )

    def post(self, request, pk):

        rider = RiderProfile.objects.get(pk=pk)

        AdminApprovalService.reject_rider(
            request.user,
            rider,
            request.data.get(
                "reason",
                "",
            ),
        )

        return Response(
            {
                "success": True
            }
        )



