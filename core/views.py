import json
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt


@require_POST
def newsletter_signup(request):
    email = request.POST.get("email", "").strip()
    if not email or "@" not in email:
        return JsonResponse({"ok": False, "error": "Invalid email address."}, status=400)

    api_key = getattr(settings, "MAILERLITE_API_KEY", "")
    if not api_key:
        # Dev fallback: just acknowledge without calling the API
        return JsonResponse({"ok": True, "message": "Thanks! (MailerLite not configured in dev)"})

    try:
        resp = requests.post(
            "https://connect.mailerlite.com/api/subscribers",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            data=json.dumps({"email": email}),
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return JsonResponse({"ok": True, "message": "You're subscribed. Thank you!"})
        if resp.status_code == 422:
            return JsonResponse({"ok": True, "message": "You're already subscribed."})
        return JsonResponse({"ok": False, "error": "Subscription failed. Please try again."}, status=502)
    except requests.RequestException:
        return JsonResponse({"ok": False, "error": "Connection error. Please try again."}, status=503)
