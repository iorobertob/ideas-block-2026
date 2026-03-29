from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.template.response import TemplateResponse

from wagtail.models import Page


def search(request):
    search_query = request.GET.get("query", "").strip()
    page_num = request.GET.get("page", 1)
    filter_type = request.GET.get("type", "all")

    results = Page.objects.none()
    total_count = 0

    if search_query:
        base_qs = Page.objects.live().search(search_query)

        # Type-filtered counts for UI badges
        from blog.models import BlogPostPage
        from events.models import EventPage
        from projects.models import ProjectPage
        from people.models import PersonPage

        counts = {}
        for label, model in [
            ("blog", BlogPostPage),
            ("events", EventPage),
            ("projects", ProjectPage),
            ("people", PersonPage),
        ]:
            counts[label] = (
                model.objects.live()
                .search(search_query)
                .count()
            )
        counts["all"] = sum(counts.values())

        # Apply type filter
        if filter_type == "blog":
            results = BlogPostPage.objects.live().search(search_query)
        elif filter_type == "events":
            results = EventPage.objects.live().search(search_query)
        elif filter_type == "projects":
            results = ProjectPage.objects.live().search(search_query)
        elif filter_type == "people":
            results = PersonPage.objects.live().search(search_query)
        else:
            results = base_qs
            filter_type = "all"
    else:
        counts = {"all": 0, "blog": 0, "events": 0, "projects": 0, "people": 0}

    paginator = Paginator(results, 12)
    try:
        search_results = paginator.page(page_num)
    except PageNotAnInteger:
        search_results = paginator.page(1)
    except EmptyPage:
        search_results = paginator.page(paginator.num_pages)

    return TemplateResponse(
        request,
        "search/search.html",
        {
            "search_query": search_query,
            "search_results": search_results,
            "counts": counts,
            "filter_type": filter_type,
        },
    )
