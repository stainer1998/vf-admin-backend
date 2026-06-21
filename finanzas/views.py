from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Case, DecimalField, Q, Sum, When
from django.db.models.functions import TruncMonth
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import AllocationFund
from .models import (
    Allocation, AlertaFinanciera, AllocationDetail, ExpenseCategory,
    FinancialTransaction, FundMovement, GastoPendiente, GastoRecurrente,
)
from .serializers import (
    AlertaFinancieraSerializer,
    ExpenseCategorySerializer,
    FinancialTransactionListSerializer,
    FinancialTransactionSerializer,
    FundMovementSerializer,
    GastoPendienteSerializer,
    GastoRecurrenteSerializer,
)


class FinancialTransactionViewSet(viewsets.ModelViewSet):
    queryset = FinancialTransaction.objects.select_related(
        "work_order", "inventory_movement"
    ).prefetch_related("allocation__details__fund").all()
    filterset_fields = ["transaction_type", "work_order"]
    search_fields = ["description"]
    ordering_fields = ["date", "amount"]
    ordering = ["-date"]

    def get_serializer_class(self):
        if self.action == "list":
            return FinancialTransactionListSerializer
        return FinancialTransactionSerializer

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Financial summary for dashboards: monthly stats + fund distribution + current month KPIs."""
        today = date.today()
        twelve_months_ago = date(today.year - 1, today.month, 1)

        # Monthly income/expense for last 12 months
        monthly_qs = (
            FinancialTransaction.objects.filter(date__gte=twelve_months_ago)
            .annotate(month=TruncMonth("date"))
            .values("month", "transaction_type")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )

        # Build a dict keyed by "YYYY-MM" with income/expense slots
        monthly_map: dict[str, dict] = {}
        for row in monthly_qs:
            key = row["month"].strftime("%Y-%m")
            if key not in monthly_map:
                monthly_map[key] = {"month": key, "income": 0, "expense": 0, "adjustment": 0}
            t = row["transaction_type"]
            if t == FinancialTransaction.INCOME:
                monthly_map[key]["income"] = float(row["total"])
            elif t == FinancialTransaction.EXPENSE:
                monthly_map[key]["expense"] = float(row["total"])
            else:
                monthly_map[key]["adjustment"] = float(row["total"])

        # Fill months with no data
        all_months = []
        cursor = twelve_months_ago
        while cursor <= today:
            key = cursor.strftime("%Y-%m")
            entry = monthly_map.get(key, {"month": key, "income": 0, "expense": 0, "adjustment": 0})
            entry["net"] = entry["income"] - entry["expense"]
            all_months.append(entry)
            # advance to next month
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)

        # Fund distribution — total credited per fund across all time
        fund_dist = []
        for fund in AllocationFund.objects.filter(is_active=True):
            total = (
                FundMovement.objects.filter(fund=fund, movement_type=FundMovement.CREDIT)
                .aggregate(t=Sum("amount"))["t"]
                or Decimal("0")
            )
            fund_dist.append({
                "fund_id": fund.pk,
                "fund_name": fund.name,
                "color": fund.color,
                "percentage": float(fund.percentage),
                "total_credited": float(total),
            })

        # Current month KPIs
        month_start = date(today.year, today.month, 1)
        month_qs = FinancialTransaction.objects.filter(date__gte=month_start)
        income_month = month_qs.filter(
            transaction_type=FinancialTransaction.INCOME
        ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
        expense_month = month_qs.filter(
            transaction_type=FinancialTransaction.EXPENSE
        ).aggregate(t=Sum("amount"))["t"] or Decimal("0")

        from trabajos.models import WorkOrder
        pending_ots = WorkOrder.objects.filter(payment_status=WorkOrder.PENDING)
        pending_count = pending_ots.count()
        pending_amount = sum(ot.amount_charged for ot in pending_ots)

        return Response({
            "monthly": all_months,
            "fund_distribution": fund_dist,
            "current_month": {
                "income": float(income_month),
                "expense": float(expense_month),
                "net": float(income_month - expense_month),
                "pending_ots_count": pending_count,
                "pending_ots_amount": float(pending_amount),
            },
        })

    @action(detail=False, methods=["get"])
    def indicadores(self, request):
        """Financial health indicators: MoM trend, avg ticket, collection rate, run rate."""
        from trabajos.models import WorkOrder, WorkOrderLine
        from django.db.models import ExpressionWrapper, F

        today = date.today()

        # ── Mes actual ──────────────────────────────────────────────────────────
        mes_actual_inicio = date(today.year, today.month, 1)

        # ── Mes anterior ────────────────────────────────────────────────────────
        if today.month == 1:
            mes_ant_inicio = date(today.year - 1, 12, 1)
        else:
            mes_ant_inicio = date(today.year, today.month - 1, 1)
        mes_ant_fin = mes_actual_inicio - timedelta(days=1)

        # ── Ingresos mes actual y anterior ──────────────────────────────────────
        def income_between(d_from, d_to):
            return float(
                FinancialTransaction.objects
                .filter(date__gte=d_from, date__lte=d_to, transaction_type=FinancialTransaction.INCOME)
                .aggregate(t=Sum("amount"))["t"] or Decimal("0")
            )

        income_actual = income_between(mes_actual_inicio, today)
        income_anterior = income_between(mes_ant_inicio, mes_ant_fin)

        variacion_mom = round(
            (income_actual - income_anterior) / income_anterior * 100, 1
        ) if income_anterior > 0 else None

        # ── Promedio ingresos 3 meses anteriores ────────────────────────────────
        meses_3m: list[float] = []
        for i in range(1, 4):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            inicio = date(y, m, 1)
            fin_m = mes_actual_inicio - timedelta(days=1) if i == 1 else date(y, m % 12 + 1, 1) - timedelta(days=1)
            # Recalculate fin_m correctly
            next_m = m + 1
            next_y = y
            if next_m > 12:
                next_m = 1
                next_y += 1
            fin_m = date(next_y, next_m, 1) - timedelta(days=1)
            meses_3m.append(income_between(inicio, fin_m))

        income_3m_avg = sum(meses_3m) / 3 if meses_3m else 0

        variacion_vs_3m = round(
            (income_actual - income_3m_avg) / income_3m_avg * 100, 1
        ) if income_3m_avg > 0 else None

        # ── Ticket promedio ──────────────────────────────────────────────────────
        def avg_ticket(ots_qs):
            tickets = [float(ot.amount_charged) for ot in ots_qs]
            return round(sum(tickets) / len(tickets), 2) if tickets else 0

        ots_pagadas_mes = WorkOrder.objects.filter(
            intake_date__gte=mes_actual_inicio,
            payment_status=WorkOrder.PAID,
        )
        ots_pagadas_ant = WorkOrder.objects.filter(
            intake_date__gte=mes_ant_inicio,
            intake_date__lte=mes_ant_fin,
            payment_status=WorkOrder.PAID,
        )

        ticket_mes = avg_ticket(ots_pagadas_mes)
        ticket_anterior = avg_ticket(ots_pagadas_ant)

        variacion_ticket = round(
            (ticket_mes - ticket_anterior) / ticket_anterior * 100, 1
        ) if ticket_anterior > 0 else None

        # ── Tasa de cobro (OTs entregadas últimos 60 días) ──────────────────────
        hace_60 = today - timedelta(days=60)
        ots_entregadas = WorkOrder.objects.filter(
            work_status=WorkOrder.DELIVERED,
            intake_date__gte=hace_60,
        )
        total_entregadas = ots_entregadas.count()
        pagadas_entregadas = ots_entregadas.filter(payment_status=WorkOrder.PAID).count()
        tasa_cobro = round(pagadas_entregadas / total_entregadas * 100, 1) if total_entregadas > 0 else 100.0
        ots_sin_cobrar = total_entregadas - pagadas_entregadas

        # ── Run rate anual ───────────────────────────────────────────────────────
        dias_transcurridos = today.day
        next_m = today.month % 12 + 1
        next_y = today.year + (1 if today.month == 12 else 0)
        dias_mes = (date(next_y, next_m, 1) - timedelta(days=1)).day
        run_rate_mensual = income_actual / dias_transcurridos * dias_mes if dias_transcurridos > 0 else 0
        run_rate_anual = round(run_rate_mensual * 12, 2)

        # ── OTs del mes ─────────────────────────────────────────────────────────
        ots_mes = WorkOrder.objects.filter(intake_date__gte=mes_actual_inicio)
        ots_mes_total = ots_mes.count()
        ots_mes_pagadas = ots_mes.filter(payment_status=WorkOrder.PAID).count()

        return Response({
            "income_mes_actual": round(income_actual, 2),
            "income_mes_anterior": round(income_anterior, 2),
            "variacion_mom": variacion_mom,
            "income_3m_avg": round(income_3m_avg, 2),
            "variacion_vs_3m": variacion_vs_3m,
            "ticket_promedio_mes": ticket_mes,
            "ticket_promedio_anterior": ticket_anterior,
            "variacion_ticket": variacion_ticket,
            "tasa_cobro": tasa_cobro,
            "ots_sin_cobrar": ots_sin_cobrar,
            "run_rate_anual": run_rate_anual,
            "ots_mes_total": ots_mes_total,
            "ots_mes_pagadas": ots_mes_pagadas,
        })

    @action(detail=False, methods=["get"])
    def reporte(self, request):
        """Financial report for a given period. tipo: resumen | fondos | transacciones."""
        import csv
        from io import StringIO
        from django.http import StreamingHttpResponse

        date_from_str = request.query_params.get("date_from")
        date_to_str = request.query_params.get("date_to")
        tipo = request.query_params.get("tipo", "resumen")

        if not date_from_str or not date_to_str:
            return Response({"error": "date_from y date_to son requeridos."}, status=400)

        try:
            from datetime import datetime
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD."}, status=400)

        base_qs = FinancialTransaction.objects.filter(date__gte=date_from, date__lte=date_to)

        if tipo == "fondos":
            result_fondos = []
            for fund in AllocationFund.objects.filter(is_active=True):
                creditos = FundMovement.objects.filter(
                    fund=fund, movement_type=FundMovement.CREDIT, date__gte=date_from, date__lte=date_to
                ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
                debitos = FundMovement.objects.filter(
                    fund=fund, movement_type=FundMovement.DEBIT, date__gte=date_from, date__lte=date_to
                ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
                movimientos = list(
                    FundMovement.objects
                    .filter(fund=fund, date__gte=date_from, date__lte=date_to)
                    .order_by("date")
                    .values("date", "movement_type", "amount", "reference")
                )
                result_fondos.append({
                    "fund_id": fund.pk,
                    "fund_name": fund.name,
                    "color": fund.color,
                    "creditos": float(creditos),
                    "debitos": float(debitos),
                    "neto": float(creditos - debitos),
                    "movimientos": [
                        {
                            "date": str(m["date"]),
                            "movement_type": m["movement_type"],
                            "amount": float(m["amount"]),
                            "reference": m["reference"],
                        }
                        for m in movimientos
                    ],
                })
            return Response({"tipo": "fondos", "date_from": date_from_str, "date_to": date_to_str, "fondos": result_fondos})

        if tipo == "transacciones":
            txs = list(
                base_qs
                .select_related("work_order")
                .order_by("date")
                .values("date", "transaction_type", "description", "amount", "work_order_id")
            )
            totals = base_qs.values("transaction_type").annotate(total=Sum("amount"))
            totals_map = {r["transaction_type"]: float(r["total"]) for r in totals}
            return Response({
                "tipo": "transacciones",
                "date_from": date_from_str,
                "date_to": date_to_str,
                "transacciones": [
                    {
                        "date": str(t["date"]),
                        "transaction_type": t["transaction_type"],
                        "description": t["description"],
                        "amount": float(t["amount"]),
                        "work_order_id": t["work_order_id"],
                    }
                    for t in txs
                ],
                "totales": {
                    "income": totals_map.get("INCOME", 0),
                    "expense": totals_map.get("EXPENSE", 0),
                    "adjustment": totals_map.get("ADJUSTMENT", 0),
                },
            })

        # tipo == "resumen" (default)
        monthly_qs = (
            base_qs
            .annotate(month=TruncMonth("date"))
            .values("month", "transaction_type")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        monthly_map: dict[str, dict] = {}
        for row in monthly_qs:
            key = row["month"].strftime("%Y-%m")
            if key not in monthly_map:
                monthly_map[key] = {"month": key, "income": 0, "expense": 0, "adjustment": 0}
            t = row["transaction_type"]
            if t == FinancialTransaction.INCOME:
                monthly_map[key]["income"] = float(row["total"])
            elif t == FinancialTransaction.EXPENSE:
                monthly_map[key]["expense"] = float(row["total"])
            else:
                monthly_map[key]["adjustment"] = float(row["total"])

        meses = []
        for m in sorted(monthly_map.values(), key=lambda x: x["month"]):
            m["net"] = m["income"] - m["expense"]
            meses.append(m)

        totales_periodo = base_qs.values("transaction_type").annotate(total=Sum("amount"))
        tm = {r["transaction_type"]: float(r["total"]) for r in totales_periodo}
        total_income = tm.get("INCOME", 0)
        total_expense = tm.get("EXPENSE", 0)
        n_meses = len(meses) or 1

        return Response({
            "tipo": "resumen",
            "date_from": date_from_str,
            "date_to": date_to_str,
            "totales": {
                "income": total_income,
                "expense": total_expense,
                "net": total_income - total_expense,
                "avg_monthly_income": round(total_income / n_meses, 2),
            },
            "por_mes": meses,
        })

    @action(detail=False, methods=["post"])
    def cash_adjustment(self, request):
        """Register a manual cash injection or withdrawal."""

        class AdjustmentSerializer(drf_serializers.Serializer):
            direction = drf_serializers.ChoiceField(choices=["INJECTION", "WITHDRAWAL"])
            amount = drf_serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
            description = drf_serializers.CharField(max_length=300)
            date = drf_serializers.DateField()
            fund = drf_serializers.IntegerField(allow_null=True, required=False, default=None)

        ser = AdjustmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        tx = FinancialTransaction.objects.create(
            transaction_type=FinancialTransaction.ADJUSTMENT,
            date=d["date"],
            amount=d["amount"],
            description=d["description"],
        )

        movement_type = FundMovement.CREDIT if d["direction"] == "INJECTION" else FundMovement.DEBIT

        if d["fund"] is not None:
            try:
                fund = AllocationFund.objects.get(pk=d["fund"], is_active=True)
            except AllocationFund.DoesNotExist:
                tx.delete()
                return Response({"fund": "Fondo no encontrado."}, status=status.HTTP_400_BAD_REQUEST)
            FundMovement.objects.create(
                fund=fund,
                movement_type=movement_type,
                amount=d["amount"],
                date=d["date"],
                reference=f"Ajuste: {d['description'][:100]}",
            )
        else:
            funds = AllocationFund.objects.filter(is_active=True)
            for fund in funds:
                fund_amount = (d["amount"] * fund.percentage / Decimal("100")).quantize(Decimal("0.01"))
                FundMovement.objects.create(
                    fund=fund,
                    movement_type=movement_type,
                    amount=fund_amount,
                    date=d["date"],
                    reference=f"Ajuste: {d['description'][:100]}",
                )

        return Response(FinancialTransactionSerializer(tx).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def proyeccion(self, request):
        """Project income and expense for current month + next 2 months based on last 3 months avg."""
        import calendar
        today = date.today()

        # ── Mes actual acumulado ──────────────────────────────────────────────
        month_start = today.replace(day=1)
        dias_mes = calendar.monthrange(today.year, today.month)[1]
        dias_transcurridos = today.day

        mes_actual_qs = FinancialTransaction.objects.filter(date__gte=month_start, date__lte=today)
        income_real = float(mes_actual_qs.filter(transaction_type="INCOME").aggregate(s=Sum("amount"))["s"] or 0)
        expense_real = float(mes_actual_qs.filter(transaction_type="EXPENSE").aggregate(s=Sum("amount"))["s"] or 0)

        income_proy = round(income_real / dias_transcurridos * dias_mes, 2) if dias_transcurridos else 0
        expense_proy = round(expense_real / dias_transcurridos * dias_mes, 2) if dias_transcurridos else 0

        # ── Promedio últimos 3 meses completos ────────────────────────────────
        three_m_data = []
        for i in range(1, 4):
            # go back i months
            y, m = today.year, today.month - i
            while m <= 0:
                m += 12
                y -= 1
            m_start = date(y, m, 1)
            m_end = date(y, m, calendar.monthrange(y, m)[1])
            qs = FinancialTransaction.objects.filter(date__gte=m_start, date__lte=m_end)
            three_m_data.append({
                "income": float(qs.filter(transaction_type="INCOME").aggregate(s=Sum("amount"))["s"] or 0),
                "expense": float(qs.filter(transaction_type="EXPENSE").aggregate(s=Sum("amount"))["s"] or 0),
            })

        avg_income = round(sum(d["income"] for d in three_m_data) / 3, 2)
        avg_expense = round(sum(d["expense"] for d in three_m_data) / 3, 2)

        # ── Próximos 2 meses ──────────────────────────────────────────────────
        months_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        proximos = []
        for i in range(1, 3):
            y, m = today.year, today.month + i
            while m > 12:
                m -= 12
                y += 1
            proximos.append({
                "label": f"{months_es[m - 1]} {str(y)[2:]}",
                "income_proyectado": avg_income,
                "expense_proyectado": avg_expense,
                "net_proyectado": round(avg_income - avg_expense, 2),
            })

        return Response({
            "mes_actual": {
                "label": f"{months_es[today.month - 1]} {str(today.year)[2:]}",
                "income_real": income_real,
                "expense_real": expense_real,
                "income_proyectado": income_proy,
                "expense_proyectado": expense_proy,
                "net_proyectado": round(income_proy - expense_proy, 2),
                "dias_transcurridos": dias_transcurridos,
                "dias_totales": dias_mes,
            },
            "proximos": proximos,
            "base_3m": {
                "avg_income": avg_income,
                "avg_expense": avg_expense,
                "avg_net": round(avg_income - avg_expense, 2),
            },
        })


class GastoRecurrenteViewSet(viewsets.ModelViewSet):
    queryset = GastoRecurrente.objects.select_related("categoria").all()
    serializer_class = GastoRecurrenteSerializer
    pagination_class = None

    @action(detail=False, methods=["get"])
    def estado_mes(self, request):
        """Lista todos los gastos recurrentes activos con flag si ya fueron aplicados este mes."""
        today = date.today()
        mes_inicio = today.replace(day=1)

        recurrentes = GastoRecurrente.objects.filter(activo=True).select_related("categoria")
        result = []
        for gr in recurrentes:
            aplicado = gr.transactions.filter(date__gte=mes_inicio).exists()
            result.append({
                "id": gr.pk,
                "nombre": gr.nombre,
                "descripcion": gr.descripcion,
                "monto": float(gr.monto),
                "categoria": gr.categoria_id,
                "categoria_nombre": gr.categoria.name if gr.categoria else None,
                "dia_del_mes": gr.dia_del_mes,
                "aplicado": aplicado,
                "vencido": today.day > gr.dia_del_mes and not aplicado,
            })
        return Response(result)

    @action(detail=True, methods=["post"])
    def aplicar(self, request, pk=None):
        """Registra el gasto recurrente como FinancialTransaction(EXPENSE) para el mes actual."""
        gr = self.get_object()
        today = date.today()
        mes_inicio = today.replace(day=1)

        if gr.transactions.filter(date__gte=mes_inicio).exists():
            return Response(
                {"detail": "Este gasto ya fue registrado en el mes actual."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tx = FinancialTransaction.objects.create(
            transaction_type=FinancialTransaction.EXPENSE,
            date=today,
            amount=gr.monto,
            description=gr.nombre,
            category=gr.categoria,
            gasto_recurrente=gr,
        )
        return Response(
            {"id": tx.pk, "description": tx.description, "amount": float(tx.amount), "date": str(tx.date)},
            status=status.HTTP_201_CREATED,
        )


class GastoPendienteViewSet(viewsets.ModelViewSet):
    queryset = GastoPendiente.objects.select_related("categoria", "work_order", "transaction").all()
    serializer_class = GastoPendienteSerializer
    filterset_fields = ["estado", "work_order"]
    ordering = ["-created_at"]
    pagination_class = None

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        """Confirma el gasto pendiente: crea FinancialTransaction(EXPENSE) y marca como CONFIRMADO."""
        gp = self.get_object()
        if gp.estado != GastoPendiente.PENDIENTE:
            return Response(
                {"detail": f"El gasto está en estado {gp.estado}, no se puede confirmar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.utils import timezone
        fecha = request.data.get("fecha") or str(date.today())

        tx = FinancialTransaction.objects.create(
            transaction_type=FinancialTransaction.EXPENSE,
            date=fecha,
            amount=gp.monto,
            description=gp.descripcion,
            category=gp.categoria,
            work_order=gp.work_order,
        )
        gp.transaction = tx
        gp.estado = GastoPendiente.CONFIRMADO
        gp.confirmado_en = timezone.now()
        gp.save(update_fields=["transaction", "estado", "confirmado_en"])

        return Response(GastoPendienteSerializer(gp).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        """Cancela el gasto pendiente sin generar transacción."""
        gp = self.get_object()
        if gp.estado != GastoPendiente.PENDIENTE:
            return Response(
                {"detail": f"El gasto está en estado {gp.estado}, no se puede cancelar."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        gp.estado = GastoPendiente.CANCELADO
        gp.save(update_fields=["estado"])
        return Response(GastoPendienteSerializer(gp).data)


class AlertaFinancieraViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Evalúa el estado financiero actual, crea/auto-resuelve alertas y las devuelve.

    GET /api/finanzas/alertas/           → evalúa + retorna alertas activas
    POST /api/finanzas/alertas/{id}/resolver/  → marca alerta como resuelta manualmente
    """
    serializer_class = AlertaFinancieraSerializer
    pagination_class = None

    def get_queryset(self):
        return AlertaFinanciera.objects.filter(activa=True)

    def list(self, request, *args, **kwargs):
        from .alertas import evaluar_alertas
        from django.utils import timezone

        hoy = date.today()
        condiciones_activas = evaluar_alertas()
        tipos_activos = {tipo for tipo, _, _ in condiciones_activas}

        # Auto-crear alertas nuevas que no existan hoy
        alertas_existentes = AlertaFinanciera.objects.filter(activa=True)
        tipos_con_alerta = set(alertas_existentes.values_list("tipo", flat=True))

        for tipo, severidad, mensaje in condiciones_activas:
            if tipo not in tipos_con_alerta:
                AlertaFinanciera.objects.create(
                    tipo=tipo,
                    severidad=severidad,
                    mensaje=mensaje,
                    fecha=hoy,
                    activa=True,
                )

        # Auto-resolver alertas cuya condición ya no se cumple
        alertas_a_resolver = alertas_existentes.exclude(tipo__in=tipos_activos)
        alertas_a_resolver.update(activa=False, resuelta_en=timezone.now())

        qs = AlertaFinanciera.objects.filter(activa=True).order_by(
            # CRITICAL primero
            "-severidad", "-fecha"
        )
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def resolver(self, request, pk=None):
        from django.utils import timezone
        alerta = self.get_object()
        if not alerta.activa:
            return Response({"detail": "La alerta ya está resuelta."}, status=status.HTTP_400_BAD_REQUEST)
        alerta.activa = False
        alerta.resuelta_en = timezone.now()
        alerta.save(update_fields=["activa", "resuelta_en"])
        return Response(self.get_serializer(alerta).data)


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    search_fields = ["name"]
    ordering = ["order", "name"]
    pagination_class = None  # always return full list


class FundMovementViewSet(viewsets.ModelViewSet):
    queryset = FundMovement.objects.select_related("fund").all()
    serializer_class = FundMovementSerializer
    filterset_fields = ["fund", "movement_type"]
    ordering_fields = ["date", "amount"]
    ordering = ["-date"]

    @action(detail=False, methods=["get"])
    def balances(self, request):
        """Return current balance for each active fund."""
        funds = AllocationFund.objects.filter(is_active=True)
        result = []
        for fund in funds:
            credits = FundMovement.objects.filter(
                fund=fund, movement_type=FundMovement.CREDIT
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            debits = FundMovement.objects.filter(
                fund=fund, movement_type=FundMovement.DEBIT
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            result.append({
                "fund_id": fund.pk,
                "fund_name": fund.name,
                "color": fund.color,
                "percentage": float(fund.percentage),
                "balance": float(credits - debits),
            })
        return Response(result)
