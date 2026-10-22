# Glossary

**Write this early.** With nine roles and four project-shaped nouns, these terms
blur within a week, and two people using "problem" differently is a bug factory.

| Term | Means | Does not mean |
|---|---|---|
| **Demand** | One citizen's report of one local need | A cluster, or a funded item |
| **Cluster** | Multiple demands about the same physical thing, merged | A category |
| **Problem Statement** | A statement a department publishes from a ranked cluster, for students to build against | A citizen's report |
| **Project** | A student team's work against a Problem Statement | A government work order |
| **Allocation** | Money committed to a cluster | Money disbursed |
| **Disbursement** | Money actually paid out | An allocation |
| **Verification** | A citizen or officer confirming the fix is real | A status change |
| **Buildfolio** | A student's portfolio of projects and endorsements | A CV |
| **Impact** | Measured outcome after verification | Output, or activity |
| **Priority Score** | The five-factor published ranking | Severity alone |

## The lifecycle in one line

> **Demand** → clustered into a **Cluster** → ranked by **Priority Score** →
> published as a **Problem Statement** → built by a **Project** → funded via
> **Allocation** → **Disbursement** → **Verification** → **Impact**

## Naming rule

A concept keeps the **same word** everywhere:

```
problem_statement   (DB table, snake_case plural: problem_statements)
ProblemStatement    (Python / Dart / TS class)
problem-statements  (API route, kebab-case plural)
problemStatement    (TS / Dart variable)
problem_statement   (JSON payload key)
```

Renaming a concept as it crosses a language boundary is the most expensive habit
available in a polyglot repository.
