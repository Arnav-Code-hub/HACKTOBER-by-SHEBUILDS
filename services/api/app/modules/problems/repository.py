"""Database access for problems. PRIVATE to this module.

Only this module's application services may call these functions.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, case, func, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.problems.models import Cluster, Report, Support
from app.modules.problems.ranking import SEVERITY_SCORES


@dataclass(frozen=True)
class ClusterSnapshot:
    cluster: Cluster
    anchor: Report
    report_count: int
    supporter_count: int
    severity: int
    affects_seniors: bool


async def cluster_snapshots(
    session: AsyncSession, district_id: UUID | None
) -> list[ClusterSnapshot]:
    """One SQL snapshot; aggregate separately to avoid multiplying join rows.

    UNION deduplicates reporter/supporter identities across all cluster members.
    Writers only accept citizen reports/support, so staff do not inflate counts.
    The caller supplies its permitted district, or None for platform oversight.
    """
    # Filter inside each aggregate so a district read never scans every district.
    in_scope: list[ColumnElement[bool]] = [Report.cluster_id.is_not(None)]
    support_scope: list[ColumnElement[bool]] = []
    if district_id is not None:
        in_scope.append(Report.district_id == district_id)
        support_scope.append(
            Support.cluster_id.in_(select(Cluster.id).where(Cluster.district_id == district_id))
        )
    members = (
        select(
            Report.cluster_id,
            func.count().label("report_count"),
            func.max(case(SEVERITY_SCORES, value=Report.severity)).label("severity"),
            func.bool_or(Report.affects_seniors).label("affects_seniors"),
        )
        .where(*in_scope)
        .group_by(Report.cluster_id)
        .subquery()
    )
    identities = union(
        select(Report.cluster_id, Report.reporter_id.label("user_id")).where(*in_scope),
        select(Support.cluster_id, Support.user_id).where(*support_scope),
    ).subquery()
    support = (
        select(identities.c.cluster_id, func.count().label("supporter_count"))
        .group_by(identities.c.cluster_id)
        .subquery()
    )
    query = (
        select(
            Cluster, Report, members.c.report_count, support.c.supporter_count,
            members.c.severity, members.c.affects_seniors,
        )
        .join(Report, Cluster.anchor_report_id == Report.id)
        .join(members, members.c.cluster_id == Cluster.id)
        .join(support, support.c.cluster_id == Cluster.id)
    )
    if district_id is not None:
        query = query.where(Cluster.district_id == district_id)
    return [
        ClusterSnapshot(
            row.Cluster, row.Report, row.report_count, row.supporter_count,
            row.severity, bool(row.affects_seniors),
        )
        for row in (await session.execute(query)).all()
    ]
