# Create your tests here.
from django.utils import timezone
from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from unittest.mock import patch

User = get_user_model()


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse("register")
        self.verify_url = reverse("verify-otp")
        self.login_url = reverse("login")

    @patch("apps.authentication.services.send_otp_email.delay")
    def test_register_success(self, mock_send):
        data = {
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertFalse(user.is_email_verified)

    def test_register_password_mismatch(self):
        data = {
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "StrongPass123!",
            "confirm_password": "Different123!",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("confirm_password", response.data)

    @patch("apps.authentication.services.send_otp_email.delay")
    def test_verify_otp_success(self, mock_send):
        # Register first
        reg_data = {
            "full_name": "Test",
            "email": "test@example.com",
            "password": "Pass123!",
            "confirm_password": "Pass123!",
        }
        self.client.post(self.register_url, reg_data)
        user = User.objects.get(email="test@example.com")
        # Simulate OTP (in real test we'd get from email, but we can create manually)
        from apps.authentication.models import OTP
        import random

        otp_code = f"{random.randint(100000, 999999)}"
        OTP.objects.create(
            user=user,
            code=otp_code,
            otp_type="REGISTER_VERIFY",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        verify_data = {
            "email": user.email,
            "otp": otp_code,
            "otp_type": "REGISTER_VERIFY",
        }
        response = self.client.post(self.verify_url, verify_data, format="json")
        print(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("access_token" in response.data["data"])
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_login_with_email_password(self):
        # Create verified user
        User.objects.create_user(
            full_name="Test User",
            email="test@example.com",
            password="Pass123!",
            is_email_verified=True,
        )
        data = {"email": "test@example.com", "password": "Pass123!"}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("access_token" in response.data["data"])
        self.assertIn("refresh_token", response.cookies)
