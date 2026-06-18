from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="trabajos.WorkOrder")
def register_payment_income(sender, instance, created, **kwargs):
    """Auto-create FinancialTransaction when a WorkOrder is marked PAID."""
    if instance.payment_status != "PAID":
        return
    if instance.financial_transactions.exists():
        return

    from core.models import AllocationFund
    from finanzas.models import (
        Allocation,
        AllocationDetail,
        FinancialTransaction,
        FundMovement,
    )

    amount = instance.amount_charged
    if amount <= 0:
        return

    tx = FinancialTransaction.objects.create(
        transaction_type=FinancialTransaction.INCOME,
        date=instance.delivery_date or instance.intake_date,
        amount=amount,
        description=f"Pago OT {instance.number}",
        work_order=instance,
    )

    allocation = Allocation.objects.create(transaction=tx)

    funds = AllocationFund.objects.filter(is_active=True)
    for fund in funds:
        fund_amount = (amount * fund.percentage / Decimal("100")).quantize(Decimal("0.01"))
        AllocationDetail.objects.create(
            allocation=allocation,
            fund=fund,
            percentage_applied=fund.percentage,
            amount=fund_amount,
        )
        FundMovement.objects.create(
            fund=fund,
            movement_type=FundMovement.CREDIT,
            amount=fund_amount,
            date=tx.date,
            reference=instance.number,
        )
