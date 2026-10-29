import type { Metadata } from "next";

import { QueryProvider } from "@/lib/api/use-api";
import { SessionProvider } from "@/lib/auth/session";

// Condensed display face for headings (SIL OFL 1.1), bundled with the app.
import "@fontsource/anton/400.css";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: {
    default: "JanMaang",
    template: "%s · JanMaang",
  },
  description:
    "A civic demand-to-budget platform. Report a local need, watch it get ranked, funded and verified.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <a className="jm-skip-link" href="#main-content">
          Skip to main content
        </a>
        <SessionProvider>
          <QueryProvider>{children}</QueryProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
