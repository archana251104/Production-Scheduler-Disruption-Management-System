from datetime import timedelta

from django.utils import timezone
from ortools.sat.python import cp_model

from .models import (
    Order,
    Operation,
    Machine,
    Operator,
    Shift,
    Breakdown,
    Maintenance,
    OperatorAbsence,
    Schedule,
    ScheduledOperation,
)


# ============================================================
# CONFIGURATION
# ============================================================

PLANNING_DAYS = 14
MINUTES_PER_DAY = 24 * 60
SOLVER_TIME_LIMIT = 30


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def datetime_to_minutes(dt, planning_start):
    """
    Convert datetime into integer minutes from planning_start.
    """

    if timezone.is_naive(dt):
        dt = timezone.make_aware(
            dt,
            timezone.get_current_timezone(),
        )

    return int(
        (dt - planning_start).total_seconds() // 60
    )


def minutes_to_datetime(minutes, planning_start):
    """
    Convert integer minutes back into datetime.
    """

    return planning_start + timedelta(
        minutes=minutes
    )


def skill_matches(operator, required_skill):
    """
    Check whether an operator has the required skill.

    Example:
        required_skill = "GRINDING"

        operator.skills =
        ["TURNING", "GRINDING"]
    """

    if not required_skill:
        return True

    required = str(
        required_skill
    ).strip().lower()

    skills = operator.skills or []

    return any(
        str(skill).strip().lower() == required
        for skill in skills
    )


# ============================================================
# SHIFT WINDOWS
# ============================================================

def build_shift_start_domain(
    planning_start,
    horizon_minutes,
    duration_minutes,
    shifts,
):
    """
    Build valid start-time ranges.

    An operation must fit completely inside one shift.
    """

    ranges = []

    for day in range(PLANNING_DAYS):

        day_start = planning_start + timedelta(
            days=day
        )

        for shift in shifts:

            shift_start = day_start.replace(
                hour=shift.start_hour,
                minute=0,
                second=0,
                microsecond=0,
            )

            # Handle overnight shifts.
            if shift.end_hour <= shift.start_hour:

                shift_end = day_start + timedelta(
                    days=1,
                    hours=shift.end_hour,
                )

            else:

                shift_end = day_start.replace(
                    hour=shift.end_hour,
                    minute=0,
                    second=0,
                    microsecond=0,
                )

            start_minute = int(
                (
                    shift_start - planning_start
                ).total_seconds() // 60
            )

            end_minute = int(
                (
                    shift_end - planning_start
                ).total_seconds() // 60
            )

            latest_start = (
                end_minute - duration_minutes
            )

            # Keep only intervals inside planning horizon.
            start_minute = max(
                0,
                start_minute,
            )

            latest_start = min(
                horizon_minutes - duration_minutes,
                latest_start,
            )

            if latest_start >= start_minute:

                ranges.append(
                    [
                        start_minute,
                        latest_start,
                    ]
                )

    return ranges


# ============================================================
# MACHINE UNAVAILABLE PERIODS
# ============================================================

def get_machine_unavailable_intervals(
    machine,
    planning_start,
):
    """
    Get machine breakdown + maintenance intervals.

    Returns:
        [(start_minutes, end_minutes), ...]
    """

    intervals = []

    breakdowns = Breakdown.objects.filter(
        machine=machine
    )

    for breakdown in breakdowns:

        start = datetime_to_minutes(
            breakdown.start_time,
            planning_start,
        )

        end = datetime_to_minutes(
            breakdown.end_time,
            planning_start,
        )

        intervals.append(
            (start, end)
        )

    maintenance_windows = Maintenance.objects.filter(
        machine=machine
    )

    for maintenance in maintenance_windows:

        start = datetime_to_minutes(
            maintenance.start_time,
            planning_start,
        )

        end = datetime_to_minutes(
            maintenance.end_time,
            planning_start,
        )

        intervals.append(
            (start, end)
        )

    return intervals


# ============================================================
# OPERATOR UNAVAILABLE PERIODS
# ============================================================

def get_operator_unavailable_intervals(
    operator,
    planning_start,
):
    """
    Get operator absence intervals.
    """

    intervals = []

    absences = OperatorAbsence.objects.filter(
        operator=operator
    )

    for absence in absences:

        start = datetime_to_minutes(
            absence.start_time,
            planning_start,
        )

        end = datetime_to_minutes(
            absence.end_time,
            planning_start,
        )

        intervals.append(
            (start, end)
        )

    return intervals


# ============================================================
# MAIN SCHEDULER
# ============================================================

def generate_baseline_schedule(
    name="Baseline 2-Week Schedule",
):
    """
    Generate a valid 2-week production schedule.

    Currently handles:

    - Open orders
    - Operation precedence
    - Machine eligibility
    - Operator eligibility
    - Machine capacity
    - Operator capacity
    - Shift windows
    - Machine breakdowns
    - Machine maintenance
    - Operator absences
    - Material availability
    - Due dates
    """

    print("\n========================================")
    print("SRIDHAR PRECISION WORKS")
    print("BASELINE SCHEDULER")
    print("========================================")

    # ========================================================
    # 1. PLANNING START
    # ========================================================

    planning_start = timezone.now()

    planning_start = planning_start.replace(
        minute=0,
        second=0,
        microsecond=0,
    )

    horizon_minutes = (
        PLANNING_DAYS * MINUTES_PER_DAY
    )

    print(
        f"Planning start : {planning_start}"
    )

    print(
        f"Horizon        : {PLANNING_DAYS} days"
    )

    # ========================================================
    # 2. LOAD DATA
    # ========================================================

    orders = list(
        Order.objects.filter(
            status__in=[
                "OPEN",
                "IN_PROGRESS",
            ]
        ).select_related(
            "customer"
        )
    )

    operations = list(
        Operation.objects.filter(
            order__in=orders
        ).select_related(
            "order"
        ).prefetch_related(
            "eligible_machines"
        )
    )

    machines = list(
        Machine.objects.filter(
            active=True
        )
    )

    operators = list(
        Operator.objects.filter(
            active=True
        )
    )

    shifts = list(
        Shift.objects.all()
    )

    print(
        f"Orders         : {len(orders)}"
    )

    print(
        f"Operations     : {len(operations)}"
    )

    print(
        f"Machines       : {len(machines)}"
    )

    print(
        f"Operators      : {len(operators)}"
    )

    print(
        f"Shifts         : {len(shifts)}"
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    if not orders:
        raise ValueError(
            "No OPEN or IN_PROGRESS orders found."
        )

    if not operations:
        raise ValueError(
            "No operations found for open orders."
        )

    if not machines:
        raise ValueError(
            "No active machines found."
        )

    if not operators:
        raise ValueError(
            "No active operators found."
        )

    if not shifts:
        raise ValueError(
            "No shifts found."
        )

    # ========================================================
    # 3. CREATE CP-SAT MODEL
    # ========================================================

    model = cp_model.CpModel()

    # ========================================================
    # 4. OPERATION VARIABLES
    # ========================================================

    operation_variables = {}

    for operation in operations:

        duration = operation.duration_minutes

        start_domain_ranges = (
            build_shift_start_domain(
                planning_start=planning_start,
                horizon_minutes=horizon_minutes,
                duration_minutes=duration,
                shifts=shifts,
            )
        )

        if not start_domain_ranges:

            raise ValueError(
                f"Operation {operation} cannot fit "
                f"inside any configured shift."
            )

        start_domain = (
            cp_model.Domain.FromIntervals(
                start_domain_ranges
            )
        )

        start = model.new_int_var_from_domain(
            start_domain,
            f"op_{operation.id}_start",
        )

        end = model.new_int_var(
            0,
            horizon_minutes,
            f"op_{operation.id}_end",
        )

        model.add(
            end == start + duration
        )

        operation_variables[
            operation.id
        ] = {
            "operation": operation,
            "start": start,
            "end": end,
            "duration": duration,
            "assignments": [],
        }

    # ========================================================
    # 5. MACHINE + OPERATOR ASSIGNMENTS
    # ========================================================

    machine_intervals = {
        machine.id: []
        for machine in machines
    }

    operator_intervals = {
        operator.id: []
        for operator in operators
    }

    for operation in operations:

        operation_data = (
            operation_variables[
                operation.id
            ]
        )

        start = operation_data["start"]
        end = operation_data["end"]
        duration = operation_data["duration"]

        eligible_machines = list(
            operation.eligible_machines.filter(
                active=True
            )
        )

        eligible_operators = [
            operator
            for operator in operators
            if skill_matches(
                operator,
                operation.required_skill,
            )
        ]

        if not eligible_machines:

            raise ValueError(
                f"No eligible machine for {operation}"
            )

        if not eligible_operators:

            raise ValueError(
                f"No eligible operator for {operation}. "
                f"Required skill: "
                f"{operation.required_skill}"
            )

        assignment_variables = []

        # ----------------------------------------------------
        # MACHINE / OPERATOR COMBINATIONS
        # ----------------------------------------------------

        for machine in eligible_machines:

            machine_unavailable = (
                get_machine_unavailable_intervals(
                    machine,
                    planning_start,
                )
            )

            for operator in eligible_operators:

                operator_unavailable = (
                    get_operator_unavailable_intervals(
                        operator,
                        planning_start,
                    )
                )

                assignment_name = (
                    f"op_{operation.id}"
                    f"_m{machine.id}"
                    f"_o{operator.id}"
                )

                assigned = model.new_bool_var(
                    f"{assignment_name}_assigned"
                )

                interval = (
                    model.new_optional_interval_var(
                        start,
                        duration,
                        end,
                        assigned,
                        f"{assignment_name}_interval",
                    )
                )

                machine_intervals[
                    machine.id
                ].append(interval)

                operator_intervals[
                    operator.id
                ].append(interval)

                assignment_variables.append(
                    {
                        "machine": machine,
                        "operator": operator,
                        "assigned": assigned,
                        "interval": interval,
                        "machine_unavailable":
                            machine_unavailable,
                        "operator_unavailable":
                            operator_unavailable,
                    }
                )

        # Exactly one machine/operator pair.
        model.add_exactly_one(
            assignment["assigned"]
            for assignment in assignment_variables
        )

        operation_data[
            "assignments"
        ] = assignment_variables

    # ========================================================
    # 6. MACHINE CAPACITY
    # ========================================================

    for machine in machines:

        intervals = machine_intervals[
            machine.id
        ]

        if intervals:

            model.add_no_overlap(
                intervals
            )

    # ========================================================
    # 7. OPERATOR CAPACITY
    # ========================================================

    for operator in operators:

        intervals = operator_intervals[
            operator.id
        ]

        if intervals:

            model.add_no_overlap(
                intervals
            )

    # ========================================================
    # 8. MACHINE BREAKDOWN / MAINTENANCE
    # ========================================================

    for machine in machines:

        unavailable_intervals = (
            get_machine_unavailable_intervals(
                machine,
                planning_start,
            )
        )

        for index, (
            start_time,
            end_time,
        ) in enumerate(
            unavailable_intervals
        ):

            start_time = max(
                0,
                start_time,
            )

            end_time = min(
                horizon_minutes,
                end_time,
            )

            if end_time <= start_time:
                continue

            # IMPORTANT:
            # Correct OR-Tools API:
            #
            # new_fixed_size_interval_var(
            #     start,
            #     size,
            #     name
            # )

            fixed_interval = (
                model.new_fixed_size_interval_var(
                    start_time,
                    end_time - start_time,
                    (
                        f"machine_{machine.id}"
                        f"_unavailable_{index}"
                    ),
                )
            )

            model.add_no_overlap(
                machine_intervals[
                    machine.id
                ] + [fixed_interval]
            )

    # ========================================================
    # 9. OPERATOR ABSENCE
    # ========================================================

    for operator in operators:

        unavailable_intervals = (
            get_operator_unavailable_intervals(
                operator,
                planning_start,
            )
        )

        for index, (
            start_time,
            end_time,
        ) in enumerate(
            unavailable_intervals
        ):

            start_time = max(
                0,
                start_time,
            )

            end_time = min(
                horizon_minutes,
                end_time,
            )

            if end_time <= start_time:
                continue

            fixed_interval = (
                model.new_fixed_size_interval_var(
                    start_time,
                    end_time - start_time,
                    (
                        f"operator_{operator.id}"
                        f"_unavailable_{index}"
                    ),
                )
            )

            model.add_no_overlap(
                operator_intervals[
                    operator.id
                ] + [fixed_interval]
            )

    # ========================================================
    # 10. OPERATION PRECEDENCE
    # ========================================================

    operations_by_order = {}

    for operation in operations:

        operations_by_order.setdefault(
            operation.order_id,
            []
        ).append(operation)

    for order_id, order_operations in (
        operations_by_order.items()
    ):

        order_operations.sort(
            key=lambda operation:
            operation.sequence
        )

        for previous, current in zip(
            order_operations,
            order_operations[1:],
        ):

            previous_end = (
                operation_variables[
                    previous.id
                ]["end"]
            )

            current_start = (
                operation_variables[
                    current.id
                ]["start"]
            )

            model.add(
                current_start >= previous_end
            )

    # ========================================================
    # 11. MATERIAL AVAILABILITY
    # ========================================================

    for order in orders:

        if (
            not order.material_available
            and order.material_available_from
        ):

            material_minutes = (
                datetime_to_minutes(
                    order.material_available_from,
                    planning_start,
                )
            )

            order_operations = (
                operations_by_order.get(
                    order.id,
                    []
                )
            )

            if order_operations:

                first_operation = min(
                    order_operations,
                    key=lambda operation:
                    operation.sequence,
                )

                first_start = (
                    operation_variables[
                        first_operation.id
                    ]["start"]
                )

                model.add(
                    first_start >= material_minutes
                )

    # ========================================================
    # 12. DUE DATE OBJECTIVE
    # ========================================================

    lateness_variables = []

    for order in orders:

        order_operations = (
            operations_by_order.get(
                order.id,
                []
            )
        )

        if not order_operations:
            continue

        last_operation = max(
            order_operations,
            key=lambda operation:
            operation.sequence,
        )

        final_end = (
            operation_variables[
                last_operation.id
            ]["end"]
        )

        due_minutes = (
            datetime_to_minutes(
                order.due_date,
                planning_start,
            )
        )

        lateness = model.new_int_var(
            0,
            horizon_minutes * 2,
            f"order_{order.id}_lateness",
        )

        model.add(
            lateness >= (
                final_end - due_minutes
            )
        )

        model.add(
            lateness >= 0
        )

        lateness_variables.append(
            lateness
        )

    # Minimize total lateness.
    if lateness_variables:

        model.minimize(
            sum(lateness_variables)
        )

    # ========================================================
    # 13. SOLVE
    # ========================================================

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = (
        SOLVER_TIME_LIMIT
    )

    solver.parameters.num_search_workers = 8

    print("\nSolving...")

    status = solver.solve(model)

    print(
        f"Solver status: "
        f"{solver.status_name(status)}"
    )

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):

        raise RuntimeError(
            "No feasible schedule was found."
        )

    # ========================================================
    # 14. CREATE DATABASE SCHEDULE
    # ========================================================

    schedule = Schedule.objects.create(
        name=name,
        strategy="ONTIME",
    )

    scheduled_count = 0

    # ========================================================
    # 15. SAVE SOLUTION
    # ========================================================

    for operation in operations:

        operation_data = (
            operation_variables[
                operation.id
            ]
        )

        start_value = solver.value(
            operation_data["start"]
        )

        end_value = solver.value(
            operation_data["end"]
        )

        selected_assignment = None

        for assignment in (
            operation_data["assignments"]
        ):

            if solver.value(
                assignment["assigned"]
            ) == 1:

                selected_assignment = (
                    assignment
                )

                break

        if selected_assignment is None:

            raise RuntimeError(
                f"No assignment found for "
                f"{operation}"
            )

        machine = selected_assignment[
            "machine"
        ]

        operator = selected_assignment[
            "operator"
        ]

        start_time = minutes_to_datetime(
            start_value,
            planning_start,
        )

        end_time = minutes_to_datetime(
            end_value,
            planning_start,
        )

        ScheduledOperation.objects.create(
            schedule=schedule,
            operation=operation,
            machine=machine,
            operator=operator,
            start_time=start_time,
            end_time=end_time,
            setup_minutes=0,
            overtime=False,
        )

        scheduled_count += 1

    # ========================================================
    # 16. PRINT SUMMARY
    # ========================================================

    print("\n========================================")
    print("SCHEDULE GENERATED")
    print("========================================")

    print(
        f"Schedule ID : {schedule.id}"
    )

    print(
        f"Operations  : {scheduled_count}"
    )

    print(
        f"Orders      : {len(orders)}"
    )

    print(
        f"Machines    : {len(machines)}"
    )

    print(
        f"Operators   : {len(operators)}"
    )

    print("========================================\n")

    return schedule