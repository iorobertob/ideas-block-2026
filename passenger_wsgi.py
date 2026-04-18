"""
Passenger WSGI entry point for cPanel shared hosting (Namecheap).

Expected directory layout on the server:

    ~/ideas_block/                  ← cPanel application root
        passenger_wsgi.py           ← this file (place here manually)
        .env                        ← secrets (place here manually, never in git)
        db.sqlite3                  ← database (transfer via scp, never in git)
        git/                        ← the cloned repository
            manage.py
            requirements.txt
            ideas_block/
            templates/
            ...

cPanel's Python Selector (Phusion Passenger) imports `application` from this file.
"""
import os
import sys

# APP_ROOT  = ~/ideas_block/         (the cPanel application root)
# REPO_ROOT = ~/ideas_block/git/     (the cloned repository)
APP_ROOT  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.join(APP_ROOT, "git")

# Put the repo on the path so Django can find the project package
sys.path.insert(0, REPO_ROOT)

# Load .env from the app root (outside the git repo — never committed)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(APP_ROOT, ".env"))
except ImportError:
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ideas_block.settings.cpanel")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
