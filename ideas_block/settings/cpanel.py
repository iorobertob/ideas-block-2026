"""
Settings for Namecheap shared hosting (cPanel + Passenger).

Directory layout assumed:

    ~/ideas_block/          ← APP_ROOT  (cPanel application root)
        passenger_wsgi.py
        .env
        db.sqlite3
        git/                ← REPO_ROOT / BASE_DIR  (this git repository)
            manage.py
            static/         ← populated by collectstatic
            media/          ← user-uploaded files (transferred via rsync)
            ideas_block/
                settings/
                    cpanel.py   ← this file

Key differences from production.py:
- SQLite database stored in APP_ROOT (outside the git repo)
- .env loaded from APP_ROOT (outside the git repo)
- STATIC_ROOT and MEDIA_ROOT stay inside the repo (git/static/, git/media/)
- WhiteNoise serves static files — Passenger routes all requests through Django
- SECURE_SSL_REDIRECT disabled — SSL termination is handled by Apache/Namecheap
"""
import os
from .base import *

# BASE_DIR  = ~/ideas_block/git/   (set in base.py)
# APP_ROOT  = ~/ideas_block/       (one level up — outside the git repo)
APP_ROOT = os.path.dirname(BASE_DIR)

# Load .env from APP_ROOT (never inside the git repo)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(APP_ROOT, ".env"))
except ImportError:
    pass

DEBUG = False

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", "ideas-block.com,www.ideas-block.com"
).split(",")

# ── Database — SQLite stored in APP_ROOT (outside public_html, outside git) ──
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(APP_ROOT, "db.sqlite3"),
    }
}

# ── Static & Media — inside git/ (BASE_DIR), served by WhiteNoise ────────────
# base.py already sets STATIC_ROOT = BASE_DIR/static and MEDIA_ROOT = BASE_DIR/media
# so no override needed here. WhiteNoise (already in MIDDLEWARE) serves static files
# since Passenger routes all requests through Django — Apache never touches git/.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND    = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST       = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT       = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS    = True
EMAIL_HOST_USER  = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL  = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@ideas-block.com")

# ── Security ──────────────────────────────────────────────────────────────────
# SSL is terminated by Apache/Namecheap — Django must NOT redirect or it loops.
SECURE_SSL_REDIRECT          = False
SESSION_COOKIE_SECURE        = True
CSRF_COOKIE_SECURE           = True
SECURE_CONTENT_TYPE_NOSNIFF  = True
SECURE_HSTS_SECONDS          = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ── Wagtail ───────────────────────────────────────────────────────────────────
WAGTAILADMIN_BASE_URL = os.environ.get("SITE_URL", "https://ideas-block.com")

try:
    from .local import *
except ImportError:
    pass
