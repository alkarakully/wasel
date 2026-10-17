from django.db.models import Q
from rest_framework import permissions, viewsets

from .models import Order
from .serializers import OrderSerializer


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Orders the signed-in user is part of: as the customer, the captain,
    or the owner of the vendor.
    """

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Order.objects.filter(Q(customer=user) | Q(captain=user) | Q(vendor__owner=user))
            .distinct()
            .prefetch_related("items__modifiers")
        )
