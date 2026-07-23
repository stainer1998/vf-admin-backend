from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Product, ProductCategory, PurchaseOrder, PurchaseOrderLine, Supplier

User = get_user_model()


class ReceiveAllPurchaseOrderTests(TestCase):
    def setUp(self):
        category = ProductCategory.objects.create(name="Repuestos")
        supplier = Supplier.objects.create(name="Proveedor Test")
        self.product_a = Product.objects.create(
            name="Producto A", category=category, purchase_price=1000, sale_price=1500
        )
        self.product_b = Product.objects.create(
            name="Producto B", category=category, purchase_price=2000, sale_price=3000
        )
        self.po = PurchaseOrder.objects.create(
            supplier=supplier, date="2026-01-01", status=PurchaseOrder.CONFIRMED
        )
        self.line_a = PurchaseOrderLine.objects.create(
            purchase_order=self.po, product=self.product_a, unit_cost=1000, quantity_ordered=10
        )
        self.line_b = PurchaseOrderLine.objects.create(
            purchase_order=self.po, product=self.product_b, unit_cost=2000, quantity_ordered=5
        )
        self.user = User.objects.create_user(username="tester", password="x", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_receive_all_marks_order_received_and_fills_lines(self):
        resp = self.client.post(f"/api/purchase-orders/{self.po.id}/receive-all/", format="json")
        self.assertEqual(resp.status_code, 200, resp.content)

        self.po.refresh_from_db()
        self.line_a.refresh_from_db()
        self.line_b.refresh_from_db()

        self.assertEqual(self.po.status, PurchaseOrder.RECEIVED)
        self.assertEqual(self.line_a.quantity_received, self.line_a.quantity_ordered)
        self.assertEqual(self.line_b.quantity_received, self.line_b.quantity_ordered)
        self.assertEqual(self.product_a.stock, 10)
        self.assertEqual(self.product_b.stock, 5)

    def test_receive_all_respects_partial_progress(self):
        self.line_a.quantity_received = 4
        self.line_a.save()

        resp = self.client.post(f"/api/purchase-orders/{self.po.id}/receive-all/", format="json")
        self.assertEqual(resp.status_code, 200, resp.content)

        self.line_a.refresh_from_db()
        self.assertEqual(self.line_a.quantity_received, 10)
        self.assertEqual(self.product_a.stock, 6)  # only the pending 6 were moved

    def test_receive_all_rejected_when_draft(self):
        self.po.status = PurchaseOrder.DRAFT
        self.po.save()
        resp = self.client.post(f"/api/purchase-orders/{self.po.id}/receive-all/", format="json")
        self.assertEqual(resp.status_code, 400)

    def test_receive_all_rejected_when_nothing_pending(self):
        self.line_a.quantity_received = self.line_a.quantity_ordered
        self.line_a.save()
        self.line_b.quantity_received = self.line_b.quantity_ordered
        self.line_b.save()

        resp = self.client.post(f"/api/purchase-orders/{self.po.id}/receive-all/", format="json")
        self.assertEqual(resp.status_code, 400)

    def test_financial_expense_created_on_receive_all(self):
        from finanzas.models import FinancialTransaction

        self.client.post(f"/api/purchase-orders/{self.po.id}/receive-all/", format="json")
        total_expense = FinancialTransaction.objects.filter(
            transaction_type=FinancialTransaction.EXPENSE
        ).count()
        self.assertEqual(total_expense, 2)  # one per line's InventoryMovement
