# 🚀 Deploy Instructions - Version 2.0 (PostgreSQL + Next.js)

## ⚠️ IMPORTANT: Do This BEFORE Deploying

### Step 1: Add PostgreSQL to Railway Project

1. **Go to Railway Dashboard**
   - URL: https://railway.app/project/a89ce437-4398-43a9-9352-9dae7178545b

2. **Add PostgreSQL Database**
   - Click **"+ New"**
   - Select **"Database"**
   - Choose **"Add PostgreSQL"**
   - Wait for provisioning (1-2 minutes)

3. **Verify DATABASE_URL**
   - Click on the PostgreSQL service
   - Go to **"Variables"** tab
   - You should see `DATABASE_URL` automatically created
   - Format: `postgresql://user:pass@host:port/db`

### Step 2: Add Environment Variables to Your Service

1. **Click on your main service** (mvp-ranksimulator)
2. **Go to "Variables" tab**
3. **Add these variables**:

```
SECRET_KEY=<generate-random-32-char-string>
JWT_SECRET_KEY=<generate-random-32-char-string>
GEMINI_API_KEY=AIzaSyDD_lRQ99lz0R_J5_vOspGtF5ITA2DmRHM
```

**Generate secret keys**:
```bash
# Run this twice to get two different keys
python -c "import secrets; print(secrets.token_hex(32))"
```

4. **Connect to PostgreSQL**
   - In your service variables, click **"+ New Variable"**
   - Click **"Add Reference"**
   - Select your PostgreSQL database
   - Choose `DATABASE_URL`
   - This will link the database to your service

### Step 3: Deploy Backend

```bash
cd c:\Users\ciopp\Desktop\ranksimulatoraudit
railway up --detach
```

### Step 4: Check Deployment Logs

```bash
railway logs
```

**Look for**:
```
Creating database tables...
✅ Database tables created!
Creating admin user...
✅ Admin user created!
   Email: ciccioragusa@gmail.com
   Password: 12345Aa!
```

### Step 5: Test API

```bash
# Test root endpoint
curl https://mvp-ranksimulator-production.up.railway.app/

# Test login
curl -X POST https://mvp-ranksimulator-production.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ciccioragusa@gmail.com","password":"12345Aa!"}'
```

---

## 📊 What Changed

### Backend (Flask API)

#### New Features
- ✅ **PostgreSQL Database** - User and analysis storage
- ✅ **JWT Authentication** - Secure token-based auth
- ✅ **User Management** - CRUD operations for users
- ✅ **Analysis History** - Save and retrieve past analyses
- ✅ **Admin User** - Pre-configured admin account
- ✅ **CORS Enabled** - Ready for Next.js frontend

#### New Endpoints

**Authentication**
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info
- `GET /api/auth/users` - List all users (admin only)
- `PUT /api/auth/users/<id>` - Update user
- `DELETE /api/auth/users/<id>` - Delete user (admin only)

**Analysis**
- `POST /api/analyze` - Start analysis (requires JWT)
- `GET /api/status/<job_id>` - Check analysis status (requires JWT)
- `GET /api/history` - Get user's analysis history (requires JWT)
- `GET /api/history/<id>` - Get specific analysis (requires JWT)
- `DELETE /api/history/<id>` - Delete analysis (requires JWT)

#### Database Schema

**Users Table**
```sql
id, email, password_hash, name, role, created_at, updated_at
```

**Analyses Table**
```sql
id, user_id, url, entity, language, ai_visibility_score, 
total_queries, covered_queries, result_data (JSON), created_at
```

---

## 🎨 Frontend Setup (Next.js + TailAdmin)

### Current Status
- ✅ TailAdmin cloned to `frontend/` directory
- ⏳ Need to configure API connection
- ⏳ Need to customize for AI Visibility
- ⏳ Need to deploy to Railway or Vercel

### Next Steps for Frontend

#### 1. Install Dependencies
```bash
cd frontend
npm install
```

#### 2. Configure API URL
Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=https://mvp-ranksimulator-production.up.railway.app
```

#### 3. Run Development Server
```bash
npm run dev
```

Frontend will be at: http://localhost:3000

#### 4. Customize Dashboard
- Remove unnecessary menu items
- Add "AI Visibility" menu item
- Create analysis page with input and charts
- Integrate with backend API

---

## 🔐 Admin Credentials

**Email**: ciccioragusa@gmail.com  
**Password**: 12345Aa!  
**Role**: admin

### Change Password

```bash
# Via Railway CLI
railway run python

# In Python shell
>>> from app import app, db
>>> from models import User
>>> with app.app_context():
...     admin = User.query.filter_by(email='ciccioragusa@gmail.com').first()
...     admin.set_password('your-new-password')
...     db.session.commit()
...     print('Password updated!')
```

---

## 📝 API Usage Example

### 1. Login
```javascript
const response = await fetch('https://mvp-ranksimulator-production.up.railway.app/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'ciccioragusa@gmail.com',
    password: '12345Aa!'
  })
});

const { access_token, user } = await response.json();
localStorage.setItem('token', access_token);
```

### 2. Start Analysis
```javascript
const token = localStorage.getItem('token');

const response = await fetch('https://mvp-ranksimulator-production.up.railway.app/api/analyze', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    url: 'https://example.com'
  })
});

const { job_id } = await response.json();
```

### 3. Poll for Results
```javascript
const checkStatus = async (jobId) => {
  const response = await fetch(
    `https://mvp-ranksimulator-production.up.railway.app/api/status/${jobId}`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  
  const data = await response.json();
  
  if (data.status === 'completed') {
    return data.result;
  } else if (data.status === 'processing') {
    // Poll again after 1 second
    await new Promise(resolve => setTimeout(resolve, 1000));
    return checkStatus(jobId);
  } else {
    throw new Error(data.error);
  }
};

const result = await checkStatus(job_id);
```

### 4. Get History
```javascript
const response = await fetch(
  'https://mvp-ranksimulator-production.up.railway.app/api/history?page=1&per_page=10',
  {
    headers: { 'Authorization': `Bearer ${token}` }
  }
);

const { analyses, total, pages } = await response.json();
```

---

## 🐛 Troubleshooting

### Database Connection Error
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Fix**: 
1. Check PostgreSQL is running in Railway
2. Verify `DATABASE_URL` variable is set
3. Check database reference is added to service

### Admin User Not Created
```bash
# Manually run init script
railway run python init_db.py
```

### JWT Token Errors
```
Error: Signature verification failed
```

**Fix**: Ensure `JWT_SECRET_KEY` is set and consistent

### CORS Errors in Frontend
```
Access to fetch blocked by CORS policy
```

**Fix**: Backend already has CORS enabled for `/api/*` routes

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────┐
│           Next.js Frontend (TailAdmin)          │
│              Port 3000 (local)                  │
│         or Vercel (production)                  │
└────────────────┬────────────────────────────────┘
                 │ HTTP/HTTPS + JWT
                 ▼
┌─────────────────────────────────────────────────┐
│         Flask API Backend (Railway)             │
│   https://mvp-ranksimulator-production...       │
│                                                 │
│  ┌──────────────┐      ┌──────────────┐        │
│  │ Auth Routes  │      │ Analysis API │        │
│  │ /api/auth/*  │      │ /api/analyze │        │
│  └──────────────┘      └──────────────┘        │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│      PostgreSQL Database (Railway)              │
│                                                 │
│  ┌──────────┐         ┌──────────────┐         │
│  │  Users   │────────▶│  Analyses    │         │
│  └──────────┘         └──────────────┘         │
└─────────────────────────────────────────────────┘
```

---

## ✅ Deployment Checklist

### Backend
- [x] PostgreSQL added to Railway
- [x] Environment variables configured
- [x] Code committed and pushed
- [ ] Deploy to Railway
- [ ] Verify database initialization
- [ ] Test API endpoints
- [ ] Test admin login

### Frontend
- [x] TailAdmin cloned
- [ ] Dependencies installed
- [ ] API URL configured
- [ ] Customize dashboard
- [ ] Add AI Visibility page
- [ ] Integrate with backend
- [ ] Deploy to Vercel/Railway

---

## 🚀 Ready to Deploy!

Run this command when PostgreSQL is configured:

```bash
railway up --detach
```

Then check logs:

```bash
railway logs
```

---

*Deployment guide created: November 5, 2025 at 1:15 PM*
