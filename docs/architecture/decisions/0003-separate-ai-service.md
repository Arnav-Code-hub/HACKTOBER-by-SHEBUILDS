# 0003. One separate AI service, modular by capability

Date: 2026-09-06
Status: accepted

## Context

Thirteen AI capabilities are specified: classification, deduplication, priority
ranking, statement generation, multilingual processing, translation,
speech-to-text, OCR, RAG, a civic chatbot, skill-gap analysis, student/problem
matching, before-and-after image analysis, and a multi-agent assistant.

## Decision

**One separate service** (`services/ai`), internally modularised by capability.
Not a module inside the API. Not six AI microservices.

Stateless: it owns no domain tables and never touches the business database. The
API calls it and persists the result.

Work splits by cost, not by capability:
- **Synchronous** — classification, scoring, translation, chat, matching
- **Queued through the API's worker** — OCR, speech-to-text, embedding backfill,
  image comparison, batch dedup, statement generation

## Consequences

**Easier.** The ML dependency set stays out of the API image. An OOM in image
analysis cannot take down citizen report submission. The AI service can move to
GPU nodes independently. Prompts are versioned files reviewed like code.

**Harder.** One network hop, so AI failures must degrade gracefully — a report
must still submit when classification is unavailable.

## Alternatives considered

**A module inside the API.** Rejected: `torch`/`transformers` would be
reinstalled on every API rebuild, and 2–30s LLM calls sharing a process with a
latency-sensitive API starves its worker pool.

**Six AI microservices.** Rejected: six deployments and six pipelines for one
team. Every capability shares tokenisation, language detection, embeddings and
prompt infrastructure. Extract only what proves it needs different hardware —
realistically vision and speech onto a GPU node.
