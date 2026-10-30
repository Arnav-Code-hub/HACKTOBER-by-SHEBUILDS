"use client";

import { useState } from "react";

import { PageHeading, countOf } from "@/components/workspace/page-heading";
import { ActionForm } from "@/components/workspace/action-form";
import { RecordList } from "@/components/workspace/record-list";
import { useInvalidate } from "@/lib/api/hooks";
import { useApi } from "@/lib/api/use-api";
import { SupervisorPanel } from "@/features/council/components/council-panels";

import { approveTeam, type Team } from "../api";
import { useInstituteTeams } from "../hooks";

const date = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });

/**
 * Institute: approve your students' teams for participation. Approval is
 * institutional sponsorship of student work, not approval of any repair.
 */
export function InstituteWorkspace() {
  const api = useApi();
  const invalidate = useInvalidate();
  const [teamId, setTeamId] = useState<string | null>(null);
  const teams = useInstituteTeams();
  const team = teams.data?.items.find((t) => t.id === teamId) ?? null;

  return (
    <>
      <PageHeading
        role="Institute"
        title="Approve your student teams"
        steps={[
          "See the teams your students have formed.",
          "Approve teams that are ready to work.",
          "Approved teams can submit solutions.",
        ]}
        stats={[
          {
            label: "Awaiting approval",
            value: countOf(teams.data?.items, (t) => !t.institute_approved),
          },
          {
            label: "Approved teams",
            value: countOf(teams.data?.items, (t) => t.institute_approved),
          },
        ]}
      >
        Approved teams can submit solutions to published problem statements. You
        only see teams from your own institute.
      </PageHeading>

      {team && <SupervisorPanel teamId={team.id} />}

      <div className="jm-panel-grid">
        <RecordList
          title="Teams at your institute"
          columns={[
            {
              header: "Team",
              cell: (t: Team) => (
                <>
                  <strong>{t.name}</strong>
                  <br />
                  <span className="jm-small">
                    {t.statement_title} · {t.member_count} member
                    {t.member_count === 1 ? "" : "s"}
                  </span>
                </>
              ),
            },
            {
              header: "Created",
              cell: (t: Team) => date.format(new Date(t.created_at)),
            },
            {
              header: "Status",
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
          emptyMessage="No teams from your institute yet."
          rowKey={(t) => t.id}
          onSelect={(t) => setTeamId(t.id)}
          selectedKey={teamId}
        />

        <div className="jm-stack">
          {!team ? (
            <section className="jm-panel">
              <h2>Select a team</h2>
              <p className="jm-muted">Open a team to review it.</p>
            </section>
          ) : team.institute_approved ? (
            <section className="jm-panel">
              <h2>{team.name}</h2>
              <p className="jm-muted">
                Approved. The team can submit solutions.
              </p>
            </section>
          ) : (
            <ActionForm
              key={`approve-${team.id}`}
              title={`Approve ${team.name}`}
              description={`Working on “${team.statement_title}”.`}
              fields={[]}
              submitLabel="Approve team"
              confirm={() =>
                `Approve ${team.name} to participate on behalf of your institute?`
              }
              onSubmit={async () => {
                await approveTeam(api, team.id);
                await invalidate("teams");
                return `${team.name} is approved.`;
              }}
            />
          )}
        </div>
      </div>
    </>
  );
}
