import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";
import { listSchema, reportStatusSchema } from "@/lib/api/schemas";

/**
 * Government work orders — mirrors services/api/app/modules/departments. A
 * work order is assigned by a Department after funding; it is separate from
 * any student project.
 */

export const workOrderSchema = z.object({
  id: z.string().min(1),
  cluster_id: z.string().min(1),
  report_code: z.string().min(1),
  title: z.string(),
  status: reportStatusSchema,
  /** Verification round; above 1 means the reporter returned the work. */
  round: z.number().int().min(1),
  location_label: z.string().nullable(),
  instructions: z.string().nullable(),
  notes: z.string().nullable(),
  allocated_paise: z.number().int().min(0),
  assigned_at: z.string().datetime(),
});
export type WorkOrder = z.infer<typeof workOrderSchema>;
export const workOrderListSchema = listSchema(workOrderSchema);

const ack = z.object({ id: z.string().min(1), status: reportStatusSchema });

const segment = (id: string) => encodeURIComponent(id);

/** A progress note. The first update moves a funded order to in progress. */
export function updateWorkOrder(api: ApiClient, id: string, notes: string) {
  return api.request(`work-orders/${segment(id)}`, {
    method: "PATCH",
    body: { notes },
    schema: ack,
  });
}

/** Attaches verified completion photos; the reporter is then asked to verify. */
export function completeWorkOrder(
  api: ApiClient,
  id: string,
  mediaIds: string[],
  idempotencyKey: string,
) {
  return api.request(`work-orders/${segment(id)}/complete`, {
    method: "POST",
    body: { media_ids: mediaIds },
    idempotencyKey,
    schema: ack,
  });
}
