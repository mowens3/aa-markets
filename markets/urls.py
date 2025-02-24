"""Routes."""

from django.urls import path

from . import views

app_name = "markets"

urlpatterns = [
    path("", views.index, name="index"),
    path("modal_loader_body", views.modal_loader_body, name="modal_loader_body"),
    path("moons", views.list_moons, name="moons"),
    path("moon/<int:moon_pk>", views.moon_details, name="moon_details"),
    path("moons_data", views.MoonListJson.as_view(), name="moons_data"),
    path("moons_fdd_data", views.moons_fdd_data, name="moons_fdd_data"),
    path("add_owner", views.add_owner, name="add_owner"),
    path("markets", views.markets, name="markets"),
    path("markets/<int:markets_pk>", views.markets_details, name="markets_details"),
    path("markets_data", views.MetenoxListJson.as_view(), name="markets_data"),
    path("markets_fdd_data", views.markets_fdd_data, name="markets_fdd_data"),
    path("corporations", views.list_corporations, name="corporations"),
    path(
        "corporations_data",
        views.CorporationListJson.as_view(),
        name="corporations_data",
    ),
    path(
        "corporations_fdd_data",
        views.corporation_fdd_data,
        name="corporations_fdd_data",
    ),
    path(
        "corporations/notification/<int:corporation_pk>",
        views.corporation_notifications,
        name="notifications",
    ),
    path(
        "corporations/notification/<int:corporation_pk>/change",
        views.change_corporation_ping_settings,
        name="change_notifications",
    ),
    path(
        "corporations/notifications/<int:corporation_pk>/add_webhook",
        views.add_webhook,
        name="add_corporation_webhook",
    ),
    path(
        "corporations/notification/<int:corporation_pk>/<int:webhook_pk>/remove",
        views.remove_corporation_webhook,
        name="remove_corporation_webhook",
    ),
    path("prices", views.prices, name="prices"),
]
