from django.db import models

from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.blocks import CharBlock, RichTextBlock, StructBlock, TextBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.search import index


class ProjectsIndexPage(Page):
    intro = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["projects.ProjectPage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        projects = ProjectPage.objects.child_of(self).live().order_by("-year", "-first_published_at")
        # Full-text search
        query = request.GET.get("q", "").strip()
        if query:
            projects = projects.search(query)
        # Year filter
        year = request.GET.get("year")
        if year and year.isdigit():
            projects = projects.filter(year=int(year))
        context["projects"] = projects
        context["query"] = query
        context["years"] = (
            ProjectPage.objects.child_of(self)
            .live()
            .exclude(year__isnull=True)
            .order_by("-year")
            .values_list("year", flat=True)
            .distinct()
        )
        return context

    class Meta:
        verbose_name = "Projects Index"


class ProjectPage(Page):
    year = models.IntegerField(null=True, blank=True)
    subtitle = models.CharField(max_length=255, blank=True)
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
            ("image_caption", StructBlock([
                ("image", ImageChooserBlock()),
                ("caption", TextBlock(required=False)),
            ])),
        ],
        use_json_field=True,
        blank=True,
    )
    collaborators = models.TextField(blank=True)
    # WordPress import metadata
    wp_post_id = models.IntegerField(null=True, blank=True, db_index=True)

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
        index.SearchField("collaborators"),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("year"),
            FieldPanel("subtitle"),
            FieldPanel("collaborators"),
        ], heading="Project info"),
        FieldPanel("intro"),
        FieldPanel("featured_image"),
        FieldPanel("body"),
    ]

    parent_page_types = ["projects.ProjectsIndexPage"]

    class Meta:
        verbose_name = "Project"
