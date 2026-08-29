# gitops-pipeline

CI/CD and GitOps showcase: GitLab CI pipelines, ArgoCD ApplicationSet,
Argo Rollouts progressive delivery, and supply-chain security (Cosign +
SBOM + SOPS).

**Domain:** Platform engineering — CI/CD and GitOps
**Pipeline:** `validate → build → test → scan → sign → push → deploy-dev → promote → deploy-staging`

## Build Status

| Stage | Description | Status |
|---|---|---|
| 1 | Repo skeleton + `.gitlab-ci.yml` scaffold | ✅ Done |
| 2 | Sample FastAPI app + Dockerfile + Helm chart | ✅ Done |
| 3 | ArgoCD ApplicationSet (dev/staging) + app-of-apps | ✅ Done |
| 4 | Argo Rollouts canary + AnalysisTemplate (+ blue-green doc'd) | ✅ Done |
| 5 | CI: validate/build/test — real implementations | ✅ Done |
| 6 | CI: scan — Trivy, Semgrep, SOPS-detect, pip-audit | ✅ Done |
| 7 | CI: sign — Cosign keyless + Syft SBOM + attestation | ✅ Done |
| 8 | Secrets — SOPS + age, real encrypted example, ArgoCD plugin | ✅ Done |
| 9 | GitLab setup docs, evidence checklist | ✅ Done |

**Not yet done (deliberately deferred — requires a live push + running
cluster to produce, not something buildable offline):**
- Actual `age-key.txt` generation + `SOPS_AGE_KEY` CI variable (yours to create — see `docs/sops-secrets.md`)
- Replacing `cypher682` with your real GitLab namespace (see `docs/gitlab-setup.md`)
- Evidence screenshots (`docs/evidence/CHECKLIST.md`)
- Content deliverables (Dev.to / LinkedIn / X) — drafted after evidence is captured, per portfolio SDLC (build → evidence → content)

## Quickstart

```bash
# 1. Push to GitLab (see docs/gitlab-setup.md for full steps)
git init && git add . && git commit -m "feat: initial gitops-pipeline scaffold"
git remote add origin https://gitlab.com/<your-namespace>/gitops-pipeline.git
git push -u origin main

# 2. Replace cypher682 placeholders
grep -rl "cypher682" . | xargs sed -i "s/cypher682/<your-namespace>/g"

# 3. Generate your own SOPS/age key and set CI variables (docs/sops-secrets.md, docs/gitlab-setup.md)

# 4. Bootstrap ArgoCD on minikube
kubectl apply -f argocd/app-of-apps.yaml -n argocd

# 5. Push a commit — pipeline runs end to end through to staging canary
```

## Repo Structure

```
gitops-pipeline/
├── app/                          # FastAPI sample app (health, CRUD, /metrics)
│   ├── app/main.py
│   ├── app/test_main.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── requirements-dev.txt
├── helm/
│   └── app-chart/                # Deployment/Rollout, Service, Ingress, HPA, NetworkPolicy, RBAC
│       ├── values.yaml / values-dev.yaml / values-staging.yaml
│       └── templates/
├── argocd/
│   ├── applicationset.yaml       # goTemplate ApplicationSet, dev (auto) + staging (manual)
│   ├── app-of-apps.yaml          # root Application
│   └── sops-plugin.yaml          # ArgoCD ConfigManagementPlugin for SOPS decryption
├── rollouts/
│   ├── rollout.yaml              # reference/evidence copy — helm template is source of truth
│   └── analysis-template.yaml    # Prometheus error-rate query for canary gates
├── .gitlab-ci.yml                # full 9-stage pipeline, real implementations
├── .semgrep.yml                  # custom SAST rules
├── .sops.yaml                    # SOPS encryption config (demo age key — replace before real use)
├── secrets/
│   └── app-secrets.enc.yaml      # real SOPS-encrypted example
├── docs/
│   ├── argocd-structure.md
│   ├── cosign-verification.md
│   ├── sops-secrets.md
│   ├── gitlab-setup.md
│   └── evidence/
│       └── CHECKLIST.md
└── README.md
```

## Key Implementation Decisions

- **goTemplate ApplicationSet** over plain-mode templating — needed real
  `{{- if }}` conditionals so dev (auto-sync) and staging (manual-sync)
  diverge from a single template instead of duplicated Application manifests.
- **Argo Rollouts CRD replaces Deployment** directly in the Helm chart
  (`rollout.enabled` toggle in values) rather than maintaining a separate
  Deployment + Rollout pair — one source of truth, canary steps driven by
  per-environment values files.
- **Cosign keyless signing** (Sigstore/Fulcio via GitLab OIDC) instead of
  static keypairs — no key storage/rotation problem, identity comes from
  the CI job itself and is auditable via the Rekor transparency log.
- **Signature re-verification at the promote gate**, not just at sign
  time — closes the gap where a tag could theoretically be replaced
  between build and staging deployment.
- **SOPS+age over PGP** for secrets — single flat keypair file, no
  keyring management, simpler to hand to CI as one masked variable.
- **`app_error_rate` exposed directly by the sample app's `/metrics`
  endpoint** rather than deriving it from generic HTTP metrics — keeps the
  AnalysisTemplate query simple and makes the auto-rollback demo (inject
  errors, watch the canary abort) straightforward to trigger on demand.
