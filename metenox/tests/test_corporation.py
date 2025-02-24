from django.contrib.auth.models import User
from django.test import TestCase

from allianceauth.authentication.models import CharacterOwnership
from app_utils.testing import create_fake_user

from metenox.models import Owner
from metenox.tests.utils import create_test_holding
from metenox.views._helpers import user_has_owner_in_corp


class TestCorporation(TestCase):

    def test_user_can_modify_corp(self):
        """
        Checks if the user_can_modify_corp is working as expected
        """

        holding_corporation = create_test_holding()

        user1: User = create_fake_user(character_id=10001, character_name="Test char 1")
        user2 = create_fake_user(character_id=10002, character_name="Test char 2")

        char1_ownership, _ = CharacterOwnership.objects.get_or_create(
            character=user1.profile.main_character, user=user1, owner_hash="fake_hash"
        )

        owner1 = Owner.objects.create(
            corporation=holding_corporation, character_ownership=char1_ownership
        )

        self.assertEqual(owner1.corporation, holding_corporation)

        self.assertTrue(user_has_owner_in_corp(user1, holding_corporation))
        self.assertFalse(user_has_owner_in_corp(user2, holding_corporation))

    def test_auditor_and_superuser_can_access_all(self):
        """
        Auditors and superusers should be able to access any metenoxes
        """

        holding_corporation = create_test_holding()

        auditor_user: User = create_fake_user(
            character_id=10001,
            character_name="Test char 1",
            permissions=["metenox.auditor"],
        )

        superuser = create_fake_user(character_id=10002, character_name="Test char 2")
        superuser.is_superuser = True
        superuser.save()

        self.assertTrue(auditor_user.has_perm("metenox.auditor"))
        self.assertTrue(user_has_owner_in_corp(auditor_user, holding_corporation))
        self.assertTrue(user_has_owner_in_corp(superuser, holding_corporation))
