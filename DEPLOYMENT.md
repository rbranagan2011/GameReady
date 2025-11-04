# GameReady Deployment Guide

## Deploying to start.gamereadyapp.com

This guide will help you deploy GameReady to a production server accessible at `start.gamereadyapp.com`.

---

## Prerequisites

- **Server**: VPS or cloud server (Ubuntu 20.04+ recommended)
  - Minimum: 1GB RAM, 1 CPU core
  - Recommended: 2GB+ RAM, 2+ CPU cores
- **Domain**: `gamereadyapp.com` with DNS access
- **SSH access** to your server
- **Python 3.8+** installed on server

---

## Step 1: Server Setup

### 1.1 Connect to Your Server
```bash
ssh user@your-server-ip
```

### 1.2 Update System Packages
```bash
sudo apt update
sudo apt upgrade -y
```

### 1.3 Install Required System Packages
```bash
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx postgresql postgresql-contrib git
```

---

## Step 2: DNS Configuration

Configure your DNS to point `start.gamereadyapp.com` to your server's IP address:

1. Log into your domain registrar (where you manage gamereadyapp.com)
2. Add an **A record**:
   - **Type**: A
   - **Name**: start
   - **Value**: Your server's IP address
   - **TTL**: 3600 (or default)

Wait for DNS propagation (can take a few minutes to 48 hours).

Verify DNS is working:
```bash
dig start.gamereadyapp.com
# or
nslookup start.gamereadyapp.com
```

---

## Step 3: Database Setup (PostgreSQL)

### 3.1 Create Database and User
```bash
sudo -u postgres psql
```

In PostgreSQL prompt:
```sql
CREATE DATABASE gameready_db;
CREATE USER gameready_user WITH PASSWORD 'your-secure-password-here';
ALTER ROLE gameready_user SET client_encoding TO 'utf8';
ALTER ROLE gameready_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE gameready_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE gameready_db TO gameready_user;
\q
```

### 3.2 Update settings.py
The production settings will use PostgreSQL (already configured in `settings/production.py`).

---

## Step 4: Upload Your Code

### Option A: Using Git (Recommended)
```bash
cd /var/www
sudo mkdir -p gameready
sudo chown $USER:$USER gameready
cd gameready
git clone <your-repo-url> .
```

### Option B: Using SCP/SFTP
```bash
# On your local machine
scp -r /Users/rbran/PycharmProjects/GameReady/* user@your-server:/var/www/gameready/
```

---

## Step 5: Configure Python Environment

```bash
cd /var/www/gameready
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 6: Configure Environment Variables

Create a `.env` file in the project root:
```bash
cd /var/www/gameready
nano .env
```

Add the following (replace with your actual values):
```env
DJANGO_SETTINGS_MODULE=GameReady.settings.production
SECRET_KEY=your-super-secret-key-generate-with-django-admin-generate-secret-key
DEBUG=False
ALLOWED_HOSTS=start.gamereadyapp.com,www.start.gamereadyapp.com
DB_NAME=gameready_db
DB_USER=gameready_user
DB_PASSWORD=your-secure-password-here
DB_HOST=localhost
DB_PORT=5432
```

**Generate a secure SECRET_KEY:**
```bash
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Step 7: Run Migrations and Collect Static Files

```bash
cd /var/www/gameready
source venv/bin/activate

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

---

## Step 8: Configure Gunicorn

Create `/etc/systemd/system/gameready.service`:
```bash
sudo nano /etc/systemd/system/gameready.service
```

Add:
```ini
[Unit]
Description=GameReady Gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/gameready
Environment="PATH=/var/www/gameready/venv/bin"
EnvironmentFile=/var/www/gameready/.env
ExecStart=/var/www/gameready/venv/bin/gunicorn \
    --access-logfile - \
    --workers 3 \
    --bind unix:/var/www/gameready/gameready.sock \
    GameReady.wsgi:application

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gameready
sudo systemctl start gameready
sudo systemctl status gameready
```

---

## Step 9: Configure Nginx

Create `/etc/nginx/sites-available/gameready`:
```bash
sudo nano /etc/nginx/sites-available/gameready
```

Add:
```nginx
server {
    listen 80;
    server_name start.gamereadyapp.com www.start.gamereadyapp.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        alias /var/www/gameready/staticfiles/;
    }
    
    location /media/ {
        alias /var/www/gameready/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/gameready/gameready.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/gameready /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Step 10: Set Up SSL Certificate (HTTPS)

```bash
sudo certbot --nginx -d start.gamereadyapp.com -d www.start.gamereadyapp.com
```

Follow the prompts. Certbot will automatically configure Nginx for HTTPS.

---

## Step 11: Set Permissions

```bash
sudo chown -R www-data:www-data /var/www/gameready
sudo chmod -R 755 /var/www/gameready
sudo chmod 600 /var/www/gameready/.env
```

---

## Step 12: Verify Deployment

1. Visit `https://start.gamereadyapp.com` in your browser
2. Check logs if there are issues:
   ```bash
   sudo journalctl -u gameready -f
   sudo tail -f /var/log/nginx/error.log
   ```

---

## Maintenance Commands

### Restart Application
```bash
sudo systemctl restart gameready
```

### View Application Logs
```bash
sudo journalctl -u gameready -f
```

### Update Code
```bash
cd /var/www/gameready
source venv/bin/activate
git pull  # or upload new files
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gameready
```

### Backup Database
```bash
sudo -u postgres pg_dump gameready_db > backup_$(date +%Y%m%d).sql
```

---

## Troubleshooting

### Check Gunicorn Status
```bash
sudo systemctl status gameready
```

### Check Nginx Status
```bash
sudo systemctl status nginx
```

### Test Nginx Configuration
```bash
sudo nginx -t
```

### View Nginx Error Logs
```bash
sudo tail -f /var/log/nginx/error.log
```

### Check Django Logs
```bash
sudo journalctl -u gameready -n 50
```

---

## Security Checklist

- [ ] `DEBUG = False` in production settings
- [ ] `SECRET_KEY` is secure and in `.env` file
- [ ] `.env` file has correct permissions (600)
- [ ] SSL certificate is installed and auto-renewing
- [ ] Database password is strong
- [ ] Firewall is configured (UFW)
- [ ] Regular backups are scheduled
- [ ] Static files are being served correctly

---

## Optional: Set Up Firewall

```bash
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw enable
```

---

## Next Steps

1. Set up automated backups
2. Configure monitoring (e.g., Sentry for error tracking)
3. Set up email service for password resets
4. Configure log rotation
5. Set up CI/CD pipeline

---

**Need help?** Check Django deployment documentation: https://docs.djangoproject.com/en/5.2/howto/deployment/

