from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect

from members.access import user_can_access
from .models import ProjectDownload


def project_download(request, download_id):
    download = get_object_or_404(ProjectDownload, pk=download_id)

    if not user_can_access(request.user, download.access_level):
        if not request.user.is_authenticated:
            return redirect(f"/members/login/?next=/files/download/{download_id}/")
        # Logged in but insufficient access (needs payer status)
        return HttpResponse(
            '<html><body style="font-family:sans-serif;padding:2rem;">'
            '<h2>Access restricted</h2>'
            '<p>This file is available to Supporters and Patrons.</p>'
            '<a href="/tickets/support/">Become a supporter →</a>'
            '</body></html>',
            status=403,
            content_type="text/html",
        )

    doc = download.file
    try:
        return FileResponse(doc.file.open("rb"), as_attachment=True, filename=doc.filename)
    except Exception:
        raise Http404
