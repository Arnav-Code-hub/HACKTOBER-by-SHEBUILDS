import { z } from "zod";

import { ROLES } from "@/lib/auth/roles";
import type { ApiClient } from "@/lib/api/client";
import { listSchema, reportStatusSchema } from "@/lib/api/schemas";

/**
 * Oversight and administration. Spans the backend's analytics (summary),
 * audit (events) and users/rbac (role and scope) modules, which share one
 * web workspace.
 */

const countsByStatus = z.record(reportStatusSchema, z.number().int().min(0));

export const summarySchema = z.object({
  district_name: z.string(),
  reports_by_status: countsByStatus,
  cluster_count: z.number().int().min(0),
  work_orders_by_status: countsByStatus,
  allocated_paise: z.number().int().min(0),
  pledged_paise: z.number().int().min(0),
});
export type Summary = z.infer<typeof summarySchema>;

export const auditEventSchema = z.object({
  id: z.string().min(1),
  at: z.string().datetime(),
  actor_name: z.string(),
  actor_role: z.enum(ROLES),
  action: z.string().min(1),
  entity_type: z.string().min(1),
  entity_id: z.string().min(1),
  reason: z.string().nullable(),
  before: z.record(z.unknown()).nullable().optional(),
  after: z.record(z.unknown()).nullable().optional(),
});
export type AuditEvent = z.infer<typeof auditEventSchema>;

export const auditCursorSchema = z.object({
  before_at: z.string().datetime(),
  before_id: z.string().min(1),
});
export type AuditCursor = z.infer<typeof auditCursorSchema>;
export const auditListSchema = listSchema(auditEventSchema).extend({
  next: auditCursorSchema.nullable().optional(),
});

export const AUDIT_PAGE_SIZE = 50;

/** The page of events older than `cursor`. */
export function fetchOlderAudit(api: ApiClient, cursor: AuditCursor) {
  return api.request("admin/audit", {
    query: { limit: AUDIT_PAGE_SIZE, ...cursor },
    schema: auditListSchema,
  });
}

const nullableId = z.string().min(1).nullable();

export const adminUserSchema = z.object({
  id: z.string().min(1),
  display_name: z.string().nullable(),
  email: z.string().nullable(),
  role: z.enum(ROLES),
  district_id: nullableId,
  department_id: nullableId,
  institute_id: nullableId,
  organization_id: nullableId.optional(),
});
export type AdminUser = z.infer<typeof adminUserSchema>;
export const adminUserListSchema = listSchema(adminUserSchema);

export const organizationSchema = z.object({
  id: z.string().min(1),
  type: z.enum(["district", "department", "institute", "industry"]),
  name: z.string().min(1),
  /** The district a department, institute or industry belongs to. */
  parent_id: z.string().min(1).nullable().optional(),
});
export type Organization = z.infer<typeof organizationSchema>;
export const organizationListSchema = listSchema(organizationSchema);

export type RoleChange = {
  role: AdminUser["role"];
  district_id: string | null;
  department_id: string | null;
  institute_id: string | null;
  organization_id?: string | null;
  reason: string;
};

/** The API applies the change and writes the audit event in one transaction. */
export function changeUserRole(api: ApiClient, id: string, change: RoleChange) {
  return api.request(`admin/users/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: change,
    schema: adminUserSchema,
  });
}
