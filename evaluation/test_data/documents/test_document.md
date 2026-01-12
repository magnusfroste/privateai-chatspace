# RAG Test Document

This is a test document for comparing RAG systems.

## Technical Configuration

### SSL Certificate Setup

To configure SSL certificates for nginx:

1. Generate or obtain your SSL certificate and private key
2. Add the following to your nginx server block:
   ```
   ssl_certificate /etc/nginx/ssl/certificate.crt;
   ssl_certificate_key /etc/nginx/ssl/private.key;
   ```
3. Restart nginx with `sudo systemctl restart nginx`

### Maximum File Upload Size

The maximum file upload size is configured to **50MB** by default. This can be changed in the application settings under `config.yaml`:

```yaml
upload:
  max_size_mb: 50
```

## Legal Information

### GDPR Article 17 - Right to Erasure

Article 17 of the General Data Protection Regulation (GDPR) establishes the "right to be forgotten" or "right to erasure". Key points:

- Data subjects can request deletion of their personal data
- Controllers must delete data "without undue delay"
- Applies when data is no longer necessary for the original purpose
- Applies when consent is withdrawn
- Maximum response time: 30 days

### Data Retention Policy

Personal data should be retained only as long as necessary:
- Customer records: 7 years after last transaction
- Employee records: 6 years after employment ends
- Marketing data: Until consent is withdrawn

## Product Specifications

### Model XR-7500-B

The XR-7500-B is our flagship network switch with the following specifications:

| Feature | Specification |
|---------|---------------|
| Ports | 24 x 10GbE |
| Throughput | 480 Gbps |
| Latency | < 1 microsecond |
| Power | 150W typical |
| Form Factor | 1U rack mount |

### Model XR-3200-A

Entry-level switch for small deployments:

| Feature | Specification |
|---------|---------------|
| Ports | 8 x 1GbE |
| Throughput | 16 Gbps |
| Power | 25W typical |

## User Guide

### Password Reset

To reset your password:

1. Click the "Forgot Password" link on the login page
2. Enter your registered email address
3. Check your email for the reset link
4. Click the link and enter your new password
5. Password must be at least 8 characters with one number

### Account Settings

Access your account settings by clicking your profile icon in the top right corner.
