import { getApps, initializeApp, type FirebaseOptions } from "firebase/app";
import { getAuth } from "firebase/auth";

export function browserAuth(options: FirebaseOptions) {
  // Called inside the client provider, after configuration validation.
  const app =
    getApps().find((entry) => entry.name === "janmaang-web") ??
    initializeApp(options, "janmaang-web");
  return getAuth(app);
}
