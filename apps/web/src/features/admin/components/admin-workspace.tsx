"use client";

import { useState } from "react";

import { PageHeading } from "@/components/workspace/page-heading";
import { CaseTracker } from "@/features/cases/components/case-tracker";
import {
  ActionForm,
  type FormValues,
} from "@/components/workspace/action-form";
import { RecordList } from "@/components/workspace/record-list";
import { STATUS_DISPLAY } from "@/components/workspace/status-badge";
import { useInvalidate } from "@/lib/api/hooks";
import { REPORT_STATUSES } from "@/lib/api/schemas";
import { useApi } from "@/lib/api/use-api";
import { ROLES, ROLE_LABEL } from "@/lib/auth/roles";
import { useSession } from "@/lib/auth/session";
import { formatPaise } from "@/lib/money";

import {
  changeUserRole,
  type AdminUser,
  type Organization,
  type Summary,
} from "../api";
import { useAdminSummary, useAdminUsers, useOrganizations } from "../hooks";
import { AuditTrail } from "./audit-trail";

/**
 * Government and super administrators: district progress, recorded funding
 * and the audit trail. Super administrators also change a user's role or
 * scope; every change carries a reason and is audited by the API.
 */
export function AdminWorkspace() {
  const { state } = useSession();
  const isSuperAdmin =
    state.status === "authenticated" && state.profile.role === "super_admin";
  const summary = useAdminSummary();

  return (
    <>
      <PageHeading
        role="Administration"
        title="District oversight"
        steps={[
          "Follow reports and work orders by status.",
          "Check recorded allocations and CSR pledges.",
          "Review the audit trail; super admins manage roles.",
        ]}
      >
        Progress, recorded funding and the audit trail for your scope. Amounts
        are recorded allocations and pledges, not payments.
      </PageHeading>

      {summary.data && (
        <div className="jm-button-row jm-refresh-row">
          <button
            type="button"
            className="jm-button jm-button-secondary jm-button-small"
            onClick={() => void summary.refetch()}
            disabled={summary.isFetching}
          >
            {summary.isFetching ? "Refreshing…" : "Refresh summary"}
          </button>
        </div>
      )}
      {summary.isLoading ? (
        <section className="jm-panel">
          <p role="status">Loading the district summary…</p>
        </section>
      ) : !summary.data ? (
        <section className="jm-panel" role="alert">
          <h2>Summary unavailable</h2>
          <button
            className="jm-button jm-button-secondary"
            onClick={() => void summary.refetch()}
          >
            Retry
          </button>
        </section>
      ) : (
        <>
          {summary.error && (
            <p className="jm-form-error" role="alert">
              Could not refresh the summary. Showing the last loaded figures.
            </p>
          )}
          <SummaryPanels summary={summary.data} />
        </>
      )}

      <CaseTracker description="Every prioritised and funded case in your scope, and who must act next." />

      <AuditTrail />

      {isSuperAdmin && <UserAdministration />}
    </>
  );
}

function SummaryPanels({ summary }: { summary: Summary }) {
  const counts = (by: Summary["reports_by_status"]) =>
    REPORT_STATUSES.filter((status) => (by[status] ?? 0) > 0).map((status) => ({
      status,
      count: by[status] ?? 0,
    }));
  const reports = counts(summary.reports_by_status);
  const orders = counts(summary.work_orders_by_status);

  return (
    <>
      <div
        className="jm-stat-grid"
        aria-label={`Summary for ${summary.district_name}`}
      >
        <div className="jm-panel jm-stat">
          <span className="jm-eyebrow">District</span>
          <strong>{summary.district_name}</strong>
        </div>
        <div className="jm-panel jm-stat">
          <span className="jm-eyebrow">Confirmed clusters</span>
          <strong>{summary.cluster_count}</strong>
        </div>
        <div className="jm-panel jm-stat">
          <span className="jm-eyebrow">Allocated (recorded)</span>
          <strong>{formatPaise(summary.allocated_paise)}</strong>
        </div>
        <div className="jm-panel jm-stat">
          <span className="jm-eyebrow">CSR pledged</span>
          <strong>{formatPaise(summary.pledged_paise)}</strong>
        </div>
      </div>
      <div className="jm-panel-grid jm-section">
        <StatusCounts
          title="Reports by status"
          rows={reports}
          empty="No reports yet."
        />
        <StatusCounts
          title="Work orders by status"
          rows={orders}
          empty="No work orders yet."
        />
      </div>
    </>
  );
}

function StatusCounts({
  title,
  rows,
  empty,
}: {
  title: string;
  rows: { status: (typeof REPORT_STATUSES)[number]; count: number }[];
  empty: string;
}) {
  return (
    <section className="jm-panel">
      <h2>{title}</h2>
      {rows.length ? (
        <dl className="jm-details">
          {rows.map((row) => (
            <div key={row.status}>
              <dt>{STATUS_DISPLAY[row.status].label}</dt>
              <dd>{row.count}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="jm-muted">{empty}</p>
      )}
    </section>
  );
}

type Access = {
  role: AdminUser["role"];
  district_id: string | null;
  department_id: string | null;
  institute_id: string | null;
  organization_id: string | null;
};

const DEPARTMENT_ROLES: readonly AdminUser["role"][] = [
  "department",
  "officer",
];
const INSTITUTE_ROLES: readonly AdminUser["role"][] = [
  "student",
  "faculty",
  "institute",
];

function currentAccess(user: AdminUser): Access {
  return {
    role: user.role,
    district_id: user.district_id,
    department_id: user.department_id,
    institute_id: user.institute_id,
    organization_id: user.organization_id ?? null,
  };
}

/** The access the API will store: scopes the role does not use are cleared. */
export function proposedAccess(values: FormValues): Access {
  const role = values.role as AdminUser["role"];
  const id = (key: string) => (values[key] ? String(values[key]) : null);
  return {
    role,
    district_id: id("district_id"),
    department_id: DEPARTMENT_ROLES.includes(role) ? id("department_id") : null,
    institute_id: INSTITUTE_ROLES.includes(role) ? id("institute_id") : null,
    organization_id: role === "industry" ? id("organization_id") : null,
  };
}

/** The scope a role needs before the API will accept it, or null. */
export function accessProblem(access: Access): string | null {
  const label = ROLE_LABEL[access.role];
  if (access.role !== "super_admin" && !access.district_id)
    return `${label} accounts need a district.`;
  if (DEPARTMENT_ROLES.includes(access.role) && !access.department_id)
    return `${label} accounts need a department in that district.`;
  if (INSTITUTE_ROLES.includes(access.role) && !access.institute_id)
    return `${label} accounts need an institute in that district.`;
  if (access.role === "industry" && !access.organization_id)
    return `${label} accounts need an industry organization in that district.`;
  return null;
}

/** A named before-and-after comparison shown before the change is applied. */
export function accessPreview(
  name: string,
  before: Access,
  after: Access,
  orgName: (id: string | null) => string,
) {
  const rows: [string, string, string][] = [
    ["Role", ROLE_LABEL[before.role], ROLE_LABEL[after.role]],
    ["District", orgName(before.district_id), orgName(after.district_id)],
    ["Department", orgName(before.department_id), orgName(after.department_id)],
    ["Institute", orgName(before.institute_id), orgName(after.institute_id)],
    [
      "Industry organization",
      orgName(before.organization_id),
      orgName(after.organization_id),
    ],
  ];
  const lines = rows
    .filter(([, from, to]) => !(from === "—" && to === "—"))
    .map(([field, from, to]) =>
      from === to ? `${field}: ${to} (unchanged)` : `${field}: ${from} → ${to}`,
    );
  return [
    `Change access for ${name}?`,
    ...lines,
    "Their access changes on their next request, and the change is audited with your reason.",
  ].join("\n");
}

const SELF_CHANGE =
  "You cannot change your own role or scope. Another super administrator must make this change.";

function UserAdministration() {
  const api = useApi();
  const invalidate = useInvalidate();
  const { state } = useSession();
  // Changing your own access would leave this session's profile, navigation
  // and cache scope stale, so the prototype refuses it (the API should too).
  const selfId = state.status === "authenticated" ? state.profile.id : null;
  const [userId, setUserId] = useState<string | null>(null);
  const users = useAdminUsers(true);
  const organizations = useOrganizations(true);
  const user = users.data?.items.find((u) => u.id === userId) ?? null;
  const orgs = organizations.data?.items ?? [];
  const orgName = (id: string | null | undefined) =>
    id ? (orgs.find((o) => o.id === id)?.name ?? id) : "—";
  const districts = orgs
    .filter((o) => o.type === "district")
    .map((o) => ({ value: o.id, label: o.name }));
  // Departments, institutes and industry organizations belong to a district;
  // only those in the chosen district are offered.
  const inDistrict =
    (type: Organization["type"]) => (values: Record<string, string>) =>
      orgs
        .filter(
          (o) =>
            o.type === type &&
            Boolean(values.district_id) &&
            o.parent_id === values.district_id,
        )
        .map((o) => ({ value: o.id, label: o.name }));

  return (
    <div className="jm-panel-grid jm-section">
      <RecordList
        title="Users"
        description="Change a user's role or organisation scope. Every change needs a reason and is audited."
        columns={[
          {
            header: "User",
            cell: (u: AdminUser) => (
              <>
                <strong>{u.display_name || u.email || u.id}</strong>
                {u.id === selfId && <span className="jm-small"> (you)</span>}
                {u.email && u.display_name && (
                  <>
                    <br />
                    <span className="jm-small">{u.email}</span>
                  </>
                )}
              </>
            ),
          },
          { header: "Role", cell: (u: AdminUser) => ROLE_LABEL[u.role] },
          {
            header: "Scope",
            cell: (u: AdminUser) =>
              [
                u.district_id,
                u.department_id,
                u.institute_id,
                u.organization_id,
              ]
                .filter(Boolean)
                .map(orgName)
                .join(" · ") || "—",
          },
        ]}
        rows={users.data?.items}
        isLoading={users.isLoading}
        error={users.error}
        onRefresh={() => void users.refetch()}
        isRefreshing={users.isFetching}
        emptyMessage="No users found."
        rowKey={(u) => u.id}
        onSelect={(u) => setUserId(u.id)}
        selectedKey={userId}
      />

      <div className="jm-stack">
        {user && user.id === selfId ? (
          <section className="jm-panel" role="status">
            <h2>This is your account</h2>
            <p className="jm-muted">{SELF_CHANGE}</p>
          </section>
        ) : user ? (
          <ActionForm
            key={`role-${user.id}-${user.role}-${user.district_id}-${user.department_id}-${user.institute_id}-${user.organization_id}`}
            title={`Change role or scope · ${user.display_name || user.email || user.id}`}
            fields={[
              {
                name: "role",
                label: "Role",
                kind: "select",
                required: true,
                defaultValue: user.role,
                options: ROLES.map((role) => ({
                  value: role,
                  label: ROLE_LABEL[role],
                })),
              },
              {
                name: "district_id",
                label: "District",
                kind: "select",
                defaultValue: user.district_id ?? "",
                options: districts,
              },
              {
                name: "department_id",
                label: "Department",
                kind: "select",
                defaultValue: user.department_id ?? "",
                options: inDistrict("department"),
                hint: "Choose a district first; only its organizations are listed.",
              },
              {
                name: "institute_id",
                label: "Institute",
                kind: "select",
                defaultValue: user.institute_id ?? "",
                options: inDistrict("institute"),
                hint: "Choose a district first; only its organizations are listed.",
              },
              {
                name: "organization_id",
                label: "Industry organization",
                kind: "select",
                defaultValue: user.organization_id ?? "",
                options: inDistrict("industry"),
                hint: "Choose a district first; only its organizations are listed.",
              },
              {
                name: "reason",
                label: "Reason for the change",
                kind: "textarea",
                required: true,
                maxLength: 300,
              },
            ]}
            submitLabel="Apply change"
            validate={(values) => accessProblem(proposedAccess(values))}
            confirm={(values) =>
              accessPreview(
                user.display_name || user.email || "this user",
                currentAccess(user),
                proposedAccess(values),
                orgName,
              )
            }
            onSubmit={async (values) => {
              // Guarded here as well as hidden above, in case the session
              // and the selected row change between render and submit.
              if (user.id === selfId) throw new RangeError(SELF_CHANGE);
              const id = (key: string) =>
                values[key] ? String(values[key]) : null;
              await changeUserRole(api, user.id, {
                role: values.role as AdminUser["role"],
                district_id: id("district_id"),
                department_id: id("department_id"),
                institute_id: id("institute_id"),
                organization_id: id("organization_id"),
                reason: String(values.reason),
              });
              await Promise.all([
                invalidate("admin", "users"),
                invalidate("admin", "audit"),
              ]);
              return "Change applied and audited.";
            }}
          />
        ) : (
          <section className="jm-panel">
            <h2>Select a user</h2>
            <p className="jm-muted">
              Open a user to change their role or scope.
            </p>
          </section>
        )}
      </div>
    </div>
  );
}
