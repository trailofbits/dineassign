"""Output formatting for dineassign."""

from collections import defaultdict

from dineassign.models import Engineer, OptimizationResult
from dineassign.parser import LIKERT_LABELS


def format_results(
    result: OptimizationResult,
    days: list[str],
    engineers: list[Engineer] | None = None,
) -> str:
    """Format optimization results for display."""
    lines: list[str] = []

    # Build lookup for engineer preferences
    eng_by_email: dict[str, Engineer] = {}
    if engineers:
        eng_by_email = {e.email: e for e in engineers}

    if not result.assignments:
        lines.append("No assignments could be made.")
        lines.append("This may be because there are no confirmed reservations yet.")
    else:
        lines.append("=== Restaurant Assignments ===")
        lines.append(f"Total satisfaction score: {result.total_satisfaction:.2f}")
        lines.append(f"Repeated pairings: {result.repeated_pairings}")
        lines.append("")

        # Group by day and restaurant, storing (name, email) tuples
        by_day_restaurant: dict[str, dict[str, list[tuple[str, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for assignment in result.assignments:
            name = assignment.engineer_email.split("@")[0]
            by_day_restaurant[assignment.day][assignment.restaurant].append(
                (name, assignment.engineer_email)
            )

        for day in days:
            if day not in by_day_restaurant:
                continue
            lines.append(f"--- {day.title()} ---")
            for restaurant, diners in sorted(by_day_restaurant[day].items()):
                lines.append(f"  {restaurant} ({len(diners)} diners):")
                for name, email in sorted(diners):
                    # Look up preference label if we have engineer data
                    pref_suffix = ""
                    if email in eng_by_email:
                        eng = eng_by_email[email]
                        raw_pref = eng.preferences.get(restaurant)
                        label = LIKERT_LABELS.get(raw_pref, "Neutral")
                        pref_suffix = f" ({label})"
                    lines.append(f"    - {name}{pref_suffix}")
            lines.append("")

        # Add preference summary if we have engineer data
        if engineers:
            lines.append(format_preference_summary(result, engineers))
            lines.append("")

    # Suggestion
    if result.suggested_reservation:
        restaurant, day, capacity = result.suggested_reservation
        lines.append("=== Next Reservation Suggestion ===")
        lines.append(f"Restaurant: {restaurant}")
        lines.append(f"Day: {day.title()}")
        lines.append(f"Suggested party size: {capacity}")
    elif result.assignments:
        lines.append("=== All reservations complete ===")
        lines.append("No additional reservations needed.")

    return "\n".join(lines)


def format_preference_summary(
    result: OptimizationResult,
    engineers: list[Engineer],
) -> str:
    """Format a summary table of preference distributions and assignments."""
    # Category order: Can't, Don't want, Neutral, Want, Have to
    categories = [
        (None, "Can't"),
        (1, "Don't want"),
        (2, "Neutral"),
        (3, "Want"),
        (4, "Have to"),
    ]

    # Build assignment lookup: email -> list of (restaurant, day) tuples
    assignments_by_eng: dict[str, list[str]] = defaultdict(list)
    for asn in result.assignments:
        assignments_by_eng[asn.engineer_email].append(asn.restaurant)

    # Build rows: (name, [(assigned, total) for each category])
    rows: list[tuple[str, list[tuple[int, int]]]] = []
    for eng in sorted(engineers, key=lambda e: e.email.split("@")[0]):
        name = eng.email.split("@")[0]
        assigned_restaurants = set(assignments_by_eng.get(eng.email, []))

        cat_stats: list[tuple[int, int]] = []
        for score, _ in categories:
            # Count restaurants rated in this category
            rated = [r for r, pref in eng.preferences.items() if pref == score]
            total = len(rated)
            # Count how many of those were assigned
            assigned = len([r for r in rated if r in assigned_restaurants])
            cat_stats.append((assigned, total))

        rows.append((name, cat_stats))

    # Format table with aligned columns
    headers = ["Diner"] + [label for _, label in categories]
    col_widths = [max(len(headers[0]), max(len(r[0]) for r in rows) if rows else 5)]
    for i, (_, label) in enumerate(categories):
        max_cell = max(len(f"{r[1][i][0]}/{r[1][i][1]}") for r in rows) if rows else 3
        col_widths.append(max(len(label), max_cell))

    # Build header row
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = "-" * len(header_line)

    lines = ["=== Preference Summary ===", header_line, separator]

    for name, stats in rows:
        cells = [name.ljust(col_widths[0])]
        for i, (assigned, total) in enumerate(stats):
            cell = f"{assigned}/{total}"
            cells.append(cell.ljust(col_widths[i + 1]))
        lines.append(" | ".join(cells))

    return "\n".join(lines)


def format_assignments_csv(result: OptimizationResult, days: list[str]) -> str:
    """Format assignments as CSV for export."""
    lines: list[str] = ["engineer,day,restaurant,preference_score"]

    # Sort by day, then restaurant, then engineer
    sorted_assignments = sorted(
        result.assignments,
        key=lambda a: (days.index(a.day) if a.day in days else 99, a.restaurant, a.engineer_email),
    )

    for assignment in sorted_assignments:
        lines.append(
            f"{assignment.engineer_email},{assignment.day},{assignment.restaurant},"
            f"{assignment.preference_score:.3f}"
        )

    return "\n".join(lines)
