# main.py
"""
X404 Weather Skill — Webhook Server
=====================================
Handles weather requests from Jarvis.
Deploy to Vercel or Railway.

Actions:
  get_current  → current weather for a location
  get_forecast → 5-day forecast
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import re

app = FastAPI(title="X404 Weather Skill", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"


def extract_location_from_message(message: str) -> str:
    """Extract location from natural language — called when webhook receives full message."""
    patterns = [
        r'\bin\s+([A-Za-z\s]+?)(?:\?|$|,|\.|today|tomorrow|now|please)',
        r'\bfor\s+([A-Za-z\s]+?)(?:\?|$|,|\.|today|tomorrow|now|please)',
        r'\bweather\s+([A-Za-z\s]+?)(?:\?|$|,|\.|today|tomorrow|now|please)',
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            if location and len(location) > 1:
                return location
    return ""


# ── Request Model ────────────────────────────────────────────────

class WebhookRequest(BaseModel):
    action: str
    params: dict = {}
    user_id: str = ""
    auth_tokens: dict = {}


# ── Main Webhook Endpoint ────────────────────────────────────────

@app.post("/execute")
async def execute(request: WebhookRequest):
    """Main entry point — Jarvis calls this for all weather actions."""

    # Get API key from user's stored tokens
    api_key = request.auth_tokens.get("api_key")

    # Fallback to server env var (for testing)
    if not api_key:
        api_key = os.getenv("OPENWEATHER_API_KEY")

    if not api_key:
        raise HTTPException(status_code=401, detail="No OpenWeatherMap API key provided")

    action   = request.action
    params   = request.params

    # Extract location from params or from the full message
    location = params.get("location") or params.get("city", "")
    if not location and params.get("message"):
        location = extract_location_from_message(params["message"])

    if not location:
        return {
            "success": False,
            "message": "Please provide a location. For example: 'weather in London'"
        }

    if action == "get_current":
        return await get_current_weather(location, api_key)

    elif action == "get_forecast":
        return await get_forecast(location, api_key)

    else:
        return await get_current_weather(location, api_key)


# ── Get Current Weather ──────────────────────────────────────────

async def get_current_weather(location: str, api_key: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(
                f"{OPENWEATHER_BASE}/weather",
                params={
                    "q": location,
                    "appid": api_key,
                    "units": "metric",
                }
            )

            if res.status_code == 401:
                return {"success": False, "message": "Invalid OpenWeatherMap API key"}
            if res.status_code == 404:
                return {"success": False, "message": f"Location '{location}' not found"}

            res.raise_for_status()
            data = res.json()

            temp_c    = round(data["main"]["temp"])
            temp_f    = round(temp_c * 9/5 + 32)
            feels_c   = round(data["main"]["feels_like"])
            feels_f   = round(feels_c * 9/5 + 32)
            humidity  = data["main"]["humidity"]
            condition = data["weather"][0]["description"].capitalize()
            city      = data["name"]
            country   = data["sys"]["country"]
            wind_ms   = data["wind"]["speed"]
            wind_kmh  = round(wind_ms * 3.6)

            # Build a natural language response for Jarvis
            message = (
                f"Currently in {city}, {country}: {condition}. "
                f"Temperature is {temp_c}°C ({temp_f}°F), "
                f"feels like {feels_c}°C ({feels_f}°F). "
                f"Humidity {humidity}%, wind {wind_kmh} km/h."
            )

            return {
                "success": True,
                "message": message,
                "data": {
                    "city":        city,
                    "country":     country,
                    "temp_c":      temp_c,
                    "temp_f":      temp_f,
                    "feels_c":     feels_c,
                    "feels_f":     feels_f,
                    "humidity":    humidity,
                    "condition":   condition,
                    "wind_kmh":    wind_kmh,
                    "icon":        data["weather"][0]["icon"],
                }
            }

        except httpx.TimeoutException:
            return {"success": False, "message": "Weather service timed out"}
        except Exception as e:
            return {"success": False, "message": f"Weather fetch failed: {str(e)}"}


# ── Get 5-Day Forecast ───────────────────────────────────────────

async def get_forecast(location: str, api_key: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(
                f"{OPENWEATHER_BASE}/forecast",
                params={
                    "q": location,
                    "appid": api_key,
                    "units": "metric",
                    "cnt": 5,  # 5 entries (each 3hrs apart)
                }
            )

            if res.status_code == 401:
                return {"success": False, "message": "Invalid API key"}
            if res.status_code == 404:
                return {"success": False, "message": f"Location '{location}' not found"}

            res.raise_for_status()
            data = res.json()

            city = data["city"]["name"]
            country = data["city"]["country"]

            forecasts = []
            for item in data["list"]:
                forecasts.append({
                    "time":      item["dt_txt"],
                    "temp_c":    round(item["main"]["temp"]),
                    "temp_f":    round(item["main"]["temp"] * 9/5 + 32),
                    "condition": item["weather"][0]["description"].capitalize(),
                    "humidity":  item["main"]["humidity"],
                })

            message = f"Forecast for {city}, {country}: "
            for f in forecasts[:3]:
                message += f"{f['time']}: {f['condition']}, {f['temp_c']}°C. "

            return {
                "success":   True,
                "message":   message,
                "data": {
                    "city":      city,
                    "country":   country,
                    "forecasts": forecasts,
                }
            }

        except Exception as e:
            return {"success": False, "message": f"Forecast fetch failed: {str(e)}"}


# ── Health Check ─────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "skill": "jarvis_weather"}


@app.get("/")
async def root():
    return {"skill": "X404 Weather", "version": "1.0.0"}
