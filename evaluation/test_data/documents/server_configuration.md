# Server Configuration Guide

## Web Server Setup

### Nginx Configuration

#### Basic Setup

Install nginx on Ubuntu:
```bash
sudo apt update
sudo apt install nginx
sudo systemctl enable nginx
```

#### SSL Certificate Configuration

To configure SSL certificates for nginx:

1. Generate or obtain your SSL certificate and private key
2. Add the following to your nginx server block:
   ```nginx
   server {
       listen 443 ssl;
       server_name example.com;
       
       ssl_certificate /etc/nginx/ssl/certificate.crt;
       ssl_certificate_key /etc/nginx/ssl/private.key;
       
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers HIGH:!aNULL:!MD5;
   }
   ```
3. Restart nginx: `sudo systemctl restart nginx`

#### Let's Encrypt Setup

For free SSL certificates:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d example.com
```

Certificates auto-renew via cron.

### Apache Configuration

#### SSL Setup for Apache

```apache
<VirtualHost *:443>
    ServerName example.com
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/certificate.crt
    SSLCertificateKeyFile /etc/ssl/private/private.key
</VirtualHost>
```

---

## Application Settings

### File Upload Configuration

The maximum file upload size is configured to **50MB** by default.

#### Changing Upload Limits

In `config.yaml`:
```yaml
upload:
  max_size_mb: 50
  allowed_types:
    - application/pdf
    - image/png
    - image/jpeg
  temp_directory: /tmp/uploads
```

In nginx (for proxy):
```nginx
client_max_body_size 50M;
```

In PHP:
```ini
upload_max_filesize = 50M
post_max_size = 50M
```

### Database Configuration

#### PostgreSQL Setup

```yaml
database:
  host: localhost
  port: 5432
  name: myapp
  user: dbuser
  password: ${DB_PASSWORD}
  pool_size: 20
```

#### Connection Pooling

Recommended pool sizes:
- Small app: 5-10 connections
- Medium app: 20-50 connections
- Large app: 100+ connections

### Caching Configuration

#### Redis Setup

```yaml
cache:
  driver: redis
  host: localhost
  port: 6379
  ttl: 3600
```

#### Memcached Alternative

```yaml
cache:
  driver: memcached
  servers:
    - localhost:11211
```

---

## Security Settings

### Firewall Configuration

#### UFW (Ubuntu)

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

#### iptables

```bash
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

### SSH Hardening

Edit `/etc/ssh/sshd_config`:
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
```

---

## Monitoring

### Log Configuration

Application logs location: `/var/log/myapp/`

Log rotation in `/etc/logrotate.d/myapp`:
```
/var/log/myapp/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
```

### Health Checks

Endpoint: `GET /health`

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "cache": "connected",
  "uptime": 86400
}
```
