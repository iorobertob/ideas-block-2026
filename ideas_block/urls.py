from django.conf import settings
from django.urls import include, path, re_path
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from .api import api_router

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from search import views as search_views

from tickets import urls as tickets_urls
from core import urls as core_urls
from members import urls as members_urls
from projects import urls as projects_urls
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
    path("members/", include(members_urls)),
    path("", include(projects_urls)),
    # Language switcher — POST to /i18n/set_language/ with next + language
    path("i18n/", include("django.conf.urls.i18n")),
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


from django.views.static import serve as _serve_static
urlpatterns += [
    re_path(r'^media/(?P<path>.+)$', _serve_static, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    from django.shortcuts import render as _render

    urlpatterns += staticfiles_urlpatterns()
    # Preview custom error pages in dev
    urlpatterns += [
        path("__404__/", lambda r: _render(r, "404.html", status=404)),
        path("__500__/", lambda r: _render(r, "500.html", status=500)),
    ]

urlpatterns = urlpatterns + i18n_patterns(
    # Wagtail page serving with optional locale prefix (/lt/..., /en/..., or /)
    path("", include(wagtail_urls)),
    prefix_default_language=False,  # /en/ prefix NOT required for default language
)
