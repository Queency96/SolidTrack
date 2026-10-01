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
from vendors.views.product_public import PublicProductListView


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



class UserLocationProductListView(PublicProductListView):
    """
    Returns products filtered by the logged-in user's state.
    Inherits all filters (search, category, etc.) from PublicProductListView.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Get the base public product queryset
        queryset = super().get_queryset()
        
        # Filter by the user's state
        user_state = self.request.user.state
        if user_state:
            # Case-insensitive exact match for the store's state
            queryset = queryset.filter(store__state__iexact=user_state)
            
        return queryset