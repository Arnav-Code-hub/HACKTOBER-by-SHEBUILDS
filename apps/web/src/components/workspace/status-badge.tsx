import type { ReportStatus } from "@/lib/api/schemas";

type Tone = "neutral" | "progress" | "success" | "critical";

/** Same wording as the Flutter status chip; `verified` is Panchayat validation. */
export const STATUS_DISPLAY: Record<
  ReportStatus,
  { label: string; tone: Tone }
> = {
  reported: { label: "Reported", tone: "neutral" },
  verified: { label: "Panchayat Validated", tone: "progress" },
  rejected: { label: "Not Accepted", tone: "critical" },
  prioritised: { label: "Prioritised", tone: "progress" },
  funded: { label: "Funded", tone: "success" },
  in_progress: { label: "In Progress", tone: "progress" },
  awaiting_verification: {
    label: "Awaiting Citizen Verification",
    tone: "progress",
  },
  citizen_verified: { label: "Citizen Verified", tone: "success" },
};

export function StatusBadge({ status }: { status: ReportStatus }) {
  const { label, tone } = STATUS_DISPLAY[status];
  return <span className={`jm-badge jm-tone-${tone}`}>{label}</span>;
}
