import random
from datetime import timedelta

from django.utils import timezone

from scheduler.models import (
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
)


random.seed(42)


# ============================================================
# CUSTOMERS
# ============================================================

def create_customers():

    Customer.objects.all().delete()

    customers = [
        {
            "name": "AutoPrime Motors",
            "tier": 1,
            "revenue_share": 60,
            "penalty": 25000,
            "jit": True,
        },
        {
            "name": "Bharat Auto Components",
            "tier": 2,
            "revenue_share": 15,
            "penalty": 10000,
            "jit": False,
        },
        {
            "name": "Metro Precision",
            "tier": 2,
            "revenue_share": 10,
            "penalty": 8000,
            "jit": False,
        },
        {
            "name": "Shakti Motors",
            "tier": 3,
            "revenue_share": 8,
            "penalty": 4000,
            "jit": False,
        },
        {
            "name": "Hosur Engineering",
            "tier": 3,
            "revenue_share": 7,
            "penalty": 3000,
            "jit": False,
        },
    ]

    result = []

    for data in customers:

        customer = Customer.objects.create(
            name=data["name"],
            tier=data["tier"],
            revenue_share=data["revenue_share"],
            late_penalty_per_hour=data["penalty"],
            jit_customer=data["jit"],
        )

        result.append(customer)

    return result


# ============================================================
# MACHINES
# ============================================================

def create_machines():

    Machine.objects.all().delete()

    machines = []

    # CNC LATHES
    for i in range(1, 6):

        machines.append(
            Machine.objects.create(
                machine_id=f"CNC0{i}",
                name=f"CNC Lathe {i}",
                machine_type="CNC",
                capabilities=["TURNING"],
            )
        )

    # MILLING
    for i in range(1, 5):

        machines.append(
            Machine.objects.create(
                machine_id=f"MIL0{i}",
                name=f"Milling Machine {i}",
                machine_type="MILLING",
                capabilities=["MILLING"],
            )
        )

    # DRILLING
    for i in range(1, 3):

        machines.append(
            Machine.objects.create(
                machine_id=f"DRL0{i}",
                name=f"Drilling Machine {i}",
                machine_type="DRILL",
                capabilities=["DRILLING"],
            )
        )

    # GRINDING
    machines.append(
        Machine.objects.create(
            machine_id="GR01",
            name="Precision Grinding Machine",
            machine_type="GRINDING",
            capabilities=["GRINDING"],
        )
    )

    # VMC
    machines.append(
        Machine.objects.create(
            machine_id="VMC01",
            name="Vertical Machining Center",
            machine_type="VMC",
            capabilities=["MILLING", "DRILLING"],
        )
    )

    # INSPECTION
    machines.append(
        Machine.objects.create(
            machine_id="INS01",
            name="Inspection Station",
            machine_type="INSPECTION",
            capabilities=["INSPECTION"],
        )
    )

    return machines


# ============================================================
# OPERATORS
# ============================================================

def create_operators():

    Operator.objects.all().delete()

    operators = []

    skills_by_group = {
        "TURNING": ["TURNING"],
        "MILLING": ["MILLING"],
        "DRILLING": ["DRILLING"],
        "GRINDING": ["GRINDING"],
        "INSPECTION": ["INSPECTION"],
    }

    employee_number = 1

    # Turning operators
    for i in range(5):

        operators.append(
            Operator.objects.create(
                employee_id=f"OP{employee_number:02d}",
                name=f"Turning Operator {i + 1}",
                skills=skills_by_group["TURNING"],
            )
        )

        employee_number += 1

    # Milling operators
    for i in range(4):

        operators.append(
            Operator.objects.create(
                employee_id=f"OP{employee_number:02d}",
                name=f"Milling Operator {i + 1}",
                skills=skills_by_group["MILLING"],
            )
        )

        employee_number += 1

    # Drilling operators
    for i in range(3):

        operators.append(
            Operator.objects.create(
                employee_id=f"OP{employee_number:02d}",
                name=f"Drilling Operator {i + 1}",
                skills=skills_by_group["DRILLING"],
            )
        )

        employee_number += 1

    # IMPORTANT:
    # Only 3 people can operate grinding.
    for i in range(3):

        operators.append(
            Operator.objects.create(
                employee_id=f"OP{employee_number:02d}",
                name=f"Grinding Specialist {i + 1}",
                skills=skills_by_group["GRINDING"],
            )
        )

        employee_number += 1

    # Inspection
    for i in range(3):

        operators.append(
            Operator.objects.create(
                employee_id=f"OP{employee_number:02d}",
                name=f"Quality Inspector {i + 1}",
                skills=skills_by_group["INSPECTION"],
            )
        )

        employee_number += 1

    return operators


# ============================================================
# SHIFTS
# ============================================================

def create_shifts():

    Shift.objects.all().delete()

    shifts = [
        {
            "name": "MORNING",
            "start_hour": 6,
            "end_hour": 14,
            "overtime": False,
        },
        {
            "name": "EVENING",
            "start_hour": 14,
            "end_hour": 22,
            "overtime": False,
        },
        {
            "name": "NIGHT",
            "start_hour": 22,
            "end_hour": 6,
            "overtime": True,
        },
    ]

    result = []

    for data in shifts:

        shift = Shift.objects.create(
            name=data["name"],
            start_hour=data["start_hour"],
            end_hour=data["end_hour"],
            overtime=data["overtime"],
        )

        result.append(shift)

    return result


# ============================================================
# CHANGEOVERS
# ============================================================

def create_changeovers():

    Changeover.objects.all().delete()

    families = ["A", "B", "C", "D"]

    for from_family in families:

        for to_family in families:

            if from_family == to_family:

                duration = 20

            elif {
                from_family,
                to_family,
            } <= {"A", "B"}:

                duration = 30

            elif {
                from_family,
                to_family,
            } <= {"C", "D"}:

                duration = 45

            else:

                duration = random.choice(
                    [90, 120, 150, 180]
                )

            Changeover.objects.create(
                from_family=from_family,
                to_family=to_family,
                duration_minutes=duration,
                cost=duration * 50,
            )


# ============================================================
# ORDERS
# ============================================================

def create_orders(customers, machines):

    Order.objects.all().delete()
    Operation.objects.all().delete()

    machine_by_type = {}

    for machine in machines:

        machine_by_type.setdefault(
            machine.machine_type,
            []
        ).append(machine)

    orders = []

    now = timezone.now()

    part_families = ["A", "B", "C", "D"]

    operation_options = [
        ["TURNING", "MILLING", "DRILLING", "GRINDING", "INSPECTION"],
        ["TURNING", "MILLING", "GRINDING", "INSPECTION"],
        ["TURNING", "DRILLING", "GRINDING", "INSPECTION"],
        ["TURNING", "MILLING", "DRILLING", "INSPECTION"],
        ["TURNING", "MILLING", "GRINDING"],
    ]

    operation_machine_types = {
        "TURNING": ["CNC"],
        "MILLING": ["MILLING", "VMC"],
        "DRILLING": ["DRILL", "VMC"],
        "GRINDING": ["GRINDING"],
        "INSPECTION": ["INSPECTION"],
    }

    operation_durations = {
        "TURNING": (120, 360),
        "MILLING": (90, 300),
        "DRILLING": (60, 180),
        "GRINDING": (120, 360),
        "INSPECTION": (30, 90),
    }

    for order_number in range(1, 26):

        customer = random.choices(
            customers,
            weights=[60, 15, 10, 8, 7],
            k=1
        )[0]

        quantity = random.randint(
            200,
            5000
        )

        family = random.choice(
            part_families
        )

        due_date = now + timedelta(
            days=random.randint(2, 14)
        )

        priority = (
            "HIGH"
            if customer.tier == 1
            else random.choice(
                ["MEDIUM", "LOW"]
            )
        )

        order = Order.objects.create(
            order_number=f"ORD{order_number:03d}",
            customer=customer,
            part_number=f"PART-{family}-{order_number:03d}",
            quantity=quantity,
            due_date=due_date,
            priority=priority,
        )

        orders.append(order)

        routing = random.choice(
            operation_options
        )

        for sequence, operation_type in enumerate(
            routing,
            start=1
        ):

            duration_range = operation_durations[
                operation_type
            ]

            duration = random.randint(
                duration_range[0],
                duration_range[1]
            )

            eligible_machines = []

            for machine_type in operation_machine_types[
                operation_type
            ]:

                eligible_machines.extend(
                    machine_by_type.get(
                        machine_type,
                        []
                    )
                )

            operation = Operation.objects.create(
                order=order,
                sequence=sequence,
                operation_type=operation_type,
                duration_minutes=duration,
                setup_family=family,
                required_skill=operation_type,
            )

            operation.eligible_machines.set(
                eligible_machines
            )

    return orders


# ============================================================
# BREAKDOWNS
# ============================================================

def create_breakdowns(machines):

    Breakdown.objects.all().delete()

    now = timezone.now()

    # Create around 10 historical/current breakdowns
    for i in range(10):

        machine = random.choice(machines)

        start = now - timedelta(
            days=random.randint(1, 30)
        )

        duration = random.choice(
            [2, 4, 6, 8, 10, 12]
        )

        end = start + timedelta(
            hours=duration
        )

        Breakdown.objects.create(
            machine=machine,
            start_time=start,
            end_time=end,
            reason=random.choice([
                "Spindle failure",
                "Hydraulic issue",
                "Electrical fault",
                "Coolant system failure",
                "Tooling failure",
                "Bearing replacement",
            ]),
            repair_cost=random.randint(
                3000,
                25000
            ),
        )


# ============================================================
# MAINTENANCE
# ============================================================

def create_maintenance(machines):

    Maintenance.objects.all().delete()

    now = timezone.now()

    for machine in machines:

        start = now + timedelta(
            days=random.randint(1, 10),
            hours=random.choice(
                [0, 8, 16]
            )
        )

        end = start + timedelta(
            hours=4
        )

        Maintenance.objects.create(
            machine=machine,
            start_time=start,
            end_time=end,
            description="Planned preventive maintenance",
        )


# ============================================================
# OPERATOR ABSENCE
# ============================================================

def create_absences(operators):

    OperatorAbsence.objects.all().delete()

    now = timezone.now()

    for operator in random.sample(
        operators,
        5
    ):

        start = now + timedelta(
            days=random.randint(1, 10)
        )

        end = start + timedelta(
            hours=8
        )

        OperatorAbsence.objects.create(
            operator=operator,
            start_time=start,
            end_time=end,
            reason=random.choice([
                "Sick leave",
                "Personal leave",
                "Training",
                "Emergency leave",
            ]),
        )


# ============================================================
# MATERIAL DELAYS
# ============================================================

def create_material_delays(orders):

    MaterialDelay.objects.all().delete()

    now = timezone.now()

    delayed_orders = random.sample(
        orders,
        5
    )

    for order in delayed_orders:

        expected_time = now + timedelta(
            days=random.randint(1, 5)
        )

        MaterialDelay.objects.create(
            order=order,
            expected_time=expected_time,
            reason=random.choice([
                "Raw material supplier delay",
                "Transport delay",
                "Incoming quality rejection",
                "Supplier production delay",
            ]),
        )


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_all():

    print("Creating customers...")
    customers = create_customers()

    print("Creating machines...")
    machines = create_machines()

    print("Creating operators...")
    operators = create_operators()

    print("Creating shifts...")
    shifts = create_shifts()

    print("Creating changeovers...")
    create_changeovers()

    print("Creating orders and operations...")
    orders = create_orders(
        customers,
        machines
    )

    print("Creating breakdown history...")
    create_breakdowns(machines)

    print("Creating maintenance...")
    create_maintenance(machines)

    print("Creating operator absences...")
    create_absences(operators)

    print("Creating material delays...")
    create_material_delays(orders)

    print("\n================================")
    print("FACTORY DATA CREATED")
    print("================================")
    print(f"Customers: {Customer.objects.count()}")
    print(f"Machines: {Machine.objects.count()}")
    print(f"Operators: {Operator.objects.count()}")
    print(f"Shifts: {Shift.objects.count()}")
    print(f"Orders: {Order.objects.count()}")
    print(f"Operations: {Operation.objects.count()}")
    print(f"Changeovers: {Changeover.objects.count()}")
    print(f"Breakdowns: {Breakdown.objects.count()}")
    print(f"Maintenance: {Maintenance.objects.count()}")
    print(
        f"Operator absences: "
        f"{OperatorAbsence.objects.count()}"
    )
    print(
        f"Material delays: "
        f"{MaterialDelay.objects.count()}"
    )