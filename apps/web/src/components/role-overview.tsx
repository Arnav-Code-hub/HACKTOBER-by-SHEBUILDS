"use client";

import {
  DataPanel,
  DetailList,
  PendingAction,
} from "@/components/workspace-panels";
import { useSession } from "@/lib/auth/session";

const WORKSPACES = {
  student: {
    title: "Student teams",
    description:
      "Create a team and submit a solution to a published local problem.",
    actions: ["Create a team", "Submit a solution"],
  },
  faculty: {
    title: "Faculty reviews",
    description: "Review solution submissions from teams at your institute.",
    actions: ["Review an institute submission"],
  },
  institute: {
    title: "Institute workspace",
    description: "Approve your institute's teams and track participation.",
    actions: ["Approve team participation"],
  },
  panchayat: {
    title: "Panchayat workspace",
    description:
      "Validate citizen reports and confirm which reports describe the same local problem.",
    actions: ["Validate a report", "Confirm cluster membership"],
  },
  department: {
    title: "Department workspace",
    description:
      "Publish problems, record allocations, and assign government work orders.",
    actions: [
      "Publish a problem statement",
      "Record an allocation",
      "Assign a work order",
    ],
  },
  officer: {
    title: "Officer work",
    description:
      "Update your assigned work orders and provide completion evidence for citizen review.",
    actions: ["Update assigned work", "Upload completion evidence"],
  },
  industry: {
    title: "Industry / CSR workspace",
    description:
      "Explore published local problems and record sponsorship pledges.",
    actions: ["Record a sponsorship pledge"],
  },
  admin: {
    title: "Administration",
    description:
      "Inspect district activity and review oversight or user administration tasks according to your assigned role.",
    actions: ["Review district activity"],
  },
} as const;

export function RoleOverview({
  workspace,
}: {
  workspace: keyof typeof WORKSPACES;
}) {
  const { state } = useSession();
  if (state.status !== "authenticated") return null;
  const { profile } = state;
  const content = WORKSPACES[workspace];
  const actions: readonly string[] =
    workspace === "admin" && profile.role === "super_admin"
      ? ["Change a user's role or organization scope"]
      : content.actions;
  return (
    <>
      <div className="jm-page-heading">
        <span className="jm-badge">Day 1 · authenticated shell</span>
        <h1>{content.title}</h1>
        <p>{content.description}</p>
      </div>
      <div className="jm-notice">
        Your identity and scope below come from the API. Workflow endpoints are
        not connected on this page yet.
      </div>
      <div className="jm-panel-grid">
        <section className="jm-panel">
          <h2>Account & scope</h2>
          <DetailList
            items={[
              {
                label: "Account",
                value: profile.display_name || "Name not provided",
              },
              { label: "Email", value: profile.email || "Not provided" },
              { label: "Role", value: profile.role },
              {
                label: "District",
                value: profile.district_id || "Not assigned",
              },
              {
                label: "Department",
                value: profile.department_id || "Not assigned",
              },
              {
                label: "Institute",
                value: profile.institute_id || "Not assigned",
              },
            ]}
          />
        </section>
        <section className="jm-panel">
          <h2>Planned workflow</h2>
          <p className="jm-muted">
            These actions become available after their backend endpoints and
            permission checks are implemented.
          </p>
          {actions.map((action) => (
            <PendingAction
              key={action}
              label={action}
              requirement="Requires the corresponding scoped business API."
            />
          ))}
        </section>
      </div>
      <DataPanel
        title="Workspace records"
        emptyMessage="No records have been requested. Connect this workspace to its scoped list API in the next phase."
      />
    </>
  );
}
