from django.db import migrations


class Migration(migrations.Migration):
    """Wasel is now Nawsil: rename the subscription model (and its table)."""

    dependencies = [
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.RenameModel("WaselPlusSubscription", "NawsilPlusSubscription"),
    ]
