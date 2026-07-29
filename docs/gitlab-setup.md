# GitLab Setup

## 1. Install glab (GitLab CLI) — Windows

```bash
winget install glab.glab
glab auth login
```

## 2. Create the GitLab project

```bash
glab repo create gitops-pipeline --public --description "CI/CD + GitOps showcase: GitLab CI, ArgoCD, Argo Rollouts, Cosign, SOPS"
```

## 3. Push this repo

```bash
cd gitops-pipeline
git init
git add .
git commit -m "feat: initial gitops-pipeline scaffold"
git remote add origin https://gitlab.com/<your-namespace>/gitops-pipeline.git
git push -u origin main
```

## 4. Replace CHANGE_ME placeholders

Search the repo for `CHANGE_ME` and replace with your actual GitLab
namespace/repo path:

```bash
grep -rl "CHANGE_ME" . | xargs sed -i "s/CHANGE_ME/<your-namespace>/g"
```

Files affected: `argocd/applicationset.yaml`, `argocd/app-of-apps.yaml`,
`rollouts/rollout.yaml`, `docs/cosign-verification.md`.

## 5. GitHub mirror (repo is primarily showcased on GitHub per portfolio convention)

```bash
# In GitLab project settings -> Repository -> Mirroring repositories,
# or via glab:
glab repo mirror --url https://github.com/cypher682/gitops-pipeline.git
```

Or push to both remotes manually:

```bash
git remote add github https://github.com/cypher682/gitops-pipeline.git
git push github main
```

## 6. Required CI/CD variables (Settings -> CI/CD -> Variables)

| Variable | Type | Protected | Masked | Purpose |
|---|---|---|---|---|
| `ARGOCD_SERVER` | Variable | Yes | No | ArgoCD API endpoint (e.g. `argocd.yourdomain.com` or tunnelled minikube service) |
| `ARGOCD_AUTH_TOKEN` | Variable | Yes | Yes | `argocd account generate-token` output |
| `SOPS_AGE_KEY` | Variable | Yes | Yes | Full contents of your `age-key.txt` — see `docs/sops-secrets.md` |
| `DEV_APP_URL` | Variable | No | No | URL the `deploy:dev-smoke-test` job curls for `/health` |

`CI_REGISTRY`, `CI_REGISTRY_USER`, `CI_REGISTRY_PASSWORD`,
`CI_JOB_TOKEN` are provided automatically by GitLab — no setup needed if
using the built-in GitLab Container Registry.

## 7. Protected environment for the promote gate

Settings -> CI/CD -> Environments -> protect `staging`, and restrict who
can approve deployments to that environment. This is what backs the
`promote:manual-gate` job's `when: manual` + `environment:` block.

## 8. Reaching ArgoCD on minikube from GitLab CI

Since ArgoCD is running on your local minikube, GitLab.com's hosted
runners can't reach it directly. Two options:

- **Self-hosted GitLab Runner** on your machine (registered against the
  GitLab project, tagged e.g. `local`), with `deploy-dev`/`deploy-staging`
  jobs pinned to that runner via `tags:`. Simplest for a local-cluster demo.
- **Tunnel** (e.g. `cloudflared` or `ngrok`) exposing the ArgoCD API
  server, with `ARGOCD_SERVER` pointing at the tunnel URL. Only needed if
  you want hosted runners to reach it directly.

Not pre-wired into `.gitlab-ci.yml` since it depends on which option you
pick — add `tags: [local]` to the `deploy:*` jobs if going the runner route.
