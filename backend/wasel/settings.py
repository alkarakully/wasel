import os
import sys
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key" if DEBUG else None)
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off")

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

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
    "notifications",
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
        "DIRS": [],
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

# Live order updates go through Redis so every server process can reach every socket.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [os.environ.get("REDIS_URL", "redis://localhost:6379/0")]},
    }
}

# Background jobs. Beat runs the periodic checks below.
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_TASK_IGNORE_RESULT = True
# Tests run tasks inline instead of needing a broker.
CELERY_TASK_ALWAYS_EAGER = "test" in sys.argv
CELERY_TIMEZONE = "Asia/Baghdad"
CELERY_BEAT_SCHEDULE = {
    "flag-stuck-orders": {"task": "orders.tasks.flag_stuck_orders", "schedule": 60.0},
    "expire-wasel-plus-trials": {"task": "subscriptions.tasks.expire_wasel_plus_trials", "schedule": 15 * 60.0},
    "sweep-dispatch-offers": {"task": "orders.tasks.sweep_dispatch_offers", "schedule": 15.0},
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

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
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
    },
}

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
        # No SMS provider chosen yet; codes go to the server log in development.
        "sms": "accounts.otp.ConsoleSender" if DEBUG else "accounts.otp.UnconfiguredSender",
    },
}

# Order pricing in IQD. Example values; set the real ones before launch.
ORDER_PRICING = {
    # Delivery: base fee covers the first BASE_KM, then a fee per started km.
    "DELIVERY_BASE_FEE": 1500,
    "DELIVERY_BASE_KM": 2,
    "DELIVERY_FEE_PER_KM": 250,
    # Fees are rounded up to this step, matching how prices are quoted in Iraq.
    "FEE_ROUNDING": 250,
    "SERVICE_FEE": 500,
    # Wasel Plus members: free delivery from this subtotal, and a lower service fee.
    "PLUS_FREE_DELIVERY_MIN": 15000,
    "PLUS_SERVICE_FEE": 250,
    "MAX_ITEM_QUANTITY": 50,
    "MAX_KG": 50,
    "MAX_TIP": 50000,
}

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

# Push notifications through Firebase Cloud Messaging (Android and, via an
# APNs key uploaded to Firebase, iPhone). Point FCM_CREDENTIALS_FILE at the
# Firebase service account JSON to send real pushes.
PUSH = {
    "FCM_CREDENTIALS_FILE": os.environ.get("FCM_CREDENTIALS_FILE", ""),
    "FCM_PROJECT_ID": os.environ.get("FCM_PROJECT_ID", ""),
    "SENDER": (
        "notifications.push.FcmSender"
        if os.environ.get("FCM_CREDENTIALS_FILE")
        else "notifications.push.ConsoleSender"
        if DEBUG
        else "notifications.push.UnconfiguredSender"
    ),
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
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
