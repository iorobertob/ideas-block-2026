from django.db import models
from django.contrib.auth.models import User


class Member(models.Model):
    """Links a Django auth user to an Ideas Block supporter subscription."""
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
    joined_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_active_supporter(self):
        return self.subscription is not None and self.subscription.active

    @property
    def plan_display(self):
        if self.subscription:
            return self.subscription.get_plan_display()
        return "No active plan"

    def __str__(self):
        return f"{self.user.email} ({self.plan_display})"

    class Meta:
        verbose_name = "Member"
