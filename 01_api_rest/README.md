# Etapa 01 — Ingesta de Datos via API REST

Descarga automatizada de los archivos Parquet mensuales de NYC Yellow Taxi
desde la API pública de la NYC Taxi and Limousine Commission (TLC),
enriquecidos con tipo de cambio USD a MXN desde una segunda API REST.

## Descripcion

Esta etapa implementa la primera fase del pipeline: la extraccion de datos
desde fuentes externas via API REST. El script descarga 36 archivos Parquet
(12 meses x 3 años) y genera muestras enriquecidas listas para la siguiente
etapa de validacion en Excel.

## APIs Utilizadas

| API | Descripcion | Autenticacion |
|---|---|---|
| NYC TLC Trip Record Data | Archivos Parquet mensuales de viajes | Sin autenticacion |
| ExchangeRate API | Tipo de cambio USD a MXN en tiempo real | Sin autenticacion |

## Archivo

    01_api_rest/
    └── 01_api_ingest.py

## Funciones Principales

| Funcion | Descripcion |
|---|---|
| setup_directories() | Crea la estructura de carpetas del proyecto |
| get_exchange_rate() | Obtiene tipo de cambio USD a MXN via API |
| build_parquet_url() | Construye la URL de cada archivo mensual |
| download_parquet() | Descarga con reintentos y barra de progreso |
| validate_parquet() | Valida filas, columnas y estadisticas basicas |
| enrich_sample_with_exchange() | Genera muestra de 10,000 filas con precios en MXN |
| run_ingestion_pipeline() | Ejecuta el pipeline completo |

## Estructura de Salida

    nyc_taxi_project/
    └── data/
        ├── raw/
        │   ├── 2022/     <- 12 archivos Parquet originales
        │   ├── 2023/     <- 12 archivos Parquet originales
        │   └── 2024/     <- 12 archivos Parquet originales
        ├── samples/      <- 36 CSVs de 10,000 filas con precios en MXN
        └── metadata/
            ├── exchange_rate.json    <- tipo de cambio usado
            └── download_summary.json <- log completo de descarga

## Uso

    # Ejecutar pipeline completo
    python 01_api_rest/01_api_ingest.py

    # Ver resumen de archivos descargados
    python 01_api_rest/01_api_ingest.py --summary

## Caracteristicas Tecnicas

- Reintentos automaticos (3 intentos por archivo)
- Deteccion de archivos ya descargados para re-ejecuciones
- Barra de progreso por archivo con tqdm
- Validacion de integridad de cada Parquet descargado
- Log completo en JSON con estadisticas por mes
- Fallback de tipo de cambio si la API no esta disponible

## Resultados

- 36 archivos Parquet descargados (2022-2024)
- ~180 millones de registros totales
- 36 muestras CSV generadas para validacion en Excel
- Tipo de cambio registrado: 1 USD = 17.33 MXN (fecha de descarga)

## Dependencias

    requests
    pandas
    pyarrow
    tqdm