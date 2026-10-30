"use client";

import { useState } from "react";

import { PageHeading, countOf } from "@/components/workspace/page-heading";
import { ActionForm } from "@/components/workspace/action-form";
import { RecordList } from "@/components/workspace/record-list";
import { useInvalidate } from "@/lib/api/hooks";
import { useApi } from "@/lib/api/use-api";
import type { Statement } from "@/features/problem-statements/api";
import { useStatements } from "@/features/problem-statements/hooks";
import { createSubmission, type Submission } from "@/features/projects/api";
import { useMySubmissions } from "@/features/projects/hooks";
import { StudentCouncil } from "@/features/council/components/council-panels";

import { createTeam, type Team } from "../api";
import { useMyTeams } from "../hooks";

const date = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });

/** An optional solution link must be an absolute HTTPS URL. */
export function checkSolutionLink(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  let url: URL;
  try {
    url = new URL(trimmed);
  } catch {
    throw new RangeError("The link must be a full https:// address.");
  }
  if (url.protocol !== "https:")
    throw new RangeError("The link must be a full https:// address.");
  return url.toString();
}

/**
 * Student: form a team around a published problem statement and, once the
 * institute approves it, submit a solution. Student work is separate from
 * government work orders and never approves a public repair.
 */
export function StudentWorkspace() {
  const api = useApi();
  const invalidate = useInvalidate();
  const [teamId, setTeamId] = useState<string | null>(null);

  const statements = useStatements("published");
  const teams = useMyTeams();
  const submissions = useMySubmissions();
  const team = teams.data?.items.find((t) => t.id === teamId) ?? null;

  return (
    <>
      <PageHeading
        role="Student"
        title="Solve a published local problem"
        steps={[
          "Choose a published problem statement.",
          "Form a team and wait for institute approval.",
          "Submit your solution for faculty review.",
        ]}
        stats={[
          { label: "Open statements", value: countOf(statements.data?.items) },
          { label: "Teams joined", value: countOf(teams.data?.items) },
          {
            label: "Solutions submitted",
            value: countOf(submissions.data?.items),
          },
        ]}
      >
        Form a team around a problem statement. Once your institute approves the
        team, submit your solution for faculty review.
      </PageHeading>

      <RecordList
        title="Published problem statements"
        description="Problems departments have opened to student teams."
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
        onRefresh={() => void statements.refetch()}
        isRefreshing={statements.isFetching}
        emptyMessage="No problem statements are published yet."
        rowKey={(s) => s.id}
      />

      <div className="jm-panel-grid jm-section">
        <RecordList
          title="Your teams"
          columns={[
            {
              header: "Team",
              cell: (t: Team) => (
                <>
                  <strong>{t.name}</strong>
                  <br />
                  <span className="jm-small">{t.statement_title}</span>
                </>
              ),
            },
            {
              header: "Institute",
              cell: (t: Team) =>
                t.institute_approved ? (
                  <span className="jm-badge jm-tone-success">Approved</span>
                ) : (
                  <span className="jm-badge">Awaiting approval</span>
                ),
            },
          ]}
          rows={teams.data?.items}
          isLoading={teams.isLoading}
          error={teams.error}
          onRefresh={() => void teams.refetch()}
          isRefreshing={teams.isFetching}
          emptyMessage="You are not in a team yet."
          rowKey={(t) => t.id}
          onSelect={(t) => setTeamId(t.id)}
          selectedKey={teamId}
        />

        <div className="jm-stack">
          {team &&
            (team.institute_approved ? (
              <ActionForm
                key={`submit-${team.id}`}
                title={`Submit a solution · ${team.name}`}
                description={`For “${team.statement_title}”. Faculty at your institute will review it.`}
                fields={[
                  {
                    name: "title",
                    label: "Solution title",
                    kind: "text",
                    required: true,
                    maxLength: 120,
                  },
                  {
                    name: "summary",
                    label: "What you propose",
                    kind: "textarea",
                    required: true,
                    maxLength: 2000,
                  },
                  {
                    name: "link",
                    label: "Link to your work",
                    kind: "text",
                    maxLength: 500,
                    hint: "A full https:// address, for example a repository or document.",
                  },
                ]}
                submitLabel="Submit solution"
                onSubmit={async (values, { idempotencyKey }) => {
                  const link = checkSolutionLink(String(values.link ?? ""));
                  await createSubmission(
                    api,
                    {
                      team_id: team.id,
                      title: String(values.title),
                      summary: String(values.summary),
                      ...(link ? { link } : {}),
                    },
                    idempotencyKey,
                  );
                  await invalidate("submissions");
                  return "Solution submitted for faculty review.";
                }}
              />
            ) : (
              <section className="jm-panel">
                <h2>{team.name}</h2>
                <p className="jm-muted">
                  Your institute has not approved this team yet. You can submit
                  a solution once it does.
                </p>
              </section>
            ))}

          <ActionForm
            title="Create a team"
            description="You will be its first member. Your institute is taken from your account."
            fields={[
              {
                name: "name",
                label: "Team name",
                kind: "text",
                required: true,
                maxLength: 80,
              },
              {
                name: "statement_id",
                label: "Problem statement",
                kind: "select",
                required: true,
                options: (statements.data?.items ?? []).map((s) => ({
                  value: s.id,
                  label: s.title,
                })),
              },
            ]}
            submitLabel="Create team"
            disabled={!statements.data?.items.length}
            onSubmit={async (values, { idempotencyKey }) => {
              const created = await createTeam(
                api,
                {
                  name: String(values.name),
                  statement_id: String(values.statement_id),
                },
                idempotencyKey,
              );
              await invalidate("teams");
              setTeamId(created.id);
              return "Team created. Ask your institute to approve it.";
            }}
          />
        </div>
      </div>

      <StudentCouncil submissions={submissions.data?.items} />

      <div className="jm-section">
        <RecordList
          title="Your submissions"
          columns={[
            {
              header: "Solution",
              cell: (s: Submission) => (
                <>
                  <strong>{s.title}</strong>
                  <br />
                  <span className="jm-small">
                    {s.team_name} · {s.statement_title}
                  </span>
                </>
              ),
            },
            {
              header: "Submitted",
              cell: (s: Submission) => date.format(new Date(s.submitted_at)),
            },
            {
              header: "Reviews",
              cell: (s: Submission) => s.review_count,
            },
          ]}
          rows={submissions.data?.items}
          isLoading={submissions.isLoading}
          error={submissions.error}
          onRefresh={() => void submissions.refetch()}
          isRefreshing={submissions.isFetching}
          emptyMessage="No solutions submitted yet."
          rowKey={(s) => s.id}
        />
      </div>
    </>
  );
}
