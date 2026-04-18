"""
Migrate past open calls from blog posts into PastCallsIndexPage > OpenCallPage.
Run once: python manage.py migrate_past_open_calls
"""
import html
import re
from datetime import date

from django.core.management.base import BaseCommand
from wagtail.models import Page

from blog.models import BlogPostPage
from opencalls.models import OpenCallPage, OpenCallsIndexPage, PastCallsIndexPage


CALLS = [
    # (blog_pk, clean_title, call_type, deadline)
    (43,  "Open Call for Designers",                         "other",      date(2017, 2, 28)),
    (44,  "Open Call for Artists",                           "other",      date(2017, 2, 28)),
    (45,  "Open Call for Creative Projects",                 "other",      date(2017, 3, 15)),
    (64,  "Open Call for Sustainable Ideas",                 "research",   date(2018, 6, 1)),
    (80,  "Open Call: Summer Artist Residency",              "residency",  date(2017, 6, 1)),
    (159, "Open Call: Mind Sharpener Talks",                 "workshop",   date(2019, 2, 1)),
    (161, "Open Call: Pop-up Artist Studio & Exhibition",    "exhibition", date(2019, 3, 1)),
    (186, "Open Call: Art Fest @ Trakų Vokės Dvaro Sodyba", "other",      date(2019, 6, 30)),
    (194, "Open Call: Creative Expressions — Covid-19",      "other",      date(2020, 5, 15)),
    (205, 'Open Call: "Made by X" Exhibition',              "exhibition", date(2020, 2, 1)),
    (243, "Open Call: Outdoor Space",                        "other",      date(2020, 8, 31)),
    (266, "Open Call: Solo or Group Exhibitions at Kompresorinė (2023–2024)", "exhibition", date(2023, 2, 20)),
    (269, "Open Call: City Sonic Vilnius Sound Camp",        "other",      date(2023, 2, 15)),
]


def _strip_tags(text):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", text)).strip()


def _get_rich_text_body(blog_page):
    """Return HTML string of all paragraph blocks joined."""
    parts = []
    for block in blog_page.body:
        if hasattr(block.value, "source"):
            src = block.value.source
            # Skip blocks that are only images from dead WP CDN
            if src.strip().startswith("<img") and "wp-content" in src:
                continue
            parts.append(src)
    return "\n".join(parts)


class Command(BaseCommand):
    help = "Migrate past open calls from blog posts to PastCallsIndexPage"

    def handle(self, *args, **options):
        index = OpenCallsIndexPage.objects.first()
        if not index:
            self.stderr.write("No OpenCallsIndexPage found. Create one in Wagtail admin first.")
            return

        # Get or create PastCallsIndexPage
        past_index = PastCallsIndexPage.objects.child_of(index).first()
        if not past_index:
            past_index = PastCallsIndexPage(
                title="Past Calls",
                slug="past-calls",
                intro="An archive of all our past open calls and programmes.",
            )
            index.add_child(instance=past_index)
            self.stdout.write(self.style.SUCCESS("Created PastCallsIndexPage"))
        else:
            self.stdout.write(f"Using existing PastCallsIndexPage (pk={past_index.pk})")

        created = 0
        skipped = 0

        for blog_pk, clean_title, call_type, deadline in CALLS:
            if OpenCallPage.objects.child_of(past_index).filter(title=clean_title).exists():
                self.stdout.write(f"  SKIP (exists): {clean_title}")
                skipped += 1
                continue

            try:
                blog = BlogPostPage.objects.get(pk=blog_pk)
            except BlogPostPage.DoesNotExist:
                self.stderr.write(f"  MISSING blog pk={blog_pk}")
                continue

            rich_body = _get_rich_text_body(blog)
            plain = _strip_tags(rich_body)
            intro = plain[:480] if plain else ""

            body_json = []
            if rich_body.strip():
                body_json = [{"type": "paragraph", "value": rich_body}]

            call = OpenCallPage(
                title=clean_title,
                slug=blog.slug,
                call_type=call_type,
                deadline=deadline,
                intro=intro,
                body=body_json,
            )
            past_index.add_child(instance=call)
            call.save_revision().publish()
            self.stdout.write(self.style.SUCCESS(f"  CREATED: {clean_title} (deadline {deadline})"))
            created += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone. Created: {created}, Skipped: {skipped}"))
