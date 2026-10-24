import { describe, expect, it } from "vitest";

import { formatPaise, rupeesToPaise } from "./money";

describe("money", () => {
  it("converts typed rupees to integer paise without floating point", () => {
    expect(rupeesToPaise("150000")).toBe(15_000_000);
    expect(rupeesToPaise("1,50,000.5")).toBe(15_000_050);
    expect(rupeesToPaise("₹ 0.07")).toBe(7);
    expect(rupeesToPaise("19.99")).toBe(1999);
  });

  it("rejects zero, negatives, extra decimals and text", () => {
    for (const input of ["0", "-5", "1.234", "ten", "", "1e5"]) {
      expect(() => rupeesToPaise(input), input).toThrow(RangeError);
    }
  });

  it("formats paise as Indian-grouped rupees", () => {
    expect(formatPaise(15_000_050)).toBe("₹1,50,000.50");
    expect(formatPaise(7)).toBe("₹0.07");
  });
});
