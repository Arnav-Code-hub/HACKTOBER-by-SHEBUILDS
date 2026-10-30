/**
 * Turns a student's PDF into plain text in the browser, so the council only
 * ever receives text evidence and never parses PDFs itself. Text is read from
 * the PDF's own text layer; scanned pages (images) have none and are refused
 * rather than guessed at.
 */

export const MAX_PDF_BYTES = 10_000_000;
export const MAX_PDF_PAGES = 50;

export async function extractPdfText(data: ArrayBuffer): Promise<string> {
  if (data.byteLength > MAX_PDF_BYTES)
    throw new RangeError("PDF is larger than 10 MB.");
  const pdfjs = await import("pdfjs-dist/legacy/build/pdf.mjs");
  // Registers pdf.js's parser on the main thread instead of a separate worker
  // file, which avoids bundler-specific worker configuration.
  await import("pdfjs-dist/legacy/build/pdf.worker.mjs");
  const document = await pdfjs.getDocument({
    data: new Uint8Array(data),
    isEvalSupported: false,
    disableFontFace: true,
    useSystemFonts: false,
    stopAtErrors: true,
  }).promise;
  try {
    if (document.numPages > MAX_PDF_PAGES)
      throw new RangeError(`PDF has more than ${MAX_PDF_PAGES} pages.`);
    const lines: string[] = [];
    for (let number = 1; number <= document.numPages; number++) {
      const page = await document.getPage(number);
      const content = await page.getTextContent();
      lines.push(`[Page ${number}]`);
      let line = "";
      for (const item of content.items) {
        if (!("str" in item)) continue;
        line += item.str;
        if (item.hasEOL) {
          lines.push(line.trimEnd());
          line = "";
        }
      }
      if (line.trim()) lines.push(line.trimEnd());
      page.cleanup();
    }
    // Control characters other than newlines would be rejected as evidence.
    const text = Array.from(lines.join("\n"))
      .filter((c) => {
        const code = c.charCodeAt(0);
        return (code >= 32 && code !== 127) || "\n\t".includes(c);
      })
      .join("")
      .replace(/\n{3,}/g, "\n\n");
    if (!text.replace(/\[Page \d+\]/g, "").trim())
      throw new RangeError(
        "This PDF has no selectable text (it may be scanned). Use a text-based PDF or paste the text instead.",
      );
    return text;
  } finally {
    await document.destroy();
  }
}
