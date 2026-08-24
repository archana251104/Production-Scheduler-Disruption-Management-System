from django.shortcuts import render
from django.views.generic import ListView, DetailView
from django.http import JsonResponse

from .models import Schedule, ScheduledOperation, Order

from .services.cost_calculator import (
    calculate_total_cost,
    calculate_ontime_metrics,
    calculate_robustness_metrics,
)


# ============================================================
# SCHEDULE LIST VIEW
# ============================================================

class ScheduleListView(ListView):
    
    model = Schedule
    template_name = "scheduler/schedule_list.html"
    context_object_name = "schedules"
    paginate_by = 10

    def get_queryset(self):
        return Schedule.objects.order_by(
            "-created_at"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add cost and metrics for each schedule
        for schedule in context["schedules"]:
            costs = calculate_total_cost(schedule)
            ontime = calculate_ontime_metrics(schedule)
            
            schedule.total_cost_display = (
                f"₹{costs['total_cost']:,.2f}"
            )
            schedule.ontime_percent = (
                f"{ontime['on_time_percent']:.1f}%"
            )
        
        return context


# ============================================================
# SCHEDULE DETAIL VIEW
# ============================================================

class ScheduleDetailView(DetailView):
    
    model = Schedule
    template_name = "scheduler/schedule_detail.html"
    context_object_name = "schedule"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        schedule = self.object

        # Get all scheduled operations, grouped by machine
        operations = (
            schedule.scheduled_operations.all()
            .select_related(
                "machine",
                "operator",
                "operation__order",
            )
            .order_by("machine_id", "start_time")
        )

        # Group by machine
        machine_schedule = {}
        
        for op in operations:
            
            machine_id = op.machine_id
            
            if machine_id not in machine_schedule:
                machine_schedule[machine_id] = []
            
            machine_schedule[machine_id].append(op)

        context["machine_schedule"] = machine_schedule

        # Calculate costs
        costs = calculate_total_cost(schedule)
        context["costs"] = costs

        # Calculate metrics
        ontime = calculate_ontime_metrics(schedule)
        context["ontime_metrics"] = ontime

        robustness = calculate_robustness_metrics(schedule)
        context["robustness_metrics"] = robustness

        # Order completion times
        orders_completed = {}
        
        for op in operations:
            
            order = op.operation.order
            order_id = order.id
            
            if order_id not in orders_completed:
                orders_completed[order_id] = {
                    "order": order,
                    "completion_time": op.end_time,
                }
            else:
                if (
                    op.end_time >
                    orders_completed[order_id][
                        "completion_time"
                    ]
                ):
                    orders_completed[order_id][
                        "completion_time"
                    ] = op.end_time

        context["orders_completed"] = list(
            orders_completed.values()
        )

        return context


# ============================================================
# SUPERVISOR DASHBOARD
# ============================================================

def supervisor_dashboard(request):
    
    # Get the most recent schedule
    latest_schedule = (
        Schedule.objects
        .order_by("-created_at")
        .first()
    )

    context = {}

    if latest_schedule:
        
        # Get today's operations
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        today_start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        today_end = today_start + timedelta(days=1)

        today_ops = (
            latest_schedule.scheduled_operations
            .filter(
                start_time__gte=today_start,
                start_time__lt=today_end,
            )
            .select_related(
                "machine",
                "operator",
                "operation__order",
            )
            .order_by("start_time")
        )

        context["today_operations"] = today_ops

        # Summary metrics
        costs = calculate_total_cost(latest_schedule)
        ontime = calculate_ontime_metrics(
            latest_schedule
        )
        robustness = (
            calculate_robustness_metrics(latest_schedule)
        )

        context["schedule"] = latest_schedule
        context["total_cost"] = (
            f"₹{costs['total_cost']:,.2f}"
        )
        context["ontime_percent"] = (
            f"{ontime['on_time_percent']:.1f}%"
        )
        context["robustness_score"] = (
            f"{robustness['robustness_score']:.1f}"
        )

        # At-risk orders (due soon)
        all_ops = (
            latest_schedule.scheduled_operations
            .all()
            .select_related(
                "operation__order__customer"
            )
        )

        orders_by_id = {}
        
        for op in all_ops:
            order = op.operation.order
            if order.id not in orders_by_id:
                orders_by_id[order.id] = {
                    "order": order,
                    "completion_time": op.end_time,
                }
            else:
                if (
                    op.end_time >
                    orders_by_id[order.id][
                        "completion_time"
                    ]
                ):
                    orders_by_id[order.id][
                        "completion_time"
                    ] = op.end_time

        at_risk = [
            oc
            for oc in orders_by_id.values()
            if oc["completion_time"] >
            oc["order"].due_date
        ]

        context["at_risk_orders"] = sorted(
            at_risk,
            key=lambda x: (
                x["order"].due_date
            ),
        )[:5]

    context["all_schedules"] = (
        Schedule.objects.order_by(
            "-created_at"
        )[:5]
    )

    return render(
        request,
        "scheduler/supervisor_dashboard.html",
        context,
    )


# ============================================================
# API ENDPOINTS
# ============================================================

def schedule_operations_json(request, schedule_id):
    
    from django.core.serializers.json import (
        DjangoJSONEncoder,
    )
    import json

    schedule = Schedule.objects.get(id=schedule_id)

    operations = (
        schedule.scheduled_operations
        .all()
        .select_related(
            "machine",
            "operator",
            "operation__order",
        )
        .order_by("start_time")
    )

    data = []

    for op in operations:
        
        data.append({
            "id": op.id,
            "machine": op.machine.machine_id,
            "operator": (
                op.operator.name if op.operator else "N/A"
            ),
            "order": op.operation.order.order_number,
            "operation": (
                op.operation.operation_type
            ),
            "start_time": op.start_time.isoformat(),
            "end_time": op.end_time.isoformat(),
            "duration_minutes": (
                op.operation.duration_minutes
            ),
        })

    return JsonResponse(
        {"operations": data},
        encoder=DjangoJSONEncoder,
    )

