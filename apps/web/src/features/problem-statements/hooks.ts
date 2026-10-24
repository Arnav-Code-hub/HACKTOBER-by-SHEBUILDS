"use client";

import { useApiQuery } from "@/lib/api/hooks";

import { statementListSchema } from "./api";

/** Statements in the caller's scope; pass a status to filter. */
export function useStatements(status?: "draft" | "published") {
  return useApiQuery(["statements"], "statements", statementListSchema, {
    query: { status },
  });
}
