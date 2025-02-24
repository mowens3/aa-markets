from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls


class MetenoxMenuItem(MenuItemHook):
    """This class ensures only authorized users will see the menu entry"""

    def __init__(self):
        # setup menu entry for sidebar
        MenuItemHook.__init__(
            self,
            "Metenox",
            "fas fa-oil-well fa-fw",
            "metenox:index",
            navactive=["metenox:"],
        )

    def render(self, request):
        if request.user.has_perm("metenox.view_moons") or request.user.has_perm(
            "metenox.view_metenoxes"
        ):
            return MenuItemHook.render(self, request)
        return ""


@hooks.register("menu_item_hook")
def register_menu():
    return MetenoxMenuItem()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "metenox", r"^metenox/")


@hooks.register("charlink")
def register_charlink_hook():
    return "metenox.thirdparty.charlink_hook"
