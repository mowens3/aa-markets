"""Admin site."""

from django.contrib import admin

from markets.models import (
    EveTypePrice,
    HoldingCorporation,
    Markets,
    MarketsHourlyProducts,
    MarketsStoredMoonMaterials,
    MarketsTag,
    Moon,
    Owner,
    Webhook,
)
from markets.templatetags.markets import formatisk


class MarketsHourlyHarvestInline(admin.TabularInline):
    model = MarketsHourlyProducts

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Moon)
class MoonAdmin(admin.ModelAdmin):
    list_display = ["name", "moon_value", "value_updated_at"]
    fields = [("eve_moon", "moonmining_moon"), ("value", "value_updated_at")]
    search_fields = ["eve_moon__name"]
    readonly_fields = ["eve_moon", "moonmining_moon"]
    inlines = (MarketsHourlyHarvestInline,)

    @admin.display(description="value")
    def moon_value(self, moon: Moon):
        return f"{formatisk(moon.value)} ISK"

    def has_add_permission(self, request):
        return False


@admin.action(description="Reset the markets ping status")
def reset_pings(modeladmin, request, queryset):
    """Resets the ping status of the selected markets for them to be pinged again"""
    queryset.update(was_magmatic_pinged=False, was_fuel_pinged=False)


class MarketsMoonMaterialBayInline(admin.TabularInline):
    model = MarketsStoredMoonMaterials

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Markets)
class MarketsAdmin(admin.ModelAdmin):
    list_display = [
        "structure_name",
        "corporation",
        "alliance",
        "tag_display",
        "markets_value",
        "fuel_blocks_count",
        "magmatic_gas_count",
        "was_fuel_pinged",
        "was_magmatic_pinged",
    ]
    list_filter = ["corporation", "corporation__corporation__alliance", "tags"]
    actions = [reset_pings]
    fields = [
        ("structure_id", "structure_name"),
        "moon",
        "corporation",
        "tags",
        ("fuel_blocks_count", "magmatic_gas_count"),
        ("was_fuel_pinged", "was_magmatic_pinged"),
    ]
    readonly_fields = ["structure_id", "moon", "was_fuel_pinged", "was_magmatic_pinged"]
    inlines = (MarketsMoonMaterialBayInline,)

    @admin.display(description="Value", ordering="moon__value")
    def markets_value(self, markets: Markets):
        return f"{formatisk(markets.moon.value)} ISK"

    @admin.display(
        description="Corporation alliance",
        ordering="corporation__corporation__alliance",
    )
    def alliance(self, markets: Markets):
        return markets.corporation.alliance

    @admin.display(description="Tags attached to the markets")
    def tag_display(self, markets: Markets):
        return " ,".join([tag.name for tag in markets.tags.all()])

    def has_add_permission(self, request):
        return False


@admin.action(description="Enable selected owners")
def enable_owners(modeladmin, request, queryset):
    """Enable all owners of the received queryset"""
    Owner.enable_owners(queryset)


@admin.action(description="Disable selected owners")
def disable_owners(modeladmin, request, queryset):
    """Disable all owners of the received queryset"""
    Owner.disable_owners(queryset)


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = [
        "char_name",
        "is_enabled",
        "corporation",
        "ally_name",
        "character_ownership",
    ]
    list_filter = ["is_enabled", "corporation", "corporation__corporation__alliance"]
    readonly_fields = ["character_ownership", "corporation"]
    actions = [enable_owners, disable_owners]

    @admin.display(
        description="Character name", ordering="character_ownership__character"
    )
    def char_name(self, owner: Owner) -> str:
        return owner.character_name

    @admin.display(
        description="Alliance name", ordering="corporation__corporation__alliance"
    )
    def ally_name(self, owner: Owner) -> str:
        return owner.alliance_name

    def has_add_permission(self, request):
        return False


@admin.action(description="Enable all owners of the corporations")
def enable_all_owners(modeladmin, request, queryset):
    """Enable all owners part of the corporations listed"""
    HoldingCorporation.enable_all_owners(queryset)


@admin.action(description="Disable all owners of the corporations")
def disable_all_owners(modeladmin, request, queryset):
    """Disable all owners part of the corporations listed"""
    HoldingCorporation.disable_all_owners(queryset)


class OwnerCharacterAdminInline(admin.TabularInline):
    model = Owner
    readonly_fields = ["character_ownership"]

    fields = ["character_ownership", "is_enabled"]

    def has_add_permission(self, request, obj):
        return False


@admin.register(HoldingCorporation)
class HoldingCorporationAdmin(admin.ModelAdmin):
    list_display = [
        "corporation",
        "alliance",
        "is_active",
        "count_markets",
        "count_owners",
        "last_updated",
    ]
    list_filter = ["corporation__alliance", "is_active"]
    sortable_by = ["is_active"]
    actions = [enable_all_owners, disable_all_owners]
    readonly_fields = ["corporation", "last_updated", "count_markets"]
    inlines = (OwnerCharacterAdminInline,)

    @admin.display(description="Number markets")
    def count_markets(self, holding: HoldingCorporation) -> int:
        return holding.count_markets

    @admin.display(
        description="Number of owners / active owners", ordering="owners__count"
    )
    def count_owners(self, holding: HoldingCorporation) -> str:
        return f"{holding.owners.count()} / {holding.active_owners().count()}"

    def has_add_permission(self, request):
        return False


@admin.register(EveTypePrice)
class EveTypePriceAdmin(admin.ModelAdmin):
    list_display = ["eve_type", "eve_group", "type_price"]
    readonly_fields = ["eve_type", "last_update"]

    @admin.display(description="Price", ordering="price")
    def type_price(self, type_price: EveTypePrice):
        return f"{formatisk(type_price.price)} ISK"

    @admin.display(description="Eve Group", ordering="eve_type__eve_group")
    def eve_group(self, type_price: EveTypePrice):
        return type_price.eve_type.eve_group

    def has_add_permission(self, request):
        return False


@admin.action(description="Add the tags to every markets")
def add_tags(modeladmin, request, queryset):
    for markets in Markets.objects.all():
        markets.tags.add(*queryset)


@admin.register(MarketsTag)
class MarketsTagAdmin(admin.ModelAdmin):
    list_display = ["name", "default"]
    actions = [add_tags]


@admin.action(description="Send a test message to the selected webhooks")
def test_webhooks(modeladmin, request, queryset):
    """Test the selected webhooks"""
    for webhook in queryset:
        webhook.send_info(
            "Test notification",
            "This is a webhook test send from the aa-markets application",
        )


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ["name", "webhook_id", "count_holdings", "default"]
    list_filter = ["holding_corporations", "default"]
    actions = [test_webhooks]
    readonly_fields = ["webhook_id", "webhook_token"]

    @admin.display(
        description="Number of corporations attached to this webhook",
        ordering="webhooks__count",
    )
    def count_holdings(self, webhook: Webhook):
        return webhook.holding_corporations.count()
