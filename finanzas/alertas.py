"""
Evaluación de alertas financieras.

Cada función `_check_*` retorna (tipo, severidad, mensaje) si la condición
se cumple, o None si no hay alerta.

La función principal `evaluar_alertas()` devuelve la lista de alertas
activas según el estado financiero actual.
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum


def _income_between(model, d_from, d_to):
    return float(
        model.objects.filter(
            date__gte=d_from, date__lte=d_to, transaction_type=model.INCOME
        ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
    )


def _expense_between(model, d_from, d_to):
    return float(
        model.objects.filter(
            date__gte=d_from, date__lte=d_to, transaction_type=model.EXPENSE
        ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
    )


def _fund_balance(FundMovement, slug):
    try:
        from core.models import AllocationFund
        fund = AllocationFund.objects.get(slug=slug, is_active=True)
    except Exception:
        return None
    credits = FundMovement.objects.filter(
        fund=fund, movement_type=FundMovement.CREDIT
    ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
    debits = FundMovement.objects.filter(
        fund=fund, movement_type=FundMovement.DEBIT
    ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
    return float(credits - debits)


def evaluar_alertas():
    """Evalúa todas las condiciones y devuelve lista de (tipo, severidad, mensaje)."""
    from .models import AlertaFinanciera, FinancialTransaction, FundMovement
    from trabajos.models import WorkOrder

    today = date.today()
    A = AlertaFinanciera

    mes_inicio = today.replace(day=1)
    mes_dias = calendar.monthrange(today.year, today.month)[1]
    mes_fin = today.replace(day=mes_dias)

    income_mes = _income_between(FinancialTransaction, mes_inicio, today)
    expense_mes = _expense_between(FinancialTransaction, mes_inicio, today)

    alertas = []

    # ── 1. Margen bruto < 30% ─────────────────────────────────────────────────
    if income_mes > 0:
        margen = (income_mes - expense_mes) / income_mes * 100
        if margen < 30:
            alertas.append((
                A.MARGEN_BRUTO_BAJO,
                A.CRITICAL,
                f"Margen bruto del mes: {margen:.1f}% (mínimo esperado 30%). "
                f"Ingresos {_fmt(income_mes)}, Gastos {_fmt(expense_mes)}.",
            ))

    # ── 2. Gastos > 60% del ingreso ──────────────────────────────────────────
    if income_mes > 0:
        ratio_gastos = expense_mes / income_mes * 100
        if ratio_gastos > 60:
            alertas.append((
                A.GASTOS_ALTOS,
                A.WARNING,
                f"Gastos operacionales representan el {ratio_gastos:.1f}% de los ingresos este mes "
                f"(límite sugerido 60%). Gastos: {_fmt(expense_mes)}.",
            ))

    # ── 3. Reserva ahorro < 3% del ingreso mensual ───────────────────────────
    balance_ahorro = _fund_balance(FundMovement, "ahorro")
    if balance_ahorro is not None and income_mes > 0:
        ratio_ahorro = balance_ahorro / income_mes * 100
        if ratio_ahorro < 3:
            alertas.append((
                A.AHORRO_BAJO,
                A.WARNING,
                f"Balance fondo Ahorro ({_fmt(balance_ahorro)}) es solo el {ratio_ahorro:.1f}% "
                f"del ingreso mensual. Se recomienda mantener al menos 3%.",
            ))

    # ── 4. Cobertura caja operacional < 1 mes ────────────────────────────────
    balance_ops = _fund_balance(FundMovement, "operaciones")
    # Calcular gasto promedio últimos 3 meses
    tres_m_gastos = []
    for i in range(1, 4):
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12
            y -= 1
        m_ini = date(y, m, 1)
        m_fin = date(y, m, calendar.monthrange(y, m)[1])
        tres_m_gastos.append(_expense_between(FinancialTransaction, m_ini, m_fin))
    avg_gasto_mensual = sum(tres_m_gastos) / 3 if tres_m_gastos else 0

    if balance_ops is not None and avg_gasto_mensual > 0:
        cobertura = balance_ops / avg_gasto_mensual
        if cobertura < 1:
            alertas.append((
                A.CAJA_BAJA,
                A.CRITICAL,
                f"Fondo Operaciones ({_fmt(balance_ops)}) cubre solo {cobertura:.1f} mes(es) "
                f"de gastos (promedio {_fmt(avg_gasto_mensual)}/mes). Se recomienda ≥ 1 mes.",
            ))

    # ── 5. Caída MoM > 10% en dos meses consecutivos ─────────────────────────
    variaciones = []
    for i in range(1, 3):  # mes anterior y el previo
        y_curr, m_curr = today.year, today.month - i
        while m_curr <= 0:
            m_curr += 12
            y_curr -= 1
        y_prev, m_prev = y_curr, m_curr - 1
        while m_prev <= 0:
            m_prev += 12
            y_prev -= 1

        ini_curr = date(y_curr, m_curr, 1)
        fin_curr = date(y_curr, m_curr, calendar.monthrange(y_curr, m_curr)[1])
        ini_prev = date(y_prev, m_prev, 1)
        fin_prev = date(y_prev, m_prev, calendar.monthrange(y_prev, m_prev)[1])

        inc_curr = _income_between(FinancialTransaction, ini_curr, fin_curr)
        inc_prev = _income_between(FinancialTransaction, ini_prev, fin_prev)
        if inc_prev > 0:
            variaciones.append((inc_curr - inc_prev) / inc_prev * 100)
        else:
            variaciones.append(None)

    if len(variaciones) == 2 and all(v is not None and v < -10 for v in variaciones):
        alertas.append((
            A.CAIDA_MOM,
            A.WARNING,
            f"Ingresos cayeron {variaciones[1]:.1f}% y {variaciones[0]:.1f}% en los últimos dos meses. "
            "Revisar captación de clientes y carga de trabajo.",
        ))

    # ── 6. Fondo impuestos < 15% del ingreso acumulado del año ───────────────
    balance_impuestos = _fund_balance(FundMovement, "impuestos")
    anio_inicio = date(today.year, 1, 1)
    income_ytd = _income_between(FinancialTransaction, anio_inicio, today)
    if balance_impuestos is not None and income_ytd > 0:
        impuestos_esperado = income_ytd * 0.15
        if balance_impuestos < impuestos_esperado * 0.9:  # tolerancia 10%
            alertas.append((
                A.IMPUESTOS_INSUFICIENTES,
                A.WARNING,
                f"Fondo Impuestos ({_fmt(balance_impuestos)}) está por debajo del 15% "
                f"del ingreso acumulado del año ({_fmt(impuestos_esperado)} esperado). "
                "Verificar antes de la próxima declaración.",
            ))

    # ── 7. Ticket promedio cayó > 15% vs mes anterior ────────────────────────
    if today.month == 1:
        y_ant, m_ant = today.year - 1, 12
    else:
        y_ant, m_ant = today.year, today.month - 1
    ini_ant = date(y_ant, m_ant, 1)
    fin_ant = date(y_ant, m_ant, calendar.monthrange(y_ant, m_ant)[1])

    ots_mes = list(WorkOrder.objects.filter(intake_date__gte=mes_inicio, payment_status=WorkOrder.PAID))
    ots_ant = list(WorkOrder.objects.filter(intake_date__gte=ini_ant, intake_date__lte=fin_ant, payment_status=WorkOrder.PAID))

    if ots_mes and ots_ant:
        ticket_mes = sum(float(ot.amount_charged) for ot in ots_mes) / len(ots_mes)
        ticket_ant = sum(float(ot.amount_charged) for ot in ots_ant) / len(ots_ant)
        if ticket_ant > 0:
            variacion_ticket = (ticket_mes - ticket_ant) / ticket_ant * 100
            if variacion_ticket < -15:
                alertas.append((
                    A.TICKET_CAYENDO,
                    A.WARNING,
                    f"Ticket promedio bajó {abs(variacion_ticket):.1f}% vs mes anterior "
                    f"({_fmt(ticket_mes)} vs {_fmt(ticket_ant)}). "
                    "Revisar mix de servicios y precios.",
                ))

    # ── 8. OTs pendientes de cobro > 15 días ─────────────────────────────────
    limite_fecha = today - timedelta(days=15)
    ots_vencidas = WorkOrder.objects.filter(
        payment_status=WorkOrder.PENDING,
        intake_date__lte=limite_fecha,
    ).count()
    if ots_vencidas > 0:
        alertas.append((
            A.OTS_PENDIENTES,
            A.WARNING,
            f"{ots_vencidas} OT(s) llevan más de 15 días sin cobrar. "
            "Gestionar cobro pendiente.",
        ))

    return alertas


def _fmt(v):
    return f"${int(round(v)):,}".replace(",", ".")
