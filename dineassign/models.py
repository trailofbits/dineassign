"""Data models for dineassign."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Diner:
    """A diner with restaurant preferences."""

    email: str
    preferences: dict[str, int | None] = field(default_factory=dict)
    # preferences maps restaurant name -> raw Likert score (None = can't eat)


@dataclass
class Reservation:
    """A restaurant reservation for a specific day."""

    restaurant: str
    day: str
    capacity: int = 0
    status: Literal["confirmed", "unavailable", "pending"] = "pending"


@dataclass
class Assignment:
    """A diner assigned to a restaurant on a specific day."""

    diner_email: str
    restaurant: str
    day: str
    preference_score: float = 0.0  # normalized preference score


@dataclass
class OptimizationResult:
    """Result of the optimization."""

    assignments: list[Assignment]
    total_satisfaction: float
    suggested_reservation: tuple[str, str, int] | None  # (restaurant, day, suggested_capacity)
    repeated_pairings: int = 0  # number of diner pairs dining together on 2+ days
