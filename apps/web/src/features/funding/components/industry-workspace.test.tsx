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

import { IndustryWorkspace } from "./industry-workspace";

afterEach(() => vi.unstubAllGlobals());

describe("Industry / CSR workspace", () => {
  it("records a pledge in paise, clearly not a payment", async () => {
    signInAs("industry");
    const api = installFakeApi({
      "GET statements": () => ({ items: [statement()] }),
      "GET sponsorships": () => ({ items: [] }),
      "POST statements/s1/sponsorships": () => ({
        id: "p1",
        statement_id: "s1",
        statement_title: "Low-cost handpump maintenance alerts",
        amount_paise: 2_500_000,
        status: "pledged",
        pledged_at: "2026-10-25T10:00:00Z",
      }),
    });
    await renderWorkspace(<IndustryWorkspace />);
    await waitFor(() => expect(screen.getByText("Open")).toBeTruthy());
    expect(api.to("GET", "statements")[0]!.url.searchParams.get("status")).toBe(
      "published",
    );
    fireEvent.click(screen.getByText("Open"));

    fireEvent.change(screen.getByLabelText(/Pledge amount/), {
      target: { value: "25,000" },
    });
    fireEvent.click(screen.getByText("Record pledge"));
    expect(screen.getByText(/₹25,000.00.*no payment is taken/)).toBeTruthy();
    await act(async () => fireEvent.click(screen.getByText("Confirm")));

    const [pledge] = api.to("POST", "statements/s1/sponsorships");
    expect(pledge!.body).toEqual({ amount_paise: 2_500_000 });
    expect(pledge!.headers["Idempotency-Key"]).toBeTruthy();
    await waitFor(() => expect(api.to("GET", "sponsorships").length).toBe(2));
  });
});
