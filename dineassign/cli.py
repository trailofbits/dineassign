"""Command-line interface for dineassign."""

import argparse
import sys
from pathlib import Path

from dineassign.optimizer import optimize_assignments
from dineassign.output import format_results
from dineassign.parser import (
    create_reservations_template,
    parse_preferences_csv,
    parse_reservations_yaml,
)


def main() -> int:
    """Main entry point for dineassign CLI."""
    parser = argparse.ArgumentParser(
        description="Optimize restaurant assignments for team offsite dining.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  dineassign preferences.csv --days tuesday wednesday
  dineassign preferences.csv --days tuesday wednesday --reservations reservations.yaml
  dineassign preferences.csv --days mon tue wed --min-group-size 3 --max-group-size 6
""",
    )
    parser.add_argument(
        "preferences_csv",
        type=Path,
        help="Path to the CSV file with engineer preferences",
    )
    parser.add_argument(
        "--days",
        nargs="+",
        required=True,
        help="Day names for the outing (e.g., tuesday wednesday)",
    )
    parser.add_argument(
        "--reservations",
        type=Path,
        help="Path to the reservations YAML file",
    )
    parser.add_argument(
        "--min-group-size",
        type=int,
        default=4,
        help="Minimum diners per restaurant (default: 4)",
    )
    parser.add_argument(
        "--max-group-size",
        type=int,
        default=8,
        help="Maximum diners per restaurant (default: 8)",
    )
    parser.add_argument(
        "--output-template",
        type=Path,
        help="Path for reservations template (default: reservations_template.yaml)",
    )
    parser.add_argument(
        "--one-shot",
        action="store_true",
        help="Assume all restaurants available with capacity=max-group-size",
    )
    parser.add_argument(
        "--diversity-weight",
        type=float,
        default=None,
        help="Weight for diversity penalty (default: auto-computed, 0=disabled)",
    )

    args = parser.parse_args()

    # Normalize day names to lowercase
    days = [d.lower() for d in args.days]

    # Validate preferences CSV exists
    if not args.preferences_csv.exists():
        print(f"Error: Preferences file not found: {args.preferences_csv}", file=sys.stderr)
        return 1

    # Parse preferences
    try:
        engineers, restaurants = parse_preferences_csv(args.preferences_csv)
    except Exception as e:
        print(f"Error parsing preferences CSV: {e}", file=sys.stderr)
        return 1

    print(f"Loaded {len(engineers)} engineers and {len(restaurants)} restaurants")

    # Parse or create reservations
    reservations = []
    if args.reservations:
        if args.reservations.exists():
            try:
                reservations = parse_reservations_yaml(args.reservations)
                confirmed = [r for r in reservations if r.status == "confirmed"]
                print(f"Loaded {len(confirmed)} confirmed reservations")
            except Exception as e:
                print(f"Error parsing reservations YAML: {e}", file=sys.stderr)
                return 1
        else:
            print(f"Error: Reservations file not found: {args.reservations}", file=sys.stderr)
            return 1

    if not reservations:
        # No reservations - create template and suggest first reservation
        template_path = args.output_template or Path("reservations_template.yaml")
        create_reservations_template(template_path, restaurants, days)
        print(f"\nNo reservations file provided. Created template at: {template_path}")
        print("Edit this file to add your confirmed reservations, then run again.\n")

    # Run optimization
    result = optimize_assignments(
        engineers=engineers,
        restaurants=restaurants,
        days=days,
        reservations=reservations,
        min_group_size=args.min_group_size,
        max_group_size=args.max_group_size,
        one_shot=args.one_shot,
        diversity_weight=args.diversity_weight,
    )

    # Output results
    print()
    print(format_results(result, days))

    return 0


if __name__ == "__main__":
    sys.exit(main())
