import { z } from "zod";

import { ApiError, type ApiClient } from "@/lib/api/client";
import { mediaSchema, type Media } from "@/lib/api/schemas";

/**
 * Signed Cloudinary upload, as in docs/api/day1-frontend-contract.md and the
 * Flutter HttpReportRepository:
 *
 *   POST media/signature → upload the file directly to Cloudinary with the
 *   exact signed parameters → POST media/complete → verified media record.
 *
 * The Firebase token goes only to the JanMaang API. The Cloudinary request is
 * a separate, unauthenticated fetch to a destination checked here.
 */

export const PHOTO_RULES = {
  maxPhotos: 3,
  maxBytes: 10 * 1024 * 1024,
} as const;

export type MediaKind = "report" | "completion";

const signatureSchema = z.object({
  upload_id: z.string().min(1),
  upload_url: z.string(),
  parameters: z.record(z.string()),
});

const cloudinaryResultSchema = z.object({
  public_id: z.string().min(1),
  version: z.number(),
  signature: z.string().min(1),
});

function readBytes(blob: Blob): Promise<ArrayBuffer> {
  if (typeof blob.arrayBuffer === "function") return blob.arrayBuffer();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(blob);
  });
}

/** Detects the real image type from the file's first bytes. */
export async function detectImageType(
  file: Blob,
): Promise<"image/jpeg" | "image/png" | "image/webp"> {
  if (file.size === 0 || file.size > PHOTO_RULES.maxBytes) {
    throw new RangeError("Each photo must be non-empty and at most 10 MB.");
  }
  const bytes = new Uint8Array(await readBytes(file.slice(0, 12)));
  if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff)
    return "image/jpeg";
  const png = [137, 80, 78, 71, 13, 10, 26, 10];
  if (png.every((value, index) => bytes[index] === value)) return "image/png";
  const ascii = (from: number, to: number) =>
    String.fromCharCode(...bytes.slice(from, to));
  if (ascii(0, 4) === "RIFF" && ascii(8, 12) === "WEBP") return "image/webp";
  throw new RangeError("Choose a JPEG, PNG, or WebP photo.");
}

/** Only HTTPS uploads to Cloudinary's upload API are accepted. */
export function trustedUploadUrl(value: string): URL {
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new ApiError(
      "The API returned an untrusted upload destination.",
      null,
    );
  }
  if (
    url.protocol !== "https:" ||
    url.hostname !== "api.cloudinary.com" ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    !/^\/v1_1\/[^/]+\/(image|auto)\/upload$/.test(url.pathname)
  ) {
    throw new ApiError(
      "The API returned an untrusted upload destination.",
      null,
    );
  }
  return url;
}

/** What `media/complete` needs once Cloudinary has accepted the file. */
export type PendingCompletion = {
  upload_id: string;
  public_id: string;
  version: number;
  signature: string;
};

export type UploadOptions = {
  fetcher?: typeof fetch;
  /** Cancels whichever stage is running. */
  signal?: AbortSignal;
  /** Bound on the direct Cloudinary transfer. */
  uploadTimeoutMs?: number;
};

function throwIfCancelled(signal: AbortSignal | undefined): void {
  if (signal?.aborted) {
    throw (
      signal.reason ??
      new DOMException("The upload was cancelled.", "AbortError")
    );
  }
}

/**
 * Stage 1: signature, then the direct Cloudinary transfer. The result is kept
 * by the caller, so a failed completion is retried without uploading the
 * photo again.
 */
export async function sendToCloudinary(
  api: ApiClient,
  file: File,
  kind: MediaKind,
  {
    fetcher = (...args: Parameters<typeof fetch>) => fetch(...args),
    signal,
    uploadTimeoutMs = 60_000,
  }: UploadOptions = {},
): Promise<PendingCompletion> {
  const contentType = await detectImageType(file);
  throwIfCancelled(signal);

  const signed = await api.request("media/signature", {
    method: "POST",
    body: {
      filename: file.name,
      content_type: contentType,
      bytes: file.size,
      kind,
    },
    schema: signatureSchema,
    signal,
  });
  const destination = trustedUploadUrl(signed.upload_url);
  if ("file" in signed.parameters) {
    throw new ApiError("The API returned invalid upload parameters.", null);
  }

  const form = new FormData();
  for (const [key, value] of Object.entries(signed.parameters)) {
    form.append(key, value);
  }
  form.append("file", file, file.name);

  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort);
  const timer = setTimeout(abort, uploadTimeoutMs);
  try {
    const response = await fetcher(destination.toString(), {
      method: "POST",
      body: form,
      credentials: "omit",
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`Cloudinary ${response.status}`);
    const uploaded = cloudinaryResultSchema.parse(await response.json());
    return { upload_id: signed.upload_id, ...uploaded };
  } catch {
    throwIfCancelled(signal);
    throw new ApiError(
      controller.signal.aborted
        ? "Photo upload timed out. Retry this photo."
        : "Photo upload failed. Retry this photo.",
      null,
    );
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", abort);
  }
}

/** Stage 2: the API verifies the upload and returns the media record. */
export function completeUpload(
  api: ApiClient,
  pending: PendingCompletion,
  { signal }: Pick<UploadOptions, "signal"> = {},
): Promise<Media> {
  return api.request("media/complete", {
    method: "POST",
    body: pending,
    schema: mediaSchema,
    signal,
  });
}

/** Both stages, for callers that do not need to resume. */
export async function uploadPhoto(
  api: ApiClient,
  file: File,
  kind: MediaKind,
  options: UploadOptions = {},
): Promise<Media> {
  const pending = await sendToCloudinary(api, file, kind, options);
  return completeUpload(api, pending, options);
}
