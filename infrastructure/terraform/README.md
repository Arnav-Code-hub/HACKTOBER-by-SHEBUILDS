# Terraform

**Empty on purpose.** Managed containers (Cloud Run / ECS / Container Apps) will
carry JanMaang well past SIH, and writing infrastructure-as-code during a
hackathon is the most reliable way to lose two days for zero user-visible
progress.

Fill this in at the **first real deployment**, not before.

## Planned layout

```
modules/
  network/   database/   storage/   secrets/   compute/
environments/
  staging/   production/
```

## Rules for when it lands

- **State holds resolved secrets in plaintext.** Remote backend with encryption
  and locking; `*.tfstate` and `*.tfvars` are gitignored (only `*.tfvars.example`
  is committed).
- CI authenticates by OIDC federation, never a long-lived cloud key.
- `staging` and `production` are separate state files and separate projects, so
  a `terraform destroy` in the wrong terminal cannot take production with it.
