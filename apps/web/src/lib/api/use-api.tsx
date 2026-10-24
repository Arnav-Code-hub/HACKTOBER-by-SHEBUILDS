"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError, createApiClient, type ApiClient } from "@/lib/api/client";
import { useSession } from "@/lib/auth/session";
import { clientConfiguration } from "@/lib/config";

/**
 * The API client for the signed-in staff member. Only usable inside the
 * authenticated dashboard shell, which renders nothing until the session is
 * confirmed by the API.
 *
 * Query functions must pass React Query's `signal` through to `request`, so a
 * sign-out or navigation actually cancels the HTTP request.
 */
export function useApi(): ApiClient {
  const { state } = useSession();
  const user = state.status === "authenticated" ? state.user : null;
  return useMemo(() => {
    if (!user) {
      return {
        request: () =>
          Promise.reject(new ApiError("Sign in to use the workspace.", 401)),
      };
    }
    return createApiClient({
      apiOrigin: clientConfiguration().apiOrigin,
      getToken: () => user.getIdToken(),
    });
  }, [user]);
}

/** Retries only transient failures; a 4xx answer will not change on retry. */
function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status !== null && error.status < 500)
    return false;
  return failureCount < 1;
}

function newQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: shouldRetry,
        refetchOnWindowFocus: false,
        staleTime: 15_000,
      },
      // Writes are never retried automatically: the official decides.
      mutations: { retry: false },
    },
  });
}

/**
 * Who the cached data belongs to: the confirmed backend identity and its
 * scope. Any change — sign-out, another account, a role or scope change by an
 * administrator — is a different scope.
 */
export function sessionScope(
  state: ReturnType<typeof useSession>["state"],
): string {
  if (state.status !== "authenticated") return "signed-out";
  const { id, role, district_id, department_id, institute_id } = state.profile;
  return JSON.stringify([id, role, district_id, department_id, institute_id]);
}

export const ScopeContext = createContext<string>("signed-out");

/**
 * Prefixes a query key with the current identity and scope, so a key can
 * never match another account's cached records even within one cache.
 *
 *   useQuery({ queryKey: useScopedKey("work-orders", { mine: true }), ... })
 */
export function useScopedKey(...parts: unknown[]): unknown[] {
  return [useContext(ScopeContext), ...parts];
}

/**
 * One query cache per identity. When the scope changes, the previous cache's
 * in-flight requests are cancelled and its records discarded, and the
 * workspace remounts against a fresh, empty cache.
 */
export function QueryProvider({ children }: { children: ReactNode }) {
  const { state } = useSession();
  const scope = sessionScope(state);
  const [store, setStore] = useState(() => ({
    scope,
    client: newQueryClient(),
  }));

  // Replace the cache during render, before any child can read the old one.
  let current = store;
  if (store.scope !== scope) {
    current = { scope, client: newQueryClient() };
    setStore(current);
  }

  useEffect(() => {
    const client = current.client;
    return () => {
      void client.cancelQueries();
      client.clear();
    };
  }, [current.client]);

  return (
    <ScopeContext.Provider value={current.scope}>
      <QueryClientProvider key={current.scope} client={current.client}>
        {children}
      </QueryClientProvider>
    </ScopeContext.Provider>
  );
}
