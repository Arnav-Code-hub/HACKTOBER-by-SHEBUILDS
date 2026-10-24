"""Database fixtures shared by the transaction tests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.roles import Role
from app.core.security import Principal
from app.modules.files.models import MediaAsset
from app.modules.problems.models import Report
from app.seeds.data import seed_id, user_id


def demo_principal(role: Role) -> Principal:
    return Principal(
        user_id=user_id(role),
        firebase_uid=f"test-{role}",
        role=role,
        district_id=seed_id("district/yadgir"),
        department_id=seed_id("department/civic")
        if role in {Role.DEPARTMENT, Role.OFFICER}
        else None,
        institute_id=seed_id("institute")
        if role in {Role.INSTITUTE, Role.FACULTY, Role.STUDENT}
        else None,
    )


def new_report(title: str = "Transaction probe") -> Report:
    return Report(
        reporter_id=user_id(Role.CITIZEN),
        district_id=seed_id("district/yadgir"),
        title=title,
        transcript="Test report",
        summary="Test report",
        category="water",
        severity="medium",
        status="reported",
        latitude=16.76,
        longitude=77.14,
        location_label="Test location",
        channel="text",
        is_demo=True,
    )


def completion_photo(work_order_id: UUID, round_: int) -> MediaAsset:
    """A verified officer completion photo attached to one work-order round."""
    unique = uuid4().hex
    return MediaAsset(
        owner_id=user_id(Role.OFFICER),
        public_id=f"janmaang/test/completion/{unique}",
        asset_id=unique,
        version=1,
        kind="completion",
        format="jpg",
        bytes=1024,
        width=640,
        height=480,
        uploaded_at=datetime.now(UTC),
        work_order_id=work_order_id,
        round=round_,
        is_demo=True,
    )
