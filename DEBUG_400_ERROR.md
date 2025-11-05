# 🐛 Debug 400 Bad Request Error

## Current Status
**Error**: POST /analyze returns 400 Bad Request  
**Response Time**: 4-144ms (very fast = validation error)  
**Date**: November 5, 2025 at 12:35 PM

---

## Changes Applied

### Added Detailed Logging
Updated `app.py` to log:
- Request method and path
- Content-Type header
- Raw request data
- JSON parsing status
- URL being analyzed

### Code Changes
```python
@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze URL for AI visibility"""
    try:
        # Log incoming request
        print(f"Received request: {request.method} {request.path}")
        print(f"Content-Type: {request.content_type}")
        print(f"Request data: {request.data}")
        
        # Get JSON data
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        url = data.get('url')
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        print(f"Analyzing URL: {url}")
        # ... rest of code
```

---

## Testing Steps

### 1. Test from Browser
1. Go to: https://mvp-ranksimulator-production.up.railway.app
2. Open Browser DevTools (F12)
3. Go to Network tab
4. Enter a URL (e.g., https://example.com)
5. Click "Analizza"
6. Check the request in Network tab:
   - Request Headers
   - Request Payload
   - Response

### 2. Check Railway Logs
```bash
railway logs
```

Look for:
- "Received request: POST /analyze"
- "Content-Type: ..."
- "Request data: ..."
- Any error messages

### 3. Test with cURL
```bash
curl -X POST https://mvp-ranksimulator-production.up.railway.app/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

Expected response:
- Success: 200 with JSON data
- Error: 400 with error message

---

## Possible Causes

### 1. Missing Content-Type Header
**Symptom**: `Content-Type must be application/json`  
**Fix**: Ensure frontend sends `Content-Type: application/json`

### 2. Empty Request Body
**Symptom**: `No JSON data provided`  
**Fix**: Ensure request body contains valid JSON

### 3. Missing URL Field
**Symptom**: `URL is required`  
**Fix**: Ensure JSON contains `{"url": "..."}`

### 4. CORS Issue
**Symptom**: Request blocked by browser  
**Fix**: Add CORS headers to Flask app

---

## Frontend Code Check

Check `templates/index.html` around line 172:

```javascript
async function analyzeURL() {
    const urlInput = document.getElementById('urlInput');
    const url = urlInput.value.trim();
    
    if (!url) {
        showError('Per favore inserisci un URL valido');
        return;
    }
    
    // Show loading
    document.getElementById('loadingSection').classList.remove('hidden');
    document.getElementById('errorSection').classList.add('hidden');
    document.getElementById('resultsSection').classList.add('hidden');
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'  // ✅ Check this
            },
            body: JSON.stringify({ url: url })  // ✅ Check this
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        displayResults(data);
        
    } catch (error) {
        console.error('Error:', error);
        showError(error.message);
    } finally {
        document.getElementById('loadingSection').classList.add('hidden');
    }
}
```

---

## Quick Fixes to Try

### Fix 1: Add CORS Support
If it's a CORS issue, add to `app.py`:

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
```

Then add to `requirements.txt`:
```
flask-cors==4.0.0
```

### Fix 2: Check Request Format
Add more detailed error messages:

```python
@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        print(f"Headers: {dict(request.headers)}")
        print(f"Form data: {request.form}")
        print(f"JSON data: {request.get_json()}")
        
        # ... rest of code
```

### Fix 3: Handle Both JSON and Form Data
```python
@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Try JSON first
        if request.is_json:
            data = request.get_json()
        # Fallback to form data
        elif request.form:
            data = {'url': request.form.get('url')}
        else:
            return jsonify({"error": "No data provided"}), 400
        
        # ... rest of code
```

---

## Expected Log Output

### Successful Request
```
Received request: POST /analyze
Content-Type: application/json
Request data: b'{"url":"https://example.com"}'
Analyzing URL: https://example.com
[... processing logs ...]
```

### Failed Request (Missing Content-Type)
```
Received request: POST /analyze
Content-Type: text/plain
Request data: b'{"url":"https://example.com"}'
Returning 400: Content-Type must be application/json
```

### Failed Request (No URL)
```
Received request: POST /analyze
Content-Type: application/json
Request data: b'{}'
Returning 400: URL is required
```

---

## Next Steps

1. ✅ Deploy with logging enabled (DONE)
2. ⏳ Test from browser and check Network tab
3. ⏳ Check Railway logs: `railway logs`
4. ⏳ Identify exact error message
5. ⏳ Apply appropriate fix
6. ⏳ Redeploy and test

---

## Commands Reference

```bash
# View logs
railway logs

# Check status
railway status

# Redeploy
railway up --detach

# Test with curl
curl -X POST https://mvp-ranksimulator-production.up.railway.app/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

---

## Contact for Debugging

Once you test the application, share:
1. Browser Network tab screenshot (Request/Response)
2. Railway logs output
3. Any error messages in browser console

This will help identify the exact issue.

---

*Logging enabled - waiting for test results*
