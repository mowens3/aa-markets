from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls


class MarketsMenuItem(MenuItemHook):
    """This class ensures only authorized users will see the menu entry"""

    def __init__(self):
        # setup menu entry for sidebar
        MenuItemHook.__init__(
            self,
            "Markets",
            "fas fa-oil-well fa-fw",
            "Markets:index",
            navactive=["markets:"],
        )

    def render(self, request):
        if request.user.has_perm("markets.view_moons") or request.user.has_perm(
            "markets.view_metenoxes"
        ):
            return MenuItemHook.render(self, request)
        return ""


@hooks.register("menu_item_hook")
def register_menu():
    return MarketsMenuItem()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "markets", r"^markets/")


@hooks.register("charlink")
def register_charlink_hook():
    return "markets.thirdparty.charlink_hook"
