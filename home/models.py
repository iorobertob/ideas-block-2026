from django.db import models

from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.blocks import CharBlock, RichTextBlock, URLBlock, StructBlock
from wagtail.images.blocks import ImageChooserBlock


class HomePage(Page):
    # Hero
    hero_tagline = models.CharField(
        max_length=255,
        blank=True,
        default="Ideas Block",
    )
    hero_subtitle = models.TextField(
        blank=True,
        default="Cultural organisation — Vilnius",
    )
    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    hero_cta_text = models.CharField(max_length=100, blank=True, default="See our work")
    hero_cta_url = models.CharField(max_length=255, blank=True, default="/projects/")

    # About snippet on homepage
    about_text = RichTextField(blank=True)

    # Featured content (manual picks)
    featured_items = StreamField(
        [
            ("featured_page", StructBlock([
                ("page_title", CharBlock()),
                ("description", CharBlock(required=False)),
                ("image", ImageChooserBlock(required=False)),
                ("url", URLBlock()),
            ])),
        ],
        use_json_field=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("hero_tagline"),
            FieldPanel("hero_subtitle"),
            FieldPanel("hero_image"),
            FieldPanel("hero_cta_text"),
            FieldPanel("hero_cta_url"),
        ], heading="Hero"),
        FieldPanel("about_text"),
        FieldPanel("featured_items"),
    ]

    def get_context(self, request, *args, **kwargs):
        import random as _random
        from blog.models import BlogPostPage
        from events.models import EventPage
        from wagtail.images import get_image_model
        context = super().get_context(request, *args, **kwargs)
        context["latest_posts"] = (
            BlogPostPage.objects.live().order_by("-first_published_at")[:3]
        )
        from django.utils import timezone
        today = timezone.now().date()
        context["upcoming_events"] = (
            EventPage.objects.live()
            .filter(start_date__gte=today)
            .order_by("start_date")[:4]
        )
        context["past_events"] = (
            EventPage.objects.live()
            .filter(start_date__lt=today)
            .order_by("-start_date")[:4]
        )
        # Random hero background image (only used when page.hero_image is not set)
        if not self.hero_image:
            Image = get_image_model()
            candidate_ids = list(
                BlogPostPage.objects.live()
                .filter(featured_image__isnull=False)
                .values_list("featured_image_id", flat=True)[:40]
            )
            if candidate_ids:
                context["hero_bg_image"] = Image.objects.filter(
                    pk=_random.choice(candidate_ids)
                ).first()
        return context

    class Meta:
        verbose_name = "Home Page"
