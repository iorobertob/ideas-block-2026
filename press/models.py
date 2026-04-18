from django.db import models

from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.blocks import (
    CharBlock, RichTextBlock, URLBlock, StructBlock, DateBlock,
)
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock


class PressPage(Page):
    """Press room: contact, press kits, and coverage log."""

    template = "press/presspage.html"

    intro = RichTextField(blank=True)
    press_contact_name = models.CharField(max_length=255, blank=True)
    press_contact_email = models.EmailField(blank=True)
    press_contact_phone = models.CharField(max_length=100, blank=True)

    # Downloadable press kits and assets
    press_kits = StreamField(
        [
            ("kit", StructBlock([
                ("title", CharBlock()),
                ("description", CharBlock(required=False)),
                ("document", DocumentChooserBlock()),
            ], label="Press kit / document")),
        ],
        use_json_field=True,
        blank=True,
    )

    # High-res image assets for press use
    press_images = StreamField(
        [
            ("image", StructBlock([
                ("caption", CharBlock(required=False)),
                ("credit", CharBlock(required=False)),
                ("image", ImageChooserBlock()),
            ], label="Press image")),
        ],
        use_json_field=True,
        blank=True,
    )

    # Organisation boilerplate
    boilerplate = RichTextField(
        blank=True,
        help_text="Standard organisation description for press use (copy-pasteable).",
    )

    # Press coverage log
    coverage = StreamField(
        [
            ("article", StructBlock([
                ("headline", CharBlock()),
                ("publication", CharBlock()),
                ("date", DateBlock(required=False)),
                ("url", URLBlock(required=False)),
                ("language", CharBlock(default="EN", required=False)),
            ], label="Press article")),
        ],
        use_json_field=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        MultiFieldPanel([
            FieldPanel("press_contact_name"),
            FieldPanel("press_contact_email"),
            FieldPanel("press_contact_phone"),
        ], heading="Press contact"),
        FieldPanel("press_kits"),
        FieldPanel("press_images"),
        FieldPanel("boilerplate"),
        FieldPanel("coverage"),
    ]

    class Meta:
        verbose_name = "Press Page"
