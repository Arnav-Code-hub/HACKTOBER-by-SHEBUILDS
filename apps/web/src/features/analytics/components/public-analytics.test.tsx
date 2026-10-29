import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/config", () => ({
  clientConfiguration: () => ({
    apiOrigin: "https://api.example.test",
    problems: [],
  }),
}));

import { PublicAnalytics } from "./public-analytics";

const totals = {
  report_count: 5,
  cluster_count: 2,
  active_cases: 1,
  citizen_verified_cases: 1,
  reports_by_status: {
    citizen_verified: 2,
    in_progress: 1,
    reported: 1,
    rejected: 1,
  },
  clusters_by_status: { citizen_verified: 1, in_progress: 1 },
  sample_data: false,
  updated_at: "2026-10-29T10:00:00Z",
};

function show() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <PublicAnalytics />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("public homepage statistics", () => {
  it("shows real report counts separately from case counts without sending credentials", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(totals)));
    vi.stubGlobal("fetch", fetcher);
    show();
    await screen.findByText("Resolved complaints");
    const cards = screen.getByRole("list", { name: "Public complaint totals" });
    expect(cards.textContent).toMatch(/Total complaints5/);
    expect(cards.textContent).toMatch(/Open complaints2/);
    expect(cards.textContent).toMatch(/Resolved complaints2/);
    expect(screen.getByText(/2 community cases/)).toBeTruthy();
    const [url, init] = fetcher.mock.calls[0]!;
    expect(url).toBe("https://api.example.test/api/v1/analytics/public");
    expect(init.credentials).toBe("omit");
    expect(init.headers).not.toHaveProperty("Authorization");
  });

  it("shows an unavailable message and retries instead of inventing zero totals", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("offline"));
    vi.stubGlobal("fetch", fetcher);
    show();
    await waitFor(
      () =>
        expect(screen.getByRole("alert").textContent).toMatch(/unavailable/i),
      { timeout: 5000 },
    );
    expect(
      screen.queryByRole("list", { name: "Public complaint totals" }),
    ).toBeNull();
    fetcher.mockResolvedValue(new Response(JSON.stringify(totals)));
    fireEvent.click(screen.getByRole("button", { name: "Retry statistics" }));
    await screen.findByText("Resolved complaints");
  });

  it("displays genuine zero statistics for an empty non-demo dataset", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            ...totals,
            report_count: 0,
            cluster_count: 0,
            active_cases: 0,
            citizen_verified_cases: 0,
            reports_by_status: {},
            clusters_by_status: {},
            updated_at: null,
          }),
        ),
      ),
    );
    show();
    await screen.findByText(/No non-demo complaints/);
    expect(
      screen.getByRole("list", { name: "Public complaint totals" }).textContent,
    ).toMatch(/Resolved complaints0/);
  });

  it("retains the last loaded counts when a refresh fails", async () => {
    const fetcher = vi
      .fn()
      .mockImplementation(async () => new Response(JSON.stringify(totals)));
    vi.stubGlobal("fetch", fetcher);
    show();
    await screen.findByText("Resolved complaints");
    fetcher.mockRejectedValue(new Error("offline"));
    fireEvent.click(screen.getByRole("button", { name: "Refresh statistics" }));
    await waitFor(
      () =>
        expect(screen.getByRole("alert").textContent).toMatch(/last loaded/),
      { timeout: 5000 },
    );
    expect(
      screen.getByRole("list", { name: "Public complaint totals" }).textContent,
    ).toMatch(/Resolved complaints2/);
  });

  it("refuses inconsistent statistics", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(
        async () =>
          new Response(
            JSON.stringify({
              ...totals,
              report_count: 999,
            }),
          ),
      ),
    );
    show();
    await waitFor(
      () =>
        expect(screen.getByRole("alert").textContent).toMatch(/unavailable/i),
      { timeout: 5000 },
    );
    expect(
      screen.queryByRole("list", { name: "Public complaint totals" }),
    ).toBeNull();
  });

  it("labels demonstration figures as sample data", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockImplementation(
          async () =>
            new Response(JSON.stringify({ ...totals, sample_data: true })),
        ),
    );
    show();
    const list = await screen.findByRole("list", {
      name: "Sample complaint totals",
    });
    expect(list.textContent).toMatch(/Total complaints5/);
    expect(screen.getByText("Sample data")).toBeTruthy();
    expect(screen.getByText(/They are not real complaints/)).toBeTruthy();
    expect(screen.queryByText(/No non-demo complaints/)).toBeNull();
  });
});
