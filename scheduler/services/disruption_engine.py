from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from ortools.sat.python import cp_model

from ..models import (
    Schedule,
    ScheduledOperation,
    Operation,
    Breakdown,
    OperatorAbsence,
    MaterialDelay,
    Rework,
)
from .scheduler_engine import (
    datetime_to_minutes,
    minutes_to_datetime,
    build_shift_start_domain,
    get_machine_unavailable_intervals,
    get_operator_unavailable_intervals,
    skill_matches,
    PLANNING_DAYS,
    MINUTES_PER_DAY,
    SOLVER_TIME_LIMIT,
)
from .cost_calculator import calculate_total_cost


# ============================================================
# DISRUPTION TYPES
# ============================================================

class DisruptionType:
    MACHINE_BREAKDOWN = "MACHINE_BREAKDOWN"
    OPERATOR_ABSENCE = "OPERATOR_ABSENCE"
    MATERIAL_DELAY = "MATERIAL_DELAY"
    REWORK = "REWORK"


# ============================================================
# DISRUPTION REPRESENTATION
# ============================================================

class Disruption:
    
    def __init__(
        self,
        disruption_type,
        resource,
        start_time,
        end_time,
        description="",
    ):
        
        self.disruption_type = disruption_type
        self.resource = resource
        self.start_time = start_time
        self.end_time = end_time
        self.description = description
    
    def __str__(self):
        return (
            f"{self.disruption_type}: "
            f"{self.resource} "
            f"{self.start_time} - {self.end_time}"
        )


# ============================================================
# DISRUPTION DETECTION
# ============================================================

def detect_disruptions(current_schedule):
    """
    Detect active and upcoming disruptions.
    
    Returns list of Disruption objects that affect
    the current schedule.
    """
    
    disruptions = []
    now = timezone.now()
    
    # Machine breakdowns
    breakdowns = Breakdown.objects.filter(
        end_time__gte=now
    )
    
    for breakdown in breakdowns:
        disruptions.append(
            Disruption(
                DisruptionType.MACHINE_BREAKDOWN,
                breakdown.machine,
                breakdown.start_time,
                breakdown.end_time,
                breakdown.reason,
            )
        )
    
    # Operator absences
    absences = OperatorAbsence.objects.filter(
        end_time__gte=now
    )
    
    for absence in absences:
        disruptions.append(
            Disruption(
                DisruptionType.OPERATOR_ABSENCE,
                absence.operator,
                absence.start_time,
                absence.end_time,
                absence.reason,
            )
        )
    
    # Material delays
    material_delays = MaterialDelay.objects.filter(
        order__status__in=["OPEN", "IN_PROGRESS"]
    )
    
    for delay in material_delays:
        if delay.actual_time is None:
            # Material hasn't arrived yet
            disruptions.append(
                Disruption(
                    DisruptionType.MATERIAL_DELAY,
                    delay.order,
                    delay.expected_time,
                    delay.expected_time +
                    timedelta(hours=24),  # Assume 24h delay
                    delay.reason,
                )
            )
    
    return disruptions


# ============================================================
# IMPACT ANALYSIS
# ============================================================

def analyze_disruption_impact(
    schedule,
    disruption,
):
    """
    Analyze which operations are affected by a disruption.
    
    Returns:
        {
            "affected_operations": [...],
            "affected_orders": [...],
            "at_risk_deliveries": [...],
        }
    """
    
    affected_ops = []
    affected_orders = set()
    at_risk_deliveries = []
    
    for scheduled_op in schedule.scheduled_operations.all():
        
        # Check if operation overlaps with disruption
        if (
            scheduled_op.start_time < disruption.end_time
            and scheduled_op.end_time >
            disruption.start_time
        ):
            
            # Check if resource matches
            if disruption.disruption_type == (
                DisruptionType.MACHINE_BREAKDOWN
            ):
                
                if (
                    scheduled_op.machine ==
                    disruption.resource
                ):
                    affected_ops.append(scheduled_op)
                    affected_orders.add(
                        scheduled_op.operation.order_id
                    )
            
            elif disruption.disruption_type == (
                DisruptionType.OPERATOR_ABSENCE
            ):
                
                if (
                    scheduled_op.operator ==
                    disruption.resource
                ):
                    affected_ops.append(scheduled_op)
                    affected_orders.add(
                        scheduled_op.operation.order_id
                    )
            
            elif disruption.disruption_type == (
                DisruptionType.MATERIAL_DELAY
            ):
                
                if (
                    scheduled_op.operation.order ==
                    disruption.resource
                ):
                    affected_ops.append(scheduled_op)
                    affected_orders.add(
                        scheduled_op.operation.order_id
                    )
    
    # Identify at-risk deliveries
    from .cost_calculator import calculate_ontime_metrics
    
    for order_id in affected_orders:
        order = (
            scheduled_op.operation.order
            for scheduled_op in affected_ops
            if scheduled_op.operation.order_id ==
            order_id
        )
        try:
            order = next(
                scheduled_op.operation.order
                for scheduled_op in affected_ops
                if (
                    scheduled_op.operation.order_id
                    == order_id
                )
            )
            if order.customer.jit_customer:
                at_risk_deliveries.append(order)
        except StopIteration:
            pass
    
    return {
        "affected_operations": affected_ops,
        "affected_orders": list(affected_orders),
        "at_risk_deliveries": at_risk_deliveries,
        "operation_count": len(affected_ops),
    }


# ============================================================
# REPLANNING STRATEGY
# ============================================================

def replan_after_disruption(
    original_schedule,
    disruption,
    strategy="ONTIME",
):
    """
    Generate a new schedule after a disruption.
    
    Strategy options:
    - ONTIME: Minimize late deliveries
    - CHEAPEST: Minimize total cost
    - ROBUST: Maximize buffer time
    """
    
    # Analyze impact
    impact = analyze_disruption_impact(
        original_schedule,
        disruption,
    )
    
    print(
        f"\nDISRUPTION DETECTED: {disruption}"
    )
    print(
        f"Affected operations: "
        f"{impact['operation_count']}"
    )
    print(
        f"At-risk deliveries: "
        f"{len(impact['at_risk_deliveries'])}"
    )
    
    # Get replanning parameters
    replanning_start = timezone.now()
    horizon_minutes = PLANNING_DAYS * MINUTES_PER_DAY
    
    # Load necessary data
    affected_ops = impact["affected_operations"]
    affected_order_ids = impact["affected_orders"]
    
    # Get all relevant data
    from ..models import (
        Order,
        Machine,
        Operator,
        Shift,
    )
    
    # Start with operations that need rescheduling
    orders_to_replan = Order.objects.filter(
        id__in=affected_order_ids
    )
    
    # Get all operations for these orders
    operations_to_replan = Operation.objects.filter(
        order__in=orders_to_replan
    ).select_related("order").prefetch_related(
        "eligible_machines"
    )
    
    # Also get unaffected operations that shouldn't
    # move
    unaffected_ops = (
        ScheduledOperation.objects
        .filter(
            schedule=original_schedule
        )
        .exclude(
            id__in=[
                op.id for op in affected_ops
            ]
        )
    )
    
    # Create new schedule
    new_schedule = Schedule.objects.create(
        name=(
            f"Replanned - {original_schedule.name} "
            f"({disruption.disruption_type})"
        ),
        strategy=strategy,
    )
    
    # Copy unaffected operations
    for scheduled_op in unaffected_ops:
        ScheduledOperation.objects.create(
            schedule=new_schedule,
            operation=scheduled_op.operation,
            machine=scheduled_op.machine,
            operator=scheduled_op.operator,
            start_time=scheduled_op.start_time,
            end_time=scheduled_op.end_time,
            setup_minutes=scheduled_op.setup_minutes,
            overtime=scheduled_op.overtime,
        )
    
    # Re-optimize affected operations using CP-SAT
    # (simplified version - full implementation
    # would call the scheduler engine)
    
    machines = list(
        Machine.objects.filter(active=True)
    )
    operators = list(
        Operator.objects.filter(active=True)
    )
    shifts = list(Shift.objects.all())
    
    print(
        f"\nReplanning {len(operations_to_replan)} "
        f"operations..."
    )
    
    # For now, reschedule operations greedily
    for operation in operations_to_replan:
        
        # Find earliest available slot
        # (simplified - full version uses CP-SAT)
        
        duration = operation.duration_minutes
        eligible_machines = list(
            operation.eligible_machines.filter(
                active=True
            )
        )
        
        eligible_operators = [
            op
            for op in operators
            if skill_matches(op, operation.required_skill)
        ]
        
        if (
            not eligible_machines or
            not eligible_operators
        ):
            print(
                f"WARNING: Cannot reschedule "
                f"{operation}"
            )
            continue
        
        # Pick first available machine and operator
        best_machine = eligible_machines[0]
        best_operator = eligible_operators[0]
        
        # Schedule as early as possible
        # after disruption
        start_time = max(
            timezone.now(),
            disruption.end_time,
        )
        
        end_time = start_time + timedelta(
            minutes=duration
        )
        
        ScheduledOperation.objects.create(
            schedule=new_schedule,
            operation=operation,
            machine=best_machine,
            operator=best_operator,
            start_time=start_time,
            end_time=end_time,
            setup_minutes=0,
            overtime=False,
        )
    
    # Calculate costs for new schedule
    costs = calculate_total_cost(new_schedule)
    original_costs = calculate_total_cost(
        original_schedule
    )
    
    cost_delta = (
        costs["total_cost"] -
        original_costs["total_cost"]
    )
    
    print(
        f"\nReplanning complete!"
    )
    print(
        f"Original schedule cost: "
        f"₹{original_costs['total_cost']:.2f}"
    )
    print(
        f"New schedule cost: ₹{costs['total_cost']:.2f}"
    )
    print(
        f"Cost delta: ₹{cost_delta:.2f}"
    )
    
    return {
        "original_schedule": original_schedule,
        "new_schedule": new_schedule,
        "disruption": disruption,
        "impact": impact,
        "original_costs": original_costs,
        "new_costs": costs,
        "cost_delta": cost_delta,
    }


# ============================================================
# RECOMMENDATION ENGINE
# ============================================================

def recommend_actions(replan_result):
    """
    Generate actionable recommendations for the
    shift supervisor.
    """
    
    disruption = replan_result["disruption"]
    impact = replan_result["impact"]
    new_schedule = replan_result["new_schedule"]
    cost_delta = replan_result["cost_delta"]
    
    recommendations = []
    
    # Analyze at-risk deliveries
    if impact["at_risk_deliveries"]:
        
        at_risk = impact["at_risk_deliveries"]
        
        recommendations.append({
            "priority": "CRITICAL",
            "action": (
                "CUSTOMER ALERT"
            ),
            "details": (
                f"{len(at_risk)} JIT customers at risk: "
                f"{', '.join(o.customer.name for o in at_risk)}"
            ),
            "phone_call": (
                "Contact tier-1 customer NOW. "
                "Inform of disruption and revised ETA."
            ),
        })
    
    # Overtime decision
    if cost_delta > 0:
        
        overtime_cost = (
            replan_result["new_costs"]["overtime"]["total"]
        )
        penalty_cost = (
            replan_result["new_costs"]["penalties"]["total"]
        )
        
        if overtime_cost < penalty_cost:
            
            recommendations.append({
                "priority": "HIGH",
                "action": "AUTHORIZE OVERTIME",
                "details": (
                    f"Running overtime saves "
                    f"₹{(penalty_cost - overtime_cost):.2f} "
                    f"vs penalties"
                ),
                "phone_call": (
                    "Call operators, offer overtime rates "
                    f"for {impact['operation_count']} ops"
                ),
            })
    
    # Alternative machine routing
    if disruption.disruption_type == (
        DisruptionType.MACHINE_BREAKDOWN
    ):
        
        recommendations.append({
            "priority": "HIGH",
            "action": "REROUTE TO ALTERNATIVE MACHINE",
            "details": (
                f"Affected machine: "
                f"{disruption.resource.machine_id}. "
                f"Consider routing to similar machines."
            ),
            "phone_call": (
                f"Speak with maintenance: "
                f"Can {disruption.resource.machine_id} "
                f"be repaired in {impact['operation_count']} hours?"
            ),
        })
    
    # Material expediting
    if disruption.disruption_type == (
        DisruptionType.MATERIAL_DELAY
    ):
        
        recommendations.append({
            "priority": "CRITICAL",
            "action": "EXPEDITE MATERIAL",
            "details": (
                f"Material for {disruption.resource} "
                f"delayed. Contact supplier NOW."
            ),
            "phone_call": (
                "Call supplier: Can material arrive by "
                f"{disruption.end_time}?"
            ),
        })
    
    return recommendations
