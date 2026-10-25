import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PageHeading, countOf } from "./page-heading";

describe("PageHeading", () => {
  it("shows the role, its three steps and live counts", () => {
    render(
      <PageHeading
        role="Panchayat"
        title="Validate reports"
        steps={["First step", "Second step", "Third step"]}
        stats={[
          { label: "To validate", value: 3 },
          { label: "In the ranking", value: undefined },
        ]}
      >
        What this page is for.
      </PageHeading>,
    );
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(
      "Validate reports",
    );
    const steps = within(screen.getByRole("region", { name: "Your part" }));
    expect(steps.getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "First step",
      "Second step",
      "Third step",
    ]);
    const glance = within(screen.getByRole("list", { name: "At a glance" }));
    expect(glance.getByText("3")).toBeTruthy();
    // A count still loading is a dash, never a guessed number.
    expect(glance.getByText("—")).toBeTruthy();
  });

  it("omits the counters when a page has none", () => {
    render(
      <PageHeading role="Admin" title="Oversight" steps={["a", "b", "c"]}>
        Body
      </PageHeading>,
    );
    expect(screen.queryByRole("list", { name: "At a glance" })).toBeNull();
  });

  it("counts loaded items and is undefined while loading", () => {
    expect(countOf(undefined)).toBeUndefined();
    expect(countOf([1, 2, 3])).toBe(3);
    expect(countOf([1, 2, 3], (n) => n > 1)).toBe(2);
  });
});
