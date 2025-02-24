"""Corporation views"""

from django_datatables_view.base_datatable_view import BaseDatatableView

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from allianceauth.eveonline.evelinks import dotlan
from allianceauth.services.hooks import get_extension_logger
from app_utils.views import link_html

from metenox.models import HoldingCorporation, Metenox, Moon, Owner
from metenox.views._helpers import metenox_details_button_html
from metenox.views.general import add_common_context

from ..templatetags.metenox import formatisk
from ._helpers import user_has_owner_in_corp

logger = get_extension_logger(__name__)


@permission_required(["metenox.view_metenoxes"])
@login_required
def metenoxes(request):
    """
    Displays the metenoxes that the user is allowed to see
    """
    return render(request, "metenox/metenoxes.html", add_common_context())


# pylint: disable = too-many-ancestors, duplicate-code
class MetenoxListJson(PermissionRequiredMixin, LoginRequiredMixin, BaseDatatableView):
    """Datatable view rendering metenoxes"""

    model = Metenox
    permission_required = "metenox.view_metenoxes"
    columns = [
        "id",
        "metenox_name",
        "moon_name",
        "corporation_name",
        "rarity_class_str",
        "solar_system_link",
        "location_html",
        "fuel_blocks_count",
        "magmatic_gas_count",
        "region_name",
        "constellation_name",
        "value",
        "details",
        "tags",
    ]

    # define column names that will be used in sorting
    # order is important and should be same as order of columns
    # displayed by datatables. For non-sortable columns use empty
    # value like ''
    order_columns = [
        "pk",
        "",
        "",
        "",
        "",
        "fuel_blocks_count",
        "magmatic_gas_count",
        "moon__value",
        "",
        "",
        "",
        "",
        "",
    ]

    # pylint: disable = too-many-return-statements
    def render_column(self, row, column):
        if column == "id":
            return row.pk

        if column == "moon_name":
            return row.moon.name

        if column == "metenox_name":
            return row.structure_name

        if column == "corporation_name":
            return self._render_corporation(row)

        if column == "value":
            return format_html(
                "{}<br>{}", formatisk(row.moon.value), formatisk(row.moon.profit)
            )

        if result := self._render_location(row, column):
            return result

        if column == "details":
            return self._render_details(row)

        return super().render_column(row, column)

    def get_initial_queryset(self):
        return self.initial_queryset(self.request)

    @classmethod
    def initial_queryset(cls, request):
        """Initial query"""
        metenox_query = Metenox.objects.select_related(
            "moon",
            "corporation",
            "moon__moonmining_moon",
            "moon__eve_moon",
            "moon__eve_moon__eve_planet__eve_solar_system",
            "moon__eve_moon__eve_planet__eve_solar_system__eve_constellation__eve_region",
        ).filter(corporation__is_active=True)

        if not request.user.has_perm("metenox.auditor"):
            user_owners = Owner.objects.filter(character_ownership__user=request.user)
            user_corporations = HoldingCorporation.objects.filter(
                owners__in=user_owners
            )
            metenox_query = metenox_query.filter(corporation__in=user_corporations)

        metenox_query = metenox_query.annotate(
            rarity_class_str=Concat(
                Value("R"),
                F("moon__moonmining_moon__rarity_class"),
                output_field=models.CharField(),
            )
        )

        return metenox_query

    def filter_queryset(self, qs):
        """Use params in the GET to filter"""
        qs = self._apply_search_filter(
            qs,
            12,
            "moon__eve_moon__eve_planet__eve_solar_system__eve_constellation__eve_region__name",
        )
        qs = self._apply_search_filter(
            qs,
            11,
            "moon__eve_moon__eve_planet__eve_solar_system__eve_constellation__name",
        )
        qs = self._apply_search_filter(
            qs, 9, "moon__eve_moon__eve_planet__eve_solar_system__name"
        )
        qs = self._apply_search_filter(qs, 10, "rarity_class_str")

        qs = self._apply_search_filter(
            qs, 2, "corporation__corporation__corporation_name"
        )

        qs = self._apply_search_filter(
            qs,
            13,
            "tags__name",
        )

        if search := self.request.GET.get("search[value]", None):
            qs = qs.filter(structure_name__icontains=search)
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

    def _render_corporation(self, row):
        corporation_link = link_html(
            dotlan.corporation_url(row.corporation.corporation_name),
            row.corporation.corporation_name,
        )
        return corporation_link

    def _render_location(self, row: Moon, column):
        solar_system = row.moon.eve_moon.eve_planet.eve_solar_system
        if solar_system.is_high_sec:
            sec_class = "text-high-sec"
        elif solar_system.is_low_sec:
            sec_class = "text-low-sec"
        else:
            sec_class = "text-null-sec"
        solar_system_link = format_html(
            '{}&nbsp;<span class="{}">{}</span>',
            link_html(dotlan.solar_system_url(solar_system.name), solar_system.name),
            sec_class,
            round(solar_system.security_status, 1),
        )

        constellation = row.moon.eve_moon.eve_planet.eve_solar_system.eve_constellation
        region = constellation.eve_region
        location_html = format_html(
            "{}<br><em>{}</em>", constellation.name, region.name
        )
        if column == "solar_system_name":
            return solar_system.name

        if column == "solar_system_link":
            return solar_system_link

        if column == "location_html":
            return location_html

        if column == "region_name":
            return region.name

        if column == "constellation_name":
            return constellation.name

        return None

    def _render_details(self, row):
        return metenox_details_button_html(row)


@login_required
@permission_required("metenox.view_metenoxes")
def metenox_fdd_data(request) -> JsonResponse:
    """Provide lists for drop down fields"""
    qs = MetenoxListJson.initial_queryset(request)
    columns = request.GET.get("columns")
    result = {}
    if columns:
        for column in columns.split(","):
            options = [
                option for option in _calc_options(request, qs, column) if option
            ]
            result[column] = sorted(list(set(options)), key=str.casefold)
    return JsonResponse(result, safe=False)


# pylint: disable = too-many-return-statements
def _calc_options(request, qs, column):
    if column == "region_name":
        return qs.values_list(
            "moon__eve_moon__eve_planet__eve_solar_system__eve_constellation__eve_region__name",
            flat=True,
        )

    if column == "constellation_name":
        return qs.values_list(
            "moon__eve_moon__eve_planet__eve_solar_system__eve_constellation__name",
            flat=True,
        )

    if column == "solar_system_name":
        return qs.values_list(
            "moon__eve_moon__eve_planet__eve_solar_system__name",
            flat=True,
        )

    if column == "rarity_class_str":
        return qs.values_list("rarity_class_str", flat=True)

    if column == "corporation_name":
        return qs.values_list("corporation__corporation__corporation_name", flat=True)

    if column == "tags":
        tag_names_list = qs.distinct().values_list("tags__name", flat=True)
        return tag_names_list

    return [f"** ERROR: Invalid column name '{column}' **"]


@login_required
@permission_required("metenox.view_metenoxes")
def metenox_details(request, metenox_pk: int):
    """Renders metenox details"""
    metenox = get_object_or_404(Metenox, pk=metenox_pk)
    if not user_has_owner_in_corp(request.user, metenox.corporation):
        logger.warning(
            "User %s tried to access metenox id %s without authorization",
            request.user,
            metenox_pk,
        )
        messages.error(request, _("An error occurred"))
        return redirect("metenoxes:metenoxes")
    context = {
        "page_title": metenox.structure_name,
        "metenox": metenox,
        "moon": metenox.moon,
    }

    if request.GET.get("new_page"):
        context["title"] = "Metenox details"
        context["content_file"] = "metenox/partials/metenox_details.html"
        return render(
            request,
            "metenox/modals/generic_modal_page.html",
            add_common_context(context),
        )
    return render(
        request, "metenox/modals/metenox_details.html", add_common_context(context)
    )
