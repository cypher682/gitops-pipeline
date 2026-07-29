# SOPS + age Secrets Workflow

## Why age instead of PGP

One flat keypair file, no keyring/web-of-trust setup, no expiry management.
Simpler to rotate and simpler to hand to CI as a single masked variable.

## One-time setup

```bash
age-keygen -o age-key.txt
# Public key: age1...   <- goes in .sops.yaml
# Private key stays in age-key.txt — NEVER commit this file
```

Put the public key in `.sops.yaml` under `creation_rules[].age`.
Put the **entire contents** of `age-key.txt` into a GitLab CI/CD variable
named `SOPS_AGE_KEY` (masked, protected, scoped to protected branches).

## Encrypting a secret

```bash
sops --encrypt --in-place secrets/app-secrets.enc.yaml
```

SOPS reads `.sops.yaml` automatically based on the file path, encrypts only
the `data`/`stringData` fields (per `encrypted_regex`), and leaves
`apiVersion`/`kind`/`metadata` in plaintext so the file stays readable and
diffable in git history.

## Decrypting locally (to verify before committing)

```bash
sops --decrypt secrets/app-secrets.enc.yaml
```

## How it reaches the cluster

1. `scan:sops-detect` (CI, scan stage) fails the pipeline if any file
   under `secrets/` is missing the `sops:` metadata block — i.e. catches
   anyone who accidentally commits plaintext.
2. ArgoCD's `sops-helm` ConfigManagementPlugin (`argocd/sops-plugin.yaml`)
   decrypts `secrets/*.enc.yaml` at sync time, using `SOPS_AGE_KEY` mounted
   into the `argocd-repo-server` sidecar as a Secret — decryption happens
   server-side, the plaintext is never written back to git.
3. The decrypted Secret object is applied alongside the Helm-rendered
   manifests in the same sync.

## Repo example

`secrets/app-secrets.enc.yaml` in this repo is a **real** SOPS-encrypted
file (genuine AES256-GCM ciphertext, valid `sops:` metadata block) —
encrypted against a demo age keypair generated solely to produce this
example. The private half of that demo key was never saved anywhere and
is not recoverable, so this file cannot be decrypted by anyone, including
its author. Before using this repo for anything real:

1. Generate your own keypair (`age-keygen -o age-key.txt`)
2. Replace the public key in `.sops.yaml`
3. Re-encrypt: `sops updatekeys secrets/app-secrets.enc.yaml`

## Evidence checklist mapping

- "SOPS encrypted secret in repo (show encrypted)" → `secrets/app-secrets.enc.yaml`, viewable directly, ciphertext is real.
- "show decrypted in pod" → once you've replaced the key and the SOPS plugin
  is wired into your `argocd-repo-server`, `kubectl exec` into the app pod
  and `env | grep DATABASE_URL` shows the decrypted value injected as an
  env var from the resulting Secret.
