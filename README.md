# Helm Registry Webhook

A Kubernetes webhook controller that automatically redirects Helm OCI registry references to use Azure Container Registry as a mirror/cache.

## Project Structure

```
helm-registry-webhook/
├── helm-webhook-controller/        # Helm chart
│   ├── Chart.yaml                 # Chart metadata
│   ├── values.yaml                # Default configuration values
│   ├── README.md                  # Chart documentation
│   ├── templates/                 # Kubernetes resource templates
│   ├── src/                       # Source code
│   │   └── webhook-server.py      # Webhook server implementation
│   ├── examples/                  # Example configurations
│   └── Dockerfile                 # Container image definition
```

## Quick Start

### Install with Helm

```bash
cd helm-webhook-controller
helm install helm-webhook-controller . \
  --namespace helm-webhook-controller \
  --create-namespace \
  --set acr.registry=your-registry.azurecr.io
```

### Install with Flux

See [helm-webhook-controller/examples/flux-helmrelease.yaml](helm-webhook-controller/examples/flux-helmrelease.yaml) for a complete Flux setup.

## Features

- Automatic URL rewriting for OCI-based Helm repositories
- Support for major registries (Docker Hub, GHCR, Quay, etc.)
- Seamless Flux CD integration
- High availability deployment
- Configurable namespace selection

## Documentation

For detailed documentation, see the [Helm chart README](helm-webhook-controller/README.md).

## License

MIT License