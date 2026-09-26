"""
One-off script used only during development in this sandbox (no outbound
network access here -- see README 'Known limitations').

It writes a *real* raw Open-Meteo-shaped snapshot for Lille, captured by
fetching https://dighim--a2c2d552746511f1915d1607ee4eb77e.web.val.run/
(a small public proxy in front of the real Open-Meteo forecast API) on
2026-09-26. These are genuine forecast values for Lille, not invented
numbers.

Two fields the proxy's page does not expose (precipitation_sum in mm, and
relative_humidity_2m_mean) are left as true `None` values rather than
fabricated -- this also gives the test suite a real, honest missing-value
case to exercise in clean.py's imputation logic.

This is NOT how the pipeline gets its data in normal operation --
pipeline/ingest.py calls the real Open-Meteo archive API directly. This
script only exists to seed one small, genuinely-sourced fixture for
offline tests in an environment with no outbound network access.
"""
import json
import os

REAL_LILLE_FORECAST_26SEP2026 = [
    ("2026-09-26", "Brouillard", 21, 15, 2, 13),
    ("2026-09-27", "Couvert", 25, 14, 12, 16),
    ("2026-09-28", "Couvert", 22, 17, 41, 15),
    ("2026-09-29", "Couvert", 28, 18, 35, 14),
    ("2026-09-30", "Bruine légère", 23, 18, 73, 17),
    ("2026-10-01", "Bruine légère", 20, 14, 57, 11),
    ("2026-10-02", "Partiellement nuageux", 20, 10, 6, 10),
    ("2026-10-03", "Plutôt dégagé", 20, 9, 12, 9),
    ("2026-10-04", "Partiellement nuageux", 21, 10, 13, 10),
    ("2026-10-05", "Couvert", 21, 11, 12, 10),
    ("2026-10-06", "Plutôt dégagé", 21, 9, 10, 6),
    ("2026-10-07", "Bruine modérée", 21, 9, 17, 20),
    ("2026-10-08", "Averses faibles", 16, 10, 20, 19),
    ("2026-10-09", "Bruine modérée", 15, 9, 16, 13),
    ("2026-10-10", "Bruine modérée", 20, 14, 22, 27),
]

DESC_TO_WMO = {
    "Brouillard": 45, "Couvert": 3, "Bruine légère": 51,
    "Partiellement nuageux": 2, "Plutôt dégagé": 1,
    "Bruine modérée": 53, "Averses faibles": 80,
}

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")


def build():
    os.makedirs(RAW_DIR, exist_ok=True)
    times, tmax, tmin, tmean, precip, wind, humidity, wcode = [], [], [], [], [], [], [], []
    for date_str, desc, hi, lo, precip_prob_pct, wind_kmh in REAL_LILLE_FORECAST_26SEP2026:
        times.append(date_str)
        tmax.append(float(hi))
        tmin.append(float(lo))
        tmean.append(round((hi + lo) / 2, 1))
        precip.append(None)
        wind.append(float(wind_kmh))
        humidity.append(None)
        wcode.append(DESC_TO_WMO[desc])

    payload = {
        "fetched_at": "2026-09-26T14:52:00+02:00",
        "location": {"city_name": "Lille", "country": "France", "latitude": 50.6292, "longitude": 3.0573},
        "source_url": "https://dighim--a2c2d552746511f1915d1607ee4eb77e.web.val.run/ (Open-Meteo-backed proxy)",
        "source_note": (
            "Captured live during development on 2026-09-26. Real Open-Meteo forecast values "
            "for Lille. precipitation_sum and relative_humidity_2m_mean are true nulls (not "
            "exposed by this source), not fabricated placeholders."
        ),
        "response": {
            "daily": {
                "time": times, "temperature_2m_max": tmax, "temperature_2m_min": tmin,
                "temperature_2m_mean": tmean, "precipitation_sum": precip,
                "wind_speed_10m_max": wind, "relative_humidity_2m_mean": humidity,
                "weather_code": wcode,
            }
        },
    }
    out_path = os.path.join(RAW_DIR, "lille_2026-09-26_2026-10-10.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    build()
