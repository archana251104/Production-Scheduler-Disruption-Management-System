from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from ..models import (
    Schedule,
    ScheduledOperation,
    Order,
    Changeover,
    Shift,
)


# ============================================================
# COST CALCULATION CONSTANTS
# ============================================================

OPERATOR_HOURLY_RATE = Decimal("250")  # INR/hour
OVERTIME_MULTIPLIER = Decimal("1.5")  # 1.5x - 2x for overtime
NIGHT_SHIFT_MULTIPLIER = Decimal("2")  # 2x for night shift
GENERATOR_HOURLY_COST = Decimal("3000")  # INR/hour (3x electricity)


# ============================================================
# OVERTIME COST CALCULATION
# ============================================================

def calculate_overtime_cost(schedule):
    """
    Calculate total overtime costs for a schedule.
    
    Overtime:
    - Night shift (22:00-06:00): 2x multiplier
    - Sunday: 1.5x multiplier
    - Additional shifts beyond 2/day: 1.5x
    """
    
    overtime_cost = Decimal("0")
    night_shift_cost = Decimal("0")
    
    for scheduled_op in schedule.scheduled_operations.all():
        
        duration_hours = (
            Decimal(scheduled_op.end_time.timestamp() -
                    scheduled_op.start_time.timestamp()) / 3600
        )
        
        # Check if operation is in overtime shift
        if scheduled_op.overtime:
            
            # Check if night shift
            if scheduled_op.start_time.hour >= 22 or (
                scheduled_op.start_time.hour < 6
            ):
                cost = (
                    duration_hours *
                    OPERATOR_HOURLY_RATE *
                    NIGHT_SHIFT_MULTIPLIER
                )
                night_shift_cost += cost
            else:
                cost = (
                    duration_hours *
                    OPERATOR_HOURLY_RATE *
                    OVERTIME_MULTIPLIER
                )
                overtime_cost += cost
    
    return {
        "overtime_cost": overtime_cost,
        "night_shift_cost": night_shift_cost,
        "total": overtime_cost + night_shift_cost,
    }


# ============================================================
# LATE DELIVERY PENALTY CALCULATION
# ============================================================

def calculate_penalty_cost(schedule):
    """
    Calculate late delivery penalties.
    
    Penalty = max(0, (actual_completion - due_date)) *
              customer.late_penalty_per_hour
    """
    
    penalty_cost = Decimal("0")
    penalty_details = []
    
    # Group scheduled operations by order
    orders_completed = {}
    
    for scheduled_op in schedule.scheduled_operations.all():
        
        order = scheduled_op.operation.order
        
        if order.id not in orders_completed:
            orders_completed[order.id] = {
                "order": order,
                "completion_time": scheduled_op.end_time,
            }
        else:
            # Keep the latest end time
            if (
                scheduled_op.end_time >
                orders_completed[order.id]["completion_time"]
            ):
                orders_completed[order.id][
                    "completion_time"
                ] = scheduled_op.end_time
    
    # Calculate penalties
    for order_data in orders_completed.values():
        
        order = order_data["order"]
        completion_time = order_data["completion_time"]
        
        if completion_time > order.due_date:
            
            hours_late = (
                (completion_time - order.due_date)
                .total_seconds() / 3600
            )
            
            penalty = (
                Decimal(hours_late) *
                order.customer.late_penalty_per_hour
            )
            
            penalty_cost += penalty
            
            penalty_details.append({
                "order": order.order_number,
                "due_date": order.due_date,
                "completion_time": completion_time,
                "hours_late": hours_late,
                "penalty": penalty,
            })
    
    return {
        "penalty_cost": penalty_cost,
        "details": penalty_details,
        "total": penalty_cost,
    }


# ============================================================
# CHANGEOVER COST CALCULATION
# ============================================================

def calculate_changeover_cost(schedule):
    """
    Calculate costs from machine changeovers.
    
    Changeover cost is stored in the Changeover model.
    """
    
    changeover_cost = Decimal("0")
    changeover_details = []
    
    # Group scheduled operations by machine
    machines_operations = {}
    
    for scheduled_op in (
        schedule.scheduled_operations.all()
        .order_by("machine_id", "start_time")
    ):
        
        machine_id = scheduled_op.machine_id
        
        if machine_id not in machines_operations:
            machines_operations[machine_id] = []
        
        machines_operations[machine_id].append(scheduled_op)
    
    # Calculate changeover costs between consecutive operations
    for machine_id, ops in machines_operations.items():
        
        for i in range(len(ops) - 1):
            
            current_op = ops[i]
            next_op = ops[i + 1]
            
            from_family = current_op.operation.setup_family
            to_family = next_op.operation.setup_family
            
            # Check if there's a gap (changeover required)
            if current_op.end_time < next_op.start_time:
                
                try:
                    changeover = Changeover.objects.get(
                        from_family=from_family,
                        to_family=to_family,
                    )
                    
                    cost = changeover.cost
                    changeover_cost += cost
                    
                    changeover_details.append({
                        "machine": current_op.machine.machine_id,
                        "from_family": from_family,
                        "to_family": to_family,
                        "changeover_time": (
                            next_op.start_time -
                            current_op.end_time
                        ),
                        "cost": cost,
                    })
                
                except Changeover.DoesNotExist:
                    pass
    
    return {
        "changeover_cost": changeover_cost,
        "details": changeover_details,
        "total": changeover_cost,
    }


# ============================================================
# GENERATOR COST CALCULATION
# ============================================================

def calculate_generator_cost(schedule, power_cut_hours=0):
    """
    Calculate diesel generator costs for power cuts.
    
    If there are unscheduled power cuts (e.g., 3 hours),
    we need to run the generator at 3x cost.
    """
    
    generator_cost = (
        Decimal(power_cut_hours) *
        GENERATOR_HOURLY_COST
    )
    
    return {
        "generator_cost": generator_cost,
        "hours": power_cut_hours,
        "total": generator_cost,
    }


# ============================================================
# TOTAL COST CALCULATION
# ============================================================

def calculate_total_cost(schedule, power_cut_hours=0):
    """
    Calculate total cost for a schedule.
    
    Total = Overtime + Penalties + Changeovers + Generator
    """
    
    overtime_calc = calculate_overtime_cost(schedule)
    penalty_calc = calculate_penalty_cost(schedule)
    changeover_calc = calculate_changeover_cost(schedule)
    generator_calc = calculate_generator_cost(schedule, power_cut_hours)
    
    total_cost = (
        overtime_calc["total"] +
        penalty_calc["total"] +
        changeover_calc["total"] +
        generator_calc["total"]
    )
    
    # Update schedule model
    schedule.overtime_cost = overtime_calc["total"]
    schedule.penalty_cost = penalty_calc["total"]
    schedule.changeover_cost = changeover_calc["total"]
    schedule.generator_cost = generator_calc["total"]
    schedule.total_cost = total_cost
    schedule.save()
    
    return {
        "overtime": overtime_calc,
        "penalties": penalty_calc,
        "changeovers": changeover_calc,
        "generator": generator_calc,
        "total_cost": total_cost,
        "breakdown": {
            "Overtime": float(overtime_calc["total"]),
            "Penalties": float(penalty_calc["total"]),
            "Changeovers": float(changeover_calc["total"]),
            "Generator": float(generator_calc["total"]),
        },
    }


# ============================================================
# ON-TIME PERFORMANCE METRICS
# ============================================================

def calculate_ontime_metrics(schedule):
    """
    Calculate on-time delivery metrics.
    """
    
    orders_completed = {}
    total_orders = set()
    late_orders = set()
    
    for scheduled_op in schedule.scheduled_operations.all():
        
        order = scheduled_op.operation.order
        total_orders.add(order.id)
        
        if order.id not in orders_completed:
            orders_completed[order.id] = {
                "order": order,
                "completion_time": scheduled_op.end_time,
            }
        else:
            if (
                scheduled_op.end_time >
                orders_completed[order.id]["completion_time"]
            ):
                orders_completed[order.id][
                    "completion_time"
                ] = scheduled_op.end_time
    
    # Check which orders are late
    for order_data in orders_completed.values():
        
        order = order_data["order"]
        completion_time = order_data["completion_time"]
        
        if completion_time > order.due_date:
            late_orders.add(order.id)
    
    on_time_count = len(total_orders) - len(late_orders)
    on_time_percent = (
        (on_time_count / len(total_orders) * 100)
        if total_orders
        else 0
    )
    
    return {
        "total_orders": len(total_orders),
        "on_time_orders": on_time_count,
        "late_orders": len(late_orders),
        "on_time_percent": on_time_percent,
    }


# ============================================================
# ROBUSTNESS METRICS
# ============================================================

def calculate_robustness_metrics(schedule):
    """
    Calculate schedule robustness against disruptions.
    
    Robustness is measured by:
    - Buffer time (gaps between operations)
    - Machine utilization (lower = more buffer)
    - Operator utilization (lower = more buffer)
    """
    
    # Calculate buffer times
    machines_ops = {}
    operators_ops = {}
    
    for scheduled_op in (
        schedule.scheduled_operations.all()
        .order_by("machine_id", "start_time")
    ):
        
        machine_id = scheduled_op.machine_id
        operator_id = scheduled_op.operator_id
        
        if machine_id not in machines_ops:
            machines_ops[machine_id] = []
        machines_ops[machine_id].append(scheduled_op)
        
        if operator_id and operator_id not in operators_ops:
            operators_ops[operator_id] = []
        if operator_id:
            operators_ops[operator_id].append(scheduled_op)
    
    total_buffer_minutes = 0
    buffer_count = 0
    
    for ops in machines_ops.values():
        for i in range(len(ops) - 1):
            buffer = (
                (ops[i + 1].start_time - ops[i].end_time)
                .total_seconds() / 60
            )
            if buffer > 0:
                total_buffer_minutes += buffer
                buffer_count += 1
    
    avg_buffer_minutes = (
        (total_buffer_minutes / buffer_count)
        if buffer_count > 0
        else 0
    )
    
    return {
        "total_buffer_minutes": total_buffer_minutes,
        "buffer_count": buffer_count,
        "avg_buffer_minutes": avg_buffer_minutes,
        "robustness_score": min(
            100,
            avg_buffer_minutes / 60
        ),  # score out of 100
    }
