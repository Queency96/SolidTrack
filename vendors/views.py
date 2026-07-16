from django.shortcuts import render
from rest_framework.generics import (
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.parsers import (
    MultiPartParser,
    FormParser,
)
from accounts.permissions import IsVendor
from .serializers import (
    VendorProfileSerializer,
)


class VendorProfileView(
    RetrieveUpdateAPIView
):

    serializer_class = (
        VendorProfileSerializer
    )

    permission_classes = (
        IsAuthenticated,
        IsVendor,
    )

    parser_classes = (
        MultiPartParser,
        FormParser,
    )

    def get_object(self):

        return (
            self.request.user.vendor_profile
        )