from django.db import models
from django.utils.translation import gettext_lazy as _

from modelcluster.fields import ParentalKey, ParentalManyToManyField
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase

from wagtail.models import Page, Orderable
from wagtail.fields import StreamField
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.blocks import (
    CharBlock, RichTextBlock,
    StructBlock, TextBlock, URLBlock,
)
from wagtail.images.blocks import ImageChooserBlock
from wagtail.search import index
from wagtail.snippets.models import register_snippet


class BlogPostTag(TaggedItemBase):
    content_object = ParentalKey(
        "BlogPostPage", related_name="tagged_items", on_delete=models.CASCADE
    )


@register_snippet
class BlogCategory(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    panels = [FieldPanel("name"), FieldPanel("slug")]

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Blog categories"


class BlogIndexPage(Page):
    intro = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    subpage_types = ["blog.BlogPostPage"]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        posts = (
            BlogPostPage.objects.child_of(self)
            .live()
            .order_by("-first_published_at")
        )
        # Full-text search
        query = request.GET.get("q", "").strip()
        if query:
            posts = posts.search(query)
        # Category filter
        category = request.GET.get("category")
        if category:
            posts = posts.filter(categories__slug=category)
        # Tag filter
        tag = request.GET.get("tag")
        if tag:
            posts = posts.filter(tags__slug=tag)
        # Year filter
        year = request.GET.get("year")
        if year and year.isdigit():
            posts = posts.filter(date__year=int(year))
        # Language filter
        lang = request.GET.get("lang")
        if lang in ("en", "lt"):
            posts = posts.filter(language=lang)
        context["posts"] = posts
        context["query"] = query
        context["categories"] = BlogCategory.objects.all()
        context["years"] = (
            BlogPostPage.objects.child_of(self)
            .live()
            .exclude(date__isnull=True)
            .dates("date", "year", order="DESC")
        )
        # Tag cloud: tags used on live posts under this index
        from taggit.models import Tag
        context["tags"] = (
            Tag.objects.filter(
                blog_blogposttag_items__content_object__in=(
                    BlogPostPage.objects.child_of(self).live()
                )
            )
            .distinct()
            .order_by("name")
        )
        return context

    class Meta:
        verbose_name = "Blog Index"


class BlogPostPage(Page):
    date = models.DateField("Post date", null=True, blank=True)
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
            ("quote", StructBlock([
                ("text", TextBlock()),
                ("attribution", CharBlock(required=False)),
            ])),
        ],
        use_json_field=True,
        blank=True,
    )
    tags = ClusterTaggableManager(through=BlogPostTag, blank=True)
    categories = ParentalManyToManyField("blog.BlogCategory", blank=True)
    # WordPress import metadata
    wp_post_id = models.IntegerField(null=True, blank=True, db_index=True)
    language = models.CharField(max_length=5, default="en", choices=[("en", "English"), ("lt", "Lietuvių")])

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("date"),
            FieldPanel("tags"),
            FieldPanel("categories"),
            FieldPanel("language"),
        ], heading="Metadata"),
        FieldPanel("intro"),
        FieldPanel("featured_image"),
        FieldPanel("body"),
    ]

    parent_page_types = ["blog.BlogIndexPage"]

    class Meta:
        verbose_name = "Blog Post"
