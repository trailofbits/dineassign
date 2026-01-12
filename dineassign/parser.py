"""CSV and YAML parsing for dineassign."""

import csv
from pathlib import Path

import yaml

from dineassign.models import Engineer, Reservation

# Likert scale mapping: higher = more preferred
LIKERT_SCORES: dict[str, int | None] = {
    "Have to eat here": 4,
    "Want to eat here": 3,
    "Neutral": 2,
    "Don't want to eat here": 1,
    "Can't eat here": None,  # Hard constraint - excluded
}


def parse_preferences_csv(csv_path: Path) -> tuple[list[Engineer], list[str]]:
    """
    Parse the preferences CSV file.

    Returns a tuple of (list of Engineers, list of restaurant names).
    """
    engineers: list[Engineer] = []
    restaurants: list[str] = []

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        # Find restaurant columns (everything after dietary restrictions)
        # Look for columns that aren't metadata
        metadata_columns = {
            "Timestamp",
            "Email Address",
            "Dining Out Days",
            "Do you have any dietary restrictions?",
        }

        for col in fieldnames:
            # Skip metadata and empty columns (like "Column 5")
            if col not in metadata_columns and col.strip() and not col.startswith("Column "):
                restaurants.append(col)

        for row in reader:
            email = row.get("Email Address", "").strip()
            if not email:
                continue

            preferences: dict[str, int | None] = {}
            for restaurant in restaurants:
                raw_pref = row.get(restaurant, "").strip()
                if raw_pref in LIKERT_SCORES:
                    preferences[restaurant] = LIKERT_SCORES[raw_pref]
                elif raw_pref == "":
                    # Empty response treated as Neutral
                    preferences[restaurant] = LIKERT_SCORES["Neutral"]
                else:
                    # Unknown response, treat as Neutral
                    preferences[restaurant] = LIKERT_SCORES["Neutral"]

            engineers.append(Engineer(email=email, preferences=preferences))

    return engineers, restaurants


def parse_reservations_yaml(yaml_path: Path) -> list[Reservation]:
    """Parse the reservations YAML file."""
    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "reservations" not in data:
        return []

    reservations: list[Reservation] = []
    for entry in data["reservations"]:
        reservations.append(
            Reservation(
                restaurant=entry["restaurant"],
                day=entry["day"].lower(),
                capacity=entry.get("capacity", 0),
                status=entry.get("status", "pending"),
            )
        )

    return reservations


def create_reservations_template(output_path: Path, restaurants: list[str], days: list[str]):
    """Create an empty reservations template YAML file."""
    template = {
        "reservations": [
            {
                "restaurant": restaurants[0] if restaurants else "Restaurant Name",
                "day": days[0] if days else "tuesday",
                "capacity": 8,
                "status": "confirmed",
            }
        ]
    }

    # Add a comment header
    header = f"""\
# Reservations file for dineassign
# Add your confirmed reservations here.
#
# Available restaurants: {", ".join(restaurants)}
# Days: {", ".join(days)}
#
# Status options:
#   - confirmed: Reservation is confirmed
#   - unavailable: Tried to book but restaurant couldn't accommodate
#   - pending: Reservation request is pending
#
# Example entry:
#   - restaurant: "Commander's Palace"
#     day: tuesday
#     capacity: 8
#     status: confirmed

"""

    with output_path.open("w", encoding="utf-8") as f:
        f.write(header)
        yaml.dump(template, f, default_flow_style=False, sort_keys=False)
