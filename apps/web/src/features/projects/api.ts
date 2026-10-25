import { z } from "zod";

import type { ApiClient } from "@/lib/api/client";
import { httpsUrl, listSchema } from "@/lib/api/schemas";

/**
 * Student submissions and faculty reviews — mirrors
 * services/api/app/modules/projects.
 */

export const reviewSchema = z.object({
  score: z.number().int().min(1).max(5),
  comment: z.string(),
});

export const submissionSchema = z.object({
  id: z.string().min(1),
  team_id: z.string().min(1),
  team_name: z.string(),
  statement_title: z.string(),
  title: z.string().min(1),
  summary: z.string(),
  // HTTPS only: the link is rendered as an anchor for faculty, so a
  // javascript: or data: URL must never get through.
  link: httpsUrl.nullable(),
  submitted_at: z.string().datetime(),
  review_count: z.number().int().min(0),
  /** The caller's own review, if they have written one. */
  my_review: reviewSchema.nullable(),
});
export type Submission = z.infer<typeof submissionSchema>;
export const submissionListSchema = listSchema(submissionSchema);

export function createSubmission(
  api: ApiClient,
  body: { team_id: string; title: string; summary: string; link?: string },
  idempotencyKey: string,
) {
  return api.request("submissions", {
    method: "POST",
    body,
    idempotencyKey,
    schema: submissionSchema,
  });
}

export function reviewSubmission(
  api: ApiClient,
  id: string,
  body: { score: number; comment: string },
  idempotencyKey: string,
) {
  return api.request(`submissions/${encodeURIComponent(id)}/reviews`, {
    method: "POST",
    body,
    idempotencyKey,
    schema: z.object({ id: z.string().min(1) }),
  });
}
