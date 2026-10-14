from typing import Any
from collections import Counter
from datetime import datetime, timedelta, timezone
import httpx
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Read OPENWEATHER_API_KEY / PORT from a local .env if present
load_dotenv()

# Initialize FastMCP server
port = int(os.getenv("PORT", 8085))
mcp = FastMCP("weather", host="0.0.0.0", port=port)

# Constants
OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"
USER_AGENT = "weather-app/1.0"

# Get API key from environment variable
API_KEY = os.getenv("OPENWEATHER_API_KEY")

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def c_to_f(celsius: float) -> float:
    return round(celsius * 9 / 5 + 32, 1)


def wind_kph(meters_per_second: float) -> float:
    return round(meters_per_second * 3.6, 1)


def wind_mph(meters_per_second: float) -> float:
    return round(meters_per_second * 2.23694, 1)


def wind_direction(degrees: float) -> str:
    return COMPASS[round(degrees / 22.5) % 16]


def local_time(unix_ts: int, tz_offset_seconds: int) -> datetime:
    """Convert an OpenWeather UTC timestamp to the city's local time."""
    return datetime.fromtimestamp(unix_ts, tz=timezone(timedelta(seconds=tz_offset_seconds)))


async def make_weather_request(endpoint: str, params: dict[str, str]) -> dict[str, Any] | None:
    """Make a request to the OpenWeatherMap API with proper error handling."""
    # Check if API key is set
    if not API_KEY:
        print("ERROR: OpenWeather API key not set. Please set OPENWEATHER_API_KEY environment variable.")
        return None

    headers = {
        "User-Agent": USER_AGENT,
    }
    # Add API key and metric units to parameters
    params["appid"] = API_KEY
    params["units"] = "metric"

    url = f"{OPENWEATHER_BASE}/{endpoint}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP Error {e.response.status_code}: {e.response.text}")
            return None
        except httpx.RequestError as e:
            print(f"Request Error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

@mcp.tool()
async def get_current_weather(city: str) -> str:
    """Get current weather conditions for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney")
    """
    params = {
        "q": city,
    }

    data = await make_weather_request("weather", params)

    if not data:
        if not API_KEY:
            return f"❌ OpenWeather API key not configured. Please set OPENWEATHER_API_KEY environment variable with your API key from openweathermap.org"
        return f"Unable to fetch current weather data for {city}. Please check the city name and API key configuration."

    main = data["main"]
    wind = data["wind"]
    condition = data["weather"][0]["description"].capitalize()
    updated = local_time(data["dt"], data["timezone"]).strftime("%Y-%m-%d %H:%M")

    return f"""
Current Weather for {data['name']}, {data['sys'].get('country', '')}:

Temperature: {main['temp']}°C ({c_to_f(main['temp'])}°F)
Feels like: {main['feels_like']}°C ({c_to_f(main['feels_like'])}°F)
Condition: {condition}
Humidity: {main['humidity']}%
Wind: {wind_kph(wind['speed'])} km/h ({wind_mph(wind['speed'])} mph) {wind_direction(wind.get('deg', 0))}
Pressure: {main['pressure']} mb
Cloudiness: {data.get('clouds', {}).get('all', 0)}%
Visibility: {data.get('visibility', 0) / 1000} km

Last updated: {updated} (local time)
"""

@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney", "Melbourne")
        days: Number of days to forecast (1-5, OpenWeather free tier gives 5 days of 3-hour steps)
    """
    # Free tier forecast covers 5 days
    days = max(1, min(days, 5))

    params = {
        "q": city,
    }

    data = await make_weather_request("forecast", params)

    if not data:
        if not API_KEY:
            return f"❌ OpenWeather API key not configured. Please set OPENWEATHER_API_KEY environment variable with your API key from openweathermap.org"
        return f"Unable to fetch forecast data for {city}. Please check the city name and API key configuration."

    location = data["city"]

    # Group the 3-hour steps by the city's local date
    by_date: dict[str, list[dict[str, Any]]] = {}
    for step in data["list"]:
        date = local_time(step["dt"], location["timezone"]).strftime("%Y-%m-%d")
        by_date.setdefault(date, []).append(step)

    forecasts = []
    # OpenWeather sometimes returns a historical name (e.g. "Turan" for Danang), so keep the queried city too
    forecasts.append(f"Weather Forecast for {city} ({location['name']}, {location.get('country', '')}):")

    for date, steps in list(by_date.items())[:days]:
        high = max(s["main"]["temp_max"] for s in steps)
        low = min(s["main"]["temp_min"] for s in steps)
        condition = Counter(s["weather"][0]["description"] for s in steps).most_common(1)[0][0]
        rain_chance = round(max(s.get("pop", 0) for s in steps) * 100)
        max_wind = max(s["wind"]["speed"] for s in steps)

        forecast = f"""
{date}:
High: {high}°C ({c_to_f(high)}°F)
Low: {low}°C ({c_to_f(low)}°F)
Condition: {condition.capitalize()}
Chance of Rain: {rain_chance}%
Max Wind: {wind_kph(max_wind)} km/h
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

@mcp.tool()
async def health_check() -> str:
    """Health check endpoint for deployment verification."""
    return "✅ Weather MCP Server is running! Ready to provide weather data (OpenWeatherMap) for Vietnamese, Australian cities and worldwide."

print("✅ MCP server initialized with Streamable HTTP transport")
print("🔧 Available tools: get_current_weather, get_forecast, health_check")

if __name__ == "__main__":
    import sys

    is_cloud_run = bool(os.getenv("PORT"))
    is_standalone = len(sys.argv) == 1 and sys.stdin.isatty()

    if is_cloud_run or is_standalone:
        print(f"🚀 Starting MCP server on http://0.0.0.0:{port}/mcp")
        mcp.run(transport="streamable-http")
    else:
        print("Starting FastMCP server in stdio mode for local client", file=sys.stderr)
        mcp.run()
