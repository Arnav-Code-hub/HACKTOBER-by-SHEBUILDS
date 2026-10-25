/**
 * Money is integer paise on the wire. Officials type rupees; nothing between
 * the input and the API ever holds a floating-point amount.
 */

const RUPEES = /^(\d{1,13})(?:\.(\d{1,2}))?$/;

/** Parses "1,50,000.50" or "150000" into paise. Throws on anything else. */
export function rupeesToPaise(input: string): number {
  const cleaned = input.trim().replace(/[,\s₹]/g, "");
  const match = RUPEES.exec(cleaned);
  if (!match) {
    throw new RangeError("Enter an amount in rupees, with at most 2 decimals.");
  }
  const rupees = match[1] ?? "0";
  const fraction = (match[2] ?? "").padEnd(2, "0");
  const paise = Number(rupees) * 100 + Number(fraction);
  if (!Number.isSafeInteger(paise) || paise <= 0) {
    throw new RangeError("Enter an amount greater than zero.");
  }
  return paise;
}

const formatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** Indian-grouped rupees, e.g. 15000050 → "₹1,50,000.50". */
export function formatPaise(paise: number): string {
  if (!Number.isSafeInteger(paise)) throw new RangeError("Invalid amount.");
  // Format whole rupees and paise separately so no float rounding is involved.
  const sign = paise < 0 ? "-" : "";
  const absolute = Math.abs(paise);
  const whole = formatter.format(Math.trunc(absolute / 100));
  return `${sign}${whole.slice(0, -2)}${String(absolute % 100).padStart(2, "0")}`;
}
