from django.urls import path
from . import views

urlpatterns = [
    path("checkout/<int:page_id>/", views.checkout, name="ticket_checkout"),
    path("checkout/<int:page_id>/session/", views.create_checkout_session, name="ticket_session"),
    path("register/<int:page_id>/", views.free_registration, name="ticket_register"),
    path("success/<uuid:order_id>/", views.checkout_success, name="ticket_success"),
    path("webhook/stripe/", views.stripe_webhook, name="stripe_webhook"),
    path("scanner/", views.scanner, name="ticket_scanner"),
    path("verify/", views.verify_ticket, name="ticket_verify"),
    path("courtesy/", views.courtesy_ticket, name="ticket_courtesy"),
    path("attendees/<int:page_id>/", views.event_attendees, name="ticket_attendees"),
    path("support/", views.support, name="support"),
    path("support/subscribe/", views.create_subscription, name="create_subscription"),
    path("support/thanks/", views.support_thanks, name="support_thanks"),
]
