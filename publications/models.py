from django.db import models

from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.blocks import CharBlock, RichTextBlock, URLBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.search import index


class PublicationsIndexPage(Page):
    intro = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["publications.PublicationPage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        pubs = (
            PublicationPage.objects.child_of(self)
            .live()
            .order_by("-year", "title")
        )
        query = request.GET.get("q", "").strip()
        if query:
            pubs = pubs.search(query)
        year = request.GET.get("year")
        if year and year.isdigit():
            pubs = pubs.filter(year=int(year))
        pub_type = request.GET.get("type")
        if pub_type:
            pubs = pubs.filter(pub_type=pub_type)
        context["publications"] = pubs
        context["query"] = query
        context["years"] = (
            PublicationPage.objects.child_of(self)
            .live()
            .exclude(year__isnull=True)
            .values_list("year", flat=True)
            .order_by("-year")
            .distinct()
        )
        context["pub_types"] = (
            PublicationPage.objects.child_of(self)
            .live()
            .exclude(pub_type="")
            .values_list("pub_type", flat=True)
            .order_by("pub_type")
            .distinct()
        )
        return context

    class Meta:
        verbose_name = "Publications Index"


class PublicationPage(Page):
    pub_type = models.CharField(
        max_length=100,
        blank=True,
        choices=[
            ("book", "Book"),
            ("catalogue", "Exhibition catalogue"),
            ("zine", "Zine / artist book"),
            ("journal", "Journal / magazine"),
            ("report", "Report"),
            ("online", "Online publication"),
            ("other", "Other"),
        ],
        default="",
        verbose_name="Type",
    )
    year = models.IntegerField(null=True, blank=True)
    authors = models.CharField(max_length=500, blank=True, help_text="Comma-separated list of authors/editors")
    isbn = models.CharField(max_length=50, blank=True, verbose_name="ISBN")
    cover_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        verbose_name="Cover image",
    )
    intro = models.TextField(blank=True, max_length=500)
    body = StreamField(
        [
            ("paragraph", RichTextBlock(features=["h2","h3","bold","italic","ol","ul","hr","link","document-link","blockquote"])),
            ("image", ImageChooserBlock()),
        ],
        use_json_field=True,
        blank=True,
    )
    # Purchase / download
    price = models.CharField(max_length=100, blank=True, help_text="e.g. '€18', 'Free', 'Out of print'")
    buy_url = models.URLField(blank=True, help_text="External purchase URL (e.g. bookshop, publisher)")
    pdf_download = models.ForeignKey(
        "wagtaildocs.Document",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        help_text="Downloadable PDF if available openly",
    )
    publisher = models.CharField(max_length=255, blank=True)

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("authors"),
        index.SearchField("body"),
        index.FilterField("year"),
        index.FilterField("pub_type"),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("pub_type"),
            FieldPanel("year"),
            FieldPanel("authors"),
            FieldPanel("isbn"),
            FieldPanel("publisher"),
        ], heading="Publication details"),
        FieldPanel("intro"),
        FieldPanel("cover_image"),
        FieldPanel("body"),
        MultiFieldPanel([
            FieldPanel("price"),
            FieldPanel("buy_url"),
            FieldPanel("pdf_download"),
        ], heading="Purchase / download"),
    ]

    parent_page_types = ["publications.PublicationsIndexPage"]

    class Meta:
        verbose_name = "Publication"
