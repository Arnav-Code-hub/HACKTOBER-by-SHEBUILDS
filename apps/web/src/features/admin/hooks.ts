"use client";

import { useApiQuery } from "@/lib/api/hooks";

import {
  adminUserListSchema,
  AUDIT_PAGE_SIZE,
  auditListSchema,
  organizationListSchema,
  summarySchema,
} from "./api";

export function useAdminSummary() {
  return useApiQuery(["admin", "summary"], "admin/summary", summarySchema);
}

export function useAuditEvents() {
  return useApiQuery(["admin", "audit"], "admin/audit", auditListSchema, {
    query: { limit: AUDIT_PAGE_SIZE },
  });
}

/** Super admin only; the API refuses other roles. */
export function useAdminUsers(enabled: boolean) {
  return useApiQuery(["admin", "users"], "admin/users", adminUserListSchema, {
    enabled,
  });
}

export function useOrganizations(enabled: boolean) {
  return useApiQuery(
    ["organizations"],
    "organizations",
    organizationListSchema,
    { enabled },
  );
}
