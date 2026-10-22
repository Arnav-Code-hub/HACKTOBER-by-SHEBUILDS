import type { FirebaseOptions } from "firebase/app";

export type ClientConfiguration = {
  firebase: FirebaseOptions;
  apiOrigin: string;
  problems: string[];
};

/** NEXT_PUBLIC values are public build-time configuration, never secrets. */
export function clientConfiguration(): ClientConfiguration {
  const firebase = {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  };
  const names: Record<keyof typeof firebase, string> = {
    apiKey: "NEXT_PUBLIC_FIREBASE_API_KEY",
    authDomain: "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN",
    projectId: "NEXT_PUBLIC_FIREBASE_PROJECT_ID",
    appId: "NEXT_PUBLIC_FIREBASE_APP_ID",
    messagingSenderId: "NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID",
  };
  const problems = (Object.keys(names) as (keyof typeof names)[])
    .filter((key) => !firebase[key]?.trim())
    .map((key) => `Set ${names[key]}.`);
  const configuredOrigin = process.env.NEXT_PUBLIC_API_URL;
  let apiOrigin = "";
  try {
    apiOrigin = parseApiOrigin(configuredOrigin);
  } catch {
    problems.push(
      "Set NEXT_PUBLIC_API_URL to the API origin, for example http://localhost:8000 (without /api/v1).",
    );
  }
  return { firebase, apiOrigin, problems };
}

export function parseApiOrigin(value: string | undefined): string {
  if (!value) throw new Error("API origin is missing.");
  const url = new URL(value);
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/"
  )
    throw new Error("API URL must contain only an HTTP(S) origin.");
  if (
    url.protocol === "http:" &&
    !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)
  ) {
    throw new Error(
      "Only loopback development APIs may use HTTP. Hosted APIs require HTTPS.",
    );
  }
  return url.origin;
}
