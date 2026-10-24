import type { z } from "zod";

/**
 * Authenticated business API transport for the staff workspace.
 *
 * - Every call fetches a fresh Firebase ID token, so the hourly refresh needs
 *   no session event (see lib/auth/session.tsx).
 * - Paths are relative to `/api/v1`; an absolute URL is refused so the token
 *   can never be sent to another host.
 * - Responses are validated with a zod schema before callers see them.
 * Cloudinary uploads use a separate, unauthenticated fetch (lib/api/media.ts).
 */

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type RequestOptions<T> = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  query?: Record<string, string | number | boolean | undefined>;
  body?: unknown;
  schema: z.ZodType<T>;
  idempotencyKey?: string;
  timeoutMs?: number;
  signal?: AbortSignal;
};

export type ApiClient = {
  request<T>(path: string, options: RequestOptions<T>): Promise<T>;
};

const MESSAGES: Record<number, string> = {
  400: "The server rejected the submitted details. Check the fields.",
  401: "Your session was rejected. Sign out and sign in again.",
  403: "Your account cannot perform this action.",
  404: "That record was not found, or it is outside your scope.",
  409: "This conflicts with an existing action. Refresh and check before retrying.",
  422: "The server rejected the submitted details. Check the fields.",
};

/** A FastAPI `detail` string is shown; a validation list is summarised. */
function messageFor(status: number, detail: unknown): string {
  if (typeof detail === "string" && detail.length <= 300) return detail;
  if (Array.isArray(detail) && detail.length && status === 422) {
    const first = detail[0] as { loc?: unknown[]; msg?: unknown };
    const field = Array.isArray(first.loc) ? first.loc.at(-1) : undefined;
    if (typeof first.msg === "string")
      return field ? `${String(field)}: ${first.msg}` : first.msg;
  }
  return (
    MESSAGES[status] ??
    "The service is unavailable. Retry after the API is available."
  );
}

/**
 * Rejects with the caller's own abort reason, so React Query recognises the
 * cancellation instead of showing it as a failed request.
 */
function throwIfCancelled(signal: AbortSignal | undefined): void {
  if (signal?.aborted) {
    throw (
      signal.reason ??
      new DOMException("The request was cancelled.", "AbortError")
    );
  }
}

export function createApiClient({
  apiOrigin,
  getToken,
  fetcher = (...args: Parameters<typeof fetch>) => fetch(...args),
}: {
  apiOrigin: string;
  getToken: () => Promise<string>;
  fetcher?: typeof fetch;
}): ApiClient {
  return {
    async request<T>(path: string, options: RequestOptions<T>): Promise<T> {
      if (/^[a-z][a-z\d+.-]*:|^\/\//i.test(path) || path.startsWith("/")) {
        throw new ApiError("API paths must be relative to /api/v1.", null);
      }
      const url = new URL(`${apiOrigin}/api/v1/${path}`);
      for (const [key, value] of Object.entries(options.query ?? {})) {
        if (value !== undefined) url.searchParams.set(key, String(value));
      }

      // A request cancelled before it starts never fetches a token or sends.
      throwIfCancelled(options.signal);

      const controller = new AbortController();
      const abort = () => controller.abort();
      options.signal?.addEventListener("abort", abort);
      const timer = setTimeout(abort, options.timeoutMs ?? 30_000);
      try {
        let token: string;
        try {
          token = await getToken();
        } catch {
          throw new ApiError(
            "Your session could not be refreshed. Sign out and sign in again.",
            401,
          );
        }
        throwIfCancelled(options.signal);
        let response: Response;
        try {
          response = await fetcher(url.toString(), {
            method: options.method ?? "GET",
            headers: {
              Authorization: `Bearer ${token}`,
              Accept: "application/json",
              ...(options.body !== undefined && {
                "Content-Type": "application/json",
              }),
              ...(options.idempotencyKey && {
                "Idempotency-Key": options.idempotencyKey,
              }),
            },
            body:
              options.body === undefined
                ? undefined
                : JSON.stringify(options.body),
            cache: "no-store",
            credentials: "omit",
            signal: controller.signal,
          });
        } catch {
          // Cancelled by the caller (navigation, sign-out): not an error to show.
          throwIfCancelled(options.signal);
          throw new ApiError(
            controller.signal.aborted
              ? "The request timed out. Check the record before retrying."
              : "Cannot reach the API. Check the connection and retry.",
            null,
          );
        }

        const text = await response.text();
        let payload: unknown = null;
        if (text) {
          try {
            payload = JSON.parse(text);
          } catch {
            if (response.ok)
              throw new ApiError(
                "The server returned an invalid response.",
                response.status,
              );
          }
        }
        if (!response.ok) {
          const detail =
            payload && typeof payload === "object" && "detail" in payload
              ? (payload as { detail: unknown }).detail
              : undefined;
          throw new ApiError(
            messageFor(response.status, detail),
            response.status,
            detail,
          );
        }
        const parsed = options.schema.safeParse(payload);
        if (!parsed.success) {
          throw new ApiError(
            "The server response did not match the expected format.",
            response.status,
            parsed.error.issues,
          );
        }
        return parsed.data;
      } finally {
        clearTimeout(timer);
        options.signal?.removeEventListener("abort", abort);
      }
    },
  };
}

/** A random key for one logical submission; reuse it when retrying. */
export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}
