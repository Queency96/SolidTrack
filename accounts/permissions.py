from rest_framework.permissions import BasePermission
from .models import User
from vendors.models import VendorProfile
from riders.models import RiderProfile




class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Roles.CUSTOMER
        )


class IsVendor(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Roles.VENDOR
        )


class IsRider(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Roles.RIDER
        )


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Roles.ADMIN
        )



class IsApprovedVendor(BasePermission):
    def has_permission(self, request, view):

        return (
            request.user.role == User.Roles.VENDOR
            and request.user.vendor_profile.verification_status
            == VendorProfile.VerificationStatus.APPROVED
        )


class IsApprovedRider(BasePermission):
    def has_permission(self, request, view):

        return (
            request.user.role == User.Roles.RIDER
            and request.user.rider_profile.verification_status
            == RiderProfile.VerificationStatus.APPROVED
        )