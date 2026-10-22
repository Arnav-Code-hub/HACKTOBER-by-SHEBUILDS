# Security

Covers the whole repository. Mobile and Firebase specifics are further down and
remain accurate.

## Reporting a vulnerability

Do **not** open a public issue. Email the maintainers, or open a
[private security advisory](https://docs.github.com/en/code-security/security-advisories).
Include what you found, how to reproduce it, and what it exposes. Expect an
acknowledgement within 72 hours.

## The rule

**No client ships a server-side credential.** Anything extractable from an APK or
readable in a browser bundle is public, because it is. That covers every
`NEXT_PUBLIC_*` variable and everything compiled into the Flutter app.

## Where secrets live

| Secret | Home | Never in |
|---|---|---|
| `LLM_API_KEY` | `services/ai/.env` locally; secret manager deployed | the API, the web bundle, the APK |
| `DATABASE_URL` | `services/api/.env`; secret manager deployed | any client |
| `AUTH_SECRET` | per-service `.env`; secret manager deployed | any client |
| Firebase service account | API runtime identity | git, any client |
| `AI_SERVICE_KEY` | shared by API and AI service only | any client |
| Maps **client** key | web env / mobile manifest, **referrer- and package-restricted** | — public by design, but scoped |
| Cloud deploy credentials | GitHub Environment secrets, via OIDC | git, runtime containers |

**Each service owns its own `.env`.** There is no root `.env` holding
everything — that would hand the web app the LLM key. The root `.env` carries
infrastructure values only (Postgres credentials, host ports).

## GitHub

- **Environment secrets, not repository secrets.** Repository-wide secrets are
  readable by any workflow on any branch. Use the `development`, `staging` and
  `production` Environments; `production` has required reviewers.
- **CI holds deploy credentials only.** It authenticates to the cloud by OIDC
  federation and never sees `LLM_API_KEY` or the database password — those come
  from the platform's secret manager at runtime.
- A workflow triggered by a fork PR never receives secrets. This is why the
  mobile release build is tag-triggered, not PR-triggered.

## Never commit

`.env` (only `.env.example`) · `google-services.json` ·
`GoogleService-Info.plist` · `firebase_options.dart` · any `*serviceAccount*.json`
· `*.jks` / `*.keystore` / `key.properties` · `.firebaserc` · `*.tfstate` /
`*.tfvars` · model weights · real citizen data.

All of these are in `.gitignore`. That is a safety net, not the control.

## Scanning

- **gitleaks** runs as a pre-commit hook *and* in CI. The hook alone is
  bypassable with `--no-verify`, so CI is the real gate — and it scans full
  history, because a secret committed and then reverted is still leaked.
- **CodeQL** on Python and TypeScript, every PR.
- **Dependency audit** — `pnpm audit` and `pip-audit`, weekly and on every PR.

## If you commit a secret

1. **Rotate it immediately.** Assume it is compromised.
2. Then remove it from history (`git filter-repo`) and force-push with the team
   informed.

Order matters. Removing a key from history does not un-leak it — the rotation is
what actually helps.

## Application security

- **Authorisation is server-side.** Web middleware and hidden buttons are UX.
  Every protected read and write is authorised by the API, scoped by both
  permission *and* the principal's district/department/institute.
- **The AI service is internal.** It is not publicly routable and accepts only
  the API, authenticated by a shared internal key.
- **Citizen report text is untrusted input reaching a model.** Prompts delimit it
  and instruct the model to treat it as data. A report reading "ignore previous
  instructions" is classified as a report, not obeyed. Every model output is
  schema-validated before anything persists it.
- **Citizen data is sensitive.** Reports carry location and often a face or a
  home. Precise coordinates, phone numbers and names never enter logs, eval
  datasets or demo seeds.

## Mobile and Firebase

### The rule

The Flutter app holds **no server-side credential**. Not the Gemini key, not a
service account, not a privileged Maps key. Anything that can be extracted from
an APK is treated as public, because it is.

### Where each secret lives

| Secret | Home | Reaches the app as |
|---|---|---|
| Gemini API key | Secret Manager, bound to `analyzeReport` | never — the client calls the callable |
| Firebase service account | Cloud Functions runtime identity | never |
| Google Maps SDK key | Android manifest / iOS plist, **restricted** by package name + SHA-1 and by API | a platform-restricted client key |
| Firebase client config | `firebase_options.dart` (gitignored) | public by design; Security Rules do the enforcing |

### Setting the Gemini key

```bash
firebase functions:secrets:set GEMINI_API_KEY
```

Nothing is echoed back and nothing is written to the repository. Rotate with the
same command; redeploy the functions afterwards.

### Why `firebase_options.dart` is gitignored

Firebase client config is not secret — Google documents it as safe to ship. It
is excluded anyway so a fork or a CI job cannot silently write to the production
project. Regenerate it per environment:

```bash
flutterfire configure --project=<your-project-id>
```

### What enforces access

Security Rules, not the client. `firebase/firestore.rules` blocks client writes
to `rank`, `priorityScore`, `scoreBreakdown`, `clusterId`, `supporterCount`,
`status` and `code`. A citizen can author their own report and correct its text;
they cannot move it up the queue, fund it, or mark it verified. Those paths run
only through Cloud Functions with admin credentials.

App Check is enforced on both callables so the functions are not an open Gemini
proxy.

### MCP credentials

The Stitch MCP key used to read the designs is a developer-machine credential.
It lives in the MCP client configuration, never in this repository, never in
Dart source, and never in a build artefact.
