FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 webhook && \
    mkdir -p /tmp/k8s-webhook-server/serving-certs && \
    chown -R webhook:webhook /tmp/k8s-webhook-server

# Copy application files
COPY --chown=webhook:webhook src/webhook-server.py .
COPY --chown=webhook:webhook requirements.txt .

# Install dependencies (if any)
RUN pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER webhook

# Expose webhook port
EXPOSE 8443

# Run the webhook server
CMD ["python", "webhook-server.py"]