import getpass
import os

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from console.models import StaffProfile
from console.staff import create_staff


class Command(BaseCommand):
    help = (
        "Create a platform admin login (email, password; the authenticator is set up at first sign-in). "
        "Use --phone to give an existing staff account, like your superuser, a platform admin login."
    )

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", default="")
        parser.add_argument("--role", default=StaffProfile.Role.ADMIN, choices=StaffProfile.Role.values)
        parser.add_argument("--phone", help="An existing staff account's phone number")
        parser.add_argument(
            "--password-env",
            metavar="VAR",
            help="Read the password from this environment variable instead of asking (for scripts)",
        )

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        if StaffProfile.objects.filter(email=email).exists():
            raise CommandError(f"{email} already has a platform admin login.")
        user = None
        if options["phone"]:
            user = User.objects.filter(phone=options["phone"].strip()).first()
            if user is None or not user.is_staff:
                raise CommandError("No staff account with that phone number.")
            if hasattr(user, "staff_profile"):
                raise CommandError("That account already has a platform admin login.")
        if options["password_env"]:
            password = os.environ.get(options["password_env"], "")
            try:
                password_validation.validate_password(password, user)
            except ValidationError as error:
                raise CommandError(" ".join(error.messages)) from error
        else:
            password = self._password(user)
        profile = create_staff(email, options["name"], options["role"], password, user=user)
        self.stdout.write(self.style.SUCCESS(f"{profile.email} can now sign in at /admin/ as {profile.role}."))

    def _password(self, user):
        while True:
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Password again: "):
                self.stderr.write("Passwords don't match.")
                continue
            try:
                password_validation.validate_password(password, user)
            except ValidationError as error:
                self.stderr.write(" ".join(error.messages))
                continue
            return password
