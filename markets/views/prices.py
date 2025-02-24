"""Price views"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from markets.models import EveTypePrice
from markets.views.general import add_common_context


@login_required
def prices(request):
    """Displays moon goo prices"""
    goo_prices = EveTypePrice.objects.all()

    return render(
        request,
        "markets/prices.html",
        add_common_context(
            {
                "goo_prices": goo_prices,
            }
        ),
    )
