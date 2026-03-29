from django.conf import settings
from django.urls import include, path
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from .api import api_router

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from search import views as search_views

from tickets import urls as tickets_urls
from core import urls as core_urls
from blog.feeds import LatestBlogFeed, LatestBlogAtomFeed
from events.feeds import UpcomingEventsFeed, UpcomingEventsAtomFeed
from django.contrib.sitemaps.views import sitemap
from wagtail.contrib.sitemaps import Sitemap as WagtailSitemap

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    path("tickets/", include(tickets_urls)),
    path("core/", include(core_urls)),
    # Sitemap
    path("sitemap.xml", sitemap, {"sitemaps": {"wagtail": WagtailSitemap}}, name="sitemap"),
    # Wagtail headless API
    path("api/v2/", api_router.urls),
    # RSS / Atom feeds
    path("blog/feed/", LatestBlogFeed(), name="blog_feed"),
    path("blog/feed/atom/", LatestBlogAtomFeed(), name="blog_feed_atom"),
    path("events/feed/", UpcomingEventsFeed(), name="events_feed"),
    path("events/feed/atom/", UpcomingEventsAtomFeed(), name="events_feed_atom"),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + i18n_patterns(
    # Wagtail page serving with optional locale prefix (/lt/..., /en/..., or /)
    path("", include(wagtail_urls)),
)
