"use client";

import { useState } from "react";

import { ActionForm } from "@/components/workspace/action-form";
import { RecordList } from "@/components/workspace/record-list";
import { StatusBadge } from "@/components/workspace/status-badge";
import { useInvalidate } from "@/lib/api/hooks";
import { useApi } from "@/lib/api/use-api";

import { assignCluster, validateReport, type Report } from "../api";
import { useClusterSuggestions, useReport, useReportQueue } from "../hooks";
import { CATEGORY_LABEL, reportedOn } from "../labels";
import { RankedClusters } from "./ranked-clusters";
import { ReportDetail } from "./report-detail";

const NEW_CLUSTER = "__new__";

const queueColumns = [
  {
    header: "Report",
    cell: (r: Report) => (
      <>
        <strong>{r.title}</strong>
        <br />
        <span className="jm-small">
          {r.code} · {CATEGORY_LABEL[r.category]}
        </span>
      </>
    ),
  },
  { header: "Reported", cell: (r: Report) => reportedOn(r.created_at) },
  { header: "Location", cell: (r: Report) => r.ward || "—" },
];

/**
 * Panchayat: validate citizen reports, then confirm which reports describe
 * the same problem. Cluster suggestions are proposals; nothing merges until
 * the Panchayat confirms.
 */
export function PanchayatWorkspace() {
  const api = useApi();
  const invalidate = useInvalidate();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const toValidate = useReportQueue("reported");
  const toCluster = useReportQueue("verified");
  const report = useReport(selectedId);
  const selected = report.data;
  const suggestions = useClusterSuggestions(
    selected?.status === "verified" ? selected.id : null,
  );

  async function refresh() {
    await Promise.all([invalidate("reports"), invalidate("clusters")]);
  }

  return (
    <>
      <div className="jm-page-heading">
        <span className="jm-badge">Panchayat</span>
        <h1>Validate and group local reports</h1>
        <p>
          Check each citizen report, then confirm whether it describes a problem
          already raised nearby. Confirmed clusters enter the district&rsquo;s
          ranked list.
        </p>
      </div>

      <div className="jm-panel-grid">
        <div className="jm-stack">
          <RecordList
            title="Awaiting validation"
            columns={queueColumns}
            rows={toValidate.data?.items}
            isLoading={toValidate.isLoading}
            error={toValidate.error}
            onRefresh={() => void toValidate.refetch()}
            isRefreshing={toValidate.isFetching}
            emptyMessage="No reports are waiting for validation."
            rowKey={(r) => r.id}
            onSelect={(r) => setSelectedId(r.id)}
            selectedKey={selectedId}
          />
          <RecordList
            title="Validated · needs a cluster"
            columns={queueColumns}
            rows={toCluster.data?.items}
            isLoading={toCluster.isLoading}
            error={toCluster.error}
            onRefresh={() => void toCluster.refetch()}
            isRefreshing={toCluster.isFetching}
            emptyMessage="No validated reports are waiting for a cluster."
            rowKey={(r) => r.id}
            onSelect={(r) => setSelectedId(r.id)}
            selectedKey={selectedId}
          />
        </div>

        <div className="jm-stack">
          {!selectedId ? (
            <section className="jm-panel">
              <h2>Select a report</h2>
              <p className="jm-muted">
                Open a report from either queue to review it.
              </p>
            </section>
          ) : report.isLoading ? (
            <section className="jm-panel">
              <p role="status">Loading report…</p>
            </section>
          ) : !selected ? (
            <section className="jm-panel" role="alert">
              <h2>Report unavailable</h2>
              <p className="jm-muted">
                It may have been moved out of your scope. Refresh the queues.
              </p>
            </section>
          ) : (
            <>
              <ReportDetail report={selected} />

              {selected.status === "reported" && (
                <>
                  <ActionForm
                    key={`validate-${selected.id}`}
                    title="Validate"
                    description="Confirms this is a genuine local problem in your area."
                    fields={[]}
                    submitLabel="Validate report"
                    confirm={() => `Validate ${selected.code}?`}
                    onSubmit={async () => {
                      await validateReport(api, selected.id, {
                        decision: "verify",
                      });
                      await refresh();
                      return `${selected.code} validated. Confirm its cluster next.`;
                    }}
                  />
                  <ActionForm
                    key={`reject-${selected.id}`}
                    title="Not accepted"
                    description="The citizen sees this reason on their report."
                    fields={[
                      {
                        name: "reason",
                        label: "Reason",
                        kind: "textarea",
                        required: true,
                        maxLength: 300,
                      },
                    ]}
                    submitLabel="Decline report"
                    confirm={() =>
                      `Decline ${selected.code}? The citizen will see your reason.`
                    }
                    onSubmit={async (values) => {
                      await validateReport(api, selected.id, {
                        decision: "reject",
                        reason: String(values.reason),
                      });
                      await refresh();
                      return `${selected.code} was not accepted.`;
                    }}
                  />
                </>
              )}

              {selected.status === "verified" && (
                <ActionForm
                  key={`cluster-${selected.id}`}
                  title="Confirm cluster"
                  description={
                    suggestions.isLoading
                      ? "Looking for similar reports nearby…"
                      : suggestions.error
                        ? "Suggestions are unavailable; you can still start a new cluster."
                        : "Suggestions are nearby clusters of the same category. Choose one only if it is the same problem."
                  }
                  fields={[
                    {
                      name: "target",
                      label: "Cluster",
                      kind: "select",
                      required: true,
                      options: [
                        ...(suggestions.data?.items ?? []).map((s) => ({
                          value: s.id,
                          label: `${s.title} · ${Math.round(s.distance_m)} m away · ${s.report_count} report${s.report_count === 1 ? "" : "s"}`,
                        })),
                        {
                          value: NEW_CLUSTER,
                          label: "None of these — start a new cluster",
                        },
                      ],
                    },
                  ]}
                  submitLabel="Confirm cluster"
                  confirm={(values) =>
                    values.target === NEW_CLUSTER
                      ? `Start a new cluster from ${selected.code}?`
                      : `Add ${selected.code} to the chosen cluster? Its community support will be counted there.`
                  }
                  onSubmit={async (values) => {
                    await assignCluster(
                      api,
                      selected.id,
                      values.target === NEW_CLUSTER
                        ? { new: true }
                        : { cluster_id: String(values.target) },
                    );
                    await refresh();
                    return `${selected.code} is now in the ranked list.`;
                  }}
                />
              )}

              {selected.status !== "reported" &&
                selected.status !== "verified" && (
                  <section className="jm-panel">
                    <h2>No Panchayat action needed</h2>
                    <p className="jm-muted">
                      This report is <StatusBadge status={selected.status} />.
                    </p>
                  </section>
                )}
            </>
          )}
        </div>
      </div>

      <RankedClusters />
    </>
  );
}
