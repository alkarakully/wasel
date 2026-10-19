import secrets

from django.db import transaction

from accounts.models import User

from .models import StaffProfile


def placeholder_phone():
    """Staff sign in by email; the phone column still needs a unique value."""
    while True:
        phone = f"staff:{secrets.token_hex(6)}"
        if not User.objects.filter(phone=phone).exists():
            return phone


@transaction.atomic
def create_staff(email, name, role, password, user=None):
    """A platform admin account. Pass `user` to give an existing staff account (e.g. a superuser) a console login."""
    if user is None:
        user = User(phone=placeholder_phone(), name=name, is_staff=True)
    else:
        user.is_staff = True
        if name and not user.name:
            user.name = name
    user.set_password(password)
    user.save()
    return StaffProfile.objects.create(user=user, email=email.strip().lower(), role=role)


def active_admins():
    return StaffProfile.objects.filter(role=StaffProfile.Role.ADMIN, user__is_active=True)
