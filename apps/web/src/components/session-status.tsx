"use client";

import Link from "next/link";

import { useSession } from "@/lib/auth/session";

export function SessionStatus() {
  const { state, retry, signOut } = useSession();
  if (state.status === "loading") {
    return (
      <div className="jm-status" role="status">
        <h2>Checking your session</h2>
        <p>Confirming your identity and API profile…</p>
      </div>
    );
  }
  if (state.status === "setup") {
    return (
      <div className="jm-status" role="status">
        <span className="jm-badge">Setup required</span>
        <h2>Firebase and API configuration are pending</h2>
        <p>
          The frontend is ready for configuration. Sign-in stays disabled until
          real services are configured.
        </p>
        <ul className="jm-setup-list">
          {state.problems.map((problem) => (
            <li key={problem}>{problem}</li>
          ))}
        </ul>
        <p>
          Copy <code>apps/web/.env.example</code> to <code>.env.local</code>,
          add the public configuration, and restart the web server. Hosted
          builds must be rebuilt after changing these values.
        </p>
        <p>
          No service-account, Cloudinary, or Gemini secrets belong in this
          frontend.
        </p>
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <div className="jm-status" role="alert">
        <span className="jm-badge">Access blocked</span>
        <h2>Session verification failed</h2>
        <p>{state.message}</p>
        <div className="jm-button-row">
          <button className="jm-button" onClick={retry}>
            Retry profile check
          </button>
          <button
            className="jm-button jm-button-secondary"
            onClick={() => void signOut()}
          >
            Sign out
          </button>
        </div>
      </div>
    );
  }
  return (
    <div className="jm-status">
      <h2>Sign in to your workspace</h2>
      <p>
        A verified Firebase account and a backend-assigned role are required.
      </p>
      <Link className="jm-button" href="/login">
        Sign in
      </Link>
    </div>
  );
}
