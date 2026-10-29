import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  harnessConfigModule,
  harnessSessionModule,
  installFakeApi,
  rankedCluster,
  renderWorkspace,
} from "@/test/api-harness";

vi.mock("@/lib/auth/session", () => harnessSessionModule);
vi.mock("@/lib/config", () => harnessConfigModule);

import { DepartmentWorkspace } from "./department-workspace";

afterEach(() => vi.unstubAllGlobals());

function routes(clusters: Record<string, unknown>[]) {
  return {
    "GET clusters/ranked": () => ({ items: clusters }),
    "GET users": () => ({
      items: [{ id: "o1", display_name: "Asha (Officer)", email: null }],
    }),
    "GET statements": () => ({ items: [] }),
    "GET cases": () => ({ items: [] }),
  };
}

async function openCluster() {
  await waitFor(() =>
    expect(screen.getAllByText("Open").length).toBeGreaterThan(0),
  );
  fireEvent.click(screen.getAllByText("Open")[0]!);
}

describe("Department workspace", () => {
  it("explains the rank and labels demo inputs", async () => {
    installFakeApi(routes([rankedCluster()]));
    await renderWorkspace(<DepartmentWorkspace />);
    await openCluster();
    expect(screen.getAllByText("Demo value")).toHaveLength(2);
    expect(screen.getByText(/not a population estimate/)).toBeTruthy();
  });

  it("funds in paise with a confirmed, idempotent request", async () => {
    const api = installFakeApi({
      ...routes([rankedCluster()]),
      "POST clusters/c1/fund": () => ({
        allocation_id: "a1",
        work_order_id: "w1",
      }),
    });
    await renderWorkspace(<DepartmentWorkspace />);
    await openCluster();
    await waitFor(() =>
      expect(screen.getByText("Asha (Officer)")).toBeTruthy(),
    );

    fireEvent.change(screen.getByLabelText(/Allocation/), {
      target: { value: "1,50,000" },
    });
    fireEvent.change(screen.getByLabelText(/Assign to officer/), {
      target: { value: "o1" },
    });
    fireEvent.click(screen.getByText("Record allocation"));
    expect(
      screen.getByText(/Allocate ₹1,50,000.00 .* Asha \(Officer\)/),
    ).toBeTruthy();
    await act(async () => fireEvent.click(screen.getByText("Confirm")));

    const [fund] = api.to("POST", "clusters/c1/fund");
    expect(fund!.body).toEqual({ amount_paise: 15_000_000, officer_id: "o1" });
    expect(fund!.headers["Idempotency-Key"]).toBeTruthy();
    expect(
      screen.getByText("Allocation recorded and work order assigned."),
    ).toBeTruthy();
  });

  it("does not offer funding for a cluster that is already funded", async () => {
    installFakeApi(routes([rankedCluster({ status: "funded" })]));
    await renderWorkspace(<DepartmentWorkspace />);
    await openCluster();
    expect(screen.queryByText("Record allocation")).toBeNull();
    expect(
      screen.getByText(/Only a prioritised cluster can be funded/),
    ).toBeTruthy();
  });

  it("updates the official ranking inputs within 0–100", async () => {
    const api = installFakeApi({
      ...routes([rankedCluster()]),
      "PATCH clusters/c1/inputs": () => ({ id: "c1" }),
    });
    await renderWorkspace(<DepartmentWorkspace />);
    await openCluster();

    fireEvent.change(
      screen.getByLabelText("Infrastructure gap", { selector: "input" }),
      { target: { value: "140" } },
    );
    fireEvent.click(screen.getByText("Save inputs"));
    expect(screen.getByRole("alert").textContent).toMatch(/between 0 and 100/);

    fireEvent.change(
      screen.getByLabelText("Infrastructure gap", { selector: "input" }),
      { target: { value: "75" } },
    );
    fireEvent.click(screen.getByText("Save inputs"));
    await act(async () => fireEvent.click(screen.getByText("Confirm")));
    expect(api.to("PATCH", "clusters/c1/inputs")[0]!.body).toEqual({
      infrastructure_gap: 75,
      equity_index: 50,
    });
  });
});
