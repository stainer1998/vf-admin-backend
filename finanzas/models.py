from django.db import models


class ExpenseCategory(models.Model):
    RECURRENTE = "RECURRENTE"
    VARIABLE = "VARIABLE"
    REPUESTO = "REPUESTO"
    TYPE_CHOICES = [
        (RECURRENTE, "Recurrente"),
        (VARIABLE, "Variable"),
        (REPUESTO, "Repuesto"),
    ]

    name = models.CharField(max_length=100, unique=True)
    category_type = models.CharField(max_length=12, choices=TYPE_CHOICES, default=VARIABLE)
    color = models.CharField(max_length=7, default="#6366f1")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


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
    category = models.ForeignKey(
        ExpenseCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
    )
    gasto_recurrente = models.ForeignKey(
        "GastoRecurrente",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
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


class AlertaFinanciera(models.Model):
    MARGEN_BRUTO_BAJO = "MARGEN_BRUTO_BAJO"
    GASTOS_ALTOS = "GASTOS_ALTOS"
    AHORRO_BAJO = "AHORRO_BAJO"
    CAJA_BAJA = "CAJA_BAJA"
    CAIDA_MOM = "CAIDA_MOM"
    IMPUESTOS_INSUFICIENTES = "IMPUESTOS_INSUFICIENTES"
    TICKET_CAYENDO = "TICKET_CAYENDO"
    OTS_PENDIENTES = "OTS_PENDIENTES"

    TIPO_CHOICES = [
        (MARGEN_BRUTO_BAJO, "Margen bruto bajo"),
        (GASTOS_ALTOS, "Gastos operacionales altos"),
        (AHORRO_BAJO, "Reserva de ahorro baja"),
        (CAJA_BAJA, "Cobertura caja operacional baja"),
        (CAIDA_MOM, "Caída de ingresos consecutiva"),
        (IMPUESTOS_INSUFICIENTES, "Fondo impuestos insuficiente"),
        (TICKET_CAYENDO, "Ticket promedio cayendo"),
        (OTS_PENDIENTES, "OTs pendientes de cobro > 15 días"),
    ]

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    SEVERIDAD_CHOICES = [(INFO, "Info"), (WARNING, "Advertencia"), (CRITICAL, "Crítico")]

    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    severidad = models.CharField(max_length=10, choices=SEVERIDAD_CHOICES)
    mensaje = models.CharField(max_length=500)
    fecha = models.DateField()
    activa = models.BooleanField(default=True)
    resuelta_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha", "severidad"]

    def __str__(self):
        estado = "activa" if self.activa else "resuelta"
        return f"[{self.severidad}] {self.get_tipo_display()} ({estado})"


class GastoRecurrente(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.CharField(max_length=300, blank=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    categoria = models.ForeignKey(
        ExpenseCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="gastos_recurrentes",
        limit_choices_to={"category_type": ExpenseCategory.RECURRENTE},
    )
    dia_del_mes = models.PositiveSmallIntegerField(
        default=1,
        help_text="Día sugerido de pago (1-28)",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["dia_del_mes", "nombre"]

    def __str__(self):
        return f"{self.nombre} (${self.monto}/mes)"


class GastoPendiente(models.Model):
    PENDIENTE = "PENDIENTE"
    CONFIRMADO = "CONFIRMADO"
    CANCELADO = "CANCELADO"
    ESTADO_CHOICES = [
        (PENDIENTE, "Pendiente"),
        (CONFIRMADO, "Confirmado"),
        (CANCELADO, "Cancelado"),
    ]

    descripcion = models.CharField(max_length=300)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    categoria = models.ForeignKey(
        ExpenseCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="gastos_pendientes",
    )
    work_order = models.ForeignKey(
        "trabajos.WorkOrder",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="gastos_pendientes",
    )
    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default=PENDIENTE)
    transaction = models.OneToOneField(
        "FinancialTransaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="gasto_pendiente",
    )
    fecha_estimada = models.DateField()
    confirmado_en = models.DateTimeField(null=True, blank=True)
    notas = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.descripcion} ${self.monto} [{self.estado}]"


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
