"""Deterministic demo identities and timestamps, never historical claims."""

from datetime import UTC, datetime
from typing import TypedDict
from uuid import NAMESPACE_URL, UUID, uuid5

from app.core.roles import Role

SEED_AT = datetime(2026, 10, 21, 10, tzinfo=UTC)


def seed_id(key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"https://janmaang.example/demo/v1/{key}")


def user_id(role: Role) -> UUID:
    return seed_id(f"user/{role}")


class OrganizationSeed(TypedDict):
    key: str
    type: str
    code: str
    name: str
    is_active: bool


ORGANIZATIONS: list[OrganizationSeed] = [
    {
        "key": "district/yadgir",
        "type": "district",
        "code": "DEMO-YDG",
        "name": "Yadgir (demonstration)",
        "is_active": True,
    },
    {
        "key": "district/boundary",
        "type": "district",
        "code": "DEMO-BOUNDARY",
        "name": "Boundary test district (inactive demonstration)",
        "is_active": False,
    },
    {
        "key": "department/civic",
        "type": "department",
        "code": "DEMO-YDG-CIVIC",
        "name": "Yadgir Civic Department (demonstration)",
        "is_active": True,
    },
    {
        "key": "institute",
        "type": "institute",
        "code": "DEMO-INSTITUTE",
        "name": "Demonstration Institute",
        "is_active": True,
    },
    {
        "key": "industry",
        "type": "industry",
        "code": "DEMO-INDUSTRY",
        "name": "Demonstration CSR Partner",
        "is_active": True,
    },
]
