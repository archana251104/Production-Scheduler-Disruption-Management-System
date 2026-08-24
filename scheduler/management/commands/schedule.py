from django.core.management.base import BaseCommand

from scheduler.scheduler_engine import generate_baseline_schedule
from scheduler.services.cost_calculator import (
    calculate_total_cost,
    calculate_ontime_metrics,
    calculate_robustness_metrics,
)


class Command(BaseCommand):

    help = "Generate a baseline 2-week production schedule"

    def add_arguments(self, parser):
        
        parser.add_argument(
            "--strategy",
            type=str,
            default="ONTIME",
            choices=["ONTIME", "CHEAPEST", "ROBUST"],
            help="Scheduling strategy",
        )

        parser.add_argument(
            "--name",
            type=str,
            default="Baseline 2-Week Schedule",
            help="Schedule name",
        )

        parser.add_argument(
            "--show-costs",
            action="store_true",
            help="Display detailed cost breakdown",
        )

        parser.add_argument(
            "--show-metrics",
            action="store_true",
            help="Display on-time and robustness metrics",
        )

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.WARNING(
                f"Generating {options['strategy']} schedule..."
            )
        )

        try:
            
            schedule = generate_baseline_schedule(
                name=options["name"]
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Schedule generated: {schedule.id}"
                )
            )

            # Calculate costs
            if options["show_costs"]:
                
                self.stdout.write(
                    self.style.HTTP_INFO(
                        "\n--- COST BREAKDOWN ---"
                    )
                )

                costs = calculate_total_cost(schedule)

                self.stdout.write(
                    f"Overtime Cost:     "
                    f"₹{costs['overtime']['total']:,.2f}"
                )

                self.stdout.write(
                    f"Penalty Cost:      "
                    f"₹{costs['penalties']['total']:,.2f}"
                )

                self.stdout.write(
                    f"Changeover Cost:   "
                    f"₹{costs['changeovers']['total']:,.2f}"
                )

                self.stdout.write(
                    f"Generator Cost:    "
                    f"₹{costs['generator']['total']:,.2f}"
                )

                self.stdout.write(
                    self.style.HTTP_SERVER_ERROR(
                        f"TOTAL COST:        "
                        f"₹{costs['total_cost']:,.2f}"
                    )
                )

            # Calculate metrics
            if options["show_metrics"]:
                
                self.stdout.write(
                    self.style.HTTP_INFO(
                        "\n--- PERFORMANCE METRICS ---"
                    )
                )

                ontime = calculate_ontime_metrics(schedule)

                self.stdout.write(
                    f"Total Orders:      {ontime['total_orders']}"
                )

                self.stdout.write(
                    f"On-Time Orders:    {ontime['on_time_orders']}"
                )

                self.stdout.write(
                    f"Late Orders:       {ontime['late_orders']}"
                )

                self.stdout.write(
                    self.style.HTTP_SUCCESS(
                        f"On-Time %:         "
                        f"{ontime['on_time_percent']:.1f}%"
                    )
                )

                robustness = (
                    calculate_robustness_metrics(schedule)
                )

                self.stdout.write(
                    f"Avg Buffer:        "
                    f"{robustness['avg_buffer_minutes']:.1f} min"
                )

                self.stdout.write(
                    self.style.HTTP_SUCCESS(
                        f"Robustness Score:  "
                        f"{robustness['robustness_score']:.1f}/100"
                    )
                )

        except Exception as e:
            
            self.stdout.write(
                self.style.ERROR(
                    f"Error: {str(e)}"
                )
            )
