import uuid
import qrcode
import io
from django.conf import settings
from django.db import models
from django.core.files.base import ContentFile
from django.utils import timezone


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_REGISTERED = "registered"   # free registration confirmed (no payment)
    STATUS_COURTESY = "courtesy"       # complimentary ticket issued by staff
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_REGISTERED, "Registered (free)"),
        (STATUS_COURTESY, "Courtesy"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    # Confirmed statuses — used for capacity and attendee queries
    CONFIRMED_STATUSES = [STATUS_PAID, STATUS_REGISTERED, STATUS_COURTESY]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # What was purchased — link to a ProductPage or EventPage by Wagtail page PK
    product_page_id = models.IntegerField(null=True, blank=True, db_index=True)
    product_title = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100, blank=True)

    # Buyer info
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    buyer_name = models.CharField(max_length=255)
    buyer_email = models.EmailField()
    buyer_phone = models.CharField(max_length=40, blank=True)

    # Pricing
    quantity = models.PositiveSmallIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="EUR")

    # Staff notes (for courtesy tickets)
    notes = models.TextField(blank=True)

    # Payment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    stripe_payment_intent = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_session_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Order"

    def __str__(self):
        return f"Order {str(self.id)[:8]} — {self.product_title} ({self.buyer_email})"

    @property
    def total(self):
        return (self.unit_price * self.quantity) - self.discount_amount

    def mark_paid(self):
        """Mark order as paid/confirmed and generate tickets."""
        if self.status not in (self.STATUS_PAID, self.STATUS_REGISTERED, self.STATUS_COURTESY):
            self.status = self.STATUS_PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at"])
        self._generate_tickets()

    def _generate_tickets(self):
        for i in range(self.quantity):
            if not self.tickets.filter(seat_number=i + 1).exists():
                ticket = Ticket(order=self, seat_number=i + 1)
                ticket.save()
                ticket.generate_qr()


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tickets")
    seat_number = models.PositiveSmallIntegerField(default=1)
    qr_code = models.ImageField(upload_to="tickets/qr/", blank=True)

    used = models.BooleanField(default=False)
    scanned_at = models.DateTimeField(null=True, blank=True)
    scanned_by = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["order", "seat_number"]
        unique_together = [("order", "seat_number")]
        verbose_name = "Ticket"

    def __str__(self):
        return f"Ticket {str(self.id)[:8]} — {self.order.product_title}"

    @property
    def qr_data(self):
        """The string encoded in the QR code: UUID|order_id|sku"""
        return f"{self.id}|{self.order.id}|{self.order.product_sku}"

    def generate_qr(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        filename = f"ticket_{self.id}.png"
        self.qr_code.save(filename, ContentFile(buf.getvalue()), save=True)

    def verify(self, sku: str | None = None) -> dict:
        """Verify and mark as used. Returns dict with ok/message."""
        if self.used:
            return {"ok": False, "message": "Ticket already used.", "ticket": self}
        if sku and self.order.product_sku and sku != self.order.product_sku:
            return {"ok": False, "message": "Ticket is for a different event.", "ticket": self}
        if self.order.status not in Order.CONFIRMED_STATUSES:
            return {"ok": False, "message": "Order not confirmed.", "ticket": self}
        self.used = True
        self.scanned_at = timezone.now()
        self.save(update_fields=["used", "scanned_at", "scanned_by"])
        return {
            "ok": True,
            "message": f"Valid — {self.order.product_title} × {self.seat_number}/{self.order.quantity}",
            "ticket": self,
        }


class Subscription(models.Model):
    """Newsletter/supporter subscription (Stripe recurring)."""
    PLAN_SUPPORTER = "supporter"
    PLAN_PATRON = "patron"

    PLAN_CHOICES = [
        (PLAN_SUPPORTER, "Supporter — €5/month"),
        (PLAN_PATRON, "Patron — €15/month"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True)
    plan = models.CharField(max_length=30, choices=PLAN_CHOICES, default=PLAN_SUPPORTER)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, db_index=True)
    active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Subscription"

    def __str__(self):
        return f"{self.email} — {self.get_plan_display()}"
