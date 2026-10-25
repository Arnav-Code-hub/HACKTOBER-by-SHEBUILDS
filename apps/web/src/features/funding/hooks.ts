"use client";

import { useApiQuery } from "@/lib/api/hooks";

import { officerListSchema, sponsorshipListSchema } from "./api";

/** Officers the API allows the caller to assign — its own district only. */
export function useAssignableOfficers() {
  return useApiQuery(["users", "officers"], "users", officerListSchema, {
    query: { role: "officer" },
  });
}

/** The caller's organisation's pledges. */
export function useMySponsorships() {
  return useApiQuery(["sponsorships"], "sponsorships", sponsorshipListSchema, {
    query: { mine: true },
  });
}
