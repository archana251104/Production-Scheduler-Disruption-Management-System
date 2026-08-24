from django.core.management.base import BaseCommand

from scheduler.scheduler_engine import generate_baseline_schedule
from scheduler.services.cost_calculator import (
    calculate_total_cost,
    calculate_ontime_metrics,
    calculate_robustness_metrics,
)
from scheduler.models import Schedule


class Command(BaseCommand):

    help = "Generate trade-off memo with 3 strategies"

    def add_arguments(self, parser):
        
        parser.add_argument(
            "--output",
            type=str,
            default="tradeoff_memo.txt",
            help="Output file for memo",
        )

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.WARNING(
                "Generating three scheduling strategies..."
            )
        )

        strategies = ["ONTIME", "CHEAPEST", "ROBUST"]
        schedules = {}
        metrics = {}

        for strategy in strategies:
            
            self.stdout.write(
                f"\n📊 Generating {strategy} schedule..."
            )

            try:
                
                schedule = generate_baseline_schedule(
                    name=f"{strategy} Strategy Schedule"
                )

                schedules[strategy] = schedule

                # Calculate metrics
                costs = calculate_total_cost(schedule)
                ontime = calculate_ontime_metrics(schedule)
                robustness = (
                    calculate_robustness_metrics(schedule)
                )

                metrics[strategy] = {
                    "costs": costs,
                    "ontime": ontime,
                    "robustness": robustness,
                }

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ {strategy} schedule ready "
                        f"(ID: {schedule.id})"
                    )
                )

            except Exception as e:
                
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to generate {strategy}: "
                        f"{str(e)}"
                    )
                )
                continue

        # Generate memo
        memo = self._generate_memo(strategies, metrics)

        # Save to file
        output_file = options["output"]

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(memo)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Trade-off memo saved to "
                f"{output_file}"
            )
        )

        # Print memo
        self.stdout.write(
            self.style.HTTP_INFO(
                "\n" + "=" * 70
            )
        )

        self.stdout.write(memo)

        self.stdout.write(
            self.style.HTTP_INFO(
                "=" * 70
            )
        )

    def _generate_memo(self, strategies, metrics):
        
        memo = []

        memo.append(
            "╔" + "=" * 68 + "╗"
        )

        memo.append(
            "║" + " " * 68 + "║"
        )

        memo.append(
            "║" +
            "SRIDHAR PRECISION WORKS".center(68) +
            "║"
        )

        memo.append(
            "║" +
            "PRODUCTION SCHEDULE TRADE-OFF ANALYSIS".center(68) +
            "║"
        )

        memo.append(
            "║" + " " * 68 + "║"
        )

        memo.append(
            "╚" + "=" * 68 + "╝"
        )

        memo.append("")

        # Executive Summary
        memo.append(
            "EXECUTIVE SUMMARY"
        )

        memo.append("-" * 70)

        best_cost_strategy = min(
            strategies,
            key=lambda s: (
                metrics[s]["costs"]["total_cost"]
            ),
        )

        best_ontime_strategy = max(
            strategies,
            key=lambda s: (
                metrics[s]["ontime"]["on_time_percent"]
            ),
        )

        best_robust_strategy = max(
            strategies,
            key=lambda s: (
                metrics[s]["robustness"]["robustness_score"]
            ),
        )

        memo.append(
            f"Cheapest Strategy:     {best_cost_strategy}"
        )

        memo.append(
            f"Most On-Time Strategy: {best_ontime_strategy}"
        )

        memo.append(
            f"Most Robust Strategy:  {best_robust_strategy}"
        )

        memo.append("")

        # Strategy Comparison
        memo.append(
            "DETAILED STRATEGY COMPARISON"
        )

        memo.append("-" * 70)

        memo.append("")

        for strategy in strategies:
            
            m = metrics[strategy]

            memo.append(
                f"📌 {strategy.upper()} STRATEGY"
            )

            memo.append("-" * 70)

            # Costs
            memo.append(
                "COST BREAKDOWN:"
            )

            memo.append(
                f"  Overtime Cost:      "
                f"₹{m['costs']['overtime']['total']:>12,.2f}"
            )

            memo.append(
                f"  Penalty Cost:       "
                f"₹{m['costs']['penalties']['total']:>12,.2f}"
            )

            memo.append(
                f"  Changeover Cost:    "
                f"₹{m['costs']['changeovers']['total']:>12,.2f}"
            )

            memo.append(
                f"  Generator Cost:     "
                f"₹{m['costs']['generator']['total']:>12,.2f}"
            )

            memo.append(
                f"  " + "-" * 36
            )

            memo.append(
                f"  TOTAL COST:         "
                f"₹{m['costs']['total_cost']:>12,.2f}"
            )

            memo.append("")

            # On-Time Performance
            memo.append(
                "ON-TIME PERFORMANCE:"
            )

            memo.append(
                f"  Total Orders:       "
                f"{m['ontime']['total_orders']:>15}"
            )

            memo.append(
                f"  On-Time:            "
                f"{m['ontime']['on_time_orders']:>15}"
            )

            memo.append(
                f"  Late:               "
                f"{m['ontime']['late_orders']:>15}"
            )

            memo.append(
                f"  On-Time %:          "
                f"{m['ontime']['on_time_percent']:>15.1f}%"
            )

            memo.append("")

            # Robustness
            memo.append(
                "ROBUSTNESS:"
            )

            memo.append(
                f"  Avg Buffer Time:    "
                f"{m['robustness']['avg_buffer_minutes']:>12.1f} min"
            )

            memo.append(
                f"  Robustness Score:   "
                f"{m['robustness']['robustness_score']:>19.1f}/100"
            )

            memo.append("")

            memo.append("")

        # Recommendation
        memo.append(
            "RECOMMENDATION"
        )

        memo.append("-" * 70)

        memo.append("")

        recommended = best_ontime_strategy

        memo.append(
            f"✓ RECOMMENDED: {recommended} STRATEGY"
        )

        memo.append("")

        if recommended == "ONTIME":
            
            memo.append(
                "RATIONALE:"
            )

            memo.append(
                "  • Our tier-1 customer (60% revenue) "
                "requires JIT delivery"
            )

            memo.append(
                "  • Late penalties are substantial and "
                "recurring"
            )

            memo.append(
                "  • On-time delivery is key to customer "
                "retention"
            )

            memo.append(
                "  • The extra cost in overtime/penalties "
                "is justified"
            )

            memo.append(
                "    by maintaining customer trust"

            )

        elif recommended == "CHEAPEST":
            
            memo.append(
                "RATIONALE:"
            )

            memo.append(
                "  • Minimizes total operational cost"
            )

            memo.append(
                "  • Suitable if customer flexibility exists"
            )

            memo.append(
                "  • Requires careful customer "
                "communication"
            )

        else:
            
            memo.append(
                "RATIONALE:"
            )

            memo.append(
                "  • Maximum buffer time protects against "
                "disruptions"
            )

            memo.append(
                "  • Machine breakdowns are unpredictable "
                "but frequent"
            )

            memo.append(
                "  • Robust schedule minimizes replanning "
                "costs"
            )

        memo.append("")

        # Risk Assessment
        memo.append(
            "RISK ASSESSMENT"
        )

        memo.append("-" * 70)

        memo.append("")

        memo.append(
            "ONTIME Strategy Risks:"
        )

        memo.append(
            "  • Machine breakdown → immediate reschedule "
            "required"
        )

        memo.append(
            "  • Limited buffer means cascading delays"
        )

        memo.append("")

        memo.append(
            "CHEAPEST Strategy Risks:"
        )

        memo.append(
            "  • High late penalties if disruptions occur"
        )

        memo.append(
            "  • JIT customer unhappy with delays"
        )

        memo.append("")

        memo.append(
            "ROBUST Strategy Risks:"
        )

        memo.append(
            "  • Highest cost due to buffer time"
        )

        memo.append(
            "  • Unused capacity if disruptions don't occur"
        )

        memo.append("")

        # Implementation Notes
        memo.append(
            "IMPLEMENTATION NOTES"
        )

        memo.append("-" * 70)

        memo.append("")

        memo.append(
            "1. OPERATOR BRIEFING"
        )

        memo.append(
            "   • Grinding machine is critical "
            "bottleneck (only 3 operators)"
        )

        memo.append(
            "   • Any grinding operator absence → "
            "high-priority issue"
        )

        memo.append("")

        memo.append(
            "2. MACHINE PRIORITY"
        )

        memo.append(
            "   • Prioritize grinding machine "
            "maintenance"
        )

        memo.append(
            "   • Keep spare capacity on CNC/milling "
            "for rework"
        )

        memo.append("")

        memo.append(
            "3. CUSTOMER COMMUNICATION"
        )

        memo.append(
            "   • Daily ETA updates to AutoPrime Motors "
            "(tier-1)"
        )

        memo.append(
            "   • Weekly schedules to other customers"
        )

        memo.append("")

        memo.append(
            "4. CONTINGENCY PLANNING"
        )

        memo.append(
            "   • Keep 2-3 orders in backup queue for "
            "quick dispatch"
        )

        memo.append(
            "   • Identify orders that can absorb delays"
        )

        memo.append("")

        return "\n".join(memo)
