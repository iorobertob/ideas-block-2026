"""
Management command: audit_wp_redirects

Fetches the live WordPress sitemap from ideas-block.com, attempts to match
each old URL to a Wagtail page in the new site, creates permanent redirects
for matches, and writes a CSV report of all URLs for manual review.

Usage:
    python manage.py audit_wp_redirects [--dry-run] [--output wp_redirect_audit.csv]
"""
import csv
import re
import xml.etree.ElementTree as ET

import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Page, Site

SITEMAP_ROOT = "https://ideas-block.com/sitemap.xml"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def fetch_urls(sitemap_url):
    """Recursively fetch all <loc> URLs from a sitemap or sitemap index."""
    try:
        resp = requests.get(sitemap_url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return [], str(exc)

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as exc:
        return [], str(exc)

    # Sitemap index — recurse into child sitemaps
    children = root.findall("sm:sitemap/sm:loc", NS)
    if children:
        urls = []
        for child in children:
            child_urls, _ = fetch_urls(child.text.strip())
            urls.extend(child_urls)
        return urls, None

    # Regular sitemap
    return [loc.text.strip() for loc in root.findall("sm:url/sm:loc", NS)], None


def slug_from_path(path):
    """Return the last non-empty path segment."""
    parts = [p for p in path.strip("/").split("/") if p]
    return parts[-1] if parts else ""


def classify(path):
    """
    Return (suggested_new_path, match_type, notes) based on heuristics.
    Caller should still try a live Wagtail slug lookup first.
    """
    p = path.strip("/")
    parts = p.split("/")

    # --- Static known remaps ---
    static = {
        "the-space": ("/about/space/", "static", "SpacePage under About"),
        "floor-plan-of-kompresorine": ("/about/space/", "static", "content now in SpacePage"),
        "program": ("/events/", "static", "WordPress programme page → events index"),
        "event-calendar": ("/events/", "static", "event calendar → events index"),
        "open-call": ("/open-calls/", "static", "open call index"),
        "artist-residence": ("/open-calls/", "static", "residency open calls"),
        "shop": ("/products/", "static", "WooCommerce shop → products index"),
        "basket": ("/members/", "static", "WooCommerce cart → members"),
        "checkout": ("/members/", "static", "WooCommerce checkout → members"),
        "my-account": ("/members/dashboard/", "static", "WooCommerce account → member dashboard"),
        "blog": ("/blog/", "static", "blog index"),
        "home": ("/", "static", "duplicate home"),
        "support-culture": ("/", "static", "support page → homepage"),
        "support-us-in-contribee": ("/", "static", "support page → homepage"),
        "terms-and-conditions": ("/about/terms-and-conditions/", "static", "T&C RichPage under About"),
        "return-policy": ("/about/terms-and-conditions/", "static", "return policy → T&C"),
        "mind-sharpener": ("/blog/", "static", "talk series → blog"),
        "art-distancing": ("/projects/", "static", "art distancing project → projects"),
        "supermarket2019": ("/events/", "static", "event → events"),
        "notcriticising-nekritika": ("/projects/", "static", "project → projects"),
    }

    if len(parts) == 1 and parts[0] in static:
        return static[parts[0]]

    # /about/* sub-pages
    if parts[0] == "about":
        if len(parts) == 1:
            return ("/about/", "static", "about page")
        sub = parts[1]
        if "2018" in sub:
            return ("/about/transparency/2018-report/", "static", "2018 annual report")
        if "2019" in sub:
            return ("/about/transparency/2019-report/", "static", "2019 annual report")
        if "2020" in sub:
            return ("/about/transparency/2020-report/", "static", "2020 annual report")
        if "privacy" in sub:
            return ("/about/privacy-policy/", "static", "privacy policy under About")
        if "newsletter" in sub:
            return ("/", "static", "newsletter signup → homepage")
        return ("/about/", "heuristic", f"unknown about sub-page: {sub}")

    # /shop/<slug>/ → /products/<slug>/
    if parts[0] == "shop" and len(parts) >= 2:
        product_slug = parts[1]
        return (f"/products/{product_slug}/", "slug-remap", "WooCommerce product → ProductPage")

    # COVID series
    if parts[0].startswith("covid-19-creative-outlet"):
        return ("/blog/", "fallback", "COVID creative outlet series → blog index")

    # City explorer series
    if parts[0].startswith("city-explorer"):
        return ("/blog/", "fallback", "city explorer series → blog index")

    # Mind sharpener series
    if parts[0].startswith("mind-sharpener"):
        return ("/blog/", "fallback", "mind sharpener talk → blog index")

    # open-call-* slugs
    if parts[0].startswith("open-call"):
        return ("/open-calls/", "heuristic", "open call → open calls index")

    # unbodies / residency pages
    if "residency" in parts[0] or "unbodies" in parts[0]:
        return ("/projects/", "heuristic", "residency → projects")

    # Fallback
    return ("/", "fallback", "no match found — redirecting to homepage")


class Command(BaseCommand):
    help = "Audit WordPress URLs and create Wagtail redirects for the new site."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report only — do not write any redirects to the database.",
        )
        parser.add_argument(
            "--output", default="wp_redirect_audit.csv",
            help="Path for the CSV audit report (default: wp_redirect_audit.csv).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        output_path = options["output"]

        self.stdout.write("Fetching WordPress sitemap…")
        urls, error = fetch_urls(SITEMAP_ROOT)
        if error:
            self.stderr.write(f"Error fetching sitemap: {error}")
            return
        self.stdout.write(f"Found {len(urls)} URLs in sitemap.")

        try:
            from wagtail.contrib.redirects.models import Redirect
        except ImportError:
            self.stderr.write(
                "wagtail.contrib.redirects is not installed. "
                "Add it to INSTALLED_APPS and run migrate first."
            )
            return

        site = Site.objects.filter(is_default_site=True).first()

        counts = {"auto": 0, "heuristic": 0, "slug-remap": 0, "fallback": 0, "static": 0, "skipped": 0}
        rows = []

        with transaction.atomic():
            for full_url in urls:
                # Strip domain to get path
                path = re.sub(r"^https?://[^/]+", "", full_url).rstrip("/") + "/"
                if path in ("/", "//"):
                    continue

                slug = slug_from_path(path)
                new_path = None
                match_type = None
                notes = ""

                # 1. Try exact slug match against live Wagtail pages
                page = Page.objects.filter(slug=slug).live().first()
                if page:
                    full_url_new = page.full_url or page.get_url()
                    new_path = full_url_new
                    match_type = "auto"
                    notes = f"{page.specific_class.__name__} pk={page.pk}"

                # 2. Heuristics
                if not page:
                    new_path, match_type, notes = classify(path)

                rows.append({
                    "old_url": full_url,
                    "old_path": path,
                    "status": match_type,
                    "new_url": new_path,
                    "match_type": match_type,
                    "notes": notes,
                })

                counts[match_type] = counts.get(match_type, 0) + 1

                if dry_run:
                    continue

                # Write redirect
                old_path_normalised = Redirect.normalise_path(path)
                if Redirect.objects.filter(old_path=old_path_normalised, site=site).exists():
                    counts["skipped"] += 1
                    continue

                if page:
                    Redirect.objects.create(
                        old_path=old_path_normalised,
                        site=site,
                        redirect_page=page,
                        is_permanent=True,
                    )
                else:
                    Redirect.objects.create(
                        old_path=old_path_normalised,
                        site=site,
                        redirect_link=new_path,
                        is_permanent=True,
                    )

        # Write CSV
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["old_url", "old_path", "status", "new_url", "match_type", "notes"])
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(
            f"\nDone{'  (DRY RUN)' if dry_run else ''}:\n"
            f"  auto-matched (slug):  {counts.get('auto', 0)}\n"
            f"  static remaps:        {counts.get('static', 0)}\n"
            f"  slug-remap (/shop/):  {counts.get('slug-remap', 0)}\n"
            f"  heuristic:            {counts.get('heuristic', 0)}\n"
            f"  fallback (→ /):       {counts.get('fallback', 0)}\n"
            f"  skipped (exists):     {counts.get('skipped', 0)}\n"
            f"  CSV written to:       {output_path}"
        ))
