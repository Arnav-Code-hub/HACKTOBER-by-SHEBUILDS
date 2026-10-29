"use client";

import { useState } from "react";

import { RecordList } from "@/components/workspace/record-list";
import { ApiError } from "@/lib/api/client";
import { useApi } from "@/lib/api/use-api";
import { ROLE_LABEL } from "@/lib/auth/roles";

import { fetchOlderAudit, type AuditCursor, type AuditEvent } from "../api";
import { useAuditEvents } from "../hooks";

const dateTime = new Intl.DateTimeFormat("en-IN", {
  dateStyle: "medium",
  timeStyle: "short",
});

const MAX_CHANGES = 6;

/** "field: before → after" for each recorded field that changed. */
export function changedFields(
  before: Record<string, unknown> | null | undefined,
  after: Record<string, unknown> | null | undefined,
) {
  const keys = new Set([
    ...Object.keys(before ?? {}),
    ...Object.keys(after ?? {}),
  ]);
  const show = (value: unknown) =>
    value === undefined || value === null || value === ""
      ? "—"
      : typeof value === "object"
        ? JSON.stringify(value)
        : String(value);
  return [...keys]
    .filter((key) => show(before?.[key]) !== show(after?.[key]))
    .map((key) => ({
      key,
      from: before ? show(before[key]) : null,
      to: show(after?.[key]),
    }));
}

function Changes({ event }: { event: AuditEvent }) {
  const changes = changedFields(event.before, event.after);
  if (!changes.length) return <>—</>;
  return (
    <ul className="jm-change-list">
      {changes.slice(0, MAX_CHANGES).map((change) => (
        <li key={change.key}>
          <span className="jm-small">{change.key.replaceAll("_", " ")}</span>{" "}
          {change.from !== null && (
            <>
              <s>{change.from}</s> →{" "}
            </>
          )}
          <strong>{change.to}</strong>
        </li>
      ))}
      {changes.length > MAX_CHANGES && (
        <li className="jm-small">
          and {changes.length - MAX_CHANGES} more fields
        </li>
      )}
    </ul>
  );
}

/**
 * The audit trail, newest first. "Load older" pages back with the API's
 * cursor, so every recorded event stays reachable.
 */
export function AuditTrail() {
  const api = useApi();
  const latest = useAuditEvents();
  const [older, setOlder] = useState<AuditEvent[]>([]);
  const [cursor, setCursor] = useState<AuditCursor | null | undefined>(
    undefined,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Older pages continue from the latest page until one has been loaded.
  const next = cursor === undefined ? latest.data?.next : cursor;
  const rows = latest.data ? [...latest.data.items, ...older] : undefined;

  async function loadOlder() {
    if (!next) return;
    setLoading(true);
    setError(null);
    try {
      const page = await fetchOlderAudit(api, next);
      setOlder((previous) => [...previous, ...page.items]);
      setCursor(page.next ?? null);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Older events could not be loaded. Try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="jm-section">
      <RecordList
        title="Audit trail"
        description="Recorded actions in your scope, newest first."
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
                <span className="jm-small">{e.entity_type}</span>
              </>
            ),
          },
          { header: "Change", cell: (e: AuditEvent) => <Changes event={e} /> },
          { header: "Reason", cell: (e: AuditEvent) => e.reason ?? "—" },
        ]}
        rows={rows}
        isLoading={latest.isLoading}
        error={latest.error}
        onRefresh={() => {
          // A refresh starts again from the newest events.
          setOlder([]);
          setCursor(undefined);
          void latest.refetch();
        }}
        isRefreshing={latest.isFetching}
        emptyMessage="No actions have been recorded yet."
        rowKey={(e) => e.id}
      />
      <div className="jm-button-row jm-load-older">
        {next ? (
          <button
            type="button"
            className="jm-button jm-button-secondary"
            onClick={() => void loadOlder()}
            disabled={loading}
          >
            {loading ? "Loading older events…" : "Load older events"}
          </button>
        ) : (
          rows &&
          rows.length > 0 && (
            <p className="jm-small">
              You have reached the first recorded event.
            </p>
          )
        )}
        {error && (
          <p className="jm-form-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
