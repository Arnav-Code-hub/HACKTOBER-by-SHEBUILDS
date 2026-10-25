import { focusManager, useQuery } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const session = vi.hoisted(() => ({
  state: { status: "signed-out" } as unknown,
}));
vi.mock("@/lib/auth/session", () => ({ useSession: () => session }));

import { QueryProvider, useScopedKey } from "./use-api";

function signedIn(id: string, role = "officer", district = "district-1") {
  session.state = {
    status: "authenticated",
    user: { uid: `firebase-${id}` },
    profile: {
      id,
      firebase_uid: `firebase-${id}`,
      role,
      display_name: id,
      email: null,
      district_id: district,
      department_id: null,
      institute_id: null,
    },
  };
}

/** Uses the same unscoped key for every account, as the reviewer's reproduction did. */
function WorkOrders({
  load,
}: {
  load: (signal: AbortSignal) => Promise<string>;
}) {
  const query = useQuery({
    queryKey: ["work-orders"],
    queryFn: ({ signal }) => load(signal),
  });
  return <p data-testid="orders">{query.data ?? "loading"}</p>;
}

function ScopedKey() {
  return <p data-testid="key">{JSON.stringify(useScopedKey("work-orders"))}</p>;
}

beforeEach(() => {
  session.state = { status: "signed-out" };
});

describe("QueryProvider account isolation", () => {
  it("never serves one account's cached records to the next", async () => {
    const load = vi.fn(async () =>
      (session.state as { profile: { id: string } }).profile.id === "a"
        ? "A's orders"
        : "B's orders",
    );
    signedIn("a");
    const { rerender } = render(
      <QueryProvider>
        <WorkOrders load={load} />
      </QueryProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("orders").textContent).toBe("A's orders"),
    );

    session.state = { status: "signed-out" };
    rerender(
      <QueryProvider>
        <WorkOrders load={load} />
      </QueryProvider>,
    );
    signedIn("b");
    rerender(
      <QueryProvider>
        <WorkOrders load={load} />
      </QueryProvider>,
    );

    expect(screen.getByTestId("orders").textContent).not.toBe("A's orders");
    await waitFor(() =>
      expect(screen.getByTestId("orders").textContent).toBe("B's orders"),
    );
    expect(load).toHaveBeenCalledTimes(3); // a, signed-out shell, b — never a cache hit across accounts
  });

  it("cancels the previous account's in-flight requests", async () => {
    const signals: AbortSignal[] = [];
    const load = vi.fn(
      (signal: AbortSignal) =>
        new Promise<string>(() => {
          signals.push(signal);
        }),
    );
    signedIn("a");
    const { rerender } = render(
      <QueryProvider>
        <WorkOrders load={load} />
      </QueryProvider>,
    );
    await waitFor(() => expect(signals).toHaveLength(1));

    signedIn("b");
    rerender(
      <QueryProvider>
        <WorkOrders load={load} />
      </QueryProvider>,
    );

    await waitFor(() => expect(signals[0]!.aborted).toBe(true));
  });

  it("treats a role or scope change for the same user as a new cache", () => {
    signedIn("a", "officer", "district-1");
    const { rerender } = render(
      <QueryProvider>
        <ScopedKey />
      </QueryProvider>,
    );
    const first = screen.getByTestId("key").textContent;
    expect(first).toContain('\\"a\\"');

    signedIn("a", "officer", "district-2");
    rerender(
      <QueryProvider>
        <ScopedKey />
      </QueryProvider>,
    );
    expect(screen.getByTestId("key").textContent).not.toBe(first);
    expect(screen.getByTestId("key").textContent).toContain("district-2");
  });

  it("refetches on every return to the window, even when data is fresh", async () => {
    let calls = 0;
    const load = vi.fn(async () => `orders v${++calls}`);
    signedIn("a");
    render(
      <QueryProvider>
        <WorkOrders load={load} />
      </QueryProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("orders").textContent).toBe("orders v1"),
    );

    // Well inside the 15 s staleTime: another role may still have changed it.
    act(() => {
      focusManager.setFocused(false);
      focusManager.setFocused(true);
    });
    await waitFor(() =>
      expect(screen.getByTestId("orders").textContent).toBe("orders v2"),
    );
    focusManager.setFocused(undefined);
  });
});
