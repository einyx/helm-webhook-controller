#!/bin/bash
set -e

# Configuration
NAMESPACE="helm-webhook-system"
SERVICE="helm-webhook-controller"
SECRET_NAME="helm-webhook-tls"
CERT_DIR="${CERT_DIR:-./certs}"

echo "Generating TLS certificates for webhook..."

# Create certificate directory
mkdir -p "$CERT_DIR"

# Generate CA private key
openssl genrsa -out "$CERT_DIR/ca.key" 2048

# Generate CA certificate
openssl req -new -x509 -days 365 -key "$CERT_DIR/ca.key" \
  -subj "/CN=Helm Webhook CA" \
  -out "$CERT_DIR/ca.crt"

# Generate server private key
openssl genrsa -out "$CERT_DIR/tls.key" 2048

# Generate certificate signing request
cat <<EOF > "$CERT_DIR/csr.conf"
[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = ${SERVICE}
DNS.2 = ${SERVICE}.${NAMESPACE}
DNS.3 = ${SERVICE}.${NAMESPACE}.svc
DNS.4 = ${SERVICE}.${NAMESPACE}.svc.cluster.local
EOF

openssl req -new -key "$CERT_DIR/tls.key" \
  -subj "/CN=${SERVICE}.${NAMESPACE}.svc" \
  -out "$CERT_DIR/server.csr" \
  -config "$CERT_DIR/csr.conf"

# Generate server certificate
openssl x509 -req -days 365 -in "$CERT_DIR/server.csr" \
  -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" \
  -CAcreateserial -out "$CERT_DIR/tls.crt" \
  -extensions v3_req -extfile "$CERT_DIR/csr.conf"

# Get CA bundle for webhook configuration
CA_BUNDLE=$(cat "$CERT_DIR/ca.crt" | base64 | tr -d '\n')

echo "Certificates generated successfully!"
echo ""
echo "CA Bundle (for webhook configuration):"
echo "$CA_BUNDLE"
echo ""
echo "To create the TLS secret in Kubernetes:"
echo "kubectl create secret tls $SECRET_NAME \\"
echo "  --cert=$CERT_DIR/tls.crt \\"
echo "  --key=$CERT_DIR/tls.key \\"
echo "  -n $NAMESPACE"