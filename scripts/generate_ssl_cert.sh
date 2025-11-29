#!/bin/bash
# Generate self-signed SSL certificate for HTTPS dashboard

CERT_DIR="/home/iot/attendance-system/certs"
mkdir -p "$CERT_DIR"

echo "======================================================================"
echo "Generating Self-Signed SSL Certificate"
echo "======================================================================"

# Generate private key and certificate
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout "$CERT_DIR/dashboard.key" \
  -out "$CERT_DIR/dashboard.crt" \
  -days 365 \
  -subj "/C=US/ST=State/L=City/O=IoT Attendance/CN=$(hostname)"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SSL Certificate generated successfully"
    echo "   Certificate: $CERT_DIR/dashboard.crt"
    echo "   Private Key: $CERT_DIR/dashboard.key"
    echo ""
    echo "⚠️  This is a self-signed certificate."
    echo "   Browsers will show a security warning."
    echo "   For production, use Let's Encrypt or a CA-signed certificate."
    echo ""
else
    echo "❌ Failed to generate SSL certificate"
    exit 1
fi

# Set permissions
chmod 600 "$CERT_DIR/dashboard.key"
chmod 644 "$CERT_DIR/dashboard.crt"

echo "✅ Certificate permissions set"
echo ""
echo "To use HTTPS, you need a reverse proxy like Nginx."
echo "See scripts/README_DASHBOARD.md for Nginx setup."
