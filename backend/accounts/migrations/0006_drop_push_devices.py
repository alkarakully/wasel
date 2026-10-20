from django.db import migrations


class Migration(migrations.Migration):
    """Wasel no longer sends pushes (no Firebase): drop the old device registry."""

    dependencies = [("accounts", "0005_countries_and_currencies")]

    operations = [
        migrations.RunSQL("DROP TABLE IF EXISTS notifications_device;", reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(
            "DELETE FROM django_migrations WHERE app = 'notifications';", reverse_sql=migrations.RunSQL.noop
        ),
    ]
