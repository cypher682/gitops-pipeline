# gitops-pipeline

**GitOps delivery pipeline — GitLab CI/CD → Argo CD → Argo Rollouts canary with Prometheus analysis.**

Push to `main` and the pipeline lints, builds, tests, scans, **keyless-signs** and pushes a container
image, updates the GitOps state in this repo, syncs the `dev` environment, and — after a human
approval gate and a Cosign signature re-verification — promotes it through a **staging canary**
(10% → Prometheus-gated → 50% → Prometheus-gated → 100%) that aborts automatically on error-rate
spikes. Secrets remain **SOPS-encrypted in git** and are decrypted at apply time by an Argo CD
ConfigManagementPlugin.

Domain: Platform engineering — CI/CD, GitOps, progressive delivery, software supply chain.

---

## Pipeline

```
validate → build → test → scan → sign → push → deploy-dev → promote → deploy-staging
```

| Stage | What runs |
|---|---|
| `validate` | app lint, Dockerfile lint (Hadolint), k8s manifest lint |
| `build` | Docker-in-Docker image build, pushed to the GitLab Container Registry |
| `test` | unit, integration, coverage gate |
| `scan` | Trivy (container), Semgrep (SAST), dependency audit, SOPS-detect |
| `sign` | Cosign **keyless** (Sigstore) signing via GitLab OIDC + Syft SBOM + SBOM attestation |
| `push` | tag `latest` + **values bump** — CI commits the new image tag into `helm/app-chart/values.yaml` |
| `deploy-dev` | `argocd app sync gitops-pipeline-dev` → smoke-test `/health` over a tunnel |
| `promote` | manual approval gate (staging environment) → Cosign verify re-check |
| `deploy-staging` | `argocd app sync gitops-pipeline-staging` → canary until fully healthy |

## Architecture

```
            ┌──────────────────────────────────────────────────────────┐
 git push   │  GitLab CI/CD (22 jobs, 9 stages)                         │
 ─────────► │  lint → build → test → scan → sign → push                 │
            │    └─ push:update-gitops-values commits new image.tag     │
            └──────────────────────────────┬────────────────────────────┘
                                           │ (git push of the bump commit)
                                           ▼
          Argo CD (minikube) — repo = desired state
 ┌─────────────────────────────────────────────────────────────────────┐
 │  gitops-pipeline-root (app-of-apps, argocd/ dir)                     │
 │    └─ ApplicationSet → gitops-pipeline-dev | gitops-pipeline-staging │
 │       repo: "." + plugin.env.VALUES_FILE (CMP: helm + SOPS decrypt)  │
 └───────┬────────────────────────────────┬─────────────────────────────┘
         │ CI-driven                      │ manual-gate only
         ▼                                ▼
   gitops-dev (Rollout)            gitops-staging (Rollout, canary)
   health / smoke test             10% → pause → AnalysisRun → 50% → pause → AnalysisRun → 100%
                                            │
                                            ▼
                                     Prometheus (observability ns)
                                     app_error_rate{job="app-chart-staging"} <= 0.05
```

## Environments & promotion model

| Env | Namespace | Replicas | Rollout strategy | Sync | Triggered by |
|---|---|---|---|---|---|
| `dev` | `gitops-dev` | 1–3 (HPA) | single-step (100%) | manual (CI-driven) | every commit |
| `staging` | `gitops-staging` | 2–6 (HPA) | canary 10 → 50 → 100 + Prometheus analysis | manual (gated) | human approval + Cosign verify |

## Tech stack

| Area | Tools |
|---|---|
| CI/CD | GitLab CI/CD (9 stages, DAG `needs:`, protected env, masked vars) |
| Container image | Python/FastAPI app, multi-stage Dockerfile, GitLab Container Registry |
| Security & supply chain | Trivy, Semgrep, pip-audit, **Cosign keyless (Sigstore)**, Syft SBOM, attestation |
| GitOps | **Argo CD** ApplicationSet + app-of-apps; **SOPS (age)** + CMP sidecar |
| Progressive delivery | **Argo Rollouts** Rollout CRD + AnalysisTemplate |
| Observability (canary) | Prometheus scraping both envs' `/metrics` |
| Deployment target | minikube (Docker driver), kubectl, kustomize-agnostic (Helm-native) |
| Reachability | ngrok + cloudflared tunnels (hosted runners → local cluster) |

## Repository layout

```
gitops-pipeline/
├── .gitlab-ci.yml                # full pipeline (validate → … → deploy-staging)
├── app/                          # FastAPI sample app: /health, /metrics (app_error_rate)
├── Dockerfile                    # app image
├── helm/app-chart/               # single chart, three value sets
│   ├── values.yaml               #    base — incl. image tag (CI bumps it)
│   ├── values-dev.yaml           #    dev — 1 replica, single-step rollout
│   ├── values-staging.yaml       #    staging — 2 replicas, canary + analysis
│   └── templates/                #    rollout, analysis-template, service, hpa,
│                                 #    ingress, networkpolicy, rbac, helpers
├── secrets/app-secrets.enc.yaml  # SOPS (age)-encrypted secret
├── .sops.yaml                    # SOPS rules (encrypted_regex)
├── argocd/                       # self-managed GitOps config (app-of-apps)
│   ├── application.yaml          #    root Application (auto-sync + prune)
│   ├── applicationset.yaml       #    generates dev + staging Applications
│   ├── sops-plugin.yaml          #    CMP: helm render + sops decrypt
│   ├── sops-plugin-patch.yaml    #    repo-server sidecar injection
│   └── cmp-sidecar/              #    sidecar image (alpine/helm + sops)
├── observability/prometheus.yaml # minimal Prometheus for canary analysis
├── rollouts/                     # reference copies (chart is the source of truth)
├── docs/                         # setup, structure, evidence checklist
└── README.md
```

## Key implementation decisions

- **The repo is the source of truth for the cluster.** The same repository carries the app, its CI,
  its Helm chart, the Argo CD config, and the encrypted secrets. Argo CD reconciles dev/staging to it;
  rollback = `git revert`.
- **ApplicationSet generation** instead of duplicate Application manifests — a single template stamps
  out `dev` and `staging`, differing only by the values file (`plugin.env.VALUES_FILE`).
- **CMP decrypt-at-apply secrets** — SOPS + age keep plaintext out of git; the ConfigManagementPlugin
  renders `helm template` and appends `sops --decrypt` output, normalising the namespace to each app's
  destination at render time.
- **Keyless signing with SIgstore** — no key pairs to rotate; the CI job's GitLab OIDC identity is
  bound to the signature and auditable via the Rekor transparency log.
- **Signature re-verification before staging**, not just at build time, followed by a
  Prometheus-gated canary so a bad release rolls back by itself instead of reaching users.
- **Tunnel-based reachability** — ngrok (Argo CD API) and cloudflared (app) expose the local cluster to
  GitLab's hosted runners; the argocd-server runs in `--insecure` mode to accept the tunnels' cleartext hop.

## Quickstart

```bash
# 1. Clone/push to your own GitLab project (see docs/gitlab-setup.md)
git remote add origin https://gitlab.com/<your-namespace>/gitops-pipeline.git

# 2. Replace the cypher682 image/namespace placeholders
grep -rl "cypher682" . --exclude-dir=.git | xargs sed -i "s/cypher682/<your-namespace>/g"

# 3. Create your age key and set CI variables (docs/sops-secrets.md, docs/gitlab-setup.md):
#    GITLAB_PUSH_TOKEN, SOPS_AGE_KEY, ARGOCD_SERVER, ARGOCD_AUTH_TOKEN, DEV_APP_URL

# 4. Bootstrap Argo CD + Rollouts + Prometheus (see docs/argocd-structure.md)
kubectl create ns argocd
kubectl apply --server-side -n argocd -f <argocd-install.yaml>   # server-side: large CRDs
kubectl apply --server-side -f <rollouts-install.yaml>
kubectl apply -n observability -f observability/prometheus.yaml
kubectl apply -n argocd -f argocd/sops-plugin.yaml
kubectl apply -n argocd -f argocd/applicationset.yaml
kubectl apply -n argocd -f argocd/application.yaml

# 5. Push — CI drives dev, approve the gate for staging, watch the canary:
kubectl argo rollouts get rollout app-chart-staging -n gitops-staging --watch
```

See `docs/gitlab-setup.md`, `docs/argocd-structure.md`, `docs/sops-secrets.md` and
`docs/evidence/CHECKLIST.md` for the full walkthrough.

## Operational notes

- **CI writes back** to the protected branch via a project access token (`write_repository`) —
  `CI_JOB_TOKEN` cannot push to protected branches.
- **`ARGOCD_SERVER` must be a bare `host:port`** (e.g. `xyz.ngrok-free.dev:443`); CLI commands use
  per-command `--auth-token`. The argocd CLI and server versions are pinned to match (v3.5.2).
- **Local images** (e.g. the CMP sidecar) are loaded with `minikube image load`; registry images pull
  per `imagePullPolicy`.
- The values bump commit uses `[skip ci]` to avoid re-triggering the pipeline endlessly.

## Status

Verified end-to-end on minikube: pipeline green through all deploy stages, dev and staging **Healthy**,
staging canary fully promoted (Step 7/7, weight 100%, `app_error_rate == 0` at each gate).

## Content

- Dev.to / LinkedIn / X write-ups and the evidence guide live outside this repo (see `writeups/` next to
  the repo folder and `docs/evidence/CHECKLIST.md`).