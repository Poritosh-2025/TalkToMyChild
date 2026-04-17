from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch
from .models import (
    Child,
    ChildProfile,
    ChildSubject,
    ChildTrait,
    ChildInterest,
    ChildDislike,
)
from .services import ChildService

User = get_user_model()


class ChildModelTests(TestCase):
    """Tests for Child v2.0 models."""

    def setUp(self):
        self.parent = User.objects.create_user(
            email="parent@test.com", full_name="Test Parent", password="testpass123"
        )

    def test_create_child_with_all_attributes(self):
        data = {
            "name": "Abdullah",
            "age": 9,
            "email": "abdullah@family.com",
            "password": "StrongPass123!",
            "subjects": ["Math", "English", "Physics"],
            "traits": ["Creative", "Curious"],
            "interests": ["Space", "Dinosaurs"],
            "dislikes": ["Loud noises", "Broccoli"],
        }

        child = ChildService.create_child(self.parent, data)

        self.assertEqual(child.name, "Abdullah")
        self.assertEqual(child.age, 9)
        self.assertEqual(child.subjects.count(), 3)
        self.assertEqual(child.traits.count(), 2)
        self.assertEqual(child.interests.count(), 2)
        self.assertEqual(child.dislikes.count(), 2)

        # Check credentials
        self.assertEqual(child.credentials.email, "abdullah@family.com")
        self.assertTrue(child.credentials.check_password("StrongPass123!"))

    def test_child_email_must_be_unique(self):
        data1 = {
            "name": "Child One",
            "age": 8,
            "email": "same@email.com",
            "password": "Pass123!",
        }
        ChildService.create_child(self.parent, data1)

        data2 = {
            "name": "Child Two",
            "age": 9,
            "email": "same@email.com",
            "password": "Pass123!",
        }

        with self.assertRaises(ValueError) as context:
            ChildService.create_child(self.parent, data2)
        self.assertIn("already in use", str(context.exception))

    def test_max_children_limit(self):
        for i in range(10):
            ChildService.create_child(
                self.parent,
                {
                    "name": f"Child {i}",
                    "age": 5,
                    "email": f"child{i}@test.com",
                    "password": "Pass123!",
                },
            )

        with self.assertRaises(ValueError) as context:
            ChildService.create_child(
                self.parent,
                {
                    "name": "Eleventh",
                    "age": 6,
                    "email": "eleventh@test.com",
                    "password": "Pass123!",
                },
            )
        self.assertIn("Maximum", str(context.exception))

    def test_update_subjects_replaces_existing(self):
        child = ChildService.create_child(
            self.parent,
            {
                "name": "Test",
                "age": 8,
                "email": "test@test.com",
                "password": "Pass123!",
                "subjects": ["Math", "Science"],
            },
        )

        self.assertEqual(child.subjects.count(), 2)

        ChildService.update_subjects(child, ["English", "History"])

        self.assertEqual(child.subjects.count(), 2)
        subject_names = [s.name for s in child.subjects.all()]
        self.assertIn("English", subject_names)
        self.assertIn("History", subject_names)
        self.assertNotIn("Math", subject_names)

    def test_duplicate_subject_names_deduplicated(self):
        child = ChildService.create_child(
            self.parent,
            {
                "name": "Test",
                "age": 8,
                "email": "test@test.com",
                "password": "Pass123!",
            },
        )

        ChildService.update_subjects(child, ["Math", "MATH", "math", "Math"])

        self.assertEqual(child.subjects.count(), 1)
        self.assertEqual(child.subjects.first().name, "Math")

    def test_has_active_calls_property(self):
        child = ChildService.create_child(
            self.parent,
            {
                "name": "Call Child",
                "age": 10,
                "email": "call@test.com",
                "password": "Pass123!",
            },
        )
        # No calls app, so should return False
        self.assertFalse(child.has_active_calls)


class ChildAPITests(TestCase):
    """Tests for Child API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.parent = User.objects.create_user(
            email="parent@test.com",
            full_name="Test Parent",
            password="pass123",
            is_email_verified=True,
        )
        self.client.force_authenticate(user=self.parent)
        self.list_url = reverse("child-list-create")

    def test_create_child_api(self):
        data = {
            "name": "Abdullah",
            "age": 9,
            "email": "abdullah@family.com",
            "password": "StrongPass123!",
            "subjects": ["Math", "English"],
            "traits": ["Creative"],
        }

        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["name"], "Abdullah")
        self.assertEqual(len(response.data["data"]["subjects"]), 2)

    def test_create_child_missing_password(self):
        data = {"name": "Abdullah", "age": 9, "email": "abdullah@family.com"}

        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 400)

    def test_update_credentials(self):
        child = ChildService.create_child(
            self.parent,
            {
                "name": "Test",
                "age": 8,
                "email": "test@test.com",
                "password": "Pass123!",
            },
        )

        url = reverse("child-credentials", kwargs={"child_id": child.id})
        data = {"email": "newemail@test.com"}

        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, 200)

        child.refresh_from_db()
        self.assertEqual(child.credentials.email, "newemail@test.com")

    def test_get_profile_intelligence_parent(self):
        child = ChildService.create_child(
            self.parent,
            {
                "name": "Intel Child",
                "age": 10,
                "email": "intel@test.com",
                "password": "Pass123!",
                "subjects": ["AI", "Robotics"],
                "traits": ["Curious"],
                "interests": ["Space"],
                "dislikes": ["Loud"],
            },
        )

        url = reverse("child-profile-intelligence", kwargs={"child_id": child.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("prompt_context", response.data["data"])
        self.assertIn("Curious", response.data["data"]["prompt_context"])

    def test_get_profile_intelligence_internal(self):
        """Test internal service access with X-Internal-Service-Key header."""
        from django.conf import settings

        child = ChildService.create_child(
            self.parent,
            {
                "name": "Internal Child",
                "age": 8,
                "email": "internal@test.com",
                "password": "Pass123!",
            },
        )

        url = reverse("child-profile-intelligence", kwargs={"child_id": child.id})
        headers = {
            "X-Internal-Service-Key": getattr(
                settings, "INTERNAL_SERVICE_KEY", "test-key"
            )
        }
        response = self.client.get(url, **headers)

        # Internal key should allow access even without authentication
        self.assertEqual(response.status_code, 200)

    def test_delete_child_without_active_calls(self):
        child = ChildService.create_child(
            self.parent,
            {
                "name": "Delete Me",
                "age": 8,
                "email": "delete@test.com",
                "password": "Pass123!",
            },
        )

        url = reverse("child-detail", kwargs={"child_id": child.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)
        child.refresh_from_db()
        self.assertFalse(child.is_active)

    def test_child_login(self):
        child = ChildService.create_child(
            self.parent,
            {
                "name": "Login Child",
                "age": 8,
                "email": "login@test.com",
                "password": "LoginPass123!",
            },
        )

        # Test the authenticate method directly
        authenticated = ChildService.authenticate_child(
            "login@test.com", "LoginPass123!"
        )
        self.assertIsNotNone(authenticated)
        self.assertEqual(authenticated.id, child.id)

        # Wrong password
        wrong = ChildService.authenticate_child("login@test.com", "WrongPass!")
        self.assertIsNone(wrong)
