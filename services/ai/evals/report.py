"""Run eval suites and print a comparable score table.

    make evals          # inside the container
    python -m evals.report --suite classification

Makes real LLM calls. Nightly and manual only — never on the PR path.
"""

# TODO(evals): suite discovery, scoring, before/after comparison table.
