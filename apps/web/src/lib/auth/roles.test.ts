import { describe, expect, it } from "vitest";

import {
  ROLES,
  ROLE_HOME,
  SEGMENT_ROLES,
  canEnter,
  dashboardDestination,
} from "./roles";

describe("role routing", () => {
  it("gives every role a landing route", () => {
    for (const role of ROLES) {
      expect(ROLE_HOME[role], `${role} has no home route`).toBeTruthy();
    }
  });

  it("lets each role into its own segment", () => {
    expect(canEnter("student", "student")).toBe(true);
    expect(canEnter("department", "department")).toBe(true);
  });

  it("keeps roles out of segments that are not theirs", () => {
    expect(canEnter("admin", "student")).toBe(false);
    expect(canEnter("department", "industry")).toBe(false);
    expect(canEnter("panchayat", "student")).toBe(false);
  });

  it("admits super_admin to oversight workspaces, not assigned officer work", () => {
    for (const segment of Object.keys(SEGMENT_ROLES)) {
      expect(canEnter(segment, "super_admin"), segment).toBe(
        segment !== "officer",
      );
    }
  });

  it("keeps assigned officer work exclusive to officers", () => {
    expect(canEnter("officer", "officer")).toBe(true);
    expect(canEnter("officer", "department")).toBe(false);
  });

  it("never routes a citizen into a web dashboard segment", () => {
    for (const segment of Object.keys(SEGMENT_ROLES)) {
      expect(canEnter(segment, "citizen"), segment).toBe(false);
    }
  });

  it("returns false for an unknown segment rather than throwing", () => {
    expect(canEnter("does-not-exist", "super_admin")).toBe(false);
  });
});

describe("login destinations", () => {
  it("preserves an authorized existing dashboard destination", () => {
    expect(dashboardDestination("/officer", "officer")).toBe("/officer");
    expect(dashboardDestination("/faculty/", "institute")).toBe("/faculty");
  });

  it("falls back to the backend-assigned role home for unauthorized routes", () => {
    expect(dashboardDestination("/admin", "student")).toBe("/student");
    expect(dashboardDestination("/officer", "citizen")).toBe("/");
    expect(dashboardDestination("/officer", "department")).toBe("/department");
    expect(dashboardDestination("/officer", "super_admin")).toBe("/admin");
    expect(dashboardDestination(null, "gov_admin")).toBe("/admin");
  });

  it.each([
    "https://attacker.example",
    "//attacker.example",
    "/\\attacker.example",
    "/%2f%2fattacker.example",
    "javascript:alert(1)",
    "/admin?next=//attacker.example",
    "/student/../../admin",
    "/missing",
    " /admin",
    "/admin\n",
    "/constructor",
    "/__proto__",
  ])("rejects unsafe or unrecognized destination %s", (destination) => {
    expect(dashboardDestination(destination, "super_admin")).toBe("/admin");
  });
});
