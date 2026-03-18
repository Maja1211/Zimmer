from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse

from app.models import Account, UserProfile, UserPreferences, Matches, Swipes
from app.views import UserType

"""
Author: Jovana Ceganjac 2022/0423
"""

class SwipeAndMatchesTests(TestCase):
    """
    Django integration tests for swipe algorithm, swipe actions and matches view.
    Creates two verified users and simulates swipes using the Django test client.
    """

    @classmethod
    def setUpTestData(cls):
        # Viewer
        cls.acc1 = Account.objects.create(
            email="swipe_user1@example.com",
            passwordhash="x",
            status="ACTIVE",
        )
        cls.profile1 = UserProfile.objects.create(
            idacc=cls.acc1,
            jmbg="1111111111111",
            phonenumber="+381600000001",
            name="User",
            surname="One",
            dateofbirth="2000-01-01",
            budget=Decimal("300"),
            isVerified=True,
            hashousing=False,
            sex="female",
            smoker="no",
            party="no",
            partner="no",
        )
        cls.prefs1 = UserPreferences.objects.create(
            idacc=cls.profile1,
            preferred_sex="doesnt_matter",
            minimumage=18,
            maximumage=99,
            hashousing="doesnt_matter",
        )

        # Candidate
        cls.acc2 = Account.objects.create(
            email="swipe_user2@example.com",
            passwordhash="x",
            status="ACTIVE",
        )
        cls.profile2 = UserProfile.objects.create(
            idacc=cls.acc2,
            jmbg="2222222222222",
            phonenumber="+381600000002",
            name="User",
            surname="Two",
            dateofbirth="1999-01-01",
            budget=Decimal("320"),
            isVerified=True,
            hashousing=False,
            sex="female",
            smoker="no",
            party="no",
            partner="no",
        )
        cls.prefs2 = UserPreferences.objects.create(
            idacc=cls.profile2,
            preferred_sex="doesnt_matter",
            minimumage=18,
            maximumage=99,
            hashousing="doesnt_matter",
        )

    def _login_as(self, client: Client, account: Account, user_type: UserType = UserType.VERIFIED):
        session = client.session
        session["user_id"] = account.idacc
        session["user_type"] = user_type.value
        session.save()

    def test_swipe_view_loads_for_verified_user(self):
        client = Client()
        self._login_as(client, self.acc1, UserType.VERIFIED)
        response = client.get(reverse("swipe"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("profiles_json", response.context)

    def test_swipe_action_creates_swipe_and_match_on_mutual_like(self):
        client = Client()
        # user1 likes user2
        self._login_as(client, self.acc1, UserType.VERIFIED)
        url = reverse("swipe_action")
        response = client.post(
            url,
            data='{"target_id": %d, "decision": "like"}' % self.profile2.idacc_id,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Swipes.objects.filter(idkor1=self.profile1, idkor2=self.profile2, decision="LIKE").exists()
        )

        # user2 likes user1 -> should create a match
        client2 = Client()
        self._login_as(client2, self.acc2, UserType.VERIFIED)
        response2 = client2.post(
            url,
            data='{"target_id": %d, "decision": "like"}' % self.profile1.idacc_id,
            content_type="application/json",
        )
        self.assertEqual(response2.status_code, 200)

        # Matches entry must exist (ids ordered)
        id1, id2 = sorted([self.profile1.idacc_id, self.profile2.idacc_id])
        self.assertTrue(Matches.objects.filter(idkor1_id=id1, idkor2_id=id2).exists())

    def test_matches_view_lists_created_match(self):
        # Pre-create a match
        id1, id2 = sorted([self.profile1.idacc_id, self.profile2.idacc_id])
        Matches.objects.create(idkor1_id=id1, idkor2_id=id2)

        client = Client()
        self._login_as(client, self.acc1, UserType.VERIFIED)
        response = client.get(reverse("matches"))
        self.assertEqual(response.status_code, 200)
        matched_users = response.context.get("matched_users") or []
        self.assertGreaterEqual(len(matched_users), 1)
        ids = {u["id"] for u in matched_users}
        self.assertIn(self.profile2.idacc_id, ids)

