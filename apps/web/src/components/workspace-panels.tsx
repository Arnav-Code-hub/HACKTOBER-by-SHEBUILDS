import type { ReactNode } from "react";

export function DetailList({
  items,
}: {
  items: { label: string; value: ReactNode }[];
}) {
  return (
    <dl className="jm-details">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Handles real list content later without inventing records for an empty API. */
export function DataPanel({
  title,
  description,
  children,
  emptyMessage,
}: {
  title: string;
  description?: string;
  children?: ReactNode;
  emptyMessage: string;
}) {
  return (
    <section className="jm-panel">
      <h2>{title}</h2>
      {description && <p className="jm-muted">{description}</p>}
      {children ?? (
        <div className="jm-empty">
          <span className="jm-badge">Not connected</span>
          <p>{emptyMessage}</p>
        </div>
      )}
    </section>
  );
}

export function PendingAction({
  label,
  requirement,
}: {
  label: string;
  requirement: string;
}) {
  return (
    <div className="jm-pending-action">
      <div>
        <strong>{label}</strong>
        <p>{requirement}</p>
      </div>
      <span className="jm-badge">Pending</span>
    </div>
  );
}
