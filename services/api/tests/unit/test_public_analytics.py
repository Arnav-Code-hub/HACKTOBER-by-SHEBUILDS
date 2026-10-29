"""Execute public aggregate SQL without connecting to any external database."""

from sqlalchemy import create_engine

from app.core.database import get_db
from app.persistence.oversight import public_transparency


async def test_live_counts_follow_case_status_and_never_mix_in_demo_data(app, client):
    engine = create_engine("sqlite://")
    with engine.connect() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE clusters "
            "(id TEXT, status TEXT, is_demo BOOLEAN, status_changed_at DATETIME)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE reports (id TEXT, cluster_id TEXT, status TEXT, is_demo BOOLEAN, "
            "status_changed_at DATETIME)"
        )
        connection.exec_driver_sql(
            "INSERT INTO clusters VALUES (?, ?, ?, ?)",
            [
                ("fixed", "citizen_verified", False, "2026-10-29 10:00:00"),
                ("working", "in_progress", False, "2026-10-28 10:00:00"),
                ("demo", "citizen_verified", True, "2026-10-29 11:00:00"),
            ],
        )
        connection.exec_driver_sql(
            "INSERT INTO reports VALUES (?, ?, ?, ?, ?)",
            [
                ("a", "fixed", "verified", False, "2026-10-25 10:00:00"),
                ("b", "fixed", "verified", False, "2026-10-25 10:00:00"),
                ("c", "working", "verified", False, "2026-10-25 10:00:00"),
                ("d", None, "reported", False, "2026-10-25 10:00:00"),
                ("e", None, "rejected", False, "2026-10-25 10:00:00"),
                ("sample", None, "reported", True, "2026-10-25 10:00:00"),
                ("mixed", "demo", "verified", False, "2026-10-25 10:00:00"),
            ],
        )

        class ReadSession:
            calls = 0

            async def execute(self, statement):
                self.calls += 1
                return connection.execute(statement)

        session = ReadSession()
        result = await public_transparency(session)  # type: ignore[arg-type]
        # Live data exists: one statement keeps case/report counts in one snapshot.
        assert session.calls == 1
        assert result.report_count == 5
        assert result.reports_by_status == {
            "citizen_verified": 2,
            "in_progress": 1,
            "reported": 1,
            "rejected": 1,
        }
        assert result.cluster_count == 2
        assert result.active_cases == result.citizen_verified_cases == 1
        assert result.sample_data is False
        assert result.updated_at.day == 29

        async def database():
            yield session

        app.dependency_overrides[get_db] = database
        response = await client.get("/api/v1/analytics/public")
        assert response.status_code == 200
        assert response.json()["reports_by_status"]["citizen_verified"] == 2
        assert set(response.json()) == {
            "report_count",
            "cluster_count",
            "active_cases",
            "citizen_verified_cases",
            "reports_by_status",
            "clusters_by_status",
            "sample_data",
            "updated_at",
        }
    engine.dispose()


async def test_public_analytics_reports_genuine_zero_counts():
    class EmptyResult:
        def all(self):
            return []

    class EmptySession:
        async def execute(self, statement):
            return EmptyResult()

    result = await public_transparency(EmptySession())  # type: ignore[arg-type]
    assert result.report_count == result.cluster_count == 0
    assert result.active_cases == result.citizen_verified_cases == 0
    assert result.updated_at is None
    # Nothing recorded at all is reported as zero, not as sample data.
    assert result.sample_data is False


async def test_demo_data_is_shown_as_sample_until_live_reports_exist():
    engine = create_engine("sqlite://")
    with engine.connect() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE clusters "
            "(id TEXT, status TEXT, is_demo BOOLEAN, status_changed_at DATETIME)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE reports (id TEXT, cluster_id TEXT, status TEXT, is_demo BOOLEAN, "
            "status_changed_at DATETIME)"
        )
        connection.exec_driver_sql(
            "INSERT INTO clusters VALUES (?, ?, ?, ?)",
            [("demo", "citizen_verified", True, "2026-10-29 11:00:00")],
        )
        connection.exec_driver_sql(
            "INSERT INTO reports VALUES (?, ?, ?, ?, ?)",
            [
                ("s1", "demo", "verified", True, "2026-10-25 10:00:00"),
                ("s2", None, "reported", True, "2026-10-25 10:00:00"),
            ],
        )

        class ReadSession:
            async def execute(self, statement):
                return connection.execute(statement)

        result = await public_transparency(ReadSession())  # type: ignore[arg-type]
        assert result.sample_data is True
        assert result.report_count == 2 and result.cluster_count == 1
        assert result.reports_by_status == {"citizen_verified": 1, "reported": 1}
    engine.dispose()
