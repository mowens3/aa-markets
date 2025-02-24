"""App settings."""

from app_utils.app_settings import clean_setting

METENOX_ADMIN_NOTIFICATIONS_ENABLED = clean_setting(
    "METENOX_ADMIN_NOTIFICATION_ENABLED", True
)
"""Whether admins will get notifications about important events like
when someone adds a new owner.
"""

METENOX_MOON_MATERIAL_BAY_CAPACITY = clean_setting(
    "METENOX_MOON_MATERIAL_BAY_CAPACITY", 500_000
)
"""
Volume of the Metenox's Moon material Output Bay
Used to calculate how long a metenox takes before being full
"""

METENOX_HOURLY_HARVEST_VOLUME = clean_setting(
    "METENOX_HOURLY_HARVEST_VOLUME ",
    30_000,
)
"""
Hourly volume in m3 that a metenox will harvest.
This value shouldn't be edited
"""

METENOX_HARVEST_REPROCESS_YIELD = clean_setting(
    "METENOX_HARVEST_REPROCESS_YIELD ", 0.40
)
"""
Yield at which the metenox reprocess the harvested materials.
This value shouldn't be edited
"""

METENOX_FUEL_BLOCKS_PER_HOUR = clean_setting("METENOX_FUEL_BLOCKS_PER_HOUR", 5)
"""
How many fuel blocks a running Metenox consumes every hours.
This value shouldn't be edited
"""

METENOX_MAGMATIC_GASES_PER_HOUR = clean_setting("METENOX_MAGMATIC_GASES_PER_HOUR", 110)
"""
How many magmatic gases a running Metenox consumes every hours.
This value shouldn't be edited
"""
