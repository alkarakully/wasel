from django.conf import settings
from django.db import models


class Device(models.Model):
    """A phone that can receive push notifications for one of the Wasel apps."""

    class Platform(models.TextChoices):
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"

    class App(models.TextChoices):
        CUSTOMER = "customer", "Customer app"
        CAPTAIN = "captain", "Captain app"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="devices")
    # The app instance's Firebase Installation ID, FCM's send target.
    fid = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=10, choices=Platform.choices)
    app = models.CharField(max_length=10, choices=App.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} {self.get_app_display()} on {self.get_platform_display()}"
