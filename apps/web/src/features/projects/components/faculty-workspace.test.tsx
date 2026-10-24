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

import { FacultyWorkspace } from "./faculty-workspace";

afterEach(() => vi.unstubAllGlobals());

function submission(overrides: Record<string, unknown> = {}) {
  return {
    id: "sub1",
    team_id: "t1",
    team_name: "Pump Watch",
    statement_title: "Low-cost handpump maintenance alerts",
    title: "SMS alerts",
    summary: "Missed-call alerts to the Panchayat.",
    link: "https://example.org/repo",
    submitted_at: "2026-10-25T10:00:00Z",
    review_count: 0,
    my_review: null,
    ...overrides,
  };
}

describe("Faculty workspace", () => {
  it("reviews an institute submission once, with a score and feedback", async () => {
    signInAs("faculty");
    const api = installFakeApi({
      "GET submissions": () => ({ items: [submission()] }),
      "POST submissions/sub1/reviews": () => ({ id: "rev1" }),
    });
    await renderWorkspace(<FacultyWorkspace />);
    await waitFor(() => expect(screen.getByText("Open")).toBeTruthy());
    expect(
      api.to("GET", "submissions")[0]!.url.searchParams.get("institute"),
    ).toBe("me");
    fireEvent.click(screen.getByText("Open"));

    fireEvent.change(screen.getByLabelText(/^Score/), {
      target: { value: "4" },
    });
    fireEvent.change(screen.getByLabelText(/Feedback for the team/), {
      target: { value: "Pilot it in one ward first." },
    });
    fireEvent.click(screen.getByText("Submit review"));
    await act(async () => fireEvent.click(screen.getByText("Confirm")));
    expect(api.to("POST", "submissions/sub1/reviews")[0]!.body).toEqual({
      score: 4,
      comment: "Pilot it in one ward first.",
    });
  });

  it("shows an existing review instead of a second form", async () => {
    signInAs("faculty");
    installFakeApi({
      "GET submissions": () => ({
        items: [submission({ my_review: { score: 5, comment: "Excellent." } })],
      }),
    });
    await renderWorkspace(<FacultyWorkspace />);
    await waitFor(() => expect(screen.getByText("Open")).toBeTruthy());
    fireEvent.click(screen.getByText("Open"));
    expect(screen.getByText("Excellent.")).toBeTruthy();
    expect(screen.queryByText("Submit review")).toBeNull();
  });

  it("never renders a script link from a submission", async () => {
    signInAs("faculty");
    installFakeApi({
      "GET submissions": () => ({
        items: [submission({ link: "javascript:alert(document.cookie)" })],
      }),
    });
    await renderWorkspace(<FacultyWorkspace />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
    expect(screen.getByRole("alert").textContent).toMatch(/expected format/);
    expect(document.querySelector('a[href^="javascript:"]')).toBeNull();
  });
});
