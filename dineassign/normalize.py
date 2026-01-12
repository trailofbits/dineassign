"""Preference normalization for dineassign."""

import statistics

from dineassign.models import Engineer


def normalize_preferences(
    engineers: list[Engineer],
    restaurants: list[str],
) -> dict[str, dict[str, float]]:
    """
    Normalize preferences using Z-score per engineer.

    Returns a dict mapping engineer_email -> restaurant -> normalized_score.
    Restaurants where an engineer "Can't eat" are mapped to negative infinity.
    """
    normalized: dict[str, dict[str, float]] = {}

    for engineer in engineers:
        # Collect non-excluded scores for this engineer
        valid_scores = [score for score in engineer.preferences.values() if score is not None]

        if not valid_scores:
            # All restaurants excluded - this is a problem
            normalized[engineer.email] = {r: float("-inf") for r in restaurants}
            continue

        mean = statistics.mean(valid_scores)
        stdev = statistics.stdev(valid_scores) if len(valid_scores) > 1 else 1.0

        # Avoid division by zero for engineers who rated everything the same
        if stdev == 0:
            stdev = 1.0

        engineer_prefs: dict[str, float] = {}
        for restaurant in restaurants:
            raw_score = engineer.preferences.get(restaurant)
            if raw_score is None:
                # Can't eat here - hard constraint
                engineer_prefs[restaurant] = float("-inf")
            else:
                # Z-score normalization
                engineer_prefs[restaurant] = (raw_score - mean) / stdev

        normalized[engineer.email] = engineer_prefs

    return normalized


def get_aggregate_preferences(
    normalized_prefs: dict[str, dict[str, float]],
    restaurants: list[str],
) -> dict[str, float]:
    """
    Compute aggregate preference score per restaurant.

    Returns a dict mapping restaurant -> sum of normalized preferences
    (excluding -inf values from "Can't eat" responses).
    """
    aggregates: dict[str, float] = {r: 0.0 for r in restaurants}

    for engineer_prefs in normalized_prefs.values():
        for restaurant, score in engineer_prefs.items():
            if score != float("-inf"):
                aggregates[restaurant] += score

    return aggregates
