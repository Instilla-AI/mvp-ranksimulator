# Deployment Instructions

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `mvp-ranksimulator`
3. Description: "Rank Simulator - AI Visibility Analyzer"
4. Set to Public or Private
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

## Step 2: Push Code to GitHub

The code is already committed locally. Once the repository is created, run:

```bash
git push -u origin main
```

## Step 3: Deploy to Railway

### Option A: Using Railway CLI

1. Install Railway CLI if not installed:
```bash
npm install -g @railway/cli
```

2. Login to Railway:
```bash
railway login
```

3. Create new project:
```bash
railway init
```
- Select "Empty Project"
- Name it: `rank-simulator`

4. Link to GitHub repository:
```bash
railway link
```

5. Deploy:
```bash
railway up
```

6. Add domain:
```bash
railway domain
```

### Option B: Using Railway Web Interface

1. Go to https://railway.app/
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose `mvp-ranksimulator` repository
5. Railway will auto-detect the Flask app
6. Click "Deploy"
7. Once deployed, click "Settings" → "Generate Domain"

## Step 4: Verify Deployment

### Check logs via CLI:
```bash
railway logs
```

### Check logs via Web:
1. Go to your Railway project
2. Click on the deployment
3. View "Deployments" tab for logs

## Environment Variables (if needed)

If you want to move API keys to environment variables:

1. In Railway dashboard, go to "Variables"
2. Add:
   - `GEMINI_API_KEY`: Your Gemini API key
   - `OPENAI_API_KEY`: Your OpenAI API key (if used)
   - `PORT`: 5000 (Railway sets this automatically)

3. Update `app.py` to use:
```python
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'your-default-key')
```

## Troubleshooting

### If Railway build fails:
- Check that `requirements.txt` has all dependencies
- Check that `Procfile` is correct: `web: gunicorn app:app`
- Check Railway logs for specific errors

### If app doesn't start:
- Ensure PORT is set correctly (Railway provides this)
- Check that Flask app is named `app` in `app.py`
- Verify all imports are in `requirements.txt`

## Quick Deploy Commands

```bash
# After creating GitHub repo
git push -u origin main

# Deploy to Railway
railway login
railway init
railway up
railway logs

# Get deployment URL
railway domain
```

## Application URL

Once deployed, your app will be available at:
- Railway: `https://rank-simulator-production.up.railway.app` (or similar)
- Custom domain can be added in Railway settings

## Testing the Deployed App

1. Visit the deployment URL
2. Enter a URL to analyze (e.g., https://example.com)
3. Click "Analizza"
4. Wait for results (may take 30-60 seconds)
5. Review AI Visibility Score and recommendations
