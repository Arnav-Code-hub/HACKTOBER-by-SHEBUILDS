# Demo data

The SIH demonstration dataset: citizens, problems, clusters, projects, funding.

**Every record carries a provenance label.** The app renders `docs/SOURCES.md` at
`/method` and shows a provenance line beside the figures it explains — *"Synthetic
rural · Approximate location"*. A number without a source does not get displayed.

Never loaded in production. `make seed-reference` loads the reference set alone.
