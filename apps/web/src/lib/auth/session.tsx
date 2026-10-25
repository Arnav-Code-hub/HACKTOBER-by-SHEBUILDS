"use client";

import { FirebaseError } from "firebase/app";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  type User,
} from "firebase/auth";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  currentProfile,
  ProfileError,
  wakeApi,
  type UserProfile,
} from "@/lib/api/profile";
import { browserAuth } from "@/lib/auth/firebase";
import { clientConfiguration } from "@/lib/config";

type SessionState =
  | { status: "loading"; message?: string }
  | { status: "setup"; problems: string[] }
  | { status: "signed-out" }
  | { status: "error"; message: string }
  | { status: "authenticated"; user: User; profile: UserProfile };

type SessionContextValue = {
  state: SessionState;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  retry: () => void;
};

const SessionContext = createContext<SessionContextValue | undefined>(
  undefined,
);

export function authenticationError(error: unknown): string {
  if (error instanceof FirebaseError) {
    switch (error.code) {
      case "auth/invalid-credential":
      case "auth/user-not-found":
      case "auth/wrong-password":
      case "auth/invalid-email":
        return "Sign-in failed. Check your email and password.";
      case "auth/too-many-requests":
        return "Too many sign-in attempts. Wait and try again.";
      case "auth/network-request-failed":
        return "Firebase could not be reached. Check your connection.";
      case "auth/operation-not-allowed":
        return "Email/password sign-in is not enabled in Firebase yet.";
      default:
        return "Firebase sign-in is unavailable. Check the project configuration and authorized domain.";
    }
  }
  return error instanceof ProfileError
    ? error.message
    : "The session could not be verified. Retry or sign out.";
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>({ status: "loading" });
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const configuration = clientConfiguration();
    if (configuration.problems.length) {
      setState({ status: "setup", problems: configuration.problems });
      return;
    }
    setState({ status: "loading" });
    let sequence = 0;
    let controller: AbortController | undefined;
    let unsubscribe: (() => void) | undefined;
    // The Firebase identity whose profile is confirmed or being confirmed.
    // A repeat callback for it must not reset the workspace.
    let currentUid: string | undefined;
    try {
      const auth = browserAuth(configuration.firebase);
      // Sign-in and sign-out only. onIdTokenChanged would also fire on the
      // hourly token refresh and unmount every open dashboard form; requests
      // fetch a fresh token with getIdToken() instead.
      unsubscribe = onAuthStateChanged(
        auth,
        (user) => {
          if (user && user.uid === currentUid) return;
          currentUid = user?.uid;
          const request = ++sequence;
          controller?.abort();
          if (!user) {
            setState({ status: "signed-out" });
            return;
          }
          setState({ status: "loading" });
          const activeController = new AbortController();
          controller = activeController;
          // Covers waking a sleeping free-tier host plus the profile request.
          const timeout = setTimeout(() => {
            activeController.abort();
            if (request === sequence) {
              setState({
                status: "error",
                message:
                  "The profile request timed out. Retry after the API is available.",
              });
            }
          }, 90_000);
          void (async () => {
            try {
              setState({
                status: "loading",
                message:
                  "Waking the server — this can take up to a minute on first load.",
              });
              await wakeApi(configuration.apiOrigin, activeController.signal);
              if (request !== sequence) return;
              setState({ status: "loading" });
              const token = await user.getIdToken();
              const profile = await currentProfile(
                configuration.apiOrigin,
                token,
                user.uid,
                activeController.signal,
              );
              if (request === sequence && !activeController.signal.aborted) {
                setState({ status: "authenticated", user, profile });
              }
            } catch (error) {
              if (request === sequence) {
                setState({
                  status: "error",
                  message: activeController.signal.aborted
                    ? "The profile request timed out. Retry after the API is available."
                    : error instanceof ProfileError
                      ? error.message
                      : error instanceof FirebaseError
                        ? authenticationError(error)
                        : "The API could not be reached. Check the API URL, CORS settings, and connection.",
                });
              }
            } finally {
              clearTimeout(timeout);
            }
          })();
        },
        (error) => {
          sequence++;
          controller?.abort();
          setState({ status: "error", message: authenticationError(error) });
        },
      );
    } catch (error) {
      setState({ status: "error", message: authenticationError(error) });
    }
    return () => {
      sequence++;
      controller?.abort();
      unsubscribe?.();
    };
  }, [revision]);

  const value: SessionContextValue = {
    state,
    async signIn(email, password) {
      const configuration = clientConfiguration();
      if (configuration.problems.length)
        throw new Error("Firebase and API setup is required first.");
      await signInWithEmailAndPassword(
        browserAuth(configuration.firebase),
        email.trim(),
        password,
      );
    },
    async signOut() {
      const configuration = clientConfiguration();
      if (!configuration.problems.length) {
        try {
          await firebaseSignOut(browserAuth(configuration.firebase));
          setState({ status: "signed-out" });
        } catch (error) {
          setState({ status: "error", message: authenticationError(error) });
        }
      }
    },
    retry: () => setRevision((previous) => previous + 1),
  };

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession(): SessionContextValue {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession requires SessionProvider.");
  return session;
}
