import { describe, expect, it, vi } from "vitest";

import { ApiError, createApiClient } from "./client";
import {
  completeUpload,
  detectImageType,
  sendToCloudinary,
  trustedUploadUrl,
  uploadPhoto,
} from "./media";

const PNG = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 0]);
const png = (name = "after.png") =>
  new File([PNG], name, { type: "image/png" });

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status });

describe("image checks", () => {
  it("detects type from content, not the file name", async () => {
    await expect(detectImageType(png("disguised.jpg"))).resolves.toBe(
      "image/png",
    );
    await expect(
      detectImageType(new File(["GIF89a......"], "a.png")),
    ).rejects.toThrow(/JPEG, PNG, or WebP/);
  });

  it("rejects empty and oversized files", async () => {
    await expect(detectImageType(new File([], "empty.png"))).rejects.toThrow(
      /10 MB/,
    );
    const big = new File([new Uint8Array(10 * 1024 * 1024 + 1)], "big.png");
    await expect(detectImageType(big)).rejects.toThrow(/10 MB/);
  });

  it("accepts only HTTPS Cloudinary upload endpoints", () => {
    expect(
      trustedUploadUrl("https://api.cloudinary.com/v1_1/demo/image/upload")
        .hostname,
    ).toBe("api.cloudinary.com");
    for (const url of [
      "http://api.cloudinary.com/v1_1/demo/image/upload",
      "https://api.cloudinary.com.evil.example/v1_1/demo/image/upload",
      "https://api.cloudinary.com/v1_1/demo/image/destroy",
      "https://api.cloudinary.com/v1_1/demo/image/upload?x=1",
    ]) {
      expect(() => trustedUploadUrl(url), url).toThrow(ApiError);
    }
  });
});

describe("signed upload", () => {
  function setup(
    uploadUrl = "https://api.cloudinary.com/v1_1/demo/image/upload",
  ) {
    const apiFetch = vi.fn(async (url: string, init: RequestInit) => {
      if (url.endsWith("/media/signature")) {
        return json({
          upload_id: "intent-1",
          upload_url: uploadUrl,
          parameters: {
            api_key: "public",
            timestamp: "1",
            signature: "sig",
            public_id: "p1",
          },
        });
      }
      expect(JSON.parse(init.body as string)).toEqual({
        upload_id: "intent-1",
        public_id: "p1",
        version: 7,
        signature: "cloud-sig",
      });
      return json({
        id: "media-1",
        url: "https://res.cloudinary.com/demo/image/upload/p1.png",
        thumbnail_url: null,
      });
    });
    const cloudinary = vi.fn(async () =>
      json({ public_id: "p1", version: 7, signature: "cloud-sig" }),
    );
    const api = createApiClient({
      apiOrigin: "https://api.example.com",
      getToken: async () => "firebase-token",
      fetcher: apiFetch as unknown as typeof fetch,
    });
    return { api, apiFetch, cloudinary };
  }

  it("signs, uploads without the Firebase token, then completes", async () => {
    const { api, apiFetch, cloudinary } = setup();
    const media = await uploadPhoto(api, png(), "completion", {
      fetcher: cloudinary as unknown as typeof fetch,
    });

    expect(media.id).toBe("media-1");
    const signature = JSON.parse(apiFetch.mock.calls[0]![1].body as string);
    expect(signature).toMatchObject({
      content_type: "image/png",
      kind: "completion",
    });

    const [url, init] = cloudinary.mock.calls[0] as unknown as [
      string,
      RequestInit,
    ];
    expect(url).toBe("https://api.cloudinary.com/v1_1/demo/image/upload");
    expect(init.headers).toBeUndefined();
    expect(init.credentials).toBe("omit");
    const form = init.body as FormData;
    expect(form.get("signature")).toBe("sig");
    expect(form.get("file")).toBeInstanceOf(File);
  });

  it("never sends the photo to an untrusted destination", async () => {
    const { api, cloudinary } = setup("https://uploads.evil.example/upload");
    await expect(
      uploadPhoto(api, png(), "report", {
        fetcher: cloudinary as unknown as typeof fetch,
      }),
    ).rejects.toThrow(/untrusted upload destination/);
    expect(cloudinary).not.toHaveBeenCalled();
  });

  it("times out a stalled Cloudinary transfer instead of hanging", async () => {
    const { api } = setup();
    const stalled = vi.fn(
      (_url: string, init: RequestInit) =>
        new Promise<Response>((_resolve, reject) =>
          init.signal?.addEventListener("abort", () =>
            reject(new DOMException("aborted", "AbortError")),
          ),
        ),
    );
    await expect(
      sendToCloudinary(api, png(), "completion", {
        fetcher: stalled as unknown as typeof fetch,
        uploadTimeoutMs: 10,
      }),
    ).rejects.toThrow(/timed out/);
  });

  it("stops a cancelled upload as a cancellation, not a failure", async () => {
    const { api } = setup();
    const controller = new AbortController();
    const stalled = vi.fn(
      (_url: string, init: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init.signal?.addEventListener("abort", () =>
            reject(new DOMException("aborted", "AbortError")),
          );
          controller.abort();
        }),
    );
    await expect(
      sendToCloudinary(api, png(), "completion", {
        fetcher: stalled as unknown as typeof fetch,
        signal: controller.signal,
      }),
    ).rejects.toMatchObject({ name: "AbortError" });
  });

  it("can complete a kept upload result without a second transfer", async () => {
    const { api, apiFetch, cloudinary } = setup();
    const pending = await sendToCloudinary(api, png(), "completion", {
      fetcher: cloudinary as unknown as typeof fetch,
    });
    await completeUpload(api, pending);
    await completeUpload(api, pending);
    expect(cloudinary).toHaveBeenCalledTimes(1);
    expect(
      apiFetch.mock.calls.filter(([url]) => url.endsWith("/media/signature")),
    ).toHaveLength(1);
  });
});
