import { DetailList } from "@/components/workspace-panels";
import { StatusBadge } from "@/components/workspace/status-badge";

import type { Report } from "../api";
import { CATEGORY_LABEL, SEVERITY_LABEL, reportedOn } from "../labels";

/**
 * A citizen report as staff see it. Category and severity are the citizen's
 * (or AI's) provisional values, labelled as such — not ranking inputs.
 */
export function ReportDetail({ report }: { report: Report }) {
  return (
    <section className="jm-panel" aria-label={`Report ${report.code}`}>
      <div className="jm-evidence-heading">
        <h2>{report.title}</h2>
        <StatusBadge status={report.status} />
      </div>
      <DetailList
        items={[
          { label: "Reference", value: report.code },
          { label: "Reported", value: reportedOn(report.created_at) },
          {
            label: "Category",
            value: `${CATEGORY_LABEL[report.category]} (provisional)`,
          },
          {
            label: "Severity",
            value: `${SEVERITY_LABEL[report.severity]} (provisional)`,
          },
          { label: "Location", value: report.ward || "Not given" },
          {
            label: "Coordinates",
            value:
              report.latitude != null && report.longitude != null
                ? `${report.latitude.toFixed(5)}, ${report.longitude.toFixed(5)}`
                : "Not given",
          },
          ...(report.rejection_reason
            ? [{ label: "Reason", value: report.rejection_reason }]
            : []),
        ]}
      />
      {(report.description || report.transcript) && (
        <p className="jm-report-text">
          {report.description || report.transcript}
        </p>
      )}
      {report.media.length > 0 ? (
        <ul className="jm-photo-strip" aria-label="Citizen photos">
          {report.media.map((media) => (
            <li key={media.id}>
              <a href={media.url}>
                <img
                  src={media.thumbnail_url ?? media.url}
                  alt={`Citizen photo for ${report.code}`}
                />
              </a>
            </li>
          ))}
        </ul>
      ) : (
        <p className="jm-small">No photos were attached.</p>
      )}
    </section>
  );
}
