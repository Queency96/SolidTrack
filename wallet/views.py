from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    WalletSerializer,
    WalletTransactionSerializer,
)


class WalletView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        serializer = WalletSerializer(
            request.user.wallet
        )

        return Response(serializer.data)


class WalletTransactionView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        transactions = (
            request.user.wallet.transactions
            .all()
            .order_by("-created_at")
        )

        serializer = WalletTransactionSerializer(
            transactions,
            many=True
        )

        return Response(serializer.data)