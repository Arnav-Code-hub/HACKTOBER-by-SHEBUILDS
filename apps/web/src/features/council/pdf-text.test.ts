// @vitest-environment node
import { describe, expect, it } from "vitest";

import { extractPdfText } from "./pdf-text";

/** A minimal, valid one-page PDF with one text line per entry. */
function pdfWith(lines: string[]): ArrayBuffer {
  const stream = lines
    .map((line, i) => `BT /F1 12 Tf 72 ${720 - i * 20} Td (${line}) Tj ET`)
    .join("\n");
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let body = "%PDF-1.4\n";
  const offsets: number[] = [];
  objects.forEach((object, i) => {
    offsets.push(body.length);
    body += `${i + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xref = body.length;
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  body += offsets
    .map((o) => `${String(o).padStart(10, "0")} 00000 n \n`)
    .join("");
  body += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return new TextEncoder().encode(body).buffer as ArrayBuffer;
}

describe("extractPdfText", () => {
  it("reads the PDF's text layer page by page", async () => {
    const text = await extractPdfText(
      pdfWith(["Baseline downtime: 12 hours", "After alerts: 7 hours"]),
    );
    expect(text).toContain("[Page 1]");
    expect(text).toContain("Baseline downtime: 12 hours");
    expect(text).toContain("After alerts: 7 hours");
  });

  it("refuses a PDF without selectable text", async () => {
    await expect(extractPdfText(pdfWith([]))).rejects.toThrow(
      /no selectable text/,
    );
  });

  it("refuses something that is not a PDF", async () => {
    await expect(
      extractPdfText(
        new TextEncoder().encode("not a pdf").buffer as ArrayBuffer,
      ),
    ).rejects.toBeTruthy();
  });

  it("refuses an oversized PDF before parsing", async () => {
    await expect(extractPdfText(new ArrayBuffer(10_000_001))).rejects.toThrow(
      /larger than 10 MB/,
    );
  });
});
