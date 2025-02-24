"""Corporations views"""

from django_datatables_view.base_datatable_view import BaseDatatableView

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from allianceauth.eveonline.evelinks import dotlan
from allianceauth.services.hooks import get_extension_logger
from app_utils.views import link_html

from metenox.models import HoldingCorporation, Owner, Webhook
from metenox.views.general import add_common_context

from ._helpers import corporation_notifications_button_html, user_has_owner_in_corp

logger = get_extension_logger(__name__)


@login_required
@permission_required("metenox.view_metenoxes")
def list_corporations(request):
    """Will list all corporations and their statistics"""

    return render(request, "metenox/corporations.html", add_common_context())


# pylint: disable = too-many-ancestors
class CorporationListJson(
    PermissionRequiredMixin, LoginRequiredMixin, BaseDatatableView
):
    """Datatable view rendering corporations"""

    model = HoldingCorporation
    permission_required = "metenox.view_metenoxes"
    columns = [
        "id",
        "corporation_name",
        "alliance_name",
        "count_metenoxes",
        "raw_revenue",
        "profit",
        "details",
    ]

    order_columns = [
        "pk",
        "",
        "",
        "",
        "",
        "",
        "",
    ]

    def render_column(self, row, column):
        if column == "id":
            return row.pk

        if column == "alliance_name":
            return self._render_alliance(row)

        if column == "corporation_name":
            return self._render_corporation(row)

        if column == "details":
            return self._render_details(row)

        return super().render_column(row, column)

    def _render_alliance(self, row: HoldingCorporation) -> str:
        alliance = row.corporation.alliance
        if alliance:
            alliance_link = link_html(
                dotlan.alliance_url(alliance.alliance_name), alliance.alliance_name
            )
            return alliance_link
        return ""

    def _render_corporation(self, row: HoldingCorporation) -> str:
        corporation_link = link_html(
            dotlan.corporation_url(row.corporation_name), row.corporation_name
        )
        return corporation_link

    def _render_details(self, row):
        return corporation_notifications_button_html(row)

    def get_initial_queryset(self):
        return self.initial_queryset(self.request)

    @classmethod
    def initial_queryset(cls, request):
        """Basic queryset of the function"""
        holding_corporations_query = HoldingCorporation.objects.select_related(
            "corporation",
            "corporation__alliance",
        ).filter(is_active=True)

        if not request.user.has_perm("metenox.auditor"):
            user_owners = Owner.objects.filter(character_ownership__user=request.user)
            holding_corporations_query = holding_corporations_query.filter(
                owners__in=user_owners
            )

        return holding_corporations_query

    def filter_queryset(self, qs):
        """Use params in the GET to filter"""

        qs = self._apply_search_filter(qs, 0, "corporation__corporation_name")

        qs = self._apply_search_filter(qs, 1, "corporation__alliance__alliance_name")

        if search := self.request.GET.get("search[value]", None):
            qs = qs.filter(
                Q(corporation__corporation_name__icontains=search)
                | Q(corporation__alliance__alliance_name__icontains=search)
            )

        return qs

    def _apply_search_filter(self, qs, column_num, field) -> models.QuerySet:
        my_filter = self.request.GET.get(f"columns[{column_num}][search][value]", None)
        if my_filter:
            if self.request.GET.get(f"columns[{column_num}][search][regex]", False):
                kwargs = {f"{field}__iregex": my_filter}
            else:
                kwargs = {f"{field}__istartswith": my_filter}
            return qs.filter(**kwargs)
        return qs


@login_required
@permission_required("metenox.view_metenoxes")
def corporation_fdd_data(request) -> JsonResponse:
    """Provide lists for drop down fields"""
    qs = CorporationListJson.initial_queryset(request)
    columns = request.GET.get("columns")
    result = {}
    if columns:
        for column in columns.split(","):
            options = _calc_options(request, qs, column)
            result[column] = sorted(list(set(options)), key=str.casefold)
    return JsonResponse(result, safe=False)


# pylint: disable = too-many-return-statements, duplicate-code
def _calc_options(request, qs, column):
    if column == "alliance_name":
        values = qs.values_list("corporation__alliance__alliance_name", flat=True)
        values = (value for value in values if value)
        return values

    if column == "corporation_name":
        return qs.values_list("corporation__corporation_name", flat=True)

    return [f"** ERROR: Invalid column name '{column}' **"]


@login_required
@permission_required("metenox.view_metenoxes")
def corporation_notifications(request, corporation_pk: int):
    """Render notification details of a corporation"""

    corporation = get_object_or_404(HoldingCorporation, pk=corporation_pk)
    context = {"corporation": corporation}

    if request.GET.get("new_page"):
        context["title"] = "Corporation notifications"
        context["content_file"] = "metenox/partials/corporation_notifications.html"
        return render(
            request,
            "metenox/modals/generic_modal_page.html",
            add_common_context(context),
        )

    return render(
        request,
        "metenox/modals/corporation_notifications.html",
        add_common_context(context),
    )


@login_required
@permission_required("metenox.corporation_manager")
def change_corporation_ping_settings(request, corporation_pk: int):
    """Changes the ping settings of the corporation"""

    corporation = get_object_or_404(HoldingCorporation, pk=corporation_pk)

    if not user_has_owner_in_corp(request.user, corporation):
        messages.error(request, _("An error occurred"))
        return redirect("metenox:corporations")

    new_ping_on_remaining_magmatic_days = request.POST.get(
        "ping_on_remaining_magmatic_days"
    )
    new_ping_on_remaining_fuel_days = request.POST.get("ping_on_remaining_fuel_days")

    corporation.ping_on_remaining_magmatic_days = new_ping_on_remaining_magmatic_days
    corporation.ping_on_remaining_fuel_days = new_ping_on_remaining_fuel_days

    corporation.save()

    messages.success(
        request,
        _("Successfully changed %(corporation_name)s ping settings")
        % {"corporation_name": corporation.corporation_name},
    )

    return redirect(
        f"{reverse('metenox:notifications', args=[corporation_pk])}?new_page=true"
    )


@login_required
@permission_required("metenox.corporation_manager")
def add_webhook(request, corporation_pk: int):
    """Adds a new webhook to the corporation"""

    corporation = get_object_or_404(HoldingCorporation, pk=corporation_pk)
    corporation_name = corporation.corporation_name

    if not user_has_owner_in_corp(request.user, corporation):
        messages.error(request, _("An error occurred"))
        return redirect("metenox:corporations")

    if request.method == "POST":  # Will handle creating the webhook
        if creation_type := request.POST.get("type"):

            if creation_type == "new":
                webhook_url = request.POST.get("webhook_url")
                webhook_name = request.POST.get("webhook_name")
                Webhook.create_from_url(webhook_url, corporation, webhook_name)
                messages.success(
                    request,
                    _(
                        "Successfully created webhook %(webhook_name)s for corporation %(corporation_name)s"
                    )
                    % {
                        "webhook_name": webhook_name,
                        "corporation_name": corporation_name,
                    },
                )
                return redirect("metenox:add_corporation_webhook", corporation_pk)

            if creation_type == "existing":
                if webhook := Webhook.get_by_id(request.POST.get("webhook_id")):
                    webhook.add_corporation(corporation)
                    webhook_name = webhook.name
                    messages.success(
                        request,
                        _(
                            "Successfully added webhook %(webhook_name)s to corporation %(corporation_name)s"
                        )
                        % {
                            "webhook_name": webhook_name,
                            "corporation_name": corporation_name,
                        },
                    )
                    return redirect("metenox:add_corporation_webhook", corporation_pk)

                messages.error(request, _("Webhook id was not found"))
                return redirect("metenox:add_corporation_webhook", corporation_pk)

            logger.error(
                "Error when trying to create a webhook for corporation id %s."
                "The type parameter had an unexpected value %s",
                corporation_pk,
                creation_type,
            )
            messages.error(
                request,
                _(
                    "Unexpected argument received when creating a webhook for corporation %(corporation_name)s"
                )
                % {"corporation_name": corporation_name},
            )
            return redirect("metenox:corporations")

        logger.error(
            "Error when trying to add a webhook for corporation id %s. The type parameter was not received",
            corporation_pk,
        )
        messages.error(
            request,
            _("Error when trying to add a webhook to corporation %(corporation_name)s")
            % {"corporation_name": corporation_name},
        )
        return redirect("metenox:corporations")

    return render(
        request,
        "metenox/add_webhook.html",
        add_common_context(
            {
                "corporation": corporation,
            }
        ),
    )


@login_required
@permission_required("metenox.corporation_manager")
def remove_corporation_webhook(request, corporation_pk: int, webhook_pk: int):
    """Deletes the selected webhook from selected corporation"""

    corporation = get_object_or_404(HoldingCorporation, pk=corporation_pk)
    webhook = get_object_or_404(Webhook, pk=webhook_pk)

    if not user_has_owner_in_corp(request.user, corporation):
        messages.error(request, _("An error occurred"))
        return redirect("metenox:corporations")

    webhook.holding_corporations.remove(corporation)

    messages.success(
        request,
        _("Webhook %(webhook_name)s was successfully removed from %(corporation_name)s")
        % {
            "webhook_name": webhook.name,
            "corporation_name": corporation.corporation_name,
        },
    )

    return redirect(
        f"{reverse('metenox:notifications', args=[corporation_pk])}?new_page=true"
    )
