"""Helpers for views."""

from moonmining.models import Moon

from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from allianceauth.authentication.admin import User
from allianceauth.services.hooks import get_extension_logger
from app_utils.views import BootstrapStyle

from metenox.models import HoldingCorporation, Metenox

logger = get_extension_logger(__name__)


def generic_details_button_html(
    moon,
    django_detail_view,
    tooltip,
    detail_modal_id,
    fa_icon,
) -> str:
    """
    Return HTML to render a button that will call a modal with an object details.

    Rewriting the function `fontawesome_modal_button_html` from app_utils
    """

    ajax_url = reverse(django_detail_view, args=[moon.pk])

    return format_html(
        '<button type="button" '
        'class="btn btn-{}" '
        'data-bs-toggle="modal" '
        'data-bs-target="#{}" '
        "{}"
        "{}>"
        '<i class="{}"></i>'
        "</button>",
        BootstrapStyle(BootstrapStyle.DEFAULT),
        detail_modal_id,
        mark_safe(f'title="{tooltip}" ') if tooltip else "",
        mark_safe(f'data-ajax_url="{ajax_url}" ') if ajax_url else "",
        fa_icon,
    )


def moon_details_button_html(moon: Moon) -> str:
    """
    Return HTML to render a moon details button.

    Rewriting the function `fontawesome_modal_button_html` from app_utils
    """

    return generic_details_button_html(
        moon, "metenox:moon_details", "Moon details", "modalMoonDetails", "fas fa-moon"
    )


def metenox_details_button_html(metenox: Metenox) -> str:
    """
    Return an HTML button to display the modal with metenox details
    """

    return generic_details_button_html(
        metenox,
        "metenox:metenox_details",
        "Metenox details",
        "modalMetenoxDetails",
        "fas fa-moon",
    )


def corporation_notifications_button_html(holding: HoldingCorporation) -> str:
    """
    Returns an HTML button to display the modal with corporation notifications details
    """

    return generic_details_button_html(
        holding,
        "metenox:notifications",
        "Notification tool",
        "modalCorporationNotifications",
        "fas fa-bell",
    )


def user_has_owner_in_corp(user: User, corporation: HoldingCorporation) -> bool:
    """
    This function will check if the user has an owner in the corporation passed as a parameter.
    Will return true if they have an owner in the corporation. False otherwise
    """
    res = corporation.owners.filter(character_ownership__user=user).exists()
    perm = user.has_perm("metenox.auditor")
    if not (res or perm):
        logger.warning(
            "User id %s tried to access corporation id %s without authorization",
            user.id,
            corporation.corporation_id,
        )

    return res or perm
