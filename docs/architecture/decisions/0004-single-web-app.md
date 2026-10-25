# 0004. One web application with role-based routes

Date: 2026-09-06
Status: accepted

## Context

Nine web-facing roles: Student, Faculty, Institute, Gram Panchayat, Department,
Officer, Industry/CSR, Government Admin, Super Admin. (Citizens use the mobile
app; the public web surface is read-only.)

## Decision

**One Next.js application.** Roles are route groups under `(app)/`, guarded by
middleware and code-split per segment.

## Consequences

**Easier.** One auth implementation, one session refresh path, one design
system, one deploy. Roles overlap heavily — Faculty and Institute share most
screens; Officer is a narrower Department view — and shared screens stay shared.
Code-splitting means a Student never downloads the Admin bundle anyway.

**Harder.** The bundle must actually be split per segment, or the app gets
heavy. Route-level authorisation must be reliable.

**The seam we keep.** Nothing under `(app)/admin` may import from another role
segment, so Super Admin can be extracted into its own deployment if a government
security review requires network isolation.

## Alternatives considered

**Nine applications.** Rejected: nine auth implementations, nine session-refresh
bugs, nine deploy targets, and a shared-component package that becomes a release
bottleneck for a 7-person team.

**Three applications** (public / institutional / government). Rejected: it draws
a boundary where the roles do not — Panchayat sits across the institutional and
government line — and still triples the auth surface.

## Non-negotiable

`middleware.ts` is UX, not security. It runs on a browser-supplied token and
only shapes navigation. **The API authorises every read and write.** A user who
defeats the middleware gets a dashboard shell with no data in it.
