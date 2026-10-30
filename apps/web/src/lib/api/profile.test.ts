import { afterEach, describe, expect, it, vi } from "vitest";

import { currentProfile, parseProfile, ProfileError, wakeApi } from "./profile";

const profile = {
  id: "user-1",
  firebase_uid: "firebase-1",
  role: "officer",
  display_name: "Assigned officer",
  email: "officer@example.com",
  district_id: "district-1",
  department_id: "department-1",
  institute_id: null,
};

afterEach(() => vi.unstubAllGlobals());

describe("verified profile contract", () => {
  it("accepts the expected backend identity and role", () => {
    expect(parseProfile(profile, "firebase-1").role).toBe("officer");
  });
  it("rejects a profile belonging to another Firebase identity", () => {
    expect(() => parseProfile(profile, "another-user")).toThrow(
      /invalid or mismatched/,
    );
  });
  it.each(["admin", "SUPER_ADMIN", "unknown", null])(
    "rejects unknown role %s",
    (role) => {
      expect(() => parseProfile({ ...profile, role }, "firebase-1")).toThrow();
    },
  );
  it("rejects a success wrapper or missing scope rather than inferring a role", () => {
    expect(() => parseProfile({ data: profile }, "firebase-1")).toThrow();
    expect(() =>
      parseProfile({ ...profile, district_id: undefined }, "firebase-1"),
    ).toThrow();
  });
});

describe("profile requests", () => {
  it("sends the ID token only to the configured versioned API, without cookies or cache", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify(profile), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetcher);
    const signal = new AbortController().signal;
    await currentProfile(
      "https://api.example.com",
      "id-token",
      "firebase-1",
      signal,
    );
    expect(fetcher).toHaveBeenCalledWith(
      "https://api.example.com/api/v1/users/me",
      {
        headers: {
          Authorization: "Bearer id-token",
          Accept: "application/json",
        },
        cache: "no-store",
        credentials: "omit",
        signal,
      },
    );
  });
  it.each([401, 403, 404, 500])(
    "blocks dashboard access when API responds %s",
    async (status) => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue(new Response("{}", { status })),
      );
      await expect(
        currentProfile(
          "https://api.example.com",
          "token",
          "firebase-1",
          new AbortController().signal,
        ),
      ).rejects.toMatchObject({ status });
    },
  );
  it("rejects malformed JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("<html>unavailable</html>")),
    );
    await expect(
      currentProfile(
        "https://api.example.com",
        "token",
        "firebase-1",
        new AbortController().signal,
      ),
    ).rejects.toThrow(/valid JSON/);
  });
});

describe("API wake-up", () => {
  it("calls /health once without a token or cookies when the API is awake", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response('{"status":"ok"}', { status: 200 }));
    vi.stubGlobal("fetch", fetcher);
    await wakeApi("https://api.example.com", new AbortController().signal);
    expect(fetcher).toHaveBeenCalledTimes(1);
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("https://api.example.com/health");
    expect(init.credentials).toBe("omit");
    expect(JSON.stringify(init.headers)).not.toContain("Authorization");
  });

  it("retries, then fails with a readable error", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response("starting", { status: 503 }));
    vi.stubGlobal("fetch", fetcher);
    await expect(
      wakeApi("https://api.example.com", new AbortController().signal, {
        attempts: 2,
        pauseMs: 0,
      }),
    ).rejects.toBeInstanceOf(ProfileError);
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("keeps waiting while a sleeping host answers 503", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(new Response("starting", { status: 503 }))
      .mockResolvedValueOnce(new Response("starting", { status: 503 }))
      .mockResolvedValue(new Response('{"status":"ok"}', { status: 200 }));
    vi.stubGlobal("fetch", fetcher);
    await wakeApi("https://api.example.com", new AbortController().signal, {
      pauseMs: 0,
    });
    expect(fetcher).toHaveBeenCalledTimes(3);
  });
});
