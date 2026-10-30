import { z } from "zod";

import { ROLES } from "@/lib/auth/roles";

const nullableId = z.string().min(1).nullable();
const profileSchema = z.object({
  id: z.string().min(1),
  firebase_uid: z.string().min(1),
  role: z.enum(ROLES),
  display_name: z.string().nullable(),
  email: z.string().email().nullable(),
  district_id: nullableId,
  department_id: nullableId,
  institute_id: nullableId,
});

export type UserProfile = z.infer<typeof profileSchema>;

export class ProfileError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ProfileError";
  }
}

export function parseProfile(value: unknown, expectedUid: string): UserProfile {
  const result = profileSchema.safeParse(value);
  if (!result.success || result.data.firebase_uid !== expectedUid) {
    throw new ProfileError(
      "The API returned an invalid or mismatched user profile. Access remains blocked.",
    );
  }
  return result.data;
}

/**
 * Waits for a sleeping free-tier API host to wake before the profile request.
 * Unauthenticated `GET /health`; no token is sent. The caller's signal bounds
 * the total wait. A waking host answers 502/503 or drops the connection for
 * up to about a minute, so attempts keep going, spaced out, until then.
 */
export async function wakeApi(
  apiOrigin: string,
  signal: AbortSignal,
  { attempts = 25, pauseMs = 3_000 } = {},
): Promise<void> {
  for (let attempt = 1; ; attempt++) {
    try {
      const response = await fetch(`${apiOrigin}/health`, {
        headers: { Accept: "application/json" },
        cache: "no-store",
        credentials: "omit",
        signal,
      });
      if (response.ok) return;
    } catch (error) {
      if (signal.aborted) throw error;
    }
    if (attempt >= attempts)
      throw new ProfileError(
        "The API is starting up or unreachable. Retry in a minute.",
      );
    await new Promise((resolve) => setTimeout(resolve, pauseMs));
  }
}

/** The token is kept in Firebase/in memory, never copied into a role cookie. */
export async function currentProfile(
  apiOrigin: string,
  token: string,
  expectedUid: string,
  signal: AbortSignal,
): Promise<UserProfile> {
  const response = await fetch(`${apiOrigin}/api/v1/users/me`, {
    headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
    cache: "no-store",
    credentials: "omit",
    signal,
  });
  if (!response.ok) {
    const message =
      response.status === 401
        ? "Your session was rejected by the API. Sign out and sign in again."
        : [403, 404].includes(response.status)
          ? "This Firebase account has no permitted JanMaang profile. Developer A must provision its role and organization."
          : "The API could not load your profile. Retry after the backend is available.";
    throw new ProfileError(message, response.status);
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ProfileError(
      "The profile endpoint did not return valid JSON. Access remains blocked.",
    );
  }
  return parseProfile(body, expectedUid);
}
