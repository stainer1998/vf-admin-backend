from django.db import models


class FinancialTransaction(models.Model):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    ADJUSTMENT = "ADJUSTMENT"
    TYPE_CHOICES = [(INCOME, "Income"), (EXPENSE, "Expense"), (ADJUSTMENT, "Adjustment")]

    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=300)
    work_order = models.ForeignKey(
        "trabajos.WorkOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="financial_transactions",
    )
    inventory_movement = models.ForeignKey(
        "inventario.InventoryMovement",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="financial_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} ${self.amount} ({self.date})"


class Allocation(models.Model):
    transaction = models.OneToOneField(
        FinancialTransaction, on_delete=models.CASCADE, related_name="allocation"
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Allocation for {self.transaction}"


class AllocationDetail(models.Model):
    allocation = models.ForeignKey(
        Allocation, on_delete=models.CASCADE, related_name="details"
    )
    fund = models.ForeignKey(
        "core.AllocationFund",
        on_delete=models.PROTECT,
        related_name="allocation_details",
    )
    percentage_applied = models.DecimalField(max_digits=5, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.fund} — ${self.amount}"


class FundMovement(models.Model):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
    TYPE_CHOICES = [(CREDIT, "Credit"), (DEBIT, "Debit")]

    fund = models.ForeignKey(
        "core.AllocationFund", on_delete=models.PROTECT, related_name="movements"
    )
    movement_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    reference = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return (
            f"{self.get_movement_type_display()} ${self.amount}"
            f" → {self.fund} ({self.date})"
        )
