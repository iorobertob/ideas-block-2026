#!/usr/bin/env python
import os
import sys


def main():
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent
    # cPanel servers place passenger_wsgi.py in APP_ROOT (parent of the git
    # clone). All other environments keep it inside the repo.
    if (repo_root.parent / "passenger_wsgi.py").exists():
        default_settings = "ideas_block.settings.cpanel"
    else:
        default_settings = "ideas_block.settings.dev"

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", default_settings)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
