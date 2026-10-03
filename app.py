from datetime import datetime, timezone
import os
import time

import requests
from flask import Flask, render_template


app = Flask(__name__)

CACHE_DURATION = 3600

exoplanet_cache = {
    "data": [],
    "last_updated": 0
}

asteroid_cache = {
    "data": [],
    "last_updated": 0
}


def get_exoplanets():
    current_time = time.time()
    cache_age = current_time - exoplanet_cache["last_updated"]

    if exoplanet_cache["data"] and cache_age < CACHE_DURATION:
        print("Using cached exoplanet data")
        return exoplanet_cache["data"]

    api_url = (
        "https://exoplanetarchive.ipac.caltech.edu/"
        "TAP/sync"
    )

    query = """
        SELECT TOP 6
            pl_name,
            hostname,
            disc_year,
            discoverymethod,
            sy_dist,
            pl_rade
        FROM pscomppars
        WHERE sy_dist IS NOT NULL
        ORDER BY sy_dist
    """

    parameters = {
        "query": query,
        "format": "json"
    }

    try:
        response = requests.get(
            api_url,
            params=parameters,
            timeout=15
        )

        response.raise_for_status()
        new_data = response.json()

        exoplanet_cache["data"] = new_data
        exoplanet_cache["last_updated"] = current_time

        print("Downloaded new exoplanet data")

        return new_data

    except requests.RequestException as error:
        print("Exoplanet API error:", error)
        return exoplanet_cache["data"]


def get_asteroids():
    current_time = time.time()
    cache_age = current_time - asteroid_cache["last_updated"]

    if asteroid_cache["data"] and cache_age < CACHE_DURATION:
        print("Using cached asteroid data")
        return asteroid_cache["data"]

    today = datetime.now(timezone.utc).date().isoformat()

    api_url = "https://api.nasa.gov/neo/rest/v1/feed"

    parameters = {
        "start_date": today,
        "end_date": today,
        "api_key": os.getenv(
            "NASA_API_KEY",
            "DEMO_KEY"
        )
    }

    try:
        response = requests.get(
            api_url,
            params=parameters,
            timeout=15
        )

        response.raise_for_status()
        response_data = response.json()

        asteroids = response_data[
            "near_earth_objects"
        ].get(today, [])

        asteroids = [
            asteroid
            for asteroid in asteroids
            if asteroid["close_approach_data"]
        ]

        asteroids.sort(
            key=lambda asteroid: float(
                asteroid["close_approach_data"][0]
                ["miss_distance"]["kilometers"]
            )
        )

        closest_asteroids = asteroids[:6]

        asteroid_cache["data"] = closest_asteroids
        asteroid_cache["last_updated"] = current_time

        print("Downloaded new asteroid data")

        return closest_asteroids

    except (
        requests.RequestException,
        KeyError,
        IndexError,
        ValueError
    ) as error:
        print("Asteroid API error:", error)
        return asteroid_cache["data"]


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/explore")
def explore():
    exoplanets = get_exoplanets()
    asteroids = get_asteroids()

    return render_template(
        "explore.html",
        exoplanets=exoplanets,
        asteroids=asteroids
    )


if __name__ == "__main__":
    app.run(debug=True)