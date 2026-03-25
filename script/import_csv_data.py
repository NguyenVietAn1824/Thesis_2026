"""Import CSV data into the PostgreSQL database.

Reads CSV files from the csv/ folder and populates:
  - provinces
  - districts
  - air_component
  - distric_stats

Usage:
    python script/import_csv_data.py
"""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime

import psycopg2

# --- config from env or defaults ---
DB_HOST = os.getenv("POSTGRES__HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES__PORT", "15432"))
DB_NAME = os.getenv("POSTGRES__DB", "hanoiair_db")
DB_USER = os.getenv("POSTGRES__USERNAME", "hanoiair_user")
DB_PASS = os.getenv("POSTGRES__PASSWORD", "hanoiair_pass")

CSV_DIR = os.path.join(os.path.dirname(__file__), "..", "csv")

NOW = datetime.utcnow()


def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS,
    )


def import_provinces(cur):
    """Insert province 12 = Hà Nội (the only province in the dataset)."""
    cur.execute(
        "INSERT INTO provinces (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
        ("12", "Hà Nội"),
    )
    print("  ✓ provinces: inserted Hà Nội (id=12)")


def import_districts(cur):
    """Import districts from districts.csv + admin IDs from districts_full.csv."""
    admin_ids: dict[str, str] = {}
    full_path = os.path.join(CSV_DIR, "districts_full.csv")
    with open(full_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            aid = (row.get("administrative_id") or "").strip()
            if aid:
                admin_ids[row["internal_id"]] = aid

    path = os.path.join(CSV_DIR, "districts.csv")
    count = 0
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            district_id = row["id"]
            cur.execute(
                """
                INSERT INTO districts (id, province_id, name, normalized_name, administrative_id, create_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    district_id,
                    row["province_id"],
                    row["name"],
                    row.get("normalized_name"),
                    admin_ids.get(district_id),
                    NOW,
                ),
            )
            count += 1
    print(f"  ✓ districts: {count} rows")


def import_air_components(cur):
    """Insert standard air quality components."""
    components = [
        ("aqi", "Air Quality Index - Overall air quality indicator"),
        ("PM2.5", "Fine particulate matter smaller than 2.5 micrometers"),
        ("PM10", "Particulate matter smaller than 10 micrometers"),
        ("NO2", "Nitrogen Dioxide"),
        ("SO2", "Sulfur Dioxide"),
        ("CO", "Carbon Monoxide"),
        ("O3", "Ozone"),
    ]
    for name, desc in components:
        cur.execute(
            """
            INSERT INTO air_component (name, description, create_at)
            SELECT %s, %s, %s
            WHERE NOT EXISTS (SELECT 1 FROM air_component WHERE name = %s)
            """,
            (name, desc, NOW, name),
        )
    print(f"  ✓ air_component: {len(components)} components")


def import_distric_stats(cur):
    """Import distric_stats from distric_stats.csv."""
    path = os.path.join(CSV_DIR, "distric_stats.csv")
    count = 0
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            aqi_val = row.get("aqi_value", "").strip()
            pm25_val = row.get("pm25_value", "").strip()
            cur.execute(
                """
                INSERT INTO distric_stats (district_id, date, hour, component_id, aqi_value, pm25_value, create_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    row["district_id"],
                    row["date"],
                    int(row["hour"]) if row.get("hour", "").strip() else None,
                    row["component_id"],
                    int(float(aqi_val)) if aqi_val else None,
                    int(float(pm25_val)) if pm25_val else None,
                    NOW,
                ),
            )
            count += 1
    print(f"  ✓ distric_stats (from distric_stats.csv): {count} rows")


def import_current_aqi(cur):
    """Import current AQI data from current_aqi.csv as distric_stats rows."""
    path = os.path.join(CSV_DIR, "current_aqi.csv")
    count = 0
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            aqi_val = row.get("aqi_value", "").strip()
            component = row.get("component", "aqi").strip()
            cur.execute(
                """
                INSERT INTO distric_stats (district_id, date, hour, component_id, aqi_value, pm25_value, create_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    row["district_id"],
                    row["date"],
                    None,
                    component,
                    int(float(aqi_val)) if aqi_val else None,
                    None,
                    NOW,
                ),
            )
            count += 1
    print(f"  ✓ distric_stats (from current_aqi.csv): {count} rows")


def import_forecast(cur):
    """Import forecast data from forecast.csv as distric_stats rows with a 'forecast' component."""
    path = os.path.join(CSV_DIR, "forecast.csv")
    count = 0
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pm25_val = row.get("pm25_value", "").strip()
            aqi_val = row.get("aqi_value", "").strip()
            component = row.get("component", "").strip() or "PM2.5"
            cur.execute(
                """
                INSERT INTO distric_stats (district_id, date, hour, component_id, aqi_value, pm25_value, create_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    row["district_id"],
                    row["date"],
                    None,
                    component,
                    int(float(aqi_val)) if aqi_val else None,
                    int(float(pm25_val)) if pm25_val else None,
                    NOW,
                ),
            )
            count += 1
    print(f"  ✓ distric_stats (from forecast.csv): {count} rows")


def import_hanoiair_data(cur):
    """Import hanoiair_data.csv — combined data rows."""
    path = os.path.join(CSV_DIR, "hanoiair_data.csv")
    count = 0
    skipped = 0
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data_type = row.get("data_type", "").strip()
            district_id = row.get("district_id", "").strip()
            date_str = row.get("date", "").strip()
            if not district_id or not date_str:
                skipped += 1
                continue

            aqi_val = row.get("aqi_avg", "").strip() or row.get("aqi_value", "").strip() or row.get("forecast_aqi", "").strip()
            if data_type == "forecast" and row.get("forecast_date", "").strip():
                date_str = row["forecast_date"].strip()
                aqi_val = row.get("forecast_aqi", "").strip() or aqi_val

            component = "aqi"
            cur.execute(
                """
                INSERT INTO distric_stats (district_id, date, hour, component_id, aqi_value, pm25_value, create_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    district_id,
                    date_str,
                    None,
                    component,
                    int(float(aqi_val)) if aqi_val else None,
                    None,
                    NOW,
                ),
            )
            count += 1
    print(f"  ✓ distric_stats (from hanoiair_data.csv): {count} rows, {skipped} skipped")


def main():
    print(f"Connecting to {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME} ...")
    conn = get_conn()
    cur = conn.cursor()
    try:
        print("Importing data from csv/ ...")
        import_provinces(cur)
        import_districts(cur)
        import_air_components(cur)
        import_distric_stats(cur)
        import_current_aqi(cur)
        import_forecast(cur)
        import_hanoiair_data(cur)
        conn.commit()
        print("\n✅ All data imported successfully!")

        cur.execute("SELECT COUNT(*) FROM provinces")
        print(f"   provinces:     {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM districts")
        print(f"   districts:     {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM air_component")
        print(f"   air_component: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM distric_stats")
        print(f"   distric_stats: {cur.fetchone()[0]}")
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
