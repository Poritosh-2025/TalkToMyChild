from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock
from .models import Child
from .services import ChildService

User = get_user_model()


class ChildModelTests(TestCase):
    """Tests for Child model."""

    def setUp(self):
        self.parent = User.objects.create_user(
            email="parent@test.com", full_name="Test Parent", password="testpass123"
        )

    def test_create_child(self):
        child = Child.objects.create(parent=self.parent, name="Test Child", age=8)
        self.assertEqual(child.name, "Test Child")
        self.assertEqual(child.age, 8)
        self.assertTrue(child.is_active)
        self.assertIsNotNone(child.id)

    def test_soft_delete(self):
        child = Child.objects.create(parent=self.parent, name="Test Child", age=8)
        child.soft_delete()
        self.assertFalse(child.is_active)

    def test_unique_name_per_parent_active(self):
        Child.objects.create(parent=self.parent, name="Same Name", age=5)

        with self.assertRaises(Exception):
            Child.objects.create(parent=self.parent, name="Same Name", age=6)

    def test_same_name_different_parent_allowed(self):
        parent2 = User.objects.create_user(
            email="parent2@test.com", full_name="Parent Two", password="testpass123"
        )
        Child.objects.create(parent=self.parent, name="Common Name", age=5)
        child2 = Child.objects.create(parent=parent2, name="Common Name", age=6)
        self.assertIsNotNone(child2)


class ChildAPITests(TestCase):
    """Tests for Child API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.parent = User.objects.create_user(
            email="parent@test.com",
            full_name="Test Parent",
            password="testpass123",
            is_email_verified=True,
        )
        self.client.force_authenticate(user=self.parent)
        self.list_url = reverse("child-list-create")

    def test_create_child_success(self):
        data = {"name": "Abdullah", "age": 9}
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["name"], "Abdullah")

    def test_create_child_duplicate_name(self):
        Child.objects.create(parent=self.parent, name="Abdullah", age=9)
        data = {"name": "Abdullah", "age": 10}
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already exists", response.data["message"])

    def test_create_child_invalid_age(self):
        data = {"name": "Child", "age": 18}
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 400)

    def test_list_children(self):
        Child.objects.create(parent=self.parent, name="Child 1", age=5)
        Child.objects.create(parent=self.parent, name="Child 2", age=7)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["count"], 2)

    def test_list_children_only_active(self):
        child = Child.objects.create(parent=self.parent, name="Active", age=5)
        inactive = Child.objects.create(parent=self.parent, name="Inactive", age=6)
        inactive.soft_delete()

        response = self.client.get(self.list_url)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"][0]["name"], "Active")

    def test_get_child_detail(self):
        child = Child.objects.create(parent=self.parent, name="Detail Child", age=8)
        url = reverse("child-detail", kwargs={"child_id": child.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["name"], "Detail Child")

    def test_get_child_detail_not_owner(self):
        other_parent = User.objects.create_user(
            email="other@test.com", full_name="Other Parent", password="testpass123"
        )
        child = Child.objects.create(parent=other_parent, name="Other Child", age=8)
        url = reverse("child-detail", kwargs={"child_id": child.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_update_child(self):
        child = Child.objects.create(parent=self.parent, name="Original", age=5)
        url = reverse("child-detail", kwargs={"child_id": child.id})
        data = {"name": "Updated Name"}

        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, 200)
        child.refresh_from_db()
        self.assertEqual(child.name, "Updated Name")

    def test_delete_child_soft(self):
        child = Child.objects.create(parent=self.parent, name="To Delete", age=5)
        url = reverse("child-detail", kwargs={"child_id": child.id})

        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)
        child.refresh_from_db()
        self.assertFalse(child.is_active)

    def test_max_children_limit(self):
        # Create 10 children
        for i in range(10):
            Child.objects.create(parent=self.parent, name=f"Child {i}", age=5)

        # Try to create 11th
        data = {"name": "Eleventh", "age": 6}
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Maximum", response.data["message"])


class ChildServiceTests(TestCase):
    """Tests for ChildService business logic."""

    def setUp(self):
        self.parent = User.objects.create_user(
            email="parent@test.com", full_name="Test Parent", password="testpass123"
        )

    def test_create_child_success(self):
        child = ChildService.create_child(self.parent, "Test", 10)
        self.assertEqual(child.name, "Test")
        self.assertEqual(child.age, 10)

    def test_create_child_max_limit(self):
        for i in range(10):
            ChildService.create_child(self.parent, f"Child {i}", 5)

        with self.assertRaises(ValueError) as context:
            ChildService.create_child(self.parent, "Eleventh", 6)
        self.assertIn("Maximum", str(context.exception))

    def test_create_child_duplicate_name_case_insensitive(self):
        ChildService.create_child(self.parent, "Test Name", 5)

        with self.assertRaises(ValueError) as context:
            ChildService.create_child(self.parent, "test name", 6)
        self.assertIn("already exists", str(context.exception))

    def test_update_child_name(self):
        child = ChildService.create_child(self.parent, "Original", 5)
        updated = ChildService.update_child(child, name="New Name")
        self.assertEqual(updated.name, "New Name")

    def test_update_child_age(self):
        child = ChildService.create_child(self.parent, "Child", 5)
        updated = ChildService.update_child(child, age=10)
        self.assertEqual(updated.age, 10)

    @patch("apps.children.services.S3ClientManager")
    def test_generate_avatar_presigned_url(self, mock_s3_manager):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://fake-url.com"
        mock_s3_manager.get_client.return_value = mock_client

        child = ChildService.create_child(self.parent, "Avatar Child", 5)
        result = ChildService.generate_avatar_presigned_url(child)

        self.assertIn("upload_url", result)
        self.assertIn("avatar_key", result)
        self.assertEqual(result["expires_in"], 300)

    def test_validate_avatar_key_belongs_to_child(self):
        from apps.children.utils import validate_avatar_key_belongs_to_child

        child_id = "12345678-1234-5678-1234-567812345678"
        valid_key = f"avatars/{child_id}/abc123.jpg"
        invalid_key = f"avatars/wrong-id/abc123.jpg"

        self.assertTrue(validate_avatar_key_belongs_to_child(valid_key, child_id))
        self.assertFalse(validate_avatar_key_belongs_to_child(invalid_key, child_id))


class ChildPermissionsTests(TestCase):
    """Tests for permission classes."""

    def setUp(self):
        self.client = APIClient()
        self.parent = User.objects.create_user(
            email="parent@test.com", full_name="Parent", password="pass123"
        )
        self.other_parent = User.objects.create_user(
            email="other@test.com", full_name="Other", password="pass123"
        )
        self.child = Child.objects.create(parent=self.parent, name="Test Child", age=5)

    def test_owner_can_access(self):
        self.client.force_authenticate(user=self.parent)
        url = reverse("child-detail", kwargs={"child_id": self.child.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_non_owner_cannot_access(self):
        self.client.force_authenticate(user=self.other_parent)
        url = reverse("child-detail", kwargs={"child_id": self.child.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_cannot_access(self):
        self.client.force_authenticate(user=None)
        url = reverse("child-detail", kwargs={"child_id": self.child.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)
