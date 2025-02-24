"""Models."""

import datetime
import re
from math import ceil, floor
from typing import Dict, List, Optional, Set

import dhooks_lite
from moonmining.models import Moon as MoonminigMoon

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Count, Min, Sum
from django.utils import timezone
from esi.models import Token
from eveuniverse.models import EveGroup, EveMoon, EveType

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.evelinks.dotlan import solar_system_url
from allianceauth.eveonline.evelinks.eveimageserver import type_icon_url
from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.notifications.models import Notification
from allianceauth.services.hooks import get_extension_logger
from app_utils.allianceauth import notify_admins

from metenox.app_settings import (
    METENOX_ADMIN_NOTIFICATIONS_ENABLED,
    METENOX_FUEL_BLOCKS_PER_HOUR,
    METENOX_MAGMATIC_GASES_PER_HOUR,
    METENOX_MOON_MATERIAL_BAY_CAPACITY,
)

ESI_SCOPES = [
    "esi-universe.read_structures.v1",
    "esi-corporations.read_structures.v1",
    "esi-assets.read_corporation_assets.v1",
]

logger = get_extension_logger(__name__)


class General(models.Model):
    """A meta model for app permissions."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("view_moons", "Can see all scanned moons"),
            (
                "view_metenoxes",
                "Can add owners and view related corporations metenoxes",
            ),
            ("corporation_manager", "Can modify a corporation ping settings"),
            ("auditor", "Can access metenox information about all corporations"),
        )


class HoldingCorporation(models.Model):
    """Corporation holding metenox moon drills"""

    corporation = models.OneToOneField(
        EveCorporationInfo, on_delete=models.CASCADE, primary_key=True
    )

    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(null=True, default=None)

    ping_on_remaining_magmatic_days = models.IntegerField(
        default=0,
        help_text="Ping should be sent when the magmatic gases stored in a Metenox allow less than this value",
    )
    ping_on_remaining_fuel_days = models.IntegerField(
        default=0,
        help_text="Ping should be sent when the fuel blocks stored in a Metenox allow less than this value",
    )

    @property
    def alliance(self):
        """Returns holding corp's alliance"""
        return self.corporation.alliance

    @property
    def corporation_name(self):
        """Returns the holding corporation's name"""
        return self.corporation.corporation_name

    @property
    def count_metenoxes(self) -> int:
        """Return the number of metenoxes a holding corporation owns"""
        return self.metenoxes.count()

    @property
    def raw_revenue(self) -> float:
        """Returns the raw metenox revenues before fuel prices"""
        return self.metenoxes.aggregate(Sum("moon__value"))["moon__value__sum"]

    @property
    def profit(self) -> float:
        """Returns the metenoxes profit after fuel prices"""
        if self.raw_revenue:
            return self.raw_revenue - self.count_metenoxes * Moon.fuel_price()
        return 0.0

    def active_owners(self):
        """Returns corporation owners that haven't been disabled"""
        return self.owners.filter(is_enabled=True)

    def set_update_time_now(self):
        """Informs that this corporation has just been properly updated"""
        self.last_updated = timezone.now()
        self.save()

    def ping_metenox_fuel(self, metenox: "Metenox", new_fuel_blocks_amount: int):
        """Sends out to all webhooks a notification about the Metenox low fuel blocks level"""
        self.alert_webhooks(
            "Low fuel blocks level",
            f"Your metenox {metenox.structure_name} in "
            f"[{metenox.system_name}]({solar_system_url(metenox.system_name)}) "
            f"level of fuel blocks is under the threshold. Refueling is required",
            [("Remaining Fuel Blocks", new_fuel_blocks_amount)],
        )

    def ping_metenox_magma(self, metenox: "Metenox", new_magmatic_gases_amount: int):
        """Sends out to all webhooks a notification about the Metenox low magmatic level"""
        self.alert_webhooks(
            "Low reagent level",
            f"Your metenox {metenox.structure_name} in "
            f"[{metenox.system_name}]({solar_system_url(metenox.system_name)}) "
            f"level of magmatic gases is under the threshold. Refueling is required",
            [("Remaining Magmatic Gases", new_magmatic_gases_amount)],
        )

    def alert_webhooks(self, title, message, fields):
        """Sends an alert to all metenoxes linked to a corporation"""
        logger.info(
            "Sending a ping to every webhook of corporation id %s",
            self.corporation.corporation_id,
        )
        for webhook in self.webhooks.all():
            webhook.send_alert(
                title,
                message,
                fields,
                self.corporation_name,
                self.corporation.logo_url(32),
            )

    def __str__(self) -> str:
        return self.corporation_name

    @classmethod
    def enable_all_owners(cls, queryset):
        """Enable all the owners of the holding corporations listed in the queryset"""
        owners_qs = Owner.objects.filter(corporation__in=queryset)
        Owner.enable_owners(owners_qs)

    @classmethod
    def disable_all_owners(cls, queryset):
        """Disable all the owners of the holding corporations listed in the queryset"""
        owners_qs = Owner.objects.filter(corporation__in=queryset)
        Owner.disable_owners(owners_qs)


class Owner(models.Model):
    """Character in corporation owning metenoxes"""

    corporation = models.ForeignKey(
        HoldingCorporation,
        on_delete=models.CASCADE,
        related_name="owners",
    )

    character_ownership = models.ForeignKey(
        CharacterOwnership,
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        related_name="+",
        help_text="Character used to sync this corporation from ESI",
    )

    is_enabled = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Disabled corporations are excluded from the update process",
    )

    class Meta:
        verbose_name = "Owner"
        verbose_name_plural = "Owners"

    def __str__(self):
        return self.name

    @property
    def name(self) -> str:
        """Return name."""
        alliance_ticker_str = (
            f" [{self.corporation.alliance.alliance_ticker}]"
            if self.corporation.alliance
            else ""
        )
        return f"{self.corporation}{alliance_ticker_str} - {self.character_name}"

    @property
    def character_name(self) -> str:
        """
        Returns the character name of this owner.
        If it detects that the ownership was deleted it will delete the owner.
        """
        if not self.character_ownership:
            self.delete()  # Will automatically cleanup the dangling toon for the next time
            return "No char associated - owner is being cleaned up"
        return str(self.character_ownership.character)

    @property
    def alliance_name(self) -> str:
        """Return alliance name."""
        return (
            self.corporation.alliance.alliance_name if self.corporation.alliance else ""
        )

    @property
    def user(self) -> User:
        """Return the user linked to this owner"""
        return self.character_ownership.user

    def fetch_token(self) -> Token:
        """Return valid token for this mining corp or raise exception on any error."""
        if not self.character_ownership:
            raise RuntimeError("This owner has no character configured.")
        token = (
            Token.objects.filter(
                character_id=self.character_ownership.character.character_id
            )
            .require_scopes(ESI_SCOPES)
            .require_valid()
            .first()
        )
        if not token:
            raise Token.DoesNotExist(f"{self}: No valid token found.")
        return token

    def enable(self):
        """Enable an owner after logging in the toon again"""
        self.is_enabled = True
        self.save()

    def disable(self, notify=True, cause="Unspecified"):
        """Disables the owner after an ESI error"""
        if notify:
            level = Notification.Level.WARNING
            title = "Metenox owner disabled"
            message = f"The owner {self} has been disabled because of {cause}"
            Notification.objects.notify_user(
                self.user,
                title,
                message,
                level,
            )
            if METENOX_ADMIN_NOTIFICATIONS_ENABLED:
                notify_admins(message, title, level)
        self.is_enabled = False
        self.save()

    @classmethod
    def get_owners_associated_to_user(cls, user: User):
        """Returns all owners of the user"""
        return cls.objects.filter(character_ownership__user=user)

    @classmethod
    def enable_owners(cls, queryset):
        """Receives a queryset of Owners and sets all of them as enabled"""
        queryset.update(is_enabled=True)

    @classmethod
    def disable_owners(cls, queryset):
        """Receives a queryset of Owners and sets all of them as disabled"""
        queryset.update(is_enabled=False)


class Moon(models.Model):
    """Represents a moon and the metenox related values"""

    eve_moon = models.OneToOneField(
        EveMoon, on_delete=models.CASCADE, primary_key=True, related_name="+"
    )

    moonmining_moon = models.OneToOneField(
        MoonminigMoon,
        on_delete=models.CASCADE,
        null=True,  # metenox might be dropped on an unknown moon
        default=None,
        related_name="+",
    )

    value = models.FloatField(default=0)
    value_updated_at = models.DateTimeField(null=True, default=None)

    @property
    def hourly_pull(self) -> Dict[EveType, int]:
        """Returns how much goo is harvested in an hour by a metenox"""
        hourly_products = MetenoxHourlyProducts.objects.filter(moon=self)
        return {product.product: product.amount for product in hourly_products}

    @property
    def name(self) -> str:
        """Returns name of this moon"""
        return self.eve_moon.name.replace("Moon ", "")

    @property
    def rarity_class(self):
        """Returns rarity class of this moon"""
        return self.moonmining_moon.rarity_class

    def update_price(self):
        """Updates the Metenox price attribute to display"""
        hourly_harvest_value = sum(
            EveTypePrice.get_eve_type_price(moon_goo) * moon_goo_amount
            for moon_goo, moon_goo_amount in self.hourly_pull.items()
        )
        self.value = hourly_harvest_value * 24 * 30
        self.value_updated_at = timezone.now()
        self.save()

    @property
    def cycles_before_full(self) -> int:
        """Number of harvest cycles before the moon material bay is at full capacity"""
        bay_capacity = METENOX_MOON_MATERIAL_BAY_CAPACITY
        harvest_volume = sum(
            goo_type.volume * amount for goo_type, amount in self.hourly_pull.items()
        )
        return ceil(bay_capacity / harvest_volume) if harvest_volume != 0 else 0

    @classmethod
    def fuel_price(cls) -> float:
        """Returns the monthly price of running a metenox"""
        hourly_price = (
            METENOX_MAGMATIC_GASES_PER_HOUR * EveTypePrice.get_magmatic_gases_price()
            + METENOX_FUEL_BLOCKS_PER_HOUR * EveTypePrice.get_fuel_block_price()
        )
        return hourly_price * 24 * 30

    @classmethod
    def moons_in_need_of_update(cls):
        """
        Returns a queryset of all moons that have products in the moonmining application but none here
        """

        moons = Moon.objects.annotate(
            num_metenox_products=Count("hourly_products", distinct=True),
            num_moonmining_products=Count("moonmining_moon__products", distinct=True),
        )
        return moons.filter(num_metenox_products__lt=1, num_moonmining_products__gt=0)

    @property
    def profit(self) -> float:
        """Returns the monthly profit of a meteneox including the fuel price"""
        return self.value - self.fuel_price()

    def __str__(self):
        return self.name


class Metenox(models.Model):
    """
    Represents a metenox anchored on a moon
    """

    structure_id = models.PositiveBigIntegerField(primary_key=True)
    structure_name = models.TextField(max_length=150)
    tags = models.ManyToManyField(
        "MetenoxTag",
        blank=True,
        help_text="Tags assigned to a Metenox",
    )

    moon = models.OneToOneField(
        Moon,
        on_delete=models.CASCADE,
        related_name="metenox",
    )
    corporation = models.ForeignKey(
        HoldingCorporation, on_delete=models.CASCADE, related_name="metenoxes"
    )

    fuel_blocks_count = models.IntegerField(default=0)
    magmatic_gas_count = models.IntegerField(default=0)

    was_magmatic_pinged = models.BooleanField(
        default=False,
        help_text="If a ping has been sent out after noticing a low magmatic level",
    )
    was_fuel_pinged = models.BooleanField(
        default=False,
        help_text="If a ping has been sent out after noticing a low fuel level",
    )

    @property
    def system_name(self) -> str:
        """Returns the system name from the structure name"""
        return self.structure_name.split(" - ", maxsplit=1)[0]

    def get_stored_moon_materials(self) -> List["MetenoxStoredMoonMaterials"]:
        """Return the list of stored moon materials in that Metenox"""
        return list(self.stored_moon_materials.all())

    def get_stored_moon_materials_value(self) -> float:
        """Return the value of all moon materials stored in the metenox"""
        return sum(
            EveTypePrice.get_eve_type_price(stored_moon_material.product)
            * stored_moon_material.amount
            for stored_moon_material in self.get_stored_moon_materials()
        )

    def get_stored_moon_materials_volume(self) -> float:
        """Return the volume of all moon materials stored in the metenox"""
        return round(
            sum(
                stored_moon_material.product.volume * stored_moon_material.amount
                for stored_moon_material in self.get_stored_moon_materials()
            ),
            2,
        )

    def set_fuel_blocs(self, new_amount):
        """Edits the amount of fuel blocks in the Metenox and sends a notification if needed"""

        self.fuel_blocks_count = new_amount

        remaining_fuel_days = floor(
            self.fuel_blocks_count / (METENOX_FUEL_BLOCKS_PER_HOUR * 24)
        )

        ping_on_remaining_fuel_days = self.corporation.ping_on_remaining_fuel_days
        if (
            ping_on_remaining_fuel_days > remaining_fuel_days
            and not self.was_fuel_pinged
        ):
            logger.info(
                "Fuel blocks level of metenox id %s are under %s (%s)",
                self.structure_id,
                ping_on_remaining_fuel_days,
                new_amount,
            )
            self.corporation.ping_metenox_fuel(self, new_amount)
            self.was_fuel_pinged = True

        elif (
            ping_on_remaining_fuel_days <= remaining_fuel_days and self.was_fuel_pinged
        ):
            logger.info(
                "Fuel block level of metenox id %s is now back above %s (%s)",
                self.structure_id,
                ping_on_remaining_fuel_days,
                new_amount,
            )
            self.was_fuel_pinged = False

        self.save()

    def set_magmatic_gases(self, new_amount):
        """Edits the amount of magmatic gases in the Metenox and sends a notification if needed"""

        self.magmatic_gas_count = new_amount

        remaining_gas_days = floor(
            self.magmatic_gas_count / (METENOX_MAGMATIC_GASES_PER_HOUR * 24)
        )

        ping_on_remaining_magmatic_days = (
            self.corporation.ping_on_remaining_magmatic_days
        )

        if (
            ping_on_remaining_magmatic_days > remaining_gas_days
            and not self.was_magmatic_pinged
        ):
            logger.info(
                "Magmatic gas level of metenox id %s are under %s (%s)",
                self.structure_id,
                ping_on_remaining_magmatic_days,
                new_amount,
            )
            self.corporation.ping_metenox_magma(self, new_amount)
            self.was_magmatic_pinged = True

        elif (
            ping_on_remaining_magmatic_days <= remaining_gas_days
            and self.was_magmatic_pinged
        ):
            logger.info(
                "Magmatic gas level of metenox id %s is now back above %s (%s)",
                self.structure_id,
                ping_on_remaining_magmatic_days,
                new_amount,
            )
            self.was_magmatic_pinged = False

        self.save()

    def __str__(self):
        return self.structure_name

    class Meta:
        verbose_name_plural = "Metenoxes"


class MetenoxHourlyProducts(models.Model):
    """
    Represents how much moon goo a Metenox harvests in an hour
    """

    moon = models.ForeignKey(
        Moon, on_delete=models.CASCADE, related_name="hourly_products"
    )
    product = models.ForeignKey(EveType, on_delete=models.CASCADE, related_name="+")

    amount = models.IntegerField()

    def __str__(self):
        return f"{self.product.name} - {self.amount}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["moon", "product"], name="functional_pk_metenoxhourlyproduct"
            )
        ]

    @classmethod
    def all_moon_goo_ids(cls) -> Set[int]:
        """Returns all known moon goo ids in the database"""
        return set(cls.objects.values_list("product", flat=True).order_by("product_id"))


class MetenoxStoredMoonMaterials(models.Model):
    """
    Represents how much moon materials are currently stored inside a Metenox
    """

    metenox = models.ForeignKey(
        Metenox, on_delete=models.CASCADE, related_name="stored_moon_materials"
    )
    product = models.ForeignKey(EveType, on_delete=models.CASCADE, related_name="+")

    amount = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.amount} in {self.metenox.structure_name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["metenox", "product"], name="functional_pk_metenoxstoredproduct"
            )
        ]


class MetenoxTag(models.Model):
    """
    Tags assigned to a metenox for easy sorting
    """

    name = models.CharField(max_length=20)
    default = models.BooleanField(
        default=False, help_text="This tag will be applied on every new metenox if true"
    )

    def __str__(self):
        return self.name


class EveTypePrice(models.Model):
    """
    Represent an eve type and its last fetched price
    """

    __MOON_GOOS_GROUP_ID = 427
    __FUEL_BLOCK_GROUP_ID = 1136
    __MAGMATIC_TYPE_ID = 81143

    eve_type = models.OneToOneField(EveType, on_delete=models.CASCADE, related_name="+")
    price = models.FloatField(default=0)
    last_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.eve_type.name} - {self.price} ISK"

    def update_price(self, new_price: float):
        """Updates the price of an item"""
        if new_price <= 0:
            return
        self.price = new_price
        self.save()

    @classmethod
    def get_eve_type_price(cls, eve_type: EveType) -> float:
        """Returns the price of an item"""
        type_price, _ = cls.objects.get_or_create(eve_type=eve_type)
        return type_price.price

    @classmethod
    def get_eve_type_id_price(cls, eve_type_id: int) -> float:
        """Returns the price of an item id"""
        return cls.get_eve_type_price(EveType.objects.get(id=eve_type_id))

    @classmethod
    def _get_type_ids_from_group(cls, group_id: int) -> Set[int]:
        """Fetches type ids from their group and returns it as a set"""
        group = EveGroup.objects.get(id=group_id)
        return set(group.eve_types.filter(published=True).values_list("id", flat=True))

    @classmethod
    def get_fuels_type_ids(cls) -> Set[int]:
        """Fetches the id of all 4 fuel blocks from their group and magmatic gas"""
        return cls._get_type_ids_from_group(cls.__FUEL_BLOCK_GROUP_ID) | {
            cls.__MAGMATIC_TYPE_ID
        }

    @classmethod
    def get_moon_goos_type_ids(cls) -> Set[int]:
        """Fetches the ids of all moon goos from their group"""
        return cls._get_type_ids_from_group(cls.__MOON_GOOS_GROUP_ID)

    @classmethod
    def get_magmatic_gas_type_id(cls) -> int:
        """Return the type of magmatic gases"""
        return cls.__MAGMATIC_TYPE_ID

    @classmethod
    def get_fuel_block_price(cls) -> float:
        """Returns the price of the cheapest fuel block"""
        return (
            cls.objects.filter(eve_type__eve_group=cls.__FUEL_BLOCK_GROUP_ID).aggregate(
                Min("price")
            )["price__min"]
            or 0.0
        )

    @classmethod
    def get_magmatic_gases_price(cls) -> float:
        """Returns the price of a unit of magmatic gases"""
        return cls.get_eve_type_id_price(cls.__MAGMATIC_TYPE_ID)


class Webhook(models.Model):
    """Represents a discord webhook information"""

    webhook_id = models.BigIntegerField(primary_key=True)
    webhook_token = models.TextField()

    name = models.CharField(
        max_length=30, unique=True, help_text="Text to recognize the webhook"
    )
    default = models.BooleanField(
        default=False,
        help_text="If the webhook will automatically be added to every new corporation",
    )

    holding_corporations = models.ManyToManyField(
        HoldingCorporation,
        related_name="webhooks",
        help_text="Corporation associated to this webhook",
    )

    @classmethod
    def create_from_url(
        cls,
        webhook_url: str,
        holding_corporation: HoldingCorporation,
        name: str = "",
    ) -> Optional["Webhook"]:
        """Parses a webhook URL to extract the information and returns the newly created webhook"""
        pattern = r"https:\/\/discord.com\/api\/webhooks\/(?P<id>\d+)\/(?P<token>.+)"
        match = re.match(pattern, webhook_url)

        if not match:  # regex didn't find the groups
            return None

        new_webhook = cls.objects.create(
            webhook_id=int(match["id"]),
            webhook_token=match["token"],
            name=name,
        )

        new_webhook.holding_corporations.add(holding_corporation)

        return new_webhook

    @classmethod
    def get_by_id(cls, webhook_id: int) -> Optional["Webhook"]:
        """Tries to find a webhook by its id"""
        try:
            return cls.objects.get(webhook_id=webhook_id)
        except cls.DoesNotExist:
            return None

    @property
    def url(self) -> str:
        """Builds the discord webhook URL"""
        return (
            f"https://discord.com/api/webhooks/{self.webhook_id}/{self.webhook_token}"
        )

    def _build_webhook(self) -> dhooks_lite.Webhook:
        """Builds the discord webhook and returns it"""
        return dhooks_lite.Webhook(
            self.url,
            username="Metenox notification",
            avatar_url="https://gitlab.com/uploads/-/system/project/avatar/60747747/oil-well-solid.png",
        )

    # pylint: disable = too-many-positional-arguments, too-many-arguments
    def send_alert(
        self,
        title: str,
        content: str,
        fields=None,
        author_name: str = None,
        author_icon_url: str = None,
    ):
        """Sends an alert through the webhook"""
        embed = self._build_embed(
            title, content, 0xFF5733, fields, author_name, author_icon_url
        )
        self._send_through_webhook([embed])

    # pylint: disable = too-many-positional-arguments, too-many-arguments
    def send_info(
        self,
        title: str,
        content: str,
        fields=None,
        author_name: str = None,
        author_icon_url: str = None,
    ):
        """Sends an information through the webhook"""
        embed = self._build_embed(
            title, content, 0x5CDBF0, fields, author_name, author_icon_url
        )
        self._send_through_webhook([embed])

    def _send_through_webhook(self, embeds: List[dhooks_lite.Embed]):
        """Sends embeds through the webhook"""
        webhook = self._build_webhook()
        webhook.execute(embeds=embeds)

    # pylint: disable = too-many-positional-arguments, too-many-arguments
    def _build_embed(
        self,
        title: str,
        content: str,
        color: int,
        fields=None,
        author_name: str = None,
        author_icon_url: str = None,
    ) -> dhooks_lite.Embed:
        """Build a discord embedd and returns it"""

        formatted_fields = []
        if fields:
            for field in fields:
                formatted_fields.append(dhooks_lite.Field(field[0], str(field[1])))

        embed = dhooks_lite.Embed(
            author=dhooks_lite.Author(
                name=author_name,
                icon_url=author_icon_url,
            ),
            title=title,
            description=content,
            thumbnail=dhooks_lite.Thumbnail(type_icon_url(81826, size=128)),
            color=color,
            fields=formatted_fields,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            footer=dhooks_lite.Footer(
                "aa-metenox",
            ),
        )

        return embed

    def add_corporation(self, corporation: HoldingCorporation):
        """Adds a corporation to the list that should be pinged"""
        self.holding_corporations.add(corporation)

    def remove_corporation(self, corporation: HoldingCorporation):
        """Removes a corporation from the list that should be pinged"""
        self.holding_corporations.remove(corporation)

    @classmethod
    def add_default_webhooks_to_corporation(cls, corporation: HoldingCorporation):
        """Adds all webhooks tagged as default to the corporation"""
        for webhook in cls.objects.filter(default=True):
            webhook.add_corporation(corporation)

    def __str__(self):
        return self.name
