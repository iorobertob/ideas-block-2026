"""
Import WordPress media (images) into Wagtail and link featured images to pages.

Steps:
  1. Parse wpr4_posts (post_type='attachment') to map attachment_id -> file path
  2. Parse wpr4_postmeta for _thumbnail_id to map post_id -> attachment_id
  3. Copy original image files (not resized variants) to media/images/
  4. Register each as a Wagtail Image
  5. Set featured_image on BlogPostPage, EventPage, ProductPage

Usage:
    python manage.py import_media
        --sql-path=/path/to/dump.sql
        --uploads-dir=/path/to/wp-content/uploads
        [--dry-run]
        [--limit=100]
"""

import os
import re
import shutil
from django.core.management.base import BaseCommand, CommandError


# WordPress auto-generated size suffix pattern
_SIZE_RE = re.compile(r'-\d+x\d+\.(jpg|jpeg|png|gif|webp)$', re.IGNORECASE)
# Supported image types Wagtail can handle
_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

BASE_WP_URL = "http://ideas-block.com/wp-content/uploads/"


def parse_attachments(sql_path: str, prefix: str) -> dict[int, str]:
    """
    Parse SQL dump and return {attachment_id: relative_file_path}.
    File path is relative to wp-content/uploads/.
    """
    from .import_wordpress import parse_row
    insert_marker = f"INSERT INTO `{prefix}posts`"
    collecting = False
    result: dict[int, str] = {}

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
            if not stripped.startswith("("):
                continue
            inner = stripped[1:-1] if stripped.endswith(")") else stripped[1:]
            row = parse_row(inner)
            if len(row) <= 20:
                continue
            if row[20] != "attachment":
                continue
            # guid (col 18) is the full URL to the file
            guid = row[18] or ""
            if guid.startswith(BASE_WP_URL):
                rel_path = guid[len(BASE_WP_URL):]
                try:
                    att_id = int(row[0])
                    result[att_id] = rel_path
                except (ValueError, TypeError):
                    pass
    return result


def parse_thumbnail_meta(sql_path: str, prefix: str) -> dict[int, int]:
    """Return {post_id: attachment_id} from _thumbnail_id postmeta."""
    from .import_wordpress import parse_row
    insert_marker = f"INSERT INTO `{prefix}postmeta`"
    collecting = False
    result: dict[int, int] = {}

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
            if not stripped.startswith("(") or "_thumbnail_id" not in stripped:
                continue
            inner = stripped[1:-1] if stripped.endswith(")") else stripped[1:]
            row = parse_row(inner)
            # postmeta cols: meta_id, post_id, meta_key, meta_value
            if len(row) >= 4 and row[2] == "_thumbnail_id":
                try:
                    result[int(row[1])] = int(row[3])
                except (ValueError, TypeError):
                    pass
    return result


class Command(BaseCommand):
    help = "Import WordPress images into Wagtail and link featured images to pages"

    def add_arguments(self, parser):
        parser.add_argument("--sql-path", required=True)
        parser.add_argument("--uploads-dir", required=True, help="Path to wp-content/uploads/")
        parser.add_argument("--table-prefix", default="wpr4_")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, default=0, help="Max images to import (0=all)")

    def handle(self, *args, **options):
        sql_path = options["sql_path"]
        uploads_dir = options["uploads_dir"]
        prefix = options["table_prefix"]
        dry_run = options["dry_run"]
        limit = options["limit"]

        for path in (sql_path, uploads_dir):
            if not os.path.exists(path):
                raise CommandError(f"Path not found: {path}")

        from django.conf import settings
        media_root = settings.MEDIA_ROOT
        dest_base = os.path.join(media_root, "images", "wp_import")
        os.makedirs(dest_base, exist_ok=True)

        # ── Step 1: parse attachments ────────────────────────────────────────
        self.stdout.write("Parsing attachment records from SQL dump…")
        attachments = parse_attachments(sql_path, prefix)
        self.stdout.write(f"  Found {len(attachments)} attachment records")

        # ── Step 2: parse thumbnail meta ────────────────────────────────────
        self.stdout.write("Parsing _thumbnail_id postmeta…")
        thumb_map = parse_thumbnail_meta(sql_path, prefix)
        self.stdout.write(f"  Found {len(thumb_map)} thumbnail assignments")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: no files copied, no DB writes."))
            return

        # ── Step 3 & 4: copy originals + register in Wagtail ────────────────
        from wagtail.images.models import Image as WagtailImage
        from django.core.files import File

        imported_images: dict[int, int] = {}  # attachment_id -> wagtail_image.id
        copied = 0
        skipped = 0

        items = list(attachments.items())
        if limit:
            items = items[:limit]

        self.stdout.write(f"Importing {len(items)} images…")
        for att_id, rel_path in items:
            ext = os.path.splitext(rel_path)[1].lower()
            if ext not in _IMAGE_EXTS:
                skipped += 1
                continue

            src_path = os.path.join(uploads_dir, rel_path)
            if not os.path.exists(src_path):
                skipped += 1
                continue

            # Skip WP resized variants
            filename = os.path.basename(rel_path)
            if _SIZE_RE.search(filename):
                skipped += 1
                continue

            # Check if already imported
            existing = WagtailImage.objects.filter(title=f"wp:{att_id}").first()
            if existing:
                imported_images[att_id] = existing.id
                skipped += 1
                continue

            # Copy file to media
            dest_dir = os.path.join(dest_base, os.path.dirname(rel_path))
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, filename)
            if not os.path.exists(dest_path):
                shutil.copy2(src_path, dest_path)

            # Register in Wagtail
            try:
                with open(dest_path, "rb") as img_file:
                    wagtail_img = WagtailImage(
                        title=f"wp:{att_id}",
                        file=File(img_file, name=filename),
                    )
                    wagtail_img.save()
                imported_images[att_id] = wagtail_img.id
                copied += 1
                if copied % 100 == 0:
                    self.stdout.write(f"  … {copied} imported")
            except Exception as e:
                self.stderr.write(f"  Error importing {filename}: {e}")
                skipped += 1

        self.stdout.write(f"  Images: {copied} imported, {skipped} skipped")

        # ── Step 5: link featured images to pages ────────────────────────────
        self.stdout.write("Linking featured images to pages…")
        self._link_featured_images(thumb_map, imported_images)

    def _link_featured_images(self, thumb_map: dict, imported_images: dict):
        from blog.models import BlogPostPage
        from events.models import EventPage
        from products.models import ProductPage
        from wagtail.images.models import Image as WagtailImage

        linked = 0
        for model_class in (BlogPostPage, EventPage, ProductPage):
            for page in model_class.objects.filter(wp_post_id__isnull=False, featured_image__isnull=True):
                att_id = thumb_map.get(page.wp_post_id)
                if att_id is None:
                    continue
                wagtail_img_id = imported_images.get(att_id)
                if wagtail_img_id is None:
                    # Try DB (already imported in a previous run)
                    img = WagtailImage.objects.filter(title=f"wp:{att_id}").first()
                    if img:
                        wagtail_img_id = img.id
                if wagtail_img_id:
                    page.featured_image_id = wagtail_img_id
                    page.save(update_fields=["featured_image"])
                    linked += 1

        self.stdout.write(f"  Linked featured images: {linked} pages updated")
