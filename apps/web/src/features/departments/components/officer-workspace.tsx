"use client";

import { useState } from "react";

import { DetailList } from "@/components/workspace-panels";
import { PageHeading, countOf } from "@/components/workspace/page-heading";
import { ActionForm } from "@/components/workspace/action-form";
import { EvidenceView } from "@/components/workspace/evidence-view";
import { PhotoUploader } from "@/components/workspace/photo-uploader";
import { RecordList } from "@/components/workspace/record-list";
import { StatusBadge } from "@/components/workspace/status-badge";
import { useInvalidate } from "@/lib/api/hooks";
import type { Media } from "@/lib/api/schemas";
import { useApi } from "@/lib/api/use-api";
import { formatPaise } from "@/lib/money";

import { completeWorkOrder, updateWorkOrder, type WorkOrder } from "../api";
import { useMyWorkOrders, useWorkOrderEvidence } from "../hooks";

const date = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });

/**
 * Officer: update assigned work and submit completion evidence. Completion
 * hands the case to the original reporter; the officer cannot mark it fixed.
 */
export function OfficerWorkspace() {
  const invalidate = useInvalidate();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const orders = useMyWorkOrders();
  const order = orders.data?.items.find((o) => o.id === selectedId) ?? null;

  return (
    <>
      <PageHeading
        role="Officer"
        title="Your assigned work"
        steps={[
          "Open a work order to see the citizen's photo.",
          "Save progress notes as the work moves.",
          "Upload completion photos; the reporter decides.",
        ]}
        stats={[
          { label: "Assigned to you", value: countOf(orders.data?.items) },
          {
            label: "Work under way",
            value: countOf(orders.data?.items, (o) =>
              ["funded", "in_progress"].includes(o.status),
            ),
          },
          {
            label: "With the citizen",
            value: countOf(
              orders.data?.items,
              (o) => o.status === "awaiting_verification",
            ),
          },
          {
            label: "Confirmed fixed",
            value: countOf(
              orders.data?.items,
              (o) => o.status === "citizen_verified",
            ),
          },
        ]}
      >
        Record progress and upload completion photos. The citizen who reported
        the problem decides whether it was fixed.
      </PageHeading>

      <div className="jm-panel-grid">
        <RecordList
          title="Assigned work orders"
          columns={[
            {
              header: "Work order",
              cell: (o: WorkOrder) => (
                <>
                  <strong>{o.title}</strong>
                  <br />
                  <span className="jm-small">
                    {o.report_code}
                    {o.location_label ? ` · ${o.location_label}` : ""}
                  </span>
                </>
              ),
            },
            {
              header: "Status",
              cell: (o: WorkOrder) => <StatusBadge status={o.status} />,
            },
          ]}
          rows={orders.data?.items}
          isLoading={orders.isLoading}
          error={orders.error}
          onRefresh={() => void invalidate("work-orders")}
          isRefreshing={orders.isFetching}
          emptyMessage="No work orders are assigned to you."
          rowKey={(o) => o.id}
          onSelect={(o) => setSelectedId(o.id)}
          selectedKey={selectedId}
        />

        <div className="jm-stack">
          {order ? (
            <WorkOrderPanel key={`${order.id}-${order.round}`} order={order} />
          ) : (
            <section className="jm-panel">
              <h2>Select a work order</h2>
              <p className="jm-muted">
                Open an assigned work order to update it.
              </p>
            </section>
          )}
        </div>
      </div>
    </>
  );
}

function WorkOrderPanel({ order }: { order: WorkOrder }) {
  const api = useApi();
  const invalidate = useInvalidate();
  const [photos, setPhotos] = useState<Media[]>([]);
  const [uploading, setUploading] = useState(0);
  // Loaded for every order, open ones included: the officer needs the
  // citizen's photo before photographing the completed work.
  const evidence = useWorkOrderEvidence(order.id, true);
  const returned = order.round > 1 && order.status === "in_progress";
  // The caption describes the photo the evidence response chose, so it reads
  // that response: the order list loads separately and can be a refresh behind.
  const shown = evidence.data;
  const afterLabel =
    shown?.status === "in_progress" && shown.after_round
      ? `Round ${shown.after_round} · returned by the citizen`
      : "After";

  async function refresh() {
    await Promise.all([
      invalidate("work-orders"),
      invalidate("reports"),
      invalidate("clusters"),
    ]);
  }

  return (
    <>
      <section
        className="jm-panel"
        aria-label={`Work order ${order.report_code}`}
      >
        <div className="jm-evidence-heading">
          <h2>{order.title}</h2>
          <StatusBadge status={order.status} />
        </div>
        {returned && (
          <p className="jm-notice" role="status">
            The citizen reported this was not fixed. This is correction round{" "}
            {order.round}; upload new completion evidence when done.
          </p>
        )}
        <DetailList
          items={[
            { label: "Report", value: order.report_code },
            { label: "Location", value: order.location_label || "Not given" },
            { label: "Allocated", value: formatPaise(order.allocated_paise) },
            {
              label: "Assigned",
              value: date.format(new Date(order.assigned_at)),
            },
            { label: "Instructions", value: order.instructions || "None" },
            { label: "Latest note", value: order.notes || "None yet" },
          ]}
        />
      </section>

      {evidence.data ? (
        <EvidenceView evidence={evidence.data} afterLabel={afterLabel} />
      ) : evidence.isLoading ? (
        <section className="jm-panel">
          <p role="status">Loading the citizen&rsquo;s evidence…</p>
        </section>
      ) : (
        <section className="jm-panel" role="alert">
          <h2>Evidence unavailable</h2>
          <p className="jm-muted">
            The citizen&rsquo;s photo could not be loaded.
          </p>
          <button
            className="jm-button jm-button-secondary"
            onClick={() => void evidence.refetch()}
            disabled={evidence.isFetching}
          >
            {evidence.isFetching ? "Retrying…" : "Retry"}
          </button>
        </section>
      )}

      {(order.status === "funded" || order.status === "in_progress") && (
        <ActionForm
          title="Progress update"
          description={
            order.status === "funded"
              ? "Your first update marks the work as in progress."
              : "Visible to the department and in the audit history."
          }
          fields={[
            {
              name: "notes",
              label: "Update",
              kind: "textarea",
              required: true,
              maxLength: 1000,
            },
          ]}
          submitLabel="Save update"
          onSubmit={async (values) => {
            await updateWorkOrder(api, order.id, String(values.notes));
            await refresh();
            return "Update saved.";
          }}
        />
      )}

      {order.status === "in_progress" && (
        <section className="jm-panel">
          <h2>Completion evidence</h2>
          <p className="jm-muted">
            Photograph the completed work from the same position as the
            citizen&rsquo;s photo where possible. Submitting asks the original
            reporter to verify the repair.
          </p>
          <PhotoUploader
            kind="completion"
            label="Completion photos"
            onChange={setPhotos}
            onPendingChange={setUploading}
          />
          <ActionForm
            // A different photo set is a different request: remounting gives
            // it a fresh idempotency key instead of a 409 on the old one.
            key={photos.map((photo) => photo.id).join("|")}
            title="Submit for citizen verification"
            fields={[]}
            submitLabel={
              uploading
                ? "Waiting for uploads…"
                : `Submit ${photos.length} photo${photos.length === 1 ? "" : "s"}`
            }
            disabled={uploading > 0 || photos.length === 0}
            confirm={() =>
              `Submit ${photos.length} completion photo${photos.length === 1 ? "" : "s"} for ${order.report_code}? The reporter will be asked to verify; you cannot mark it fixed yourself.`
            }
            onSubmit={async (_values, { idempotencyKey }) => {
              await completeWorkOrder(
                api,
                order.id,
                photos.map((photo) => photo.id),
                order.round,
                idempotencyKey,
              );
              await refresh();
              return "Submitted. Awaiting citizen verification.";
            }}
          />
        </section>
      )}
    </>
  );
}
