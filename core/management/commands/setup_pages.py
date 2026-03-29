"""
Management command to ensure all required Wagtail pages exist in the page tree.
Safe to run multiple times — creates pages only if they don't already exist.

Usage:
    python manage.py setup_pages
"""
from django.core.management.base import BaseCommand
from wagtail.models import Page


PAGE_SPECS = [
    # (slug, title, app.ModelClass, kwargs)
    ("open-calls", "Open Calls", "opencalls.OpenCallsIndexPage", {
        "intro": "Current and past open calls from Ideas Block.",
    }),
    ("press", "Press", "press.PressPage", {
        "press_contact_email": "press@ideas-block.com",
    }),
    ("publications", "Publications", "publications.PublicationsIndexPage", {
        "intro": "Books, catalogues, and publications by Ideas Block.",
    }),
    ("people", "People", "people.PeoplePage", {
        "intro": "The team behind Ideas Block.",
    }),
]


def _import_model(dotted):
    module_path, class_name = dotted.rsplit(".", 1)
    import importlib
    mod = importlib.import_module(module_path + ".models")
    return getattr(mod, class_name)


class Command(BaseCommand):
    help = "Create required Wagtail pages if they don't already exist."

    def handle(self, *args, **options):
        try:
            home = Page.objects.get(slug="home")
        except Page.DoesNotExist:
            self.stderr.write("No Home page found — run initial migrations and create the site first.")
            return

        for slug, title, model_path, extra_kwargs in PAGE_SPECS:
            if Page.objects.filter(slug=slug).exists():
                self.stdout.write(f"  exists  {slug}")
                continue
            Model = _import_model(model_path)
            page = Model(title=title, slug=slug, **extra_kwargs)
            home.add_child(instance=page)
            revision = page.save_revision()
            revision.publish()
            self.stdout.write(self.style.SUCCESS(f"  created {slug} ({model_path})"))

        self.stdout.write(self.style.SUCCESS("setup_pages complete."))
