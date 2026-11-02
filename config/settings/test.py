import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-faqat-testlar-uchun-0123456789")
# docker compose'dagi db servisi hostga 5433-portda ochilgan
os.environ.setdefault("DATABASE_URL", "postgres://shoeflow:shoeflow@localhost:5433/shoeflow")

from .base import *  # noqa: E402

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True
