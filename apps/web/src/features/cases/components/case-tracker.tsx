"use client";

import { useState } from "react";

import { EvidenceView } from "@/components/workspace/evidence-view";
import { RecordList } from "@/components/workspace/record-list";
import { StatusBadge } from "@/components/workspace/status-badge";
import { DetailList } from "@/components/workspace-panels";
import { useWorkOrderEvidence } from "@/features/departments/hooks";
import { CATEGORY_LABEL } from "@/features/problems/labels";
import { formatPaise } from "@/lib/money";

import { WAITING_LABEL, WAITING_ON, type Case } from "../api";
import { useCases } from "../hooks";

const date = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });

/**
 * Every case from prioritisation to citizen verification: who must act next,
 * and for funded work the allocation receipt and the evidence. Funded cases
 * leave the ranked list; this is where they are followed afterwards.
 */
export function CaseTracker({ description }: { description: string }) {
  const cases = useCases();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected =
    cases.data?.items.find((c) => c.cluster_id === selectedId) ?? null;
  const counts = (waiting: Case["waiting_on"]) =>
    cases.data?.items.filter((c) => c.waiting_on === waiting).length;

  return (
    <div className="jm-section">
      <ul className="jm-stat-blocks" aria-label="Who the cases are waiting on">
        {WAITING_ON.map((waiting) => (
          <li key={waiting}>
            <span>
              {waiting === "none"
                ? "Verified by citizens"
                : `Waiting on ${WAITING_LABEL[waiting].toLowerCase()}`}
            </span>
            <strong>{counts(waiting) ?? "—"}</strong>
          </li>
        ))}
      </ul>
      <div className="jm-panel-grid">
        <RecordList
          title="Case tracker"
          description={description}
          columns={[
            {
              header: "Case",
              cell: (c: Case) => (
                <>
                  <strong>{c.title}</strong>
                  <br />
                  <span className="jm-small">
                    {c.report_code} · {CATEGORY_LABEL[c.category]}
                  </span>
                </>
              ),
            },
            {
              header: "Status",
              cell: (c: Case) => <StatusBadge status={c.status} />,
            },
            {
              header: "Waiting on",
              cell: (c: Case) => (
                <span className={`jm-waiting jm-waiting-${c.waiting_on}`}>
                  {WAITING_LABEL[c.waiting_on]}
                </span>
              ),
            },
            {
              header: "Allocated",
              cell: (c: Case) =>
                c.allocated_paise === null
                  ? "—"
                  : formatPaise(c.allocated_paise),
            },
          ]}
          rows={cases.data?.items}
          isLoading={cases.isLoading}
          error={cases.error}
          onRefresh={() => void cases.refetch()}
          isRefreshing={cases.isFetching}
          emptyMessage="No prioritised or funded cases yet."
          rowKey={(c) => c.cluster_id}
          onSelect={(c) => setSelectedId(c.cluster_id)}
          selectedKey={selectedId}
        />
        <div className="jm-stack">
          {selected ? (
            <CaseDetail key={selected.cluster_id} item={selected} />
          ) : (
            <section className="jm-panel">
              <h2>Select a case</h2>
              <p className="jm-muted">
                Open a case to see its allocation receipt and evidence.
              </p>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

function CaseDetail({ item }: { item: Case }) {
  const evidence = useWorkOrderEvidence(
    item.work_order_id,
    item.work_order_id !== null,
  );
  return (
    <>
      <section className="jm-panel" aria-label={`Case ${item.report_code}`}>
        <div className="jm-evidence-heading">
          <h2>{item.title}</h2>
          <StatusBadge status={item.status} />
        </div>
        {item.work_order_id === null ? (
          <p className="jm-muted">
            Prioritised and waiting for the responsible department to record an
            allocation and assign an officer.
          </p>
        ) : (
          <>
            <h3 className="jm-subheading">Allocation receipt</h3>
            <DetailList
              items={[
                {
                  label: "Amount",
                  value:
                    item.allocated_paise === null
                      ? "—"
                      : formatPaise(item.allocated_paise),
                },
                { label: "Department", value: item.department_name ?? "—" },
                { label: "Officer", value: item.officer_name ?? "—" },
                {
                  label: "Recorded by",
                  value: item.allocated_by_name ?? "—",
                },
                {
                  label: "Recorded on",
                  value: item.allocated_at
                    ? date.format(new Date(item.allocated_at))
                    : "—",
                },
                { label: "Round", value: item.round ?? "—" },
                {
                  label: "Waiting on",
                  value: WAITING_LABEL[item.waiting_on],
                },
              ]}
            />
            <p className="jm-small">A recorded allocation, not a payment.</p>
          </>
        )}
      </section>
      {item.work_order_id !== null &&
        (evidence.data ? (
          <EvidenceView evidence={evidence.data} />
        ) : evidence.isLoading ? (
          <section className="jm-panel">
            <p role="status">Loading the evidence…</p>
          </section>
        ) : (
          <section className="jm-panel" role="alert">
            <h2>Evidence unavailable</h2>
            <button
              type="button"
              className="jm-button jm-button-secondary"
              onClick={() => void evidence.refetch()}
            >
              Retry
            </button>
          </section>
        ))}
    </>
  );
}
