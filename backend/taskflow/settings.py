"""
Django settings for the TaskFlow project.
"""
import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
import dj_database_url
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key-change-me')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        'DJANGO_ALLOWED_HOSTS',
        'localhost,127.0.0.1'
    ).split(',')
    if host.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',

    # Local apps
    'users',
    'projects',
    'tasks',
    'comments',
    'attachments',
    'notifications',
    'audit',
    'dashboard',
    'reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'audit.middleware.CurrentUserMiddleware',
]

ROOT_URLCONF = 'taskflow.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'taskflow.wsgi.application'



DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=DATABASE_URL.startswith(('postgres://', 'postgresql://')),
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }



AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- DRF / JWT -------------------------------------------------------------

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'users.authentication.ActiveMemberJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_THROTTLE_RATES': {
        'registration': '5/hour',
        'auth_email': '5/hour',
        'auth_verification': '20/hour',
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# --- CORS (TypeScript/React dev server) ------------------------------------

CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS', 'http://localhost:5173'
).split(',')
if DEBUG:
    CORS_ALLOWED_ORIGIN_REGEXES = [
        pattern.strip()
        for pattern in os.environ.get(
            'CORS_ALLOWED_ORIGIN_REGEXES',
            r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$',
        ).split(',')
        if pattern.strip()
    ]
CORS_ALLOW_CREDENTIALS = True

# --- email delivery ------------------------------------------------------

MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND')
if EMAIL_BACKEND is None:
    if MAIL_USERNAME and MAIL_PASSWORD:
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    elif DEBUG:
        EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    else:
        raise ImproperlyConfigured(
            'Set MAIL_USERNAME and MAIL_PASSWORD to enable verification and password reset emails.'
        )
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = MAIL_USERNAME
EMAIL_HOST_PASSWORD = MAIL_PASSWORD
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', MAIL_USERNAME or 'TaskFlow <noreply@localhost>')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173')


# Email configuration (Brevo SMTP)

# --- Email configuration (Brevo SMTP) ---

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend" if not DEBUG
    else "django.core.mail.backends.console.EmailBackend",
)

EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp-relay.brevo.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "")
FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    "http://localhost:5173" if DEBUG else "",
)

if not DEBUG and EMAIL_BACKEND.endswith("smtp.EmailBackend"):
    if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD or not DEFAULT_FROM_EMAIL:
        raise ImproperlyConfigured(
            "Production email requires EMAIL_HOST_USER, "
            "EMAIL_HOST_PASSWORD, and DEFAULT_FROM_EMAIL."
        )

if not DEBUG and not FRONTEND_URL:
    raise ImproperlyConfigured(
        "FRONTEND_URL must be configured in production."
    )
