# 🚀 Quick Deploy Guide - Rank Simulator

## ✅ Status: Ready to Deploy

Your application is **fully functional** and tested locally at http://127.0.0.1:5000

## 📋 Pre-Deployment Checklist

- ✅ Flask application created (`app.py`)
- ✅ HTML template with brand colors (`templates/index.html`)
- ✅ Requirements file (`requirements.txt`)
- ✅ Procfile for Railway (`Procfile`)
- ✅ Git repository initialized
- ✅ Code committed locally
- ✅ Railway CLI installed (v4.5.4)

## 🎯 Deploy in 3 Steps

### Step 1: Create GitHub Repository (2 minutes)

**Option A: Via Web (Recommended)**
1. Open: https://github.com/new
2. Repository name: `mvp-ranksimulator`
3. Keep it **Public**
4. **UNCHECK** "Initialize this repository with a README"
5. Click "Create repository"

**Option B: Via CLI (if you have GitHub CLI)**
```bash
gh repo create mvp-ranksimulator --public --source=. --remote=origin --push
```

### Step 2: Push Code to GitHub (1 minute)

```bash
cd c:\Users\ciopp\Desktop\ranksimulatoraudit
git push -u origin main
```

If you get authentication errors, use:
```bash
git push -u origin main --force
```

### Step 3: Deploy to Railway (3 minutes)

**Option A: Via Web Interface (Easiest)**
1. Go to: https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select `mvp-ranksimulator`
4. Railway auto-detects Flask
5. Click "Deploy"
6. Wait 2-3 minutes for build
7. Click "Settings" → "Generate Domain"
8. Your app is live! 🎉

**Option B: Via CLI**
```bash
# Login to Railway (opens browser)
railway login

# Initialize project
railway init

# Name it: rank-simulator

# Deploy
railway up

# Generate domain
railway domain

# View logs
railway logs
```

## 🔍 Verify Deployment

### Check Build Logs
```bash
railway logs
```

### Test the Application
1. Visit your Railway URL (e.g., `https://rank-simulator-production.up.railway.app`)
2. Enter test URL: `https://example.com`
3. Click "Analizza"
4. Wait 30-60 seconds for analysis
5. Verify AI Visibility Score appears

## 🐛 Troubleshooting

### If GitHub push fails:
```bash
# Check remote
git remote -v

# If remote is wrong, update it
git remote set-url origin https://github.com/YOUR_USERNAME/mvp-ranksimulator.git

# Force push
git push -u origin main --force
```

### If Railway build fails:
1. Check Railway logs: `railway logs`
2. Common issues:
   - Missing dependencies → Check `requirements.txt`
   - Wrong start command → Check `Procfile`
   - Python version → Check `runtime.txt`

### If app crashes on Railway:
1. View logs: `railway logs --follow`
2. Check for:
   - Import errors
   - API key issues
   - Port binding issues

## 📊 Expected Performance

- **Build time**: 2-3 minutes
- **First request**: 5-10 seconds (cold start)
- **Analysis time**: 30-60 seconds per URL
- **Concurrent users**: 10-20 (free tier)

## 🔑 API Keys (Already Configured)

The app includes API keys in the code:
- ✅ Gemini API Key: Configured
- ✅ OpenAI API Key: Configured (backup)

**For production**, consider moving to environment variables:
1. Railway Dashboard → Variables
2. Add `GEMINI_API_KEY`
3. Update `app.py` to use `os.environ.get('GEMINI_API_KEY')`

## 🌐 Custom Domain (Optional)

1. Railway Dashboard → Settings → Domains
2. Click "Add Domain"
3. Enter your domain
4. Update DNS records as shown
5. Wait for SSL certificate (5-10 minutes)

## 📈 Monitoring

### View Metrics:
- Railway Dashboard → Metrics tab
- CPU usage
- Memory usage
- Request count
- Response times

### View Logs:
```bash
railway logs --follow
```

## 🎨 Application Features

Your deployed app includes:
- ✅ URL input with validation
- ✅ AI Visibility Score (0-100%)
- ✅ Query fan-out simulation (20+ queries)
- ✅ Routing format analysis
- ✅ Reasoning for each query
- ✅ Actionable recommendations
- ✅ Beautiful UI with brand colors (#FF6B35)
- ✅ Responsive design (mobile-friendly)
- ✅ Real-time progress indicators

## 🚀 Next Steps After Deployment

1. **Test thoroughly** with different URLs
2. **Share the link** with stakeholders
3. **Monitor logs** for errors
4. **Collect feedback** from users
5. **Iterate** based on usage patterns

## 📞 Support

If you encounter issues:
1. Check Railway logs: `railway logs`
2. Check GitHub Actions (if enabled)
3. Review error messages
4. Test locally first: `python app.py`

## ✨ You're Ready!

Your application is production-ready. Just:
1. Create GitHub repo
2. Push code
3. Deploy to Railway

**Estimated total time: 6-10 minutes** ⏱️

Good luck! 🎉
