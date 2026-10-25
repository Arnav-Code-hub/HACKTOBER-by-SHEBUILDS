import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="jm-page jm-landing">
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
          JanMaang is being built to connect citizen reports, district
          priorities, funding, and citizen verification in one shared record.
        </p>
        <Link className="jm-button" href="/login">
          Open your workspace <span aria-hidden="true">→</span>
        </Link>
      </section>
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
        Day 1 development build. Staff login requires Firebase configuration and
        a provisioned API profile. Business workflows are still being connected.
      </p>
    </main>
  );
}
