"use client";

import { useId, useState, type FormEvent } from "react";

import { ApiError, newIdempotencyKey } from "@/lib/api/client";
import { rupeesToPaise } from "@/lib/money";

export type FieldSpec = {
  name: string;
  label: string;
  kind: "text" | "textarea" | "number" | "select" | "money";
  required?: boolean;
  options?: { value: string; label: string }[];
  maxLength?: number;
  min?: number;
  max?: number;
  hint?: string;
  defaultValue?: string;
};

/** Text and select values are strings; number fields are numbers; money is paise. */
export type FormValues = Record<string, string | number>;

export type SubmitContext = {
  /** Stable across retries of unchanged values; new after an edit or success. */
  idempotencyKey: string;
};

/**
 * One workspace action: fields, an optional confirmation step for
 * consequential writes, and the server's answer shown as-is. A failed submit
 * keeps the entered values and the same idempotency key, so a retry is the
 * same logical request.
 */
export function ActionForm({
  title,
  description,
  fields,
  submitLabel,
  confirm,
  onSubmit,
  disabled,
}: {
  title: string;
  description?: string;
  fields: FieldSpec[];
  submitLabel: string;
  /** When set, the action asks for confirmation with this text first. */
  confirm?: (values: FormValues) => string;
  /** Resolves with an optional success message. */
  onSubmit: (
    values: FormValues,
    context: SubmitContext,
  ) => Promise<string | void>;
  disabled?: boolean;
}) {
  const formId = useId();
  const initial = () =>
    Object.fromEntries(fields.map((f) => [f.name, f.defaultValue ?? ""]));
  const [raw, setRaw] = useState<Record<string, string>>(initial);
  const [pending, setPending] = useState<FormValues | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [key, setKey] = useState(newIdempotencyKey);

  function parse(): FormValues {
    const values: FormValues = {};
    for (const field of fields) {
      const value = (raw[field.name] ?? "").trim();
      if (!value) {
        if (field.required) throw new RangeError(`${field.label} is required.`);
        continue;
      }
      if (field.kind === "money") {
        values[field.name] = rupeesToPaise(value);
      } else if (field.kind === "number") {
        const number = Number(value);
        if (
          !Number.isFinite(number) ||
          (field.min !== undefined && number < field.min) ||
          (field.max !== undefined && number > field.max)
        ) {
          throw new RangeError(
            `${field.label} must be a number between ${field.min ?? "−∞"} and ${field.max ?? "∞"}.`,
          );
        }
        values[field.name] = number;
      } else {
        values[field.name] = value;
      }
    }
    return values;
  }

  async function run(values: FormValues) {
    setBusy(true);
    setError(null);
    try {
      const message = await onSubmit(values, { idempotencyKey: key });
      setSuccess(message || "Saved.");
      setRaw(initial());
      setKey(newIdempotencyKey());
      setPending(null);
    } catch (caught) {
      setPending(null);
      setError(
        // ApiError: the server's answer. RangeError: a check the caller ran
        // before sending, e.g. a link format.
        caught instanceof ApiError || caught instanceof RangeError
          ? caught.message
          : "The action could not be completed. Retry or refresh.",
      );
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setSuccess(null);
    let values: FormValues;
    try {
      values = parse();
    } catch (caught) {
      setError(
        caught instanceof RangeError ? caught.message : "Check the fields.",
      );
      return;
    }
    if (confirm) {
      setError(null);
      setPending(values);
      return;
    }
    void run(values);
  }

  return (
    <section className="jm-panel">
      <h2>{title}</h2>
      {description && <p className="jm-muted">{description}</p>}
      <form className="jm-form" onSubmit={submit} noValidate>
        {fields.map((field) => {
          const id = `${formId}-${field.name}`;
          const common = {
            id,
            name: field.name,
            value: raw[field.name] ?? "",
            disabled: busy || disabled || pending !== null,
            required: field.required,
            "aria-describedby": field.hint ? `${id}-hint` : undefined,
            onChange: (
              event: React.ChangeEvent<
                HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
              >,
            ) => {
              setRaw((previous) => ({
                ...previous,
                [field.name]: event.target.value,
              }));
              // Edited values are a different request, not a retry of the
              // failed one; reusing its key would be refused as a conflict.
              setKey(newIdempotencyKey());
            },
          };
          return (
            <div className="jm-field" key={field.name}>
              <label htmlFor={id}>
                {field.label}
                {field.kind === "money" && " (₹)"}
                {!field.required && <span className="jm-small"> optional</span>}
              </label>
              {field.kind === "textarea" ? (
                <textarea {...common} maxLength={field.maxLength} rows={3} />
              ) : field.kind === "select" ? (
                <select {...common}>
                  <option value="">Choose…</option>
                  {field.options?.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  {...common}
                  type="text"
                  inputMode={
                    field.kind === "number"
                      ? "numeric"
                      : field.kind === "money"
                        ? "decimal"
                        : undefined
                  }
                  maxLength={field.maxLength}
                />
              )}
              {field.hint && (
                <p className="jm-small" id={`${id}-hint`}>
                  {field.hint}
                </p>
              )}
            </div>
          );
        })}
        {error && (
          <p className="jm-form-error" role="alert">
            {error}
          </p>
        )}
        {success && (
          <p className="jm-form-success" role="status">
            {success}
          </p>
        )}
        {pending && confirm ? (
          <div
            className="jm-confirm"
            role="alertdialog"
            aria-label="Confirm action"
          >
            <p>{confirm(pending)}</p>
            <div className="jm-button-row">
              <button
                type="button"
                className="jm-button"
                disabled={busy}
                onClick={() => void run(pending)}
              >
                {busy ? "Saving…" : "Confirm"}
              </button>
              <button
                type="button"
                className="jm-button jm-button-secondary"
                disabled={busy}
                onClick={() => setPending(null)}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            className="jm-button"
            type="submit"
            disabled={busy || disabled}
          >
            {busy ? "Saving…" : submitLabel}
          </button>
        )}
      </form>
    </section>
  );
}
