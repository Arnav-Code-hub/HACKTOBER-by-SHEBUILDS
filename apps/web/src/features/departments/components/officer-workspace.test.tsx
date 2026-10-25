import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  harnessConfigModule,
  harnessSessionModule,
  installFakeApi,
  media,
  renderWorkspace,
} from "@/test/api-harness";

vi.mock("@/lib/auth/session", () => harnessSessionModule);
vi.mock("@/lib/config", () => harnessConfigModule);

import { OfficerWorkspace } from "./officer-workspace";

afterEach(() => vi.unstubAllGlobals());

const CLOUDINARY = "https://api.cloudinary.com/v1_1/demo/image/upload";
const PNG = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 0]);

function order(overrides: Record<string, unknown> = {}) {
  return {
    id: "w1",
    cluster_id: "c1",
    report_code: "YDG-WTR-0001",
    title: "Handpump not working",
    status: "in_progress",
    round: 1,
    location_label: "Ward 4",
    instructions: "Replace the cylinder.",
    notes: null,
    allocated_paise: 15_000_000,
    assigned_at: "2026-10-22T09:00:00Z",
    ...overrides,
  };
}

/** An open order: the citizen's photo, nothing completed yet. */
const openEvidence = {
  report_code: "YDG-WTR-0001",
  status: "funded",
  before: { url: media("before").url, uploaded_at: "2026-10-20T08:00:00Z" },
  after: null,
  card_url: null,
};

/** Round 1's completion, returned by the citizen; round 2 is open. */
const evidence = {
  report_code: "YDG-WTR-0001",
  status: "in_progress",
  before: { url: media("before").url, uploaded_at: "2026-10-20T08:00:00Z" },
  after: { url: media("after").url, uploaded_at: "2026-10-24T08:00:00Z" },
  after_round: 1,
  card_url: null,
  verdict_label: "Round 1 · returned for correction",
};

async function openOrder() {
  await waitFor(() =>
    expect(screen.getAllByText("Open").length).toBeGreaterThan(0),
  );
  fireEvent.click(screen.getAllByText("Open")[0]!);
}

describe("Officer workspace", () => {
  it("submits completion only after the photos are verified", async () => {
    const api = installFakeApi({
      "GET work-orders": () => ({ items: [order()] }),
      "GET work-orders/w1/evidence": () => openEvidence,
      "POST media/signature": () => ({
        upload_id: "intent-1",
        upload_url: CLOUDINARY,
        parameters: { api_key: "public", timestamp: "1", signature: "sig" },
      }),
      [`POST ${CLOUDINARY}`]: () => ({
        public_id: "p1",
        version: 3,
        signature: "c",
      }),
      "POST media/complete": () => media("after"),
      "POST work-orders/w1/complete": () => ({
        id: "w1",
        status: "awaiting_verification",
      }),
    });
    await renderWorkspace(<OfficerWorkspace />);
    await openOrder();
    expect(screen.getByText("₹1,50,000.00")).toBeTruthy();

    const submit = () =>
      screen.getByText(/^Submit \d photo|Waiting for uploads/);
    expect((submit() as HTMLButtonElement).disabled).toBe(true);

    fireEvent.change(screen.getByLabelText(/Completion photos/), {
      target: { files: [new File([PNG], "after.png", { type: "image/png" })] },
    });
    await waitFor(() =>
      expect(screen.getByText("Uploaded and verified")).toBeTruthy(),
    );
    // The page learns of verified photos one render after the uploader shows them.
    await waitFor(() =>
      expect((submit() as HTMLButtonElement).disabled).toBe(false),
    );

    fireEvent.click(submit());
    expect(screen.getByText(/you cannot mark it fixed yourself/)).toBeTruthy();
    await act(async () => fireEvent.click(screen.getByText("Confirm")));

    const [complete] = api.to("POST", "work-orders/w1/complete");
    expect(complete!.body).toEqual({ media_ids: ["after"], expected_round: 1 });
    expect(complete!.headers["Idempotency-Key"]).toBeTruthy();
    // The Firebase token went to the API, never to Cloudinary.
    const [upload] = api.to("POST", CLOUDINARY);
    expect(upload!.headers).toEqual({});
  });

  it("records a progress note; a funded order offers no completion yet", async () => {
    const api = installFakeApi({
      "GET work-orders": () => ({ items: [order({ status: "funded" })] }),
      "GET work-orders/w1/evidence": () => openEvidence,
      "PATCH work-orders/w1": () => ({ id: "w1", status: "in_progress" }),
    });
    await renderWorkspace(<OfficerWorkspace />);
    await openOrder();
    expect(screen.queryByText("Completion evidence")).toBeNull();
    expect(
      screen.getByText(/first update marks the work as in progress/),
    ).toBeTruthy();

    fireEvent.change(screen.getByLabelText(/^Update/), {
      target: { value: "Materials ordered." },
    });
    await act(async () => fireEvent.click(screen.getByText("Save update")));
    expect(api.to("PATCH", "work-orders/w1")[0]!.body).toEqual({
      notes: "Materials ordered.",
    });
  });

  it("shows a returned order's round and the previous evidence", async () => {
    installFakeApi({
      "GET work-orders": () => ({ items: [order({ round: 2 })] }),
      "GET work-orders/w1/evidence": () => evidence,
    });
    await renderWorkspace(<OfficerWorkspace />);
    await openOrder();
    expect(screen.getByText(/correction round 2/)).toBeTruthy();
    await waitFor(() =>
      expect(
        screen.getByAltText("Completion evidence, YDG-WTR-0001"),
      ).toBeTruthy(),
    );
    expect(screen.getByText("Round 1 · returned by the citizen")).toBeTruthy();
  });

  it("captions the photo from the evidence, not a stale order list", async () => {
    // The list still shows round 1 awaiting verification; the evidence has
    // already moved on to the citizen's return.
    installFakeApi({
      "GET work-orders": () => ({
        items: [order({ status: "awaiting_verification" })],
      }),
      "GET work-orders/w1/evidence": () => evidence,
    });
    await renderWorkspace(<OfficerWorkspace />);
    await openOrder();
    await waitFor(() =>
      expect(
        screen.getByText("Round 1 · returned by the citizen"),
      ).toBeTruthy(),
    );
  });

  it("captions a submitted round's photo as the current result", async () => {
    installFakeApi({
      // A stale list may still say the work was returned.
      "GET work-orders": () => ({ items: [order({ round: 2 })] }),
      "GET work-orders/w1/evidence": () => ({
        ...evidence,
        status: "awaiting_verification",
        after_round: 2,
        verdict_label: "Awaiting citizen verification",
      }),
    });
    await renderWorkspace(<OfficerWorkspace />);
    await openOrder();
    await waitFor(() =>
      expect(
        screen.getByAltText("Completion evidence, YDG-WTR-0001"),
      ).toBeTruthy(),
    );
    expect(screen.queryByText(/returned by the citizen/)).toBeNull();
  });

  it("shows the citizen's photo before the first completion", async () => {
    const api = installFakeApi({
      "GET work-orders": () => ({ items: [order({ status: "funded" })] }),
      "GET work-orders/w1/evidence": () => openEvidence,
    });
    await renderWorkspace(<OfficerWorkspace />);
    await openOrder();
    await waitFor(() =>
      expect(
        screen.getByAltText("Reported problem, YDG-WTR-0001"),
      ).toBeTruthy(),
    );
    expect(
      screen.getByText("Completion evidence has not been uploaded yet."),
    ).toBeTruthy();
    expect(api.to("GET", "work-orders/w1/evidence")).toHaveLength(1);
  });

  it("offers Retry when the citizen's evidence cannot load", async () => {
    installFakeApi({
      "GET work-orders": () => ({ items: [order()] }),
      "GET work-orders/w1/evidence": () =>
        new Response("{}", { status: 503 }),
    });
    await renderWorkspace(<OfficerWorkspace />);
    await openOrder();
    await waitFor(
      () => expect(screen.getByText("Evidence unavailable")).toBeTruthy(),
      { timeout: 4000 },
    );
    expect(screen.getByText("Retry")).toBeTruthy();
  });
});
