from django.db import models
from django.contrib.auth.models import User


class Member(models.Model):
    """Links a Django auth user to an Ideas Block account and optional subscription."""

    ROLE_CHOICES = [
        ("friend", "Friend"),            # free registered account
        ("collaborator", "Collaborator"), # external artist / practitioner
        ("staff", "Staff"),              # internal organisation team
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="member_profile",
    )
    subscription = models.OneToOneField(
        "tickets.Subscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="member",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="friend",
        help_text="Account type. Supporter/Patron status is determined by active subscription.",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------

    @property
    def is_active_supporter(self):
        return self.subscription is not None and self.subscription.active

    @property
    def is_payer(self):
        """True if the member has an active subscription OR any paid order."""
        if self.subscription and self.subscription.active:
            return True
        from tickets.models import Order
        return Order.objects.filter(buyer_email=self.user.email, status="paid").exists()

    def can_access(self, access_level):
        """Return True if this member can access content at the given level."""
        if access_level == "public":
            return True
        if access_level == "members":
            return True  # any Member (= any registered account)
        if access_level == "payers":
            return self.is_payer or self.role == "staff" or self.user.is_staff
        return False

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    @property
    def plan_display(self):
        if self.subscription and self.subscription.active:
            return self.subscription.get_plan_display()
        return "No active plan"

    @property
    def account_type_display(self):
        """Human-readable account type combining role + subscription."""
        if self.user.is_staff:
            return "Staff"
        if self.subscription and self.subscription.active:
            return self.subscription.get_plan_display()  # Supporter / Patron
        return self.get_role_display()  # Friend / Collaborator / Staff

    @property
    def access_level_display(self):
        """What content level this member can reach."""
        if self.user.is_staff or self.role == "staff":
            return "Full access"
        if self.is_payer:
            return "Members + Payer content"
        return "Members content"

    def __str__(self):
        return f"{self.user.email} ({self.account_type_display})"

    class Meta:
        verbose_name = "Member"
