"""Output formatting for dineassign."""

from collections import defaultdict

from dineassign.models import OptimizationResult


def format_results(result: OptimizationResult, days: list[str]) -> str:
    """Format optimization results for display."""
    lines: list[str] = []

    if not result.assignments:
        lines.append("No assignments could be made.")
        lines.append("This may be because there are no confirmed reservations yet.")
    else:
        lines.append("=== Restaurant Assignments ===")
        lines.append(f"Total satisfaction score: {result.total_satisfaction:.2f}")
        lines.append(f"Repeated pairings: {result.repeated_pairings}")
        lines.append("")

        # Group by day and restaurant
        by_day_restaurant: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for assignment in result.assignments:
            by_day_restaurant[assignment.day][assignment.restaurant].append(
                assignment.engineer_email.split("@")[0]  # Use name part of email
            )

        for day in days:
            if day not in by_day_restaurant:
                continue
            lines.append(f"--- {day.title()} ---")
            for restaurant, engineers in sorted(by_day_restaurant[day].items()):
                lines.append(f"  {restaurant} ({len(engineers)} diners):")
                for eng in sorted(engineers):
                    lines.append(f"    - {eng}")
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
