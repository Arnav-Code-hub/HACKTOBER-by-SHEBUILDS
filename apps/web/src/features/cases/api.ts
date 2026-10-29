import { z } from "zod";

import {
  categorySchema,
  listSchema,
  reportStatusSchema,
} from "@/lib/api/schemas";

/**
 * The case tracker: each case from prioritisation to citizen verification,
 * with its allocation. Mirrors `GET /cases`.
 */
export const WAITING_ON = ["department", "officer", "citizen", "none"] as const;
export type WaitingOn = (typeof WAITING_ON)[number];

export const caseSchema = z.object({
  cluster_id: z.string().min(1),
  report_code: z.string().min(1),
  title: z.string(),
  category: categorySchema,
  status: reportStatusSchema,
  waiting_on: z.enum(WAITING_ON),
  status_changed_at: z.string().datetime(),
  work_order_id: z.string().min(1).nullable(),
  round: z.number().int().min(1).nullable(),
  department_name: z.string().nullable(),
  officer_name: z.string().nullable(),
  allocated_paise: z.number().int().min(0).nullable(),
  allocated_at: z.string().datetime().nullable(),
  allocated_by_name: z.string().nullable(),
});
export type Case = z.infer<typeof caseSchema>;
export const caseListSchema = listSchema(caseSchema);

export const WAITING_LABEL: Record<WaitingOn, string> = {
  department: "Department",
  officer: "Officer",
  citizen: "Citizen",
  none: "Nobody · verified",
};
