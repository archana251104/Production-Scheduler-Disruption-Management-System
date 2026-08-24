# QUICK START GUIDE - Defense Session

## Pre-Defense Checklist

### Before Meeting
1. ✅ Database populated with 25 orders
2. ✅ Schedules generated (ID: 1, 2-4, 5-7)
3. ✅ Trade-off memo saved
4. ✅ Web server tested
5. ✅ All management commands working

### System Running
```bash
cd sridhar_precision_scheduler
python manage.py runserver
# Visit http://localhost:8000/
```

---

## DEMO FLOW (15-20 minutes)

### PART 1: THE PROBLEM (2 min)

**Show:** Dashboard with scheduled operations
**Say:** 
- 40 people, 14 machines, 2 shifts
- ~25 open orders with 3-6 operations each
- Owner pays BOTH overtime AND late penalties monthly
- Tier-1 customer (60% revenue) requires JIT delivery

**Navigate to:** http://localhost:8000/

---

### PART 2: THE SCHEDULE (3 min)

**Show:** Today's operations in dashboard
**Explain:**
- 103 operations scheduled across 14 machines
- Each operation assigned to specific machine and operator
- Respects shift windows (6AM-2PM, 2PM-10PM, 10PM-6AM)
- Maintains operator skill requirements
- No machine or operator conflicts

**Click:** View Current Schedule link

**Show:** Machine-by-machine breakdown
**Highlight:**
- Grinding machine (bottleneck) - only 3 operators can run
- CNC machines (high volume)
- Sequence-dependent changeovers between part families

---

### PART 3: THE COSTS (3 min)

**Show:** Cost breakdown
```
Overtime Cost:    ₹0.00
Penalty Cost:     ₹0.00
Changeover Cost:  ₹183,250.00
Generator Cost:   ₹0.00
─────────────────────────
TOTAL:            ₹183,250.00
```

**Explain:**
- Current schedule achieves 100% on-time delivery
- No overtime needed
- No late penalties
- Cost primarily from changeovers (part family switching)

**Show:** On-Time Performance
```
Total Orders:     25
On-Time:          25
Late:             0
On-Time %:        100.0%
```

---

### PART 4: THE TRADEOFFS (3 min)

**Open:** tradeoff_memo.txt

**Read:** Executive Summary
```
Recommended: ONTIME STRATEGY

RATIONALE:
• Tier-1 customer (60% revenue) requires JIT delivery
• Late penalties are substantial (₹25,000/hour)
• On-time delivery is key to customer retention
• Extra cost in overtime/penalties is justified by customer trust
```

**Show:** Three strategies comparison table

**Explain:**
- ONTIME: Best for revenue protection (100% on-time)
- CHEAPEST: Lowest cost if customer flexibility exists
- ROBUST: Maximum buffer time for disruption resistance

---

### PART 5: THE DISRUPTION HANDLING (5 min)

**Scenario:** "Tuesday 11 AM - Grinding machine breaks down for 8 hours"

**Navigate to:** Terminal

**Run Command:**
```bash
python manage.py handle_disruption --auto-detect --strategy ONTIME
```

**Show Output:**
```
DISRUPTION DETECTED: MACHINE_BREAKDOWN: GR01
Affected operations: 7
At-risk deliveries: 2

RECOMMENDATIONS
[CRITICAL] CUSTOMER ALERT
→ Contact AutoPrime Motors NOW. Inform of disruption.

[HIGH] AUTHORIZE OVERTIME  
→ Running overtime saves ₹X vs penalties

[HIGH] REROUTE TO ALTERNATIVE MACHINE
→ Speak with maintenance: Can GR01 be repaired in 7 hours?
```

**Explain:**
- System detects active disruption
- Analyzes impact (7 operations affected, 2 JIT orders at risk)
- Generates replanned schedule
- Provides specific phone call guidance to owner
- Calculates cost delta (additional cost from disruption)

---

### PART 6: THE INTERFACE (2 min)

**Show:** Schedule List
- Multiple strategies displayed
- Cost per strategy
- On-time % for each

**Show:** Admin Panel (if time)
- http://localhost:8000/admin/
- View schedules, operations, orders
- Create new breakdowns/absences for testing

---

## KEY NUMBERS TO REMEMBER

| Metric | Value |
|--------|-------|
| Factory Size | 40 people |
| Machines | 14 (5 CNC, 4 milling, 2 drilling, 1 grinding, 1 VMC, 1 inspection) |
| Operators | 18 |
| Grinding Operators | 3 (CRITICAL BOTTLENECK) |
| Open Orders | 25 |
| Operations | 103 |
| Planning Horizon | 14 days |
| Shift Hours | 8 AM-10 PM (8:6-14, 14-22, 22-6) |
| Current On-Time % | 100% |
| Current Total Cost | ₹183,250 (changeovers only) |
| Tier-1 Customer Revenue Share | 60% |
| Tier-1 Late Penalty | ₹25,000/hour |

---

## TALKING POINTS BY QUESTION

### Q: "How does the system know what's optimal?"

**A:** Google OR-Tools CP-SAT solver uses constraint programming:
- Decision variables: operation start times, machine assignments
- Constraints: shift windows, capacity, precedence, skills, breakdowns
- Objective: minimize total lateness (hours late × penalty)
- Solver finds globally optimal solution in 30 seconds

### Q: "What if there's a breakdown?"

**A:** System automatically:
1. Detects the breakdown
2. Analyzes which operations are affected
3. Reruns solver with disruption as fixed constraint
4. Shows what moved, what's at-risk
5. Calculates cost impact
6. Recommends actions (calls to make)

### Q: "Why is grinding machine so critical?"

**A:** Only 3 operators in shop can run it, and grinding is last operation before delivery for most jobs. If one of 3 is absent, system has zero slack.

### Q: "How much would the schedule change with disruptions?"

**A:** [Run demo] - Shows in real-time. Replanning takes <1 minute.

### Q: "Which strategy should we run?"

**A:** ONTIME - Because 60% of revenue from JIT customer with high penalties. ₹25K/hour penalty > overtime costs, so protecting delivery is higher ROI.

---

## CONTINGENCY - If Something Goes Wrong

### Issue: Web server won't start
**Solution:** 
```bash
python manage.py runserver 8000
# or
python manage.py runserver 127.0.0.1:8000
```

### Issue: Can't see today's operations
**Solution:** 
- Make sure database has data: `python manage.py shell`
- `from scheduler.models import ScheduledOperation; ScheduledOperation.objects.count()`
- Should be ~103

### Issue: Tradeoff memo file not found
**Solution:**
- It's in the project root: `./tradeoff_memo.txt`
- Can also regenerate: `python manage.py tradeoff_memo`

### Issue: Disruption command doesn't work
**Solution:**
- Make sure --auto-detect flag is used
- Or manually create a breakdown: `python manage.py shell`
```python
from scheduler.models import Breakdown, Machine
from django.utils import timezone
from datetime import timedelta

grinding = Machine.objects.get(machine_id='GR01')
Breakdown.objects.create(
    machine=grinding,
    start_time=timezone.now(),
    end_time=timezone.now() + timedelta(hours=8),
    reason="Spindle failure"
)
```

---

## HANDOVER MATERIALS FOR OWNER

### What They Get

1. **Baseline Schedule (Schedule ID: 1)**
   - Current 2-week production plan
   - All 25 orders scheduled
   - Projected 100% on-time delivery
   - Total cost: ₹183,250

2. **Trade-Off Memo (tradeoff_memo.txt)**
   - Three strategy comparison
   - Recommendation: ONTIME strategy
   - Risk assessment
   - Implementation notes

3. **Web Dashboard (http://localhost:8000/)**
   - Daily operations display
   - At-risk delivery alerts
   - Real-time schedule updates
   - Mobile-friendly interface

4. **Disruption Handling Protocol**
   - When breakdown happens: `python manage.py handle_disruption --auto-detect`
   - Gets new schedule in 1 minute
   - Shows exactly what phone calls to make

### First Month Goals

1. Generate schedule weekly (Monday morning)
2. Update for Tuesday/Wednesday disruptions
3. Track actual vs. planned performance
4. Collect feedback on recommendations quality
5. Adjust penalty rates based on actual customer impact

### Long-term Value

- **No more guesswork:** Data-driven decisions
- **Quantified tradeoffs:** See cost of every hour late
- **Reduced planning time:** 2 weeks in 30 seconds
- **Faster disruption response:** Replanning in 1 minute
- **Customer transparency:** Give accurate ETAs

---

## END-OF-DEMO SUMMARY

"Sridhar Precision Works can now:

✅ Generate optimal 2-week schedules in 30 seconds
✅ Quantify the cost of overtime vs. late penalties
✅ Identify the grinding machine as the true bottleneck
✅ Make customer-priority decisions data-driven
✅ Replan within minutes when disruptions occur
✅ Provide shift supervisors actionable daily guidance

The result: Eliminate the contradiction of paying both overtime AND penalties."

---

**Questions? See README.md for full documentation**
