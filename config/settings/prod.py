from .base import *

DEBUG = False

# Konteyner ichidagi healthcheck localhost orqali murojaat qiladi
ALLOWED_HOSTS = [*ALLOWED_HOSTS, "localhost"]

# Domen bo'lmasa (faqat IP orqali) HTTPS yo'q — xavfsiz cookie va redirectlar o'chiriladi
HTTPS = env.bool("DJANGO_HTTPS", default=True)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = HTTPS
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SESSION_COOKIE_SECURE = HTTPS
CSRF_COOKIE_SECURE = HTTPS
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30 if HTTPS else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = HTTPS
SECURE_CONTENT_TYPE_NOSNIFF = True

# Prod'da browsable API kerak emas
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = ["rest_framework.renderers.JSONRenderer"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
