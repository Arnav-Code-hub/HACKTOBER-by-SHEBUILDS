"use client";

import type { ReactNode } from "react";

import { ApiError } from "@/lib/api/client";

export type Column<T> = {
  header: string;
  cell: (row: T) => ReactNode;
};

/**
 * A scoped list from the API with explicit loading, error and empty states.
 * It renders only what the API returned — an empty list says so rather than
 * showing sample rows. Shaped to take a React Query result directly.
 *
 * Writes made in another browser (another role) cannot invalidate this
 * page's cache, so every loaded list — empty or not — offers Refresh. A
 * failed background refresh keeps the rows already shown.
 */
export function RecordList<T>({
  title,
  description,
  columns,
  rows,
  isLoading,
  error,
  onRefresh,
  isRefreshing = false,
  emptyMessage,
  rowKey,
  onSelect,
  selectedKey,
}: {
  title: string;
  description?: string;
  columns: Column<T>[];
  rows: T[] | undefined;
  isLoading: boolean;
  error?: unknown;
  /** Refetches the list; shown as Refresh, or Retry after a failed load. */
  onRefresh?: () => void;
  /** True while a refetch is in flight (React Query's `isFetching`). */
  isRefreshing?: boolean;
  emptyMessage: string;
  rowKey: (row: T) => string;
  onSelect?: (row: T) => void;
  selectedKey?: string | null;
}) {
  const hasRows = Boolean(rows?.length);
  const message =
    error instanceof ApiError ? error.message : "The list could not be loaded.";
  return (
    <section className="jm-panel">
      <div className="jm-list-heading">
        <h2>{title}</h2>
        {onRefresh && !isLoading && !(error && !hasRows) && (
          <button
            type="button"
            className="jm-button jm-button-secondary jm-button-small"
            onClick={onRefresh}
            disabled={isRefreshing}
          >
            {isRefreshing ? "Refreshing…" : "Refresh"}
          </button>
        )}
      </div>
      {description && <p className="jm-muted">{description}</p>}
      {error && hasRows ? (
        <p className="jm-form-error" role="alert">
          Could not refresh: {message} Showing the last loaded list.
        </p>
      ) : null}
      {isLoading ? (
        <p className="jm-muted" role="status">
          Loading…
        </p>
      ) : error && !hasRows ? (
        <div className="jm-empty" role="alert">
          <span className="jm-badge jm-tone-critical">Could not load</span>
          <p>{message}</p>
          {onRefresh && (
            <button
              type="button"
              className="jm-button jm-button-secondary"
              onClick={onRefresh}
              disabled={isRefreshing}
            >
              {isRefreshing ? "Retrying…" : "Retry"}
            </button>
          )}
        </div>
      ) : !rows?.length ? (
        <div className="jm-empty">
          <span className="jm-badge">Nothing here</span>
          <p>{emptyMessage}</p>
        </div>
      ) : (
        <div
          className="jm-table-wrap"
          role="region"
          aria-label={`${title} records`}
          tabIndex={0}
        >
          <table className="jm-table" aria-label={title}>
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column.header} scope="col">
                    {column.header}
                  </th>
                ))}
                {onSelect && (
                  <th scope="col">
                    <span className="jm-visually-hidden">Actions</span>
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const key = rowKey(row);
                const selected = key === selectedKey;
                return (
                  <tr
                    key={key}
                    className={selected ? "is-selected" : undefined}
                  >
                    {columns.map((column) => (
                      <td key={column.header}>{column.cell(row)}</td>
                    ))}
                    {onSelect && (
                      <td className="jm-table-actions">
                        <button
                          className="jm-button jm-button-secondary jm-button-small"
                          aria-pressed={selected}
                          onClick={() => onSelect(row)}
                        >
                          {selected ? "Selected" : "Open"}
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
