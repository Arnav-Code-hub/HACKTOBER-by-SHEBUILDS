"use client";

import { useState } from "react";

import { DetailList } from "@/components/workspace-panels";
import { PageHeading, countOf } from "@/components/workspace/page-heading";
import { ActionForm } from "@/components/workspace/action-form";
import { RecordList } from "@/components/workspace/record-list";
import { useInvalidate } from "@/lib/api/hooks";
import { useApi } from "@/lib/api/use-api";
import { FacultyCouncil } from "@/features/council/components/council-panels";

import { reviewSubmission, type Submission } from "../api";
import { useInstituteSubmissions } from "../hooks";

const date = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });

const SCORES = [
  { value: "5", label: "5 — Excellent" },
  { value: "4", label: "4 — Strong" },
  { value: "3", label: "3 — Adequate" },
  { value: "2", label: "2 — Weak" },
  { value: "1", label: "1 — Not workable" },
];

/** Faculty: review solutions from teams at your own institute, once each. */
export function FacultyWorkspace() {
  const api = useApi();
  const invalidate = useInvalidate();
  const [submissionId, setSubmissionId] = useState<string | null>(null);
  const submissions = useInstituteSubmissions();
  const submission =
    submissions.data?.items.find((s) => s.id === submissionId) ?? null;

  return (
    <>
      <PageHeading
        role="Faculty"
        title="Review student solutions"
        steps={[
          "Open a submission from your institute's teams.",
          "Read the solution and follow its links.",
          "Leave one review per submission.",
        ]}
        stats={[
          {
            label: "Waiting for your review",
            value: countOf(submissions.data?.items, (s) => !s.my_review),
          },
          {
            label: "Reviewed by you",
            value: countOf(submissions.data?.items, (s) => !!s.my_review),
          },
        ]}
      >
        Solutions from teams at your institute. Each reviewer can review a
        submission once.
      </PageHeading>

      <FacultyCouncil />

      <div className="jm-panel-grid">
        <RecordList
          title="Submissions to review"
          columns={[
            {
              header: "Solution",
              cell: (s: Submission) => (
                <>
                  <strong>{s.title}</strong>
                  <br />
                  <span className="jm-small">{s.team_name}</span>
                </>
              ),
            },
            {
              header: "Submitted",
              cell: (s: Submission) => date.format(new Date(s.submitted_at)),
            },
            {
              header: "Your review",
              cell: (s: Submission) =>
                s.my_review ? (
                  <span className="jm-badge jm-tone-success">
                    Reviewed · {s.my_review.score}/5
                  </span>
                ) : (
                  <span className="jm-badge">To review</span>
                ),
            },
          ]}
          rows={submissions.data?.items}
          isLoading={submissions.isLoading}
          error={submissions.error}
          onRefresh={() => void submissions.refetch()}
          isRefreshing={submissions.isFetching}
          emptyMessage="No submissions from your institute yet."
          rowKey={(s) => s.id}
          onSelect={(s) => setSubmissionId(s.id)}
          selectedKey={submissionId}
        />

        <div className="jm-stack">
          {!submission ? (
            <section className="jm-panel">
              <h2>Select a submission</h2>
              <p className="jm-muted">
                Open a submission to read and review it.
              </p>
            </section>
          ) : (
            <>
              <section
                className="jm-panel"
                aria-label={`Submission ${submission.title}`}
              >
                <h2>{submission.title}</h2>
                <DetailList
                  items={[
                    { label: "Team", value: submission.team_name },
                    { label: "Statement", value: submission.statement_title },
                    {
                      label: "Submitted",
                      value: date.format(new Date(submission.submitted_at)),
                    },
                    {
                      label: "Link",
                      value: submission.link ? (
                        <a
                          href={submission.link}
                          rel="noopener noreferrer"
                          target="_blank"
                        >
                          {submission.link}
                        </a>
                      ) : (
                        "None"
                      ),
                    },
                  ]}
                />
                <p className="jm-report-text">{submission.summary}</p>
              </section>

              {submission.my_review ? (
                <section className="jm-panel">
                  <h2>Your review</h2>
                  <p>
                    <strong>{submission.my_review.score}/5</strong>
                  </p>
                  <p className="jm-muted">{submission.my_review.comment}</p>
                </section>
              ) : (
                <ActionForm
                  key={`review-${submission.id}`}
                  title="Review"
                  fields={[
                    {
                      name: "score",
                      label: "Score",
                      kind: "select",
                      required: true,
                      options: SCORES,
                    },
                    {
                      name: "comment",
                      label: "Feedback for the team",
                      kind: "textarea",
                      required: true,
                      maxLength: 1000,
                    },
                  ]}
                  submitLabel="Submit review"
                  confirm={() =>
                    "Submit this review? You can review each submission once."
                  }
                  onSubmit={async (values, { idempotencyKey }) => {
                    await reviewSubmission(
                      api,
                      submission.id,
                      {
                        score: Number(values.score),
                        comment: String(values.comment),
                      },
                      idempotencyKey,
                    );
                    await invalidate("submissions");
                    return "Review submitted.";
                  }}
                />
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
