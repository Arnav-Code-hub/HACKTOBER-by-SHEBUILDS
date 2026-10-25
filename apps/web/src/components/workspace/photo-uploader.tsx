"use client";

import { useEffect, useId, useRef, useState } from "react";

import { ApiError, type ApiClient } from "@/lib/api/client";
import {
  PHOTO_RULES,
  completeUpload,
  sendToCloudinary,
  type MediaKind,
  type PendingCompletion,
} from "@/lib/api/media";
import type { Media } from "@/lib/api/schemas";
import { useApi } from "@/lib/api/use-api";

type Item = {
  key: string;
  file: File;
  preview: string | null;
  status: "uploading" | "done" | "failed";
  media?: Media;
  error?: string;
};

function preview(file: File): string | null {
  return typeof URL.createObjectURL === "function"
    ? URL.createObjectURL(file)
    : null;
}

/**
 * Evidence photos for a staff action (for example, officer completion
 * evidence). Uploads each photo through the signed Cloudinary flow as soon as
 * it is chosen and reports only verified media to the parent.
 */
export function PhotoUploader({
  kind,
  label = "Photos",
  onChange,
  onPendingChange,
  api: apiOverride,
}: {
  kind: MediaKind;
  label?: string;
  /** Called with the verified media, in the order they were chosen. */
  onChange: (media: Media[]) => void;
  /** Called with how many photos are still uploading, so a form can wait. */
  onPendingChange?: (uploading: number) => void;
  /** Test seam; defaults to the signed-in user's API client. */
  api?: ApiClient;
}) {
  const sessionApi = useApi();
  const api = apiOverride ?? sessionApi;
  const inputId = useId();
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);
  const counter = useRef(0);
  const latest = useRef(items);
  latest.current = items;

  // Report only when the verified set changes, not on every render.
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const verifiedKey = items.map((item) => item.media?.id ?? "").join("|");
  useEffect(() => {
    onChangeRef.current(
      latest.current.flatMap((item) => (item.media ? [item.media] : [])),
    );
  }, [verifiedKey]);

  const onPendingRef = useRef(onPendingChange);
  onPendingRef.current = onPendingChange;
  const uploading = items.filter((item) => item.status === "uploading").length;
  useEffect(() => {
    onPendingRef.current?.(uploading);
  }, [uploading]);

  // One controller per running upload, and the Cloudinary result of any photo
  // whose completion failed — a retry then resumes at completion instead of
  // uploading the photo again.
  const controllers = useRef(new Map<string, AbortController>());
  const pending = useRef(new Map<string, PendingCompletion>());

  useEffect(() => {
    const running = controllers.current;
    return () => {
      for (const controller of running.values()) controller.abort();
      for (const item of latest.current)
        if (item.preview) URL.revokeObjectURL(item.preview);
    };
  }, []);

  function update(key: string, patch: Partial<Item>) {
    setItems((current) =>
      current.map((item) => (item.key === key ? { ...item, ...patch } : item)),
    );
  }

  async function start(key: string, file: File) {
    controllers.current.get(key)?.abort();
    const controller = new AbortController();
    controllers.current.set(key, controller);
    const current = () => controllers.current.get(key) === controller;
    update(key, { status: "uploading", error: undefined });
    try {
      let completion = pending.current.get(key);
      if (!completion) {
        completion = await sendToCloudinary(api, file, kind, {
          signal: controller.signal,
        });
        pending.current.set(key, completion);
      }
      const media = await completeUpload(api, completion, {
        signal: controller.signal,
      });
      pending.current.delete(key);
      if (current()) update(key, { status: "done", media });
    } catch (caught) {
      // A removed or restarted photo has a newer owner; leave it alone.
      if (!current()) return;
      update(key, {
        status: "failed",
        error: controller.signal.aborted
          ? "Upload cancelled. Retry or remove this photo."
          : caught instanceof ApiError || caught instanceof RangeError
            ? caught.message
            : "Upload failed. Retry this photo.",
      });
    } finally {
      if (current()) controllers.current.delete(key);
    }
  }

  function cancel(key: string) {
    controllers.current.get(key)?.abort();
  }

  function choose(list: FileList | null) {
    setError(null);
    const files = Array.from(list ?? []);
    if (!files.length) return;
    if (latest.current.length + files.length > PHOTO_RULES.maxPhotos) {
      setError(`Choose no more than ${PHOTO_RULES.maxPhotos} photos in total.`);
      return;
    }
    const added = files.map((file) => ({
      key: `photo-${++counter.current}`,
      file,
      preview: preview(file),
      status: "uploading" as const,
    }));
    setItems((current) => [...current, ...added]);
    for (const item of added) void start(item.key, item.file);
  }

  function remove(key: string) {
    const controller = controllers.current.get(key);
    controllers.current.delete(key);
    controller?.abort();
    pending.current.delete(key);
    setItems((current) => {
      const item = current.find((entry) => entry.key === key);
      if (item?.preview) URL.revokeObjectURL(item.preview);
      return current.filter((entry) => entry.key !== key);
    });
  }

  const full = items.length >= PHOTO_RULES.maxPhotos;
  return (
    <div className="jm-field">
      <label htmlFor={inputId}>
        {label}{" "}
        <span className="jm-small">
          JPEG, PNG or WebP · up to 10 MB each · at most {PHOTO_RULES.maxPhotos}
        </span>
      </label>
      <input
        id={inputId}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        disabled={full}
        onChange={(event) => {
          choose(event.target.files);
          event.target.value = "";
        }}
      />
      {error && (
        <p className="jm-form-error" role="alert">
          {error}
        </p>
      )}
      {items.length > 0 && (
        <ul className="jm-photo-list">
          {items.map((item) => (
            <li key={item.key}>
              {item.preview ? (
                <img src={item.preview} alt={item.file.name} />
              ) : (
                <span className="jm-photo-placeholder" aria-hidden />
              )}
              <div>
                <strong>{item.file.name}</strong>
                <p
                  className="jm-small"
                  role={item.status === "failed" ? "alert" : "status"}
                >
                  {item.status === "uploading"
                    ? "Uploading…"
                    : item.status === "done"
                      ? "Uploaded and verified"
                      : item.error}
                </p>
                <div className="jm-button-row">
                  {item.status === "uploading" && (
                    <button
                      type="button"
                      className="jm-button jm-button-secondary jm-button-small"
                      onClick={() => cancel(item.key)}
                    >
                      Cancel
                    </button>
                  )}
                  {item.status === "failed" && (
                    <button
                      type="button"
                      className="jm-button jm-button-secondary jm-button-small"
                      onClick={() => void start(item.key, item.file)}
                    >
                      Retry
                    </button>
                  )}
                  {item.status !== "uploading" && (
                    <button
                      type="button"
                      className="jm-button jm-button-secondary jm-button-small"
                      onClick={() => remove(item.key)}
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
