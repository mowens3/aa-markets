"""Template Tags."""

import datetime as dt
from typing import Optional

from moonmining.constants import DATETIME_FORMAT

from django import template
from eveuniverse.models import EveType

from metenox.models import EveTypePrice

register = template.Library()


@register.filter
def formatisk(value, magnitude: str = None) -> Optional[str]:
    """Return the formatted ISK value or None if input was invalid.

    Args:
    - magnitude: use the given magnitude to format the number, e.g. "b"
    """
    try:
        value = float(value)
    except (ValueError, TypeError):
        return None
    negative = False
    if value < 0:
        value *= -1
        negative = True
    power_map = {"t": 12, "b": 9, "m": 6, "k": 3, "": 0}
    if magnitude not in power_map:
        if value >= 10**12:
            magnitude = "t"
        elif value >= 10**9:
            magnitude = "b"
        elif value >= 10**6:
            magnitude = "m"
        elif value >= 10**3:
            magnitude = "k"
        else:
            magnitude = ""
    result = f"{value / 10 ** power_map[magnitude]:,.1f}{magnitude}"
    if negative:
        result = f"-{result}"
    return result


@register.simple_tag
def goo_price(
    moon_goo_type: EveType, amount: int = 1, monthly: bool = False
) -> Optional[str]:
    """
    Returns the stored price of a moon goo
    If amount is mentioned it will return the price of `amount` units of goo
    If monthly is added it will multiply the price by `24 * 30` to mimic the value of `amount` hourly for a month
    """
    if value := EveTypePrice.get_eve_type_price(moon_goo_type):
        if monthly:
            amount *= 24 * 30
        return formatisk(value * amount)
    return None


@register.filter
def datetime(value: dt.datetime) -> Optional[str]:
    """Render as datetime if possible or return None."""
    try:
        return value.strftime(DATETIME_FORMAT)
    except AttributeError:
        return None


@register.filter
def hours_to_days(number: int) -> str:
    """Converts a number of hours to a str indicating number of months/days/hours"""
    n_hours = number % 24
    number = number // 24
    n_days = number % 31
    n_months = number // 31
    if n_months:
        return f"{n_months} months {n_days} days {n_hours} hours"
    return f"{n_days} days {n_hours} hours"
