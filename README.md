# Sridhar Precision Works - Production Scheduler

A sophisticated production scheduling and disruption management system using Google OR-Tools constraint programming and Django.

## Overview

This system addresses the core scheduling challenge at Sridhar Precision Works, a 40-person auto-components machine shop in Hosur, India:

> **The Problem**: "Every month I pay overtime AND late-delivery penalties. Both. How is that possible?"

The system generates optimal 2-week production schedules considering:
- Multi-step job routings (3-6 operations per order)
- Sequence-dependent changeovers (20 min - 3 hours)
- Customer priority (60% revenue from one tier-1 JIT customer)
- Operator skill constraints (only 3 people can run grinding machine)
- Machine breakdowns and maintenance windows
- Operator absences and material delays
- Overtime costs vs. late delivery penalties

## Project Structure

```
sridhar_precision_scheduler/
├── config/                          # Django configuration
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── scheduler/                       # Main app
│   ├── models.py                   # Database models
│   ├── views.py                    # Web views
│   ├── urls.py                     # URL routing
│   ├── admin.py                    # Django admin
│   ├── scheduler_engine.py         # OR-Tools scheduler
│   ├── tests.py
│   ├── data/
│   │   ├── generator.py            # Factory data generation
│   ├── management/
│   │   └── commands/
│   │       ├── generate_data.py    # Generate test data
│   │       ├── schedule.py         # Generate schedules
│   │       ├── handle_disruption.py # Handle disruptions
│   │       └── tradeoff_memo.py    # Generate trade-off analysis
│   ├── services/
│   │   ├── cost_calculator.py      # Cost & metrics
│   │   ├── disruption_engine.py    # Replanning logic
│   │   └── changeover.py
│   └── templates/scheduler/        # HTML templates
├── db.sqlite3                       # SQLite database
└── manage.py

```

## Key Components

### 1. Data Model (`models.py`)

- **Customer**: Tiers, revenue share, penalty rates
- **Machine**: Type, capabilities, active status
- **Operator**: Skills, availability, overtime eligibility
- **Shift**: Morning, Evening, Night (overtime)
- **Order**: Part number, quantity, due date, customer
- **Operation**: Sequence, type, duration, machine/skill requirements
- **Schedule**: Generated schedule with cost breakdown
- **ScheduledOperation**: Individual machine-operator-time assignments
- **Breakdown/Maintenance/OperatorAbsence**: Disruptions
- **Changeover**: Sequence-dependent setup times and costs

### 2. Scheduler Engine (`scheduler_engine.py`)

Uses Google OR-Tools CP-SAT solver to optimize:

**Decision Variables:**
- Start time for each operation (constrained to valid shift windows)
- Machine-operator assignment for each operation

**Constraints:**
- Shift windows (operations must fit completely inside shifts)
- Machine capacity (no overlaps)
- Operator capacity (no overlaps)
- Operation precedence (order within jobs)
- Machine breakdowns/maintenance (unavailable intervals)
- Operator absences (unavailable intervals)
- Material availability (can't start before material arrives)
- Skill requirements (operator must have required skill)

**Objective:**
- Minimize total lateness (sum of hours late across all orders)

### 3. Cost Calculator (`services/cost_calculator.py`)

Calculates four cost categories:

```
Total Cost = Overtime + Penalties + Changeovers + Generator
```

- **Overtime**: Night shift (2x), Sunday (1.5x), additional shifts
- **Penalties**: Late delivery penalties per hour (varies by customer tier)
- **Changeovers**: Part family switching costs (20 min - 3 hours)
- **Generator**: Diesel generator for power cuts (3x cost)

Also provides:
- On-time metrics (% of orders delivered on schedule)
- Robustness metrics (average buffer time between operations)

### 4. Disruption Engine (`services/disruption_engine.py`)

Handles real-time disruptions:

- **Machine Breakdown**: Blocks machine for duration, affects downstream operations
- **Operator Absence**: Removes operator from resource pool
- **Material Delay**: Delays order start until material arrives
- **Rework**: Reintroduces failed pieces back into queue

**Replanning Strategy:**
1. Detects active disruptions
2. Analyzes impact (affected operations, at-risk deliveries)
3. Re-optimizes schedule around disruption
4. Generates actionable recommendations
5. Calculates cost impact (delta from original schedule)

### 5. Management Commands

#### `python manage.py generate_data`
Populates database with realistic factory data:
- 5 customers (1 tier-1 JIT, 4 others)
- 14 machines (5 CNC, 4 milling, 2 drilling, 1 grinding, 1 VMC, 1 inspection)
- 18 operators (5 turning, 4 milling, 3 drilling, 3 grinding, 3 inspection)
- 25 open orders with 3-6 operations each
- 10 machine breakdowns
- 14 maintenance windows
- 5 operator absences
- 5 material delays

#### `python manage.py schedule --show-costs --show-metrics`
Generates baseline 2-week schedule:
- Solves CP-SAT model
- Saves schedule to database
- Shows cost breakdown and metrics

**Options:**
```
--strategy {ONTIME,CHEAPEST,ROBUST}  # Optimization strategy
--name TEXT                          # Schedule name
--show-costs                         # Display cost details
--show-metrics                       # Display metrics
```

#### `python manage.py handle_disruption [OPTIONS]`
Replans schedule after a disruption:
- `--breakdown ID`        - Handle machine breakdown
- `--absence ID`          - Handle operator absence
- `--material-delay ID`   - Handle material delay
- `--auto-detect`         - Auto-detect active disruptions
- `--current-schedule ID` - Specify schedule to replan
- `--strategy {ONTIME,CHEAPEST,ROBUST}`

**Example:**
```bash
python manage.py handle_disruption --breakdown 1 --current-schedule 1 --strategy ONTIME
```

#### `python manage.py tradeoff_memo`
Generates comprehensive trade-off analysis comparing three strategies:
- ONTIME: Minimizes late deliveries
- CHEAPEST: Minimizes total cost
- ROBUST: Maximizes buffer time

Saves to `tradeoff_memo.txt` with:
- Executive summary
- Detailed cost/metric comparison
- Risk assessment
- Implementation notes

## Web Interface

### Supervisor Dashboard
URL: `http://localhost:8000/`

**Displays:**
- Today's operations (machine, operator, order, time)
- At-risk deliveries (due soon but possibly late)
- Key metrics (total cost, on-time %, robustness score)
- Quick links to detailed views

**Design:** Color-coded, large text for easy reading by supervisors

### Schedule List
URL: `http://localhost:8000/schedules/`

Shows all generated schedules with:
- ID, name, strategy type
- Number of operations
- Total cost
- On-time percentage
- Creation time

### Schedule Detail
URL: `http://localhost:8000/schedules/<id>/`

Comprehensive schedule view:
- Cost breakdown (pie chart data ready)
- Performance metrics
- Machine-by-machine schedule table
- Order completion times
- Status (on-time/late)

## Usage Examples

### 1. Initial Setup

```bash
# Create virtual environment
python -m venv venv
source venv/Scripts/activate

# Install dependencies
pip install django ortools

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Generate factory data
python manage.py generate_data
```

### 2. Generate First Schedule

```bash
python manage.py schedule --show-costs --show-metrics
```

Output:
```
✓ Schedule generated: 1

--- COST BREAKDOWN ---
Overtime Cost:     ₹0.00
Penalty Cost:      ₹0.00
Changeover Cost:   ₹183,250.00
Generator Cost:    ₹0.00
TOTAL COST:        ₹183,250.00

--- PERFORMANCE METRICS ---
Total Orders:      25
On-Time Orders:    25
Late Orders:       0
On-Time %:         100.0%
Avg Buffer:        229.6 min
Robustness Score:  3.8/100
```

### 3. View Web Dashboard

```bash
python manage.py runserver
```

Visit `http://localhost:8000/` in browser

### 4. Generate Trade-Off Memo

```bash
python manage.py tradeoff_memo
```

Generates `tradeoff_memo.txt` with three strategy comparison

### 5. Handle a Disruption

```bash
# Auto-detect and replan
python manage.py handle_disruption --auto-detect --strategy ONTIME

# Or specify specific disruption
python manage.py handle_disruption --breakdown 1 --current-schedule 1
```

Output shows:
- Affected operations count
- At-risk deliveries
- Recommendations (with action items)
- Cost delta

## Disruption Simulation

For the defense session, inject disruptions:

### Scenario: Grinding Machine Breakdown

```bash
# In Django shell:
from scheduler.models import Breakdown, Machine
from django.utils import timezone
from datetime import timedelta

grinding = Machine.objects.get(machine_id='GR01')
Breakdown.objects.create(
    machine=grinding,
    start_time=timezone.now() + timedelta(hours=2),
    end_time=timezone.now() + timedelta(hours=10),
    reason="Spindle failure - emergency repair"
)

# Then replan:
# python manage.py handle_disruption --auto-detect
```

### Scenario: Grinding Operator Absent

```bash
from scheduler.models import OperatorAbsence, Operator
from django.utils import timezone
from datetime import timedelta

grinding_op = Operator.objects.filter(
    skills__contains='GRINDING'
).first()

OperatorAbsence.objects.create(
    operator=grinding_op,
    start_time=timezone.now() + timedelta(hours=2),
    end_time=timezone.now() + timedelta(hours=10),
    reason="Medical emergency"
)

# Then replan
```

## Key Design Decisions

### 1. Sequence-Dependent Changeovers
Instead of fixed setup time, changeover duration depends on:
- Part family similarity
- Machine type
- Previous operation

**Implementation:** `Changeover` model stores from_family → to_family durations

### 2. Grinding Machine Bottleneck
Only 3 operators can run the grinding machine (critical constraint):
- Model restricts skill="GRINDING" to 3 operators
- Any absence = urgent issue
- Prioritize scheduling grinding operations early

### 3. Customer Tiers
JIT customers (tier-1) get priority:
- Penalties are much higher (₹25,000/hour for AutoPrime)
- Scheduler minimizes their lateness
- Early warning system for at-risk deliveries

### 4. Cost-Based Tradeoffs
Present three schedules to decision-maker:
- **ONTIME**: Best for JIT customer (100% on-time)
- **CHEAPEST**: Lowest total cost (maybe some late orders)
- **ROBUST**: Most buffer time (best for disruptions)

Owner chooses based on business priorities.

### 5. Shift Constraints
Operations must fit completely inside shifts:
- Morning: 6 AM - 2 PM
- Evening: 2 PM - 10 PM
- Night: 10 PM - 6 AM (overtime)

Prevents operations from spanning shifts.

## Algorithm: OR-Tools CP-SAT

### Model Building
1. Create integer variables for operation start times
2. Domain: valid start-time intervals based on shifts
3. Create boolean variables for machine-operator assignments
4. Create interval variables for scheduling

### Constraints
- `model.add(end == start + duration)`
- `model.add_no_overlap(intervals)` for capacity
- `model.add(current_start >= previous_end)` for precedence
- Fixed interval variables for unavailable periods

### Objective
- `model.minimize(sum(lateness_variables))`

### Solver
- CP-SAT solver with 30-second time limit
- 8 parallel workers for faster solving
- Returns OPTIMAL or FEASIBLE solution

## Performance Metrics

### On-Time Delivery %
```
On-Time % = (Orders delivered ≤ due_date) / Total Orders × 100%
```

### Robustness Score (0-100)
```
Robustness = min(100, Avg_Buffer_Minutes / 60)
```

Average gap between consecutive operations on a machine.
- 0-30 min: Fragile (< 20/100)
- 30-60 min: Moderate (20-60/100)
- 60+ min: Robust (>80/100)

### Cost Per Order
```
Cost_Per_Order = Total_Cost / Number_Of_Orders
```

## Future Enhancements

1. **Multi-Objective Optimization**
   - Pareto frontier of cost vs. on-time vs. robustness
   - Interactive weight adjustment

2. **Predictive Disruption**
   - Historical breakdown patterns
   - Predict high-risk periods
   - Proactive scheduling

3. **Quality Integration**
   - Rework batches (2-5% failure rate)
   - Rework scheduling as priority queues
   - Root cause analysis

4. **Advanced Interfaces**
   - Gantt chart visualization
   - Real-time drag-and-drop rescheduling
   - Mobile app for shop floor

5. **Machine Learning**
   - Predict operator productivity
   - Changeover time refinement
   - Anomaly detection

## Defense Session Readiness

### Data Ready
✓ 25 open orders with realistic routings
✓ 14 machines with capabilities
✓ 18 operators with skill constraints
✓ 10 machine breakdowns in history
✓ Sequence-dependent changeover matrix

### Schedules Ready
✓ Baseline on-time schedule (Schedule ID: 1)
✓ Trade-off memo with 3 strategies (Schedules 2, 3, 4)
✓ All costs calculated and validated

### Disruption Handling Ready
✓ Disruption detection engine
✓ Replanning algorithm
✓ Impact analysis
✓ Recommendation system

### Supervisor Interface Ready
✓ Web dashboard with today's operations
✓ At-risk delivery alerts
✓ Schedule list and detail views
✓ Cost and metric displays

### Commands Ready
```bash
# Simulate disruption
python manage.py handle_disruption --auto-detect

# Show memo
cat tradeoff_memo.txt

# View dashboard
python manage.py runserver
# Visit http://localhost:8000/
```

## Support

For questions or issues, refer to:
1. This README.md
2. Code comments in each module
3. Django admin interface at `/admin/`
4. Management command help: `python manage.py <command> --help`

---

**Sridhar Precision Works © 2024**
Powered by Django + Google OR-Tools
