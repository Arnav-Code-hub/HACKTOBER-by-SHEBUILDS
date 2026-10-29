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
  "GET cases": () => ({ items: [] }),
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
          {
            id: "dep1",
            type: "department",
            name: "Rural Water Supply",
            parent_id: "d1",
          },
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
      organization_id: null,
      reason: "Promoted to department lead.",
    });
  });

  it("sends the selected industry organization when assigning a CSR role", async () => {
    signInAs("super_admin");
    const user = {
      id: "u9",
      display_name: "Partner",
      email: "partner@example.test",
      role: "citizen",
      district_id: "d1",
      department_id: null,
      institute_id: null,
      organization_id: null,
    };
    const api = installFakeApi({
      ...oversight,
      "GET admin/users": () => ({ items: [user] }),
      "GET organizations": () => ({
        items: [
          { id: "d1", type: "district", name: "Yadgir" },
          {
            id: "csr1",
            type: "industry",
            name: "Demo sponsor",
            parent_id: "d1",
          },
        ],
      }),
      "PATCH admin/users/u9": () => ({
        ...user,
        role: "industry",
        organization_id: "csr1",
      }),
    });
    await renderWorkspace(<AdminWorkspace />);
    await waitFor(() => expect(screen.getByText("Partner")).toBeTruthy());
    fireEvent.click(screen.getByText("Open"));
    fireEvent.change(screen.getByLabelText(/^Role/), {
      target: { value: "industry" },
    });
    fireEvent.change(screen.getByLabelText(/Industry organization/), {
      target: { value: "csr1" },
    });
    fireEvent.change(screen.getByLabelText(/Reason for the change/), {
      target: { value: "CSR demo" },
    });
    fireEvent.click(screen.getByText("Apply change"));
    await act(async () => fireEvent.click(screen.getByText("Confirm")));
    expect(api.to("PATCH", "admin/users/u9")[0]!.body).toEqual({
      role: "industry",
      district_id: "d1",
      department_id: null,
      institute_id: null,
      organization_id: "csr1",
      reason: "CSR demo",
    });
  });

  it("refuses to change the signed-in super admin's own role or scope", async () => {
    signInAs("super_admin");
    const api = installFakeApi({
      ...oversight,
      "GET admin/users": () => ({
        items: [
          {
            id: "staff-1",
            display_name: "Me",
            email: null,
            role: "super_admin",
            district_id: null,
            department_id: null,
            institute_id: null,
          },
        ],
      }),
      "GET organizations": () => ({ items: [] }),
    });
    await renderWorkspace(<AdminWorkspace />);
    await waitFor(() => expect(screen.getByText("(you)")).toBeTruthy());
    fireEvent.click(screen.getByText("Open"));
    expect(
      screen.getByText(/cannot change your own role or scope/),
    ).toBeTruthy();
    expect(screen.queryByText("Apply change")).toBeNull();
    expect(api.to("PATCH", "admin/users/staff-1")).toHaveLength(0);
  });

  it("pages back through older audit events and shows what changed", async () => {
    signInAs("gov_admin");
    const event = (id: string, at: string, extra = {}) => ({
      id,
      at,
      actor_name: "Asha",
      actor_role: "department",
      action: "cluster.funded",
      entity_type: "cluster",
      entity_id: "c1",
      reason: null,
      ...extra,
    });
    const api = installFakeApi({
      ...oversight,
      "GET admin/audit": (call) =>
        call.url.searchParams.get("before_id") === "e1"
          ? { items: [event("e0", "2026-10-20T10:00:00Z")], next: null }
          : {
              items: [
                event("e1", "2026-10-25T10:00:00Z", {
                  action: "cluster.inputs_updated",
                  before: { infrastructure_gap: 40 },
                  after: { infrastructure_gap: 70 },
                }),
              ],
              next: { before_at: "2026-10-25T10:00:00Z", before_id: "e1" },
            },
    });
    await renderWorkspace(<AdminWorkspace />);
    await waitFor(() =>
      expect(screen.getByText("cluster.inputs_updated")).toBeTruthy(),
    );
    expect(screen.getByText("infrastructure gap")).toBeTruthy();
    expect(screen.getByText("40")).toBeTruthy();
    expect(screen.getByText("70")).toBeTruthy();

    await act(async () =>
      fireEvent.click(screen.getByText("Load older events")),
    );
    await waitFor(() =>
      expect(screen.getByText("cluster.funded")).toBeTruthy(),
    );
    const older = api
      .to("GET", "admin/audit")
      .find((c) => c.url.searchParams.get("before_id") === "e1");
    expect(older?.url.searchParams.get("before_at")).toBe(
      "2026-10-25T10:00:00Z",
    );
    expect(
      screen.getByText("You have reached the first recorded event."),
    ).toBeTruthy();
  });

  it("offers only the chosen district's organizations and previews the access change", async () => {
    signInAs("super_admin");
    const user = {
      id: "u5",
      display_name: "Meera",
      email: "meera@example.test",
      role: "citizen",
      district_id: "d1",
      department_id: null,
      institute_id: null,
      organization_id: null,
    };
    const api = installFakeApi({
      ...oversight,
      "GET admin/users": () => ({ items: [user] }),
      "GET organizations": () => ({
        items: [
          { id: "d1", type: "district", name: "Yadgir" },
          { id: "d2", type: "district", name: "Raichur" },
          {
            id: "w1",
            type: "department",
            name: "Water (Yadgir)",
            parent_id: "d1",
          },
          {
            id: "w2",
            type: "department",
            name: "Water (Raichur)",
            parent_id: "d2",
          },
        ],
      }),
      "PATCH admin/users/u5": () => ({ ...user, role: "officer" }),
    });
    await renderWorkspace(<AdminWorkspace />);
    await waitFor(() => expect(screen.getByText("Meera")).toBeTruthy());
    fireEvent.click(screen.getByText("Open"));

    const department = screen.getByLabelText(/^Department/);
    const offered = () =>
      [...department.querySelectorAll("option")].map((o) => o.textContent);
    expect(offered()).toEqual(["Choose…", "Water (Yadgir)"]);

    fireEvent.change(screen.getByLabelText(/^Role/), {
      target: { value: "officer" },
    });
    fireEvent.change(screen.getByLabelText(/Reason for the change/), {
      target: { value: "New field officer" },
    });
    // An officer without a department would be refused; nothing is sent.
    fireEvent.click(screen.getByText("Apply change"));
    expect(screen.getByRole("alert").textContent).toMatch(
      /Officer accounts need a department/,
    );
    expect(api.to("PATCH", "admin/users/u5")).toHaveLength(0);

    fireEvent.change(department, { target: { value: "w1" } });
    // Moving district clears a department that belongs to the old one.
    fireEvent.change(screen.getByLabelText(/^District/), {
      target: { value: "d2" },
    });
    expect((department as HTMLSelectElement).value).toBe("");
    expect(offered()).toEqual(["Choose…", "Water (Raichur)"]);
    fireEvent.change(department, { target: { value: "w2" } });

    fireEvent.click(screen.getByText("Apply change"));
    const preview = screen.getByRole("alertdialog").textContent ?? "";
    expect(preview).toMatch(/Role: Citizen → Officer/);
    expect(preview).toMatch(/District: Yadgir → Raichur/);
    expect(preview).toMatch(/Department: — → Water \(Raichur\)/);
    await act(async () => fireEvent.click(screen.getByText("Confirm")));
    expect(api.to("PATCH", "admin/users/u5")[0]!.body).toMatchObject({
      role: "officer",
      district_id: "d2",
      department_id: "w2",
    });
  });
});
