import type { ReactNode } from "react";

export type HeadingStat = {
  label: string;
  /** `undefined` while the data is loading; shown as a dash, never a guess. */
  value: ReactNode | undefined;
};

/**
 * The top of every workspace: what the page is for, the role's part in the
 * journey in three steps, and live counts from data the page already loads.
 * The coloured blocks are decoration; status and severity keep their own
 * five-tier colours.
 */
export function PageHeading({
  role,
  title,
  children,
  steps,
  stats,
}: {
  role: string;
  title: string;
  children: ReactNode;
  steps: [string, string, string];
  stats?: HeadingStat[];
}) {
  return (
    <>
      <div className="jm-page-heading">
        <div className="jm-heading-main">
          <span className="jm-badge">{role}</span>
          <h1>{title}</h1>
          <p>{children}</p>
        </div>
        <section className="jm-heading-guide" aria-label="Your part">
          <p className="jm-eyebrow">Your part</p>
          <ol>
            {steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </section>
      </div>
      {stats && stats.length > 0 && (
        <ul className="jm-stat-blocks" aria-label="At a glance">
          {stats.map((stat) => (
            <li key={stat.label}>
              <span>{stat.label}</span>
              <strong>{stat.value ?? "—"}</strong>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

/** Items in a loaded list, optionally filtered; `undefined` while loading. */
export function countOf<T>(
  items: T[] | undefined,
  keep: (item: T) => boolean = () => true,
): number | undefined {
  return items?.filter(keep).length;
}
