import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";
import { listSchema } from "@/lib/api/schemas";

/**
 * Problem statements — mirrors services/api/app/modules/problem_statements.
 * A statement invites student solutions and CSR pledges; it is not a
 * government work order and authorises no public repair.
 */

export const statementSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  body: z.string(),
  status: z.enum(["draft", "published"]),
  cluster_id: z.string().nullable(),
  published_at: z.string().datetime().nullable(),
});
export type Statement = z.infer<typeof statementSchema>;
export const statementListSchema = listSchema(statementSchema);

export function createStatement(
  api: ApiClient,
  body: { title: string; body: string; cluster_id?: string },
  idempotencyKey: string,
) {
  return api.request("statements", {
    method: "POST",
    body,
    idempotencyKey,
    schema: statementSchema,
  });
}

export function publishStatement(api: ApiClient, id: string) {
  return api.request(`statements/${encodeURIComponent(id)}/publish`, {
    method: "POST",
    schema: statementSchema,
  });
}
