"use client";

import { useApiQuery } from "@/lib/api/hooks";
import { evidenceSchema } from "@/lib/api/schemas";

import { workOrderListSchema } from "./api";

/** Work orders assigned to the signed-in officer. */
export function useMyWorkOrders() {
  return useApiQuery(["work-orders"], "work-orders", workOrderListSchema, {
    query: { mine: true },
  });
}

export function useWorkOrderEvidence(id: string | null, enabled: boolean) {
  return useApiQuery(
    ["work-orders", id, "evidence"],
    `work-orders/${encodeURIComponent(id ?? "")}/evidence`,
    evidenceSchema,
    { enabled: Boolean(id) && enabled },
  );
}
