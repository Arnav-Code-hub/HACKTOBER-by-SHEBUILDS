import Link from "next/link";

import { PublicAnalytics } from "@/features/analytics/components/public-analytics";

export default function LandingPage() {
  return (
    <main className="jm-page jm-landing" id="main-content" tabIndex={-1}>
      <header className="jm-landing-header">
        <Link className="jm-wordmark" href="/">
          JanMaang
        </Link>
        <Link className="jm-button jm-button-secondary" href="/login">
          Workspace sign-in
        </Link>
      </header>
      <section className="jm-hero">
        <p className="jm-eyebrow">Citizen needs. Accountable action.</p>
        <h1>
          A local problem deserves
          <br />a visible path to resolution.
        </h1>
        <p>
          JanMaang connects citizen reports, district priorities, funding, and
          citizen verification in one shared record.
        </p>
        <div className="jm-button-row">
          <a
            className="jm-button"
            href="https://hacktober-by-she-builds.web.app"
          >
            Report or track a problem <span aria-hidden="true">→</span>
          </a>
          <Link className="jm-button jm-button-secondary" href="/login">
            Staff & partner sign-in
          </Link>
        </div>
      </section>
      <PublicAnalytics />
      <ol className="jm-journey">
        <li>
          <span>01</span>
          <strong>Report & organize</strong>
          <p>Capture a local need and identify related reports.</p>
        </li>
        <li>
          <span>02</span>
          <strong>Prioritize & act</strong>
          <p>Review priorities, record allocations, and track work.</p>
        </li>
        <li>
          <span>03</span>
          <strong>Verify the outcome</strong>
          <p>Compare the evidence and collect a citizen's verdict.</p>
        </li>
      </ol>
      <p className="jm-small">
        JanMaang is a demonstration prototype. Sample data is labelled; recorded
        allocations and pledges do not transfer money.
      </p>
    </main>
  );
}
