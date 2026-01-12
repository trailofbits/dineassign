# dineassign

Restaurant assignment optimizer for team offsite dining.

## Architecture

- `models.py` - Data classes (Engineer, Reservation, Assignment, OptimizationResult)
- `parser.py` - CSV preferences and YAML reservations parsing
- `normalize.py` - Z-score normalization per engineer
- `optimizer.py` - ILP formulation using scipy.optimize.milp
- `output.py` - Result formatting
- `cli.py` - Command-line interface

## Key Design Decisions

**Z-score normalization**: Preferences are normalized per-engineer so relative rankings matter. An engineer who rates most restaurants poorly but two highly should have those preferences weighted more than someone who rates everything highly.

**ILP over heuristics**: The problem size (~500 binary variables for 20 engineers, 12 restaurants, 2 days) is tractable for scipy's MILP solver. This guarantees optimal solutions rather than approximations.

**"Can't eat here" as hard constraint**: Implemented via variable bounds (forced to 0) and large penalty in objective. Never violated.

## Testing

```bash
# Run with sample data (no reservations - creates template)
uv run dineassign "2026 R&E Offsite Dining (Responses) - Form Responses 1.csv" --days tuesday wednesday

# One-shot mode - full assignment without reservations
uv run dineassign "2026 R&E Offsite Dining (Responses) - Form Responses 1.csv" --days tuesday wednesday --one-shot

# Verify linting and types
uv run ruff check dineassign
uv run ty check
```

When testing assignments, verify:
1. No engineer assigned to a "Can't eat here" restaurant
2. Each engineer at a different restaurant each day
3. Group sizes within bounds
4. Total capacity >= number of engineers per day

## Constraints

- Minimum group size default is 4 (restaurants typically won't take smaller parties)
- Maximum group size default is 8 (manageable for conversation)
- Reservations must be confirmed before engineers can be assigned
