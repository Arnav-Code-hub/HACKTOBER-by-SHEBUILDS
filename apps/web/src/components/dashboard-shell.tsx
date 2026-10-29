"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { SessionStatus } from "@/components/session-status";
import {
  ROLE_HOME,
  ROLE_LABEL,
  SEGMENT_ROLES,
  canEnter,
} from "@/lib/auth/roles";
import { useSession } from "@/lib/auth/session";

const NAV_LABELS: Record<string, string> = {
  student: "Student teams",
  faculty: "Faculty reviews",
  institute: "Institute",
  panchayat: "Panchayat",
  department: "Department",
  officer: "Officer work",
  industry: "Industry / CSR",
  admin: "Administration",
};

export function DashboardShell({ children }: { children: ReactNode }) {
  const { state, signOut } = useSession();
  const pathname = usePathname();
  const router = useRouter();
  const segment = pathname.split("/")[1] ?? "";
  useEffect(() => {
    if (state.status === "signed-out") {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [state.status, pathname, router]);

  if (state.status !== "authenticated")
    return (
      <main className="jm-page" id="main-content" tabIndex={-1}>
        <Link className="jm-wordmark" href="/">
          JanMaang<span> / workspace</span>
        </Link>
        <SessionStatus />
      </main>
    );
  const { profile } = state;
  if (!canEnter(segment, profile.role)) {
    return (
      <main className="jm-page" id="main-content" tabIndex={-1}>
        <div className="jm-status" role="alert">
          <span className="jm-badge">Access denied</span>
          <h1>This workspace is outside your role</h1>
          <p>
            Your account is assigned to {ROLE_LABEL[profile.role]}. Contact an
            administrator if this is incorrect.
          </p>
          <Link className="jm-button" href={ROLE_HOME[profile.role]}>
            {profile.role === "citizen" ? "Go to home" : "Open your workspace"}
          </Link>
        </div>
      </main>
    );
  }

  return (
    <div className="jm-app-shell">
      <aside className="jm-sidebar">
        <Link className="jm-wordmark" href="/">
          JanMaang
        </Link>
        <p className="jm-eyebrow">Staff & partners</p>
        <nav aria-label="Your workspaces">
          {Object.keys(SEGMENT_ROLES)
            .filter((entry) => canEnter(entry, profile.role))
            .map((entry) => (
              <Link
                key={entry}
                href={`/${entry}` as Route}
                className={`jm-nav-link${segment === entry ? " is-active" : ""}`}
                aria-current={segment === entry ? "page" : undefined}
              >
                {NAV_LABELS[entry]}
              </Link>
            ))}
        </nav>
        <div className="jm-sidebar-note">
          Your access
          <br />
          <span>
            You see the records and actions available to your role and
            organization.
          </span>
        </div>
      </aside>
      <div className="jm-workspace">
        <header className="jm-topbar">
          <div>
            <p className="jm-eyebrow">{ROLE_LABEL[profile.role]}</p>
            <strong>
              {profile.display_name || profile.email || "JanMaang account"}
            </strong>
          </div>
          <button
            className="jm-button jm-button-secondary"
            onClick={() => void signOut()}
          >
            Sign out
          </button>
        </header>
        <main className="jm-content" id="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
