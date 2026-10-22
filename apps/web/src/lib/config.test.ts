import { describe, expect, it } from "vitest";

import { parseApiOrigin } from "./config";

describe("API configuration", () => {
  it("accepts HTTPS and loopback development origins", () => {
    expect(parseApiOrigin("https://api.example.com/")).toBe(
      "https://api.example.com",
    );
    expect(parseApiOrigin("http://localhost:8000")).toBe(
      "http://localhost:8000",
    );
    expect(parseApiOrigin("http://127.0.0.1:8000")).toBe(
      "http://127.0.0.1:8000",
    );
    expect(parseApiOrigin("http://[::1]:8000")).toBe("http://[::1]:8000");
  });

  it.each([
    undefined,
    "",
    "not-a-url",
    "http://api.example.com",
    "http://localhost.attacker.example",
    "ftp://api.example.com",
    "https://user:password@api.example.com",
    "https://api.example.com/api/v1",
    "https://api.example.com?query=value",
    "https://api.example.com#fragment",
  ])("rejects ambiguous or unsafe origin %s", (origin) => {
    expect(() => parseApiOrigin(origin)).toThrow();
  });
});
