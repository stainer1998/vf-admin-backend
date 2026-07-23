from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AllocationFund

User = get_user_model()


class AllocationFundAjustarPorcentajesTests(TestCase):
    def setUp(self):
        self.f1 = AllocationFund.objects.create(name="Sueldo", slug="sueldo", percentage=60, is_active=True, order=1)
        self.f2 = AllocationFund.objects.create(name="Ahorro", slug="ahorro", percentage=40, is_active=True, order=2)
        self.user = User.objects.create_user(username="tester", password="x", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_valid_adjustment_saves(self):
        resp = self.client.post(
            "/api/allocation-funds/ajustar_porcentajes/",
            data={"funds": [
                {"id": self.f1.id, "percentage": "50.00", "is_active": True},
                {"id": self.f2.id, "percentage": "50.00", "is_active": True},
            ]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.f1.refresh_from_db()
        self.f2.refresh_from_db()
        self.assertEqual(str(self.f1.percentage), "50.00")
        self.assertEqual(str(self.f2.percentage), "50.00")

    def test_invalid_adjustment_rejected_and_unchanged(self):
        resp = self.client.post(
            "/api/allocation-funds/ajustar_porcentajes/",
            data={"funds": [
                {"id": self.f1.id, "percentage": "30.00", "is_active": True},
                {"id": self.f2.id, "percentage": "50.00", "is_active": True},
            ]},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.f1.refresh_from_db()
        self.f2.refresh_from_db()
        self.assertEqual(str(self.f1.percentage), "60.00")
        self.assertEqual(str(self.f2.percentage), "40.00")

    def test_single_patch_breaking_sum_rejected(self):
        resp = self.client.patch(
            f"/api/allocation-funds/{self.f1.id}/",
            data={"percentage": "99.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.f1.refresh_from_db()
        self.assertEqual(str(self.f1.percentage), "60.00")

    def test_create_inactive_fund_allowed(self):
        resp = self.client.post(
            "/api/allocation-funds/",
            data={
                "name": "Impuestos", "slug": "impuestos", "color": "#111111",
                "order": 3, "is_active": False, "percentage": "0.00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_list_not_paginated(self):
        resp = self.client.get("/api/allocation-funds/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)
