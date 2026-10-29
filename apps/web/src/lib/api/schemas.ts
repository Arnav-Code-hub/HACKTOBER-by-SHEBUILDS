import { z } from "zod";

/**
 * Shapes shared by every workspace. They mirror
 * docs/api/day1-frontend-contract.md; a value outside them is a protocol
 * error, never coerced into something plausible.
 */

/** The agreed report lifecycle. `verified` is Panchayat validation. */
export const REPORT_STATUSES = [
  "reported",
  "verified",
  "rejected",
  "prioritised",
  "funded",
  "in_progress",
  "awaiting_verification",
  "citizen_verified",
] as const;

export const reportStatusSchema = z.enum(REPORT_STATUSES);
export type ReportStatus = z.infer<typeof reportStatusSchema>;

export const CATEGORIES = [
  "water",
  "roads",
  "lighting",
  "sanitation",
  "health",
  "education",
  "electricity",
  "transport",
  "other",
] as const;
export const categorySchema = z.enum(CATEGORIES);

export const SEVERITIES = ["low", "medium", "high", "critical"] as const;
export const severitySchema = z.enum(SEVERITIES);

export const httpsUrl = z
  .string()
  .url()
  .refine((value) => new URL(value).protocol === "https:", "HTTPS only");

/** A verified media record. The ID is for attaching; URLs are for display. */
export const mediaSchema = z.object({
  id: z.string().min(1),
  url: httpsUrl,
  thumbnail_url: httpsUrl.nullish(),
});
export type Media = z.infer<typeof mediaSchema>;

/** One of the five ranking factors, 0–100, with its published weight. */
export const scoreFactorSchema = z.object({
  factor: z.string().min(1),
  label: z.string().min(1),
  score: z.number().min(0).max(100),
  weight: z.number().min(0).max(1),
  /** True for a seeded or neutral-default input rather than an official one. */
  is_demo: z.boolean(),
});
export type ScoreFactor = z.infer<typeof scoreFactorSchema>;

/** Before/after evidence for one work order. */
export const evidenceSchema = z.object({
  report_code: z.string().min(1),
  status: reportStatusSchema,
  // Null when the citizen attached no photo; report photos are optional.
  before: z
    .object({ url: httpsUrl, uploaded_at: z.string().datetime() })
    .nullable(),
  after: z
    .object({ url: httpsUrl, uploaded_at: z.string().datetime() })
    .nullable(),
  /** Which round `after` belongs to; earlier rounds were returned. */
  after_round: z.number().int().min(1).nullable().optional(),
  card_url: httpsUrl.nullable(),
  verdict_label: z.string().nullable().optional(),
  /** The citizen's reason when the round shown was returned. */
  returned_comment: z.string().nullable().optional(),
});
export type Evidence = z.infer<typeof evidenceSchema>;

/** Every list endpoint returns `{ "items": [...] }`. */
export function listSchema<T extends z.ZodTypeAny>(item: T) {
  return z.object({ items: z.array(item) });
}
