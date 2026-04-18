from django.db import models
from django.core.mail import send_mail
from django.contrib import messages as django_messages
from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.blocks import (
    CharBlock, RichTextBlock, URLBlock, StructBlock, TextBlock,
)
from wagtail.images.blocks import ImageChooserBlock
from wagtail.documents.blocks import DocumentChooserBlock


class ContactPage(Page):
    intro = RichTextField(blank=True)
    address = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("address"),
        FieldPanel("email"),
        FieldPanel("phone"),
    ]

    def serve(self, request, *args, **kwargs):
        from django.shortcuts import render
        if request.method == "POST":
            name = request.POST.get("name", "")
            email = request.POST.get("email", "")
            message = request.POST.get("message", "")
            if name and email and message:
                try:
                    send_mail(
                        subject=f"[Ideas Block contact] from {name}",
                        message=f"From: {name} <{email}>\n\n{message}",
                        from_email="noreply@ideas-block.com",
                        recipient_list=[self.email or "contact@ideas-block.com"],
                    )
                    django_messages.success(request, "Thank you — your message has been sent.")
                except Exception:
                    django_messages.error(request, "There was an error sending your message. Please try emailing us directly.")
        return render(request, "core/contact_page.html", {"page": self, "messages": django_messages.get_messages(request)})

    class Meta:
        verbose_name = "Contact Page"


class SpacePage(Page):
    """The Kompresorinė venue page with floor plan and description."""
    parent_page_types = ["core.AboutPage"]

    intro = models.TextField(blank=True)
    body = RichTextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    gallery = StreamField(
        [("image", StructBlock([
            ("image", ImageChooserBlock()),
            ("caption", CharBlock(required=False)),
        ], label="Photo"))],
        use_json_field=True, blank=True,
        help_text="Additional venue photos",
    )
    floor_plan_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        help_text="Primary floor plan image",
    )
    floor_plan_extra = StreamField(
        [("image", StructBlock([
            ("image", ImageChooserBlock()),
            ("caption", CharBlock(required=False)),
        ], label="Floor plan detail"))],
        use_json_field=True, blank=True,
        help_text="Additional floor plan / technical drawings",
    )
    capacity = models.CharField(max_length=100, blank=True)
    booking_email = models.EmailField(blank=True)
    booking_info = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("hero_image"),
        FieldPanel("body"),
        FieldPanel("gallery"),
        FieldPanel("address"),
        FieldPanel("capacity"),
        FieldPanel("floor_plan_image"),
        FieldPanel("floor_plan_extra"),
        FieldPanel("booking_email"),
        FieldPanel("booking_info"),
    ]

    class Meta:
        verbose_name = "Space / Venue Page"


class RichPage(Page):
    """Generic rich-text page for About, Documents, and similar standalone pages."""
    intro = models.TextField(blank=True)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
    ]

    class Meta:
        verbose_name = "Rich Text Page"


class AboutPage(Page):
    """Institutional about page with narrative sections, funders, and team overview."""
    subpage_types = ["core.SpacePage", "core.RichPage", "core.TransparencyPage"]


    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    intro = models.TextField(
        blank=True,
        help_text="Short intro sentence shown in the page header.",
    )

    body = StreamField(
        [
            ("heading", CharBlock(form_classname="title")),
            ("paragraph", RichTextBlock(features=["h2","h3","h4","bold","italic","ol","ul","hr","link","document-link","blockquote","code"])),
            ("image", StructBlock([
                ("image", ImageChooserBlock()),
                ("caption", CharBlock(required=False)),
            ], label="Image with caption")),
            ("annual_report", StructBlock([
                ("year", CharBlock()),
                ("title", CharBlock(required=False)),
                ("document", DocumentChooserBlock(required=False)),
                ("url", URLBlock(required=False,
                    help_text="External link if document is hosted elsewhere")),
            ], label="Annual report")),
        ],
        use_json_field=True,
        blank=True,
        help_text="Main narrative body — history, mission, values, etc.",
    )

    # Funders and partners
    funders = StreamField(
        [
            ("funder", StructBlock([
                ("name", CharBlock()),
                ("logo", ImageChooserBlock(required=False)),
                ("url", URLBlock(required=False)),
                ("description", CharBlock(required=False)),
            ], label="Funder / partner")),
        ],
        use_json_field=True,
        blank=True,
        help_text="Funders, partners, sponsors — logos and links.",
    )

    contact_address = models.TextField(blank=True, help_text="Physical address")
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("hero_image"),
        FieldPanel("body"),
        FieldPanel("funders"),
        MultiFieldPanel([
            FieldPanel("contact_address"),
            FieldPanel("contact_email"),
            FieldPanel("contact_phone"),
        ], heading="Contact details"),
    ]

    class Meta:
        verbose_name = "About Page"


class TransparencyPage(Page):
    """Transparency/governance section under About — houses annual reports."""
    parent_page_types = ["core.AboutPage"]
    subpage_types = ["core.AnnualReportPage"]

    intro = models.TextField(blank=True)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
    ]

    class Meta:
        verbose_name = "Transparency Page"


class AnnualReportPage(Page):
    """Individual annual / financial report, child of TransparencyPage."""
    parent_page_types = ["core.TransparencyPage"]
    subpage_types = []

    year = models.IntegerField()
    intro = models.TextField(blank=True)
    body = RichTextField(blank=True)
    document = models.ForeignKey(
        "wagtaildocs.Document",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    external_url = models.URLField(blank=True, help_text="Link if report is hosted externally")

    content_panels = Page.content_panels + [
        FieldPanel("year"),
        FieldPanel("intro"),
        FieldPanel("body"),
        FieldPanel("document"),
        FieldPanel("external_url"),
    ]

    class Meta:
        verbose_name = "Annual Report"
        ordering = ["-year"]
