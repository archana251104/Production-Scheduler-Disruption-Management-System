from django.db import models


# ============================================================
# CUSTOMER
# ============================================================

class Customer(models.Model):
    TIER_CHOICES = [
        (1, "Tier 1"),
        (2, "Tier 2"),
        (3, "Tier 3"),
    ]

    name = models.CharField(max_length=100)
    tier = models.IntegerField(choices=TIER_CHOICES)
    revenue_share = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    late_penalty_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    jit_customer = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# ============================================================
# MACHINE
# ============================================================

class Machine(models.Model):
    MACHINE_TYPES = [
        ("CNC", "CNC Lathe"),
        ("MILLING", "Milling"),
        ("DRILL", "Drilling"),
        ("GRINDING", "Grinding"),
        ("VMC", "VMC"),
        ("INSPECTION", "Inspection"),
    ]

    machine_id = models.CharField(
        max_length=20,
        unique=True
    )

    name = models.CharField(max_length=100)

    machine_type = models.CharField(
        max_length=20,
        choices=MACHINE_TYPES
    )

    capabilities = models.JSONField(
        default=list
    )

    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.machine_id} - {self.name}"


# ============================================================
# OPERATOR
# ============================================================

class Operator(models.Model):

    name = models.CharField(max_length=100)

    employee_id = models.CharField(
        max_length=20,
        unique=True
    )

    skills = models.JSONField(
        default=list
    )

    can_work_overtime = models.BooleanField(
        default=True
    )

    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.employee_id} - {self.name}"


# ============================================================
# SHIFT
# ============================================================

class Shift(models.Model):

    SHIFT_CHOICES = [
        ("MORNING", "Morning"),
        ("EVENING", "Evening"),
        ("NIGHT", "Night"),
    ]

    name = models.CharField(
        max_length=20,
        choices=SHIFT_CHOICES
    )

    start_hour = models.IntegerField()
    end_hour = models.IntegerField()

    overtime = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# ============================================================
# ORDER
# ============================================================

class Order(models.Model):

    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("LATE", "Late"),
    ]

    PRIORITY_CHOICES = [
        ("HIGH", "High"),
        ("MEDIUM", "Medium"),
        ("LOW", "Low"),
    ]

    order_number = models.CharField(
        max_length=30,
        unique=True
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    part_number = models.CharField(
        max_length=50
    )

    quantity = models.IntegerField()

    due_date = models.DateTimeField()

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="MEDIUM"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="OPEN"
    )

    material_available = models.BooleanField(
        default=True
    )

    material_available_from = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.order_number


# ============================================================
# OPERATION
# ============================================================

class Operation(models.Model):

    OPERATION_TYPES = [
        ("TURNING", "Turning"),
        ("MILLING", "Milling"),
        ("DRILLING", "Drilling"),
        ("GRINDING", "Grinding"),
        ("INSPECTION", "Inspection"),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="operations"
    )

    sequence = models.PositiveIntegerField()

    operation_type = models.CharField(
        max_length=20,
        choices=OPERATION_TYPES
    )

    duration_minutes = models.PositiveIntegerField()

    setup_family = models.CharField(
        max_length=20
    )

    required_skill = models.CharField(
        max_length=50
    )

    eligible_machines = models.ManyToManyField(
        Machine,
        related_name="operations"
    )

    def __str__(self):
        return (
            f"{self.order.order_number} - "
            f"Operation {self.sequence}"
        )


# ============================================================
# CHANGEOVER
# ============================================================

class Changeover(models.Model):

    from_family = models.CharField(
        max_length=20
    )

    to_family = models.CharField(
        max_length=20
    )

    duration_minutes = models.PositiveIntegerField()

    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    class Meta:
        unique_together = (
            "from_family",
            "to_family",
        )

    def __str__(self):
        return (
            f"{self.from_family} → "
            f"{self.to_family}"
        )


# ============================================================
# MACHINE BREAKDOWN
# ============================================================

class Breakdown(models.Model):

    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name="breakdowns"
    )

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    reason = models.CharField(
        max_length=200
    )

    repair_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return (
            f"{self.machine.machine_id} - "
            f"{self.reason}"
        )


# ============================================================
# MAINTENANCE
# ============================================================

class Maintenance(models.Model):

    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name="maintenance_windows"
    )

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    description = models.CharField(
        max_length=200
    )

    def __str__(self):
        return (
            f"{self.machine.machine_id} maintenance"
        )


# ============================================================
# OPERATOR ABSENCE
# ============================================================

class OperatorAbsence(models.Model):

    operator = models.ForeignKey(
        Operator,
        on_delete=models.CASCADE,
        related_name="absences"
    )

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    reason = models.CharField(
        max_length=200
    )

    def __str__(self):
        return (
            f"{self.operator.name} absent"
        )


# ============================================================
# MATERIAL DELAY
# ============================================================

class MaterialDelay(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="material_delays"
    )

    expected_time = models.DateTimeField()

    actual_time = models.DateTimeField(
        null=True,
        blank=True
    )

    reason = models.CharField(
        max_length=200
    )

    def __str__(self):
        return (
            f"{self.order.order_number} material delay"
        )


# ============================================================
# REWORK
# ============================================================

class Rework(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="reworks"
    )

    quantity = models.PositiveIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    reason = models.CharField(
        max_length=200
    )

    additional_minutes = models.PositiveIntegerField(
        default=0
    )

    completed = models.BooleanField(
        default=False
    )

    def __str__(self):
        return (
            f"{self.order.order_number} "
            f"rework ({self.quantity})"
        )


# ============================================================
# SCHEDULE
# ============================================================

class Schedule(models.Model):

    STRATEGY_CHOICES = [
        ("CHEAPEST", "Cheapest"),
        ("ONTIME", "Most On-Time"),
        ("ROBUST", "Most Robust"),
    ]

    name = models.CharField(
        max_length=100
    )

    strategy = models.CharField(
        max_length=20,
        choices=STRATEGY_CHOICES
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    overtime_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    penalty_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    changeover_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    generator_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return self.name


# ============================================================
# SCHEDULED OPERATION
# ============================================================

class ScheduledOperation(models.Model):

    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name="scheduled_operations"
    )

    operation = models.ForeignKey(
        Operation,
        on_delete=models.CASCADE
    )

    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE
    )

    operator = models.ForeignKey(
        Operator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    setup_minutes = models.PositiveIntegerField(
        default=0
    )

    overtime = models.BooleanField(
        default=False
    )

    def __str__(self):
        return (
            f"{self.operation} - "
            f"{self.machine.machine_id}"
        )