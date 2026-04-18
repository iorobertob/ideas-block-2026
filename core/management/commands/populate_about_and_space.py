"""
Management command: populate_about_and_space

Downloads all images from the original WordPress /the-space/,
/floor-plan-of-kompresorine/, and /about/ pages, then populates:
  - SpacePage: gallery + floor plan detail images + full body text
  - AboutPage: mission, vision, values, founders content

Usage:
    python manage.py populate_about_and_space
"""
import io
import json
import requests
from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand


# ── Image sources ─────────────────────────────────────────────────────────────

SPACE_GALLERY_IMAGES = [
    ("https://i0.wp.com/ideas-block.com/wp-content/uploads/2023/09/Entrance-1.jpg", "kompresorine-entrance.jpg", "Entrance"),
    ("https://i0.wp.com/ideas-block.com/wp-content/uploads/2023/01/gostauto_new.jpeg", "kompresorine-gostauto.jpeg", "A. Goštauto st. 11"),
    ("https://i0.wp.com/ideas-block.com/wp-content/uploads/2023/09/IMG_4836-1024x768.jpeg", "kompresorine-gallery-space.jpeg", "Gallery space"),
    ("https://i0.wp.com/ideas-block.com/wp-content/uploads/2023/09/IMG_6396.jpeg", "kompresorine-events-space.jpeg", "Events space"),
    ("https://i0.wp.com/ideas-block.com/wp-content/uploads/2023/09/Co-working-workshop-area.jpg", "kompresorine-coworking.jpg", "Co-working / workshop area"),
    ("https://i0.wp.com/ideas-block.com/wp-content/uploads/2023/09/Lab.jpg", "kompresorine-lab.jpg", "Lab"),
    ("https://i0.wp.com/ideas-block.com/wp-content/uploads/2023/09/Reading-Room.jpg", "kompresorine-reading-room.jpg", "Reading room"),
]

FLOOR_PLAN_IMAGES = [
    ("https://i0.wp.com/ideas-block.com/wp-content/uploads/2023/09/Screenshot-2023-09-18-at-15.19.45-1024x828.png", "floor-plan-events-space.png", "Events space layout"),
    ("https://i0.wp.com/ideas-block.com/wp-content/uploads/2023/09/Screenshot-2023-09-18-at-15.21.00-1024x806.png", "floor-plan-gallery-space.png", "Gallery space layout"),
    ("https://i0.wp.com/ideas-block.com/wp-content/uploads/2023/09/Screenshot-2023-09-18-at-15.20.30-1024x965.png", "floor-plan-ambisonics.png", "Ambisonics speaker layout — events space"),
]

ABOUT_FOUNDER_IMAGES = [
    ("https://i0.wp.com/ideas-block.com/wp-content/uploads/2021/03/image001-edited.jpg", "liucija-dervinyte.jpg", "Liucija Dervinytė"),
    ("https://i0.wp.com/ideas-block.com/wp-content/uploads/2021/03/me.branching.patterns.jpg", "roberto-becerra.jpg", "Roberto Becerra"),
]

# ── Content ───────────────────────────────────────────────────────────────────

SPACE_BODY = (
    "<p>Kompresorinė occupies a former compressor room of the old Physics Institute "
    "in Vilnius, at A. Goštauto st. 11. The venue also features a café open throughout "
    "the day and spans around 200 m² across three main areas.</p>"
    "<h2>Gallery Space — 42 m²</h2>"
    "<p>7.3-metre ceilings, abundant natural light, and reverberant acoustics — suited "
    "to exhibitions and concerts. Rental: €30/hour.</p>"
    "<h2>Events Space — 50 m²</h2>"
    "<p>Stage and sound equipment for concerts and performances, including a spatial "
    "ambisonic sound system with 23 speakers surrounding the space. Rental: €30/hour.</p>"
    "<h2>Co-working / Workshop Space — 70 m²</h2>"
    "<p>A co-working area, lab and equipment workshop, and a small reading room with "
    "books on culture, visual arts, music, and design. Rental: €20/hour.</p>"
    "<p><strong>Entire space:</strong> €60/hour. Additional services, equipment, and "
    "staff are charged separately.</p>"
    "<p>The entrance is in the courtyard accessible from A. Goštauto 11 or Lukiškių 9. "
    "Opening hours: Tuesday–Friday 3–7 pm · Saturday 11 am–5 pm.</p>"
)


def _build_about_body_json(founder_images):
    """Build the AboutPage body StreamField JSON with mission, vision, values, founders."""
    blocks = [
        {"type": "heading", "value": "Mission"},
        {"type": "paragraph", "value": (
            "<p>Ideas Block (VšĮ 'idėjų blokas LT') is a non-profit organisation with the "
            "mission to provide a framework, physical space and the necessary technology for "
            "relevant, interdisciplinary cultural content and education.</p>"
        )},
        {"type": "heading", "value": "Vision"},
        {"type": "paragraph", "value": (
            "<p>We aim to become self-sufficient while providing opportunities, building "
            "partnerships, and contributing to sustainable cultural environments through "
            "multiple platforms. In 2022 we opened Kompresorinė, an independent cultural "
            "space at A. Goštauto st. 11 in Vilnius. We also run Arttice, a digital "
            "networking platform for cultural sector professionals and organisations.</p>"
        )},
        {"type": "heading", "value": "Values"},
        {"type": "paragraph", "value": (
            "<ul>"
            "<li>Sharing ideas</li>"
            "<li>Sustainable culture</li>"
            "<li>Tolerance and freedom of expression</li>"
            "<li>Responsible social engagement</li>"
            "<li>Welcoming community</li>"
            "<li>Inspiring creativity</li>"
            "<li>Knowledge and research</li>"
            "<li>Partnerships and collaborations</li>"
            "<li>Flexible structure</li>"
            "</ul>"
        )},
        {"type": "heading", "value": "Co-founders"},
    ]

    for img, name, role in [
        (founder_images.get("liucija"), "Liucija Dervinytė", "Director — Artist and cultural manager"),
        (founder_images.get("roberto"), "Roberto Becerra", "Director — Technologist and artist"),
    ]:
        if img:
            blocks.append({
                "type": "image",
                "value": {"image": img.pk, "caption": f"{name} — {role}"},
            })
        blocks.append({
            "type": "paragraph",
            "value": f"<p><strong>{name}</strong> — {role}</p>",
        })

    return json.dumps(blocks)


def download_image(url, filename, title):
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        from wagtail.images.models import Image
        img = Image(title=title)
        img.file = ImageFile(io.BytesIO(resp.content), name=filename)
        img.save()
        return img
    except Exception as exc:
        return None


class Command(BaseCommand):
    help = "Populate SpacePage gallery and AboutPage with content from WordPress."

    def handle(self, *args, **options):
        from core.models import SpacePage, AboutPage
        from wagtail.images.models import Image

        about = AboutPage.objects.filter(slug="about").first()
        if not about:
            self.stderr.write("No AboutPage found.")
            return

        space = SpacePage.objects.child_of(about).first()
        if not space:
            self.stderr.write("No SpacePage under AboutPage found.")
            return

        # ── SpacePage: gallery images ─────────────────────────────────────────
        self.stdout.write("\n— Downloading Space gallery images…")
        gallery_blocks = []
        for url, filename, caption in SPACE_GALLERY_IMAGES:
            # Skip if already downloaded by title
            existing = Image.objects.filter(title=caption).first()
            if existing:
                self.stdout.write(f"  exists  {caption}")
                img = existing
            else:
                img = download_image(url, filename, caption)
                if img:
                    self.stdout.write(self.style.SUCCESS(f"  saved   {caption} (pk={img.pk})"))
                else:
                    self.stdout.write(self.style.WARNING(f"  failed  {caption}"))
                    continue
            gallery_blocks.append({"type": "image", "value": {"image": img.pk, "caption": caption}})

        # ── SpacePage: floor plan extra images ────────────────────────────────
        self.stdout.write("\n— Downloading floor plan detail images…")
        fp_extra_blocks = []
        for url, filename, caption in FLOOR_PLAN_IMAGES:
            existing = Image.objects.filter(title=caption).first()
            if existing:
                self.stdout.write(f"  exists  {caption}")
                img = existing
            else:
                img = download_image(url, filename, caption)
                if img:
                    self.stdout.write(self.style.SUCCESS(f"  saved   {caption} (pk={img.pk})"))
                else:
                    self.stdout.write(self.style.WARNING(f"  failed  {caption}"))
                    continue
            fp_extra_blocks.append({"type": "image", "value": {"image": img.pk, "caption": caption}})

        # Apply to SpacePage
        space.body = SPACE_BODY
        space.gallery = json.dumps(gallery_blocks)
        space.floor_plan_extra = json.dumps(fp_extra_blocks)
        space.save()
        rev = space.save_revision()
        rev.publish()
        self.stdout.write(self.style.SUCCESS(
            f"\nSpacePage updated: {space.full_url}\n"
            f"  gallery images:      {len(gallery_blocks)}\n"
            f"  floor plan details:  {len(fp_extra_blocks)}"
        ))

        # ── AboutPage: founder portrait images ────────────────────────────────
        self.stdout.write("\n— Downloading founder portraits…")
        founder_images = {}
        for url, filename, title in ABOUT_FOUNDER_IMAGES:
            key = "liucija" if "liucija" in filename else "roberto"
            existing = Image.objects.filter(title=title).first()
            if existing:
                self.stdout.write(f"  exists  {title}")
                founder_images[key] = existing
            else:
                img = download_image(url, filename, title)
                if img:
                    self.stdout.write(self.style.SUCCESS(f"  saved   {title} (pk={img.pk})"))
                    founder_images[key] = img
                else:
                    self.stdout.write(self.style.WARNING(f"  failed  {title}"))

        # ── AboutPage: body content ───────────────────────────────────────────
        about.body = _build_about_body_json(founder_images)
        about.intro = "Cultural organisation providing a framework, physical space, and technology for interdisciplinary cultural content and education."
        about.save()
        rev = about.save_revision()
        rev.publish()
        self.stdout.write(self.style.SUCCESS(
            f"\nAboutPage updated: {about.full_url}\n"
            f"  intro set, body blocks written, founder images: {list(founder_images.keys())}"
        ))
