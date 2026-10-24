"use client";

import { useState } from "react";

import { ActionForm } from "@/components/workspace/action-form";
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
  type AuditEvent,
  type Organization,
  type Summary,
} from "../api";
import {
  useAdminSummary,
  useAdminUsers,
  useAuditEvents,
  useOrganizations,
} from "../hooks";

const dateTime = new Intl.DateTimeFormat("en-IN", {
  dateStyle: "medium",
  timeStyle: "short",
});

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
  const audit = useAuditEvents();

  return (
    <>
      <div className="jm-page-heading">
        <span className="jm-badge">Administration</span>
        <h1>District oversight</h1>
        <p>
          Progress, recorded funding and the audit trail for your scope. Amounts
          are recorded allocations and pledges, not payments.
        </p>
      </div>

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

      <div className="jm-section">
        <RecordList
          title="Audit trail"
          description="The latest recorded actions in your scope, newest first."
          columns={[
            {
              header: "When",
              cell: (e: AuditEvent) => dateTime.format(new Date(e.at)),
            },
            {
              header: "Who",
              cell: (e: AuditEvent) => (
                <>
                  {e.actor_name}
                  <br />
                  <span className="jm-small">{ROLE_LABEL[e.actor_role]}</span>
                </>
              ),
            },
            {
              header: "Action",
              cell: (e: AuditEvent) => (
                <>
                  <code>{e.action}</code>
                  <br />
                  <span className="jm-small">
                    {e.entity_type} {e.entity_id}
                  </span>
                </>
              ),
            },
            { header: "Reason", cell: (e: AuditEvent) => e.reason ?? "—" },
          ]}
          rows={audit.data?.items}
          isLoading={audit.isLoading}
          error={audit.error}
          onRefresh={() => void audit.refetch()}
          isRefreshing={audit.isFetching}
          emptyMessage="No actions have been recorded yet."
          rowKey={(e) => e.id}
        />
      </div>

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
  const orgName = (id: string | null) =>
    id ? (orgs.find((o) => o.id === id)?.name ?? id) : "—";
  const options = (type: Organization["type"]) =>
    orgs
      .filter((o) => o.type === type)
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
              [u.district_id, u.department_id, u.institute_id]
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
            key={`role-${user.id}-${user.role}-${user.district_id}-${user.department_id}-${user.institute_id}`}
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
                options: options("district"),
              },
              {
                name: "department_id",
                label: "Department",
                kind: "select",
                defaultValue: user.department_id ?? "",
                options: options("department"),
              },
              {
                name: "institute_id",
                label: "Institute",
                kind: "select",
                defaultValue: user.institute_id ?? "",
                options: options("institute"),
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
            confirm={(values) =>
              `Change ${user.display_name || user.email || "this user"} to ${ROLE_LABEL[values.role as AdminUser["role"]]}? Their access changes on their next request, and the change is audited with your reason.`
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
