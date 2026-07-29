# ArgoCD Structure

## Pattern: App-of-Apps + ApplicationSet

```
gitops-pipeline-root (Application, app-of-apps)
  └── applies argocd/applicationset.yaml
        └── ApplicationSet (list generator, goTemplate mode)
              ├── gitops-pipeline-dev      (Application, auto-sync + self-heal)
              └── gitops-pipeline-staging  (Application, manual sync)
```

## Why this shape

- **One root object to manage.** You only ever `kubectl apply` the root
  Application once. Everything else — the ApplicationSet, and the
  per-environment Applications it generates — is owned and reconciled by
  ArgoCD from that point on.
- **ApplicationSet avoids copy-pasted Application manifests.** Adding a
  third environment later is one new element in the `list` generator, not
  a new YAML file.
- **goTemplate mode** is what lets dev and staging diverge on sync policy
  from a single template (see the `{{- if .autoSync }}` block in
  `applicationset.yaml`) — plain-mode ApplicationSet templating can't do
  conditionals.

## Sync Policies

| Environment | Policy | Why |
|---|---|---|
| dev | `automated: { prune: true, selfHeal: true }` | Fast iteration — CI pushes, dev reflects it within ArgoCD's default 3-min poll (or immediately via webhook) |
| staging | No `automated` block — sync is manual | Only triggered by the CI `promote:manual-gate` job after cosign signature verification passes. Prevents unreviewed images reaching the canary environment. |

`CreateNamespace=true` is set on both so first-time sync doesn't fail on
missing `gitops-dev` / `gitops-staging` namespaces (also pre-created
directly in `applicationset.yaml` as a belt-and-suspenders measure, since
NetworkPolicy namespaceSelectors need the namespace label present).

## Setup on minikube

```bash
# 1. Install ArgoCD (if not already running in the cluster)
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 2. Apply the root Application
kubectl apply -f argocd/app-of-apps.yaml -n argocd

# 3. Verify
argocd app list
argocd app get gitops-pipeline-root
argocd app get gitops-pipeline-dev
argocd app get gitops-pipeline-staging
```

## Promoting to staging manually (until CI wiring lands in Stage 7)

```bash
argocd app sync gitops-pipeline-staging
```

## Repo URL placeholder

`repoURL` in both `applicationset.yaml` and `app-of-apps.yaml` is set to
`https://gitlab.com/CHANGE_ME/gitops-pipeline.git`. Replace `CHANGE_ME`
with your actual GitLab namespace once the repo is pushed (Stage 9).
