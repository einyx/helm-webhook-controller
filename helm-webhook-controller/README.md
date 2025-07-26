# Helm Webhook Controller

A Kubernetes mutating admission webhook that automatically redirects Helm OCI registry references to use Azure Container Registry (ACR) as a mirror/cache. This webhook intercepts Flux CD's `HelmRepository` resources and rewrites their URLs to use ACR cached paths, improving reliability and reducing external dependencies.

## Overview

The Helm Webhook Controller helps organizations:
- **Reduce external registry dependencies** by caching Helm charts in ACR
- **Improve deployment reliability** by using a local registry mirror
- **Centralize registry authentication** with automatic secret injection
- **Support air-gapped environments** with pre-cached charts

## Features

- Automatic URL rewriting for OCI-based Helm repositories
- Automatic ACR authentication secret injection
- Support for major registries (Docker Hub, GHCR, Quay, GCR, etc.)
- Seamless integration with Flux CD
- Configurable namespace selection
- High availability with multiple replicas
- Choice between cert-manager or self-generated certificates

## Supported Registries

The webhook automatically rewrites URLs from these registries:
- Docker Hub (`registry-1.docker.io`, `docker.io`)
- GitHub Container Registry (`ghcr.io`)
- Quay (`quay.io`)
- Google Container Registry (`gcr.io`)
- Kubernetes Registry (`registry.k8s.io`)
- Microsoft Container Registry (`mcr.microsoft.com`)

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- Azure Container Registry with cached repositories
- (Optional) cert-manager for certificate management

## Installation

### Using Helm

```bash
# Add the Helm repository
helm repo add helm-webhook-controller https://your-helm-repo-url
helm repo update

# Install the webhook
helm install helm-webhook-controller helm-webhook-controller/helm-webhook-controller \
  --namespace helm-webhook-controller \
  --create-namespace \
  --set acr.registry=your-registry.azurecr.io \
  --set acr.createSecret=true \
  --set acr.dockerConfigJson="your-base64-encoded-docker-config"
```

### Using Flux CD

See the [Flux HelmRelease example](examples/flux-helmrelease.yaml) for a complete setup.

## Configuration

### Key Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of webhook replicas | `2` |
| `namespace` | Namespace to install the webhook | `helm-webhook-controller` |
| `acr.registry` | ACR registry URL | `meshxregistry.azurecr.io` |
| `acr.authSecret` | Name of the ACR auth secret | `meshxregistry-helm-secret` |
| `acr.createSecret` | Create the ACR auth secret | `false` |
| `webhook.failurePolicy` | Webhook failure policy (Fail/Ignore) | `Fail` |
| `webhook.namespaceSelector` | Namespace selector rules | `[]` (all non-system namespaces) |
| `certManager.enabled` | Use cert-manager for certificates | `false` |

### ACR Authentication

You need to provide ACR credentials in one of two ways:

1. **Let the chart create the secret** (set `acr.createSecret=true`):
```yaml
acr:
  createSecret: true
  dockerConfigJson: |
    {
      "auths": {
        "your-registry.azurecr.io": {
          "username": "your-username",
          "password": "your-password",
          "auth": "base64-encoded-username:password"
        }
      }
    }
```

2. **Create the secret manually**:
```bash
kubectl create secret docker-registry meshxregistry-helm-secret \
  --namespace helm-webhook-controller \
  --docker-server=your-registry.azurecr.io \
  --docker-username=your-username \
  --docker-password=your-password
```

### Namespace Selection

Control which namespaces the webhook applies to:

```yaml
webhook:
  namespaceSelector:
    - key: environment
      operator: In
      values: ["production", "staging"]
    - key: webhook.helm/enabled
      operator: NotIn
      values: ["false"]
```

## How It Works

1. **Interception**: The webhook intercepts CREATE and UPDATE operations on `HelmRepository` resources
2. **URL Detection**: Checks if the repository URL uses the `oci://` protocol
3. **Registry Mapping**: Maps known registries to ACR cached paths
4. **URL Rewriting**: Transforms URLs like:
   - `oci://docker.io/bitnami/nginx` → `oci://your-acr.azurecr.io/cached/docker.io/bitnami/nginx`
5. **Secret Injection**: Adds ACR authentication secret reference if not present

## Example

Before webhook mutation:
```yaml
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: HelmRepository
metadata:
  name: bitnami
spec:
  interval: 10m
  url: oci://registry-1.docker.io/bitnamicharts
```

After webhook mutation:
```yaml
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: HelmRepository
metadata:
  name: bitnami
spec:
  interval: 10m
  url: oci://meshxregistry.azurecr.io/cached/docker.io/bitnamicharts
  secretRef:
    name: meshxregistry-helm-secret
```

## Setting Up ACR Cache

To use this webhook, you need to set up repository caching in ACR:

```bash
# Example: Cache bitnami charts
az acr import \
  --name your-acr \
  --source docker.io/bitnami/nginx:latest \
  --image cached/docker.io/bitnami/nginx:latest
```

Or use ACR Tasks for automated syncing:
```bash
az acr task create \
  --name sync-bitnami \
  --registry your-acr \
  --context /dev/null \
  --file - \
  --schedule "0 */6 * * *" \
  --commit-trigger-enabled false \
  <<EOF
version: v1.1.0
steps:
  - cmd: acr import --source docker.io/bitnami/nginx:latest --image cached/docker.io/bitnami/nginx:latest
EOF
```

## Troubleshooting

### Check webhook logs
```bash
kubectl logs -n helm-webhook-controller -l app.kubernetes.io/name=helm-webhook-controller
```

### Verify webhook configuration
```bash
kubectl get mutatingwebhookconfigurations helm-webhook-controller -o yaml
```

### Test the webhook
```bash
# Apply a test HelmRepository
kubectl apply -f - <<EOF
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: HelmRepository
metadata:
  name: test-repo
  namespace: default
spec:
  interval: 10m
  url: oci://docker.io/bitnami/nginx
EOF

# Check if it was mutated
kubectl get helmrepository test-repo -o yaml
```

## Security Considerations

- The webhook requires cluster-wide permissions to mutate HelmRepository resources
- ACR credentials are stored as Kubernetes secrets
- Use RBAC to limit access to the webhook namespace
- Consider using managed identities for ACR authentication in production

## Development

### Building the Docker image
```bash
docker build -t your-registry/helm-webhook-controller:latest .
docker push your-registry/helm-webhook-controller:latest
```

### Running locally
```bash
cd helm-webhook-controller/src
python webhook-server.py
```

### Running tests
```bash
# Apply test resources
kubectl apply -f examples/test-helm-oci.yaml
kubectl apply -f examples/test-simple-helm.yaml
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
