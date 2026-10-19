"""
Keep live sockets in step with who may see what. Socket groups are chosen
when a socket connects, so any change to a person's access closes their
sockets and the app reconnects with the right groups (or is refused).
"""

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from accounts.models import User
from vendors import access
from vendors.models import StoreMember, Vendor

from .realtime import revoke_sockets


@receiver(post_save, sender=StoreMember)
@receiver(post_delete, sender=StoreMember)
def membership_changed(sender, instance, **kwargs):
    # Added: join the store's orders now. Removed: stop seeing them now.
    revoke_sockets(instance.user_id)


@receiver(pre_save, sender=User)
def _remember_access(sender, instance, **kwargs):
    if instance.pk:
        old = User.objects.filter(pk=instance.pk).values("is_active", "role", "is_staff").first()
        instance._old_access = old


@receiver(post_save, sender=User)
def account_changed(sender, instance, created, **kwargs):
    old = getattr(instance, "_old_access", None)
    if created or old is None:
        return
    if (old["is_active"], old["role"], old["is_staff"]) != (instance.is_active, instance.role, instance.is_staff):
        revoke_sockets(instance.pk)


@receiver(post_delete, sender=Token)
def signed_out(sender, instance, **kwargs):
    # Logging out deletes the token; a socket opened with it must not live on.
    revoke_sockets(instance.user_id)


@receiver(pre_save, sender=Vendor)
def _remember_owner(sender, instance, **kwargs):
    if instance.pk:
        instance._old_store = Vendor.objects.filter(pk=instance.pk).values("owner_id", "status").first()


@receiver(post_save, sender=Vendor)
def owner_changed(sender, instance, created, **kwargs):
    old = getattr(instance, "_old_store", None)
    if created or not old:
        return
    if old["owner_id"] != instance.owner_id:
        revoke_sockets(old["owner_id"])
        revoke_sockets(instance.owner_id)
    elif old["status"] != instance.status:
        # Approved: the team joins the store's orders. Taken back: they stop.
        for user_id in access.staff_ids(instance):
            revoke_sockets(user_id)
