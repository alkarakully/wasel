"""
Who can do what at a store.

  owner    everything: orders, menu and hours, reports, billing, team
  manager  orders, menu and hours, reports
  cashier  orders (accept, reject, ready), stock switches, open/close

The owner is Vendor.owner; everyone else is a StoreMember.
"""

from django.db.models import Q

from .models import StoreMember, Vendor

OWNER = "owner"

ALLOWED = {
    "orders": {OWNER, StoreMember.Role.MANAGER, StoreMember.Role.CASHIER},
    "menu": {OWNER, StoreMember.Role.MANAGER},
    "reports": {OWNER, StoreMember.Role.MANAGER},
    "billing": {OWNER},
    "team": {OWNER},
}


def role_for(vendor, user):
    """'owner', 'manager', 'cashier', or None if the user doesn't work there."""
    if not user or not user.is_authenticated:
        return None
    if vendor.owner_id == user.pk:
        return OWNER
    member = StoreMember.objects.filter(vendor=vendor, user=user).values_list("role", flat=True).first()
    return member


def can(vendor, user, area):
    return role_for(vendor, user) in ALLOWED[area]


def stores_for(user):
    """Stores the user owns or works at."""
    return Vendor.objects.filter(Q(owner=user) | Q(members__user=user)).distinct()


def store_ids_for(user):
    return list(stores_for(user).values_list("pk", flat=True))


def staff_ids(vendor):
    """Everyone who should hear about the store's orders: owner and team."""
    return [vendor.owner_id, *StoreMember.objects.filter(vendor=vendor).values_list("user_id", flat=True)]
