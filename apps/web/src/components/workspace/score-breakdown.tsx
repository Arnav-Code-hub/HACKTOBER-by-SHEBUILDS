import type { ScoreFactor } from "@/lib/api/schemas";

/**
 * The five published ranking factors behind a score. Seeded or neutral-default
 * inputs are labelled, so a demonstration value is never read as an official
 * measurement.
 */
export function ScoreBreakdown({ factors }: { factors: ScoreFactor[] }) {
  const total = factors.reduce((sum, f) => sum + f.score * f.weight, 0);
  return (
    <section className="jm-score" aria-label="Priority score breakdown">
      <p className="jm-score-total">
        Priority score <strong>{total.toFixed(1)}</strong>
        <span className="jm-small"> / 100</span>
      </p>
      <ul>
        {factors.map((factor) => (
          <li key={factor.factor}>
            <div className="jm-score-label">
              <span>
                {factor.label}{" "}
                <span className="jm-small">
                  ({Math.round(factor.weight * 100)}%)
                </span>
              </span>
              <span>
                {factor.is_demo && (
                  <span className="jm-badge jm-tone-neutral">Demo value</span>
                )}{" "}
                {Math.round(factor.score)}
              </span>
            </div>
            <div
              className="jm-score-bar"
              role="meter"
              aria-label={factor.label}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(factor.score)}
            >
              <span style={{ width: `${factor.score}%` }} />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
