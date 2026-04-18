from django.db import models
from django.utils import timezone

from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.blocks import CharBlock, RichTextBlock, StructBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.search import index


class OpenCallsIndexPage(Page):
    template = "opencalls/opencallsindexpage.html"

    intro = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["opencalls.OpenCallPage", "opencalls.PastCallsIndexPage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        today = timezone.now().date()
        all_calls = OpenCallPage.objects.child_of(self).live()
        context["open_calls"] = (
            all_calls
            .filter(models.Q(deadline__gte=today) | models.Q(deadline__isnull=True))
            .order_by("deadline")
        )
        context["past_calls_page"] = (
            PastCallsIndexPage.objects.child_of(self).live().first()
        )
        return context

    class Meta:
        verbose_name = "Open Calls Index"


class PastCallsIndexPage(Page):
    template = "opencalls/pastcallsindexpage.html"

    intro = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["opencalls.OpenCallPage"]
    parent_page_types = ["opencalls.OpenCallsIndexPage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["past_calls"] = (
            OpenCallPage.objects.child_of(self).live().order_by("-deadline")
        )
        return context

    class Meta:
        verbose_name = "Past Calls Index"


class OpenCallPage(Page):
    template = "opencalls/opencallpage.html"

    subtitle = models.CharField(max_length=255, blank=True)
    deadline = models.DateField(
        null=True, blank=True,
        help_text="Application deadline. Leave blank for rolling/ongoing calls.",
    )
    call_type = models.CharField(
        max_length=100,
        blank=True,
        choices=[
            ("residency", "Residency"),
            ("exhibition", "Exhibition Proposal"),
            ("commission", "Commission"),
            ("research", "Research"),
            ("workshop", "Workshop Pitch"),
            ("other", "Other"),
        ],
        default="",
    )
    featured_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    intro = models.TextField(blank=True, max_length=500)
    body = StreamField(
        [
            ("heading", CharBlock(form_classname="title")),
            ("paragraph", RichTextBlock(features=["h2","h3","h4","bold","italic","ol","ul","hr","link","document-link","blockquote","code"])),
            ("image", ImageChooserBlock()),
            ("eligibility", StructBlock([
                ("title", CharBlock(default="Who can apply")),
                ("text", RichTextBlock()),
            ], label="Eligibility block")),
        ],
        use_json_field=True,
        blank=True,
    )
    application_email = models.EmailField(
        blank=True,
        help_text="Email address for applications (used if no external form URL).",
    )
    application_url = models.URLField(
        blank=True,
        help_text="External application form URL (e.g. Google Form, Submittable).",
    )
    fee = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. 'Free', '€10', 'By invitation'",
    )

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
        index.SearchField("call_type"),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("subtitle"),
            FieldPanel("call_type"),
            FieldPanel("deadline"),
            FieldPanel("fee"),
        ], heading="Call details"),
        FieldPanel("intro"),
        FieldPanel("featured_image"),
        FieldPanel("body"),
        MultiFieldPanel([
            FieldPanel("application_email"),
            FieldPanel("application_url"),
        ], heading="How to apply"),
    ]

    parent_page_types = ["opencalls.OpenCallsIndexPage", "opencalls.PastCallsIndexPage"]

    @property
    def is_open(self):
        if self.deadline is None:
            return True
        return self.deadline >= timezone.now().date()

    class Meta:
        verbose_name = "Open Call"
