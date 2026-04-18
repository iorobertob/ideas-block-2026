from django import template
from members.access import user_can_access

register = template.Library()


@register.filter(name="can_access")
def can_access_filter(user, access_level):
    """
    Usage: {% if request.user|can_access:"payers" %}

    Returns True if the user meets the access level requirement.
    """
    return user_can_access(user, access_level)
