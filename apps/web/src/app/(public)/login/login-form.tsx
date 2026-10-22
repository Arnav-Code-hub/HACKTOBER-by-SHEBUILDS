"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { SessionStatus } from "@/components/session-status";
import { dashboardDestination } from "@/lib/auth/roles";
import { authenticationError, useSession } from "@/lib/auth/session";

export function LoginForm() {
  const { state, signIn, signOut } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
    <main className="jm-page jm-login-page">
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
            Sign in to the role and district assigned to your account. Role
            access is confirmed by the JanMaang API.
          </p>
          <div className="jm-login-note">
            Citizens use the Flutter app to report problems and verify repairs.
            This workspace serves staff and partner roles.
          </div>
        </section>
        <section className="jm-panel jm-login-card">
          {state.status === "signed-out" ? (
            <>
              <span className="jm-badge">Staff & partners</span>
              <h2>Sign in</h2>
              <p className="jm-muted">
                Use a provisioned Firebase email/password account.
              </p>
              <form onSubmit={(event) => void submit(event)}>
                <label htmlFor="email">Email address</label>
                <input
                  id="email"
                  type="email"
                  autoComplete="username"
                  required
                  value={email}
                  disabled={busy}
                  onChange={(event) => setEmail(event.target.value)}
                />
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  disabled={busy}
                  onChange={(event) => setPassword(event.target.value)}
                />
                {error && (
                  <p className="jm-form-error" role="alert">
                    {error}
                  </p>
                )}
                <button className="jm-button" type="submit" disabled={busy}>
                  {busy ? "Signing in…" : "Sign in"}
                </button>
              </form>
              <p className="jm-small">
                Need access? An administrator must create your account and
                assign its backend profile.
              </p>
            </>
          ) : state.status === "authenticated" &&
            state.profile.role === "citizen" ? (
            <>
              <span className="jm-badge">Citizen account</span>
              <h2>You are signed in</h2>
              <p>
                Citizen reporting is available in the Flutter app. This account
                has no staff dashboard access.
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
