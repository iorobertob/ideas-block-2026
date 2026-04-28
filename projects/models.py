from django.db import models

from modelcluster.fields import ParentalKey
from wagtail.models import Page, Orderable
from wagtail.fields import StreamField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel, PageChooserPanel
from wagtail.blocks import CharBlock, RichTextBlock, StructBlock, TextBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.search import index


class ProjectDownload(Orderable):
    """A downloadable file attached to a project, with access control."""

    ACCESS_CHOICES = [
        ("public", "Public — anyone can download"),
        ("members", "Members — registered accounts only"),
        ("payers", "Payers — active subscribers or ticket buyers only"),
    ]

    page = ParentalKey("ProjectPage", on_delete=models.CASCADE, related_name="downloads")
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True)
    file = models.ForeignKey(
        "wagtaildocs.Document",
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name="File",
    )
    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_CHOICES,
        default="public",
    )

    panels = [
        FieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("file"),
        FieldPanel("access_level"),
    ]


class ProjectsIndexPage(Page):
    intro = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["projects.ProjectPage", "projects.VerbalImagesPage"]

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
        # Type filter
        project_type = request.GET.get("type")
        if project_type:
            projects = projects.filter(project_type=project_type)
        context["projects"] = projects
        context["verbal_image_pages"] = VerbalImagesPage.objects.child_of(self).live()
        context["query"] = query
        context["years"] = (
            ProjectPage.objects.child_of(self)
            .live()
            .exclude(year__isnull=True)
            .order_by("-year")
            .values_list("year", flat=True)
            .distinct()
        )
        context["project_types"] = (
            ProjectPage.objects.child_of(self)
            .live()
            .exclude(project_type="")
            .values_list("project_type", flat=True)
            .order_by("project_type")
            .distinct()
        )
        return context

    class Meta:
        verbose_name = "Projects Index"


class ProjectParticipant(Orderable):
    page = ParentalKey("ProjectPage", on_delete=models.CASCADE, related_name="participants")
    person = models.ForeignKey(
        "people.PersonPage",
        on_delete=models.CASCADE,
        related_name="+",
    )

    panels = [PageChooserPanel("person", page_type="people.PersonPage")]


class ProjectPage(Page):
    STATUS_CHOICES = [
        ("in_progress", "In progress"),
        ("completed", "Completed"),
        ("ongoing", "Ongoing"),
        ("archived", "Archived"),
    ]
    TYPE_CHOICES = [
        ("exhibition", "Exhibition"),
        ("residency", "Residency"),
        ("community", "Community"),
        ("digital", "Digital"),
        ("research", "Research"),
        ("publication", "Publication"),
        ("performance", "Performance"),
        ("other", "Other"),
    ]

    year = models.IntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank if ongoing.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, default="")
    project_type = models.CharField(max_length=50, choices=TYPE_CHOICES, blank=True, default="")
    subtitle = models.CharField(max_length=255, blank=True)
    intro = models.TextField(blank=True, max_length=500)
    featured_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    external_url = models.URLField(blank=True, help_text="Project website or documentation link.")
    gallery = StreamField(
        [
            ("image", StructBlock([
                ("image", ImageChooserBlock()),
                ("caption", CharBlock(required=False)),
            ], label="Gallery image")),
        ],
        use_json_field=True,
        blank=True,
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
    collaborators = models.TextField(blank=True, help_text="Free-text list for external collaborators not in the People section.")
    related_posts_filter = models.CharField(
        max_length=200, blank=True,
        help_text="Title prefix to auto-pull related blog posts, e.g. 'COVID-19 CREATIVE OUTLET'.",
    )
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
            FieldPanel("start_date"),
            FieldPanel("end_date"),
            FieldPanel("status"),
            FieldPanel("project_type"),
            FieldPanel("subtitle"),
            FieldPanel("external_url"),
        ], heading="Project info"),
        FieldPanel("intro"),
        FieldPanel("featured_image"),
        InlinePanel("participants", heading="Participants", label="Person"),
        FieldPanel("collaborators"),
        FieldPanel("related_posts_filter"),
        FieldPanel("gallery"),
        FieldPanel("body"),
        InlinePanel("downloads", heading="Downloads", label="File"),
    ]

    parent_page_types = ["projects.ProjectsIndexPage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        if self.related_posts_filter:
            from blog.models import BlogPostPage
            context["related_posts"] = (
                BlogPostPage.objects.live()
                .filter(title__icontains=self.related_posts_filter)
                .order_by("date")
            )
        return context

    class Meta:
        verbose_name = "Project"


class VerbalImagesPage(Page):
    """Verbal Images in Literature Database — project page with tabbed interface."""

    year = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=ProjectPage.STATUS_CHOICES, blank=True, default="ongoing"
    )
    project_type = models.CharField(
        max_length=50, choices=ProjectPage.TYPE_CHOICES, blank=True, default="research"
    )
    intro = models.TextField(blank=True, max_length=500)
    featured_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("year"), FieldPanel("status"), FieldPanel("project_type")],
            heading="Project info",
        ),
        FieldPanel("intro"),
        FieldPanel("featured_image"),
    ]

    parent_page_types = ["projects.ProjectsIndexPage"]
    subpage_types = []

    def get_context(self, request, *args, **kwargs):
        import csv
        import os

        from django.conf import settings

        context = super().get_context(request, *args, **kwargs)
        csv_path = os.path.join(settings.BASE_DIR, "data", "verbalimages", "database.csv")
        headers, rows = [], []
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=";")
                headers = next(reader)
                rows = list(reader)
        except (FileNotFoundError, StopIteration):
            pass
        context["csv_headers"] = headers
        context["csv_rows"] = rows
        context["active_tab"] = request.GET.get("tab", "database")
        return context

    class Meta:
        verbose_name = "Verbal Images Database"
