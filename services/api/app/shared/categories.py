"""Categories shared by reports and department responsibility mappings."""

from enum import StrEnum


class Category(StrEnum):
    WATER = "water"
    ROADS = "roads"
    LIGHTING = "lighting"
    SANITATION = "sanitation"
    HEALTH = "health"
    EDUCATION = "education"
    ELECTRICITY = "electricity"
    TRANSPORT = "transport"
    OTHER = "other"


CATEGORY_CHECK = "category IN (" + ", ".join(f"'{value}'" for value in Category) + ")"
