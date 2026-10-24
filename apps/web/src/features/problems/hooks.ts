"use client";

import { useApiQuery } from "@/lib/api/hooks";
import type { ReportStatus } from "@/lib/api/schemas";

import {
  clusterSuggestionListSchema,
  rankedClusterListSchema,
  reportListSchema,
  reportSchema,
} from "./api";

/** Reports in the caller's scope with one status, e.g. the validation queue. */
export function useReportQueue(status: ReportStatus) {
  return useApiQuery(["reports"], "reports", reportListSchema, {
    query: { status },
  });
}

export function useReport(id: string | null) {
  return useApiQuery(
    ["reports", id],
    `reports/${encodeURIComponent(id ?? "")}`,
    reportSchema,
    {
      enabled: Boolean(id),
    },
  );
}

export function useClusterSuggestions(reportId: string | null) {
  return useApiQuery(
    ["reports", reportId, "cluster-suggestions"],
    `reports/${encodeURIComponent(reportId ?? "")}/cluster-suggestions`,
    clusterSuggestionListSchema,
    { enabled: Boolean(reportId) },
  );
}

export function useRankedClusters() {
  return useApiQuery(
    ["clusters", "ranked"],
    "clusters/ranked",
    rankedClusterListSchema,
  );
}
