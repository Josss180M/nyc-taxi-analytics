import os
import glob
import gc
import warnings
import pickle
import time

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

warnings.filterwarnings("ignore")

BASE_DIR = "."
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MODELS_DIR = os.path.join(BASE_DIR, "models")
FIGURES_DIR = os.path.join(BASE_DIR, "figures")
ZONE_LOOKUP = os.path.join(BASE_DIR, "data", "taxi_zone_lookup.csv")
YEARS = ["2022", "2023", "2024"]
EDA_SAMPLE_FRAC = 0.25   # 25% para EDA/limpieza (~30M filas, seguro con 10GB RAM)
ML_SAMPLE_FRAC  = 0.10   # 10% adicional para ML (el modelo no mejora mucho con más)

COLS = [
    "VendorID",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "RatecodeID",
    "store_and_fwd_flag",
    "PULocationID",
    "DOLocationID",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
]

FEATURES = [
    "hour",
    "dayofweek",
    "PULocationID",
    "DOLocationID",
    "trip_distance",
    "passenger_count",
    "fare_amount",
    "RatecodeID",
    "duration_min",
]

for d in [PROCESSED_DIR, MODELS_DIR, FIGURES_DIR]:
    os.makedirs(d, exist_ok=True)

sns.set_theme(style="darkgrid", palette="viridis")
plt.rcParams.update(
    {
        "figure.dpi": 120,
        "figure.facecolor": "#0f0f0f",
        "axes.facecolor": "#1a1a2e",
        "axes.labelcolor": "white",
        "xtick.color": "white",
        "ytick.color": "white",
        "text.color": "white",
        "axes.titlecolor": "white",
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "grid.color": "#333355",
    }
)


# ── 1. CARGA ─────────────────────────────────────────────────────────────────

frames = []
for year in YEARS:
    for fp in sorted(glob.glob(os.path.join(RAW_DIR, year, "*.parquet"))):
        df_tmp = pd.read_parquet(fp, engine="pyarrow", columns=COLS)
        if EDA_SAMPLE_FRAC < 1.0:
            df_tmp = df_tmp.sample(frac=EDA_SAMPLE_FRAC, random_state=42)
        df_tmp["source_year"] = int(year)
        frames.append(df_tmp)

if not frames:
    raise FileNotFoundError(f"No se encontraron Parquet en {RAW_DIR}")

df_raw = pd.concat(frames, ignore_index=True)
print(f"Raw: {len(df_raw):,} filas | {df_raw.memory_usage(deep=True).sum()/1e6:.0f} MB")

df_raw["pickup_dt"] = pd.to_datetime(df_raw["tpep_pickup_datetime"], errors="coerce")
df_raw["dropoff_dt"] = pd.to_datetime(df_raw["tpep_dropoff_datetime"], errors="coerce")
df_raw["hour"] = df_raw["pickup_dt"].dt.hour
df_raw["dayofweek"] = df_raw["pickup_dt"].dt.dayofweek
df_raw["month_year"] = df_raw["pickup_dt"].dt.to_period("M")


# ── 2. EDA ────────────────────────────────────────────────────────────────────


def savefig(name):
    path = os.path.join(FIGURES_DIR, name)
    plt.savefig(path, bbox_inches="tight", facecolor="#0f0f0f")
    plt.close()
    print(f"  fig -> {path}")


# Distribuciones
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle("Distribución de Variables Clave", fontsize=14, color="white")
for ax, col, color, xlim in zip(
    axes,
    ["fare_amount", "tip_amount", "trip_distance"],
    ["#00d4ff", "#ff6b9d", "#a8ff78"],
    [(-50, 200), (-5, 50), (-5, 100)],
):
    ax.hist(
        df_raw[col].dropna().clip(*xlim),
        bins=80,
        color=color,
        alpha=0.8,
        edgecolor="none",
    )
    ax.set_title(col)
    ax.axvline(
        df_raw[col].median(),
        color="yellow",
        linestyle="--",
        linewidth=1.5,
        label=f"Mediana: ${df_raw[col].median():.2f}",
    )
    ax.legend(fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f}K"))
plt.tight_layout()
savefig("01_distribuciones.png")

# Heatmap viajes por hora y día
heatmap_data = (
    df_raw.groupby(["dayofweek", "hour"])
    .size()
    .reset_index(name="trips")
    .pivot(index="dayofweek", columns="hour", values="trips")
)
fig, ax = plt.subplots(figsize=(16, 5))
sns.heatmap(
    heatmap_data,
    ax=ax,
    cmap="YlOrRd",
    fmt=".0f",
    linewidths=0.3,
    cbar_kws={"label": "N° viajes"},
    yticklabels=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
)
ax.set_title("Heatmap Viajes por Hora y Día de Semana")
ax.set_xlabel("Hora")
ax.set_ylabel("Día")
plt.tight_layout()
savefig("02_heatmap_hora_dia.png")

# Tendencia mensual de revenue
mask_valid = df_raw["pickup_dt"].dt.year.between(2022, 2024) & df_raw[
    "fare_amount"
].between(0, 500)
monthly = (
    df_raw.loc[mask_valid]
    .groupby("month_year")["fare_amount"]
    .sum()
    .reset_index()
    .sort_values("month_year")
)
monthly["month_str"] = monthly["month_year"].astype(str)
monthly["fare_M"] = monthly["fare_amount"] / 1e6

fig, ax = plt.subplots(figsize=(16, 5))
colors_year = {"2022": "#00d4ff", "2023": "#a8ff78", "2024": "#ff6b9d"}
for year, grp in monthly.groupby(monthly["month_str"].str[:4]):
    c = colors_year.get(year, "white")
    ax.plot(
        grp["month_str"], grp["fare_M"], marker="o", lw=2.2, color=c, label=year, ms=5
    )
    ax.fill_between(grp["month_str"], grp["fare_M"], alpha=0.12, color=c)
ax.set_title("Tendencia Mensual de Revenue 2022-2024")
ax.set_xlabel("Mes")
ax.set_ylabel("Revenue (M USD)")
ax.tick_params(axis="x", rotation=45)
ax.legend()
plt.tight_layout()
savefig("03_tendencia_mensual_revenue.png")

# Top zonas por revenue
if os.path.exists(ZONE_LOOKUP):
    zones = pd.read_csv(ZONE_LOOKUP).rename(columns={"LocationID": "PULocationID"})
    zone_rev = (
        df_raw.loc[df_raw["fare_amount"].between(0, 500)]
        .groupby("PULocationID")["fare_amount"]
        .sum()
        .reset_index()
        .merge(zones[["PULocationID", "Zone"]], on="PULocationID", how="left")
        .dropna(subset=["Zone"])
        .sort_values("fare_amount", ascending=False)
        .head(20)
    )
    fig, ax = plt.subplots(figsize=(14, 7))
    palette = sns.color_palette("viridis", len(zone_rev))
    ax.barh(zone_rev["Zone"][::-1], zone_rev["fare_amount"][::-1] / 1e6, color=palette)
    ax.set_title("Top 20 Zonas por Revenue (Pickup)")
    ax.set_xlabel("Revenue (M USD)")
    plt.tight_layout()
    savefig("04_top_zonas_revenue.png")

# Correlación
num_cols = [
    "fare_amount",
    "tip_amount",
    "trip_distance",
    "passenger_count",
    "extra",
    "mta_tax",
    "tolls_amount",
    "total_amount",
    "congestion_surcharge",
]
sample = df_raw[num_cols].dropna().sample(min(200_000, len(df_raw)), random_state=42)
fig, ax = plt.subplots(figsize=(11, 9))
mask = np.triu(np.ones_like(sample.corr(), dtype=bool))
sns.heatmap(
    sample.corr(),
    ax=ax,
    mask=mask,
    annot=True,
    fmt=".2f",
    cmap="coolwarm",
    vmin=-1,
    vmax=1,
    linewidths=0.5,
    annot_kws={"size": 8},
)
ax.set_title("Matriz de Correlación")
plt.tight_layout()
savefig("05_correlacion.png")


# ── 3. LIMPIEZA ───────────────────────────────────────────────────────────────

n0 = len(df_raw)

# Calcular duration_min en df_raw directamente (sin copy)
df_raw["duration_min"] = (df_raw["dropoff_dt"] - df_raw["pickup_dt"]).dt.total_seconds() / 60

# Máscara única — evita df.copy() de 4.5 GB
mask_clean = (
    df_raw["fare_amount"].between(0, 500)
    & df_raw["passenger_count"].notna()
    & (df_raw["passenger_count"] > 0)
    & df_raw["trip_distance"].between(1e-3, 200)
    & df_raw["duration_min"].between(1, 300)
    & df_raw["pickup_dt"].dt.year.between(2022, 2024)
    & df_raw["fare_amount"].notna()
    & df_raw["tip_amount"].notna()
    & df_raw["trip_distance"].notna()
    & df_raw["PULocationID"].notna()
    & df_raw["DOLocationID"].notna()
    & df_raw["payment_type"].notna()
    & df_raw["RatecodeID"].notna()
)

df = df_raw[mask_clean].reset_index(drop=True)
del df_raw, mask_clean
gc.collect()

df["hour"] = df["pickup_dt"].dt.hour
df["dayofweek"] = df["pickup_dt"].dt.dayofweek
df["day_name"] = df["pickup_dt"].dt.day_name()
df["month"] = df["pickup_dt"].dt.month
df["year"] = df["pickup_dt"].dt.year
df["month_year"] = df["pickup_dt"].dt.to_period("M").astype(str)
df["tip_pct"] = np.where(
    df["fare_amount"] > 0, df["tip_amount"] / df["fare_amount"] * 100, 0
).round(2)
df["price_per_mile"] = np.where(
    df["trip_distance"] > 0, df["fare_amount"] / df["trip_distance"], 0
).round(4)

print(f"Limpieza: {n0:,} -> {len(df):,} filas ({len(df)/n0*100:.1f}% retenido)")

df.to_csv(os.path.join(PROCESSED_DIR, "fact_trips.csv"), index=False)
print(f"Exportado: fact_trips.csv ({len(df):,} filas)")

# ── 4. MODELO ML ──────────────────────────────────────────────────────────────

mask_ml = (df["payment_type"] == 1) & df["tip_amount"].between(0, 50)
df_ml = df[mask_ml].dropna(subset=FEATURES + ["tip_amount"])
if ML_SAMPLE_FRAC < 1.0:
    df_ml = df_ml.sample(frac=ML_SAMPLE_FRAC, random_state=42)
print(f"ML sample: {len(df_ml):,} filas")

for col in [
    "PULocationID",
    "DOLocationID",
    "RatecodeID",
    "passenger_count",
    "hour",
    "dayofweek",
]:
    df_ml[col] = df_ml[col].astype(int)

X = df_ml[FEATURES]
y = df_ml["tip_amount"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = RandomForestRegressor(
    n_estimators=150, max_depth=15, min_samples_leaf=10, n_jobs=-1, random_state=42
)
t0 = time.time()
model.fit(X_train, y_train)
print(f"Entrenamiento: {time.time()-t0:.1f}s")

y_pred = model.predict(X_test)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)
print(f"RMSE: {rmse:.4f} | R²: {r2:.4f}")

# Feature importance
feat_imp = pd.Series(model.feature_importances_, index=FEATURES).sort_values(
    ascending=True
)
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(
    feat_imp.index, feat_imp.values, color=sns.color_palette("viridis", len(feat_imp))
)
ax.set_title("Feature Importance — RandomForest (tip_amount)")
for bar in ax.patches:
    ax.text(
        bar.get_width() + 0.003,
        bar.get_y() + bar.get_height() / 2,
        f"{bar.get_width():.3f}",
        va="center",
        fontsize=9,
    )
plt.tight_layout()
savefig("06_feature_importance.png")

# Predicciones vs real
idx = np.random.choice(len(y_test), min(5000, len(y_test)), replace=False)
fig, ax = plt.subplots(figsize=(8, 8))
ax.scatter(
    np.array(y_test)[idx],
    y_pred[idx],
    alpha=0.25,
    s=8,
    color="#00d4ff",
    edgecolors="none",
)
lim = max(np.array(y_test)[idx].max(), y_pred[idx].max())
ax.plot([0, lim], [0, lim], "r--", lw=1.5, label="Predicción perfecta")
ax.set_title(f"Predicciones vs Real | R²={r2:.4f} | RMSE={rmse:.4f}")
ax.set_xlabel("tip_amount real")
ax.set_ylabel("tip_amount predicho")
ax.legend()
plt.tight_layout()
savefig("07_predicciones_vs_real.png")

with open(os.path.join(MODELS_DIR, "rf_tip_predictor.pkl"), "wb") as f:
    pickle.dump(model, f)


# ── 5. EXPORTACIÓN ────────────────────────────────────────────────────────────

df_pred = df_ml.loc[
    X_test.index,
    [
        "pickup_dt",
        "dropoff_dt",
        "duration_min",
        "PULocationID",
        "DOLocationID",
        "trip_distance",
        "passenger_count",
        "fare_amount",
        "tip_amount",
        "hour",
        "dayofweek",
        "day_name",
        "month",
        "year",
        "tip_pct",
        "price_per_mile",
    ],
].copy()

df_pred["tip_amount_predicted"] = y_pred
df_pred["prediction_error"] = (
    df_pred["tip_amount_predicted"] - df_pred["tip_amount"]
).round(4)
df_pred["abs_error"] = df_pred["prediction_error"].abs()

df_pred.to_csv(os.path.join(PROCESSED_DIR, "fact_predictions.csv"), index=False)
print(f"Exportado: fact_predictions.csv ({len(df_pred):,} filas)")

pd.DataFrame(
    [
        {
            "model": "RandomForestRegressor",
            "n_estimators": 150,
            "max_depth": 15,
            "train_size": len(X_train),
            "test_size": len(X_test),
            "rmse": round(rmse, 6),
            "r2": round(r2, 6),
            "features": str(FEATURES),
        }
    ]
).to_csv(os.path.join(MODELS_DIR, "model_metadata.csv"), index=False)

print("\nEtapa 03 completada.")
