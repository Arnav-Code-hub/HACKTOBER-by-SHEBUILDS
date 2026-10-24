import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";
import { listSchema } from "@/lib/api/schemas";

/**
 * Allocations and work-order assignment — mirrors
 * services/api/app/modules/funding and departments. Amounts are integer paise;
 * these are recorded allocations, not payments.
 */

export const officerSchema = z.object({
  id: z.string().min(1),
  display_name: z.string().nullable(),
  email: z.string().nullable(),
});
export type Officer = z.infer<typeof officerSchema>;
export const officerListSchema = listSchema(officerSchema);

export const fundResultSchema = z.object({
  allocation_id: z.string().min(1),
  work_order_id: z.string().min(1),
});

export function officerName(officer: Officer): string {
  return officer.display_name || officer.email || officer.id;
}

/**
 * Records the allocation and assigns the work order in one server
 * transaction. The idempotency key makes a retried click the same request;
 * the API also refuses a second allocation for the same cluster.
 */
export function fundCluster(
  api: ApiClient,
  clusterId: string,
  body: { amount_paise: number; officer_id: string; notes?: string },
  idempotencyKey: string,
) {
  return api.request(`clusters/${encodeURIComponent(clusterId)}/fund`, {
    method: "POST",
    body,
    idempotencyKey,
    schema: fundResultSchema,
  });
}

/** A CSR pledge against a published statement — pledged, never paid here. */
export const sponsorshipSchema = z.object({
  id: z.string().min(1),
  statement_id: z.string().min(1),
  statement_title: z.string(),
  amount_paise: z.number().int().positive(),
  status: z.literal("pledged"),
  pledged_at: z.string().datetime(),
});
export type Sponsorship = z.infer<typeof sponsorshipSchema>;
export const sponsorshipListSchema = listSchema(sponsorshipSchema);

export function pledgeSponsorship(
  api: ApiClient,
  statementId: string,
  amountPaise: number,
  idempotencyKey: string,
) {
  return api.request(
    `statements/${encodeURIComponent(statementId)}/sponsorships`,
    {
      method: "POST",
      body: { amount_paise: amountPaise },
      idempotencyKey,
      schema: sponsorshipSchema,
    },
  );
}
