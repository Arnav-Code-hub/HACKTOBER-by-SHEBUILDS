"use client";

import { useApiQuery } from "@/lib/api/hooks";

import { teamListSchema } from "./api";

/** The signed-in student's teams. */
export function useMyTeams() {
  return useApiQuery(["teams"], "teams", teamListSchema, {
    query: { mine: true },
  });
}

/** Teams at the caller's institute — the API scopes this to the institute. */
export function useInstituteTeams() {
  return useApiQuery(["teams"], "teams", teamListSchema, {
    query: { institute: "me" },
  });
}
