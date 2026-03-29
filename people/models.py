from django.db import models

from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel


class PeoplePage(Page):
    intro = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["people.PersonPage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["people"] = PersonPage.objects.child_of(self).live().order_by("title")
        return context

    class Meta:
        verbose_name = "People Index"


class PersonPage(Page):
    role = models.CharField(max_length=255, blank=True)
    bio = RichTextField(blank=True)
    photo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    instagram = models.CharField(
        max_length=100,
        blank=True,
        help_text="Instagram handle without @, e.g. ideasblock.lt",
    )

    content_panels = Page.content_panels + [
        FieldPanel("role"),
        FieldPanel("photo"),
        FieldPanel("bio"),
        MultiFieldPanel([
            FieldPanel("email"),
            FieldPanel("website"),
            FieldPanel("instagram"),
        ], heading="Contact & Social"),
    ]

    parent_page_types = ["people.PeoplePage"]

    def get_context(self, request, *args, **kwargs):
        from blog.models import BlogPostPage
        from events.models import EventPage
        context = super().get_context(request, *args, **kwargs)
        # Related blog posts: posts whose title or intro mentions this person's name
        # Simple approach: show latest N posts from the blog for now
        # Editors can refine this by tagging posts with the person's name
        context["related_posts"] = (
            BlogPostPage.objects.live()
            .order_by("-first_published_at")[:3]
        )
        return context

    class Meta:
        verbose_name = "Person"
