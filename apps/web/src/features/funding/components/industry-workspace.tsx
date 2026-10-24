"use client";

import { useState } from "react";

import { ActionForm } from "@/components/workspace/action-form";
import { RecordList } from "@/components/workspace/record-list";
import { useInvalidate } from "@/lib/api/hooks";
import { formatPaise } from "@/lib/money";
import { useApi } from "@/lib/api/use-api";
import type { Statement } from "@/features/problem-statements/api";
import { useStatements } from "@/features/problem-statements/hooks";

import { pledgeSponsorship, type Sponsorship } from "../api";
import { useMySponsorships } from "../hooks";

const date = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });

/**
 * Industry / CSR: pledge support against published problem statements. A
 * pledge is a recorded intention; JanMaang moves no money.
 */
export function IndustryWorkspace() {
  const api = useApi();
  const invalidate = useInvalidate();
  const [statementId, setStatementId] = useState<string | null>(null);
  const statements = useStatements("published");
  const pledges = useMySponsorships();
  const statement =
    statements.data?.items.find((s) => s.id === statementId) ?? null;

  return (
    <>
      <div className="jm-page-heading">
        <span className="jm-badge">Industry / CSR</span>
        <h1>Support a local problem</h1>
        <p>
          Pledge support for a published problem statement. A pledge is recorded
          for transparency; no payment is taken here.
        </p>
      </div>

      <div className="jm-panel-grid">
        <RecordList
          title="Published problem statements"
          columns={[
            {
              header: "Statement",
              cell: (s: Statement) => (
                <>
                  <strong>{s.title}</strong>
                  <p className="jm-small jm-clamp">{s.body}</p>
                </>
              ),
            },
          ]}
          rows={statements.data?.items}
          isLoading={statements.isLoading}
          error={statements.error}
          onRetry={() => void statements.refetch()}
          emptyMessage="No problem statements are published yet."
          rowKey={(s) => s.id}
          onSelect={(s) => setStatementId(s.id)}
          selectedKey={statementId}
        />

        <div className="jm-stack">
          {statement ? (
            <ActionForm
              key={`pledge-${statement.id}`}
              title={`Pledge for “${statement.title}”`}
              description={statement.body}
              fields={[
                {
                  name: "amount_paise",
                  label: "Pledge amount",
                  kind: "money",
                  required: true,
                },
              ]}
              submitLabel="Record pledge"
              confirm={(values) =>
                `Record a pledge of ${formatPaise(Number(values.amount_paise))}? It is published as pledged support; no payment is taken.`
              }
              onSubmit={async (values, { idempotencyKey }) => {
                await pledgeSponsorship(
                  api,
                  statement.id,
                  Number(values.amount_paise),
                  idempotencyKey,
                );
                await invalidate("sponsorships");
                return "Pledge recorded.";
              }}
            />
          ) : (
            <section className="jm-panel">
              <h2>Select a statement</h2>
              <p className="jm-muted">Open a statement to pledge support.</p>
            </section>
          )}
        </div>
      </div>

      <div className="jm-section">
        <RecordList
          title="Your pledges"
          columns={[
            {
              header: "Statement",
              cell: (p: Sponsorship) => p.statement_title,
            },
            {
              header: "Amount",
              cell: (p: Sponsorship) => formatPaise(p.amount_paise),
            },
            {
              header: "Status",
              cell: () => <span className="jm-badge">Pledged</span>,
            },
            {
              header: "Date",
              cell: (p: Sponsorship) => date.format(new Date(p.pledged_at)),
            },
          ]}
          rows={pledges.data?.items}
          isLoading={pledges.isLoading}
          error={pledges.error}
          onRetry={() => void pledges.refetch()}
          emptyMessage="Your organisation has not pledged yet."
          rowKey={(p) => p.id}
        />
      </div>
    </>
  );
}
