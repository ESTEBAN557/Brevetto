"""
Configuración de Django para Brevetto (Coltebienes S.A.).

Todas las variables sensibles se leen del entorno (.env) mediante django-environ.
Stack obligatorio: Django 5 + DRF + Celery + PostgreSQL 16 + Redis 7 + S3/MinIO.
"""

from datetime import timedelta
from pathlib import Path

import environ
from corsheaders.defaults import default_headers

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
# Orígenes HTTPS confiables para el admin de Django detrás del proxy (ej. https://brevetto.example.com).
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
# Ruta del admin de Django. En producción el frontend Next.js ya usa /admin, por eso se publica
# en otra ruta (docker-compose.prod.yml usa "django-admin/").
DJANGO_ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

# Detrás de un proxy TLS (Caddy en docker-compose.prod.yml): confiar en X-Forwarded-Proto.
if env.bool("DJANGO_BEHIND_TLS_PROXY", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

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
    "apps.customer.apps.CustomerConfig",
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

if not DEBUG:
    # Sirve los estáticos del admin de Django en producción (gunicorn no sirve archivos;
    # en desarrollo los sirve runserver). Requiere `collectstatic` en la imagen.
    MIDDLEWARE.insert(
        MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
        "whitenoise.middleware.WhiteNoiseMiddleware",
    )

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
        "client_auth": env("CLIENT_AUTH_THROTTLE", default="40/hour"),
    },
}

# --- Portal público de inquilinos -------------------------------------------
PORTAL_SESSION_TTL_SECONDS = env.int("PORTAL_SESSION_TTL_SECONDS", default=1800)  # 30 minutos

# --- Mi Portal (clientes) -----------------------------------------------------
CLIENT_SESSION_TTL_SECONDS = env.int("CLIENT_SESSION_TTL_SECONDS", default=8 * 3600)
# Devuelve el OTP en la respuesta de la API. Solo para desarrollo: no hay proveedor SMS integrado.
CLIENT_OTP_DEV_ECHO = env.bool("CLIENT_OTP_DEV_ECHO", default=DEBUG)
CLIENT_PORTAL_EXECUTIVE_NAME = env("CLIENT_PORTAL_EXECUTIVE_NAME", default="Equipo de Servicio al Cliente")
CLIENT_PORTAL_EXECUTIVE_EMAIL = env("CLIENT_PORTAL_EXECUTIVE_EMAIL", default="")
CLIENT_PORTAL_EXECUTIVE_WHATSAPP = env("CLIENT_PORTAL_EXECUTIVE_WHATSAPP", default="")
# URL pública del frontend, usada en los correos que se envían al cliente.
PUBLIC_FRONTEND_URL = env("PUBLIC_FRONTEND_URL", default="http://localhost:3000").rstrip("/")

# --- Correo (códigos de acceso y avisos de requerimientos) --------------------
# Con EMAIL_HOST definido se usa SMTP real (ej. Gmail con contraseña de aplicación, SendGrid, Mailgun).
# Sin EMAIL_HOST los correos se imprimen en el log del backend (útil en desarrollo).
EMAIL_HOST = env("EMAIL_HOST", default="")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = env.int("EMAIL_PORT", default=587)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
    EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
    EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Brevetto · Coltebienes <no-reply@brevetto.local>")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
}

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-portal-token",
]
CORS_EXPOSE_HEADERS = [
    "content-disposition",
]

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
# Alertas de vencimiento documental (Coltebienes #6): ventana de aviso y frecuencia de revisión.
EXPIRATION_ALERT_DAYS = env.int("EXPIRATION_ALERT_DAYS", default=30)
CELERY_BEAT_SCHEDULE = {
    "requeue-stale-documents": {
        "task": "documents.requeue_stale_documents",
        "schedule": env.int("STALE_DOCUMENTS_CHECK_SECONDS", default=300),
    },
    "check-expiring-documents": {
        "task": "documents.check_expiring_documents",
        "schedule": env.int("EXPIRATION_CHECK_SECONDS", default=6 * 60 * 60),
    },
}

# --- Reglas de negocio Brevetto ---------------------------------------------
FILING_NUMBER_PREFIX = "RAD"  # RAD-YYYYMMDD-XXXXXX
FILING_NUMBER_SEQUENCE_DIGITS = 6
AI_CONFIDENCE_THRESHOLD = env("AI_CONFIDENCE_THRESHOLD")  # HITL: < 0.85 => revisión manual
UPLOAD_MAX_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MANUAL_MINUTES_PER_DOCUMENT = env.int("MANUAL_MINUTES_PER_DOCUMENT", default=8)  # supuesto KPI de ahorro
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
