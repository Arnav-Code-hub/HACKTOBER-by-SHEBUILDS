import { Suspense } from "react";

import { LoginForm } from "./login-form";

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="jm-page" role="status" id="main-content" tabIndex={-1}>
          Loading sign-in…
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
