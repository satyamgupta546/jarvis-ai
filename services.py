"""SAM External Services - Weather, News, Cricket, Stocks, Radio, etc.
No API keys needed — uses free public APIs and RSS feeds.
"""

import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from config import DEFAULT_CITY


def get_weather(city: str = "") -> dict:
    """Get current weather using wttr.in (free, no API key)."""
    city = city or DEFAULT_CITY
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "SAM/1.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())

        current = data["current_condition"][0]
        forecast_today = data["weather"][0]
        forecast_tomorrow = data["weather"][1] if len(data["weather"]) > 1 else None

        result = {
            "city": city,
            "temp_c": current["temp_C"],
            "feels_like_c": current["FeelsLikeC"],
            "humidity": current["humidity"],
            "description": current["weatherDesc"][0]["value"],
            "wind_kmph": current["windspeedKmph"],
            "today_max": forecast_today["maxtempC"],
            "today_min": forecast_today["mintempC"],
        }
        if forecast_tomorrow:
            result["tomorrow_max"] = forecast_tomorrow["maxtempC"]
            result["tomorrow_min"] = forecast_tomorrow["mintempC"]
            result["tomorrow_desc"] = forecast_tomorrow["hourly"][4]["weatherDesc"][0]["value"]

        return {"status": "ok", "data": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_news(topic: str = "", count: int = 5) -> dict:
    """Get latest news headlines from Google News RSS (free, no API key)."""
    try:
        if topic:
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(topic)}&hl=en-IN&gl=IN&ceid=IN:en"
        else:
            url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

        req = urllib.request.Request(url, headers={"User-Agent": "SAM/1.0"})
        data = urllib.request.urlopen(req, timeout=10).read()
        root = ET.fromstring(data)
        items = root.findall(".//item")[:count]

        headlines = []
        for item in items:
            title = item.find("title")
            headlines.append(title.text if title is not None else "")

        return {"status": "ok", "topic": topic or "top stories", "headlines": headlines}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_cricket_score() -> dict:
    """Get live cricket scores (basic - from web search suggestion)."""
    return {
        "status": "ok",
        "suggestion": "For live cricket scores, please use [WEB_SEARCH: live cricket score India]"
    }


# ── Radio Stations (free online streams) ──
RADIO_STATIONS = {
    "bollywood": {
        "name": "Bollywood Radio",
        "url": "https://www.youtube.com/results?search_query=bollywood+radio+live+24/7",
    },
    "lofi": {
        "name": "Lo-Fi Chill",
        "url": "https://www.youtube.com/results?search_query=lofi+hip+hop+radio+live",
    },
    "english": {
        "name": "English Pop",
        "url": "https://www.youtube.com/results?search_query=pop+music+radio+live+24/7",
    },
    "hindi": {
        "name": "Hindi Radio",
        "url": "https://www.youtube.com/results?search_query=hindi+songs+radio+live+24/7",
    },
    "news": {
        "name": "News Radio",
        "url": "https://www.youtube.com/results?search_query=india+news+live+hindi",
    },
    "devotional": {
        "name": "Devotional",
        "url": "https://www.youtube.com/results?search_query=bhajan+live+radio+24/7",
    },
}


def get_radio_url(genre: str) -> dict:
    """Get a radio station URL by genre."""
    genre_lower = genre.lower().strip()

    # Try exact match
    if genre_lower in RADIO_STATIONS:
        station = RADIO_STATIONS[genre_lower]
        return {"status": "ok", "name": station["name"], "url": station["url"]}

    # Try fuzzy match
    for key, station in RADIO_STATIONS.items():
        if key in genre_lower or genre_lower in key:
            return {"status": "ok", "name": station["name"], "url": station["url"]}

    # Default: search on YouTube
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(genre)}+radio+live"
    return {"status": "ok", "name": f"{genre} Radio", "url": url}
