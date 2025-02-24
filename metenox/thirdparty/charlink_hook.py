"""Hooks for charlink application"""

from charlink.app_imports.utils import (  # pylint: disable=import-error
    AppImport,
    LoginImport,
)

from django.contrib import messages
from django.contrib.auth.models import Permission, User
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404

from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from app_utils.allianceauth import notify_admins, users_with_permission

from metenox import tasks
from metenox.app_settings import METENOX_ADMIN_NOTIFICATIONS_ENABLED
from metenox.models import ESI_SCOPES, HoldingCorporation, Owner, Webhook


# pylint: disable=duplicate-code
def _add_character(request, token):
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
    if METENOX_ADMIN_NOTIFICATIONS_ENABLED:
        notify_admins(
            message=f"{owner} was added as new owner by {request.user}.",
            title=f"Metenox: Owner added: {owner}",
        )


def _check_permissions(user: User) -> bool:
    """Checks if the user can use the Metenox application"""

    return user.has_perm("metenox.view_moons") or user.has_perm(
        "metenox.view_metenoxes"
    )


def _is_character_added(character: EveCharacter) -> bool:
    """Checks if the character is already added in the Metenox application"""

    return Owner.objects.filter(character_ownership__character=character).exists()


def _users_with_perms():
    return users_with_permission(
        Permission.objects.get(content_type__app_label="metenox", codename="view_moons")
    ) | users_with_permission(
        Permission.objects.get(
            content_type__app_label="metenox", codename="view_metenoxes"
        )
    )


app_import = AppImport(
    "metenox",
    [
        LoginImport(
            app_label="metenox",
            unique_id="default",
            field_label="Metenox",
            add_character=_add_character,
            scopes=ESI_SCOPES,
            check_permissions=_check_permissions,
            is_character_added=_is_character_added,
            is_character_added_annotation=Exists(
                Owner.objects.filter(character_ownership__character_id=OuterRef("pk"))
            ),
            get_users_with_perms=_users_with_perms,
        )
    ],
)
