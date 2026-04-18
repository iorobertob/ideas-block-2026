from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from tickets.models import Order, Subscription


def member_login(request):
    if request.user.is_authenticated:
        return redirect("member_dashboard")
    error = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get("next", "member_dashboard"))
        error = "Invalid email or password."
    return render(request, "members/login.html", {"error": error})


def member_register(request):
    if request.user.is_authenticated:
        return redirect("member_dashboard")
    error = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")
        name = request.POST.get("name", "").strip()

        if not email or not password:
            error = "Email and password are required."
        elif password != password2:
            error = "Passwords do not match."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif User.objects.filter(username=email).exists():
            error = "An account with this email already exists."
        else:
            parts = name.split(" ", 1) if name else ["", ""]
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=parts[0],
                last_name=parts[1] if len(parts) > 1 else "",
            )
            # Auto-link to any existing active subscription for this email
            from .models import Member
            try:
                sub = Subscription.objects.get(email=email, active=True)
                Member.objects.get_or_create(user=user, defaults={"subscription": sub})
            except Subscription.DoesNotExist:
                Member.objects.get_or_create(user=user)

            login(request, user)
            return redirect("member_dashboard")
    return render(request, "members/register.html", {"error": error})


@login_required(login_url="/members/login/")
def member_dashboard(request):
    from .models import Member
    member, _ = Member.objects.get_or_create(user=request.user)

    # Try to auto-link subscription if not yet linked
    if not member.subscription:
        try:
            sub = Subscription.objects.get(email=request.user.email, active=True)
            member.subscription = sub
            member.save(update_fields=["subscription"])
        except Subscription.DoesNotExist:
            pass

    orders = Order.objects.filter(
        Q(user=request.user) | Q(buyer_email=request.user.email)
    ).exclude(status=Order.STATUS_PENDING).order_by("-created_at").distinct()[:20]

    return render(request, "members/dashboard.html", {
        "member": member,
        "orders": orders,
    })


@require_POST
def member_logout(request):
    logout(request)
    return redirect("/")
