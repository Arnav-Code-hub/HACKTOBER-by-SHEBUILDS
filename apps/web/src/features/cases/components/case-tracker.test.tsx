import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  harnessConfigModule,
  harnessSessionModule,
  installFakeApi,
  media,
  renderWorkspace,
  signInAs,
} from "@/test/api-harness";

vi.mock("@/lib/auth/session", () => harnessSessionModule);
vi.mock("@/lib/config", () => harnessConfigModule);

import { CaseTracker } from "./case-tracker";

afterEach(() => vi.unstubAllGlobals());

const base = {
  category: "water",
  status_changed_at: "2026-10-26T09:00:00Z",
  work_order_id: null,
  round: null,
  department_name: null,
  officer_name: null,
  allocated_paise: null,
  allocated_at: null,
  allocated_by_name: null,
};

const returned = {
  ...base,
  cluster_id: "c1",
  report_code: "YDG-WTR-0001",
  title: "Handpump not working",
  status: "in_progress",
  waiting_on: "officer",
  work_order_id: "w1",
  round: 2,
  department_name: "Rural Water Supply",
  officer_name: "Asha (Officer)",
  allocated_paise: 15_000_000,
  allocated_at: "2026-10-22T09:00:00Z",
  allocated_by_name: "Ravi (Department)",
};

const unfunded = {
  ...base,
  cluster_id: "c2",
  report_code: "YDG-WTR-0002",
  title: "Pipeline leak",
  status: "prioritised",
  waiting_on: "department",
};

const verified = {
  ...returned,
  cluster_id: "c3",
  report_code: "YDG-WTR-0003",
  title: "Tap repaired",
  status: "citizen_verified",
  waiting_on: "none",
  work_order_id: "w3",
  round: 1,
};

function routes() {
  return {
    "GET cases": () => ({ items: [returned, unfunded, verified] }),
    "GET work-orders/w1/evidence": () => ({
      report_code: "YDG-WTR-0001",
      status: "in_progress",
      before: { url: media("before").url, uploaded_at: "2026-10-20T08:00:00Z" },
      after: { url: media("after").url, uploaded_at: "2026-10-24T08:00:00Z" },
      after_round: 1,
      card_url: null,
      verdict_label: "Round 1 · returned for correction",
      returned_comment: "Still no water in the evening.",
    }),
  };
}

describe("Case tracker", () => {
  it("counts who each case is waiting on", async () => {
    signInAs("gov_admin");
    installFakeApi(routes());
    await renderWorkspace(<CaseTracker description="District cases." />);
    const counts = await screen.findByRole("list", {
      name: "Who the cases are waiting on",
    });
    await waitFor(() =>
      expect(
        within(counts)
          .getAllByRole("listitem")
          .map((item) => item.textContent),
      ).toEqual([
        "Waiting on department1",
        "Waiting on officer1",
        "Waiting on citizen0",
        "Verified by citizens1",
      ]),
    );
  });

  it("shows the allocation receipt and the citizen's reason for a returned round", async () => {
    signInAs("department");
    installFakeApi(routes());
    await renderWorkspace(<CaseTracker description="Your cases." />);
    await waitFor(() =>
      expect(screen.getByText("Handpump not working")).toBeTruthy(),
    );
    fireEvent.click(screen.getAllByText("Open")[0]!);

    const receipt = screen.getByRole("region", { name: "Case YDG-WTR-0001" });
    expect(within(receipt).getByText("Allocation receipt")).toBeTruthy();
    expect(within(receipt).getByText("Ravi (Department)")).toBeTruthy();
    expect(within(receipt).getByText("Asha (Officer)")).toBeTruthy();
    expect(within(receipt).getByText(/not a payment/)).toBeTruthy();

    await waitFor(() =>
      expect(screen.getByText("Still no water in the evening.")).toBeTruthy(),
    );
    expect(screen.getByText("Why the citizen returned round 1")).toBeTruthy();
  });

  it("explains that an unfunded case is waiting for the department", async () => {
    signInAs("department");
    const api = installFakeApi(routes());
    await renderWorkspace(<CaseTracker description="Your cases." />);
    await waitFor(() => expect(screen.getByText("Pipeline leak")).toBeTruthy());
    fireEvent.click(screen.getAllByText("Open")[1]!);
    expect(
      screen.getByText(/waiting for the responsible department/),
    ).toBeTruthy();
    // No work order yet, so no evidence request.
    expect(api.calls.some((c) => c.path.includes("evidence"))).toBe(false);
  });
});
