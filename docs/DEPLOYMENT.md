# 🚀 Deployment Guide

Complete guide for deploying WhatsApp Sales Agent Pro to production environments.

## 🌐 Deployment Options

### 1. Heroku (Recommended for beginners)
### 2. AWS EC2 (Scalable)
### 3. Docker (Containerized)
### 4. DigitalOcean (Cost-effective)

---

## 🟣 Heroku Deployment

### Prerequisites
- Heroku account
- Heroku CLI installed
- Git repository

### Step 1: Prepare for Heroku

Create `Procfile`:
```
web: python src/whatsapp_integration.py
```

Create `runtime.txt`:
```
python-3.11.0
```

Update `config/requirements.txt` with production dependencies:
```
flask==2.3.3
requests==2.31.0
python-dotenv==1.0.0
streamlit==1.28.0
phi-ai==2.4.0
google-generativeai==0.3.0
duckduckgo-search==3.9.0
tenacity==8.2.3
gunicorn==21.2.0
```

### Step 2: Deploy to Heroku

```bash
# Login to Heroku
heroku login

# Create Heroku app
heroku create your-whatsapp-bot

# Set environment variables
heroku config:set GOOGLE_API_KEY=your_google_api_key
heroku config:set WHATSAPP_ACCESS_TOKEN=your_access_token
heroku config:set WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
heroku config:set WHATSAPP_VERIFY_TOKEN=sales_agent_verify_token

# Deploy
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

### Step 3: Configure Webhook

Update Meta Developer Console webhook URL:
```
https://your-whatsapp-bot.herokuapp.com/webhook
```

### Step 4: Scale and Monitor

```bash
# Scale dynos
heroku ps:scale web=1

# View logs
heroku logs --tail

# Check status
heroku ps
```

---

## 🟠 AWS EC2 Deployment

### Prerequisites
- AWS account
- EC2 instance (t2.micro for testing)
- Security group configured

### Step 1: Launch EC2 Instance

1. **Create EC2 Instance**
   - AMI: Ubuntu 22.04 LTS
   - Instance type: t2.micro (free tier)
   - Security group: Allow HTTP (80), HTTPS (443), SSH (22)

2. **Connect to Instance**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```

### Step 2: Setup Environment

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv nginx -y

# Clone repository
git clone https://github.com/shamil3923/ERP_Recommendation_Widget-.git
cd Task_02

# Create virtual environment
python3 -m venv sales_agent_env
source sales_agent_env/bin/activate

# Install dependencies
pip install -r config/requirements.txt
pip install gunicorn
```

### Step 3: Configure Environment

```bash
# Create environment file
nano config/.env
# Add your environment variables

# Test the application
python src/whatsapp_integration.py
```

### Step 4: Setup Gunicorn

Create `gunicorn.conf.py`:
```python
bind = "0.0.0.0:5000"
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

### Step 5: Setup Systemd Service

Create `/etc/systemd/system/whatsapp-bot.service`:
```ini
[Unit]
Description=WhatsApp Sales Agent
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/Task_02
Environment=PATH=/home/ubuntu/Task_02/sales_agent_env/bin
ExecStart=/home/ubuntu/Task_02/sales_agent_env/bin/gunicorn --config gunicorn.conf.py src.whatsapp_integration:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable whatsapp-bot
sudo systemctl start whatsapp-bot
sudo systemctl status whatsapp-bot
```

### Step 6: Setup Nginx

Create `/etc/nginx/sites-available/whatsapp-bot`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/whatsapp-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 7: Setup SSL (Optional)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

---

## 🐳 Docker Deployment

### Step 1: Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY config/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port
EXPOSE 5000

# Run application
CMD ["python", "src/whatsapp_integration.py"]
```

### Step 2: Create docker-compose.yml

```yaml
version: '3.8'

services:
  whatsapp-bot:
    build: .
    ports:
      - "5000:5000"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - WHATSAPP_ACCESS_TOKEN=${WHATSAPP_ACCESS_TOKEN}
      - WHATSAPP_PHONE_NUMBER_ID=${WHATSAPP_PHONE_NUMBER_ID}
      - WHATSAPP_VERIFY_TOKEN=${WHATSAPP_VERIFY_TOKEN}
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - whatsapp-bot
    restart: unless-stopped
```

### Step 3: Deploy with Docker

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f whatsapp-bot

# Scale service
docker-compose up -d --scale whatsapp-bot=3
```

---

## 🌊 DigitalOcean Deployment

### Step 1: Create Droplet

1. **Create Droplet**
   - Image: Ubuntu 22.04
   - Size: Basic $6/month
   - Add SSH key

2. **Connect and Setup**
   ```bash
   ssh root@your-droplet-ip
   ```

### Step 2: Setup Application

Follow AWS EC2 steps 2-6 (same process)

### Step 3: Setup Domain (Optional)

1. **Configure DNS**
   - Point domain to droplet IP
   - Add A record: `@ -> your-droplet-ip`
   - Add CNAME: `www -> @`

2. **Setup SSL**
   ```bash
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

---

## 📊 Production Configuration

### Environment Variables

```env
# Production settings
FLASK_ENV=production
DEBUG=False
LOG_LEVEL=WARNING

# API Keys (use secure storage)
GOOGLE_API_KEY=your_production_key
WHATSAPP_ACCESS_TOKEN=your_production_token
WHATSAPP_PHONE_NUMBER_ID=your_production_id
WHATSAPP_VERIFY_TOKEN=your_secure_token

# Database (if using)
DATABASE_URL=postgresql://user:pass@host:port/db

# Redis (for caching)
REDIS_URL=redis://localhost:6379/0
```

### Security Checklist

- [ ] Use HTTPS in production
- [ ] Set secure environment variables
- [ ] Enable firewall (UFW on Ubuntu)
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Use strong passwords/keys
- [ ] Implement rate limiting
- [ ] Set up backup strategy

### Performance Optimization

```python
# gunicorn.conf.py for production
bind = "0.0.0.0:5000"
workers = 4  # 2 * CPU cores
worker_class = "gevent"
worker_connections = 1000
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

### Monitoring Setup

1. **Application Monitoring**
   ```bash
   # Install monitoring tools
   pip install prometheus-client
   pip install sentry-sdk[flask]
   ```

2. **System Monitoring**
   ```bash
   # Install htop, netstat
   sudo apt install htop net-tools
   
   # Monitor processes
   htop
   
   # Monitor network
   netstat -tulpn
   ```

3. **Log Management**
   ```python
   # In whatsapp_integration.py
   import logging
   from logging.handlers import RotatingFileHandler
   
   handler = RotatingFileHandler('logs/app.log', maxBytes=10000000, backupCount=5)
   handler.setLevel(logging.INFO)
   app.logger.addHandler(htop)
   ```

---

## 🔧 Maintenance

### Regular Tasks

1. **Update Dependencies**
   ```bash
   pip list --outdated
   pip install --upgrade package_name
   ```

2. **Monitor Logs**
   ```bash
   tail -f /var/log/nginx/access.log
   tail -f logs/app.log
   ```

3. **Backup Configuration**
   ```bash
   # Backup environment and config
   tar -czf backup-$(date +%Y%m%d).tar.gz config/ src/
   ```

4. **Monitor Resources**
   ```bash
   # Check disk space
   df -h
   
   # Check memory
   free -h
   
   # Check CPU
   top
   ```

### Troubleshooting

1. **Service Not Starting**
   ```bash
   sudo systemctl status whatsapp-bot
   sudo journalctl -u whatsapp-bot -f
   ```

2. **High Memory Usage**
   ```bash
   # Check memory usage
   ps aux --sort=-%mem | head
   
   # Restart service
   sudo systemctl restart whatsapp-bot
   ```

3. **SSL Certificate Issues**
   ```bash
   # Check certificate
   sudo certbot certificates
   
   # Renew certificate
   sudo certbot renew
   ```

---

## 📈 Scaling

### Horizontal Scaling

1. **Load Balancer Setup**
   ```nginx
   upstream whatsapp_backend {
       server 127.0.0.1:5000;
       server 127.0.0.1:5001;
       server 127.0.0.1:5002;
   }
   
   server {
       location / {
           proxy_pass http://whatsapp_backend;
       }
   }
   ```

2. **Multiple Workers**
   ```bash
   # Run multiple instances
   gunicorn --workers 4 --bind 0.0.0.0:5000 src.whatsapp_integration:app
   ```

### Database Integration

For high-volume deployments, consider:
- PostgreSQL for user sessions
- Redis for caching
- MongoDB for conversation history

---

**Your WhatsApp Sales Agent is now ready for production! 🚀**

For support, see [SETUP_GUIDE.md](SETUP_GUIDE.md) or create an issue on GitHub.
