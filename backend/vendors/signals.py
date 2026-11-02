"""Keep each store's search text in step with its name and menu."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Product, Vendor
from .search import refresh_search_text


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def menu_changed(sender, instance, **kwargs):
    refresh_search_text([instance.vendor_id])


@receiver(post_save, sender=Vendor)
def store_changed(sender, instance, update_fields=None, **kwargs):
    if update_fields is None or "name" in update_fields:
        refresh_search_text([instance.pk])
