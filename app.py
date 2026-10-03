import csv
import math
import os
import time
from datetime import datetime, timezone

import requests
from flask import Flask, render_template


app = Flask(__name__)

CACHE_DURATION = 3600  # One hour

exoplanet_cache = {
    "data": [],
    "last_updated": 0
}

asteroid_cache = {
    "data": [],
    "last_updated": 0
}

position_cache = {
    "data": [],
    "last_updated": 0
}


def get_exoplanets():
    current_time = time.time()

    if (
        exoplanet_cache["data"]
        and current_time - exoplanet_cache["last_updated"] < CACHE_DURATION
    ):
        return exoplanet_cache["data"]

    url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

    query = """
        SELECT TOP 6
            pl_name,
            hostname,
            sy_dist,
            pl_rade,
            pl_eqt,
            discoverymethod
        FROM pscomppars
        WHERE sy_dist IS NOT NULL
        ORDER BY sy_dist ASC
    """

    parameters = {
        "query": query,
        "format": "json"
    }

    try:
        response = requests.get(url, params=parameters, timeout=15)
        response.raise_for_status()
        exoplanets = response.json()

        exoplanet_cache["data"] = exoplanets
        exoplanet_cache["last_updated"] = current_time

    except requests.RequestException as error:
        print(f"Exoplanet API error: {error}")

    return exoplanet_cache["data"]


def get_asteroids():
    current_time = time.time()

    if (
        asteroid_cache["data"]
        and current_time - asteroid_cache["last_updated"] < CACHE_DURATION
    ):
        return asteroid_cache["data"]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    url = "https://api.nasa.gov/neo/rest/v1/feed"

    parameters = {
        "start_date": today,
        "end_date": today,
        "api_key": os.environ.get("NASA_API_KEY", "DEMO_KEY")
    }

    try:
        response = requests.get(url, params=parameters, timeout=15)
        response.raise_for_status()

        nasa_data = response.json()
        asteroid_results = []

        for asteroid in nasa_data["near_earth_objects"].get(today, []):
            approaches = asteroid.get("close_approach_data", [])

            if not approaches:
                continue

            approach = approaches[0]
            diameter = asteroid["estimated_diameter"]["kilometers"]

            asteroid_results.append({
                "name": asteroid["name"].replace("(", "").replace(")", ""),
                "diameter": round(
                    (
                        diameter["estimated_diameter_min"]
                        + diameter["estimated_diameter_max"]
                    ) / 2,
                    3
                ),
                "distance": round(
                    float(approach["miss_distance"]["kilometers"]),
                    0
                ),
                "speed": round(
                    float(approach["relative_velocity"]["kilometers_per_hour"]),
                    0
                ),
                "hazardous": asteroid[
                    "is_potentially_hazardous_asteroid"
                ]
            })

        asteroid_results.sort(key=lambda asteroid: asteroid["distance"])

        asteroid_cache["data"] = asteroid_results[:6]
        asteroid_cache["last_updated"] = current_time

    except (requests.RequestException, KeyError, ValueError) as error:
        print(f"Asteroid API error: {error}")

    return asteroid_cache["data"]


def get_planet_positions():
    current_time = time.time()

    if (
        position_cache["data"]
        and current_time - position_cache["last_updated"] < CACHE_DURATION
    ):
        return position_cache["data"]

    planets = {
        "Mercury": "199",
        "Venus": "299",
        "Earth": "399",
        "Mars": "499",
        "Jupiter": "599",
        "Saturn": "699",
        "Uranus": "799",
        "Neptune": "899"
    }

    position_results = []

    observation_time = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d %H:%M")

    for planet_name, planet_id in planets.items():
        parameters = {
            "format": "json",
            "COMMAND": f"'{planet_id}'",
            "OBJ_DATA": "'NO'",
            "MAKE_EPHEM": "'YES'",
            "EPHEM_TYPE": "'VECTORS'",
            "CENTER": "'500@10'",
            "TLIST": f"'{observation_time}'",
            "OUT_UNITS": "'AU-D'",
            "VEC_TABLE": "'1'",
            "CSV_FORMAT": "'YES'"
        }

        try:
            response = requests.get(
                "https://ssd.jpl.nasa.gov/api/horizons.api",
                params=parameters,
                timeout=15
            )

            response.raise_for_status()
            api_data = response.json()

            if "error" in api_data:
                print(
                    f"JPL error for {planet_name}: "
                    f"{api_data['error']}"
                )
                continue

            result = api_data["result"]

            data_section = (
                result.split("$$SOE")[1]
                .split("$$EOE")[0]
            )

            first_line = data_section.strip().splitlines()[0]
            row = next(csv.reader([first_line]))

            x_position = float(row[2])
            y_position = float(row[3])
            z_position = float(row[4])

            distance_from_sun = math.sqrt(
                x_position ** 2
                + y_position ** 2
                + z_position ** 2
            )

            position_results.append({
                "name": planet_name,
                "x": round(x_position, 4),
                "y": round(y_position, 4),
                "z": round(z_position, 4),
                "distance": round(distance_from_sun, 4)
            })

        except (
            requests.RequestException,
            KeyError,
            ValueError,
            IndexError
        ) as error:
            print(
                f"Position API error for "
                f"{planet_name}: {error}"
            )

    if position_results:
        position_cache["data"] = position_results
        position_cache["last_updated"] = current_time

    return position_cache["data"]


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/explore")
def explore():
    exoplanets = get_exoplanets()
    asteroids = get_asteroids()
    planet_positions = get_planet_positions()

    return render_template(
        "explore.html",
        exoplanets=exoplanets,
        asteroids=asteroids,
        planet_positions=planet_positions
    )


if __name__ == "__main__":
    app.run(debug=True)