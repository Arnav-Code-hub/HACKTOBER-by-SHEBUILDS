"""The Role enum.

Its own module so that `security.py` (which puts a Role on every Principal) and
`permissions.py` (which maps Roles to Permissions) can both import it without a
cycle. Nothing else belongs here — this file must stay import-free.

Mirrored into TypeScript and Dart via packages/contracts.
"""

from enum import StrEnum


class Role(StrEnum):
    """Every role in JanMaang.

    CITIZEN is the mobile app's role and has no web dashboard; the other nine
    are web roles.
    """

    CITIZEN = "citizen"
    STUDENT = "student"
    FACULTY = "faculty"
    INSTITUTE = "institute"
    PANCHAYAT = "panchayat"
    DEPARTMENT = "department"
    OFFICER = "officer"
    INDUSTRY = "industry"
    GOV_ADMIN = "gov_admin"
    SUPER_ADMIN = "super_admin"
