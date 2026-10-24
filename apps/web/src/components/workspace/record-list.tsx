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
 */
export function RecordList<T>({
  title,
  description,
  columns,
  rows,
  isLoading,
  error,
  onRetry,
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
  onRetry?: () => void;
  emptyMessage: string;
  rowKey: (row: T) => string;
  onSelect?: (row: T) => void;
  selectedKey?: string | null;
}) {
  return (
    <section className="jm-panel">
      <h2>{title}</h2>
      {description && <p className="jm-muted">{description}</p>}
      {isLoading ? (
        <p className="jm-muted" role="status">
          Loading…
        </p>
      ) : error ? (
        <div className="jm-empty" role="alert">
          <span className="jm-badge jm-tone-critical">Could not load</span>
          <p>
            {error instanceof ApiError
              ? error.message
              : "The list could not be loaded."}
          </p>
          {onRetry && (
            <button className="jm-button jm-button-secondary" onClick={onRetry}>
              Retry
            </button>
          )}
        </div>
      ) : !rows?.length ? (
        <div className="jm-empty">
          <span className="jm-badge">Nothing here</span>
          <p>{emptyMessage}</p>
        </div>
      ) : (
        <div className="jm-table-wrap">
          <table className="jm-table">
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
                      <td>
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
