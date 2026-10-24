"use client";

import { RecordList } from "@/components/workspace/record-list";
import { StatusBadge } from "@/components/workspace/status-badge";

import type { RankedCluster } from "../api";
import { useRankedClusters } from "../hooks";
import { CATEGORY_LABEL } from "../labels";

/**
 * The district's ranked list. Support is labelled as community support — a
 * count of unique citizens, not a measured population estimate.
 */
export function RankedClusters({
  onSelect,
  selectedId,
  description = "Clusters ranked on the five published factors.",
}: {
  onSelect?: (cluster: RankedCluster) => void;
  selectedId?: string | null;
  description?: string;
}) {
  const query = useRankedClusters();
  return (
    <RecordList
      title="Ranked clusters"
      description={description}
      columns={[
        { header: "Rank", cell: (c: RankedCluster) => `#${c.rank}` },
        {
          header: "Cluster",
          cell: (c) => (
            <>
              <strong>{c.title}</strong>
              <br />
              <span className="jm-small">
                {CATEGORY_LABEL[c.category]} · {c.report_count} report
                {c.report_count === 1 ? "" : "s"} · from {c.anchor_report_code}
              </span>
            </>
          ),
        },
        {
          header: "Score",
          cell: (c) => (
            <>
              {c.priority_score.toFixed(1)}
              {c.inputs_are_demo && (
                <>
                  {" "}
                  <span className="jm-badge">Demo inputs</span>
                </>
              )}
            </>
          ),
        },
        { header: "Community support", cell: (c) => c.supporter_count },
        { header: "Status", cell: (c) => <StatusBadge status={c.status} /> },
      ]}
      rows={query.data?.items}
      isLoading={query.isLoading}
      error={query.error}
      onRefresh={() => void query.refetch()}
      isRefreshing={query.isFetching}
      emptyMessage="No clusters have been confirmed in this district yet."
      rowKey={(c) => c.id}
      onSelect={onSelect}
      selectedKey={selectedId}
    />
  );
}
