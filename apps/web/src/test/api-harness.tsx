import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";

/**
 * A fake backend for page tests: the real API client, cache and upload code
 * run against a stubbed `fetch`. Routes are "METHOD path" with the path after
 * /api/v1 (query strings ignored), or a full URL for third-party calls.
 *
 * The test file must mock the session and config modules first:
 *
 *   vi.mock("@/lib/auth/session", () => harnessSessionModule);
 *   vi.mock("@/lib/config", () => harnessConfigModule);
 */

export const API_ORIGIN = "https://api.example.test";

export type Call = {
  method: string;
  path: string;
  url: URL;
  body: unknown;
  headers: Record<string, string>;
};

export type Route = (call: Call) => unknown | Response;

export const harnessSession = {
  state: {
    status: "authenticated",
    user: { uid: "firebase-staff", getIdToken: async () => "staff-token" },
    profile: {
      id: "staff-1",
      firebase_uid: "firebase-staff",
      role: "panchayat",
      display_name: "Staff",
      email: null,
      district_id: "district-1",
      department_id: null,
      institute_id: null,
    },
  } as Record<string, unknown>,
};

export const harnessSessionModule = { useSession: () => harnessSession };
export const harnessConfigModule = {
  clientConfiguration: () => ({
    apiOrigin: API_ORIGIN,
    firebase: {},
    problems: [],
  }),
};

export function installFakeApi(routes: Record<string, Route>) {
  const calls: Call[] = [];
  const fetcher = vi.fn(async (input: string, init: RequestInit = {}) => {
    const url = new URL(input);
    const method = (init.method ?? "GET").toUpperCase();
    const path =
      url.origin === API_ORIGIN
        ? url.pathname.replace(/^\/api\/v1\//, "")
        : `${url.origin}${url.pathname}`;
    const body =
      typeof init.body === "string"
        ? JSON.parse(init.body)
        : (init.body ?? null);
    const call: Call = {
      method,
      path,
      url,
      body,
      headers: (init.headers ?? {}) as Record<string, string>,
    };
    calls.push(call);
    const route = routes[`${method} ${path}`];
    if (!route) {
      return new Response(
        JSON.stringify({ detail: `No fake route for ${method} ${path}` }),
        {
          status: 404,
        },
      );
    }
    const result = await route(call);
    return result instanceof Response
      ? result
      : new Response(JSON.stringify(result), { status: 200 });
  });
  vi.stubGlobal("fetch", fetcher);
  return {
    calls,
    /** Calls to one route, in order. */
    to: (method: string, path: string) =>
      calls.filter((c) => c.method === method && c.path === path),
  };
}

export async function renderWorkspace(ui: ReactElement) {
  const { QueryProvider } = await import("@/lib/api/use-api");
  return render(<QueryProvider>{ui}</QueryProvider>);
}

export const media = (id: string) => ({
  id,
  url: `https://res.cloudinary.com/demo/image/upload/${id}.jpg`,
  thumbnail_url: `https://res.cloudinary.com/demo/image/upload/c_limit,w_320/${id}.jpg`,
});

export function report(overrides: Record<string, unknown> = {}) {
  return {
    id: "r1",
    code: "YDG-WTR-0001",
    title: "Handpump not working",
    description: "No water since Monday.",
    transcript: null,
    category: "water",
    severity: "high",
    status: "reported",
    ward: "Ward 4",
    district: "Yadgir",
    latitude: 16.76,
    longitude: 77.14,
    created_at: "2026-10-20T08:00:00Z",
    media: [media("before")],
    cluster_id: null,
    rejection_reason: null,
    ...overrides,
  };
}

export function factors(demo = true) {
  return [
    {
      factor: "support",
      label: "Community support",
      score: 60,
      weight: 0.3,
      is_demo: false,
    },
    {
      factor: "gap",
      label: "Infrastructure gap",
      score: 50,
      weight: 0.22,
      is_demo: demo,
    },
    {
      factor: "equity",
      label: "Equity",
      score: 50,
      weight: 0.2,
      is_demo: demo,
    },
    {
      factor: "severity",
      label: "Severity",
      score: 80,
      weight: 0.18,
      is_demo: false,
    },
    {
      factor: "age",
      label: "Time unaddressed",
      score: 10,
      weight: 0.1,
      is_demo: false,
    },
  ];
}

export function rankedCluster(overrides: Record<string, unknown> = {}) {
  return {
    id: "c1",
    title: "Handpump not working",
    category: "water",
    status: "prioritised",
    rank: 1,
    priority_score: 52.4,
    supporter_count: 14,
    report_count: 3,
    anchor_report_code: "YDG-WTR-0001",
    infrastructure_gap: 50,
    equity_index: 50,
    inputs_are_demo: true,
    score_breakdown: factors(),
    ...overrides,
  };
}

/** Signs the harness in as another role (and so another cache scope). */
export function signInAs(role: string) {
  const profile = harnessSession.state.profile as Record<string, unknown>;
  harnessSession.state = {
    ...harnessSession.state,
    profile: { ...profile, role },
  };
}

export function statement(overrides: Record<string, unknown> = {}) {
  return {
    id: "s1",
    title: "Low-cost handpump maintenance alerts",
    body: "Design a way for villagers to report handpump faults early.",
    status: "published",
    cluster_id: "c1",
    published_at: "2026-10-23T09:00:00Z",
    ...overrides,
  };
}
