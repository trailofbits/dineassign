# dineassign

Optimize restaurant assignments for team offsite dining. Given engineer preferences and confirmed reservations, assigns engineers to restaurants while maximizing overall satisfaction.

> **Note**: This project was entirely vibe-coded in a single session using [Claude Code](https://github.com/anthropics/claude-code).

## Installation

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Usage

```bash
# First run - creates a reservations template
uv run dineassign preferences.csv --days tuesday wednesday

# With reservations file
uv run dineassign preferences.csv --days tuesday wednesday --reservations reservations.yaml

# Custom group sizes
uv run dineassign preferences.csv --days tue wed --min-group-size 3 --max-group-size 6

# One-shot mode - full assignment assuming all restaurants available
uv run dineassign preferences.csv --days tuesday wednesday --one-shot

# Disable diversity optimization (allows repeated dining companions)
uv run dineassign preferences.csv --days tuesday wednesday --one-shot --diversity-weight 0
```

### Options

| Option | Description |
|--------|-------------|
| `preferences.csv` | Path to CSV with engineer preferences (required) |
| `--days` | Day names for the outing (required, e.g., `tuesday wednesday`) |
| `--reservations` | Path to reservations YAML file |
| `--min-group-size` | Minimum diners per restaurant (default: 4) |
| `--max-group-size` | Maximum diners per restaurant (default: 8) |
| `--output-template` | Path for generated template (default: `reservations_template.yaml`) |
| `--one-shot` | Output full assignment assuming all restaurants available |
| `--diversity-weight` | Weight for diversity penalty (default: auto-computed, 0 to disable) |

## Input Formats

### Preferences CSV

Export from Google Forms with columns:
- `Email Address` - Engineer identifier
- Restaurant columns with Likert scale responses:
  - `Have to eat here` - Strong preference
  - `Want to eat here` - Preference
  - `Neutral` - No preference
  - `Don't want to eat here` - Negative preference
  - `Can't eat here` - Hard constraint (dietary, etc.)

### Reservations YAML

```yaml
reservations:
  - restaurant: "Commander's Palace"
    day: tuesday
    capacity: 8
    status: confirmed
  - restaurant: "August"
    day: tuesday
    status: unavailable  # Tried but couldn't book
```

Status options:
- `confirmed` - Reservation is confirmed, engineers can be assigned
- `unavailable` - Restaurant couldn't accommodate (excluded from suggestions)
- `pending` - Reservation pending confirmation

## Algorithm

### Preference Normalization

Preferences are normalized per-engineer using Z-scores. This ensures relative rankings are respected: an engineer who marks only 2 restaurants as "Have to eat here" and everything else as "Don't want to eat here" will have those preferences weighted more heavily than someone who marks everything "Want to eat here".

### Optimization

Uses Integer Linear Programming (scipy.optimize.milp) to maximize total satisfaction subject to:

- **Hard constraint**: Engineers are never assigned to "Can't eat here" restaurants
- **Uniqueness**: Each engineer visits a different restaurant each day
- **Capacity**: Group sizes stay within min/max bounds per reservation
- **Diversity**: Minimizes repeated dining companions across days (secondary objective)

### Reservation Suggestions

When not all engineers can be assigned, the tool suggests the next reservation to make based on:
- Which day needs more capacity
- Aggregate preference scores across engineers
- Excluding restaurants already marked unavailable

## Example Output

```
Loaded 20 engineers and 12 restaurants
Loaded 6 confirmed reservations

=== Restaurant Assignments ===
Total satisfaction score: 35.82
Repeated pairings: 0

--- Tuesday ---
  Commander's Palace (4 diners):
    - alice (Have to eat here)
    - bob (Want to eat here)
    - charlie (Neutral)
    - eve (Want to eat here)

--- Wednesday ---
  Dakar NOLA (4 diners):
    - alice (Want to eat here)
    - carol (Have to eat here)
    - dave (Neutral)
    - eve (Want to eat here)

=== Preference Summary ===
Diner   | Can't | Don't want | Neutral | Want | Have to
-------------------------------------------------------
alice   | 0/1   | 0/2        | 0/4     | 1/3  | 1/2
bob     | 0/0   | 0/1        | 1/5     | 1/4  | 0/2
...

=== All reservations complete ===
No additional reservations needed.
```

The preference summary shows `X/Y` where X is the number of assignments and Y is the total restaurants rated in each category.

## License

AGPL-3.0. See [LICENSE](LICENSE) for details.
