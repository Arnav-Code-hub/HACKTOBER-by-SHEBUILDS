import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const signIn = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/lib/auth/session", () => ({
  useSession: () => ({
    state: { status: "signed-out" },
    signIn,
    signOut: vi.fn(),
  }),
  authenticationError: () => "Sign-in failed.",
}));

import { LoginForm } from "./login-form";

describe("sign-in experience", () => {
  it("can reveal and hide the same password without submitting", () => {
    render(<LoginForm />);
    const password = screen.getByLabelText("Password") as HTMLInputElement;
    fireEvent.change(password, { target: { value: "test-only-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(password.type).toBe("text");
    expect(password.value).toBe("test-only-password");
    fireEvent.click(screen.getByRole("button", { name: "Hide password" }));
    expect(password.type).toBe("password");
    expect(password.value).toBe("test-only-password");
    expect(signIn).not.toHaveBeenCalled();
    expect(
      screen
        .getByRole("link", { name: /Open citizen app/i })
        .getAttribute("href"),
    ).toBe("https://hacktober-by-she-builds.web.app");
  });
});
