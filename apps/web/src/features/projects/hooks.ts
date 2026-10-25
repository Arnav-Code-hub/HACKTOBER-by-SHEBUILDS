"use client";

import { useApiQuery } from "@/lib/api/hooks";

import { submissionListSchema } from "./api";

/** The signed-in student's team submissions. */
export function useMySubmissions() {
  return useApiQuery(["submissions"], "submissions", submissionListSchema, {
    query: { mine: true },
  });
}

/** Submissions from teams at the caller's institute. */
export function useInstituteSubmissions() {
  return useApiQuery(["submissions"], "submissions", submissionListSchema, {
    query: { institute: "me" },
  });
}
