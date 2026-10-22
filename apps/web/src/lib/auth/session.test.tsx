import { act, render, screen, waitFor } from "@testing-library/react";
import type { User } from "firebase/auth";
import { beforeEach, describe, expect, it, vi } from "vitest";

const doubles = vi.hoisted(() => ({
  configuration: vi.fn(),
  tokenObserver: vi.fn(),
  browserAuth: vi.fn(),
  profile: vi.fn(),
  signIn: vi.fn(),
  signOut: vi.fn(),
}));

vi.mock("@/lib/config", () => ({ clientConfiguration: doubles.configuration }));
vi.mock("@/lib/auth/firebase", () => ({ browserAuth: doubles.browserAuth }));
vi.mock("firebase/auth", () => ({
  onIdTokenChanged: doubles.tokenObserver,
  signInWithEmailAndPassword: doubles.signIn,
  signOut: doubles.signOut,
}));
vi.mock("@/lib/api/profile", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/profile")>()),
  currentProfile: doubles.profile,
}));

import { ProfileError, type UserProfile } from "@/lib/api/profile";
import { SessionProvider, useSession } from "./session";

let observe: (user: User | null) => void;
const apiProfile: UserProfile = {
  id: "user-1",
  firebase_uid: "firebase-1",
  role: "officer",
  display_name: "Officer",
  email: "officer@example.com",
  district_id: "district-1",
  department_id: "department-1",
  institute_id: null,
};
const firebaseUser = {
  uid: "firebase-1",
  getIdToken: vi.fn().mockResolvedValue("verified-token"),
} as unknown as User;

function Probe() {
  const { state } = useSession();
  return (
    <div data-testid="session-state">
      {state.status}
      {state.status === "authenticated" ? `:${state.profile.role}` : ""}
    </div>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  doubles.configuration.mockReturnValue({
    firebase: {},
    apiOrigin: "https://api.example.com",
    problems: [],
  });
  doubles.tokenObserver.mockImplementation(
    (_auth: unknown, listener: typeof observe) => {
      observe = listener;
      listener(null);
      return vi.fn();
    },
  );
});

describe("session trust boundary", () => {
  it("requires setup without calling Firebase when public configuration is missing", async () => {
    doubles.configuration.mockReturnValue({
      firebase: {},
      apiOrigin: "",
      problems: ["Missing Firebase configuration"],
    });
    render(
      <SessionProvider>
        <Probe />
      </SessionProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("session-state").textContent).toBe("setup"),
    );
    expect(doubles.browserAuth).not.toHaveBeenCalled();
    expect(doubles.profile).not.toHaveBeenCalled();
  });

  it("does not authenticate a Firebase user until the backend profile succeeds", async () => {
    doubles.profile.mockRejectedValue(
      new ProfileError("Account not provisioned", 403),
    );
    render(
      <SessionProvider>
        <Probe />
      </SessionProvider>,
    );
    act(() => observe(firebaseUser));
    await waitFor(() =>
      expect(screen.getByTestId("session-state").textContent).toBe("error"),
    );
  });

  it("uses the backend profile role after identity confirmation", async () => {
    doubles.profile.mockResolvedValue(apiProfile);
    render(
      <SessionProvider>
        <Probe />
      </SessionProvider>,
    );
    act(() => observe(firebaseUser));
    await waitFor(() =>
      expect(screen.getByTestId("session-state").textContent).toBe(
        "authenticated:officer",
      ),
    );
  });

  it("ignores an old profile response after sign-out", async () => {
    let complete: ((profile: UserProfile) => void) | undefined;
    doubles.profile.mockReturnValue(
      new Promise<UserProfile>((resolve) => {
        complete = resolve;
      }),
    );
    render(
      <SessionProvider>
        <Probe />
      </SessionProvider>,
    );
    act(() => observe(firebaseUser));
    await waitFor(() => expect(doubles.profile).toHaveBeenCalled());
    act(() => observe(null));
    await act(async () => {
      complete?.(apiProfile);
    });
    expect(screen.getByTestId("session-state").textContent).toBe("signed-out");
  });
});
