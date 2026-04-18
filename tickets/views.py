"""
Ticket purchase, Stripe checkout, webhook, QR scanner, courtesy tickets,
attendee management, and supporter subscription views.
"""

import json
import logging

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required

from .models import Order, Ticket, Subscription

logger = logging.getLogger(__name__)

MEMBER_DISCOUNT_EUR = getattr(settings, "MEMBER_DISCOUNT_EUR", 2.00)
TICKETS_BCC_EMAIL = getattr(settings, "TICKETS_BCC_EMAIL", "contact@ideas-block.com")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_page(page_id):
    from wagtail.models import Page
    return get_object_or_404(Page, pk=page_id).specific


def _page_context(page):
    """Common context values derived from a ProductPage or EventPage."""
    price = getattr(page, "price", None)
    is_free = getattr(page, "is_free", False) if hasattr(page, "is_free") else (price is None or price == 0)
    capacity = getattr(page, "capacity", None)
    spots_remaining = None
    if capacity:
        sold = (
            Order.objects
            .filter(product_page_id=page.pk, status__in=Order.CONFIRMED_STATUSES)
            .aggregate(total=Sum("quantity"))["total"] or 0
        )
        spots_remaining = max(0, capacity - sold)
    return {
        "product_page": page,
        "price": price,
        "price_display": getattr(page, "price_display", ""),
        "is_free": is_free,
        "capacity": capacity,
        "spots_remaining": spots_remaining,
        "stripe_publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
    }


def _is_payer(user):
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    try:
        return user.member_profile.is_payer
    except Exception:
        return False


# ── Checkout ──────────────────────────────────────────────────────────────────

def checkout(request, page_id: int):
    """Show checkout/registration form for a ProductPage or EventPage."""
    page = _get_page(page_id)
    ctx = _page_context(page)
    if ctx["spots_remaining"] == 0:
        ctx["sold_out"] = True
    if _is_payer(request.user) and ctx["price"]:
        ctx["member_discount"] = MEMBER_DISCOUNT_EUR
        ctx["discounted_price"] = max(0, float(ctx["price"]) - MEMBER_DISCOUNT_EUR)
    return render(request, "tickets/checkout.html", ctx)


@require_POST
def free_registration(request, page_id: int):
    """Handle free event registration without Stripe."""
    page = _get_page(page_id)
    buyer_name = request.POST.get("name", "").strip()
    buyer_email = request.POST.get("email", "").strip()
    buyer_phone = request.POST.get("phone", "").strip()
    quantity = max(1, min(int(request.POST.get("quantity", 1) or 1), 20))

    if not buyer_name or not buyer_email:
        ctx = _page_context(page)
        ctx["error"] = "Name and email are required."
        return render(request, "tickets/checkout.html", ctx)

    # Capacity check
    capacity = getattr(page, "capacity", None)
    if capacity:
        sold = (
            Order.objects
            .filter(product_page_id=page_id, status__in=Order.CONFIRMED_STATUSES)
            .aggregate(total=Sum("quantity"))["total"] or 0
        )
        if sold + quantity > capacity:
            ctx = _page_context(page)
            ctx["error"] = f"Sorry, only {max(0, capacity - sold)} spot(s) remaining."
            return render(request, "tickets/checkout.html", ctx)

    order = Order.objects.create(
        product_page_id=page_id,
        product_title=page.title,
        product_sku=getattr(page, "sku", str(page_id)),
        user=request.user if request.user.is_authenticated else None,
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        buyer_phone=buyer_phone,
        quantity=quantity,
        unit_price=0,
        status=Order.STATUS_REGISTERED,
    )
    order.paid_at = timezone.now()
    order.save(update_fields=["paid_at"])
    order._generate_tickets()
    _send_ticket_email(order)
    return redirect("ticket_success", order_id=order.id)


@require_POST
def create_checkout_session(request, page_id: int):
    """Create a Stripe Checkout session and redirect."""
    import stripe

    stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        return JsonResponse({"error": "Payment not configured."}, status=503)

    page = _get_page(page_id)
    price = getattr(page, "price", None)
    quantity = max(1, min(int(request.POST.get("quantity", 1) or 1), 20))
    buyer_name = request.POST.get("name", "").strip()
    buyer_email = request.POST.get("email", "").strip()
    buyer_phone = request.POST.get("phone", "").strip()

    if not buyer_email:
        return redirect(f"/tickets/checkout/{page_id}/")

    # Capacity check
    capacity = getattr(page, "capacity", None)
    if capacity:
        sold = (
            Order.objects
            .filter(product_page_id=page_id, status__in=Order.CONFIRMED_STATUSES)
            .aggregate(total=Sum("quantity"))["total"] or 0
        )
        if sold + quantity > capacity:
            ctx = _page_context(page)
            ctx["error"] = f"Sorry, only {max(0, capacity - sold)} spot(s) remaining."
            return render(request, "tickets/checkout.html", ctx)

    # Member discount
    unit_price = float(price or 0)
    discount = 0.0
    if _is_payer(request.user) and unit_price > 0:
        discount = min(MEMBER_DISCOUNT_EUR, unit_price)
        unit_price = max(0, unit_price - discount)

    unit_amount = int(unit_price * 100)  # Stripe expects cents

    order = Order.objects.create(
        product_page_id=page_id,
        product_title=page.title,
        product_sku=getattr(page, "sku", str(page_id)),
        user=request.user if request.user.is_authenticated else None,
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        buyer_phone=buyer_phone,
        quantity=quantity,
        unit_price=price or 0,
        discount_amount=discount * quantity,
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
        ctx = _page_context(page)
        ctx["error"] = "Payment failed. Please try again."
        return render(request, "tickets/checkout.html", ctx)


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

    if not webhook_secret:
        logger.warning("STRIPE_WEBHOOK_SECRET not set — rejecting unsigned webhook")
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    event_type = event["type"]

    # ── One-time checkout ──────────────────────────────────────────────────
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")
        if order_id:
            try:
                order = Order.objects.get(pk=order_id)
                order.stripe_payment_intent = session.get("payment_intent", "")
                order.save(update_fields=["stripe_payment_intent"])
                order.mark_paid()
                _send_ticket_email(order)
            except Order.DoesNotExist:
                logger.warning("Webhook: order %s not found", order_id)

    # ── Subscription lifecycle ─────────────────────────────────────────────
    elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
        sub_data = event["data"]["object"]
        stripe_sub_id = sub_data.get("id", "")
        stripe_status = sub_data.get("status", "")
        is_active = stripe_status == "active"
        plan_id = None
        try:
            plan_id = sub_data["items"]["data"][0]["price"]["id"]
        except (KeyError, IndexError):
            pass
        _sync_subscription(stripe_sub_id, is_active, plan_id, sub_data.get("customer_email") or sub_data.get("customer"))

    elif event_type == "customer.subscription.deleted":
        stripe_sub_id = event["data"]["object"].get("id", "")
        try:
            Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).update(active=False)
        except Exception as e:
            logger.error("Subscription delete sync error: %s", e)

    elif event_type == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        stripe_sub_id = invoice.get("subscription", "")
        if stripe_sub_id:
            try:
                Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).update(active=True)
            except Exception as e:
                logger.error("Invoice payment sync error: %s", e)

    elif event_type == "invoice.payment_failed":
        invoice = event["data"]["object"]
        stripe_sub_id = invoice.get("subscription", "")
        if stripe_sub_id:
            try:
                Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).update(active=False)
            except Exception as e:
                logger.error("Invoice failure sync error: %s", e)

    return HttpResponse(status=200)


def _sync_subscription(stripe_sub_id, is_active, price_id, customer_ref):
    """Create or update a Subscription record from Stripe data."""
    import stripe as stripe_lib
    try:
        sub = Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).first()
        if not sub:
            return  # subscription created via create_subscription view; wait for that flow
        sub.active = is_active
        # Update plan if we can match the price ID
        price_to_plan = {
            getattr(settings, "STRIPE_PRICE_SUPPORTER", ""): Subscription.PLAN_SUPPORTER,
            getattr(settings, "STRIPE_PRICE_PATRON", ""): Subscription.PLAN_PATRON,
        }
        if price_id and price_id in price_to_plan:
            sub.plan = price_to_plan[price_id]
        sub.save(update_fields=["active", "plan"])
    except Exception as e:
        logger.error("Subscription sync error: %s", e)


def _send_ticket_email(order: Order):
    from django.core.mail import EmailMessage
    from django.template.loader import render_to_string
    try:
        body = render_to_string("tickets/email_ticket.html", {"order": order})
        bcc = [TICKETS_BCC_EMAIL] if TICKETS_BCC_EMAIL else []
        email = EmailMessage(
            subject=f"Your ticket: {order.product_title}",
            body=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@ideas-block.com"),
            to=[order.buyer_email],
            bcc=bcc,
        )
        email.content_subtype = "html"
        for ticket in order.tickets.all():
            if ticket.qr_code:
                try:
                    email.attach_file(ticket.qr_code.path)
                except Exception as attach_err:
                    logger.warning("Could not attach QR for ticket %s: %s", ticket.id, attach_err)
        email.send()
    except Exception as e:
        logger.error("Failed to send ticket email: %s", e)


# ── QR Scanner ───────────────────────────────────────────────────────────────

@staff_member_required
def scanner(request):
    """QR scanner UI for staff. Shows both events and products with SKUs."""
    from products.models import ProductPage
    from events.models import EventPage

    products = [
        {"title": f"Product: {p.title}", "sku": p.sku}
        for p in ProductPage.objects.live().filter(is_available=True).exclude(sku="")
    ]
    events = [
        {"title": f"Event: {e.title}", "sku": e.sku}
        for e in EventPage.objects.live().exclude(sku="")
    ]
    items = sorted(products + events, key=lambda x: x["title"])
    return render(request, "tickets/scanner.html", {
        "items": items,
        "attendee_url_base": "/tickets/attendees/",
    })


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

    already_used = ticket.used

    # Populate scanned_by before verify() saves
    ticket.scanned_by = request.user.username

    result = ticket.verify(sku=sku_filter or None)
    order = ticket.order
    return JsonResponse({
        "ok": result["ok"],
        "message": result["message"],
        "already_used": already_used,
        "name": order.buyer_name,
        "email": order.buyer_email,
        "event": order.product_title,
        "seat": f"{ticket.seat_number}/{order.quantity}",
        "status": order.get_status_display(),
        "notes": order.notes or "",
    })


# ── Courtesy Tickets ──────────────────────────────────────────────────────────

@staff_member_required
def courtesy_ticket(request):
    """Staff-only: create complimentary tickets without payment."""
    from wagtail.models import Page
    from products.models import ProductPage
    from events.models import EventPage

    # Build list of ticketable pages for the dropdown
    ticketable = list(
        EventPage.objects.live().values("pk", "title")
    ) + list(
        ProductPage.objects.live().filter(is_available=True).values("pk", "title")
    )
    ticketable.sort(key=lambda x: x["title"])

    error = None
    if request.method == "POST":
        page_id = request.POST.get("page_id")
        buyer_name = request.POST.get("name", "").strip()
        buyer_email = request.POST.get("email", "").strip()
        quantity = max(1, min(int(request.POST.get("quantity", 1) or 1), 20))
        notes = request.POST.get("notes", "").strip()

        if not page_id or not buyer_name or not buyer_email:
            error = "Event/product, name, and email are required."
        else:
            page = get_object_or_404(Page, pk=page_id).specific
            order = Order.objects.create(
                product_page_id=page_id,
                product_title=page.title,
                product_sku=getattr(page, "sku", str(page_id)),
                user=None,
                buyer_name=buyer_name,
                buyer_email=buyer_email,
                quantity=quantity,
                unit_price=0,
                status=Order.STATUS_COURTESY,
                notes=notes,
            )
            order.mark_paid()
            _send_ticket_email(order)
            return redirect("ticket_success", order_id=order.id)

    return render(request, "tickets/courtesy.html", {
        "ticketable": ticketable,
        "error": error,
    })


# ── Attendee List ─────────────────────────────────────────────────────────────

@staff_member_required
def event_attendees(request, page_id: int):
    """Staff-only: per-event attendee list with CSV export."""
    from wagtail.models import Page

    page = get_object_or_404(Page, pk=page_id).specific
    orders = (
        Order.objects
        .filter(product_page_id=page_id, status__in=Order.CONFIRMED_STATUSES)
        .prefetch_related("tickets")
        .order_by("-created_at")
    )

    total_tickets = sum(o.quantity for o in orders)
    checked_in = Ticket.objects.filter(order__product_page_id=page_id, used=True).count()

    if request.GET.get("format") == "csv":
        return _attendees_csv(page, orders)

    return render(request, "tickets/attendees.html", {
        "page": page,
        "orders": orders,
        "total_tickets": total_tickets,
        "checked_in": checked_in,
    })


def _attendees_csv(page, orders):
    """Stream a CSV of all attendees for an event."""
    def rows():
        yield "Name,Email,Phone,Quantity,Status,Date,Checked in\r\n"
        for o in orders:
            checked = sum(1 for t in o.tickets.all() if t.used)
            yield (
                f'"{o.buyer_name}","{o.buyer_email}","{o.buyer_phone}",'
                f'{o.quantity},{o.get_status_display()},'
                f'"{(o.paid_at or o.created_at).strftime("%Y-%m-%d %H:%M")}",{checked}\r\n'
            )

    response = StreamingHttpResponse(rows(), content_type="text/csv")
    safe_title = page.title.replace(" ", "_")[:40]
    response["Content-Disposition"] = f'attachment; filename="attendees_{safe_title}.csv"'
    return response


# ── Subscription ─────────────────────────────────────────────────────────────

def support(request):
    """Support/subscription page."""
    context = {
        "plans": Subscription.PLAN_CHOICES,
        "stripe_publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
    }
    return render(request, "tickets/support.html", context)


@require_POST
def create_subscription(request):
    """Create Stripe subscription checkout session and record a pending Subscription."""
    import stripe
    stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        return JsonResponse({"error": "Payment not configured."}, status=503)

    plan = request.POST.get("plan", "supporter")
    email = request.POST.get("email", "").strip()
    name = request.POST.get("name", "").strip()

    price_ids = {
        "supporter": getattr(settings, "STRIPE_PRICE_SUPPORTER", ""),
        "patron": getattr(settings, "STRIPE_PRICE_PATRON", ""),
    }
    price_id = price_ids.get(plan, "")
    if not price_id:
        return JsonResponse({"error": "Plan not configured."}, status=503)

    # Upsert a Subscription record so webhook can find it by email
    sub, _ = Subscription.objects.get_or_create(
        email=email,
        defaults={"name": name, "plan": plan, "active": False},
    )
    sub.plan = plan
    sub.save(update_fields=["plan"])

    base_url = request.build_absolute_uri("/")
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=email or None,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{base_url}tickets/support/thanks/",
            cancel_url=f"{base_url}tickets/support/",
            metadata={"plan": plan, "subscriber_email": email},
        )
        return redirect(session.url, permanent=False)
    except stripe.error.StripeError as e:
        return render(request, "tickets/support.html", {
            "error": str(e),
            "plans": Subscription.PLAN_CHOICES,
            "stripe_publishable_key": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
        })


def support_thanks(request):
    return render(request, "tickets/support_thanks.html")
