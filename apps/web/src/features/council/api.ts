import { z } from "zod";

export const councilConfigSchema = z.object({ enabled: z.boolean() });
export const supervisorSchema = z.object({
  faculty_id: z.string().min(1).nullable(),
  display_name: z.string().nullable(),
});
export const facultyListSchema = z.object({
  items: z.array(z.object({ id: z.string().min(1), display_name: z.string() })),
});
export const assessmentSchema = z.object({
  id: z.string().min(1),
  submission_id: z.string().min(1),
  title: z.string(),
  status: z.enum([
    "queued",
    "reviewing",
    "incomplete",
    "delivery_failed",
    "available",
  ]),
  completed_reviewers: z.number().int().min(0).max(5),
  created_at: z.string().datetime(),
  error: z.string().nullable(),
  supervisor_name: z.string(),
});
export type Assessment = z.infer<typeof assessmentSchema>;
export const assessmentListSchema = z.object({
  items: z.array(assessmentSchema),
});
export const pdfSchema = z.object({ content_base64: z.string().min(1) });
export type EvidenceFile = { name: string; content: string };

export const assessmentDetailSchema = assessmentSchema.extend({
  report: z.record(z.unknown()).nullable(),
  evidence: z.object({
    title: z.string(),
    research_question: z.string(),
    findings: z.string(),
    methods: z.string(),
    results: z.string(),
    limitations: z.string(),
    files: z.array(z.object({ name: z.string(), content: z.string() })),
  }),
});
export type AssessmentDetail = z.infer<typeof assessmentDetailSchema>;
