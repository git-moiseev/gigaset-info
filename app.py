
#!/usr/bin/env python3

import logging
import os
import time
from html import escape
from threading import Lock
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from flask import Flask, Response, request
from datetime import datetime, timedelta, timezone

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

API_URL = "https://api.open-meteo.com/v1/forecast"

LAT = float(os.environ["LAT"])
LON = float(os.environ["LON"])
CACHE_TTL = int(os.getenv("CACHE_TTL", 1800))

PARAMS = {
    "latitude": LAT,
    "longitude": LON,
    "current": ",".join([
        "temperature_2m",
        "apparent_temperature",
        "relative_humidity_2m",
        "pressure_msl",
        "wind_speed_10m",
        "weather_code",
    ]),
    "wind_speed_unit": "ms",
}

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Freezing fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm, hail",
    99: "Thunderstorm, hail",
}

cache = {
    "data": None,
    "updated": 0,
}

cache_lock = Lock()


def get_weather():
    with cache_lock:
        now = time.monotonic()

        if cache["data"] is not None:
            if now - cache["updated"] < CACHE_TTL:
                return cache["data"], False

        try:
            response = requests.get(
                API_URL,
                params=PARAMS,
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()["current"]

            cache["data"] = data
            cache["updated"] = time.monotonic()

            return data, False

        except (requests.RequestException, ValueError, KeyError):
            app.logger.exception("Weather API error")
            return cache["data"], True


def fmt(value, suffix="", decimals=0):
    if value is None:
        return "--"
    return f"{value:.{decimals}f}{suffix}"


def paragraph(text, style=""):
    return f'<p style="{style}">{escape(text)}</p>'


def render_weather():
    data, stale = get_weather()

    tz_minutes = request.args.get("tz", default=0, type=int)
    tz = timezone(timedelta(minutes=tz_minutes))
    now = datetime.now(tz)
    datestr = now.strftime("%A, %d %b")

    body = []

    if data is None:
        body.append(paragraph("Weather unavailable"))
    else:
        code = data.get("weather_code", -1)
        description = WEATHER_CODES.get(code, "Unknown")

        temp = data.get("temperature_2m")

        body.append(paragraph(
            f"{temp:+.1f} C" if temp is not None else "-",
            "text-align:center;font-weight:bold",
        ))

        body.append(paragraph(
            description,
            "text-align:center",
        ))

        body.append(paragraph(
            "Feels like: " +
            fmt(data.get("apparent_temperature"), " C", 1)
        ))

        body.append(paragraph(
            "Humidity: " +
            fmt(data.get("relative_humidity_2m"), "%")
        ))

        body.append(paragraph(
            "Pressure: " +
            fmt(data.get("pressure_msl"), " hPa")
        ))

        body.append(paragraph(
            "Wind: " +
            fmt(data.get("wind_speed_10m"), " m/s", 1)
        ))

        if stale:
            body.append(paragraph(
                "STALE DATA",
                "text-align:center;font-weight:bold",
            ))

    content = "\n".join(body)

    return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//OMA//DTD XHTML Mobile 1.2//EN"
"http://www.openmobilealliance.org/tech/DTD/xhtml-mobile12.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>{datestr}</title>
<meta name="expires" content="60" />
</head>
<body>
{content}
</body>
</html>"""


@app.route("/info/request.do")
@app.route("/info/menu.jsp")
def gigaset_weather():
    return Response(
        render_weather(),
        content_type="application/xhtml+xml; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
