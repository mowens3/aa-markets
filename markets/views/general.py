"""Utility views or functions used everywhere"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from esi.decorators import token_required

from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.services.hooks import get_extension_logger
from app_utils.allianceauth import notify_admins

from markets import tasks
from markets.app_settings import (
    MARKETS_ADMIN_NOTIFICATIONS_ENABLED,
    MARKETS_FUEL_BLOCKS_PER_HOUR,
    MARKETS_MAGMATIC_GASES_PER_HOUR,
)
from markets.models import ESI_SCOPES, HoldingCorporation, Moon, Owner, Webhook

logger = get_extension_logger(__name__)


@login_required
def index(request):
    """
    Basic view of the app.
    Should redirect depending on user's roles
    """

    if request.user.has_perm("markets.view_moons"):
        return redirect("markets:moons")

    if request.user.has_perm("markets.view_markets"):
        return redirect("markets:markets")

    logger.warning(
        "User %s tried to access the markets application unauthorized", request.user
    )
    messages.error(request, _("An error occured"))
    return redirect("/")


def add_common_context(context: dict = None) -> dict:
    """Enhance the templates context with context that should be added to every page"""
    if context is None:
        context = {}

    if basic_title := context.get("page_title"):
        context["page_title"] = f"{basic_title} - Markets"
    else:
        context["page_title"] = "Markets"

    context["monthly_fuel_price"] = Moon.fuel_price()
    context["markets_fuel_blocks_per_hour"] = MARKETS_FUEL_BLOCKS_PER_HOUR
    context["markets_magmatic_gases_per_hour"] = MARKETS_MAGMATIC_GASES_PER_HOUR

    return context


@cache_page(3600)
def modal_loader_body(request):
    """Draw the loader body. Useful for showing a spinner while loading a modal."""
    return render(request, "markets/modals/loader_body.html")


@permission_required(["markets.view_markets"])
@token_required(scopes=ESI_SCOPES)
@login_required
def add_owner(request, token):
    """Render view to add an owner."""
    character_ownership = get_object_or_404(
        request.user.character_ownerships.select_related("character"),
        character__character_id=token.character_id,
    )
    corporation_id = character_ownership.character.corporation_id
    try:
        corporation = EveCorporationInfo.objects.get(corporation_id=corporation_id)
    except EveCorporationInfo.DoesNotExist:
        corporation = EveCorporationInfo.objects.create_corporation(
            corp_id=corporation_id
        )
        corporation.save()

    holding_corporation, created_corporation = HoldingCorporation.objects.get_or_create(
        corporation=corporation,
    )

    if created_corporation:
        Webhook.add_default_webhooks_to_corporation(holding_corporation)

    owner, created_owner = Owner.objects.get_or_create(
        corporation=holding_corporation, character_ownership=character_ownership
    )
    if not created_owner:
        owner.enable()  # Gives another chance to the toon at being used for updates

    # TODO figure out why I need to type all this to get the right corp id
    tasks.update_holding.delay(owner.corporation.corporation.corporation_id)
    messages.success(request, f"Update of refineries started for {owner}.")
    if MARKETS_ADMIN_NOTIFICATIONS_ENABLED:
        notify_admins(
            message=f"{owner} was added as new owner by {request.user}.",
            title=f"Markets: Owner added: {owner}",
        )
    return redirect("markets:corporations")
