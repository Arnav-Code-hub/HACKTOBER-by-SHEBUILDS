"use client";

import { useEffect, useRef, useState } from "react";

import { ActionForm } from "@/components/workspace/action-form";
import { RecordList } from "@/components/workspace/record-list";
import type { Submission } from "@/features/projects/api";
import { ApiError, newIdempotencyKey } from "@/lib/api/client";
import { useApiQuery, useInvalidate } from "@/lib/api/hooks";
import { useApi } from "@/lib/api/use-api";

import {
  assessmentDetailSchema,
  assessmentListSchema,
  assessmentSchema,
  councilConfigSchema,
  facultyListSchema,
  pdfSchema,
  supervisorSchema,
  type Assessment,
  type AssessmentDetail,
  type EvidenceFile,
} from "../api";

const date = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });
const SOURCE_EXTENSIONS =
  ".txt,.md,.csv,.py,.js,.jsx,.ts,.tsx,.dart,.java,.go,.rs,.html,.css,.sql,.json,.yaml,.yml,.c,.cpp,.h";

function useCouncilEnabled() {
  return (
    useApiQuery(["council", "config"], "council/config", councilConfigSchema)
      .data?.enabled === true
  );
}

export function SupervisorPanel({ teamId }: { teamId: string }) {
  const enabled = useCouncilEnabled();
  return enabled ? <SupervisorAssignment teamId={teamId} /> : null;
}

function SupervisorAssignment({ teamId }: { teamId: string }) {
  const api = useApi();
  const invalidate = useInvalidate();
  const faculty = useApiQuery(
    ["council", "faculty"],
    "council/faculty",
    facultyListSchema,
  );
  const supervisor = useApiQuery(
    ["council", "supervisor", teamId],
    `council/teams/${encodeURIComponent(teamId)}/supervisor`,
    supervisorSchema,
  );
  return (
    <div className="jm-section">
      <ActionForm
        key={teamId}
        title="Assign the AI Council supervisor"
        description={
          supervisor.data?.display_name
            ? `Current supervisor: ${supervisor.data.display_name}. Completed reports retain their originally assigned supervisor.`
            : "An assigned faculty member is required before students can request a council report."
        }
        fields={[
          {
            name: "faculty_id",
            label: "Supervising faculty",
            kind: "select",
            required: true,
            options: (faculty.data?.items ?? []).map((f) => ({
              value: f.id,
              label: f.display_name,
            })),
          },
        ]}
        disabled={
          faculty.isLoading ||
          !!faculty.error ||
          supervisor.isLoading ||
          !!supervisor.error
        }
        submitLabel="Assign supervisor"
        onSubmit={async (values) => {
          await api.request(
            `council/teams/${encodeURIComponent(teamId)}/supervisor`,
            {
              method: "POST",
              body: { faculty_id: values.faculty_id },
              schema: supervisorSchema,
            },
          );
          await invalidate("council", "supervisor", teamId);
          return "Supervisor assigned.";
        }}
      />
      {(faculty.error || supervisor.error) && (
        <p role="alert" className="jm-form-error">
          Could not load the supervising faculty.{" "}
          <button
            type="button"
            className="jm-button jm-button-secondary"
            onClick={() => {
              void faculty.refetch();
              void supervisor.refetch();
            }}
          >
            Retry
          </button>
        </p>
      )}
    </div>
  );
}

export function StudentCouncil({
  submissions,
}: {
  submissions: Submission[] | undefined;
}) {
  const enabled = useCouncilEnabled();
  return enabled ? (
    <div className="jm-section jm-stack">
      <CouncilRequest submissions={submissions ?? []} />
      <CouncilReports canRetry />
    </div>
  ) : null;
}

export function FacultyCouncil() {
  const enabled = useCouncilEnabled();
  return enabled ? (
    <div className="jm-section">
      <CouncilReports />
    </div>
  ) : null;
}

function CouncilRequest({ submissions }: { submissions: Submission[] }) {
  const api = useApi();
  const invalidate = useInvalidate();
  const [files, setFiles] = useState<EvidenceFile[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [reading, setReading] = useState(false);
  const request = useRef({ body: "", key: "" });

  async function readFiles(selected: FileList | null) {
    setFileError(null);
    setFiles([]);
    if (!selected) return;
    setReading(true);
    try {
      if (selected.length > 20)
        throw new RangeError("At most 20 evidence files are accepted.");
      const next: EvidenceFile[] = [];
      for (const file of Array.from(selected)) {
        const extension = "." + file.name.split(".").pop()?.toLowerCase();
        if (!SOURCE_EXTENSIONS.split(",").includes(extension))
          throw new RangeError(`Unsupported evidence file: ${file.name}`);
        if (
          !/^[A-Za-z0-9][A-Za-z0-9_. -]{0,127}$/.test(file.name) ||
          file.name.includes("..") ||
          /[ .]$/.test(file.name)
        )
          throw new RangeError(
            "Use plain filenames without folders or traversal.",
          );
        if (file.size > 200000)
          throw new RangeError(`File is too large: ${file.name}`);
        const content = new TextDecoder("utf-8", { fatal: true }).decode(
          await file.arrayBuffer(),
        );
        if (
          !content.trim() ||
          content.length > 50000 ||
          Array.from(content).some(
            (c) => c.charCodeAt(0) < 32 && !"\n\r\t".includes(c),
          )
        )
          throw new RangeError(`Invalid or oversized text file: ${file.name}`);
        next.push({ name: file.name, content });
      }
      if (new Set(next.map((f) => f.name.toLowerCase())).size !== next.length)
        throw new RangeError("Evidence filenames must be unique.");
      setFiles(next);
    } catch (error) {
      setFileError(
        error instanceof RangeError
          ? error.message
          : "Evidence must be valid UTF-8 text.",
      );
    } finally {
      setReading(false);
    }
  }

  return (
    <section className="jm-panel">
      <h2>AI Council</h2>
      <p className="jm-muted">
        Completed reports are automatically shared with your assigned
        supervising faculty. The report is advisory and does not change faculty
        grades.
      </p>
      <label>
        Supporting text and source files
        <input
          aria-label="Council evidence files"
          type="file"
          multiple
          accept={SOURCE_EXTENSIONS}
          disabled={reading}
          onChange={(e) => {
            void readFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </label>
      <p className="jm-small">
        Up to 20 UTF-8 files; 50,000 characters each; 200,000 characters total.
        Files are read as evidence and never executed.
      </p>
      {fileError && (
        <p className="jm-form-error" role="alert">
          {fileError}
          <button
            type="button"
            className="jm-button jm-button-secondary"
            onClick={() => setFileError(null)}
          >
            Clear file error
          </button>
        </p>
      )}
      {files.length > 0 && (
        <ul>
          {files.map((f) => (
            <li key={f.name}>
              {f.name}{" "}
              <button
                type="button"
                className="jm-button jm-button-secondary jm-button-small"
                aria-label={`Remove ${f.name}`}
                onClick={() => setFiles(files.filter((item) => item !== f))}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
      <ActionForm
        title="Request an AI Council critique"
        fields={[
          {
            name: "submission_id",
            label: "Student submission",
            kind: "select",
            required: true,
            options: submissions.map((s) => ({ value: s.id, label: s.title })),
          },
          {
            name: "research_question",
            label: "Research question",
            kind: "textarea",
            required: true,
            maxLength: 10000,
          },
          {
            name: "findings",
            label: "Student findings",
            kind: "textarea",
            required: true,
            maxLength: 20000,
          },
          {
            name: "methods",
            label: "Methods",
            kind: "textarea",
            maxLength: 20000,
          },
          {
            name: "results",
            label: "Results and measurements",
            kind: "textarea",
            maxLength: 20000,
          },
          {
            name: "limitations",
            label: "Known limitations",
            kind: "textarea",
            maxLength: 10000,
          },
        ]}
        submitLabel="Request council report"
        disabled={!submissions.length || reading || !!fileError}
        onSubmit={async (values) => {
          const submission = submissions.find(
            (s) => s.id === values.submission_id,
          );
          if (!submission) throw new RangeError("Choose a current submission.");
          const body = {
            title: submission.title,
            research_question: String(values.research_question),
            findings: String(values.findings),
            methods: String(values.methods ?? ""),
            results: String(values.results ?? ""),
            limitations: String(values.limitations ?? ""),
            files,
          };
          if (
            Object.values(body)
              .filter((v): v is string => typeof v === "string")
              .reduce((total, value) => total + value.length, 0) +
              files.reduce((total, f) => total + f.content.length, 0) >
            200000
          )
            throw new RangeError("Total evidence exceeds 200,000 characters.");
          const fingerprint = JSON.stringify([submission.id, body]);
          if (request.current.body !== fingerprint)
            request.current = { body: fingerprint, key: newIdempotencyKey() };
          await api.request(
            `council/submissions/${encodeURIComponent(submission.id)}/assessments`,
            {
              method: "POST",
              body,
              idempotencyKey: request.current.key,
              schema: assessmentSchema,
            },
          );
          request.current = { body: "", key: "" };
          setFiles([]);
          await invalidate("council", "assessments");
          return "Assessment queued. The completed report will be shared with the assigned faculty.";
        }}
      />
    </section>
  );
}

function CouncilReports({ canRetry = false }: { canRetry?: boolean }) {
  const api = useApi();
  const assessments = useApiQuery(
    ["council", "assessments"],
    "council/assessments",
    assessmentListSchema,
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inspected, setInspected] = useState<AssessmentDetail | null>(null);
  useEffect(() => {
    if (
      !assessments.data?.items.some((a) =>
        ["queued", "reviewing", "delivery_failed"].includes(a.status),
      )
    )
      return;
    const interval = window.setInterval(() => void assessments.refetch(), 5000);
    return () => window.clearInterval(interval);
  }, [assessments.data, assessments.refetch]);

  async function inspect(row: Assessment) {
    setBusy(row.id);
    setError(null);
    setInspected(null);
    try {
      const detail = await api.request(
        `council/assessments/${encodeURIComponent(row.id)}`,
        { schema: assessmentDetailSchema },
      );
      setInspected(detail);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Could not load the evidence snapshot.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function download(row: Assessment) {
    setBusy(row.id);
    setError(null);
    try {
      const result = await api.request(
        `council/assessments/${encodeURIComponent(row.id)}/pdf`,
        { schema: pdfSchema },
      );
      const bytes = Uint8Array.from(atob(result.content_base64), (c) =>
        c.charCodeAt(0),
      );
      if (new TextDecoder().decode(bytes.subarray(0, 5)) !== "%PDF-")
        throw new RangeError("The server did not return a PDF report.");
      const url = URL.createObjectURL(
        new Blob([bytes], { type: "application/pdf" }),
      );
      try {
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `council-${row.id}.pdf`;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
      } finally {
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    } catch (caught) {
      setError(
        caught instanceof ApiError || caught instanceof RangeError
          ? caught.message
          : "Could not download the report.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function retry(row: Assessment) {
    setBusy(row.id);
    setError(null);
    try {
      await api.request(
        `council/assessments/${encodeURIComponent(row.id)}/retry`,
        { method: "POST", schema: assessmentSchema },
      );
      await assessments.refetch();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Could not retry the assessment.",
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <RecordList<Assessment>
        title="AI Council reports"
        description="Only reports for your student teams or your assigned supervision are shown. Completed reports are available to both the student team and its assigned faculty."
        rows={assessments.data?.items}
        isLoading={assessments.isLoading}
        error={assessments.error}
        onRefresh={() => void assessments.refetch()}
        isRefreshing={assessments.isFetching}
        emptyMessage="No council reports yet."
        rowKey={(a) => a.id}
        columns={[
          {
            header: "Project",
            cell: (a) => (
              <>
                <strong>{a.title}</strong>
                <br />
                <span className="jm-small">
                  {date.format(new Date(a.created_at))}
                </span>
              </>
            ),
          },
          { header: "Supervisor", cell: (a) => a.supervisor_name },
          {
            header: "Council status",
            cell: (a) => (
              <>
                <span className="jm-badge">
                  {a.status.replaceAll("_", " ")}
                </span>
                <p className="jm-small">{a.completed_reviewers}/5 reviewers</p>
                {a.error && <p className="jm-form-error">{a.error}</p>}
              </>
            ),
          },
          {
            header: "Evidence",
            cell: (a) => (
              <button
                className="jm-button jm-button-secondary"
                disabled={busy === a.id}
                onClick={() => void inspect(a)}
              >
                Inspect evidence
              </button>
            ),
          },
          {
            header: "Report",
            cell: (a) =>
              a.status === "available" ? (
                <button
                  className="jm-button jm-button-secondary"
                  disabled={busy === a.id}
                  onClick={() => void download(a)}
                >
                  Download PDF
                </button>
              ) : a.status === "incomplete" && canRetry ? (
                <button
                  className="jm-button jm-button-secondary"
                  disabled={busy === a.id}
                  onClick={() => void retry(a)}
                >
                  Retry incomplete assessment
                </button>
              ) : (
                <span className="jm-muted">
                  {a.status === "delivery_failed"
                    ? "Delivery will retry automatically."
                    : a.status === "incomplete"
                      ? "The student team can retry this assessment."
                      : "Waiting for completion."}
                </span>
              ),
          },
        ]}
      />
      {error && (
        <p className="jm-form-error" role="alert">
          {error}
        </p>
      )}
      {inspected && <EvidenceSnapshot assessment={inspected} />}
    </div>
  );
}

function EvidenceSnapshot({ assessment }: { assessment: AssessmentDetail }) {
  const evidence = assessment.evidence;
  const sections = [
    { name: "Research question", content: evidence.research_question },
    { name: "Student findings", content: evidence.findings },
    { name: "Methods", content: evidence.methods },
    { name: "Results", content: evidence.results },
    { name: "Known limitations", content: evidence.limitations },
    ...evidence.files,
  ];
  return (
    <section
      className="jm-panel jm-section"
      aria-label="Submitted evidence snapshot"
    >
      <h2>Submitted evidence / {assessment.title}</h2>
      <p className="jm-muted">
        This is the immutable evidence for this assessment, not the latest
        project edits. Match PDF citations such as E01:L1 to the identifiers and
        line numbers below.
      </p>
      <p className="jm-small">Assessment: {assessment.id}</p>
      {sections.map((section, index) => {
        const lines = section.content.split(/\r\n|[\n\r\u0085\u2028\u2029]/);
        if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();
        return (
          <details key={index} open={index === 0}>
            <summary>
              E{String(index + 1).padStart(2, "0")} / {section.name}
            </summary>
            <pre
              className="jm-report-text"
              style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
            >
              {lines
                .map((line, number) => `L${number + 1}: ${line}`)
                .join("\n")}
            </pre>
          </details>
        );
      })}
    </section>
  );
}
