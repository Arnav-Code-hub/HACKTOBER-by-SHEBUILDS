"use client";

import { useState } from "react";

import { PageHeading, countOf } from "@/components/workspace/page-heading";
import { CaseTracker } from "@/features/cases/components/case-tracker";
import { ActionForm } from "@/components/workspace/action-form";
import { RecordList } from "@/components/workspace/record-list";
import { ScoreBreakdown } from "@/components/workspace/score-breakdown";
import { StatusBadge } from "@/components/workspace/status-badge";
import { useInvalidate } from "@/lib/api/hooks";
import { useApi } from "@/lib/api/use-api";
import { formatPaise } from "@/lib/money";
import {
  createStatement,
  publishStatement,
  type Statement,
} from "@/features/problem-statements/api";
import { useStatements } from "@/features/problem-statements/hooks";
import { updateRankingInputs } from "@/features/problems/api";
import { RankedClusters } from "@/features/problems/components/ranked-clusters";
import { useRankedClusters } from "@/features/problems/hooks";

import { fundCluster, officerName } from "../api";
import { useAssignableOfficers } from "../hooks";

/**
 * Department: review the ranked list, correct the officer-controlled ranking
 * inputs, fund a cluster and assign its work order, and publish problem
 * statements for student and CSR participation.
 */
export function DepartmentWorkspace() {
  const api = useApi();
  const invalidate = useInvalidate();
  const [clusterId, setClusterId] = useState<string | null>(null);
  const [statementId, setStatementId] = useState<string | null>(null);

  const ranked = useRankedClusters();
  const officers = useAssignableOfficers();
  const statements = useStatements();
  const cluster = ranked.data?.items.find((c) => c.id === clusterId) ?? null;
  const statement =
    statements.data?.items.find((s) => s.id === statementId) ?? null;
  const officerOptions = (officers.data?.items ?? []).map((o) => ({
    value: o.id,
    label: officerName(o),
  }));

  return (
    <>
      <PageHeading
        role="Department"
        title="Fund the ranked list"
        steps={[
          "Pick a prioritised cluster from the ranked list.",
          "Record the allocation and assign an officer.",
          "Publish problem statements for students and CSR partners.",
        ]}
        stats={[
          { label: "Ready to fund", value: countOf(ranked.data?.items) },
          { label: "Officers to assign", value: countOf(officers.data?.items) },
          { label: "Statements", value: countOf(statements.data?.items) },
        ]}
      >
        Allocations are recorded against a cluster and its work order is
        assigned to an officer in your district. This records the allocation; it
        does not move money.
      </PageHeading>

      <RankedClusters
        onSelect={(c) => setClusterId(c.id)}
        selectedId={clusterId}
        description="Open a cluster to see why it ranks where it does, adjust its official inputs, or fund it."
      />

      {cluster && (
        <div className="jm-panel-grid jm-section">
          <section className="jm-panel" aria-label={`Cluster ${cluster.title}`}>
            <div className="jm-evidence-heading">
              <h2>
                #{cluster.rank} · {cluster.title}
              </h2>
              <StatusBadge status={cluster.status} />
            </div>
            <ScoreBreakdown factors={cluster.score_breakdown} />
            <p className="jm-small">
              Community support counts unique citizens who reported or supported
              this problem. It is not a population estimate.
            </p>
          </section>

          <div className="jm-stack">
            <ActionForm
              key={`inputs-${cluster.id}-${cluster.infrastructure_gap}-${cluster.equity_index}`}
              title="Official ranking inputs"
              description={
                cluster.inputs_are_demo
                  ? "These values are demo or neutral defaults. Replace them with your department's assessment."
                  : "Your department's current assessment, 0–100."
              }
              fields={[
                {
                  name: "infrastructure_gap",
                  label: "Infrastructure gap",
                  kind: "number",
                  required: true,
                  min: 0,
                  max: 100,
                  defaultValue: String(cluster.infrastructure_gap),
                },
                {
                  name: "equity_index",
                  label: "Equity index",
                  kind: "number",
                  required: true,
                  min: 0,
                  max: 100,
                  defaultValue: String(cluster.equity_index),
                },
              ]}
              submitLabel="Save inputs"
              confirm={() =>
                "Save these inputs? The ranking is recalculated for the whole district and the change is audited."
              }
              onSubmit={async (values) => {
                await updateRankingInputs(api, cluster.id, {
                  infrastructure_gap: Number(values.infrastructure_gap),
                  equity_index: Number(values.equity_index),
                });
                await invalidate("clusters");
                return "Inputs saved. The ranking has been recalculated.";
              }}
            />

            {cluster.status === "prioritised" ? (
              <ActionForm
                key={`fund-${cluster.id}`}
                title="Fund and assign"
                description={
                  officers.error
                    ? "The officer list could not be loaded. Refresh before assigning."
                    : "One allocation per cluster. The officer receives the work order."
                }
                fields={[
                  {
                    name: "amount_paise",
                    label: "Allocation",
                    kind: "money",
                    required: true,
                  },
                  {
                    name: "officer_id",
                    label: "Assign to officer",
                    kind: "select",
                    required: true,
                    options: officerOptions,
                  },
                  {
                    name: "notes",
                    label: "Instructions for the officer",
                    kind: "textarea",
                    maxLength: 500,
                  },
                ]}
                submitLabel="Record allocation"
                disabled={!officerOptions.length}
                confirm={(values) => {
                  const officer = officerOptions.find(
                    (o) => o.value === values.officer_id,
                  );
                  return `Allocate ${formatPaise(Number(values.amount_paise))} to “${cluster.title}” and assign the work order to ${officer?.label ?? "the selected officer"}? This is recorded and audited.`;
                }}
                onSubmit={async (values, { idempotencyKey }) => {
                  await fundCluster(
                    api,
                    cluster.id,
                    {
                      amount_paise: Number(values.amount_paise),
                      officer_id: String(values.officer_id),
                      ...(values.notes ? { notes: String(values.notes) } : {}),
                    },
                    idempotencyKey,
                  );
                  await Promise.all([
                    invalidate("clusters"),
                    invalidate("reports"),
                  ]);
                  return "Allocation recorded and work order assigned.";
                }}
              />
            ) : (
              <section className="jm-panel">
                <h2>Funding</h2>
                <p className="jm-muted">
                  Only a prioritised cluster can be funded. This cluster is{" "}
                  <StatusBadge status={cluster.status} />.
                </p>
              </section>
            )}
          </div>
        </div>
      )}

      <div className="jm-panel-grid jm-section">
        <RecordList
          title="Problem statements"
          description="Published statements invite student solutions and CSR pledges. They do not authorise a government repair."
          columns={[
            {
              header: "Statement",
              cell: (s: Statement) => <strong>{s.title}</strong>,
            },
            {
              header: "Status",
              cell: (s: Statement) => (
                <span className="jm-badge">
                  {s.status === "published" ? "Published" : "Draft"}
                </span>
              ),
            },
          ]}
          rows={statements.data?.items}
          isLoading={statements.isLoading}
          error={statements.error}
          onRefresh={() => void statements.refetch()}
          isRefreshing={statements.isFetching}
          emptyMessage="No problem statements yet."
          rowKey={(s) => s.id}
          onSelect={(s) => setStatementId(s.id)}
          selectedKey={statementId}
        />

        <div className="jm-stack">
          {statement?.status === "draft" && (
            <ActionForm
              key={`publish-${statement.id}`}
              title={`Publish “${statement.title}”`}
              description={statement.body}
              fields={[]}
              submitLabel="Publish statement"
              confirm={() =>
                "Publish this statement? Students and CSR partners will be able to respond to it."
              }
              onSubmit={async () => {
                await publishStatement(api, statement.id);
                await invalidate("statements");
                return "Statement published.";
              }}
            />
          )}
          <ActionForm
            title="New problem statement"
            description="Saved as a draft; publish it when ready."
            fields={[
              {
                name: "title",
                label: "Title",
                kind: "text",
                required: true,
                maxLength: 120,
              },
              {
                name: "body",
                label: "What needs solving",
                kind: "textarea",
                required: true,
                maxLength: 2000,
              },
              {
                name: "cluster_id",
                label: "Linked cluster",
                kind: "select",
                options: (ranked.data?.items ?? []).map((c) => ({
                  value: c.id,
                  label: `#${c.rank} · ${c.title}`,
                })),
              },
            ]}
            submitLabel="Save draft"
            onSubmit={async (values, { idempotencyKey }) => {
              const saved = await createStatement(
                api,
                {
                  title: String(values.title),
                  body: String(values.body),
                  ...(values.cluster_id
                    ? { cluster_id: String(values.cluster_id) }
                    : {}),
                },
                idempotencyKey,
              );
              await invalidate("statements");
              setStatementId(saved.id);
              return "Draft saved. Publish it from the list when ready.";
            }}
          />
        </div>
      </div>

      <CaseTracker description="Cases your department must fund or has funded, from prioritisation to citizen verification." />
    </>
  );
}
