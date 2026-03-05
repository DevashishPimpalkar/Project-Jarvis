"""
handlers/weather_handler.py — Weather information via OpenWeatherMap
=====================================================================
Demonstrates how to add an external API integration.  Requires a free
OpenWeatherMap API key (set WEATHER_API_KEY in .env).

Supported intents:
    get_weather → Report current conditions for a given city

Adding more weather intents (forecast, humidity, etc.) is trivial:
    1. Add entries to supported_intents()
    2. Add a new elif branch in handle()
    3. Implement the method
"""

from __future__ import annotations

from handlers.base_handler import BaseHandler
from core.parser import Intent
from config import settings


class WeatherHandler(BaseHandler):
    """Fetches and announces current weather conditions."""

    WEATHER_API_BASE = "https://api.openweathermap.org/data/2.5/weather"

    def supported_intents(self) -> list[tuple[str, str]]:
        return [
            ("get_weather", "weather"),
        ]

    def is_available(self) -> bool:
        if not settings.WEATHER_API_KEY:
            self.logger.warning("WEATHER_API_KEY not set. WeatherHandler disabled.")
            return False

        try:
            import requests  # type: ignore  # noqa: F401
            return True
        except ImportError:
            self.logger.warning("requests not installed. Run: pip install requests")
            return False

    def handle(self, intent: Intent) -> None:
        if intent.action == "get_weather":
            self._get_weather(intent)
        else:
            self.speak(f"Unknown weather action: {intent.action}")

    # ------------------------------------------------------------------ #
    #  Action implementations                                             #
    # ------------------------------------------------------------------ #

    def _get_weather(self, intent: Intent):
        """Fetch and report current weather for the specified city."""
        city = self.get_param(intent, "city") or settings.DEFAULT_CITY

        self.logger.info(f"Fetching weather for: {city}")

        try:
            data = self._fetch_weather(city)
        except Exception as exc:  # noqa: BLE001
            self.logger.error(f"Weather API error: {exc}")
            self.speak(f"I couldn't retrieve the weather for {city}. Please try again.")
            return

        if data.get("cod") != 200:
            msg = data.get("message", "unknown error")
            self.speak(f"I couldn't find weather for {city}: {msg}.")
            return

        description = data["weather"][0]["description"]
        temp_k      = data["main"]["temp"]
        temp_c      = round(temp_k - 273.15)
        temp_f      = round((temp_k - 273.15) * 9 / 5 + 32)
        humidity    = data["main"]["humidity"]
        feels_like_k = data["main"]["feels_like"]
        feels_like_c = round(feels_like_k - 273.15)
        feels_like_f = round((feels_like_k - 273.15) * 9 / 5 + 32)

        response = (
            f"Currently in {city}: {description}. "
            f"Temperature is {temp_c}°C ({temp_f}°F), "
            f"feels like {feels_like_c}°C. "
            f"Humidity is {humidity}%."
        )
        self.speak(response)

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _fetch_weather(self, city: str) -> dict:
        """Make the HTTP request to OpenWeatherMap."""
        import requests  # type: ignore

        response = requests.get(
            self.WEATHER_API_BASE,
            params={
                "q":     city,
                "appid": settings.WEATHER_API_KEY,
            },
            timeout=8,
        )
        response.raise_for_status()
        return response.json()
