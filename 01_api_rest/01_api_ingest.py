"""
NYC Taxi Analytics — Stage 01: REST API Ingestion

Downloads NYC TLC yellow taxi parquet files (2022–2024), fetches a live
USD/MXN exchange rate, and produces 10k-row CSV samples with MXN columns.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm


NYC_TLC_BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"
EXCHANGE_API = "https://api.exchangerate-api.com/v4/latest/USD"

PROYECTO_RAIZ = Path(__file__).parent.parent
DATA_DIR      = PROYECTO_RAIZ / "data"
RAW_DIR       = DATA_DIR / "raw"
SAMPLES_DIR   = DATA_DIR / "samples"
METADATA_DIR  = DATA_DIR / "metadata"

YEARS       = [2022, 2023, 2024]
MONTHS      = list(range(1, 13))

SAMPLE_SIZE  = 10_000
MAX_RETRIES  = 3
RETRY_DELAY  = 5
CHUNK_SIZE   = 524_288

COLUMNAS_PRECIO = [
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
    "airport_fee",
]


def configurar_logging() -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    nombre_log = f"ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    ruta_log   = METADATA_DIR / nombre_log

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)-8s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(ruta_log, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logging.info("Log → %s", ruta_log)


def crear_carpetas() -> None:
    for year in YEARS:
        (RAW_DIR / str(year)).mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.info("Carpetas listas → %s", DATA_DIR.resolve())


def obtener_tipo_de_cambio() -> float:
    """Returns live USD/MXN rate; falls back to 17.50 if the API is unreachable."""
    logging.info("Consultando tipo de cambio USD → MXN ...")
    try:
        respuesta = requests.get(EXCHANGE_API, timeout=15)
        respuesta.raise_for_status()
        datos = respuesta.json()
        tasa  = float(datos["rates"]["MXN"])

        ruta_fx = METADATA_DIR / "exchange_rate.json"
        with open(ruta_fx, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, indent=2, ensure_ascii=False)

        logging.info(
            "1 USD = %.4f MXN  (fecha: %s)",
            tasa,
            datos.get("date", "N/A"),
        )
        return tasa

    except Exception as error:
        tasa_respaldo = 17.50
        logging.warning(
            "No se pudo obtener el tipo de cambio (%s). Usando respaldo: %.2f MXN",
            error,
            tasa_respaldo,
        )
        return tasa_respaldo


def descargar_parquet(url: str, destino: Path) -> bool:
    """Downloads a parquet file with retry logic and a progress bar."""
    for intento in range(1, MAX_RETRIES + 1):
        try:
            logging.info("Descargando (intento %d/%d): %s", intento, MAX_RETRIES, url)
            respuesta = requests.get(url, stream=True, timeout=120)

            if respuesta.status_code == 404:
                logging.warning("Archivo no disponible (404): %s", destino.name)
                return False

            respuesta.raise_for_status()
            total_bytes = int(respuesta.headers.get("Content-Length", 0))

            with open(destino, "wb") as archivo, tqdm(
                total=total_bytes,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=f"  {destino.name}",
                leave=False,
                colour="cyan",
            ) as barra:
                for pedazo in respuesta.iter_content(chunk_size=CHUNK_SIZE):
                    archivo.write(pedazo)
                    barra.update(len(pedazo))

            tamanio_mb = destino.stat().st_size / 1_000_000
            logging.info("  OK → %.1f MB  %s", tamanio_mb, destino.name)
            return True

        except requests.RequestException as error:
            logging.error("  Error en intento %d: %s", intento, error)
            if destino.exists():
                destino.unlink()
            if intento < MAX_RETRIES:
                logging.info("  Reintentando en %d s ...", RETRY_DELAY)
                time.sleep(RETRY_DELAY)

    logging.error("  FALLÓ después de %d intentos: %s", MAX_RETRIES, url)
    return False


def validar_parquet(ruta: Path) -> dict:
    """Returns basic quality metrics (row count, null percentages, descriptive stats)."""
    logging.info("  Validando: %s", ruta.name)
    df = pd.read_parquet(ruta)
    filas, columnas = df.shape

    pct_nulos = (df.isnull().sum() / filas * 100).round(2).to_dict()

    cols_presentes = [c for c in COLUMNAS_PRECIO if c in df.columns]
    estadisticas   = (
        df[cols_presentes].describe().round(4).to_dict()
        if cols_presentes else {}
    )

    logging.info(
        "  → %d filas | %d columnas | nulos total_amount: %.1f%%",
        filas,
        columnas,
        pct_nulos.get("total_amount", 0.0),
    )
    return {
        "filas":        filas,
        "columnas":     columnas,
        "pct_nulos":    pct_nulos,
        "estadisticas": estadisticas,
    }


def generar_muestra_csv(ruta: Path, year: int, month: int, tasa: float) -> dict:
    """
    Samples SAMPLE_SIZE rows from the parquet, adds MXN price columns, and
    saves a CSV with utf-8-sig encoding so Excel opens it without extra steps.
    """
    df = pd.read_parquet(ruta)
    n  = min(SAMPLE_SIZE, len(df))
    # random_state=42 keeps the sample deterministic across re-runs
    muestra = df.sample(n=n, random_state=42).copy()

    for col in COLUMNAS_PRECIO:
        if col in muestra.columns:
            muestra[f"{col}_MXN"] = (muestra[col] * tasa).round(4)

    muestra["year"]         = year
    muestra["month"]        = month
    muestra["usd_mxn_rate"] = tasa
    muestra["sampled_at"]   = datetime.now(timezone.utc).isoformat(timespec="seconds")

    nombre_csv = f"sample_yellow_{year}_{month:02d}.csv"
    ruta_csv   = SAMPLES_DIR / nombre_csv
    muestra.to_csv(ruta_csv, index=False, encoding="utf-8-sig")

    logging.info("  Muestra CSV → %s  (%d filas, tasa=%.4f)", nombre_csv, n, tasa)
    return {"archivo_muestra": nombre_csv, "filas_muestra": n, "tasa_usada": tasa}


def guardar_log_json(entradas: list, tasa: float) -> None:
    resumen = {
        "timestamp_utc":  datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tasa_usd_mxn":   tasa,
        "total_meses":    len(entradas),
        "descargados":    sum(1 for e in entradas if e["estado"] == "descargado"),
        "ya_existian":    sum(1 for e in entradas if e["estado"] == "ya_existe"),
        "no_disponibles": sum(1 for e in entradas if e["estado"] == "no_disponible"),
        "fallidos":       sum(1 for e in entradas if e["estado"] == "fallido"),
        "detalle":        entradas,
    }
    ruta_log = METADATA_DIR / "ingest_log.json"
    with open(ruta_log, "w", encoding="utf-8") as archivo:
        json.dump(resumen, archivo, indent=2, default=str, ensure_ascii=False)
    logging.info("Log JSON → %s", ruta_log)


def main() -> None:
    configurar_logging()

    logging.info("=" * 65)
    logging.info("NYC TAXI ANALYTICS — ETAPA 01: INGESTA API REST")
    logging.info("Inicio: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logging.info("=" * 65)

    crear_carpetas()
    tasa_fx = obtener_tipo_de_cambio()

    entradas    = []
    total_meses = len(YEARS) * len(MONTHS)

    with tqdm(total=total_meses, desc="Progreso total", unit="mes", colour="green") as barra_general:
        for year in YEARS:
            for month in MONTHS:
                etiqueta = f"{year}-{month:02d}"
                nombre   = f"yellow_tripdata_{year}-{month:02d}.parquet"
                destino  = RAW_DIR / str(year) / nombre
                url      = f"{NYC_TLC_BASE}/{nombre}"

                barra_general.set_description(f"[{etiqueta}]")

                entrada = {
                    "mes":        etiqueta,
                    "archivo":    nombre,
                    "url":        url,
                    "estado":     None,
                    "validacion": None,
                    "muestra":    None,
                }

                if destino.exists():
                    logging.info("[SKIP] Ya existe: %s", nombre)
                    entrada["estado"] = "ya_existe"

                    ruta_muestra = SAMPLES_DIR / f"sample_yellow_{year}_{month:02d}.csv"
                    if not ruta_muestra.exists():
                        try:
                            entrada["muestra"] = generar_muestra_csv(destino, year, month, tasa_fx)
                        except Exception as e:
                            entrada["muestra"] = {"error": str(e)}

                    barra_general.update(1)
                    entradas.append(entrada)
                    continue

                exito = descargar_parquet(url, destino)

                if not exito:
                    entrada["estado"] = "no_disponible" if not destino.exists() else "fallido"
                    barra_general.update(1)
                    entradas.append(entrada)
                    continue

                entrada["estado"] = "descargado"

                try:
                    entrada["validacion"] = validar_parquet(destino)
                except Exception as e:
                    logging.error("  Error validando %s: %s", nombre, e)
                    entrada["validacion"] = {"error": str(e)}

                try:
                    entrada["muestra"] = generar_muestra_csv(destino, year, month, tasa_fx)
                except Exception as e:
                    logging.error("  Error generando muestra de %s: %s", nombre, e)
                    entrada["muestra"] = {"error": str(e)}

                barra_general.update(1)
                entradas.append(entrada)

    guardar_log_json(entradas, tasa_fx)

    descargados    = sum(1 for e in entradas if e["estado"] == "descargado")
    ya_existian    = sum(1 for e in entradas if e["estado"] == "ya_existe")
    no_disponibles = sum(1 for e in entradas if e["estado"] == "no_disponible")
    fallidos       = sum(1 for e in entradas if e["estado"] == "fallido")

    logging.info("=" * 65)
    logging.info("RESUMEN FINAL")
    logging.info("  Descargados nuevos       : %d", descargados)
    logging.info("  Ya existían (omitidos)   : %d", ya_existian)
    logging.info("  No disponibles (404)     : %d", no_disponibles)
    logging.info("  Fallidos                 : %d", fallidos)
    logging.info("  Tipo de cambio           : 1 USD = %.4f MXN", tasa_fx)
    logging.info("  Parquets en              : %s", RAW_DIR.resolve())
    logging.info("  Muestras CSV en          : %s", SAMPLES_DIR.resolve())
    logging.info("  Metadata en              : %s", METADATA_DIR.resolve())
    logging.info("=" * 65)
    logging.info("Etapa 01 completa.")


if __name__ == "__main__":
    main()
