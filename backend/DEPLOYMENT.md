# Deployment Guide - Night Plate Detection System

## 🚀 Production Deployment Checklist

### Prerequisites
- Python 3.8+
- MongoDB Atlas account (or local MongoDB)
- Sufficient RAM (min 4GB, recommended 8GB+)
- GPU (optional but recommended for better performance)

---

## 📋 Pre-Deployment Steps

### 1. Environment Configuration

Create/Update `.env` file:
```env
# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:<db_password>@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=night_plate_detection

# JWT Configuration (CHANGE THESE IN PRODUCTION!)
JWT_SECRET_KEY=your-super-secret-key-min-32-chars-long-change-this
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Security
PASSWORD_MIN_LENGTH=8

# Application
APP_NAME=Night Plate Detection
APP_VERSION=1.0.0
```

**⚠️ IMPORTANT:**
- Replace `<db_password>` with actual MongoDB password
- Generate strong JWT_SECRET_KEY (use: `python -c "import secrets; print(secrets.token_hex(32))"`)
- Never commit `.env` to version control!

---

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

---

### 3. Verify Models

Ensure models exist:
```
models/
  ├── yolov8x.pt      # Main detection model (nighttime trained)
  └── yolov8x.onnx    # Optional: ONNX version
```

Download if missing:
```bash
# YOLOv8x from Ultralytics (use your trained best.pt file)
cp /path/to/your/best.pt models/yolov8x.pt
```

---

### 4. MongoDB Setup

#### Option A: MongoDB Atlas (Cloud - Recommended)

1. Create account at https://www.mongodb.com/cloud/atlas
2. Create cluster (Free tier available)
3. Set up database user
4. Whitelist IP addresses (0.0.0.0/0 for testing, specific IPs for production)
5. Get connection string
6. Update MONGODB_URI in `.env`

#### Option B: Local MongoDB

1. Install MongoDB locally
2. Start MongoDB service:
   ```bash
   # Windows
   net start MongoDB
   
   # Linux
   sudo systemctl start mongod
   ```
3. Use local URI: `mongodb://localhost:27017/`

---

### 5. Database Indexing (Performance)

Run once to create indexes:
```bash
python -c "from database.mongodb_client import mongodb_client; mongodb_client.setup_indexes()"
```

This creates indexes on:
- `user_id` (detections)
- `tracking_id` (detections)
- `session_id` (detections)
- `timestamp` (detections)
- `username` (users)
- `email` (users)

---

## 🖥️ Deployment Options

### Option 1: Local Server

```bash
# Activate environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Run Streamlit
streamlit run streamlit_app/streamlit_app_auth.py

# Access at: http://localhost:8501
```

---

### Option 2: Docker Deployment

**Dockerfile** (already included in project):
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "streamlit_app/streamlit_app_auth.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Build and Run:**
```bash
# Build image
docker build -t night-plate-detection .

# Run container
docker run -p 8501:8501 --env-file .env night-plate-detection

# With GPU support (NVIDIA Docker)
docker run --gpus all -p 8501:8501 --env-file .env night-plate-detection
```

---

### Option 3: Streamlit Cloud (Free Hosting)

1. Push code to GitHub (exclude `.env`, `venv/`, `data/`)
2. Go to https://share.streamlit.io
3. Connect GitHub repository
4. Set deployment branch (main)
5. Add secrets in Streamlit Cloud settings:
   - Copy `.env` contents to Secrets section
6. Deploy!

**Note:** Free tier limitations:
- 1GB RAM
- CPU only (no GPU)
- Public access only

---

### Option 4: Cloud VM (AWS/GCP/Azure)

#### AWS EC2 Example:

1. **Launch EC2 Instance:**
   - Instance type: t2.medium (4GB RAM) or better
   - OS: Ubuntu 20.04 LTS
   - Security Group: Open port 8501

2. **SSH into instance:**
   ```bash
   ssh -i your-key.pem ubuntu@ec2-xx-xx-xx-xx.compute.amazonaws.com
   ```

3. **Setup:**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python
   sudo apt install python3-pip python3-venv -y
   
   # Clone repository
   git clone https://github.com/your-repo/night-plate-detection.git
   cd night-plate-detection
   
   # Setup environment
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Create .env file
   nano .env
   # (paste configuration)
   
   # Run with nohup (background)
   nohup streamlit run streamlit_app/streamlit_app_auth.py &
   ```

4. **Access:** `http://your-ec2-public-ip:8501`

---

## 🔒 Production Security

### 1. HTTPS/SSL Setup

Use Nginx as reverse proxy:

**Install Nginx:**
```bash
sudo apt install nginx
```

**Configure (`/etc/nginx/sites-available/night-plate`):**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Enable SSL with Let's Encrypt:**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

### 2. Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

---

### 3. Environment Variables

Never hardcode sensitive data. Always use:
- Environment variables (`.env`)
- Cloud secrets manager (AWS Secrets Manager, Azure Key Vault)
- Docker secrets

---

### 4. User Authentication

✅ Already implemented:
- JWT tokens
- Password hashing (bcrypt)
- Session management

**Additional recommendations:**
- Enable HTTPS in production
- Implement rate limiting
- Add CAPTCHA for registration
- Enable 2FA (future enhancement)

---

## 📊 Monitoring & Logging

### Application Logs

Monitor Streamlit logs:
```bash
# View logs
tail -f ~/.streamlit/logs/streamlit.log

# Docker logs
docker logs -f container-name
```

### MongoDB Monitoring

Check database health:
```python
from database.mongodb_client import mongodb_client
stats = mongodb_client.detections.database.command("dbStats")
print(stats)
```

### Resource Monitoring

Install monitoring tools:
```bash
# CPU/Memory monitoring
htop

# GPU monitoring (if available)
nvidia-smi
```

---

## 🎯 Performance Optimization

### 1. Model Optimization

**Use ONNX for faster inference:**
```bash
python scripts/convert_to_onnx.py
```

Update config to use ONNX model:
```python
model_path = "models/yolov8x.onnx"
use_onnx = True
```

### 2. Caching

Already implemented in code:
- Model caching
- Temporal voting (reduces redundant processing)
- Smart database saving (one record per vehicle)

### 3. Database Optimization

**Create compound indexes:**
```python
mongodb_client.detections.create_index([
    ("user_id", 1),
    ("timestamp", -1)
])
```

**Archive old data:**
```python
# Move data older than 30 days to archive collection
from datetime import datetime, timedelta
cutoff = datetime.utcnow() - timedelta(days=30)
mongodb_client.detections_archive.insert_many(
    mongodb_client.detections.find({"timestamp": {"$lt": cutoff}})
)
mongodb_client.detections.delete_many({"timestamp": {"$lt": cutoff}})
```

---

## 🧪 Testing Before Deployment

### 1. Functional Tests

```bash
# Test database connection
python -c "from database.mongodb_client import mongodb_client; print('✓ MongoDB connected')"

# Test models
python core/detector.py
python core/ocr.py

# Test authentication
python -c "from auth.jwt_handler import JWTHandler; h = JWTHandler(); print('✓ JWT working')"
```

### 2. Load Testing

Use sample video:
```bash
python scripts/benchmark_fps.py
```

### 3. Security Audit

- Check `.env` is in `.gitignore`
- Verify strong JWT secret
- Test authentication flow
- Validate input sanitization

---

## 🔄 CI/CD Pipeline (Optional)

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          python -m pytest tests/
      
      - name: Deploy to server
        env:
          SSH_KEY: ${{ secrets.SSH_KEY }}
        run: |
          ssh user@server 'cd /app && git pull && systemctl restart night-plate'
```

---

## 📱 Mobile/Edge Deployment

For deployment on edge devices (Jetson Nano, Raspberry Pi):

1. **Optimize model:**
   ```bash
   python scripts/quantize_model.py  # INT8 quantization
   ```

2. **Use lighter model:**
   - YOLOv8n.pt (nano) instead of YOLOv9c
   - Reduces accuracy but 10x faster

3. **Adjust settings:**
   - Lower resolution
   - Reduce preprocessing
   - Increase frame skip

---

## 🐛 Troubleshooting

### Common Issues:

**1. "Failed to connect to MongoDB"**
- Check MONGODB_URI in `.env`
- Verify network connectivity
- Check firewall rules
- Whitelist IP in MongoDB Atlas

**2. "Model not found"**
- Ensure `models/yolov8x.pt` exists
- Copy your trained best.pt to models/yolov8x.pt
- Or download from Ultralytics: `yolo download yolov8x.pt`

**3. "Out of memory"**
- Reduce batch size
- Use smaller model
- Enable ONNX
- Add more RAM

**4. "Low FPS"**
- Enable GPU
- Use ONNX model
- Reduce frame resolution
- Skip frames (process every 2nd frame)

---

## 📚 Maintenance

### Regular Tasks:

**Daily:**
- Monitor error logs
- Check disk space

**Weekly:**
- Database backup
- Review detection accuracy
- Check user feedback

**Monthly:**
- Update dependencies: `pip install --upgrade -r requirements.txt`
- Security audit
- Performance optimization

### Backup Strategy:

```bash
# MongoDB backup
mongodump --uri="$MONGODB_URI" --out=backup/$(date +%Y%m%d)

# Restore
mongorestore --uri="$MONGODB_URI" backup/20250112/
```

---

## 🎓 Next Steps

After deployment:

1. **User Training** - Create documentation for end users
2. **Monitoring Setup** - Implement APM (Application Performance Monitoring)
3. **Analytics** - Track detection accuracy, user activity
4. **Scaling** - Add load balancer for high traffic
5. **Updates** - Regular model retraining with new data

---

## 📞 Support

For issues:
1. Check logs first
2. Review this deployment guide
3. Check GitHub issues
4. Contact: your-email@domain.com

---

**Deployment Date:** ___________  
**Deployed By:** ___________  
**Environment:** ☐ Development  ☐ Staging  ☐ Production  
**Status:** ☐ Success  ☐ Pending  ☐ Failed

---

## ✅ Post-Deployment Verification

- [ ] Application accessible at deployment URL
- [ ] User registration working
- [ ] User login working
- [ ] Video detection functional
- [ ] MongoDB saving data correctly
- [ ] No duplicate records
- [ ] OCR accuracy acceptable
- [ ] Performance metrics within limits
- [ ] HTTPS enabled (production)
- [ ] Backups configured
- [ ] Monitoring active
- [ ] Documentation complete

**Congratulations! Your Night Plate Detection System is ready for production! 🎉**
