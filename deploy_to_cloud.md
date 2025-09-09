# 🌐 Deploy Velora Demo to Cloud for Mobile Access

Since Cursor's environment doesn't allow external access, here are FREE options to deploy the demo for mobile access:

## 🚀 **Option 1: Deploy to Render (Recommended - FREE)**

### Steps:
1. **Push code to GitHub**
2. **Go to [render.com](https://render.com)**
3. **Sign up for free account**
4. **Create New > Web Service**
5. **Connect your GitHub repo**
6. **Configure:**
   ```yaml
   Build Command: pip install -r requirements.txt
   Start Command: python demo/standalone_server.py
   ```
7. **Deploy!**
8. **Get URL like:** `https://velora-demo.onrender.com`

### Render Deploy File:
```yaml
# render.yaml
services:
  - type: web
    name: velora-demo
    env: python
    buildCommand: pip install fastapi uvicorn httpx
    startCommand: python demo/standalone_server.py
    envVars:
      - key: PORT
        value: 8001
```

## 🔷 **Option 2: Deploy to Railway (FREE Trial)**

### Steps:
1. **Go to [railway.app](https://railway.app)**
2. **Sign up with GitHub**
3. **New Project > Deploy from GitHub**
4. **Select your repo**
5. **Auto-deploys!**
6. **Get URL like:** `https://velora-demo.up.railway.app`

## 🟢 **Option 3: Deploy to Replit (FREE)**

### Steps:
1. **Go to [replit.com](https://replit.com)**
2. **Create new Repl > Import from GitHub**
3. **Run these in Shell:**
   ```bash
   pip install fastapi uvicorn httpx
   python demo/standalone_server.py
   ```
4. **Replit provides public URL automatically!**

## 🔵 **Option 4: Deploy to Heroku (FREE tier limited)**

### Create these files:

**Procfile:**
```
web: uvicorn demo.standalone_server:app --host 0.0.0.0 --port $PORT
```

**runtime.txt:**
```
python-3.11.0
```

**requirements.txt:**
```
fastapi==0.104.1
uvicorn==0.24.0
httpx==0.25.1
```

### Deploy:
```bash
heroku create velora-demo
git push heroku main
```

## 🟡 **Option 5: Use Gitpod (FREE 50hrs/month)**

1. **Add this to your repo README:**
   ```markdown
   [![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/YOUR_USERNAME/velora)
   ```

2. **Create `.gitpod.yml`:**
   ```yaml
   tasks:
     - init: pip install fastapi uvicorn httpx
       command: python demo/standalone_server.py
   ports:
     - port: 8001
       visibility: public
   ```

## 📱 **Option 6: Use ngrok (Temporary Tunnel)**

If you can run the demo on YOUR local machine:

1. **Install ngrok:**
   ```bash
   # Mac
   brew install ngrok
   
   # Windows
   choco install ngrok
   
   # Linux
   snap install ngrok
   ```

2. **Run demo locally:**
   ```bash
   python demo/standalone_server.py
   ```

3. **Create tunnel:**
   ```bash
   ngrok http 8001
   ```

4. **Get public URL like:** `https://abc123.ngrok.io`

## 🌟 **Option 7: Use Localhost.run (No Install)**

On YOUR local machine:
```bash
# Start demo
python demo/standalone_server.py

# In another terminal:
ssh -R 80:localhost:8001 localhost.run
```

You'll get a public URL immediately!

## 📲 **Quick Comparison**

| Service | Free Tier | Setup Time | Best For |
|---------|-----------|------------|----------|
| **Render** | ✅ 750hrs | 5 min | Production demo |
| **Railway** | ✅ $5 credit | 3 min | Quick deploy |
| **Replit** | ✅ Always on | 2 min | Development |
| **Heroku** | ⚠️ Limited | 10 min | Professional |
| **Gitpod** | ✅ 50hrs | 5 min | Development |
| **ngrok** | ✅ Temporary | 1 min | Quick test |
| **localhost.run** | ✅ Temporary | 30 sec | Instant demo |

## 🎯 **Recommended for Mobile Demo**

### For Quick Test (5 minutes):
1. Use **localhost.run** - No signup needed!
2. Run on your local machine
3. Share URL with mobile

### For Presentation (1 hour):
1. Use **Render.com** - Free & reliable
2. Deploy once, use anywhere
3. Custom domain possible

### For Development:
1. Use **Replit** - Edit & run in browser
2. Automatic URL
3. Collaborative editing

---

## 🚀 **Fastest Option Right Now**

Since you want to access from mobile immediately:

1. **Download the code to YOUR computer**
2. **Run this:**
   ```bash
   cd velora
   python3 demo/standalone_server.py
   ```
3. **Find your computer's IP:**
   - Windows: `ipconfig`
   - Mac/Linux: `ifconfig` or `ip addr`
4. **On your mobile (same WiFi):**
   - Open browser
   - Go to: `http://[YOUR-COMPUTER-IP]:8001`

Example: `http://192.168.1.100:8001`

This works immediately without any cloud deployment!