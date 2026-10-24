import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";
import { listSchema } from "@/lib/api/schemas";

/**
 * Student teams — mirrors services/api/app/modules/teams. A team works on a
 * published problem statement and needs its institute's approval before it
 * can submit. Team work never authorises a government repair.
 */

export const teamSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  statement_id: z.string().min(1),
  statement_title: z.string(),
  institute_approved: z.boolean(),
  member_count: z.number().int().min(1),
  created_at: z.string().datetime(),
});
export type Team = z.infer<typeof teamSchema>;
export const teamListSchema = listSchema(teamSchema);

export function createTeam(
  api: ApiClient,
  body: { name: string; statement_id: string },
  idempotencyKey: string,
) {
  return api.request("teams", {
    method: "POST",
    body,
    idempotencyKey,
    schema: teamSchema,
  });
}

export function approveTeam(api: ApiClient, id: string) {
  return api.request(`teams/${encodeURIComponent(id)}/approve`, {
    method: "POST",
    schema: teamSchema,
  });
}
