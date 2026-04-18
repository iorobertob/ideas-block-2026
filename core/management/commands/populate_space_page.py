"""
Management command: populate_space_page

Downloads real content and images from the live WordPress site and populates
the Wagtail SpacePage with accurate venue information.

Usage:
    python manage.py populate_space_page
"""
import io
import requests
from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand


IMAGES = {
    "hero": "https://i0.wp.com/ideas-block.com/wp-content/uploads/2023/09/343326740_2228647517342801_6359593650874086280_n-1024x683.jpg",
    "floor_plan": "https://i0.wp.com/ideas-block.com/wp-content/uploads/2023/05/Kompresorine-space-plan-1.png",
}

BODY_HTML = """<p>Kompresorinė is a cultural venue in a former compressor room at A. Goštauto st. 11 in Vilnius. The facility spans approximately 200 square meters across three main areas:</p>

<ul>
  <li><strong>Gallery Space (42 m²)</strong> — 7.3-metre ceilings, abundant natural light, and acoustic properties suited to exhibitions and concerts.</li>
  <li><strong>Events Space (50 m²)</strong> — Stage and sound equipment including a 23-speaker spatial ambisonic system.</li>
  <li><strong>Co-working / Workshop / Reading Room (70 m²)</strong> — Creative workspace, equipment lab, and a library focused on culture, arts, music, and design.</li>
</ul>

<p><strong>Opening hours:</strong> Tuesday–Friday 3–7 pm · Saturday 11 am–5 pm</p>

<p><strong>Rental rates:</strong><br>
€30/hour — gallery or events space<br>
€20/hour — co-working/workshop area<br>
€60/hour — entire space<br>
Additional charges may apply for services, equipment, and staff.</p>

<p>The entrance is in the courtyard accessible from A. Goštauto 11 or Lukiškių 9.</p>"""

BOOKING_INFO_HTML = """<p>To enquire about booking Kompresorinė for exhibitions, events, workshops, or residencies, please get in touch by email. Co-working and lab memberships are available via Contribee.</p>"""


def download_image(url, filename):
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return ImageFile(io.BytesIO(resp.content), name=filename)
    except requests.RequestException as exc:
        return None, str(exc)


class Command(BaseCommand):
    help = "Populate SpacePage with real content and images from the WordPress site."

    def handle(self, *args, **options):
        from core.models import SpacePage
        from wagtail.images.models import Image

        # Target the SpacePage that is a child of AboutPage
        from core.models import AboutPage
        about = AboutPage.objects.filter(slug="about").first()
        if not about:
            self.stderr.write("No AboutPage found. Run restructure_about first.")
            return
        space = SpacePage.objects.child_of(about).first()
        if not space:
            self.stderr.write("No SpacePage under AboutPage found.")
            return

        # ── Hero image ────────────────────────────────────────────────────────
        if not space.hero_image or space.hero_image.title.startswith("wp:"):
            self.stdout.write("Downloading hero image…")
            img_file = download_image(IMAGES["hero"], "kompresorine-interior.jpg")
            if img_file:
                hero_img = Image(title="Kompresorinė interior")
                hero_img.file = img_file
                hero_img.save()
                space.hero_image = hero_img
                self.stdout.write(self.style.SUCCESS(f"  Hero image saved (pk={hero_img.pk})"))
            else:
                self.stdout.write(self.style.WARNING("  Could not download hero image — skipping"))

        # ── Floor plan image ──────────────────────────────────────────────────
        if not space.floor_plan_image or space.floor_plan_image.title.startswith("wp:"):
            self.stdout.write("Downloading floor plan image…")
            img_file = download_image(IMAGES["floor_plan"], "kompresorine-floor-plan.png")
            if img_file:
                fp_img = Image(title="Kompresorinė floor plan")
                fp_img.file = img_file
                fp_img.save()
                space.floor_plan_image = fp_img
                self.stdout.write(self.style.SUCCESS(f"  Floor plan image saved (pk={fp_img.pk})"))
            else:
                self.stdout.write(self.style.WARNING("  Could not download floor plan image — skipping"))

        # ── Text content ──────────────────────────────────────────────────────
        space.title = "The Space"
        space.slug = "space"
        space.intro = "Kompresorinė — our cultural venue at A. Goštauto st. 11, Vilnius."
        space.body = BODY_HTML
        space.address = "A. Goštauto st. 11, Vilnius (courtyard entrance also from Lukiškių 9)"
        space.capacity = "200 m² total — gallery 42 m², events 50 m², co-working 70 m²"
        space.booking_email = "contact@ideas-block.com"
        space.booking_info = BOOKING_INFO_HTML
        space.save()

        rev = space.save_revision()
        rev.publish()

        self.stdout.write(self.style.SUCCESS(
            f"\nSpacePage updated: {space.full_url}\n"
            f"  title:         {space.title}\n"
            f"  hero_image:    {space.hero_image}\n"
            f"  floor_plan:    {space.floor_plan_image}\n"
            f"  address:       {space.address}"
        ))
