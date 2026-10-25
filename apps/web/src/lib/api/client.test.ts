import { describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { ApiError, createApiClient } from "./client";

const ok = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status });

function client(fetcher: ReturnType<typeof vi.fn>) {
  return createApiClient({
    apiOrigin: "https://api.example.com",
    getToken: async () => "fresh-token",
    fetcher: fetcher as unknown as typeof fetch,
  });
}

describe("API client", () => {
  it("sends a fresh token to the versioned API only, without cookies", async () => {
    const fetcher = vi.fn().mockResolvedValue(ok({ items: [] }));
    await client(fetcher).request("reports", {
      query: { status: "reported", limit: undefined },
      schema: z.object({ items: z.array(z.unknown()) }),
    });
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("https://api.example.com/api/v1/reports?status=reported");
    expect(init.headers).toMatchObject({ Authorization: "Bearer fresh-token" });
    expect(init.credentials).toBe("omit");
  });

  it("refuses absolute or rooted paths so the token cannot leave the API", async () => {
    const fetcher = vi.fn();
    for (const path of [
      "https://evil.example/x",
      "//evil.example/x",
      "/api/v1/reports",
    ]) {
      await expect(
        client(fetcher).request(path, { schema: z.unknown() }),
      ).rejects.toBeInstanceOf(ApiError);
    }
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("sends JSON bodies and the idempotency key", async () => {
    const fetcher = vi.fn().mockResolvedValue(ok({ id: "a1" }, 201));
    await client(fetcher).request("clusters/c1/fund", {
      method: "POST",
      body: { amount_paise: 100 },
      idempotencyKey: "key-1",
      schema: z.object({ id: z.string() }),
    });
    const [, init] = fetcher.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(init.body).toBe('{"amount_paise":100}');
    expect(init.headers).toMatchObject({
      "Content-Type": "application/json",
      "Idempotency-Key": "key-1",
    });
  });

  it("shows the server's detail, or a readable message per status", async () => {
    const cases: [Response, RegExp, number][] = [
      [
        ok({ detail: "Work order is not awaiting verification." }, 409),
        /not awaiting/,
        409,
      ],
      [
        ok(
          { detail: [{ loc: ["body", "amount_paise"], msg: "must be > 0" }] },
          422,
        ),
        /amount_paise: must be > 0/,
        422,
      ],
      [ok({}, 403), /cannot perform this action/, 403],
      [new Response("oops", { status: 502 }), /service is unavailable/, 502],
    ];
    for (const [response, message, status] of cases) {
      const error = await client(vi.fn().mockResolvedValue(response))
        .request("x", { schema: z.unknown() })
        .catch((caught: unknown) => caught);
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).message).toMatch(message);
      expect((error as ApiError).status).toBe(status);
    }
  });

  it("rejects a success response that does not match the schema", async () => {
    const fetcher = vi.fn().mockResolvedValue(ok({ items: "nope" }));
    await expect(
      client(fetcher).request("reports", {
        schema: z.object({ items: z.array(z.unknown()) }),
      }),
    ).rejects.toThrow(/expected format/);
  });

  it("turns a network failure and a timeout into readable errors", async () => {
    await expect(
      client(vi.fn().mockRejectedValue(new TypeError("fetch failed"))).request(
        "x",
        { schema: z.unknown() },
      ),
    ).rejects.toThrow(/Cannot reach the API/);

    const hanging = vi.fn(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) =>
          init.signal?.addEventListener("abort", () =>
            reject(new DOMException("aborted", "AbortError")),
          ),
        ),
    );
    await expect(
      client(hanging).request("x", { schema: z.unknown(), timeoutMs: 10 }),
    ).rejects.toThrow(/timed out/);
  });

  it("never fetches a token or sends a request that is already cancelled", async () => {
    const fetcher = vi.fn();
    const getToken = vi.fn(async () => "token");
    const api = createApiClient({
      apiOrigin: "https://api.example.com",
      getToken,
      fetcher: fetcher as unknown as typeof fetch,
    });
    const controller = new AbortController();
    controller.abort();

    const error = await api
      .request("work-orders", {
        schema: z.unknown(),
        signal: controller.signal,
      })
      .catch((caught: unknown) => caught);

    expect((error as DOMException).name).toBe("AbortError");
    expect(getToken).not.toHaveBeenCalled();
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("does not send when cancelled while the token is being fetched", async () => {
    const fetcher = vi.fn();
    const controller = new AbortController();
    const api = createApiClient({
      apiOrigin: "https://api.example.com",
      getToken: async () => {
        controller.abort();
        return "token";
      },
      fetcher: fetcher as unknown as typeof fetch,
    });
    await expect(
      api.request("x", { schema: z.unknown(), signal: controller.signal }),
    ).rejects.toMatchObject({ name: "AbortError" });
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("reports a caller cancellation mid-request as a cancellation, not an outage", async () => {
    const controller = new AbortController();
    const hanging = vi.fn(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) =>
          init.signal?.addEventListener("abort", () =>
            reject(new DOMException("aborted", "AbortError")),
          ),
        ),
    );
    const pending = client(hanging).request("x", {
      schema: z.unknown(),
      signal: controller.signal,
    });
    await vi.waitFor(() => expect(hanging).toHaveBeenCalled());
    controller.abort();
    const error = await pending.catch((caught: unknown) => caught);
    expect(error).not.toBeInstanceOf(ApiError);
    expect((error as DOMException).name).toBe("AbortError");
  });
});
