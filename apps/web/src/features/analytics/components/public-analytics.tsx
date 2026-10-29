"use client";

import { useQuery } from "@tanstack/react-query";

import { STATUS_DISPLAY } from "@/components/workspace/status-badge";
import { REPORT_STATUSES } from "@/lib/api/schemas";

import { loadPublicAnalytics } from "../api";

const number = new Intl.NumberFormat("en-IN");

export function PublicAnalytics() {
  const query = useQuery({
    queryKey: ["public", "analytics"],
    queryFn: ({ signal }) => loadPublicAnalytics(signal),
    staleTime: 60_000,
    retry: 1,
  });
  const data = query.data;
  const resolved = data?.reports_by_status.citizen_verified ?? 0;
  const rejected = data?.reports_by_status.rejected ?? 0;

  return (
    <section
      className="jm-public-analytics"
      aria-labelledby="public-progress-title"
    >
      <div className="jm-list-heading">
        <h2 id="public-progress-title">Community progress</h2>
        {data && (
          <button
            type="button"
            className="jm-button jm-button-secondary jm-button-small"
            onClick={() => void query.refetch()}
            disabled={query.isFetching}
          >
            {query.isFetching ? "Refreshing…" : "Refresh statistics"}
          </button>
        )}
      </div>
      {data?.sample_data ? (
        <p className="jm-notice" role="note">
          <span className="jm-badge jm-sample-badge">Sample data</span> No live
          complaints have been recorded yet, so these figures come from the
          labelled demonstration dataset. They are not real complaints.
        </p>
      ) : (
        <p className="jm-muted">
          Public totals from saved complaints. Labelled demo data is excluded.
          Resolved means the original reporter accepted the repair.
        </p>
      )}
      {!data ? (
        query.isPending ? (
          <p role="status">Loading public statistics…</p>
        ) : (
          <div className="jm-notice" role="alert">
            <p>
              Public statistics are currently unavailable. Please try again.
            </p>
            <button
              type="button"
              className="jm-button jm-button-secondary"
              onClick={() => void query.refetch()}
              disabled={query.isFetching}
            >
              {query.isFetching ? "Retrying…" : "Retry statistics"}
            </button>
          </div>
        )
      ) : (
        <>
          {query.isError && (
            <p className="jm-notice" role="alert">
              Could not refresh. Showing the last loaded statistics.
            </p>
          )}
          <ul
            className="jm-stat-blocks"
            aria-label={
              data.sample_data
                ? "Sample complaint totals"
                : "Public complaint totals"
            }
          >
            {[
              ["Total complaints", data.report_count],
              ["Open complaints", data.report_count - resolved - rejected],
              ["Resolved complaints", resolved],
              ["Not accepted", rejected],
            ].map(([label, value]) => (
              <li key={label}>
                <span>{label}</span>
                <strong>{number.format(Number(value))}</strong>
              </li>
            ))}
          </ul>
          <p className="jm-small">
            {number.format(data.cluster_count)} community cases ·{" "}
            {number.format(data.citizen_verified_cases)} citizen-verified
            repairs. Multiple complaints can belong to one case.
          </p>
          {!data.sample_data && data.report_count === 0 && (
            <p className="jm-muted">
              No non-demo complaints have been recorded yet.
            </p>
          )}
          <details className="jm-panel">
            <summary>See complaint status breakdown</summary>
            <dl className="jm-details">
              {REPORT_STATUSES.map((status) => (
                <div key={status}>
                  <dt>{STATUS_DISPLAY[status].label}</dt>
                  <dd>{number.format(data.reports_by_status[status] ?? 0)}</dd>
                </div>
              ))}
            </dl>
          </details>
          {data.updated_at && (
            <p className="jm-small jm-section">
              Latest recorded status change:{" "}
              {new Date(data.updated_at).toLocaleString("en-IN", {
                dateStyle: "medium",
                timeStyle: "short",
              })}
            </p>
          )}
        </>
      )}
    </section>
  );
}
