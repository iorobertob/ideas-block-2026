"""
Settings for Namecheap shared hosting (cPanel + Passenger).

Directory layout assumed:

    ~/ideas_block/          ← APP_ROOT  (cPanel application root)
        passenger_wsgi.py
        .env
        db.sqlite3
        errors.log          ← Django error log (auto-created)
        git/                ← REPO_ROOT / BASE_DIR  (this git repository)
            manage.py
            static/         ← populated by collectstatic
            media/          ← user-uploaded files (transferred via rsync)
            ideas_block/
                settings/
                    cpanel.py   ← this file
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

# ── Core ──────────────────────────────────────────────────────────────────────
# Set DEBUG=True in .env to see full tracebacks in the browser temporarily.
DEBUG = os.environ.get("DEBUG", "False") == "True"

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", "ideas-block.com,www.ideas-block.com"
).split(",")

# ── Database — SQLite stored in APP_ROOT (outside git) ───────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(APP_ROOT, "db.sqlite3"),
    }
}

# ── Static & Media ────────────────────────────────────────────────────────────
# base.py sets STATIC_ROOT = BASE_DIR/static and MEDIA_ROOT = BASE_DIR/media.
# WhiteNoise (already in MIDDLEWARE in base.py) serves static files via Passenger.
# Run: python manage.py collectstatic --settings=ideas_block.settings.cpanel

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND    = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST       = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT       = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS    = True
EMAIL_HOST_USER  = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL  = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@ideas-block.com")

# ── Security ──────────────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT          = False  # SSL terminated by Apache
SESSION_COOKIE_SECURE        = True
CSRF_COOKIE_SECURE           = True
SECURE_CONTENT_TYPE_NOSNIFF  = True
SECURE_HSTS_SECONDS          = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ── Wagtail ───────────────────────────────────────────────────────────────────
WAGTAILADMIN_BASE_URL = os.environ.get("SITE_URL", "https://ideas-block.com")

# ── Logging — always write errors to APP_ROOT/errors.log ─────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": os.path.join(APP_ROOT, "errors.log"),
            "level": "ERROR",
        },
    },
    "root": {"handlers": ["file"], "level": "ERROR"},
}

try:
    from .local import *
except ImportError:
    pass
