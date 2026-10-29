"use client";

import { useEffect, useId, useRef, useState, type FormEvent } from "react";

import { ApiError, newIdempotencyKey } from "@/lib/api/client";
import { rupeesToPaise } from "@/lib/money";

export type FieldOption = { value: string; label: string };

export type FieldSpec = {
  name: string;
  label: string;
  kind: "text" | "textarea" | "number" | "select" | "money";
  required?: boolean;
  /**
   * Select choices. A function receives the form's current raw values, so a
   * choice can depend on another field; a selection that stops being offered
   * is cleared.
   */
  options?: FieldOption[] | ((values: Record<string, string>) => FieldOption[]);
  maxLength?: number;
  min?: number;
  max?: number;
  hint?: string;
  defaultValue?: string;
};

function optionsFor(field: FieldSpec, values: Record<string, string>) {
  return typeof field.options === "function"
    ? field.options(values)
    : (field.options ?? []);
}

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
  validate,
  onSubmit,
  disabled,
}: {
  title: string;
  description?: string;
  fields: FieldSpec[];
  submitLabel: string;
  /** When set, the action asks for confirmation with this text first. */
  confirm?: (values: FormValues) => string;
  /**
   * A check across fields, run before confirmation; a returned message is
   * shown instead of sending a request the server would refuse.
   */
  validate?: (values: FormValues) => string | null;
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
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [errorRevision, setErrorRevision] = useState(0);
  const [success, setSuccess] = useState<string | null>(null);
  const [key, setKey] = useState(newIdempotencyKey);
  const summaryRef = useRef<HTMLDivElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);
  const submitRef = useRef<HTMLButtonElement>(null);
  const successRef = useRef<HTMLParagraphElement>(null);
  const wasConfirming = useRef(false);

  useEffect(() => {
    if (pending) confirmRef.current?.focus();
    else if (wasConfirming.current) submitRef.current?.focus();
    wasConfirming.current = pending !== null;
  }, [pending]);
  // Focus only after a submission, never on every edit to an invalid field.
  useEffect(() => {
    summaryRef.current?.focus();
  }, [errorRevision]);
  useEffect(() => {
    if (success) successRef.current?.focus();
  }, [success]);

  function parse(): FormValues | null {
    const values: FormValues = {};
    const errors: Record<string, string> = {};
    for (const field of fields) {
      const value = (raw[field.name] ?? "").trim();
      try {
        if (!value) {
          if (field.required)
            throw new RangeError(`${field.label} is required.`);
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
      } catch (caught) {
        errors[field.name] =
          caught instanceof RangeError ? caught.message : "Check this field.";
      }
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length) {
      setErrorRevision((revision) => revision + 1);
      return null;
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
      setErrorRevision((revision) => revision + 1);
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || disabled || pending) return;
    setSuccess(null);
    setError(null);
    const values = parse();
    if (!values) return;
    // A check across fields, after each field is valid on its own.
    const problem = validate?.(values);
    if (problem) {
      setError(problem);
      setErrorRevision((revision) => revision + 1);
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
        {(error || Object.keys(fieldErrors).length > 0) && (
          <div
            className="jm-form-error"
            role="alert"
            tabIndex={-1}
            ref={summaryRef}
          >
            {error ? (
              <p>{error}</p>
            ) : (
              <>
                <p>Check the following fields:</p>
                <ul>
                  {Object.entries(fieldErrors).map(([name, message]) => (
                    <li key={name}>
                      <a
                        href={`#${formId}-${name}`}
                        onClick={(event) => {
                          event.preventDefault();
                          document.getElementById(`${formId}-${name}`)?.focus();
                        }}
                      >
                        {message}
                      </a>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
        {fields.map((field) => {
          const id = `${formId}-${field.name}`;
          const fieldError = fieldErrors[field.name];
          const common = {
            id,
            name: field.name,
            value: raw[field.name] ?? "",
            disabled: busy || disabled || pending !== null,
            required: field.required,
            "aria-invalid": fieldError ? true : undefined,
            "aria-describedby":
              [field.hint && `${id}-hint`, fieldError && `${id}-error`]
                .filter(Boolean)
                .join(" ") || undefined,
            onChange: (
              event: React.ChangeEvent<
                HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
              >,
            ) => {
              setRaw((previous) => {
                const next = {
                  ...previous,
                  [field.name]: event.target.value,
                };
                // A dependent choice no longer offered is cleared, never
                // submitted invisibly.
                for (const other of fields) {
                  if (
                    other.kind === "select" &&
                    typeof other.options === "function" &&
                    next[other.name] &&
                    !optionsFor(other, next).some(
                      (option) => option.value === next[other.name],
                    )
                  ) {
                    next[other.name] = "";
                  }
                }
                return next;
              });
              // Edited values are a different request, not a retry of the
              // failed one; reusing its key would be refused as a conflict.
              setKey(newIdempotencyKey());
              setSuccess(null);
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
                  {optionsFor(field, raw).map((option) => (
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
              {fieldError && (
                <p className="jm-form-error" id={`${id}-error`}>
                  {fieldError}
                </p>
              )}
            </div>
          );
        })}
        {success && (
          <p
            className="jm-form-success"
            role="status"
            tabIndex={-1}
            ref={successRef}
          >
            {success}
          </p>
        )}
        {pending && confirm ? (
          <div
            className="jm-confirm"
            role="alertdialog"
            aria-label="Confirm action"
            aria-describedby={`${formId}-confirmation`}
            onKeyDown={(event) => {
              if (event.key === "Escape" && !busy) {
                event.preventDefault();
                setPending(null);
              }
            }}
          >
            <p id={`${formId}-confirmation`}>{confirm(pending)}</p>
            <div className="jm-button-row">
              <button
                type="button"
                ref={confirmRef}
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
            ref={submitRef}
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
