"""Small-distance matching for the prototype, without a spatial extension."""

from math import asin, cos, radians, sin, sqrt

from app.shared.categories import Category


def cluster_radius_m(category: str) -> float:
    # Drains use sanitation in the current contract; there is no drain subtype.
    return 500.0 if category in {Category.ROADS, Category.SANITATION} else 100.0


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance, including coincident points and the date line."""
    phi1, phi2 = radians(lat1), radians(lat2)
    delta_phi, delta_lambda = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    return 2 * 6_371_008.8 * asin(sqrt(min(1.0, max(0.0, a))))
