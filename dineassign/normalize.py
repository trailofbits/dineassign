"""Preference normalization for dineassign."""

import statistics

from dineassign.models import Diner


def normalize_preferences(
    diners: list[Diner],
    restaurants: list[str],
) -> dict[str, dict[str, float]]:
    """
    Normalize preferences using Z-score per diner.

    Returns a dict mapping diner_email -> restaurant -> normalized_score.
    Restaurants where a diner "Can't eat" are mapped to negative infinity.
    """
    normalized: dict[str, dict[str, float]] = {}

    for diner in diners:
        # Collect non-excluded scores for this diner
        valid_scores = [score for score in diner.preferences.values() if score is not None]

        if not valid_scores:
            # All restaurants excluded - this is a problem
            normalized[diner.email] = {r: float("-inf") for r in restaurants}
            continue

        mean = statistics.mean(valid_scores)
        stdev = statistics.stdev(valid_scores) if len(valid_scores) > 1 else 1.0

        # Avoid division by zero for diners who rated everything the same
        if stdev == 0:
            stdev = 1.0

        diner_prefs: dict[str, float] = {}
        for restaurant in restaurants:
            raw_score = diner.preferences.get(restaurant)
            if raw_score is None:
                # Can't eat here - hard constraint
                diner_prefs[restaurant] = float("-inf")
            else:
                # Z-score normalization
                diner_prefs[restaurant] = (raw_score - mean) / stdev

        normalized[diner.email] = diner_prefs

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

    for diner_prefs in normalized_prefs.values():
        for restaurant, score in diner_prefs.items():
            if score != float("-inf"):
                aggregates[restaurant] += score

    return aggregates
