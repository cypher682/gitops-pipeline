# Evidence Checklist

Per the D2 project spec. Each item maps to where it's produced — check the
box once you've captured the actual screenshot/output and dropped it in
this `docs/evidence/` folder.

- [ ] **GitLab CI pipeline visualization (all stages green)**
      Push to GitLab, screenshot the pipeline graph view.

- [ ] **Trivy scan blocking a CRITICAL image**
      Temporarily pin `app/Dockerfile`'s base image to an old tag known to
      have a CRITICAL CVE, push, screenshot `scan:trivy` failing with the
      finding, then revert.

- [ ] **Cosign signature verification output**
      Run the command in `docs/cosign-verification.md` locally against a
      real pushed+signed tag, screenshot the terminal output.

- [ ] **SBOM file (show it exists + structure)**
      `sbom.cyclonedx.json` job artifact from `sign:sbom` — download from
      a pipeline run, `cat` or open in an editor, screenshot the CycloneDX
      structure (components list, etc).

- [ ] **ArgoCD ApplicationSet — both environments synced**
      `argocd app list` showing `gitops-pipeline-dev` and
      `gitops-pipeline-staging` both `Synced`/`Healthy`.

- [ ] **Argo Rollouts canary progression screenshot**
      `kubectl argo rollouts get rollout app-chart-staging -n gitops-staging --watch`
      during a staging promotion — screenshot mid-canary (e.g. at 50%).

- [ ] **Argo Rollouts auto-rollback triggered (inject error, show rollback)**
      Temporarily modify `app/app/main.py`'s `/health` or `/metrics` to
      force `app_error_rate` above 0.05, push through to staging, screenshot
      the AnalysisRun failing and the Rollout aborting/rolling back. Revert after.

- [ ] **SOPS encrypted secret in repo (show encrypted, show decrypted in pod)**
      `secrets/app-secrets.enc.yaml` is already real ciphertext (see
      `docs/sops-secrets.md`). "Decrypted in pod" requires your own age key
      wired in first — see that doc's setup steps.

- [ ] **Pipeline approval gate screenshot (GitLab protected environment)**
      Screenshot the `promote:manual-gate` job awaiting manual action in
      the GitLab UI, plus the protected-environment approval dialog.

- [ ] **Semgrep finding screenshot**
      `semgrep-report.json` job artifact from `scan:semgrep` — the custom
      `hardcoded-secret-like-string` rule in `.semgrep.yml` should fire if
      you temporarily hardcode a fake credential in `app/app/main.py` to
      demonstrate it, screenshot the finding, then revert.
