"""
DBBSA Django Settings
Monolithic architecture with modular app structure

Key Features:
- Multi-domain routing (dbbsa.com, admin.dbbsa.com, sys.neuralvillage.com)
- Role-based access control middleware
- JWT token management for CBT sessions
- Hardware sync background tasks
"""

import os
from pathlib import Path
from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('DJANGO_SECRET_KEY', default='dev-secret-key-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = [
    host.strip() for host in config(
        'ALLOWED_HOSTS',
        default='localhost,127.0.0.1,lvh.me,.lvh.me,*.onrender.com,dbbsa.com,portal.neuralvillage.com,admin.dbbsa.com,sys.neuralvillage.com'
    ).split(',')
    if host.strip()
]

# ============================================
# INSTALLED APPS
# ============================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    # Celery is configured separately; not added to INSTALLED_APPS
    
    # DBBSA Apps
    'neural_village.core.apps.CoreConfig',
    'neural_village.auth.apps.AuthConfig',
    'neural_village.student.apps.StudentConfig',
    'neural_village.instructor.apps.InstructorConfig',
    'neural_village.parent.apps.ParentConfig',
    'neural_village.school_admin.apps.SchoolAdminConfig',
    'neural_village.super_admin.apps.SuperAdminConfig',
    'neural_village.cbt.apps.CbtConfig',
    'neural_village.hardware.apps.HardwareConfig',
    'neural_village.api.apps.ApiConfig',
]

# ============================================
# MIDDLEWARE
# ============================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # DBBSA Custom Middleware
    'neural_village.middleware.DomainRoutingMiddleware',
    'neural_village.middleware.RoleBasedAccessMiddleware',
    'neural_village.middleware.SilentTokenRefreshMiddleware',
]

ROOT_URLCONF = 'neural_village.urls'

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/auth/login/'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'neural_village.wsgi.application'

# ============================================
# DATABASE
# ============================================
DATABASE_URL = config('DATABASE_URL', default=None)
DB_HOST = config('DB_HOST', default=None)
DB_NAME = config('DB_NAME', default=None)
DB_USER = config('DB_USER', default=None)
DB_PASSWORD = config('DB_PASSWORD', default=None)
DB_PORT = config('DB_PORT', default=None)

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    if not DEBUG and not DB_HOST:
        raise ImproperlyConfigured(
            'DATABASE_URL or DB_HOST must be configured for production. '
            'On Render, link the Postgres database service and ensure DATABASE_URL is available.'
        )

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': DB_NAME or 'neural_village',
            'USER': DB_USER or 'postgres',
            'PASSWORD': DB_PASSWORD or 'postgres',
            'HOST': DB_HOST or 'localhost',
            'PORT': DB_PORT or '5432',
        }
    }

# Development convenience: fallback to SQLite when DEBUG is True.
# This prevents requiring psycopg2/PostgreSQL for local development.
if DEBUG and not DATABASE_URL and not DB_HOST:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ============================================
# AUTHENTICATION
# ============================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================
# REST FRAMEWORK & JWT
# ============================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
}

# ============================================
# CORS (for frontend-backend communication)
# ============================================
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:8000',
    'https://dbbsa.com',
    'https://portal.neuralvillage.com',
    'https://admin.dbbsa.com',
    'https://sys.neuralvillage.com',
]

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    'http://lvh.me:8000',
    'http://portal.lvh.me:8000',
    'https://portal.neuralvillage.com',
]

# ============================================
# INTERNATIONALIZATION
# ============================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# ============================================
# STATIC FILES
# ============================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# Use standard WhiteNoise storage (Render-compatible)
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.WhiteNoiseStaticFilesStorage'
else:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================
# LOGGING
# ============================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# On development, also log to file if logs dir exists
if DEBUG:
    log_file = BASE_DIR / 'logs' / 'neural_village.log'
    if log_file.parent.exists():
        LOGGING['handlers']['file'] = {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': log_file,
            'formatter': 'verbose',
        }
        LOGGING['root']['handlers'].append('file')

# ============================================
# CELERY (Background Tasks - Hardware Sync)
# ============================================
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# ============================================
# SECURITY SETTINGS (Production)
# ============================================
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_SECURITY_POLICY = {
        "default-src": ("'self'",),
        "script-src": ("'self'", "'unsafe-inline'", "cdn.tailwindcss.com", "unpkg.com"),
        "style-src": ("'self'", "'unsafe-inline'", "fonts.googleapis.com", "cdn.tailwindcss.com"),
        "font-src": ("'self'", "fonts.gstatic.com"),
        "img-src": ("'self'", "data:", "https:"),
    }

# Development: trusted CSRF origins for local subdomains (lvh.me)
CSRF_TRUSTED_ORIGINS = [
    'http://lvh.me:8000',
    'http://portal.lvh.me:8000',
]

# ============================================
# PAYMENT GATEWAY CONFIGURATION
# ============================================
PAYMENT_GATEWAY = config('PAYMENT_GATEWAY', default='paystack').upper()
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='')
PAYSTACK_API_BASE_URL = config('PAYSTACK_API_BASE_URL', default='https://api.paystack.co')
REMITA_SECRET_KEY = config('REMITA_SECRET_KEY', default='')
BASE_PUBLIC_URL = config('BASE_PUBLIC_URL', default='http://localhost:8000')

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    if RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    wildcard_render = f'.{RENDER_EXTERNAL_HOSTNAME}'
    if wildcard_render not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(wildcard_render)
    if BASE_PUBLIC_URL == 'http://localhost:8000':
        BASE_PUBLIC_URL = f'https://{RENDER_EXTERNAL_HOSTNAME}'
