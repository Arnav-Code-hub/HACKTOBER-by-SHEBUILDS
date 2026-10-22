import { afterEach, describe, expect, it, vi } from "vitest";

import { currentProfile, parseProfile } from "./profile";

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
