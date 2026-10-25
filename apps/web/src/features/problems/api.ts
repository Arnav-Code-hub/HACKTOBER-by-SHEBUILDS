import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";
import {
  categorySchema,
  listSchema,
  mediaSchema,
  reportStatusSchema,
  scoreFactorSchema,
  severitySchema,
} from "@/lib/api/schemas";

/**
 * Reports, clusters and ranking — mirrors services/api/app/modules/problems.
 * Shapes follow docs/api/day1-frontend-contract.md ("Staff workspace
 * endpoints"); scope is enforced by the API, never filtered here.
 */

export const reportSchema = z.object({
  id: z.string().min(1),
  code: z.string().min(1),
  title: z.string(),
  description: z.string().nullish(),
  transcript: z.string().nullish(),
  category: categorySchema,
  severity: severitySchema,
  status: reportStatusSchema,
  ward: z.string().nullish(),
  district: z.string().nullish(),
  latitude: z.number().nullish(),
  longitude: z.number().nullish(),
  created_at: z.string().datetime(),
  media: z.array(mediaSchema),
  cluster_id: z.string().nullish(),
  rejection_reason: z.string().nullish(),
});
export type Report = z.infer<typeof reportSchema>;
export const reportListSchema = listSchema(reportSchema);

export const clusterSuggestionSchema = z.object({
  id: z.string().min(1),
  title: z.string(),
  category: categorySchema,
  distance_m: z.number().min(0),
  report_count: z.number().int().min(0),
  supporter_count: z.number().int().min(0),
});
export type ClusterSuggestion = z.infer<typeof clusterSuggestionSchema>;
export const clusterSuggestionListSchema = listSchema(clusterSuggestionSchema);

export const rankedClusterSchema = z.object({
  id: z.string().min(1),
  title: z.string(),
  category: categorySchema,
  status: reportStatusSchema,
  rank: z.number().int().min(1),
  priority_score: z.number().min(0).max(100),
  supporter_count: z.number().int().min(0),
  report_count: z.number().int().min(0),
  anchor_report_code: z.string().min(1),
  infrastructure_gap: z.number().min(0).max(100),
  equity_index: z.number().min(0).max(100),
  inputs_are_demo: z.boolean(),
  score_breakdown: z.array(scoreFactorSchema),
});
export type RankedCluster = z.infer<typeof rankedClusterSchema>;
export const rankedClusterListSchema = listSchema(rankedClusterSchema);

const ack = z.object({ id: z.string().min(1), status: reportStatusSchema });

const segment = (id: string) => encodeURIComponent(id);

export function validateReport(
  api: ApiClient,
  id: string,
  decision: { decision: "verify" } | { decision: "reject"; reason: string },
) {
  return api.request(`reports/${segment(id)}/validate`, {
    method: "POST",
    body: decision,
    schema: ack,
  });
}

export function assignCluster(
  api: ApiClient,
  reportId: string,
  target: { cluster_id: string } | { new: true },
) {
  return api.request(`reports/${segment(reportId)}/cluster`, {
    method: "POST",
    body: target,
    schema: ack,
  });
}

export function updateRankingInputs(
  api: ApiClient,
  clusterId: string,
  inputs: { infrastructure_gap: number; equity_index: number },
) {
  return api.request(`clusters/${segment(clusterId)}/inputs`, {
    method: "PATCH",
    body: inputs,
    schema: z.object({ id: z.string().min(1) }),
  });
}
