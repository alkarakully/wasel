import os
import sys
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key" if DEBUG else None)
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off")

# The Django admin is an emergency tool for superusers, at a path only the team knows.
# /admin/ is the platform admin app (apps/admin). Set a long random path in production.
DJANGO_ADMIN_PATH = os.environ.get("DJANGO_ADMIN_PATH", "django-admin/").strip("/") + "/"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
# Full origins (scheme and host) allowed to post forms, e.g. https://wasel.example.com
CSRF_TRUSTED_ORIGINS = [origin for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if origin]

if not DEBUG:
    # Behind nginx, which terminates HTTPS and says so in X-Forwarded-Proto.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    # Docker health checks call this over plain HTTP from inside the network.
    SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", 60 * 60 * 24 * 30))
    SECURE_REFERRER_POLICY = "same-origin"

INSTALLED_APPS = [
    # Daphne first so `runserver` serves HTTP and WebSockets (ASGI).
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "rest_framework",
    "rest_framework.authtoken",
    "channels",
    "accounts",
    "subscriptions",
    "vendors",
    "orders",
    "ops",
    "billing",
    "console",
    "regions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "wasel.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Project-wide overrides, e.g. the branded admin header.
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "wasel.wsgi.application"
ASGI_APPLICATION = "wasel.asgi.application"

TESTING = "test" in sys.argv

# Live order updates go through Redis so every server process can reach every socket.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [os.environ.get("REDIS_URL", "redis://localhost:6379/0")]},
    }
}
if TESTING:
    # Tests must never reach real sockets: a test order for a test store whose
    # id matches a real one would ring that store's real tablets.
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Background jobs. Beat runs the periodic checks below.
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_TASK_IGNORE_RESULT = True
# Tests run tasks inline instead of needing a broker.
CELERY_TASK_ALWAYS_EAGER = TESTING
CELERY_TIMEZONE = "Asia/Baghdad"
CELERY_BEAT_SCHEDULE = {
    "flag-stuck-orders": {"task": "orders.tasks.flag_stuck_orders", "schedule": 60.0},
    "expire-wasel-plus-trials": {"task": "subscriptions.tasks.expire_wasel_plus_trials", "schedule": 15 * 60.0},
    "sweep-dispatch-offers": {"task": "orders.tasks.sweep_dispatch_offers", "schedule": 15.0},
    # Weekly store statements; does nothing until a week has ended.
    "close-billing-weeks": {"task": "billing.tasks.close_weeks", "schedule": 60 * 60.0},
}

DATABASES = {
    "default": dj_database_url.config(
        default="postgis://wasel:wasel@localhost:5432/wasel",
        conn_max_age=60,
    )
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Baghdad"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Product photos stores upload. Production keeps them on a volume nginx serves.
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.DeviceTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    # Per client IP, on top of the per-phone limits in OTP below.
    "DEFAULT_THROTTLE_RATES": {
        "otp_request": "10/hour",
        "otp_verify": "30/hour",
        # Phone/email + password sign-in, per IP; accounts also lock after 5 wrong passwords.
        "password_login": "30/hour",
        # Platform admin sign-in, per IP; accounts also lock after 5 wrong passwords.
        "console_login": "30/hour",
    },
}

# Email for login codes: any SMTP provider (Gmail/Workspace, Zoho, Mailgun, Brevo, SES SMTP...).
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "0") == "1"
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Wasel <no-reply@localhost>")

# Phone login codes.
OTP = {
    "CODE_TTL_SECONDS": 300,
    "RESEND_SECONDS": 60,
    "MAX_PER_HOUR": 5,
    "MAX_ATTEMPTS": 5,
    "SENDERS": {
        "whatsapp": (
            "accounts.otp.WhatsAppCloudSender"
            if os.environ.get("WHATSAPP_TOKEN")
            else "accounts.otp.ConsoleSender"
            if DEBUG
            else "accounts.otp.UnconfiguredSender"
        ),
        # Through the SMTP server above; to the server log in development without one.
        "email": (
            "accounts.otp.EmailSender"
            if os.environ.get("EMAIL_HOST")
            else "accounts.otp.ConsoleSender"
            if DEBUG
            else "accounts.otp.UnconfiguredSender"
        ),
    },
}

# Cart limits. Fees, tips and Wasel Plus thresholds are per country, in its
# currency (regions/regions.py); tune them here per country, e.g.
# REGIONS = {"SA": {"SERVICE_FEE": "1.5"}, "IQ": {"DELIVERY_BASE_FEE": 2000}}.
# How customers may pay. Cash on delivery only for now; the Wasel Wallet
# ("wallet") can be switched back on here (comma-separated) without app changes.
PAYMENT_METHODS = [m.strip() for m in os.environ.get("PAYMENT_METHODS", "cod").split(",") if m.strip()]

ORDER_PRICING = {
    "MAX_ITEM_QUANTITY": 50,
    "MAX_KG": 50,
}
REGIONS = {}

# Minutes an order may sit in a step before support is alerted.
STUCK_ORDER_MINUTES = {
    "not_accepted": 5,  # after it was placed
    "not_ready": 15,  # past the store's estimated ready time
    "no_captain": 10,  # after the store accepted
    "not_picked_up": 15,  # after it was marked ready
    "delivery_late": 60,  # after pickup
}

WASEL_PLUS_TRIAL_DAYS = 14

# Automatic dispatch: each accepted order is offered to the nearest free captain.
DISPATCH = {
    "OFFER_SECONDS": 30,  # how long one captain has to accept
    "RADIUS_KM": 5,  # captain to store
    "STALE_MINUTES": 10,  # ignore captains whose last GPS fix is older
}

# Vector map styles for web pages. OpenFreeMap needs no API key; set a licensed
# provider's style URLs (Mapbox, MapTiler) here if traffic outgrows it.
MAP_STYLES = {
    "light": os.environ.get("MAP_STYLE_LIGHT", "https://tiles.openfreemap.org/styles/positron"),
    "dark": os.environ.get("MAP_STYLE_DARK", "https://tiles.openfreemap.org/styles/dark"),
}

WHATSAPP = {
    "TOKEN": os.environ.get("WHATSAPP_TOKEN", ""),
    "PHONE_NUMBER_ID": os.environ.get("WHATSAPP_PHONE_NUMBER_ID", ""),
    "TEMPLATE": os.environ.get("WHATSAPP_TEMPLATE", "wasel_login_code"),
    "TEMPLATE_LANGUAGE": os.environ.get("WHATSAPP_TEMPLATE_LANGUAGE", "ar"),
    "API_VERSION": os.environ.get("WHATSAPP_API_VERSION", "v21.0"),
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "WARNING")},
}
