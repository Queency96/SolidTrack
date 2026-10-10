from pathlib import Path
from decouple import config
from datetime import timedelta
import os



# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = 'django-insecure-rq@rcwpr4&dyi2t#0w$h_z*+2gthay(bl^7536u61f^z!+s5z2'
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = True
DEBUG = config("DEBUG", cast=bool)


# Application definition

INSTALLED_APPS = [
    "daphne",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "cloudinary_storage",
    "cloudinary",


    # Third Party Apps
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
    "rest_framework_simplejwt.token_blacklist",

    # Local Apps
    "accounts.apps.AccountsConfig",
    "customers",
    "vendors",
    "riders",
    "deliveries",
    "wallet",
    "payments",
    "tracking",
    "chat",
    "notifications",
    "common",
    "communications",
    "order",
    "cart",
    "checkout",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
    }
}


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}



SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}


CORS_ALLOW_ALL_ORIGINS = True


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


# Cloudinary credentials (pushed into process env so pycloudinary / django-cloudinary-storage can read them)
CLOUDINARY_URL = config("CLOUDINARY_URL", default="")
os.environ["CLOUDINARY_URL"] = CLOUDINARY_URL


SPECTACULAR_SETTINGS = {
    "TITLE": "SolidTrack API",
    "DESCRIPTION": "Logistics Delivery Backend API",
    "VERSION": "1.0.0",
}

AUTH_USER_MODEL = "accounts.User"


EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT", cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool)

DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")

FRONTEND_URL = config("FRONTEND_URL")

MAP_PROVIDER = "OPENROUTE"

OPENROUTESERVICE_API_KEY = config("OPENROUTESERVICE_API_KEY")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=lambda v: [s.strip() for s in v.split(",")])

WHATSAPP_PHONE_NUMBER_ID = config("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = config("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_BUSINESS_ACCOUNT_ID = config("WHATSAPP_BUSINESS_ACCOUNT_ID")
WHATSAPP_WEBHOOK_VERIFY_TOKEN = config("WHATSAPP_WEBHOOK_VERIFY_TOKEN")





GEOIP_PATH = os.path.join(BASE_DIR, "geoip")

# Trust exactly one proxy hop (your PaaS router).
IPWARE_META_PRECEDENCE_ORDER = (
    "HTTP_X_FORWARDED_FOR",
    "REMOTE_ADDR",
)


# Paystack webhook IP addresses (for signature verification)
PAYSTACK_WEBHOOK_IPS = [
    "52.31.139.75",
    "52.49.173.169",
    "52.214.14.220",
]


# Paystack credentials
PAYSTACK_SECRET_KEY = config("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = config("PAYSTACK_PUBLIC_KEY")
PAYSTACK_CALLBACK_URL = config(
    "PAYSTACK_CALLBACK_URL",
    default="https://yourapp.com/payments/callback/",
)


# ==================================================
# Celery
# ==================================================
#
# Broker and result backend are required in production.
# Fails loudly at startup if either is missing.
#
# Local dev: set CELERY_BROKER_URL=redis://localhost:6379/0
# in .env and start Redis locally.
# ==================================================

CELERY_BROKER_URL = config("CELERY_BROKER_URL")

CELERY_RESULT_BACKEND = config(
    "CELERY_RESULT_BACKEND",
    default="",
)

# Serialization
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Time zone — matches Django's TIME_ZONE
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Task behaviour
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300          # hard limit, seconds
CELERY_TASK_SOFT_TIME_LIMIT = 240     # soft limit, seconds
CELERY_TASK_ACKS_LATE = True          # ack after execution, not before
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Worker behaviour
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 200   # recycle workers periodically

# Beat schedule
CELERY_BEAT_SCHEDULE = {

    # ==================================================
    # Offer lifecycle
    # ==================================================
    #
    # Expire PENDING offers whose expires_at passed, and
    # trigger redispatch. 60-second cadence keeps the
    # loop tight without hammering the broker.
    # ------------------------------------------------
    "deliveries.expire_stale_offers": {
        "task": "deliveries.expire_stale_offers",
        "schedule": 60.0,
    },

    # ==================================================
    # Scheduled dispatch
    # ==================================================
    #
    # Fire mark_ready_for_dispatch for SCHEDULED deliveries
    # within the 15-minute pre-pickup window.
    # ------------------------------------------------
    "order.dispatch_scheduled_deliveries": {
        "task": "order.dispatch_scheduled_deliveries",
        "schedule": 60.0,
    },

    # ==================================================
    # OTP safety net
    # ==================================================
    #
    # Recover OUT_FOR_DELIVERY fulfillments that never got
    # a delivery OTP (failed cascade).
    # ------------------------------------------------
    "order.sweep_missing_delivery_otps": {
        "task": "order.sweep_missing_delivery_otps",
        "schedule": 300.0,  # every 5 minutes
    },

    # ==================================================
    # Refund retry
    # ==================================================
    #
    # Retry FAILED refunds from the last 7 days.
    # ------------------------------------------------
    "order.retry_failed_refunds": {
        "task": "order.retry_failed_refunds",
        "schedule": 900.0,  # every 15 minutes
    },

    # ==================================================
    # Rider earnings settlement
    # ==================================================
    #
    # Credit rider wallets for completed assignments.
    # ------------------------------------------------
    "wallet.settle_rider_earnings": {
        "task": "wallet.settle_rider_earnings",
        "schedule": 900.0,  # every 15 minutes
    },

    # ==================================================
    # Housekeeping
    # ==================================================
    #
    # Delete stale IPStateMapping rows (>90 days idle).
    # ------------------------------------------------
    "common.cleanup_ip_state_mappings": {
        "task": "common.cleanup_ip_state_mappings",
        "schedule": 86400.0,  # daily
    },
}