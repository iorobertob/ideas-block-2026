from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from .models import BlogPostPage


class LatestBlogFeed(Feed):
    title = "Ideas Block — Blog"
    link = "/blog/"
    description = "Latest posts from Ideas Block, Vilnius"

    def items(self):
        return (
            BlogPostPage.objects.live()
            .order_by("-first_published_at")[:20]
        )

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.intro or ""

    def item_pubdate(self, item):
        return item.first_published_at

    def item_link(self, item):
        return item.full_url or item.get_url()


class LatestBlogAtomFeed(LatestBlogFeed):
    feed_type = Atom1Feed
    subtitle = LatestBlogFeed.description
