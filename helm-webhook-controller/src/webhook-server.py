#!/usr/bin/env python3
import base64
import json
import logging
import os
import ssl
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
ACR_REGISTRY = os.getenv("ACR_REGISTRY", "meshxregistry.azurecr.io")
ACR_AUTH_SECRET = os.getenv("ACR_AUTH_SECRET", "meshxregistry-secret")

# Registry mappings
REGISTRY_MAPPINGS = {
    "registry-1.docker.io": "docker.io",
    "docker.io": "docker.io",
    "ghcr.io": "ghcr.io",
    "quay.io": "quay.io",
    "gcr.io": "gcr.io",
    "registry.k8s.io": "registry.k8s.io",
    "mcr.microsoft.com": "mcr.microsoft.com",
}


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(
            "%s - - [%s] %s"
            % (self.address_string(), self.log_date_time_string(), format % args)
        )

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith("/mutate"):
            self.handle_mutate()
        elif self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def handle_mutate(self):
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)

        try:
            admission_review = json.loads(body)
            request = admission_review.get("request", {})

            # Log the request
            logger.info(
                f"Mutating {request.get('kind', {}).get('kind')} "
                f"{request.get('namespace')}/{request.get('name')}"
            )

            # Generate patches based on resource type
            patches = []
            kind = request.get("kind", {}).get("kind")

            if kind == "HelmRepository":
                patches = self.mutate_helm_repository(request.get("object", {}))

            # Build response
            admission_response = {
                "uid": request.get("uid"),
                "allowed": True,
            }

            if patches:
                admission_response["patchType"] = "JSONPatch"
                admission_response["patch"] = base64.b64encode(
                    json.dumps(patches).encode()
                ).decode()

            response = {
                "apiVersion": "admission.k8s.io/v1",
                "kind": "AdmissionReview",
                "response": admission_response,
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            logger.error(f"Error: {e}")
            self.send_response(500)
            self.end_headers()

    def mutate_helm_repository(self, obj):
        patches = []
        spec = obj.get("spec", {})
        url = spec.get("url", "")

        if url.startswith("oci://"):
            new_url = self.rewrite_oci_url(url)
            if new_url != url:
                patches.append({"op": "replace", "path": "/spec/url", "value": new_url})

                # Add secret reference if not present
                if not spec.get("secretRef"):
                    patches.append(
                        {
                            "op": "add",
                            "path": "/spec/secretRef",
                            "value": {"name": ACR_AUTH_SECRET},
                        }
                    )

                logger.info(f"Rewriting URL from {url} to {new_url}")

        return patches

    def rewrite_oci_url(self, url):
        if not url.startswith("oci://"):
            return url

        # Parse OCI URL: oci://registry/path
        url_parts = url[6:]  # Remove "oci://"
        parts = url_parts.split("/", 1)

        if len(parts) < 2:
            return url

        registry = parts[0]
        path = parts[1]

        # Check if this registry should be mirrored
        if registry in REGISTRY_MAPPINGS:
            cached_prefix = REGISTRY_MAPPINGS[registry]
            # Rewrite to ACR cached path
            new_url = f"oci://{ACR_REGISTRY}/cached/{cached_prefix}/{path}"
            return new_url

        return url


if __name__ == "__main__":
    # Wait for cert files to be available
    import time

    cert_file = "/certs/cert"
    key_file = "/certs/key"

    for i in range(30):
        if os.path.exists(cert_file) and os.path.exists(key_file):
            break
        logger.info(f"Waiting for certificates... {i}/30")
        time.sleep(1)
    else:
        logger.error("Certificates not found after 30 seconds")
        exit(1)

    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)

    # Create and start server
    httpd = HTTPServer(("", 8443), WebhookHandler)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    logger.info("Webhook server started on port 8443")
    httpd.serve_forever()
