import { fireEvent, screen, waitFor } from "@testing-library/react";
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

import {
  FacultyCouncil,
  StudentCouncil,
  SupervisorPanel,
} from "./council-panels";

afterEach(() => vi.unstubAllGlobals());

const submission = {
  id: "s1",
  team_id: "t1",
  team_name: "Team",
  statement_title: "Statement",
  title: "Study",
  summary: "Findings",
  link: null,
  submitted_at: "2026-10-30T00:00:00Z",
  review_count: 0,
  my_review: null,
};
const row = {
  id: "a1",
  submission_id: "s1",
  title: "Study",
  status: "incomplete",
  completed_reviewers: 2,
  created_at: "2026-10-30T00:00:00Z",
  error: "Reviewer failed.",
  supervisor_name: "Dr Singh",
};

describe("Council integration", () => {
  it("keeps the integration hidden when disabled", async () => {
    signInAs("student");
    const api = installFakeApi({
      "GET council/config": () => ({ enabled: false }),
    });
    await renderWorkspace(<StudentCouncil submissions={[submission]} />);
    await waitFor(() =>
      expect(api.to("GET", "council/config")).toHaveLength(1),
    );
    expect(screen.queryByText("AI Council")).toBeNull();
    expect(api.to("GET", "council/assessments")).toHaveLength(0);
  });

  it("assigns only a server-offered supervisor", async () => {
    signInAs("institute");
    const api = installFakeApi({
      "GET council/config": () => ({ enabled: true }),
      "GET council/faculty": () => ({
        items: [{ id: "f1", display_name: "Dr Singh" }],
      }),
      "GET council/teams/t1/supervisor": () => ({
        faculty_id: null,
        display_name: null,
      }),
      "POST council/teams/t1/supervisor": () => ({
        faculty_id: "f1",
        display_name: "Dr Singh",
      }),
    });
    await renderWorkspace(<SupervisorPanel teamId="t1" />);
    await screen.findByRole("option", { name: "Dr Singh" });
    fireEvent.change(screen.getByLabelText(/^Supervising faculty/), {
      target: { value: "f1" },
    });
    fireEvent.click(screen.getByText("Assign supervisor"));
    await waitFor(() =>
      expect(api.to("POST", "council/teams/t1/supervisor")).toHaveLength(1),
    );
    expect(api.to("POST", "council/teams/t1/supervisor")[0]!.body).toEqual({
      faculty_id: "f1",
    });
  });

  it("submits structured evidence and shows faculty sharing", async () => {
    signInAs("student");
    const api = installFakeApi({
      "GET council/config": () => ({ enabled: true }),
      "GET council/assessments": () => ({ items: [] }),
      "POST council/submissions/s1/assessments": () => ({
        ...row,
        status: "queued",
        error: null,
      }),
    });
    await renderWorkspace(<StudentCouncil submissions={[submission]} />);
    await screen.findByText("Request an AI Council critique");
    fireEvent.change(screen.getByLabelText(/^Student submission/), {
      target: { value: "s1" },
    });
    fireEvent.change(screen.getByLabelText(/^Research question/), {
      target: { value: "Does it work?" },
    });
    fireEvent.change(screen.getByLabelText(/^Student findings/), {
      target: { value: "Five users reported benefit." },
    });
    fireEvent.click(screen.getByText("Request council report"));
    await waitFor(() =>
      expect(api.to("POST", "council/submissions/s1/assessments")).toHaveLength(
        1,
      ),
    );
    const call = api.to("POST", "council/submissions/s1/assessments")[0]!;
    expect(call.body).toEqual({
      title: "Study",
      research_question: "Does it work?",
      findings: "Five users reported benefit.",
      methods: "",
      results: "",
      limitations: "",
      files: [],
    });
    expect(call.headers["Idempotency-Key"]).toBeTruthy();
    expect(
      screen.getByText(
        /automatically shared with your assigned supervising faculty/,
      ),
    ).toBeTruthy();
  });

  it("shows incomplete reports without a PDF and retries explicitly", async () => {
    signInAs("student");
    const api = installFakeApi({
      "GET council/config": () => ({ enabled: true }),
      "GET council/assessments": () => ({ items: [row] }),
      "POST council/assessments/a1/retry": () => ({ ...row, status: "queued" }),
    });
    await renderWorkspace(<StudentCouncil submissions={[]} />);
    await screen.findByText("Reviewer failed.");
    expect(screen.queryByText("Download PDF")).toBeNull();
    fireEvent.click(screen.getByText("Retry incomplete assessment"));
    await waitFor(() =>
      expect(api.to("POST", "council/assessments/a1/retry")).toHaveLength(1),
    );
  });

  it("surfaces a failed PDF download", async () => {
    signInAs("faculty");
    installFakeApi({
      "GET council/config": () => ({ enabled: true }),
      "GET council/assessments": () => ({
        items: [{ ...row, status: "available", error: null }],
      }),
      "GET council/assessments/a1/pdf": () =>
        new Response(
          JSON.stringify({ detail: "Report artifact unavailable." }),
          { status: 503 },
        ),
    });
    await renderWorkspace(<FacultyCouncil />);
    fireEvent.click(await screen.findByText("Download PDF"));
    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toMatch(
        /artifact unavailable/,
      ),
    );
  });

  it("does not let faculty trigger another billed assessment", async () => {
    signInAs("faculty");
    installFakeApi({
      "GET council/config": () => ({ enabled: true }),
      "GET council/assessments": () => ({ items: [row] }),
    });
    await renderWorkspace(<FacultyCouncil />);
    await screen.findByText("Reviewer failed.");
    expect(screen.queryByText("Retry incomplete assessment")).toBeNull();
    expect(
      screen.getByText("The student team can retry this assessment."),
    ).toBeTruthy();
  });

  it("lets faculty resolve PDF citations against the immutable evidence snapshot", async () => {
    signInAs("faculty");
    const api = installFakeApi({
      "GET council/config": () => ({ enabled: true }),
      "GET council/assessments": () => ({ items: [row] }),
      "GET council/assessments/a1": () => ({
        ...row,
        report: null,
        evidence: {
          title: "Study",
          research_question: "Does it work?",
          findings: "No baseline was measured.",
          methods: "",
          results: "",
          limitations: "",
          files: [
            { name: "study.py", content: "print('first')\nprint('second')\n" },
          ],
        },
      }),
    });
    await renderWorkspace(<FacultyCouncil />);
    fireEvent.click(await screen.findByText("Inspect evidence"));
    await screen.findByText("E01 / Research question");
    expect(screen.getByText("L1: Does it work?")).toBeTruthy();
    fireEvent.click(screen.getByText("E06 / study.py"));
    expect(screen.getByText(/L2: print\('second'\)/)).toBeTruthy();
    expect(screen.getByText(/L2: print\('second'\)/).textContent).not.toContain(
      "L3:",
    );
    expect(api.to("GET", "council/assessments/a1")).toHaveLength(1);
  });
});
