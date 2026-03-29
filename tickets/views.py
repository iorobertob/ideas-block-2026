"""
Ticket purchase, Stripe checkout, webhook, and QR scanner views.
"""

import json
import uuid
import logging

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required

from .models import Order, Ticket

logger = logging.getLogger(__name__)


# ── Checkout ──────────────────────────────────────────────────────────────────

def checkout(request, page_id: int):
    """
    Show checkout form for a ProductPage or EventPage.
    page_id = Wagtail page PK
    """
    from wagtail.models import Page
    page = get_object_or_404(Page, pk=page_id).specific
    price = getattr(page, "price", None)
    price_display = getattr(page, "price_display", "")
    is_free = getattr(page, "is_free", False) if hasattr(page, "is_free") else (price is None or price == 0)

    context = {
        "product_page": page,
        "price": price,
        "price_display": price_display,
        "is_free": is_free,
        "stripe_publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
    }
    return render(request, "tickets/checkout.html", context)


@require_POST
def create_checkout_session(request, page_id: int):
    """Create a Stripe Checkout session and redirect."""
    import stripe

    stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        return JsonResponse({"error": "Payment not configured."}, status=503)

    from wagtail.models import Page
    page = get_object_or_404(Page, pk=page_id).specific
    price = getattr(page, "price", None)
    quantity = max(1, min(int(request.POST.get("quantity", 1)), 20))
    buyer_name = request.POST.get("name", "")
    buyer_email = request.POST.get("email", "")

    if not buyer_email:
        return redirect(f"/tickets/checkout/{page_id}/")

    unit_amount = int((price or 0) * 100)  # cents

    # Create pending order
    order = Order.objects.create(
        product_page_id=page_id,
        product_title=page.title,
        product_sku=getattr(page, "sku", str(page_id)),
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        quantity=quantity,
        unit_price=price or 0,
    )

    base_url = request.build_absolute_uri("/")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "product_data": {"name": page.title},
                    "unit_amount": unit_amount,
                },
                "quantity": quantity,
            }],
            mode="payment",
            customer_email=buyer_email,
            metadata={"order_id": str(order.id)},
            success_url=f"{base_url}tickets/success/{order.id}/",
            cancel_url=f"{base_url}tickets/checkout/{page_id}/",
        )
        order.stripe_session_id = session.id
        order.save(update_fields=["stripe_session_id"])
        return redirect(session.url, permanent=False)
    except stripe.error.StripeError as e:
        logger.error("Stripe error: %s", e)
        order.status = Order.STATUS_FAILED
        order.save(update_fields=["status"])
        return render(request, "tickets/checkout.html", {
            "product_page": page,
            "price": price,
            "error": "Payment failed. Please try again.",
            "stripe_publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
        })


def checkout_success(request, order_id):
    """Success page after payment — shows QR tickets."""
    order = get_object_or_404(Order, pk=order_id)
    return render(request, "tickets/success.html", {"order": order})


# ── Stripe Webhook ────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def stripe_webhook(request):
    import stripe
    stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")
        if order_id:
            try:
                order = Order.objects.get(pk=order_id)
                order.stripe_payment_intent = session.get("payment_intent", "")
                order.mark_paid()  # generates tickets + QR codes
                _send_ticket_email(order)
            except Order.DoesNotExist:
                logger.warning("Webhook: order %s not found", order_id)

    return HttpResponse(status=200)


def _send_ticket_email(order: Order):
    from django.core.mail import EmailMessage
    from django.template.loader import render_to_string
    try:
        body = render_to_string("tickets/email_ticket.html", {"order": order})
        email = EmailMessage(
            subject=f"Your ticket: {order.product_title}",
            body=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@ideas-block.com"),
            to=[order.buyer_email],
        )
        email.content_subtype = "html"
        for ticket in order.tickets.all():
            if ticket.qr_code:
                email.attach_file(ticket.qr_code.path)
        email.send()
    except Exception as e:
        logger.error("Failed to send ticket email: %s", e)


# ── QR Scanner ───────────────────────────────────────────────────────────────

@staff_member_required
def scanner(request):
    """QR scanner UI for staff."""
    from products.models import ProductPage
    products = ProductPage.objects.live().filter(is_available=True)
    return render(request, "tickets/scanner.html", {"products": products})


def verify_ticket(request):
    """
    POST /tickets/verify/
    Body: {qr_data: "ticket_uuid|order_uuid|sku", sku: "optional-filter"}
    Returns JSON {ok, message}
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "POST required"}, status=405)
    if not (request.user.is_staff or request.user.groups.filter(name="Ticket Scanner").exists()):
        return JsonResponse({"ok": False, "message": "Unauthorized"}, status=403)

    try:
        data = json.loads(request.body)
        qr_data = data.get("qr_data", "")
        sku_filter = data.get("sku", "")
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"ok": False, "message": "Invalid request"}, status=400)

    parts = qr_data.split("|")
    if not parts:
        return JsonResponse({"ok": False, "message": "Invalid QR data"})

    ticket_id = parts[0]
    try:
        ticket = Ticket.objects.select_related("order").get(pk=ticket_id)
    except (Ticket.DoesNotExist, ValueError):
        return JsonResponse({"ok": False, "message": "Ticket not found"})

    result = ticket.verify(sku=sku_filter or None)
    return JsonResponse({"ok": result["ok"], "message": result["message"]})


# ── Subscription ─────────────────────────────────────────────────────────────

def support(request):
    """Support/subscription page."""
    from .models import Subscription
    context = {
        "plans": Subscription.PLAN_CHOICES,
        "stripe_publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
    }
    return render(request, "tickets/support.html", context)


@require_POST
def create_subscription(request):
    """Create Stripe subscription checkout."""
    import stripe
    stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        return JsonResponse({"error": "Payment not configured."}, status=503)

    plan = request.POST.get("plan", "supporter")
    email = request.POST.get("email", "")

    # Price IDs should be set in settings or .env
    price_ids = {
        "supporter": getattr(settings, "STRIPE_PRICE_SUPPORTER", ""),
        "patron": getattr(settings, "STRIPE_PRICE_PATRON", ""),
    }
    price_id = price_ids.get(plan, "")
    if not price_id:
        return JsonResponse({"error": "Plan not configured."}, status=503)

    base_url = request.build_absolute_uri("/")
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=email or None,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{base_url}tickets/support/thanks/",
            cancel_url=f"{base_url}tickets/support/",
            metadata={"plan": plan},
        )
        return redirect(session.url, permanent=False)
    except stripe.error.StripeError as e:
        return render(request, "tickets/support.html", {
            "error": str(e),
            "plans": __import__("tickets.models", fromlist=["Subscription"]).Subscription.PLAN_CHOICES,
        })


def support_thanks(request):
    return render(request, "tickets/support_thanks.html")
