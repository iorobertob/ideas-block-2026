"""
Utility for checking user access to gated content.

Access levels:
  public    — anyone, no login required
  members   — any authenticated user (any role)
  payers    — active subscription OR any paid order
"""


def user_can_access(user, access_level):
    if access_level == "public":
        return True
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True  # Django staff always has full access
    if access_level == "members":
        return True  # any authenticated user qualifies
    if access_level == "payers":
        try:
            return user.member_profile.can_access("payers")
        except Exception:
            return False
    return False
