"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useContext } from "react";
import type { z } from "zod";

import type { RequestOptions } from "@/lib/api/client";
import { ScopeContext, useApi, useScopedKey } from "@/lib/api/use-api";

/**
 * A scoped GET. The key is prefixed with the signed-in identity, and React
 * Query's signal is passed through so navigation and sign-out cancel the
 * request. Pass `enabled: false` until required inputs (an ID) exist.
 */
export function useApiQuery<T>(
  key: unknown[],
  path: string,
  schema: z.ZodType<T>,
  {
    query,
    enabled = true,
  }: { query?: RequestOptions<T>["query"]; enabled?: boolean } = {},
) {
  const api = useApi();
  return useQuery({
    queryKey: useScopedKey(...key, query ?? {}),
    queryFn: ({ signal }) => api.request(path, { schema, query, signal }),
    enabled,
  });
}

/** Refetches every scoped query whose key starts with `prefix`, after a write. */
export function useInvalidate() {
  const client = useQueryClient();
  const scope = useContext(ScopeContext);
  return useCallback(
    (...prefix: unknown[]) =>
      client.invalidateQueries({ queryKey: [scope, ...prefix] }),
    [client, scope],
  );
}
