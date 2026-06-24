from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="inventario.InventoryMovement")
def register_inventory_expense(sender, instance, created, **kwargs):
    """Auto-create EXPENSE transaction when stock is received (ENTRY movement)."""
    if not created:
        return
    if instance.movement_type != "ENTRY":
        return

    amount = (instance.unit_cost * Decimal(instance.quantity)).quantize(Decimal("0.01"))
    if amount <= 0:
        return

    if instance.financial_transactions.exists():
        return

    from finanzas.models import FinancialTransaction

    desc = f"Compra inventario: {instance.quantity}× {instance.product.name}"
    if instance.reference:
        desc += f" ({instance.reference})"

    FinancialTransaction.objects.create(
        transaction_type=FinancialTransaction.EXPENSE,
        date=instance.date,
        amount=amount,
        description=desc[:300],
        inventory_movement=instance,
    )
