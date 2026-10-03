from flask import Flask, render_template
import requests

app = Flask(__name__)

import time
exoplanet_cache = {
    "data": [],
    "last_updated": 0
}

CACHE_DURATION = 3600

def get_exoplanets():
    current_time = time.time()

    cache_age = (
        current_time
        - exoplanet_cache["last_updated"]
    )

    if (
        exoplanet_cache["data"]
        and cache_age < CACHE_DURATION
    ):
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


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/explore")
def explore():
    exoplanets = get_exoplanets()

    return render_template(
        "explore.html",
        exoplanets=exoplanets
    )


if __name__ == "__main__":
    app.run(debug=True)