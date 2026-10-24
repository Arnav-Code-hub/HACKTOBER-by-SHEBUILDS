import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  harnessConfigModule,
  harnessSessionModule,
  installFakeApi,
  renderWorkspace,
  signInAs,
} from "@/test/api-harness";

vi.mock("@/lib/auth/session", () => harnessSessionModule);
vi.mock("@/lib/config", () => harnessConfigModule);

import { AdminWorkspace } from "./admin-workspace";

afterEach(() => vi.unstubAllGlobals());

const oversight = {
  "GET admin/summary": () => ({
    district_name: "Yadgir",
    reports_by_status: { reported: 4, verified: 2, citizen_verified: 1 },
    cluster_count: 3,
    work_orders_by_status: { in_progress: 1, awaiting_verification: 1 },
    allocated_paise: 15_000_000,
    pledged_paise: 2_500_000,
  }),
  "GET admin/audit": () => ({
    items: [
      {
        id: "e1",
        at: "2026-10-25T10:00:00Z",
        actor_name: "Asha",
        actor_role: "department",
        action: "cluster.funded",
        entity_type: "cluster",
        entity_id: "c1",
        reason: null,
      },
    ],
  }),
};

describe("Admin workspace", () => {
  it("shows a gov admin progress, recorded funding and the audit trail — no user admin", async () => {
    signInAs("gov_admin");
    const api = installFakeApi(oversight);
    await renderWorkspace(<AdminWorkspace />);

    await waitFor(() => expect(screen.getByText("Yadgir")).toBeTruthy());
    expect(screen.getByText("₹1,50,000.00")).toBeTruthy();
    expect(screen.getByText("Allocated (recorded)")).toBeTruthy();
    expect(screen.getByText("Panchayat Validated")).toBeTruthy();
    await waitFor(() =>
      expect(screen.getByText("cluster.funded")).toBeTruthy(),
    );

    expect(screen.queryByText("Users")).toBeNull();
    expect(api.to("GET", "admin/users")).toHaveLength(0);
  });

  it("lets a super admin change a role and scope, with a reason", async () => {
    signInAs("super_admin");
    const api = installFakeApi({
      ...oversight,
      "GET admin/users": () => ({
        items: [
          {
            id: "u7",
            display_name: "Ravi",
            email: "ravi@example.test",
            role: "officer",
            district_id: "d1",
            department_id: "dep1",
            institute_id: null,
          },
        ],
      }),
      "GET organizations": () => ({
        items: [
          { id: "d1", type: "district", name: "Yadgir" },
          { id: "dep1", type: "department", name: "Rural Water Supply" },
        ],
      }),
      "PATCH admin/users/u7": () => ({
        id: "u7",
        display_name: "Ravi",
        email: "ravi@example.test",
        role: "department",
        district_id: "d1",
        department_id: "dep1",
        institute_id: null,
      }),
    });
    await renderWorkspace(<AdminWorkspace />);
    await waitFor(() => expect(screen.getByText("Ravi")).toBeTruthy());
    fireEvent.click(screen.getByText("Open"));

    fireEvent.change(screen.getByLabelText(/^Role/), {
      target: { value: "department" },
    });
    fireEvent.click(screen.getByText("Apply change"));
    expect(screen.getByRole("alert").textContent).toMatch(
      /Reason for the change is required/,
    );

    fireEvent.change(screen.getByLabelText(/Reason for the change/), {
      target: { value: "Promoted to department lead." },
    });
    fireEvent.click(screen.getByText("Apply change"));
    expect(
      screen.getByText(/changes on their next request.*audited/),
    ).toBeTruthy();
    await act(async () => fireEvent.click(screen.getByText("Confirm")));

    expect(api.to("PATCH", "admin/users/u7")[0]!.body).toEqual({
      role: "department",
      district_id: "d1",
      department_id: "dep1",
      institute_id: null,
      reason: "Promoted to department lead.",
    });
  });
});
