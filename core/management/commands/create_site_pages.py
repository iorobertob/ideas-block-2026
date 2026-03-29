"""
Create structural pages: About, People (Roberto + Liucija), Contact,
Projects index, Documents — populating content from the WP SQL dump.

Usage:
    python manage.py create_site_pages --sql-path=/path/to/dump.sql
"""

import re
import os
from django.core.management.base import BaseCommand, CommandError


# ── SQL helpers ──────────────────────────────────────────────────────────────

def extract_page_by_slug(sql_path: str, slug: str, prefix: str = "wpr4_") -> dict | None:
    """Return the first published post row matching the given slug."""
    from .import_wordpress import parse_row

    insert_marker = f"INSERT INTO `{prefix}posts`"
    collecting = False
    target = f"'{slug}'"

    with open(sql_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith(insert_marker):
                collecting = True
                continue
            if not collecting:
                continue
            if line.startswith("INSERT INTO") and not line.startswith(insert_marker):
                collecting = False
                continue
            stripped = line.rstrip("\n").rstrip(",").rstrip(";").rstrip()
            if not stripped.startswith("(") or target not in stripped:
                continue
            inner = stripped[1:-1] if stripped.endswith(")") else stripped[1:]
            row = parse_row(inner)
            # slug is col 11, status col 7
            if len(row) > 20 and row[11] == slug and row[7] == "publish":
                return {
                    "title": row[5],
                    "slug": row[11],
                    "content": row[4] or "",
                    "excerpt": row[6] or "",
                }
    return None


def clean_wp_html(html_content: str) -> str:
    """Strip Gutenberg block comments, leaving plain HTML."""
    if not html_content:
        return ""
    cleaned = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
    return cleaned


# ── Command ──────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Create structural site pages from the WordPress SQL dump"

    def add_arguments(self, parser):
        parser.add_argument("--sql-path", required=True, help="Path to WordPress SQL dump")
        parser.add_argument("--table-prefix", default="wpr4_")

    def handle(self, *args, **options):
        sql_path = options["sql_path"]
        prefix = options["table_prefix"]

        if not os.path.exists(sql_path):
            raise CommandError(f"File not found: {sql_path}")

        from home.models import HomePage
        home = HomePage.objects.first()
        if not home:
            raise CommandError("No HomePage found. Run import_wordpress first.")

        self._create_about(home, sql_path, prefix)
        self._create_people(home, sql_path, prefix)
        self._create_contact(home, sql_path, prefix)
        self._create_projects_index(home)
        self._create_documents(home, sql_path, prefix)
        self._create_space(home, sql_path, prefix)

        self.stdout.write(self.style.SUCCESS("\nAll structural pages created/verified."))

    # ── Individual page creators ─────────────────────────────────────────────

    def _create_about(self, home, sql_path, prefix):
        from core.models import RichPage
        from wagtail.models import Page
        if Page.objects.filter(slug="about").exists():
            self.stdout.write("  About: already exists")
            return
        data = extract_page_by_slug(sql_path, "about", prefix)
        body = clean_wp_html(data["content"]) if data else "<p>Ideas Block is a non-profit cultural organisation based in Vilnius, Lithuania.</p>"
        page = RichPage(
            title="About",
            slug="about",
            intro="Ideas Block — cultural organisation, Vilnius.",
            body=body,
        )
        home.add_child(instance=page)
        self.stdout.write("  About: created")

    def _create_people(self, home, sql_path, prefix):
        from people.models import PeoplePage, PersonPage
        people_index = PeoplePage.objects.first()
        if not people_index:
            people_index = PeoplePage(
                title="People",
                slug="people",
                intro="The team behind Ideas Block.",
            )
            home.add_child(instance=people_index)
            self.stdout.write("  People index: created")
        else:
            self.stdout.write("  People index: already exists")

        bios = [
            ("roberto-becerra", "Roberto Becerra", "Co-founder & Director"),
            ("liucija-dervinyte", "Liucija Dervinytė", "Co-founder & Curator"),
        ]
        for slug, name, role in bios:
            if PersonPage.objects.filter(slug=slug).exists():
                self.stdout.write(f"  {name}: already exists")
                continue
            data = extract_page_by_slug(sql_path, slug, prefix)
            bio_html = clean_wp_html(data["content"]) if data else ""
            person = PersonPage(title=name, slug=slug, role=role, bio=bio_html)
            people_index.add_child(instance=person)
            self.stdout.write(f"  {name}: created")

    def _create_contact(self, home, sql_path, prefix):
        from core.models import ContactPage
        if ContactPage.objects.exists():
            self.stdout.write("  Contact: already exists")
            return
        page = ContactPage(
            title="Contact",
            slug="contact",
            intro="<p>Get in touch with Ideas Block.</p>",
            email="contact@ideas-block.com",
            address="Vilnius, Lithuania",
        )
        home.add_child(instance=page)
        self.stdout.write("  Contact: created")

    def _create_projects_index(self, home):
        from projects.models import ProjectsIndexPage
        if ProjectsIndexPage.objects.exists():
            self.stdout.write("  Projects index: already exists")
            return
        page = ProjectsIndexPage(
            title="Projects",
            slug="projects",
            intro="Exhibitions, residencies, and cultural projects produced by Ideas Block since 2014.",
        )
        home.add_child(instance=page)
        self.stdout.write("  Projects index: created")

    def _create_documents(self, home, sql_path, prefix):
        from core.models import RichPage
        from wagtail.models import Page
        if Page.objects.filter(slug="documents").exists():
            self.stdout.write("  Documents: already exists")
            return

        # Pull both annual reports
        bodies = []
        for slug in ("2018-metu-vsi-ideju-blokas-lt-veiklos-ataskaita",
                     "2019-metu-vsi-ideju-blokas-lt-veiklos-ataskaita"):
            data = extract_page_by_slug(sql_path, slug, prefix)
            if data:
                year = "2018" if "2018" in slug else "2019"
                bodies.append(f"<h2>Annual report {year}</h2>" + clean_wp_html(data["content"]))

        body = "\n\n".join(bodies) or "<p>Annual reports and organisational documents.</p>"
        page = RichPage(
            title="Documents",
            slug="documents",
            intro="Annual reports and organisational documents.",
            body=body,
        )
        home.add_child(instance=page)
        self.stdout.write("  Documents: created")

    def _create_space(self, home, sql_path, prefix):
        from core.models import SpacePage
        from wagtail.models import Page
        if Page.objects.filter(slug="space").exists():
            self.stdout.write("  Space: already exists")
            return

        # Try the floor-plan page slug first, then the kompresorine slug
        data = None
        for slug in ("floor-plan-of-kompresorine", "kompresorine", "space"):
            data = extract_page_by_slug(sql_path, slug, prefix)
            if data:
                break

        body = clean_wp_html(data["content"]) if data else (
            "<p>Kompresorinė was Ideas Block's venue in Vilnius — "
            "a flexible cultural space hosting exhibitions, workshops, performances, and residencies.</p>"
        )
        page = SpacePage(
            title="Space",
            slug="space",
            intro="Kompresorinė — our venue in Vilnius.",
            body=body,
            address="Kompresorinė, Vilnius, Lithuania",
            booking_email="contact@ideas-block.com",
        )
        home.add_child(instance=page)
        self.stdout.write("  Space: created")
