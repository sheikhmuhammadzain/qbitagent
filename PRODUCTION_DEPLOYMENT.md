# 🚀 Production Deployment Guide

## Critical Fixes Applied

### ✅ Fixed Issues That Prevented SQLite MCP Server from Working in Production

#### **Issue 1: Hardcoded `python` Command**
**Before:**
```python
command="python",  # ❌ Doesn't exist on Linux servers
```

**After:**
```python
command=sys.executable,  # ✅ Uses current Python interpreter
```

**Why:** Most Linux servers use `python3` command, not `python`. Using `sys.executable` ensures we use the correct Python interpreter, including when running in virtual environments.

---

#### **Issue 2: Relative Script Paths**
**Before:**
```python
args=["sqlite_mcp_fastmcp.py", "example.db"]  # ❌ Assumes current working directory
```

**After:**
```python
current_dir = Path(__file__).parent.resolve()
sqlite_server_script = str(current_dir / "sqlite_mcp_fastmcp.py")
args=["-u", sqlite_server_script, default_db]  # ✅ Absolute paths
```

**Why:** Process managers (systemd, supervisor, PM2) may start the application from any directory. Absolute paths ensure the script is always found.

---

#### **Issue 3: Missing Environment Variables**
**Before:**
```python
env=None  # ❌ Subprocess has no access to PATH, etc.
```

**After:**
```python
env=os.environ.copy()  # ✅ Inherits all environment variables
```

**Why:** The subprocess needs access to PATH and other environment variables to function properly, especially in virtual environments.

---

#### **Issue 4: Unbuffered Python Output**
**After:**
```python
args=["-u", sqlite_server_script, ...]  # -u flag for unbuffered output
```

**Why:** The `-u` flag ensures Python output is unbuffered, which is critical for stdio communication between processes.

---

## Deployment Options

### Option 1: systemd (Recommended for Linux Servers)

**1. Create systemd service file:**
```bash
sudo nano /etc/systemd/system/mcp-server.service
```

**2. Add configuration:**
```ini
[Unit]
Description=MCP Server - AI-Powered SQLite Database Assistant
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/mcp-server
Environment="PATH=/path/to/mcp-server/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="OPENROUTER_API_KEY=your-key-here"
Environment="DEFAULT_MODEL=z-ai/glm-4.5-air:free"
ExecStart=/path/to/mcp-server/.venv/bin/python run_fixed.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**3. Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-server
sudo systemctl start mcp-server
sudo systemctl status mcp-server
```

**4. View logs:**
```bash
sudo journalctl -u mcp-server -f
```

---

### Option 2: Docker (Recommended for Portability)

**1. Create Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p uploads static

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV OPENROUTER_API_KEY=""

# Run application
CMD ["python", "run_fixed.py"]
```

**2. Create docker-compose.yml:**
```yaml
version: '3.8'

services:
  mcp-server:
    build: .
    container_name: mcp-server
    ports:
      - "8000:8000"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - DEFAULT_MODEL=z-ai/glm-4.5-air:free
      - SESSION_SECRET=${SESSION_SECRET:-change-me-in-production}
    volumes:
      - ./uploads:/app/uploads
      - ./server.db:/app/server.db
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**3. Deploy:**
```bash
# Create .env file
echo "OPENROUTER_API_KEY=your-key-here" > .env
echo "SESSION_SECRET=$(openssl rand -hex 32)" >> .env

# Build and run
docker-compose up -d

# View logs
docker-compose logs -f
```

---

### Option 3: PM2 (Node.js Process Manager)

**1. Install PM2:**
```bash
npm install -g pm2
```

**2. Create ecosystem.config.js:**
```javascript
module.exports = {
  apps: [{
    name: 'mcp-server',
    script: 'run_fixed.py',
    interpreter: '/path/to/venv/bin/python',
    cwd: '/path/to/mcp-server',
    env: {
      OPENROUTER_API_KEY: 'your-key-here',
      DEFAULT_MODEL: 'z-ai/glm-4.5-air:free',
      SESSION_SECRET: 'your-secret-here'
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
  }]
};
```

**3. Deploy:**
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup  # Follow instructions
```

---

### Option 4: Supervisor

**1. Install supervisor:**
```bash
sudo apt-get install supervisor
```

**2. Create config:**
```bash
sudo nano /etc/supervisor/conf.d/mcp-server.conf
```

```ini
[program:mcp-server]
directory=/path/to/mcp-server
command=/path/to/venv/bin/python run_fixed.py
user=your-username
autostart=true
autorestart=true
stderr_logfile=/var/log/mcp-server.err.log
stdout_logfile=/var/log/mcp-server.out.log
environment=OPENROUTER_API_KEY="your-key-here",DEFAULT_MODEL="z-ai/glm-4.5-air:free"
```

**3. Deploy:**
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start mcp-server
```

---

## Nginx Reverse Proxy (Recommended)

**Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # For Server-Sent Events (streaming)
        proxy_buffering off;
        proxy_read_timeout 300s;
    }

    # Optional: SSL with Let's Encrypt
    # listen 443 ssl;
    # ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
}
```

---

## Production Checklist

### Security
- [ ] Change `SESSION_SECRET` to a strong random value
- [ ] Use HTTPS (SSL/TLS) in production
- [ ] Set proper CORS origins in `.env`: `ALLOWED_ORIGINS=https://your-domain.com`
- [ ] Secure database files with proper permissions
- [ ] Never commit `.env` file to version control
- [ ] Use environment-specific API keys

### Performance
- [ ] Set appropriate worker processes (uvicorn workers)
- [ ] Configure database connection pooling if needed
- [ ] Set up log rotation
- [ ] Monitor memory usage
- [ ] Implement rate limiting if needed

### Monitoring
- [ ] Set up application logging
- [ ] Configure system monitoring (CPU, memory, disk)
- [ ] Set up error tracking (e.g., Sentry)
- [ ] Configure uptime monitoring
- [ ] Set up log aggregation

### Backup
- [ ] Regular backup of `server.db` (user data)
- [ ] Backup uploaded databases in `uploads/`
- [ ] Document restoration procedures
- [ ] Test backup restoration

---

## Environment Variables

**Required:**
```env
OPENROUTER_API_KEY=sk-or-...
```

**Optional:**
```env
DEFAULT_MODEL=z-ai/glm-4.5-air:free
SESSION_SECRET=your-random-secret-here
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
APP_DB_PATH=server.db
DEBUG=false
LOG_LEVEL=INFO
```

**Notion Integration (Optional):**
```env
NOTION_CLIENT_ID=your-client-id
NOTION_CLIENT_SECRET=your-client-secret
NOTION_REDIRECT_URI=https://yourdomain.com/api/notion/callback
```

---

## Troubleshooting Production Issues

### SQLite MCP Server Not Working

**Check 1: Verify Python executable**
```bash
which python3
# Should match sys.executable in your app
```

**Check 2: Verify script paths**
```bash
ls -la /path/to/mcp-server/sqlite_mcp_fastmcp.py
# Should exist and be readable
```

**Check 3: Check process logs**
```bash
# systemd
sudo journalctl -u mcp-server -n 100

# docker
docker logs mcp-server -f

# pm2
pm2 logs mcp-server
```

**Check 4: Test subprocess manually**
```bash
cd /path/to/mcp-server
/path/to/venv/bin/python -u sqlite_mcp_fastmcp.py example.db
# Should start without errors
```

**Check 5: Verify environment variables**
```bash
# In your app, add logging
import os
print(f"Python: {sys.executable}")
print(f"CWD: {os.getcwd()}")
print(f"Script: {Path(__file__).parent.resolve()}")
```

---

## Performance Tuning

### Run with Multiple Workers
```bash
# In run_fixed.py or command line
uvicorn fastapi_app_fixed:app --host 0.0.0.0 --port 8000 --workers 4
```

### Gunicorn with Uvicorn Workers (Production)
```bash
pip install gunicorn

gunicorn fastapi_app_fixed:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300 \
  --access-logfile - \
  --error-logfile -
```

---

## Migration from Development to Production

**1. Update configuration:**
```bash
# Copy and update environment
cp .env.example .env
nano .env  # Add production values
```

**2. Install production dependencies:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

**3. Test locally first:**
```bash
python run_fixed.py
# Visit http://localhost:8000
```

**4. Deploy using chosen method above**

**5. Verify:**
```bash
curl http://localhost:8000/api
# Should return {"message": "MCP Client API (Fixed)", "status": "running"}
```

---

## Success Indicators

When properly deployed, you should see:

✅ Server starts without errors  
✅ SQLite MCP subprocess spawns successfully  
✅ Database connections work  
✅ Chat responses are generated  
✅ File uploads succeed  
✅ Logs show no path-related errors  

---

## Support

If issues persist after applying these fixes:

1. **Check logs** for specific error messages
2. **Verify paths** are absolute and correct
3. **Test subprocess** spawning manually
4. **Ensure environment variables** are set
5. **Check file permissions** on scripts and databases

---

## Changes Summary

| File | Line | Change | Reason |
|------|------|--------|--------|
| `mcp_client_fixed.py` | 175 | `command="python"` → `command=sys.executable` | Works across environments |
| `mcp_client_fixed.py` | 176 | Relative path → Absolute path | Works with any CWD |
| `mcp_client_fixed.py` | 177 | `env=None` → `env=os.environ.copy()` | Subprocess needs env vars |
| `fastapi_app_fixed.py` | 885-886 | Added absolute path resolution | Production compatibility |
| `fastapi_app_fixed.py` | 887 | `env=None` → `env=os.environ.copy()` | Environment inheritance |

These fixes ensure the SQLite MCP server works in production environments regardless of:
- Working directory
- Python command name (`python` vs `python3`)
- Process manager used
- Virtual environment setup
- Operating system (Linux/Windows/Mac)
