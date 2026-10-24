import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  harnessConfigModule,
  harnessSessionModule,
  installFakeApi,
  rankedCluster,
  renderWorkspace,
  report,
} from "@/test/api-harness";

vi.mock("@/lib/auth/session", () => harnessSessionModule);
vi.mock("@/lib/config", () => harnessConfigModule);

import { PanchayatWorkspace } from "./panchayat-workspace";

afterEach(() => vi.unstubAllGlobals());

function routes(current: Record<string, unknown>) {
  return {
    "GET reports": ({ url }: { url: URL }) => ({
      items: url.searchParams.get("status") === current.status ? [current] : [],
    }),
    "GET reports/r1": () => current,
    "GET clusters/ranked": () => ({ items: [rankedCluster()] }),
    "GET reports/r1/cluster-suggestions": () => ({
      items: [
        {
          id: "c1",
          title: "Handpump not working",
          category: "water",
          distance_m: 42.4,
          report_count: 3,
          supporter_count: 14,
        },
      ],
    }),
  };
}

async function open() {
  await waitFor(() =>
    expect(screen.getAllByText("Open").length).toBeGreaterThan(0),
  );
  fireEvent.click(screen.getAllByText("Open")[0]!);
  await waitFor(() =>
    expect(screen.getByLabelText("Report YDG-WTR-0001")).toBeTruthy(),
  );
}

describe("Panchayat workspace", () => {
  it("validates a report after confirmation and refreshes the queues", async () => {
    const current = report();
    const api = installFakeApi({
      ...routes(current),
      "POST reports/r1/validate": () => {
        current.status = "verified";
        return { id: "r1", status: "verified" };
      },
    });
    await renderWorkspace(<PanchayatWorkspace />);
    await open();
    expect(screen.getByText("Water (provisional)")).toBeTruthy();

    fireEvent.click(screen.getByText("Validate report"));
    expect(api.to("POST", "reports/r1/validate")).toHaveLength(0);
    await act(async () => fireEvent.click(screen.getByText("Confirm")));

    expect(api.to("POST", "reports/r1/validate")[0]!.body).toEqual({
      decision: "verify",
    });
    await waitFor(() =>
      expect(
        screen.getByText("Confirm cluster", { selector: "h2" }),
      ).toBeTruthy(),
    );
    expect(api.to("GET", "reports").length).toBeGreaterThan(2);
  });

  it("requires a reason to decline, and sends it", async () => {
    const api = installFakeApi({
      ...routes(report()),
      "POST reports/r1/validate": () => ({ id: "r1", status: "rejected" }),
    });
    await renderWorkspace(<PanchayatWorkspace />);
    await open();

    fireEvent.click(screen.getByText("Decline report"));
    expect(screen.getByRole("alert").textContent).toMatch(/Reason is required/);

    fireEvent.change(screen.getByLabelText(/Reason/), {
      target: { value: "Outside this Panchayat" },
    });
    fireEvent.click(screen.getByText("Decline report"));
    await act(async () => fireEvent.click(screen.getByText("Confirm")));
    expect(api.to("POST", "reports/r1/validate")[0]!.body).toEqual({
      decision: "reject",
      reason: "Outside this Panchayat",
    });
  });

  it("offers nearby clusters but lets the Panchayat start a new one", async () => {
    const api = installFakeApi({
      ...routes(report({ status: "verified" })),
      "POST reports/r1/cluster": () => ({ id: "r1", status: "prioritised" }),
    });
    await renderWorkspace(<PanchayatWorkspace />);
    await open();

    const select = await screen.findByLabelText(/^Cluster/);
    await waitFor(() =>
      expect(screen.getByText(/42 m away · 3 reports/)).toBeTruthy(),
    );

    fireEvent.change(select, { target: { value: "__new__" } });
    fireEvent.click(
      screen.getByText("Confirm cluster", { selector: "button" }),
    );
    await act(async () => fireEvent.click(screen.getByText("Confirm")));
    expect(api.to("POST", "reports/r1/cluster")[0]!.body).toEqual({
      new: true,
    });
  });

  it("shows the API's refusal instead of pretending the action worked", async () => {
    installFakeApi({
      ...routes(report()),
      "POST reports/r1/validate": () =>
        new Response(
          JSON.stringify({ detail: "Report is outside your Panchayat." }),
          {
            status: 403,
          },
        ),
    });
    await renderWorkspace(<PanchayatWorkspace />);
    await open();
    fireEvent.click(screen.getByText("Validate report"));
    await act(async () => fireEvent.click(screen.getByText("Confirm")));
    expect(screen.getByRole("alert").textContent).toMatch(
      /outside your Panchayat/,
    );
  });
});
