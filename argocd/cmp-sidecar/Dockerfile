# Sidecar image for the ArgoCD sops-helm ConfigManagementPlugin.
# Contains the two tools the plugin needs (helm + sops). The
# argocd-cmp-server entrypoint binary is shared into the sidecar from the
# repo-server via the /var/run/argocd volume — it is NOT baked in here.
#
# Rebuild the sops binary if it needs refreshing (v3.9.4):
#   curl -fL -o sops-linux-amd64 \
#     https://github.com/getsops/sops/releases/download/v3.9.4/sops-v3.9.4.linux.amd64
# (the binary is git-ignored; download it before docker build)
FROM alpine/helm:3.15.4
COPY sops-linux-amd64 /usr/local/bin/sops
RUN chmod +x /usr/local/bin/sops \
    && sops --version