import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  harnessConfigModule,
  harnessSessionModule,
  installFakeApi,
  renderWorkspace,
  signInAs,
  statement,
} from "@/test/api-harness";

vi.mock("@/lib/auth/session", () => harnessSessionModule);
vi.mock("@/lib/config", () => harnessConfigModule);

import { InstituteWorkspace } from "./institute-workspace";
import { StudentWorkspace, checkSolutionLink } from "./student-workspace";

afterEach(() => vi.unstubAllGlobals());

function team(overrides: Record<string, unknown> = {}) {
  return {
    id: "t1",
    name: "Pump Watch",
    statement_id: "s1",
    statement_title: "Low-cost handpump maintenance alerts",
    institute_approved: false,
    member_count: 3,
    created_at: "2026-10-23T10:00:00Z",
    ...overrides,
  };
}

const studentRoutes = (teams: unknown[]) => ({
  "GET statements": () => ({ items: [statement()] }),
  "GET teams": () => ({ items: teams }),
  "GET submissions": () => ({ items: [] }),
});

describe("Student workspace", () => {
  it("creates a team for a published statement", async () => {
    signInAs("student");
    const api = installFakeApi({
      ...studentRoutes([]),
      "POST teams": () => team(),
    });
    await renderWorkspace(<StudentWorkspace />);
    await waitFor(() =>
      expect(
        screen.getAllByText("Low-cost handpump maintenance alerts").length,
      ).toBeGreaterThan(1),
    );

    fireEvent.change(screen.getByLabelText(/Team name/), {
      target: { value: "Pump Watch" },
    });
    fireEvent.change(screen.getByLabelText(/Problem statement/), {
      target: { value: "s1" },
    });
    await act(async () => fireEvent.click(screen.getByText("Create team")));

    const [create] = api.to("POST", "teams");
    expect(create!.body).toEqual({ name: "Pump Watch", statement_id: "s1" });
    expect(create!.headers["Idempotency-Key"]).toBeTruthy();
    expect(screen.getByText(/Ask your institute to approve it/)).toBeTruthy();
  });

  it("only an approved team can submit, with an HTTPS link", async () => {
    signInAs("student");
    const api = installFakeApi({
      ...studentRoutes([team({ institute_approved: true })]),
      "POST submissions": () => ({
        id: "sub1",
        team_id: "t1",
        team_name: "Pump Watch",
        statement_title: "Low-cost handpump maintenance alerts",
        title: "SMS alerts",
        summary: "…",
        link: "https://example.org/repo",
        submitted_at: "2026-10-25T10:00:00Z",
        review_count: 0,
        my_review: null,
      }),
    });
    await renderWorkspace(<StudentWorkspace />);
    await waitFor(() => expect(screen.getByText("Open")).toBeTruthy());
    fireEvent.click(screen.getByText("Open"));

    fireEvent.change(screen.getByLabelText(/Solution title/), {
      target: { value: "SMS alerts" },
    });
    fireEvent.change(screen.getByLabelText(/What you propose/), {
      target: { value: "Missed-call alerts to the Panchayat." },
    });
    fireEvent.change(screen.getByLabelText(/Link to your work/), {
      target: { value: "http://example.org/repo" },
    });
    await act(async () => fireEvent.click(screen.getByText("Submit solution")));
    expect(screen.getByRole("alert").textContent).toMatch(/https:\/\//);
    expect(api.to("POST", "submissions")).toHaveLength(0);

    fireEvent.change(screen.getByLabelText(/Link to your work/), {
      target: { value: "https://example.org/repo" },
    });
    await act(async () => fireEvent.click(screen.getByText("Submit solution")));
    expect(api.to("POST", "submissions")[0]!.body).toEqual({
      team_id: "t1",
      title: "SMS alerts",
      summary: "Missed-call alerts to the Panchayat.",
      link: "https://example.org/repo",
    });
  });

  it("an unapproved team is told to wait instead of offered a form", async () => {
    signInAs("student");
    installFakeApi(studentRoutes([team()]));
    await renderWorkspace(<StudentWorkspace />);
    await waitFor(() => expect(screen.getByText("Open")).toBeTruthy());
    fireEvent.click(screen.getByText("Open"));
    expect(screen.getByText(/has not approved this team yet/)).toBeTruthy();
    expect(screen.queryByText("Submit solution")).toBeNull();
  });

  it("refuses script and non-HTTPS links", () => {
    for (const link of ["javascript:alert(1)", "ftp://x.org", "not a url"]) {
      expect(() => checkSolutionLink(link), link).toThrow(RangeError);
    }
    expect(checkSolutionLink("  ")).toBeUndefined();
  });
});

describe("Institute workspace", () => {
  it("approves a pending team after confirmation", async () => {
    signInAs("institute");
    const api = installFakeApi({
      "GET teams": () => ({ items: [team()] }),
      "POST teams/t1/approve": () => team({ institute_approved: true }),
    });
    await renderWorkspace(<InstituteWorkspace />);
    await waitFor(() => expect(screen.getByText("Open")).toBeTruthy());
    expect(api.to("GET", "teams")[0]!.url.searchParams.get("institute")).toBe(
      "me",
    );

    fireEvent.click(screen.getByText("Open"));
    fireEvent.click(screen.getByText("Approve team"));
    expect(api.to("POST", "teams/t1/approve")).toHaveLength(0);
    await act(async () => fireEvent.click(screen.getByText("Confirm")));
    expect(api.to("POST", "teams/t1/approve")).toHaveLength(1);
    expect(screen.getByText("Pump Watch is approved.")).toBeTruthy();
  });
});
