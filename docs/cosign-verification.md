# Cosign Keyless Signature Verification

## Why keyless

No key management, no rotation, no secure key storage problem. Identity is
proven by GitLab CI's OIDC token against Sigstore's Fulcio CA at sign time,
and the signature + transparency log entry (Rekor) are what get checked at
verify time — not a static keypair.

## Signing (happens automatically in CI — sign:cosign job)

```bash
cosign sign --yes "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
```

## Verifying manually (evidence screenshot target)

```bash
cosign verify \
  --certificate-identity-regexp ".*gitops-pipeline.*" \
  --certificate-oidc-issuer "https://gitlab.com" \
  registry.gitlab.com/CHANGE_ME/gitops-pipeline:<sha>
```

Expected output includes the certificate subject (GitLab CI job identity),
the OIDC issuer, and a `Bundle` transparency-log entry — that log entry is
what makes the signature auditable even after the fact.

## SBOM attestation verification

```bash
cosign verify-attestation \
  --type cyclonedx \
  --certificate-identity-regexp ".*gitops-pipeline.*" \
  --certificate-oidc-issuer "https://gitlab.com" \
  registry.gitlab.com/CHANGE_ME/gitops-pipeline:<sha>
```

## Where this is enforced, not just demonstrated

`promote:verify-signature` (CI, promote stage) runs the same `cosign
verify` command before staging deployment is allowed to proceed — an
unsigned or tampered image cannot reach the canary environment even if
someone bypasses the manual approval gate through a direct kubectl apply
(the ArgoCD sync itself doesn't re-check signatures, so this CI gate is
the actual enforcement point; noted as a known gap below).

## Known gap / possible hardening

Signature verification currently happens in CI, not admission control. A
stronger setup would add a Kyverno or Sigstore Policy Controller admission
webhook on the `gitops-staging` namespace to reject unsigned images at the
cluster level regardless of how they were applied. Not implemented here —
documented as a deliberate scope boundary for this project, and a natural
next step if extended.
