# 🚂 Railway Setup Guide - PostgreSQL + API

## Step 1: Add PostgreSQL Database

### Via Railway Dashboard
1. Go to your Railway project: https://railway.app/project/a89ce437-4398-43a9-9352-9dae7178545b
2. Click **"+ New"** → **"Database"** → **"Add PostgreSQL"**
3. Wait for provisioning (1-2 minutes)
4. PostgreSQL will automatically create `DATABASE_URL` variable

### Via Railway CLI
```bash
railway add --database postgresql
```

---

## Step 2: Configure Environment Variables

### Required Variables

Go to your service settings and add these variables:

```bash
# Database (automatically set by Railway PostgreSQL)
DATABASE_URL=postgresql://...  # Auto-generated

# Security Keys (generate random strings)
SECRET_KEY=your-random-secret-key-here
JWT_SECRET_KEY=your-random-jwt-secret-key-here

# API Keys
GEMINI_API_KEY=AIzaSyDD_lRQ99lz0R_J5_vOspGtF5ITA2DmRHM
OPENAI_API_KEY=sk-proj-...

# Server
PORT=5000
FLASK_ENV=production
```

### Generate Secret Keys

```bash
# In Python
python -c "import secrets; print(secrets.token_hex(32))"
```

Or use online generator: https://randomkeygen.com/

---

## Step 3: Deploy Backend

### Commit and Push
```bash
cd c:\Users\ciopp\Desktop\ranksimulatoraudit

git add -A
git commit -m "Add PostgreSQL, authentication, and API endpoints"
railway up --detach
```

### Wait for Deployment
```bash
railway logs
```

Look for:
```
Creating database tables...
✅ Database tables created!
Creating admin user...
✅ Admin user created!
   Email: ciccioragusa@gmail.com
   Password: 12345Aa!
```

---

## Step 4: Test API Endpoints

### 1. Test Root Endpoint
```bash
curl https://mvp-ranksimulator-production.up.railway.app/
```

Expected:
```json
{
  "message": "Rank Simulator API",
  "version": "2.0",
  "endpoints": {
    "auth": "/api/auth",
    "analyze": "/api/analyze",
    "status": "/api/status/<job_id>",
    "history": "/api/history"
  }
}
```

### 2. Test Login
```bash
curl -X POST https://mvp-ranksimulator-production.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ciccioragusa@gmail.com",
    "password": "12345Aa!"
  }'
```

Expected:
```json
{
  "message": "Login successful",
  "user": {
    "id": 1,
    "email": "ciccioragusa@gmail.com",
    "name": "Admin",
    "role": "admin"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### 3. Test Protected Endpoint
```bash
# Save token from login response
TOKEN="your-access-token-here"

curl https://mvp-ranksimulator-production.up.railway.app/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## Step 5: Setup Frontend (Next.js)

### Install Dependencies
```bash
cd c:\Users\ciopp\Desktop\ranksimulatoraudit\frontend

npm install
# or
yarn install
```

### Configure API URL

Create `.env.local`:
```bash
NEXT_PUBLIC_API_URL=https://mvp-ranksimulator-production.up.railway.app
```

### Run Development Server
```bash
npm run dev
# or
yarn dev
```

Frontend will be available at: http://localhost:3000

---

## API Endpoints Reference

### Authentication

#### Register
```
POST /api/auth/register
Body: { "email": "user@example.com", "password": "password", "name": "Name" }
```

#### Login
```
POST /api/auth/login
Body: { "email": "user@example.com", "password": "password" }
Returns: { "access_token": "...", "user": {...} }
```

#### Get Current User
```
GET /api/auth/me
Headers: Authorization: Bearer <token>
```

#### Get All Users (Admin Only)
```
GET /api/auth/users
Headers: Authorization: Bearer <token>
```

#### Update User
```
PUT /api/auth/users/<user_id>
Headers: Authorization: Bearer <token>
Body: { "name": "New Name", "email": "new@email.com" }
```

#### Delete User (Admin Only)
```
DELETE /api/auth/users/<user_id>
Headers: Authorization: Bearer <token>
```

### Analysis

#### Start Analysis
```
POST /api/analyze
Headers: Authorization: Bearer <token>
Body: { "url": "https://example.com" }
Returns: { "job_id": "...", "status": "queued" }
```

#### Check Status
```
GET /api/status/<job_id>
Headers: Authorization: Bearer <token>
Returns: { "status": "processing|completed|error", "result": {...} }
```

#### Get History
```
GET /api/history?page=1&per_page=10
Headers: Authorization: Bearer <token>
Returns: { "analyses": [...], "total": 50, "pages": 5 }
```

#### Get Specific Analysis
```
GET /api/history/<analysis_id>
Headers: Authorization: Bearer <token>
Returns: { "analysis": {...} }
```

#### Delete Analysis
```
DELETE /api/history/<analysis_id>
Headers: Authorization: Bearer <token>
```

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Analyses Table
```sql
CREATE TABLE analyses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    url VARCHAR(500) NOT NULL,
    entity VARCHAR(200),
    language VARCHAR(10),
    ai_visibility_score FLOAT,
    total_queries INTEGER,
    covered_queries INTEGER,
    result_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Admin User

**Email**: ciccioragusa@gmail.com  
**Password**: 12345Aa!  
**Role**: admin

### Change Admin Password

```bash
# Via Railway CLI
railway run python

# In Python shell
from app import app, db
from models import User

with app.app_context():
    admin = User.query.filter_by(email='ciccioragusa@gmail.com').first()
    admin.set_password('your-new-password')
    db.session.commit()
    print('Password updated!')
```

---

## Troubleshooting

### Database Connection Error
```
Error: could not connect to server
```

**Fix**: Check `DATABASE_URL` environment variable is set correctly

### Admin User Not Created
```bash
railway run python init_db.py
```

### JWT Token Errors
```
Error: Signature verification failed
```

**Fix**: Ensure `JWT_SECRET_KEY` is set and consistent

### CORS Errors
```
Access to fetch blocked by CORS policy
```

**Fix**: Check `CORS(app)` configuration in `app.py`

---

## Next Steps

1. ✅ PostgreSQL configured
2. ✅ Backend API deployed
3. ✅ Admin user created
4. ⏳ Configure frontend to use API
5. ⏳ Customize TailAdmin dashboard
6. ⏳ Add "AI Visibility" menu item
7. ⏳ Integrate charts and graphs

---

## Monitoring

### Check Logs
```bash
railway logs
```

### Check Database
```bash
railway run psql $DATABASE_URL
```

### SQL Queries
```sql
-- Count users
SELECT COUNT(*) FROM users;

-- List all users
SELECT id, email, name, role, created_at FROM users;

-- Count analyses
SELECT COUNT(*) FROM analyses;

-- Recent analyses
SELECT id, url, entity, ai_visibility_score, created_at 
FROM analyses 
ORDER BY created_at DESC 
LIMIT 10;
```

---

*Setup guide created: November 5, 2025*
