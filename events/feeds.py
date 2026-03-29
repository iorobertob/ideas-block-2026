from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from .models import EventPage


class UpcomingEventsFeed(Feed):
    title = "Ideas Block — Upcoming Events"
    link = "/events/"
    description = "Upcoming events from Ideas Block, Vilnius"

    def items(self):
        from django.utils import timezone
        return (
            EventPage.objects.live()
            .filter(start_date__gte=timezone.now().date())
            .order_by("start_date")[:20]
        )

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        parts = []
        if item.start_date:
            parts.append(str(item.start_date))
        if item.location:
            parts.append(item.location)
        if item.intro:
            parts.append(item.intro)
        return " · ".join(parts)

    def item_pubdate(self, item):
        return item.first_published_at

    def item_link(self, item):
        return item.full_url or item.get_url()


class UpcomingEventsAtomFeed(UpcomingEventsFeed):
    feed_type = Atom1Feed
    subtitle = UpcomingEventsFeed.description
