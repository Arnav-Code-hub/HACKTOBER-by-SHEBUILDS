import { z } from "zod";

import { ApiError } from "@/lib/api/client";
import { reportStatusSchema } from "@/lib/api/schemas";
import { clientConfiguration } from "@/lib/config";

const count = z.number().int().nonnegative();
const publicAnalyticsSchema = z
  .object({
    report_count: count,
    cluster_count: count,
    active_cases: count,
    citizen_verified_cases: count,
    reports_by_status: z.record(reportStatusSchema, count),
    clusters_by_status: z.record(reportStatusSchema, count),
    /** True while no live report exists and the figures are the labelled demo data. */
    sample_data: z.boolean(),
    updated_at: z.string().datetime({ offset: true }).nullable(),
  })
  .refine(
    (data) =>
      Object.values(data.reports_by_status).reduce(
        (sum, value) => sum + value,
        0,
      ) === data.report_count,
  );

export async function loadPublicAnalytics(signal: AbortSignal) {
  const { apiOrigin } = clientConfiguration();
  if (!apiOrigin)
    throw new ApiError("Public statistics are unavailable.", null);
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal.addEventListener("abort", abort);
  if (signal.aborted) abort();
  const timer = setTimeout(abort, 30_000);
  try {
    const response = await fetch(`${apiOrigin}/api/v1/analytics/public`, {
      signal: controller.signal,
      credentials: "omit",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok)
      throw new ApiError("Public statistics are unavailable.", response.status);
    const result = publicAnalyticsSchema.safeParse(await response.json());
    if (!result.success)
      throw new ApiError("Public statistics could not be verified.", null);
    return result.data;
  } finally {
    clearTimeout(timer);
    signal.removeEventListener("abort", abort);
  }
}
