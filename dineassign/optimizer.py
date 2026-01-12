"""ILP-based optimization for restaurant assignments."""

import numpy as np
from scipy.optimize import LinearConstraint, milp

from dineassign.models import Assignment, Engineer, OptimizationResult, Reservation
from dineassign.normalize import get_aggregate_preferences, normalize_preferences


def _var_index(
    e_idx: int,
    r_idx: int,
    d_idx: int,
    num_restaurants: int,
    num_days: int,
) -> int:
    """Convert (engineer, restaurant, day) indices to flat variable index."""
    return e_idx * (num_restaurants * num_days) + r_idx * num_days + d_idx


def optimize_assignments(
    engineers: list[Engineer],
    restaurants: list[str],
    days: list[str],
    reservations: list[Reservation],
    min_group_size: int = 4,
    max_group_size: int = 8,
    one_shot: bool = False,
) -> OptimizationResult:
    """
    Optimize restaurant assignments using Integer Linear Programming.

    Returns an OptimizationResult with assignments, total satisfaction,
    and a suggested next reservation if applicable.
    """
    num_engineers = len(engineers)
    num_restaurants = len(restaurants)
    num_days = len(days)
    num_assignment_vars = num_engineers * num_restaurants * num_days

    # In one-shot mode, add indicator variables for (restaurant, day) slots
    # y_{r,d} = 1 if restaurant r is used on day d, 0 otherwise
    num_indicator_vars = num_restaurants * num_days if one_shot else 0
    num_vars = num_assignment_vars + num_indicator_vars

    def _indicator_index(r_idx: int, d_idx: int) -> int:
        return num_assignment_vars + r_idx * num_days + d_idx

    # Normalize preferences
    normalized_prefs = normalize_preferences(engineers, restaurants)

    # Build restaurant/day -> reservation lookup
    confirmed_reservations: dict[tuple[str, str], Reservation] = {}
    unavailable: set[tuple[str, str]] = set()
    for res in reservations:
        key = (res.restaurant, res.day)
        if res.status == "confirmed":
            confirmed_reservations[key] = res
        elif res.status == "unavailable":
            unavailable.add(key)

    # Build objective: maximize satisfaction (negate for minimization)
    c = np.zeros(num_vars)
    for e_idx, engineer in enumerate(engineers):
        for r_idx, restaurant in enumerate(restaurants):
            pref = normalized_prefs[engineer.email][restaurant]
            for d_idx in range(num_days):
                var_idx = _var_index(e_idx, r_idx, d_idx, num_restaurants, num_days)
                if pref == float("-inf"):
                    # Can't eat here - set very negative coefficient
                    c[var_idx] = 1e6  # Large penalty (we're minimizing -satisfaction)
                else:
                    c[var_idx] = -pref  # Negate because milp minimizes

    # Build constraints
    A_eq_rows: list[np.ndarray] = []
    b_eq: list[float] = []
    A_ub_rows: list[np.ndarray] = []
    b_ub: list[float] = []

    # Constraint 1: Each engineer at exactly one restaurant per day
    for e_idx in range(num_engineers):
        for d_idx in range(num_days):
            row = np.zeros(num_vars)
            for r_idx in range(num_restaurants):
                var_idx = _var_index(e_idx, r_idx, d_idx, num_restaurants, num_days)
                row[var_idx] = 1.0
            A_eq_rows.append(row)
            b_eq.append(1.0)

    # Constraint 2: Each engineer at each restaurant at most once across all days
    for e_idx in range(num_engineers):
        for r_idx in range(num_restaurants):
            row = np.zeros(num_vars)
            for d_idx in range(num_days):
                var_idx = _var_index(e_idx, r_idx, d_idx, num_restaurants, num_days)
                row[var_idx] = 1.0
            A_ub_rows.append(row)
            b_ub.append(1.0)

    # Constraint 3: Group size bounds for confirmed reservations
    # For restaurants with confirmed reservations: min_size <= sum <= capacity
    # For restaurants without: sum = 0 (nobody can be assigned there yet)
    # For one-shot mode: either sum = 0 OR min_size <= sum <= max_size
    for r_idx, restaurant in enumerate(restaurants):
        for d_idx, day in enumerate(days):
            key = (restaurant, day)
            row = np.zeros(num_vars)
            for e_idx in range(num_engineers):
                var_idx = _var_index(e_idx, r_idx, d_idx, num_restaurants, num_days)
                row[var_idx] = 1.0

            if key in confirmed_reservations:
                res = confirmed_reservations[key]
                # sum >= min_group_size: -sum <= -min_group_size
                A_ub_rows.append(-row)
                b_ub.append(-min_group_size)
                # sum <= capacity
                A_ub_rows.append(row.copy())
                b_ub.append(float(res.capacity))
            elif one_shot:
                # One-shot: use indicator var y to model "sum=0 OR min<=sum<=max"
                # sum <= max * y (if y=0, sum=0; if y=1, sum<=max)
                # sum >= min * y (if y=0, sum>=0 trivially; if y=1, sum>=min)
                y_idx = _indicator_index(r_idx, d_idx)
                row_upper = row.copy()
                row_upper[y_idx] = -max_group_size
                A_ub_rows.append(row_upper)  # sum - max*y <= 0
                b_ub.append(0.0)
                row_lower = -row.copy()
                row_lower[y_idx] = min_group_size
                A_ub_rows.append(row_lower)  # -sum + min*y <= 0
                b_ub.append(0.0)
            else:
                # No reservation - nobody can be assigned
                A_eq_rows.append(row)
                b_eq.append(0.0)

    # Constraint 4: Hard exclusions (Can't eat here)
    # Already handled via large penalty in objective, but add explicit bounds
    bounds_lower = np.zeros(num_vars)
    bounds_upper = np.ones(num_vars)  # All vars (assignment + indicator) are binary [0,1]
    for e_idx, engineer in enumerate(engineers):
        for r_idx, restaurant in enumerate(restaurants):
            if normalized_prefs[engineer.email][restaurant] == float("-inf"):
                for d_idx in range(num_days):
                    var_idx = _var_index(e_idx, r_idx, d_idx, num_restaurants, num_days)
                    bounds_upper[var_idx] = 0.0  # Force to 0

    # Convert to arrays
    A_eq = np.array(A_eq_rows) if A_eq_rows else None
    b_eq_arr = np.array(b_eq) if b_eq else None
    A_ub = np.array(A_ub_rows) if A_ub_rows else None
    b_ub_arr = np.array(b_ub) if b_ub else None

    # Build constraints for milp
    constraints = []
    if A_eq is not None and b_eq_arr is not None:
        constraints.append(LinearConstraint(A_eq, b_eq_arr, b_eq_arr))
    if A_ub is not None and b_ub_arr is not None:
        constraints.append(LinearConstraint(A_ub, -np.inf, b_ub_arr))

    from scipy.optimize import Bounds

    bounds = Bounds(bounds_lower, bounds_upper)
    integrality = np.ones(num_vars, dtype=np.intp)  # All binary

    # Solve
    result = milp(c, constraints=constraints, bounds=bounds, integrality=integrality)

    if not result.success:
        # Try to provide useful feedback
        return OptimizationResult(
            assignments=[],
            total_satisfaction=0.0,
            suggested_reservation=_suggest_reservation(
                engineers,
                restaurants,
                days,
                confirmed_reservations,
                unavailable,
                normalized_prefs,
                min_group_size,
                max_group_size,
            ),
        )

    # Extract assignments
    assert result.x is not None  # Guaranteed by result.success check above
    x = result.x
    assignments: list[Assignment] = []
    total_satisfaction = 0.0

    for e_idx, engineer in enumerate(engineers):
        for r_idx, restaurant in enumerate(restaurants):
            for d_idx, day in enumerate(days):
                var_idx = _var_index(e_idx, r_idx, d_idx, num_restaurants, num_days)
                if x[var_idx] > 0.5:  # Binary, so check > 0.5
                    pref_score = normalized_prefs[engineer.email][restaurant]
                    assignments.append(
                        Assignment(
                            engineer_email=engineer.email,
                            restaurant=restaurant,
                            day=day,
                            preference_score=pref_score if pref_score != float("-inf") else 0.0,
                        )
                    )
                    if pref_score != float("-inf"):
                        total_satisfaction += pref_score

    # Suggest next reservation
    suggested = _suggest_reservation(
        engineers,
        restaurants,
        days,
        confirmed_reservations,
        unavailable,
        normalized_prefs,
        min_group_size,
        max_group_size,
    )

    return OptimizationResult(
        assignments=assignments,
        total_satisfaction=total_satisfaction,
        suggested_reservation=suggested,
    )


def _suggest_reservation(
    engineers: list[Engineer],
    restaurants: list[str],
    days: list[str],
    confirmed: dict[tuple[str, str], Reservation],
    unavailable: set[tuple[str, str]],
    normalized_prefs: dict[str, dict[str, float]],
    min_group_size: int,
    max_group_size: int,
) -> tuple[str, str, int] | None:
    """Suggest the next reservation to make."""
    num_engineers = len(engineers)

    # Count how many engineers can eat at each restaurant (not "Can't eat")
    can_eat_count: dict[str, int] = {}
    for restaurant in restaurants:
        count = sum(1 for prefs in normalized_prefs.values() if prefs[restaurant] != float("-inf"))
        can_eat_count[restaurant] = count

    # Get aggregate preferences
    aggregates = get_aggregate_preferences(normalized_prefs, restaurants)

    # Count current capacity per day
    day_capacity: dict[str, int] = {day: 0 for day in days}
    for (_restaurant, day), res in confirmed.items():
        if day in day_capacity:
            day_capacity[day] += res.capacity

    # Find which day needs more capacity
    engineers_per_day = num_engineers
    days_needing_capacity = [
        (day, engineers_per_day - day_capacity[day])
        for day in days
        if day_capacity[day] < engineers_per_day
    ]

    if not days_needing_capacity:
        return None  # All days have enough capacity

    # Sort by most capacity needed
    days_needing_capacity.sort(key=lambda x: -x[1])

    # Find best (restaurant, day) combination
    best: tuple[str, str, int] | None = None
    best_score = float("-inf")

    for day, capacity_needed in days_needing_capacity:
        for restaurant in restaurants:
            key = (restaurant, day)
            if key in confirmed or key in unavailable:
                continue

            # Skip if not enough people can eat there
            if can_eat_count[restaurant] < min_group_size:
                continue

            # Score = aggregate preference + bonus for capacity fit
            score = aggregates[restaurant]
            suggested_capacity = min(max_group_size, capacity_needed, can_eat_count[restaurant])

            if score > best_score and suggested_capacity >= min_group_size:
                best_score = score
                best = (restaurant, day, suggested_capacity)

    return best
