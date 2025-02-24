"""App settings."""

from app_utils.app_settings import clean_setting

MARKETS_ADMIN_NOTIFICATIONS_ENABLED = clean_setting(
    "MARKETS_ADMIN_NOTIFICATION_ENABLED", True
)
"""Whether admins will get notifications about important events like
when someone adds a new owner.
"""

MARKETS_MOON_MATERIAL_BAY_CAPACITY = clean_setting(
    "MARKETS_MOON_MATERIAL_BAY_CAPACITY", 500_000
)
"""
Volume of the Metenox's Moon material Output Bay
Used to calculate how long a metenox takes before being full
"""

MARKETS_HOURLY_HARVEST_VOLUME = clean_setting(
    "MARKETS_HOURLY_HARVEST_VOLUME ",
    30_000,
)
"""
Hourly volume in m3 that a metenox will harvest.
This value shouldn't be edited
"""

MARKETS_HARVEST_REPROCESS_YIELD = clean_setting(
    "MARKETS_HARVEST_REPROCESS_YIELD ", 0.40
)
"""
Yield at which the metenox reprocess the harvested materials.
This value shouldn't be edited
"""

MARKETS_FUEL_BLOCKS_PER_HOUR = clean_setting("MARKETS_FUEL_BLOCKS_PER_HOUR", 5)
"""
How many fuel blocks a running Metenox consumes every hours.
This value shouldn't be edited
"""

MARKETS_MAGMATIC_GASES_PER_HOUR = clean_setting("MARKETS_MAGMATIC_GASES_PER_HOUR", 110)
"""
How many magmatic gases a running Metenox consumes every hours.
This value shouldn't be edited
"""
