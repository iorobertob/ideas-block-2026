from django.urls import path
from . import views

urlpatterns = [
    path("files/download/<int:download_id>/", views.project_download, name="project_download"),
]
