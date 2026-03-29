from django.db import models
from django.utils import timezone

from wagtail.models import Page
from wagtail.fields import StreamField, RichTextField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, HelpPanel
from wagtail.blocks import CharBlock, RichTextBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.search import index


class EventsIndexPage(Page):
    intro = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["events.EventPage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        now = timezone.now().date()
        all_events = (
            EventPage.objects.child_of(self).live().order_by("-start_date")
        )
        # Full-text search
        query = request.GET.get("q", "").strip()
        if query:
            all_events = all_events.search(query)
        context["query"] = query
        filter_type = request.GET.get("filter", "all")
        if filter_type == "upcoming":
            all_events = all_events.filter(start_date__gte=now)
        elif filter_type == "past":
            all_events = all_events.filter(start_date__lt=now)
        # Year filter
        year = request.GET.get("year")
        if year and year.isdigit():
            all_events = all_events.filter(start_date__year=int(year))
        context["events"] = all_events
        context["filter_type"] = filter_type
        context["years"] = (
            EventPage.objects.child_of(self)
            .live()
            .exclude(start_date__isnull=True)
            .dates("start_date", "year", order="DESC")
        )
        return context

    class Meta:
        verbose_name = "Events Index"


class EventPage(Page):
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    intro = models.TextField(blank=True, max_length=500)
    featured_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    body = StreamField(
        [
            ("heading", CharBlock(form_classname="title")),
            ("paragraph", RichTextBlock(features=["h2","h3","h4","bold","italic","ol","ul","hr","link","document-link","image","embed","blockquote","code"])),
            ("image", ImageChooserBlock()),
        ],
        use_json_field=True,
        blank=True,
    )
    ticket_url = models.URLField(blank=True)
    use_stripe = models.BooleanField(default=False, help_text="Use built-in Stripe checkout for tickets")
    sku = models.CharField(max_length=100, blank=True, help_text="Event SKU for ticket scanning")
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # WordPress import metadata
    wp_post_id = models.IntegerField(null=True, blank=True, db_index=True)
    language = models.CharField(max_length=5, default="en", choices=[("en", "English"), ("lt", "Lietuvių")])

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("location"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("start_date"),
            FieldPanel("end_date"),
            FieldPanel("start_time"),
            FieldPanel("location"),
            FieldPanel("language"),
        ], heading="Event details"),
        FieldPanel("intro"),
        FieldPanel("featured_image"),
        FieldPanel("body"),
        MultiFieldPanel([
            HelpPanel(content=(
                "<strong>To enable online ticket sales via Stripe:</strong><br>"
                "1. Set a <em>Price</em> (e.g. 10.00) and uncheck <em>Is free</em>.<br>"
                "2. Set an <em>Event SKU</em> — a short unique code like <code>EVT-2025-01</code> "
                "used to identify this event on the door scanner.<br>"
                "3. Check <em>Use Stripe checkout</em>. A &ldquo;Get tickets&rdquo; button will "
                "appear on the event page once you publish.<br>"
                "4. Stripe keys must be configured in <code>.env</code> "
                "(<code>STRIPE_PUBLISHABLE_KEY</code> / <code>STRIPE_SECRET_KEY</code>).<br>"
                "If you have an external ticketing URL instead, leave <em>Use Stripe checkout</em> "
                "unchecked and fill in <em>Ticket URL</em>."
            )),
            FieldPanel("is_free"),
            FieldPanel("price"),
            FieldPanel("sku"),
            FieldPanel("use_stripe"),
            FieldPanel("ticket_url"),
        ], heading="Tickets &amp; Payment"),
    ]

    parent_page_types = ["events.EventsIndexPage"]

    @property
    def is_past(self):
        if self.start_date:
            return self.start_date < timezone.now().date()
        return False

    class Meta:
        verbose_name = "Event"
