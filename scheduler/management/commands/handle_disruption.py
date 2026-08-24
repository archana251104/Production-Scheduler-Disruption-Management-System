from django.core.management.base import BaseCommand
from django.utils import timezone

from scheduler.models import (
    Breakdown,
    OperatorAbsence,
    MaterialDelay,
    Schedule,
)
from scheduler.services.disruption_engine import (
    Disruption,
    DisruptionType,
    replan_after_disruption,
    recommend_actions,
    detect_disruptions,
)


class Command(BaseCommand):

    help = "Handle production disruptions and replan schedule"

    def add_arguments(self, parser):
        
        parser.add_argument(
            "--breakdown",
            type=int,
            help="Breakdown ID to handle",
        )

        parser.add_argument(
            "--absence",
            type=int,
            help="Operator absence ID to handle",
        )

        parser.add_argument(
            "--material-delay",
            type=int,
            help="Material delay ID to handle",
        )

        parser.add_argument(
            "--current-schedule",
            type=int,
            help="Current schedule ID",
        )

        parser.add_argument(
            "--strategy",
            type=str,
            default="ONTIME",
            choices=["ONTIME", "CHEAPEST", "ROBUST"],
            help="Replanning strategy",
        )

        parser.add_argument(
            "--auto-detect",
            action="store_true",
            help="Auto-detect active disruptions",
        )

    def handle(self, *args, **options):

        # Get current schedule
        if options["current_schedule"]:
            
            try:
                schedule = Schedule.objects.get(
                    id=options["current_schedule"]
                )
            except Schedule.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        "Schedule not found"
                    )
                )
                return
        
        else:
            
            # Get most recent schedule
            schedule = (
                Schedule.objects
                .order_by("-created_at")
                .first()
            )

            if not schedule:
                self.stdout.write(
                    self.style.ERROR(
                        "No schedule found. "
                        "Generate one first."
                    )
                )
                return

        self.stdout.write(
            self.style.WARNING(
                f"Current schedule: {schedule.name} "
                f"(ID: {schedule.id})"
            )
        )

        # Detect disruption
        disruption = None

        if options["auto_detect"]:
            
            self.stdout.write(
                "Auto-detecting disruptions..."
            )

            disruptions_list = detect_disruptions(schedule)

            if disruptions_list:
                
                disruption = disruptions_list[0]

                self.stdout.write(
                    self.style.WARNING(
                        f"Detected: {disruption}"
                    )
                )
            
            else:
                
                self.stdout.write(
                    self.style.SUCCESS(
                        "No active disruptions found"
                    )
                )
                return

        elif options["breakdown"]:
            
            try:
                breakdown = Breakdown.objects.get(
                    id=options["breakdown"]
                )

                disruption = Disruption(
                    DisruptionType.MACHINE_BREAKDOWN,
                    breakdown.machine,
                    breakdown.start_time,
                    breakdown.end_time,
                    breakdown.reason,
                )

                self.stdout.write(
                    self.style.WARNING(
                        f"Handling breakdown: "
                        f"{breakdown.machine.machine_id}"
                    )
                )
            
            except Breakdown.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        "Breakdown not found"
                    )
                )
                return

        elif options["absence"]:
            
            try:
                absence = OperatorAbsence.objects.get(
                    id=options["absence"]
                )

                disruption = Disruption(
                    DisruptionType.OPERATOR_ABSENCE,
                    absence.operator,
                    absence.start_time,
                    absence.end_time,
                    absence.reason,
                )

                self.stdout.write(
                    self.style.WARNING(
                        f"Handling absence: "
                        f"{absence.operator.name}"
                    )
                )
            
            except OperatorAbsence.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        "Absence not found"
                    )
                )
                return

        elif options["material_delay"]:
            
            try:
                delay = MaterialDelay.objects.get(
                    id=options["material_delay"]
                )

                disruption = Disruption(
                    DisruptionType.MATERIAL_DELAY,
                    delay.order,
                    delay.expected_time,
                    delay.expected_time +
                    timezone.timedelta(hours=24),
                    delay.reason,
                )

                self.stdout.write(
                    self.style.WARNING(
                        f"Handling material delay: "
                        f"{delay.order.order_number}"
                    )
                )
            
            except MaterialDelay.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        "Material delay not found"
                    )
                )
                return

        if not disruption:
            self.stdout.write(
                self.style.ERROR(
                    "No disruption specified"
                )
            )
            return

        # Replan
        self.stdout.write(
            self.style.WARNING(
                f"\nReplanning with {options['strategy']} "
                f"strategy..."
            )
        )

        result = replan_after_disruption(
            schedule,
            disruption,
            strategy=options["strategy"],
        )

        new_schedule = result["new_schedule"]

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Replanned schedule created: "
                f"{new_schedule.id}"
            )
        )

        # Show recommendations
        self.stdout.write(
            self.style.HTTP_INFO(
                "\n--- RECOMMENDATIONS ---"
            )
        )

        recommendations = recommend_actions(result)

        for rec in recommendations:
            
            if rec["priority"] == "CRITICAL":
                style = self.style.ERROR
            elif rec["priority"] == "HIGH":
                style = self.style.WARNING
            else:
                style = self.style.SUCCESS

            self.stdout.write(
                style(
                    f"\n[{rec['priority']}] "
                    f"{rec['action']}"
                )
            )

            self.stdout.write(
                f"  Details: {rec['details']}"
            )

            self.stdout.write(
                f"  → {rec['phone_call']}"
            )

        # Show cost impact
        self.stdout.write(
            self.style.HTTP_INFO(
                "\n--- COST IMPACT ---"
            )
        )

        cost_delta = result["cost_delta"]

        if cost_delta > 0:
            
            self.stdout.write(
                self.style.ERROR(
                    f"Cost increase: "
                    f"₹{cost_delta:,.2f}"
                )
            )
        
        else:
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cost savings: "
                    f"₹{abs(cost_delta):,.2f}"
                )
            )

        original_total = (
            result["original_costs"]["total_cost"]
        )

        new_total = result["new_costs"]["total_cost"]

        self.stdout.write(
            f"Original: ₹{original_total:,.2f}"
        )

        self.stdout.write(
            f"New:      ₹{new_total:,.2f}"
        )
