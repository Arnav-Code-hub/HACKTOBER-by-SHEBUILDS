import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/use-api", () => ({
  useApi: () => ({ request: vi.fn() }),
}));
vi.mock("@/lib/api/media", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/media")>()),
  sendToCloudinary: vi.fn(),
  completeUpload: vi.fn(),
}));

import { ActionForm } from "@/components/workspace/action-form";
import { EvidenceView } from "@/components/workspace/evidence-view";
import { PhotoUploader } from "@/components/workspace/photo-uploader";
import { RecordList } from "@/components/workspace/record-list";
import { ScoreBreakdown } from "@/components/workspace/score-breakdown";
import { STATUS_DISPLAY } from "@/components/workspace/status-badge";
import { ApiError } from "@/lib/api/client";
import { completeUpload, sendToCloudinary } from "@/lib/api/media";
import { REPORT_STATUSES } from "@/lib/api/schemas";

type Row = { id: string; title: string };
const columns = [{ header: "Title", cell: (row: Row) => row.title }];

describe("RecordList", () => {
  it("shows loading, error with retry, empty, and rows", () => {
    const retry = vi.fn();
    const base = {
      title: "Queue",
      columns,
      emptyMessage: "No reports are waiting.",
      rowKey: (row: Row) => row.id,
    };
    const { rerender } = render(
      <RecordList {...base} rows={undefined} isLoading />,
    );
    expect(screen.getByRole("status").textContent).toMatch(/Loading/);

    rerender(
      <RecordList
        {...base}
        rows={undefined}
        isLoading={false}
        error={new ApiError("Outside your scope.", 404)}
        onRefresh={retry}
      />,
    );
    expect(screen.getByRole("alert").textContent).toMatch(/Outside your scope/);
    fireEvent.click(screen.getByText("Retry"));
    expect(retry).toHaveBeenCalled();

    rerender(<RecordList {...base} rows={[]} isLoading={false} />);
    expect(screen.getByText("No reports are waiting.")).toBeTruthy();

    const select = vi.fn();
    rerender(
      <RecordList
        {...base}
        rows={[{ id: "r1", title: "Broken handpump" }]}
        isLoading={false}
        onSelect={select}
      />,
    );
    fireEvent.click(screen.getByText("Open"));
    expect(select).toHaveBeenCalledWith({ id: "r1", title: "Broken handpump" });
  });
});

describe("RecordList refresh", () => {
  const base = {
    title: "Queue",
    columns,
    emptyMessage: "No reports are waiting.",
    rowKey: (row: Row) => row.id,
  };

  it("offers Refresh for empty and populated lists, not while loading", () => {
    const refresh = vi.fn();
    const { rerender } = render(
      <RecordList {...base} rows={undefined} isLoading onRefresh={refresh} />,
    );
    expect(screen.queryByText("Refresh")).toBeNull();

    rerender(
      <RecordList {...base} rows={[]} isLoading={false} onRefresh={refresh} />,
    );
    fireEvent.click(screen.getByText("Refresh"));
    expect(refresh).toHaveBeenCalledTimes(1);

    rerender(
      <RecordList
        {...base}
        rows={[{ id: "r1", title: "Broken handpump" }]}
        isLoading={false}
        onRefresh={refresh}
        isRefreshing
      />,
    );
    const button = screen.getByText("Refreshing…") as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it("keeps loaded rows when a background refresh fails", () => {
    render(
      <RecordList
        {...base}
        rows={[{ id: "r1", title: "Broken handpump" }]}
        isLoading={false}
        error={new ApiError("The service is unavailable.", 503)}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByText("Broken handpump")).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toMatch(
      /Could not refresh.*last loaded list/,
    );
  });
});

describe("ActionForm", () => {
  const fields = [
    {
      name: "amount_paise",
      label: "Amount",
      kind: "money" as const,
      required: true,
    },
    { name: "notes", label: "Notes", kind: "textarea" as const },
  ];

  it("identifies every invalid field and focuses a linked error summary", () => {
    const submit = vi.fn();
    render(
      <ActionForm
        title="Fund"
        fields={[
          ...fields,
          { name: "officer", label: "Officer", kind: "select", required: true },
        ]}
        submitLabel="Save"
        onSubmit={submit}
      />,
    );
    fireEvent.click(screen.getByText("Save"));
    const summary = screen.getByRole("alert");
    expect(document.activeElement).toBe(summary);
    for (const label of ["Amount", "Officer"]) {
      const field = screen.getByLabelText(new RegExp(label));
      expect(field.getAttribute("aria-invalid")).toBe("true");
      const errorId = field.getAttribute("aria-describedby")!;
      expect(document.getElementById(errorId)?.textContent).toBe(
        `${label} is required.`,
      );
      const link = screen.getByRole("link", { name: `${label} is required.` });
      expect(link.getAttribute("href")).toBe(`#${field.id}`);
      fireEvent.click(link);
      expect(document.activeElement).toBe(field);
    }
    expect(submit).not.toHaveBeenCalled();
  });

  it("moves focus into confirmation and returns it on cancel without losing input", () => {
    render(
      <ActionForm
        title="Fund"
        fields={fields}
        submitLabel="Save"
        confirm={() => "Allocate this amount?"}
        onSubmit={vi.fn()}
      />,
    );
    const amount = screen.getByLabelText(/Amount/);
    fireEvent.change(amount, { target: { value: "12" } });
    fireEvent.click(screen.getByText("Save"));
    expect(document.activeElement).toBe(screen.getByText("Confirm"));
    fireEvent.click(screen.getByText("Cancel"));
    expect(document.activeElement).toBe(screen.getByText("Save"));
    expect((amount as HTMLInputElement).value).toBe("12");
  });

  it("converts rupees to paise and confirms before a consequential write", async () => {
    const submit = vi.fn().mockResolvedValue("Allocation recorded.");
    render(
      <ActionForm
        title="Fund"
        fields={fields}
        submitLabel="Record allocation"
        confirm={() => "Allocate this amount?"}
        onSubmit={submit}
      />,
    );
    fireEvent.change(screen.getByLabelText(/Amount/), {
      target: { value: "1,500.50" },
    });
    fireEvent.click(screen.getByText("Record allocation"));
    expect(screen.getByText("Allocate this amount?")).toBeTruthy();
    expect(submit).not.toHaveBeenCalled();

    await act(async () => {
      fireEvent.click(screen.getByText("Confirm"));
    });
    expect(submit).toHaveBeenCalledWith(
      { amount_paise: 150050 },
      { idempotencyKey: expect.any(String) },
    );
    expect(screen.getByRole("status").textContent).toBe("Allocation recorded.");
  });

  it("reuses the idempotency key for an unchanged retry, not after an edit", async () => {
    const submit = vi
      .fn()
      .mockRejectedValueOnce(new ApiError("The request timed out.", null))
      .mockRejectedValueOnce(new ApiError("The request timed out.", null))
      .mockResolvedValue(undefined);
    render(
      <ActionForm
        title="Fund"
        fields={fields}
        submitLabel="Save"
        onSubmit={submit}
      />,
    );
    const amount = screen.getByLabelText(/Amount/);
    fireEvent.change(amount, { target: { value: "10" } });

    await act(async () => fireEvent.click(screen.getByText("Save")));
    expect(screen.getByRole("alert").textContent).toMatch(/timed out/);
    expect((amount as HTMLInputElement).value).toBe("10");
    await act(async () => fireEvent.click(screen.getByText("Save")));

    fireEvent.change(amount, { target: { value: "11" } });
    await act(async () => fireEvent.click(screen.getByText("Save")));

    const keys = submit.mock.calls.map((call) => call[1].idempotencyKey);
    expect(keys[0]).toBe(keys[1]);
    expect(keys[2]).not.toBe(keys[1]);
  });

  it("validates required and money fields before calling the API", async () => {
    const submit = vi.fn();
    render(
      <ActionForm
        title="Fund"
        fields={fields}
        submitLabel="Save"
        onSubmit={submit}
      />,
    );
    fireEvent.click(screen.getByText("Save"));
    expect(screen.getByRole("alert").textContent).toMatch(/Amount is required/);
    fireEvent.change(screen.getByLabelText(/Amount/), {
      target: { value: "12.345" },
    });
    fireEvent.click(screen.getByText("Save"));
    expect(screen.getByRole("alert").textContent).toMatch(/at most 2 decimals/);
    expect(submit).not.toHaveBeenCalled();
  });
});

describe("status and evidence display", () => {
  it("says so when the citizen attached no photo, instead of a stand-in", () => {
    render(
      <EvidenceView
        evidence={{
          report_code: "JM-7",
          status: "in_progress",
          before: null,
          after: null,
          card_url: null,
        }}
      />,
    );
    expect(screen.getByText(/did not attach a photo/)).toBeTruthy();
    expect(document.querySelector("img")).toBeNull();
  });

  it("labels every agreed status, with verified as Panchayat validation", () => {
    for (const status of REPORT_STATUSES)
      expect(STATUS_DISPLAY[status]).toBeTruthy();
    expect(STATUS_DISPLAY.verified.label).toBe("Panchayat Validated");
    expect(STATUS_DISPLAY.citizen_verified.label).toBe("Citizen Verified");
  });

  it("shows before/after with the human-review caveat and the card", () => {
    render(
      <EvidenceView
        evidence={{
          report_code: "YDG-WTR-0001",
          status: "awaiting_verification",
          before: {
            url: "https://res.cloudinary.com/d/before.jpg",
            uploaded_at: "2026-10-20T10:00:00Z",
          },
          after: {
            url: "https://res.cloudinary.com/d/after.jpg",
            uploaded_at: "2026-10-24T10:00:00Z",
          },
          card_url: "https://res.cloudinary.com/d/card.jpg",
        }}
      />,
    );
    expect(screen.getByText("Awaiting Citizen Verification")).toBeTruthy();
    expect(screen.getByText(/not proof that a repair/)).toBeTruthy();
    expect(screen.getByAltText("Evidence card for YDG-WTR-0001")).toBeTruthy();
  });

  it("labels demonstration ranking inputs", () => {
    render(
      <ScoreBreakdown
        factors={[
          {
            factor: "support",
            label: "Community support",
            score: 80,
            weight: 0.3,
            is_demo: false,
          },
          {
            factor: "equity",
            label: "Equity",
            score: 50,
            weight: 0.2,
            is_demo: true,
          },
        ]}
      />,
    );
    expect(screen.getAllByText("Demo value")).toHaveLength(1);
    expect(screen.getByText("34.0")).toBeTruthy();
  });
});

describe("PhotoUploader", () => {
  const PNG = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 0]);
  const file = (name: string) => new File([PNG], name, { type: "image/png" });
  const pendingFor = (id: string) => ({
    upload_id: `intent-${id}`,
    public_id: id,
    version: 1,
    signature: "s",
  });
  const media = (id: string) => ({
    id,
    url: `https://res.cloudinary.com/d/${id}.png`,
  });

  beforeEach(() => {
    vi.mocked(sendToCloudinary).mockReset();
    vi.mocked(completeUpload).mockReset();
  });

  it("reports only verified media; a failed completion retries without re-uploading", async () => {
    vi.mocked(sendToCloudinary).mockImplementation(async (_api, f) =>
      pendingFor(f.name),
    );
    vi.mocked(completeUpload)
      .mockResolvedValueOnce(media("a.png"))
      .mockRejectedValueOnce(new ApiError("The service is unavailable.", 503))
      .mockResolvedValueOnce(media("b.png"));
    const changes = vi.fn();
    render(<PhotoUploader kind="completion" onChange={changes} />);

    fireEvent.change(screen.getByLabelText(/Photos/), {
      target: { files: [file("a.png"), file("b.png")] },
    });
    await waitFor(() =>
      expect(screen.getByText(/service is unavailable/)).toBeTruthy(),
    );
    expect(changes).toHaveBeenLastCalledWith([
      expect.objectContaining({ id: "a.png" }),
    ]);

    fireEvent.click(screen.getByText("Retry"));
    await waitFor(() =>
      expect(changes).toHaveBeenLastCalledWith([
        expect.objectContaining({ id: "a.png" }),
        expect.objectContaining({ id: "b.png" }),
      ]),
    );
    // Two photos, two transfers: the retry resumed at completion.
    expect(sendToCloudinary).toHaveBeenCalledTimes(2);
    expect(vi.mocked(completeUpload).mock.calls[2]![1]).toEqual(
      pendingFor("b.png"),
    );
  });

  it("lets a stalled upload be cancelled, then retried or removed", async () => {
    vi.mocked(sendToCloudinary).mockImplementation(
      (_api, _file, _kind, options) =>
        new Promise((_resolve, reject) =>
          options?.signal?.addEventListener("abort", () =>
            reject(new DOMException("aborted", "AbortError")),
          ),
        ),
    );
    const pendingCounts: number[] = [];
    render(
      <PhotoUploader
        kind="completion"
        onChange={vi.fn()}
        onPendingChange={(count) => pendingCounts.push(count)}
      />,
    );
    fireEvent.change(screen.getByLabelText(/Photos/), {
      target: { files: [file("slow.png")] },
    });
    expect(screen.getByText("Uploading…")).toBeTruthy();
    expect(pendingCounts.at(-1)).toBe(1);

    await act(async () => fireEvent.click(screen.getByText("Cancel")));
    expect(screen.getByText(/Upload cancelled/)).toBeTruthy();
    expect(screen.getByText("Retry")).toBeTruthy();
    expect(pendingCounts.at(-1)).toBe(0);

    fireEvent.click(screen.getByText("Remove"));
    expect(screen.queryByText("slow.png")).toBeNull();
  });

  it("refuses more than three photos in total", () => {
    render(<PhotoUploader kind="report" onChange={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(/Photos/), {
      target: {
        files: [file("1.png"), file("2.png"), file("3.png"), file("4.png")],
      },
    });
    expect(screen.getByRole("alert").textContent).toMatch(/no more than 3/);
  });
});
