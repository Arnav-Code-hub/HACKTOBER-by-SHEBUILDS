import type { z } from "zod";

import type { categorySchema, severitySchema } from "@/lib/api/schemas";

type Category = z.infer<typeof categorySchema>;
type Severity = z.infer<typeof severitySchema>;

export const CATEGORY_LABEL: Record<Category, string> = {
  water: "Water",
  roads: "Roads",
  lighting: "Lighting",
  sanitation: "Sanitation",
  health: "Health",
  education: "Education",
  electricity: "Electricity",
  transport: "Transport",
  other: "Other",
};

export const SEVERITY_LABEL: Record<Severity, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

const date = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" });

export function reportedOn(iso: string): string {
  return date.format(new Date(iso));
}
