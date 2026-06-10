import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "nyc_taxi")

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

PROCESSED_DIR = os.path.join("data", "processed")
ZONE_LOOKUP    = os.path.join("data", "taxi_zone_lookup.csv")


# ── 1. SCHEMA ─────────────────────────────────────────────────────────────────

DDL = """
DROP TABLE IF EXISTS fact_trips CASCADE;
DROP TABLE IF EXISTS dim_zone    CASCADE;
DROP TABLE IF EXISTS dim_payment CASCADE;
DROP TABLE IF EXISTS dim_vendor  CASCADE;
DROP TABLE IF EXISTS dim_ratecode CASCADE;

CREATE TABLE dim_vendor (
    vendor_id   SMALLINT PRIMARY KEY,
    vendor_name VARCHAR(50)
);

CREATE TABLE dim_payment (
    payment_type_id SMALLINT PRIMARY KEY,
    payment_desc    VARCHAR(30)
);

CREATE TABLE dim_ratecode (
    ratecode_id   SMALLINT PRIMARY KEY,
    ratecode_desc VARCHAR(40)
);

CREATE TABLE dim_zone (
    zone_id      SMALLINT PRIMARY KEY,
    borough      VARCHAR(30),
    zone         VARCHAR(60),
    service_zone VARCHAR(30)
);

CREATE TABLE fact_trips (
    trip_id               BIGSERIAL PRIMARY KEY,
    vendor_id             SMALLINT  REFERENCES dim_vendor(vendor_id),
    pickup_datetime       TIMESTAMP,
    dropoff_datetime      TIMESTAMP,
    duration_min          NUMERIC(8,2),
    passenger_count       SMALLINT,
    trip_distance         NUMERIC(8,2),
    pu_location_id        SMALLINT  REFERENCES dim_zone(zone_id),
    do_location_id        SMALLINT  REFERENCES dim_zone(zone_id),
    ratecode_id           SMALLINT  REFERENCES dim_ratecode(ratecode_id),
    payment_type_id       SMALLINT  REFERENCES dim_payment(payment_type_id),
    fare_amount           NUMERIC(10,2),
    extra                 NUMERIC(8,2),
    mta_tax               NUMERIC(8,2),
    tip_amount            NUMERIC(10,2),
    tip_pct               NUMERIC(8,2),
    tolls_amount          NUMERIC(10,2),
    improvement_surcharge NUMERIC(8,2),
    total_amount          NUMERIC(10,2),
    congestion_surcharge  NUMERIC(8,2),
    airport_fee           NUMERIC(8,2),
    price_per_mile        NUMERIC(10,4),
    hour                  SMALLINT,
    day_of_week           SMALLINT,
    month                 SMALLINT,
    year                  SMALLINT
);
"""

with engine.connect() as conn:
    conn.execute(text(DDL))
    conn.commit()
print("Schema creado.")


# ── 2. DIM TABLES ─────────────────────────────────────────────────────────────

vendors = pd.DataFrame([
    {"vendor_id": 1, "vendor_name": "Creative Mobile Technologies"},
    {"vendor_id": 2, "vendor_name": "VeriFone Inc."},
])

payments = pd.DataFrame([
    {"payment_type_id": 1, "payment_desc": "Credit card"},
    {"payment_type_id": 2, "payment_desc": "Cash"},
    {"payment_type_id": 3, "payment_desc": "No charge"},
    {"payment_type_id": 4, "payment_desc": "Dispute"},
    {"payment_type_id": 5, "payment_desc": "Unknown"},
    {"payment_type_id": 6, "payment_desc": "Voided trip"},
])

ratecodes = pd.DataFrame([
    {"ratecode_id": 1, "ratecode_desc": "Standard rate"},
    {"ratecode_id": 2, "ratecode_desc": "JFK"},
    {"ratecode_id": 3, "ratecode_desc": "Newark"},
    {"ratecode_id": 4, "ratecode_desc": "Nassau/Westchester"},
    {"ratecode_id": 5, "ratecode_desc": "Negotiated fare"},
    {"ratecode_id": 6, "ratecode_desc": "Group ride"},
])

vendors.to_sql("dim_vendor",   engine, if_exists="append", index=False)
payments.to_sql("dim_payment", engine, if_exists="append", index=False)
ratecodes.to_sql("dim_ratecode", engine, if_exists="append", index=False)
print("dim_vendor, dim_payment, dim_ratecode cargadas.")

if os.path.exists(ZONE_LOOKUP):
    zones = pd.read_csv(ZONE_LOOKUP)
    zones.columns = ["zone_id", "borough", "zone", "service_zone"]
    zones.to_sql("dim_zone", engine, if_exists="append", index=False)
    print(f"dim_zone cargada: {len(zones)} zonas.")
else:
    print(f"WARN: {ZONE_LOOKUP} no encontrado — dim_zone vacia.")


# ── 3. FACT TABLE ─────────────────────────────────────────────────────────────

fact_path = os.path.join(PROCESSED_DIR, "fact_trips.csv")
print(f"Cargando {fact_path}...")

col_map = {
    "VendorID":              "vendor_id",
    "pickup_dt":             "pickup_datetime",
    "dropoff_dt":            "dropoff_datetime",
    "PULocationID":          "pu_location_id",
    "DOLocationID":          "do_location_id",
    "payment_type":          "payment_type_id",
    "RatecodeID":            "ratecode_id",
    "dayofweek":             "day_of_week",
    "Airport_fee":           "airport_fee",
}

FACT_COLS = [
    "vendor_id", "pickup_datetime", "dropoff_datetime", "duration_min",
    "passenger_count", "trip_distance", "pu_location_id", "do_location_id",
    "ratecode_id", "payment_type_id", "fare_amount", "extra", "mta_tax",
    "tip_amount", "tip_pct", "tolls_amount", "improvement_surcharge",
    "total_amount", "congestion_surcharge", "airport_fee", "price_per_mile",
    "hour", "day_of_week", "month", "year",
]

CHUNKSIZE = 100_000
total = 0

for chunk in pd.read_csv(fact_path, chunksize=CHUNKSIZE, low_memory=False):
    chunk = chunk.rename(columns=col_map)
    chunk.columns = chunk.columns.str.lower()

    if "airport_fee" not in chunk.columns:
        chunk["airport_fee"] = 0.0

    for col in ["pickup_datetime", "dropoff_datetime"]:
        chunk[col] = pd.to_datetime(chunk[col], errors="coerce")

    chunk = chunk[chunk["pu_location_id"].between(1, 265)]
    chunk = chunk[chunk["do_location_id"].between(1, 265)]
    chunk = chunk[chunk["ratecode_id"].between(1, 6)]
    chunk = chunk[chunk["payment_type_id"].between(1, 6)]
    chunk = chunk[chunk["vendor_id"].isin([1, 2])]

    chunk[FACT_COLS].to_sql(
        "fact_trips", engine,
        if_exists="append", index=False,
        method="multi", chunksize=5_000,
    )
    total += len(chunk)
    print(f"  {total:,} filas insertadas...")

print(f"fact_trips cargada: {total:,} filas.")


# ── 4. INDEXES ────────────────────────────────────────────────────────────────

INDEXES = """
CREATE INDEX idx_fact_pickup     ON fact_trips(pickup_datetime);
CREATE INDEX idx_fact_pu_loc     ON fact_trips(pu_location_id);
CREATE INDEX idx_fact_do_loc     ON fact_trips(do_location_id);
CREATE INDEX idx_fact_payment    ON fact_trips(payment_type_id);
CREATE INDEX idx_fact_year_month ON fact_trips(year, month);
CREATE INDEX idx_fact_hour       ON fact_trips(hour);
"""

with engine.connect() as conn:
    conn.execute(text(INDEXES))
    conn.commit()
print("Indices creados.")
print("\nEtapa 04 completada.")
