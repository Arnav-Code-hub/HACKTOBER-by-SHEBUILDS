# Kubernetes

**Empty on purpose — do not fill this in for SIH.**

The directory exists so the decision has a home, not because you should make it
now. Managed container platforms cover this workload for a long time; Kubernetes
buys scheduling flexibility the project cannot yet use, at the price of a
control plane someone has to operate.

## Adopt when at least one is true

- Multiple services genuinely need independent horizontal scaling under load
- A government deployment mandates on-prem or a specific sovereign cloud
- The AI service needs GPU node pools with different scheduling from the API

## Planned layout

```
base/                     deployments, services, configmaps, HPAs
overlays/staging/         kustomize patches
overlays/production/      kustomize patches
```

Secrets come from the cluster's secret manager (External Secrets / CSI driver).
A `Secret` manifest is base64, not encryption — never commit one.
