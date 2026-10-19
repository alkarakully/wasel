"""
What each Wasel staff role may see and change in the platform admin.

Every console endpoint names its area; reading needs the role in READ,
changing anything needs it in WRITE. The server enforces this; the admin app
only hides what a role can't use.
"""

from rest_framework import permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.views import APIView

from .models import StaffProfile

R = StaffProfile.Role
EVERYONE = set(R.values)

READ = {
    "overview": EVERYONE,
    "stores": {R.ADMIN, R.OPERATIONS, R.SUPPORT, R.MARKETING, R.FINANCE},
    "orders": {R.ADMIN, R.OPERATIONS, R.SUPPORT, R.FINANCE},
    "people": {R.ADMIN, R.OPERATIONS, R.SUPPORT, R.FINANCE},
    "money": {R.ADMIN, R.FINANCE},
    "marketing": {R.ADMIN, R.MARKETING, R.OPERATIONS},
    "reports": {R.ADMIN, R.OPERATIONS, R.FINANCE, R.MARKETING},
    "staff": {R.ADMIN},
    "audit": {R.ADMIN},
}

WRITE = {
    "overview": set(),
    "stores": {R.ADMIN, R.OPERATIONS},
    "orders": {R.ADMIN, R.OPERATIONS, R.SUPPORT},
    "people": {R.ADMIN, R.OPERATIONS, R.SUPPORT},
    "money": {R.ADMIN, R.FINANCE},
    "marketing": {R.ADMIN, R.MARKETING},
    "reports": set(),
    "staff": {R.ADMIN},
    "audit": set(),
}

# Set in the session once password and authenticator code both passed.
VERIFIED = "console_verified_user"


def staff_profile(request):
    """The signed-in, fully verified staff member's profile, or None."""
    user = request.user
    if not (user and user.is_authenticated and user.is_active and user.is_staff):
        return None
    if request.session.get(VERIFIED) != user.pk:
        return None
    return StaffProfile.objects.filter(user=user).first()


def areas_for(role):
    return {
        area: "write" if role in WRITE[area] else "read"
        for area, roles in READ.items()
        if role in roles
    }


class ConsolePermission(permissions.BasePermission):
    message = "Sign in to the platform admin."

    def has_permission(self, request, view):
        profile = staff_profile(request)
        if profile is None:
            return False
        request.staff = profile
        area = getattr(view, "area", None)
        allowed = WRITE if request.method not in permissions.SAFE_METHODS else READ
        if area is not None and profile.role not in allowed[area]:
            self.message = "Your role can't do this."
            return False
        return True


class ConsoleView(APIView):
    """Base for console endpoints: session cookie (with CSRF), verified staff, role rules."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [ConsolePermission]
    area = None
