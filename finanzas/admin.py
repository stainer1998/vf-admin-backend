from django.contrib import admin

from .models import Allocation, AllocationDetail, FinancialTransaction, FundMovement


class AllocationDetailInline(admin.TabularInline):
    model = AllocationDetail
    extra = 0
    readonly_fields = ["fund", "percentage_applied", "amount"]
    can_delete = False


class AllocationInline(admin.StackedInline):
    model = Allocation
    extra = 0
    readonly_fields = ["generated_at"]
    can_delete = False
    show_change_link = True


@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "id", "transaction_type", "date", "amount", "description", "work_order",
    ]
    list_filter = ["transaction_type"]
    search_fields = ["description"]
    readonly_fields = ["created_at"]
    date_hierarchy = "date"
    autocomplete_fields = ["work_order"]
    inlines = [AllocationInline]


@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    list_display = ["id", "transaction", "generated_at"]
    readonly_fields = ["generated_at"]
    inlines = [AllocationDetailInline]


@admin.register(FundMovement)
class FundMovementAdmin(admin.ModelAdmin):
    list_display = ["fund", "movement_type", "amount", "date", "reference"]
    list_filter = ["fund", "movement_type"]
    search_fields = ["reference"]
    date_hierarchy = "date"
