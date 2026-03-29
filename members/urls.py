from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.member_login, name="member_login"),
    path("register/", views.member_register, name="member_register"),
    path("dashboard/", views.member_dashboard, name="member_dashboard"),
    path("logout/", views.member_logout, name="member_logout"),
]
