from django.shortcuts import render
from rest_framework.generics import (
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import (
    MultiPartParser,
    FormParser,
)
from accounts.permissions import IsCustomer
from .serializers import CustomerProfileSerializer


class CustomerProfileView(
    RetrieveUpdateAPIView
):

    serializer_class = CustomerProfileSerializer

    permission_classes = (
        IsAuthenticated,
        IsCustomer,
    )

    parser_classes = (
        MultiPartParser,
        FormParser,
    )
    def get_object(self):
        return self.request.user.customer_profile