# Demo data

The prototype demonstration fixtures are defined in `app/seeds/data.py` and
`app/seeds/loader.py`. Run `python -m app.seeds` after `alembic upgrade head`.

Every seeded row has `is_demo=true`; names/text identify synthetic cases.
`users.json` contains disabled placeholders, not working Firebase identities.
Supply real UIDs with `--users-file seeds/demo/users.local.json`; no passwords.

Use approved photos and `--photos-manifest` as described in `photos/README.md`.
Without that option, no photo or Cloudinary upload is claimed to exist.
Demo loading is refused in production. See
[`backend-phase1.md`](../../../../docs/development/backend-phase1.md) for reset
guards, provider setup and verification.
