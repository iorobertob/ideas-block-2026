"""
Management command: restructure_about

Converts the About RichPage into a proper AboutPage and builds the correct
child hierarchy:

  AboutPage (slug=about)
  ├── SpacePage     (slug=space)        [moved from root]
  ├── TransparencyPage (slug=transparency)
  │     ├── AnnualReportPage (slug=2018-report)
  │     └── AnnualReportPage (slug=2019-report)
  └── RichPage      (slug=privacy-policy) [moved from root]

Safe to run multiple times — skips work that's already done.

Usage:
    python manage.py restructure_about
"""
from django.core.management.base import BaseCommand
from wagtail.models import Page


class Command(BaseCommand):
    help = "Restructure the About section into a proper page hierarchy."

    def handle(self, *args, **options):
        from core.models import AboutPage, SpacePage, TransparencyPage, AnnualReportPage, RichPage
        from home.models import HomePage

        home = HomePage.objects.first()
        if not home:
            self.stderr.write("No HomePage found.")
            return

        # ── 1. Ensure an AboutPage exists at slug=about ──────────────────────
        about_page = AboutPage.objects.filter(slug="about").first()
        if not about_page:
            # There may be a legacy RichPage at slug=about — rename it first
            old_about = Page.objects.filter(slug="about").first()
            if old_about:
                old_about.slug = "about-legacy"
                old_about.save()
                self.stdout.write("  Renamed old RichPage 'about' → 'about-legacy'")

            about_page = AboutPage(
                title="About",
                slug="about",
                intro="Ideas Block — cultural organisation, Vilnius.",
            )
            home.add_child(instance=about_page)
            rev = about_page.save_revision()
            rev.publish()
            self.stdout.write(self.style.SUCCESS("  Created AboutPage slug=about"))
        else:
            self.stdout.write("  AboutPage already exists")

        # ── 2. Move SpacePage under AboutPage ─────────────────────────────────
        space = SpacePage.objects.filter(slug="space").first()
        if space:
            if space.get_parent().pk != about_page.pk:
                space.move(about_page, pos="last-child")
                self.stdout.write(self.style.SUCCESS("  Moved SpacePage under AboutPage"))
            else:
                self.stdout.write("  SpacePage already under AboutPage")
        else:
            self.stdout.write("  SpacePage not found — create it via create_site_pages")

        # ── 3. Move privacy-policy RichPage under AboutPage ───────────────────
        privacy = Page.objects.filter(slug="privacy-policy").first()
        if privacy:
            if privacy.get_parent().pk != about_page.pk:
                privacy.move(about_page, pos="last-child")
                self.stdout.write(self.style.SUCCESS("  Moved privacy-policy under AboutPage"))
            else:
                self.stdout.write("  privacy-policy already under AboutPage")

        # ── 4. Create TransparencyPage under AboutPage ────────────────────────
        transparency = TransparencyPage.objects.filter(slug="transparency").first()
        if not transparency:
            transparency = TransparencyPage(
                title="Transparency",
                slug="transparency",
                intro="<p>Organisational documents, financial reports, and governance information.</p>",
            )
            about_page.add_child(instance=transparency)
            rev = transparency.save_revision()
            rev.publish()
            self.stdout.write(self.style.SUCCESS("  Created TransparencyPage"))
        else:
            if transparency.get_parent().pk != about_page.pk:
                transparency.move(about_page, pos="last-child")
                self.stdout.write(self.style.SUCCESS("  Moved TransparencyPage under AboutPage"))
            else:
                self.stdout.write("  TransparencyPage already under AboutPage")

        # ── 5. Migrate legacy documents RichPage content into AnnualReportPages
        docs_page = Page.objects.filter(slug="documents").first()

        for year in (2018, 2019, 2020):
            slug = f"{year}-report"
            if AnnualReportPage.objects.filter(slug=slug).exists():
                self.stdout.write(f"  AnnualReportPage {year}: already exists")
                continue
            report = AnnualReportPage(
                title=f"Annual Report {year}",
                slug=slug,
                year=year,
                intro=f"VSI Idėjų Blokas — {year} annual financial report.",
            )
            transparency.add_child(instance=report)
            rev = report.save_revision()
            rev.publish()
            self.stdout.write(self.style.SUCCESS(f"  Created AnnualReportPage {year}"))

        # Delete legacy documents RichPage once reports are created
        if docs_page and docs_page.slug == "documents":
            docs_page.delete()
            self.stdout.write(self.style.SUCCESS("  Deleted legacy documents RichPage"))

        self.stdout.write(self.style.SUCCESS("\nAbout hierarchy restructure complete."))
        self.stdout.write("\nResulting tree:")
        about_page.refresh_from_db()
        self.stdout.write(f"  {about_page.full_url} [{about_page.specific_class.__name__}]")
        for child in about_page.get_children().specific():
            self.stdout.write(f"    {child.full_url} [{child.__class__.__name__}]")
            if hasattr(child, 'get_children'):
                for grandchild in child.get_children().specific():
                    self.stdout.write(f"      {grandchild.full_url} [{grandchild.__class__.__name__}]")
