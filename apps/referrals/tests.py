from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from unittest.mock import patch
from datetime import timedelta
from .models import Referral, UserReferralCode
from .services import ReferralService

User = get_user_model()


class ReferralModelTests(TestCase):
    """Tests for Referral models."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="user1@test.com", full_name="User One", password="pass123"
        )
        self.user2 = User.objects.create_user(
            email="user2@test.com", full_name="User Two", password="pass123"
        )

    def test_create_referral_code(self):
        code = ReferralService.create_referral_code(self.user1)
        self.assertIsNotNone(code.code)
        self.assertEqual(len(code.code), 8)
        self.assertTrue(code.code.isalnum())
        self.assertTrue(code.code.isupper())

    def test_referral_code_unique(self):
        code1 = ReferralService.create_referral_code(self.user1)
        code2 = ReferralService.create_referral_code(self.user2)
        self.assertNotEqual(code1.code, code2.code)

    def test_referral_code_auto_created_on_user_creation(self):
        new_user = User.objects.create_user(
            email="new@test.com", full_name="New User", password="pass123"
        )
        self.assertIsNotNone(UserReferralCode.objects.filter(user=new_user).first())

    def test_create_referral_invitation(self):
        referral = ReferralService.create_referral_invitation(
            self.user1, "friend@test.com"
        )
        self.assertEqual(referral.referrer, self.user1)
        self.assertEqual(referral.referred_email, "friend@test.com")
        self.assertEqual(referral.status, "PENDING")
        self.assertFalse(referral.credits_issued)
        self.assertIsNotNone(referral.expires_at)

    def test_email_normalization_on_create(self):
        referral = ReferralService.create_referral_invitation(
            self.user1, "FRIEND@TEST.COM"
        )
        self.assertEqual(referral.referred_email, "friend@test.com")

    def test_cannot_create_duplicate_pending_invitation(self):
        ReferralService.create_referral_invitation(self.user1, "friend@test.com")
        with self.assertRaises(ValueError):
            ReferralService.create_referral_invitation(self.user1, "friend@test.com")

    def test_cannot_invite_already_registered_email(self):
        with self.assertRaises(ValueError) as context:
            ReferralService.create_referral_invitation(self.user1, self.user2.email)
        self.assertIn("already registered", str(context.exception))

    def test_referral_expiry(self):
        referral = Referral.objects.create(
            referrer=self.user1,
            referred_email="friend@test.com",
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.assertTrue(referral.is_expired())
        self.assertFalse(referral.can_be_redeemed())


class ReferralRedemptionTests(TestCase):
    """Tests for referral redemption flow."""

    def setUp(self):
        self.client = APIClient()
        self.referrer = User.objects.create_user(
            email="referrer@test.com", full_name="Referrer User", password="pass123"
        )
        self.referee = User.objects.create_user(
            email="referee@test.com", full_name="Referee User", password="pass123"
        )
        self.referral_code = ReferralService.create_referral_code(self.referrer)

    @patch("apps.referrals.services.ReferralService._add_credits")
    def test_redeem_referral_success(self, mock_add_credits):
        mock_add_credits.return_value = 2

        result = ReferralService.redeem_referral(self.referral_code.code, self.referee)

        self.assertEqual(result["referrer_credits_added"], 2)
        self.assertEqual(result["referee_credits_added"], 2)
        self.assertEqual(result["referrer_name"], "Referrer User")

        # Check referral record
        referral = Referral.objects.get(
            referrer=self.referrer, referred_email=self.referee.email
        )
        self.assertEqual(referral.status, "COMPLETED")
        self.assertTrue(referral.credits_issued)
        self.assertIsNotNone(referral.redeemed_at)

    def test_redeem_self_referral_fails(self):
        with self.assertRaises(ValueError) as context:
            ReferralService.redeem_referral(self.referral_code.code, self.referrer)
        self.assertIn("own referral code", str(context.exception))

    def test_redeem_expired_referral_fails(self):
        # Create expired referral
        Referral.objects.create(
            referrer=self.referrer,
            referred_email=self.referee.email,
            expires_at=timezone.now() - timedelta(days=1),
            status="PENDING",
        )

        with self.assertRaises(ValueError) as context:
            ReferralService.redeem_referral(self.referral_code.code, self.referee)
        self.assertIn("expired", str(context.exception))

    def test_cannot_redeem_twice(self):
        ReferralService.redeem_referral(self.referral_code.code, self.referee)

        # Try to redeem again
        with self.assertRaises(ValueError) as context:
            ReferralService.redeem_referral(self.referral_code.code, self.referee)
        self.assertIn("already been used", str(context.exception))


class ReferralAPITests(TestCase):
    """Tests for Referral API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@test.com",
            full_name="Test User",
            password="pass123",
            is_email_verified=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_get_my_referral_code(self):
        url = reverse("my-referral-code")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIn("referral_code", response.data["data"])
        self.assertIn("share_links", response.data["data"])
        self.assertIn("whatsapp", response.data["data"]["share_links"])

    def test_get_referral_stats(self):
        # Create some referrals
        ReferralService.create_referral_invitation(self.user, "friend1@test.com")
        ReferralService.create_referral_invitation(self.user, "friend2@test.com")

        url = reverse("referral-stats")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["total_referrals"], 2)
        self.assertEqual(response.data["data"]["pending"], 2)
        self.assertIn("conversion_rate", response.data["data"])

    def test_get_referral_list(self):
        ReferralService.create_referral_invitation(self.user, "friend1@test.com")
        ReferralService.create_referral_invitation(self.user, "friend2@test.com")

        url = reverse("referral-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["count"], 2)
        self.assertIn("days_until_expiry", response.data["data"]["results"][0])

    def test_get_referral_list_with_status_filter(self):
        referral = ReferralService.create_referral_invitation(
            self.user, "friend1@test.com"
        )

        url = reverse("referral-list")
        response = self.client.get(url, {"status": "PENDING"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["count"], 1)

    def test_create_referral_invitation(self):
        url = reverse("referral-invite")
        data = {"email": "newfriend@test.com"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["email"], "newfriend@test.com")

    def test_create_referral_invitation_self_fails(self):
        url = reverse("referral-invite")
        data = {"email": self.user.email}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot send", response.data["message"])

    def test_create_referral_invitation_already_registered_fails(self):
        other_user = User.objects.create_user(
            email="existing@test.com", full_name="Existing", password="pass123"
        )
        url = reverse("referral-invite")
        data = {"email": other_user.email}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already registered", response.data["message"])

    def test_check_referral_eligibility(self):
        code_obj = ReferralService.create_referral_code(self.user)

        url = reverse("referral-check")
        response = self.client.get(
            url, {"code": code_obj.code, "email": "newuser@test.com"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["eligible"])
        self.assertEqual(response.data["data"]["referrer_name"], self.user.full_name)

    def test_check_referral_eligibility_self_fails(self):
        code_obj = ReferralService.create_referral_code(self.user)

        url = reverse("referral-check")
        response = self.client.get(
            url, {"code": code_obj.code, "email": self.user.email}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["data"]["eligible"])
        self.assertIn("own referral", response.data["data"]["message"])

    def test_check_referral_eligibility_invalid_code(self):
        url = reverse("referral-check")
        response = self.client.get(
            url, {"code": "INVALID99", "email": "newuser@test.com"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["data"]["eligible"])

    def test_unauthenticated_access_fails(self):
        self.client.force_authenticate(user=None)
        url = reverse("my-referral-code")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)


class ReferralExpiryTaskTests(TestCase):
    """Tests for referral expiry task."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@test.com", full_name="Test User", password="pass123"
        )

    def test_expire_pending_referrals(self):
        # Create expired referral
        Referral.objects.create(
            referrer=self.user,
            referred_email="expired@test.com",
            expires_at=timezone.now() - timedelta(days=1),
            status="PENDING",
        )
        # Create valid referral
        Referral.objects.create(
            referrer=self.user,
            referred_email="valid@test.com",
            expires_at=timezone.now() + timedelta(days=7),
            status="PENDING",
        )

        expired_count = ReferralService.expire_pending_referrals()
        self.assertEqual(expired_count, 1)

        # Verify expired referral status changed
        expired = Referral.objects.get(referred_email="expired@test.com")
        self.assertEqual(expired.status, "EXPIRED")

        # Verify valid referral unchanged
        valid = Referral.objects.get(referred_email="valid@test.com")
        self.assertEqual(valid.status, "PENDING")

    def test_no_expiry_for_completed_referrals(self):
        Referral.objects.create(
            referrer=self.user,
            referred_email="completed@test.com",
            expires_at=timezone.now() - timedelta(days=1),
            status="COMPLETED",
        )

        expired_count = ReferralService.expire_pending_referrals()
        self.assertEqual(expired_count, 0)


class ReferralCacheTests(TestCase):
    """Tests for referral caching."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@test.com", full_name="Test User", password="pass123"
        )
        ReferralService.create_referral_code(self.user)

    def test_stats_are_cached(self):
        from django.core.cache import cache

        # Clear cache
        cache.clear()

        # First call - should hit database
        stats1 = ReferralService.get_referral_stats_for_user(self.user)

        # Second call - should hit cache
        stats2 = ReferralService.get_referral_stats_for_user(self.user)

        self.assertEqual(stats1["total_referrals"], stats2["total_referrals"])

    def test_cache_invalidated_on_new_referral(self):
        from django.core.cache import cache

        cache.clear()

        # Get stats to populate cache
        ReferralService.get_referral_stats_for_user(self.user)

        # Create new referral
        ReferralService.create_referral_invitation(self.user, "friend@test.com")

        # Cache should be invalidated
        stats = ReferralService.get_referral_stats_for_user(self.user)
        self.assertEqual(stats["total_referrals"], 1)
