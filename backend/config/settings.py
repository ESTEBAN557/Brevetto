"""
Configuración de Django para Brevetto (Coltebienes S.A.).

Todas las variables sensibles se leen del entorno (.env) mediante django-environ.
Stack obligatorio: Django 5 + DRF + Celery + PostgreSQL 16 + Redis 7 + S3/MinIO.
"""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000"]),
    POSTGRES_PORT=(int, 5432),
    PRESIGNED_URL_EXPIRATION_SECONDS=(int, 900),
    AI_CONFIDENCE_THRESHOLD=(float, 0.85),
)
# Lee el .env de la raíz del repositorio si existe (ejecución local fuera de Docker).
# Las variables ya presentes en el entorno del proceso tienen prioridad.
environ.Env.read_env(BASE_DIR.parent / ".env")

# --- Seguridad --------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# --- Aplicaciones -----------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "corsheaders",
    "storages",
    # Dominio Brevetto
    "apps.core.apps.CoreConfig",
    "apps.documents.apps.DocumentsConfig",
    "apps.portal.apps.PortalConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Base de datos: PostgreSQL 16 (sin fallback a SQLite) --------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="brevetto"),
        "USER": env("POSTGRES_USER", default="brevetto"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="brevetto"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT"),
        "CONN_MAX_AGE": 60,
        "ATOMIC_REQUESTS": False,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internacionalización ---------------------------------------------------
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"  # US-006: hora local de radicación; la BD almacena UTC.
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos y almacenamiento de objetos -------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="minioadmin")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="minioadmin")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="brevetto-docs")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="http://localhost:9000")
# Host que ve el navegador para URLs prefirmadas (dentro de Docker el interno es minio:9000).
AWS_S3_PUBLIC_ENDPOINT_URL = env("AWS_S3_PUBLIC_ENDPOINT_URL", default="")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = True
AWS_QUERYSTRING_EXPIRE = env("PRESIGNED_URL_EXPIRATION_SECONDS")  # 15 min (NFR seguridad)
AWS_S3_ADDRESSING_STYLE = "path"  # requerido por MinIO
AWS_S3_SIGNATURE_VERSION = "s3v4"

STORAGES = {
    "default": {"BACKEND": "storages.backends.s3.S3Storage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# --- Django REST Framework + JWT --------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_THROTTLE_RATES": {
        "portal_verify": env("PORTAL_VERIFY_THROTTLE", default="30/hour"),
        "portal_submit": env("PORTAL_SUBMIT_THROTTLE", default="60/hour"),
    },
}

# --- Portal público de inquilinos -------------------------------------------
PORTAL_SESSION_TTL_SECONDS = env.int("PORTAL_SESSION_TTL_SECONDS", default=1800)  # 30 minutos

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
}

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# --- Celery (broker y backend de resultados en Redis) -----------------------
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TRACK_STARTED = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
# Documentos sin avance en RECIBIDO/PROCESANDO tras N minutos se re-encolan (Celery beat).
PROCESSING_STALE_AFTER_MINUTES = env.int("PROCESSING_STALE_AFTER_MINUTES", default=15)
CELERY_BEAT_SCHEDULE = {
    "requeue-stale-documents": {
        "task": "documents.requeue_stale_documents",
        "schedule": env.int("STALE_DOCUMENTS_CHECK_SECONDS", default=300),
    },
}

# --- Reglas de negocio Brevetto ---------------------------------------------
FILING_NUMBER_PREFIX = "RAD"  # RAD-YYYYMMDD-XXXXXX
FILING_NUMBER_SEQUENCE_DIGITS = 6
AI_CONFIDENCE_THRESHOLD = env("AI_CONFIDENCE_THRESHOLD")  # HITL: < 0.85 => revisión manual
UPLOAD_MAX_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
UPLOAD_ALLOWED_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg")
UPLOAD_ALLOWED_MIME_TYPES = ("application/pdf", "image/png", "image/jpeg")

# --- Google Gemini ----------------------------------------------------------
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
# gemini-1.5-flash y la familia 2.x fueron retirados en 2026; alternativa rápida: gemini-3-flash-preview.
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-3.5-flash")
# Respaldo inmediato cuando el principal responde 503/429 por saturación (vacío = desactivado).
GEMINI_FALLBACK_MODEL = env("GEMINI_FALLBACK_MODEL", default="gemini-3-flash-preview")

# --- Logging ----------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}
