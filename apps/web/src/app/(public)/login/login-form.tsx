"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { SessionStatus } from "@/components/session-status";
import { dashboardDestination } from "@/lib/auth/roles";
import { authenticationError, useSession } from "@/lib/auth/session";

const judgeAccounts = [
  ["Panchayat", "panchayat@janmaang.example"],
  ["Department", "department@janmaang.example"],
  ["Officer", "officer@janmaang.example"],
  ["Student", "student@janmaang.example"],
  ["Institute", "institute@janmaang.example"],
  ["Faculty", "faculty@janmaang.example"],
  ["Industry / CSR", "industry@janmaang.example"],
  ["Government Admin", "gov_admin@janmaang.example"],
  ["Super Admin", "super_admin@janmaang.example"],
] as const;

export function LoginForm() {
  const { state, signIn, signOut } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const next = useSearchParams().get("next");
  useEffect(() => {
    if (state.status === "authenticated") {
      setPassword("");
      // A citizen's web home is public; show a clear message instead of looping.
      if (state.profile.role !== "citizen")
        router.replace(dashboardDestination(next, state.profile.role));
    }
  }, [state, next, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || state.status !== "signed-out") return;
    setBusy(true);
    setError(null);
    try {
      await signIn(email, password);
      setPassword("");
    } catch (caught) {
      setError(authenticationError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="jm-page jm-login-page" id="main-content" tabIndex={-1}>
      <Link className="jm-wordmark" href="/">
        JanMaang<span> / workspace</span>
      </Link>
      <div className="jm-login-grid">
        <section className="jm-login-intro">
          <p className="jm-eyebrow">From local needs to public action</p>
          <h1>
            One workspace.
            <br />A clear responsibility.
          </h1>
          <p>
            Sign in to continue work for your assigned role and district. Your
            account takes you to the right workspace.
          </p>
          <div className="jm-login-note">
            Reporting a local problem or checking a repair?{" "}
            <a
              className="jm-text-link"
              href="https://hacktober-by-she-builds.web.app"
            >
              Open citizen app
            </a>
            . This workspace is for staff and partners.
          </div>
        </section>
        <section className="jm-panel jm-login-card">
          {state.status === "signed-out" ? (
            <>
              <span className="jm-badge">Staff & partners</span>
              <h2>Sign in</h2>
              <p className="jm-muted">
                Use the email and password provided by your administrator.
              </p>
              <form onSubmit={(event) => void submit(event)} aria-busy={busy}>
                <label htmlFor="email">Email address</label>
                <input
                  id="email"
                  type="email"
                  autoComplete="username"
                  name="email"
                  aria-describedby={error ? "sign-in-error" : undefined}
                  required
                  value={email}
                  disabled={busy}
                  onChange={(event) => setEmail(event.target.value)}
                />
                <label htmlFor="password">Password</label>
                <div className="jm-password-field">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    aria-describedby={error ? "sign-in-error" : undefined}
                    required
                    value={password}
                    disabled={busy}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                  <button
                    type="button"
                    className="jm-button jm-button-secondary"
                    aria-label={
                      showPassword ? "Hide password" : "Show password"
                    }
                    aria-controls="password"
                    aria-pressed={showPassword}
                    disabled={busy}
                    onClick={() => setShowPassword((visible) => !visible)}
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
                {error && (
                  <p className="jm-form-error" id="sign-in-error" role="alert">
                    {error}
                  </p>
                )}
                <button className="jm-button" type="submit" disabled={busy}>
                  {busy ? "Signing in…" : "Sign in"}
                </button>
              </form>
              <p className="jm-small">
                Need access? Contact your organization’s administrator to set up
                your account and role.
              </p>
              <section
                className="jm-login-note jm-judge-access"
                aria-labelledby="judge-access-title"
              >
                <h3 id="judge-access-title">Judge demo access</h3>
                <p>
                  Copy an email below and use the shared password:{" "}
                  <code>123456</code>
                </p>
                <p>
                  Each account has different responsibilities and permissions.
                  Panchayat reviews complaints, Department records funding and
                  assigns work, and Officer uploads repair evidence. The other
                  accounts demonstrate academic, CSR and administration
                  workflows. Sign out before switching roles.
                </p>
                <dl className="jm-details">
                  {judgeAccounts.map(([role, email]) => (
                    <div key={email}>
                      <dt>{role}</dt>
                      <dd>
                        <code>{email}</code>
                      </dd>
                    </div>
                  ))}
                </dl>
                <p>
                  Citizen account: <code>citizen@janmaang.example</code>, same
                  password. Use it in the{" "}
                  <a
                    className="jm-text-link"
                    href="https://hacktober-by-she-builds.web.app"
                  >
                    citizen app
                  </a>
                  .
                </p>
                <p className="jm-small">
                  Shared demonstration accounts. Other judges may change their
                  demo records. Super Admin can change account access.
                </p>
              </section>
            </>
          ) : state.status === "authenticated" &&
            state.profile.role === "citizen" ? (
            <>
              <span className="jm-badge">Citizen account</span>
              <h2>You are signed in</h2>
              <p>
                Use the citizen app to report problems, track progress and
                verify repairs. Your account does not have a staff workspace.
              </p>
              <p>
                <a
                  className="jm-button"
                  href="https://hacktober-by-she-builds.web.app"
                >
                  Open citizen app
                </a>
              </p>
              <button
                className="jm-button jm-button-secondary"
                onClick={() => void signOut()}
              >
                Sign out
              </button>
            </>
          ) : state.status === "authenticated" ? (
            <p role="status">Opening your assigned workspace…</p>
          ) : (
            <SessionStatus />
          )}
        </section>
      </div>
    </main>
  );
}
