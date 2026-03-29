"""
Import WordPress content from a MySQL SQL dump file.

Usage:
    python manage.py import_wordpress --sql-path=/path/to/dump.sql [--dry-run]

Maps:
  wp_posts (post)         -> BlogPostPage  (under BlogIndexPage)
  wp_posts (page)         -> Static pages (About, Contact, etc.)
  wp_posts (tribe_events) -> EventPage    (under EventsIndexPage)
  wp_posts (product)      -> ProductPage  (under ProductsIndexPage)
"""

import re
import html
import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from wagtail.models import Page, Site


# ---------------------------------------------------------------------------
# SQL dump parser helpers
# ---------------------------------------------------------------------------

def unescape_sql_string(s: str) -> str:
    """Undo MySQL string escaping."""
    return (
        s.replace("\\'", "'")
         .replace('\\"', '"')
         .replace("\\\\", "\\")
         .replace("\\n", "\n")
         .replace("\\r", "\r")
         .replace("\\t", "\t")
    )


def extract_table_rows(sql_path: str, table: str) -> list[list[str]]:
    """
    Stream the SQL file line by line. Each data row in the VALUES block
    starts with '(' and is on a single line (newlines in content are \\n).
    Much faster than loading 184MB into memory.
    """
    insert_marker = f"INSERT INTO `{table}`"
    rows = []
    collecting = False

    with open(sql_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            # Start or restart collecting on INSERT for this table
            if line.startswith(insert_marker):
                collecting = True
                continue
            if not collecting:
                continue
            # Inside a VALUES block — stop only on a non-row, non-blank line
            # that is an INSERT for a DIFFERENT table
            if line.startswith("INSERT INTO") and not line.startswith(insert_marker):
                collecting = False
                continue
            stripped = line.rstrip("\n").rstrip(",").rstrip(";").rstrip()
            if not stripped or stripped.startswith("--") or stripped.startswith("/*"):
                continue
            if stripped.startswith("(") and stripped.endswith(")"):
                inner = stripped[1:-1]
                rows.append(parse_row(inner))
            elif stripped.startswith("("):
                # Row doesn't end with ) on this line — strip opening ( and append
                inner = stripped[1:]
                rows.append(parse_row(inner))

    return rows


def parse_row(row_str: str) -> list[str]:
    """Parse a single SQL row string into a list of Python values."""
    values = []
    i = 0
    n = len(row_str)
    while i < n:
        # Skip whitespace and commas between values
        while i < n and row_str[i] in (' ', '\t', '\n', '\r'):
            i += 1
        if i >= n:
            break
        if row_str[i] == ',':
            i += 1
            continue
        if row_str[i] == "'":
            # Quoted string
            i += 1
            buf = []
            while i < n:
                if row_str[i] == '\\' and i + 1 < n:
                    buf.append(row_str[i])
                    buf.append(row_str[i + 1])
                    i += 2
                elif row_str[i] == "'":
                    i += 1
                    break
                else:
                    buf.append(row_str[i])
                    i += 1
            values.append(unescape_sql_string(''.join(buf)))
        elif row_str[i:i+4].upper() == 'NULL':
            values.append(None)
            i += 4
        else:
            # Unquoted value (number, etc.)
            j = i
            while j < n and row_str[j] not in (',', ')'):
                j += 1
            values.append(row_str[i:j].strip())
            i = j
    return values


def parse_date(s: str):
    """Parse MySQL datetime string to Python date or None."""
    if not s or s.startswith('0000'):
        return None
    try:
        return datetime.datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def sanitize_slug(slug: str) -> str:
    """Ensure slug contains only Unicode letters, numbers, underscores, hyphens."""
    import unicodedata
    # Normalize and strip problematic chars
    slug = slug.strip().lower()
    # Replace spaces/dots with hyphens
    slug = re.sub(r'[\s\.]+', '-', slug)
    # Remove anything that's not alphanumeric, underscore, or hyphen
    slug = re.sub(r'[^\w\-]', '', slug, flags=re.UNICODE)
    # Collapse multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-_')
    return slug[:80] or 'post'


def is_lithuanian(text: str) -> bool:
    """Heuristic: check for Lithuanian-specific characters."""
    lt_chars = set('ąčęėįšųūžĄČĘĖĮŠŲŪŽ')
    return any(c in lt_chars for c in (text or ''))


def html_to_streamfield_json(html_content: str) -> str:
    """
    Convert WordPress HTML/Gutenberg content to a minimal Wagtail StreamField JSON.
    Wraps the entire content in a single richtext block.
    """
    import json
    if not html_content:
        return "[]"
    # Strip Gutenberg block comments
    cleaned = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL).strip()
    cleaned = html.unescape(cleaned)
    if not cleaned:
        return "[]"
    blocks = [{"type": "paragraph", "value": cleaned, "id": "imported"}]
    return json.dumps(blocks)


# ---------------------------------------------------------------------------
# WordPress post columns (wpr4_posts)
# ID, post_author, post_date, post_date_gmt, post_content, post_title,
# post_excerpt, post_status, comment_status, ping_status, post_password,
# post_name, to_ping, pinged, post_modified, post_modified_gmt,
# post_content_filtered, post_parent, guid, menu_order, post_type,
# post_mime_type, comment_count
# ---------------------------------------------------------------------------
COL_ID = 0
COL_DATE = 2
COL_CONTENT = 4
COL_TITLE = 5
COL_EXCERPT = 6
COL_STATUS = 7
COL_SLUG = 11
COL_POST_TYPE = 20


class Command(BaseCommand):
    help = "Import WordPress SQL dump into Wagtail"

    def add_arguments(self, parser):
        parser.add_argument("--sql-path", required=True, help="Path to the .sql dump file")
        parser.add_argument("--dry-run", action="store_true", help="Parse only, do not write to DB")
        parser.add_argument("--table-prefix", default="wpr4_", help="WordPress table prefix (default: wpr4_)")
        parser.add_argument("--limit", type=int, default=0, help="Limit rows per type (0 = all)")

    def handle(self, *args, **options):
        sql_path = options["sql_path"]
        dry_run = options["dry_run"]
        prefix = options["table_prefix"]
        limit = options["limit"]

        self.stdout.write(f"Reading SQL dump: {sql_path}")
        import os
        if not os.path.exists(sql_path):
            raise CommandError(f"File not found: {sql_path}")

        self.stdout.write("Parsing posts table…")
        table_name = f"{prefix}posts"
        rows = extract_table_rows(sql_path, table_name)
        self.stdout.write(f"  Total rows in {table_name}: {len(rows)}")

        # Filter to published content
        published = [
            r for r in rows
            if len(r) > COL_POST_TYPE
            and r[COL_STATUS] == "publish"
            and r[COL_POST_TYPE] in ("post", "page", "tribe_events", "product")
        ]
        self.stdout.write(f"  Published items: {len(published)}")

        by_type: dict[str, list] = {}
        for r in published:
            pt = r[COL_POST_TYPE]
            by_type.setdefault(pt, []).append(r)

        for pt, items in by_type.items():
            self.stdout.write(f"    {pt}: {len(items)}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run mode — no DB writes."))
            return

        # Get or create root page structure
        from home.models import HomePage
        from blog.models import BlogIndexPage, BlogPostPage, BlogCategory
        from events.models import EventsIndexPage, EventPage
        from projects.models import ProjectsIndexPage
        from products.models import ProductsIndexPage, ProductPage

        root = Page.objects.filter(depth=1).first()
        if not root:
            raise CommandError("No root page found. Run migrations and initial data setup first.")

        home = HomePage.objects.first()
        if not home:
            self.stdout.write(self.style.WARNING("No HomePage found — creating one."))
            home = HomePage(
                title="Ideas Block",
                slug="home",
                hero_tagline="Ideas Block",
                hero_subtitle="Cultural organisation — Vilnius",
            )
            root.add_child(instance=home)

        # Ensure index pages exist
        blog_index = BlogIndexPage.objects.first()
        if not blog_index:
            blog_index = BlogIndexPage(title="Blog", slug="blog")
            home.add_child(instance=blog_index)
            self.stdout.write("  Created BlogIndexPage")

        events_index = EventsIndexPage.objects.first()
        if not events_index:
            events_index = EventsIndexPage(title="Events", slug="events")
            home.add_child(instance=events_index)
            self.stdout.write("  Created EventsIndexPage")

        products_index = ProductsIndexPage.objects.first()
        if not products_index:
            products_index = ProductsIndexPage(title="Workshops & Products", slug="workshops")
            home.add_child(instance=products_index)
            self.stdout.write("  Created ProductsIndexPage")

        # Import blog posts
        posts = by_type.get("post", [])
        if limit:
            posts = posts[:limit]
        imported_posts = 0
        skipped_posts = 0
        for row in posts:
            wp_id_str = row[COL_ID]
            try:
                wp_id = int(wp_id_str)
            except (ValueError, TypeError):
                continue
            if BlogPostPage.objects.filter(wp_post_id=wp_id).exists():
                skipped_posts += 1
                continue
            title = row[COL_TITLE] or "Untitled"
            slug_base = sanitize_slug(row[COL_SLUG] or slugify(title))
            slug = self._unique_slug(slug_base, BlogPostPage)
            excerpt = row[COL_EXCERPT] or ""
            content = row[COL_CONTENT] or ""
            pub_date = parse_date(row[COL_DATE])
            lang = "lt" if is_lithuanian(title + content) else "en"
            body_json = html_to_streamfield_json(content)
            page = BlogPostPage(
                title=title,
                slug=slug,
                date=pub_date,
                intro=excerpt[:500] if excerpt else "",
                wp_post_id=wp_id,
                language=lang,
            )
            page.body = body_json
            blog_index.add_child(instance=page)
            imported_posts += 1

        self.stdout.write(f"  Blog posts: imported {imported_posts}, skipped {skipped_posts}")

        # Import events
        events = by_type.get("tribe_events", [])
        if limit:
            events = events[:limit]
        imported_events = 0
        for row in events:
            try:
                wp_id = int(row[COL_ID])
            except (ValueError, TypeError):
                continue
            if EventPage.objects.filter(wp_post_id=wp_id).exists():
                continue
            title = row[COL_TITLE] or "Untitled Event"
            slug_base = sanitize_slug(row[COL_SLUG] or slugify(title))
            slug = self._unique_slug(slug_base, EventPage)
            excerpt = row[COL_EXCERPT] or ""
            content = row[COL_CONTENT] or ""
            pub_date = parse_date(row[COL_DATE])
            lang = "lt" if is_lithuanian(title + content) else "en"
            body_json = html_to_streamfield_json(content)
            page = EventPage(
                title=title,
                slug=slug,
                start_date=pub_date,
                intro=excerpt[:500] if excerpt else "",
                wp_post_id=wp_id,
                language=lang,
            )
            page.body = body_json
            events_index.add_child(instance=page)
            imported_events += 1

        self.stdout.write(f"  Events: imported {imported_events}")

        # Import products
        products = by_type.get("product", [])
        if limit:
            products = products[:limit]
        imported_products = 0
        for row in products:
            try:
                wp_id = int(row[COL_ID])
            except (ValueError, TypeError):
                continue
            if ProductPage.objects.filter(wp_post_id=wp_id).exists():
                continue
            title = row[COL_TITLE] or "Untitled"
            slug_base = sanitize_slug(row[COL_SLUG] or slugify(title))
            slug = self._unique_slug(slug_base, ProductPage)
            excerpt = row[COL_EXCERPT] or ""
            content = row[COL_CONTENT] or ""
            body_json = html_to_streamfield_json(content)
            page = ProductPage(
                title=title,
                slug=slug,
                intro=excerpt[:500] if excerpt else "",
                wp_post_id=wp_id,
            )
            page.body = body_json
            products_index.add_child(instance=page)
            imported_products += 1

        self.stdout.write(f"  Products: imported {imported_products}")

        self.stdout.write(self.style.SUCCESS(
            f"\nImport complete: {imported_posts} posts, {imported_events} events, {imported_products} products."
        ))

    def _unique_slug(self, base: str, model_class) -> str:
        """Ensure slug is unique within the model."""
        slug = base[:60]
        if not model_class.objects.filter(slug=slug).exists():
            return slug
        n = 1
        while model_class.objects.filter(slug=f"{slug}-{n}").exists():
            n += 1
        return f"{slug}-{n}"
