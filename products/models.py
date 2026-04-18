from django.db import models

from wagtail.models import Page
from wagtail.fields import StreamField, RichTextField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, HelpPanel
from wagtail.blocks import CharBlock, RichTextBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.search import index


class ProductsIndexPage(Page):
    intro = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["products.ProductPage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        products = ProductPage.objects.child_of(self).live().order_by("-first_published_at")
        # Full-text search
        query = request.GET.get("q", "").strip()
        if query:
            products = products.search(query)
        context["query"] = query
        # Availability filter
        avail = request.GET.get("available")
        if avail == "1":
            products = products.filter(is_available=True)
        # Price filter
        price_filter = request.GET.get("price")
        if price_filter == "free":
            products = products.filter(price__isnull=True, price_display="")
        elif price_filter == "paid":
            products = products.exclude(price__isnull=True)
        context["products"] = products
        context["active_filter"] = avail or price_filter or "all"
        return context

    class Meta:
        verbose_name = "Products Index"


class ProductPage(Page):
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
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price_display = models.CharField(max_length=100, blank=True, help_text="e.g. '€25 / free for members'")
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum units/registrations. Leave blank for unlimited.")
    is_available = models.BooleanField(default=False, help_text="Show a purchase/registration CTA")
    use_stripe = models.BooleanField(default=False, help_text="Use built-in Stripe checkout instead of external URL")
    external_purchase_url = models.URLField(blank=True)
    sku = models.CharField(max_length=100, blank=True, help_text="Product SKU for ticket scanning")
    # WordPress import metadata
    wp_post_id = models.IntegerField(null=True, blank=True, db_index=True)

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("featured_image"),
        FieldPanel("body"),
        MultiFieldPanel([
            HelpPanel(content=(
                "<strong>To enable online purchases via Stripe:</strong><br>"
                "1. Enter the <em>Price</em> (e.g. 25.00) and optionally a <em>Price display</em> "
                "label (e.g. &ldquo;€25 / free for members&rdquo;).<br>"
                "2. Set a <em>SKU</em> — a short unique code like <code>WS-2025-01</code>.<br>"
                "3. Check <em>Is available</em> to show the purchase button on the page.<br>"
                "4. Check <em>Use Stripe checkout</em> to route buyers through Stripe.<br>"
                "5. Alternatively, add an <em>External purchase URL</em> (e.g. Eventbrite link) "
                "and leave <em>Use Stripe checkout</em> unchecked.<br>"
                "Stripe keys must be set in <code>.env</code>."
            )),
            FieldPanel("price"),
            FieldPanel("price_display"),
            FieldPanel("capacity"),
            FieldPanel("sku"),
            FieldPanel("is_available"),
            FieldPanel("use_stripe"),
            FieldPanel("external_purchase_url"),
        ], heading="Pricing &amp; Payment"),
    ]

    parent_page_types = ["products.ProductsIndexPage"]

    class Meta:
        verbose_name = "Product / Workshop"
