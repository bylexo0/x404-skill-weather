# X404 Weather Skill — Webhook Server

Official weather skill for the X404 / Jarvis platform.
Powered by OpenWeatherMap API.

---

## Deploy to Vercel (Free)

### Step 1 — Push to GitHub
Create a new repo called `x404-weather-skill` and push this folder.

### Step 2 — Deploy to Vercel
1. Go to vercel.com → New Project
2. Import your GitHub repo
3. Framework: Other
4. Click Deploy

### Step 3 — Get your webhook URL
After deploy you'll get a URL like:
```
https://x404-weather-skill.vercel.app
```

Your webhook URL is:
```
https://x404-weather-skill.vercel.app/execute
```

### Step 4 — Update Supabase
Run this in Supabase SQL Editor:
```sql
UPDATE public.skills
SET webhook_url = 'https://x404-weather-skill.vercel.app/execute'
WHERE skill_key = 'jarvis_weather';
```

---

## Test Locally First

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Test with curl:
```bash
curl -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{
    "action": "get_current",
    "params": {"location": "London"},
    "auth_tokens": {"api_key": "YOUR_OPENWEATHER_KEY"}
  }'
```

---

## How It Works

```
User: "What's the weather in NYC?"
         ↓
Jarvis backend calls POST /execute
with user's stored API key
         ↓
Webhook hits OpenWeatherMap API
         ↓
Returns natural language response
         ↓
Jarvis tells the user ✅
```

---

## Actions Supported

```
get_current  → current weather
get_forecast → 5-day forecast
```

Get a free OpenWeatherMap API key at:
https://openweathermap.org/api
