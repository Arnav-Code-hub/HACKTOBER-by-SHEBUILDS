/**
 * Role and permission definitions.
 *
 * MIRRORS services/api/app/core/permissions.py. Generated into
 * @janmaang/contracts from the API's OpenAPI schema — do not hand-edit the
 * generated copy, and do not let this file drift from the Python one.
 *
 * This is UX only. Authorisation is enforced server-side by the API, always.
 * Hiding a button is not access control.
 */

import type { Route } from "next";

export const ROLES = [
  "citizen",
  "student",
  "faculty",
  "institute",
  "panchayat",
  "department",
  "officer",
  "industry",
  "gov_admin",
  "super_admin",
] as const;

export type Role = (typeof ROLES)[number];

/** Landing route per role. The API remains the authorization boundary. */
export const ROLE_HOME: Record<Role, Route> = {
  citizen: "/", // citizens use the mobile app; the web landing is public
  student: "/student",
  faculty: "/faculty",
  institute: "/institute",
  panchayat: "/panchayat",
  department: "/department",
  officer: "/officer",
  industry: "/industry",
  gov_admin: "/admin",
  super_admin: "/admin",
};

/** Which roles may enter each route segment under (app). */
export const SEGMENT_ROLES: Record<string, readonly Role[]> = {
  student: ["student", "super_admin"],
  faculty: ["faculty", "institute", "super_admin"],
  institute: ["institute", "super_admin"],
  panchayat: ["panchayat", "gov_admin", "super_admin"],
  department: ["department", "gov_admin", "super_admin"],
  // This page uses the assigned-officer endpoint, not an oversight view.
  officer: ["officer"],
  industry: ["industry", "super_admin"],
  admin: ["gov_admin", "super_admin"],
};

export function canEnter(segment: string, role: Role): boolean {
  return (
    Object.hasOwn(SEGMENT_ROLES, segment) &&
    SEGMENT_ROLES[segment]?.includes(role) === true
  );
}

export const ROLE_LABEL: Record<Role, string> = {
  citizen: "Citizen",
  student: "Student",
  faculty: "Faculty",
  institute: "Institute",
  panchayat: "Panchayat",
  department: "Department",
  officer: "Officer",
  industry: "Industry / CSR",
  gov_admin: "Government administrator",
  super_admin: "Super administrator",
};

/** Only existing, authorized dashboard pages can be a login destination. */
export function dashboardDestination(
  candidate: string | null,
  role: Role,
): Route {
  if (candidate && /^\/[a-z_]+\/?$/.test(candidate)) {
    const segment = candidate.replace(/\/$/, "").slice(1);
    if (canEnter(segment, role)) return `/${segment}` as Route;
  }
  return ROLE_HOME[role];
}
