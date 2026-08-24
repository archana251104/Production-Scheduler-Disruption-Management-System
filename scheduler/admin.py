from django.contrib import admin

from .models import (
    Customer,
    Machine,
    Operator,
    Shift,
    Order,
    Operation,
    Changeover,
    Breakdown,
    Maintenance,
    OperatorAbsence,
    MaterialDelay,
    Rework,
    Schedule,
    ScheduledOperation,
)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "tier",
        "revenue_share",
        "late_penalty_per_hour",
        "jit_customer",
    )

    list_filter = (
        "tier",
        "jit_customer",
    )

    search_fields = (
        "name",
    )


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = (
        "machine_id",
        "name",
        "machine_type",
        "active",
    )

    list_filter = (
        "machine_type",
        "active",
    )

    search_fields = (
        "machine_id",
        "name",
    )


@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = (
        "employee_id",
        "name",
        "can_work_overtime",
        "active",
    )

    list_filter = (
        "active",
        "can_work_overtime",
    )

    search_fields = (
        "employee_id",
        "name",
    )


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "start_hour",
        "end_hour",
        "overtime",
    )

    list_filter = (
        "overtime",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer",
        "part_number",
        "quantity",
        "due_date",
        "priority",
        "status",
        "material_available",
    )

    list_filter = (
        "priority",
        "status",
        "material_available",
        "customer__tier",
    )

    search_fields = (
        "order_number",
        "part_number",
        "customer__name",
    )

    ordering = (
        "due_date",
    )


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "sequence",
        "operation_type",
        "duration_minutes",
        "setup_family",
        "required_skill",
    )

    list_filter = (
        "operation_type",
        "required_skill",
    )

    search_fields = (
        "order__order_number",
    )

    ordering = (
        "order",
        "sequence",
    )


@admin.register(Changeover)
class ChangeoverAdmin(admin.ModelAdmin):
    list_display = (
        "from_family",
        "to_family",
        "duration_minutes",
        "cost",
    )

    list_filter = (
        "from_family",
        "to_family",
    )


@admin.register(Breakdown)
class BreakdownAdmin(admin.ModelAdmin):
    list_display = (
        "machine",
        "start_time",
        "end_time",
        "reason",
        "repair_cost",
    )

    list_filter = (
        "machine",
    )

    search_fields = (
        "machine__machine_id",
        "reason",
    )


@admin.register(Maintenance)
class MaintenanceAdmin(admin.ModelAdmin):
    list_display = (
        "machine",
        "start_time",
        "end_time",
        "description",
    )

    list_filter = (
        "machine",
    )


@admin.register(OperatorAbsence)
class OperatorAbsenceAdmin(admin.ModelAdmin):
    list_display = (
        "operator",
        "start_time",
        "end_time",
        "reason",
    )

    list_filter = (
        "operator",
    )


@admin.register(MaterialDelay)
class MaterialDelayAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "expected_time",
        "actual_time",
        "reason",
    )

    list_filter = (
        "order",
    )


@admin.register(Rework)
class ReworkAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "quantity",
        "created_at",
        "reason",
        "additional_minutes",
        "completed",
    )

    list_filter = (
        "completed",
    )


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "strategy",
        "created_at",
        "overtime_cost",
        "penalty_cost",
        "changeover_cost",
        "generator_cost",
        "total_cost",
    )

    list_filter = (
        "strategy",
    )


@admin.register(ScheduledOperation)
class ScheduledOperationAdmin(admin.ModelAdmin):
    list_display = (
        "schedule",
        "operation",
        "machine",
        "operator",
        "start_time",
        "end_time",
        "setup_minutes",
        "overtime",
    )

    list_filter = (
        "machine",
        "overtime",
    )