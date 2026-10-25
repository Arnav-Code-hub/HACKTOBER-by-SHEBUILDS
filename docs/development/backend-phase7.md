# Backend Phase 7 — optional AI report suggestions

Implemented on 25 October 2026 in the primary checkout on `test`. Local
evidence only: no Gemini key or model is configured, so no real call has been
made. Tests fake the provider.

## Delivered

- **`POST /api/v1/reports/suggest`** — citizens only (403 otherwise). The
  transcript is trimmed and must be 1–2000 characters (422). The reply is
  category, severity, title, summary, mentioned location (or `null`) and
  detected language, all suggestions the citizen can change. Nothing is
  stored, no idempotency key, no audit event.
- **Order of checks** — role, then configuration (no key or model → 503 without
  calling Gemini), then the rate limit, then one provider call.
- **Gemini adapter** (`app/integrations/gemini.py`) — one cached async client
  per key and timeout (connections are reused), retries off, the SDK timeout
  plus an `asyncio.wait_for` of `GEMINI_TIMEOUT_SECONDS` (8 s). JSON output is
  constrained by an inline schema; anything but one candidate that finished
  with `STOP` is refused. Thinking is off by default
  (`GEMINI_THINKING_BUDGET=0`) because thinking tokens count against both the
  output limit and the timeout.
- **Validation** — the reply is parsed by `ReportSuggestion` (enums, length
  limits, extra fields refused, blank values refused). Any failure, exception
  or timeout is a generic 503 that echoes no provider or model text.
- **Rate limit** — 10 suggestions per citizen per rolling minute (429), kept
  in process memory; idle users are forgotten.
- **Prompt** — `app/prompts/classify_v1.txt`, packaged with the application
  (the production image copies `app/`) and loaded with `importlib.resources`.
  The transcript is JSON-encoded between `BEGIN_UNTRUSTED_TRANSCRIPT` and
  `END_UNTRUSTED_TRANSCRIPT`; the prompt says it is data, never instructions,
  and rules out status, scores and funding.
- **Logging** — outcome, latency and user id only; never the transcript or
  the model's output.
- **Flutter** — `HttpReportRepository.analyze()` posts the trimmed transcript
  (no photos), checks every field and maps it to `ReportAnalysis`. Invalid
  values are a failure, not a crash. 503 → "Suggestions are unavailable right
  now. Enter the details yourself."; 429 → "Too many suggestion requests; wait
  a minute." Manual values still override suggestions, and demo mode is
  unchanged.

## Decisions — 25 October 2026

**Rate limit in memory, not Redis or Postgres.** Options: Redis (a new hosted
service for an optional feature), a Postgres table (a write on every call to
an endpoint that otherwise writes nothing), or a process-local window.
Choice: process-local, 10 per minute per citizen. Reason: one Render instance,
no Redis in the prototype, and the goal is to stop accidental overuse of the
Gemini quota. Trade-off: it resets on restart and each extra instance allows
its own 10. Revisit before running more than one instance.

**Citizens only.** Only the citizen app pre-fills a report from a transcript;
staff never do. Widening to another role is a one-line change.

**An inline response schema.** The schema sent to Gemini lists the enums
inline, with no `$ref`, `$defs` or `anyOf`, which providers support unevenly.
`ReportSuggestion` still validates the reply; a unit test keeps the two in
step.

**Thinking budget.** `GEMINI_THINKING_BUDGET` defaults to 0 (Flash models).
Models that cannot turn thinking off need a small positive budget (for
example 128); `-1` uses the model's dynamic default. The output limit is
1024 tokens plus the budget.

## Tests

`tests/integration/test_phase7_api.py` (real PostgreSQL, faked Gemini): the
contract shape and that no table changes; a `null` location; twelve kinds of
malformed output → 503; a slow provider → 503 within the timeout; a provider
error → 503 without its text; missing key or model → 503 with no provider
call; five non-citizen roles → 403; empty, blank, too-long and non-string
transcripts and extra fields → 422; the 11th request in a minute → 429 while
another citizen is unaffected; report creation still works while suggestions
fail.

`tests/unit/test_phase7_suggestions.py`: the prompt loads from the package;
the inline schema matches the validating model; the limiter's window and
memory; the adapter sends the delimited transcript, schema and thinking
budget through real SDK types, and refuses `MAX_TOKENS`, `SAFETY`, multiple
candidates and empty replies.

`apps/mobile/test/unit/live_suggestion_test.dart`: the request body, the
mapping, invalid fields, a missing location key, and the 503 and 429
messages.

## Not verified

- A real Gemini call: set `GEMINI_API_KEY`, `GEMINI_MODEL` and, if the model
  requires thinking, `GEMINI_THINKING_BUDGET`, then try a few transcripts in
  different languages. Check that the inline schema is accepted and replies
  come back well within 8 s.
