from django.conf import settings


def analytics(request):
    return {
        "PLAUSIBLE_DOMAIN": getattr(settings, "PLAUSIBLE_DOMAIN", ""),
    }
