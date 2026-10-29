"use client";

import { useApiQuery } from "@/lib/api/hooks";

import { caseListSchema } from "./api";

/** Departments see their own cases; administrators see their district. */
export function useCases() {
  return useApiQuery(["cases"], "cases", caseListSchema);
}
