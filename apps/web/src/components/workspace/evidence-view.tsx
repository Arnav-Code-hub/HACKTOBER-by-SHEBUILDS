import { StatusBadge } from "@/components/workspace/status-badge";
import type { Evidence } from "@/lib/api/schemas";

const date = new Intl.DateTimeFormat("en-IN", {
  dateStyle: "medium",
  timeStyle: "short",
});

/**
 * Before/after evidence for one work order, plus the server-generated
 * evidence card. Matching photos support a human judgement; they are not
 * proof that a repair happened, and the page says so.
 */
export function EvidenceView({
  evidence,
  afterLabel = "After",
}: {
  evidence: Evidence;
  /**
   * Caption for the completion photo. On a correction round it is the
   * attempt the citizen returned, and must not read as the current result.
   */
  afterLabel?: string;
}) {
  return (
    <section
      className="jm-panel"
      aria-label={`Evidence for ${evidence.report_code}`}
    >
      <div className="jm-evidence-heading">
        <h2>Evidence · {evidence.report_code}</h2>
        <StatusBadge status={evidence.status} />
      </div>
      <div className="jm-evidence-grid">
        <figure>
          {evidence.before ? (
            <>
              <img
                src={evidence.before.url}
                alt={`Reported problem, ${evidence.report_code}`}
              />
              <figcaption>
                <strong>Before</strong> · reported{" "}
                {date.format(new Date(evidence.before.uploaded_at))}
              </figcaption>
            </>
          ) : (
            // Report photos are optional; never show a stand-in image.
            <div className="jm-empty">
              <span className="jm-badge">Before</span>
              <p>The citizen did not attach a photo to this report.</p>
            </div>
          )}
        </figure>
        <figure>
          {evidence.after ? (
            <>
              <img
                src={evidence.after.url}
                alt={`Completion evidence, ${evidence.report_code}`}
              />
              <figcaption>
                <strong>{afterLabel}</strong> · uploaded{" "}
                {date.format(new Date(evidence.after.uploaded_at))}
              </figcaption>
            </>
          ) : (
            <div className="jm-empty">
              <span className="jm-badge">After</span>
              <p>Completion evidence has not been uploaded yet.</p>
            </div>
          )}
        </figure>
      </div>
      {evidence.after_round && evidence.status === "in_progress" && (
        <div className="jm-correction-brief" role="note">
          <h3 className="jm-subheading">
            Why the citizen returned round {evidence.after_round}
          </h3>
          {evidence.returned_comment ? (
            <blockquote>{evidence.returned_comment}</blockquote>
          ) : (
            <p className="jm-muted">
              The citizen returned it without a comment. Compare the photos with
              the original report.
            </p>
          )}
        </div>
      )}
      <p className="jm-notice">
        Evidence for human review — matching photos are not proof that a repair
        happened. Only the original reporter&rsquo;s verdict marks a case
        citizen verified.
      </p>
      {evidence.card_url && (
        <figure className="jm-evidence-card">
          <img
            src={evidence.card_url}
            alt={`Evidence card for ${evidence.report_code}`}
          />
          <figcaption className="jm-small">
            Generated evidence card · status when generated ·{" "}
            <a href={evidence.card_url}>Open full size</a>
          </figcaption>
        </figure>
      )}
    </section>
  );
}
