# NYC Taxi Analytics — Proyecto End-to-End

Proyecto de portafolio de análisis de datos utilizando el dataset
público de NYC Yellow Taxi Trips (2022–2024), implementando un
pipeline completo desde la ingesta de datos hasta la automatización.

## Objetivo

Construir un pipeline end-to-end que demuestre competencias en
recopilación, procesamiento, modelado, visualización y automatización
de datos, utilizando herramientas estándar de la industria.

## Stack Tecnológico

| Herramienta           | Aplicación                                  |
|-----------------------|---------------------------------------------|
| Python + pandas       | EDA, limpieza de datos, modelo ML           |
| scikit-learn          | Modelo predictivo de propina (RandomForest) |
| PostgreSQL            | Modelado relacional, queries avanzadas      |
| Power BI + DAX        | Dashboard ejecutivo con KPIs                |
| Excel + Power Query   | Profiling, validación y documentación       |
| Power Automate        | Automatización del pipeline mensual         |
| SharePoint            | Almacenamiento y distribución de reportes   |

## Flujo del Proyecto

    API REST → Excel → Python → PostgreSQL → Power BI → Power Automate → SharePoint

## Estructura del Proyecto

| Carpeta                | Descripción                            | Estado       |
|------------------------|----------------------------------------|--------------|
| 01_api_rest            | Ingesta desde API pública NYC TLC      | Completado   |
| 02_excel_power_query   | Profiling, validación y análisis       | Completado   |
| 03_python_eda          | EDA, limpieza y modelo ML              | Completado   |
| 04_postgresql          | Modelado estrella y queries SQL        | Pendiente    |
| 05_power_bi            | Dashboard ejecutivo                    | Pendiente    |
| 06_power_automate      | Automatización mensual                 | Pendiente    |
| 07_sharepoint          | Almacenamiento de reportes             | Pendiente    |

## Dataset

- **Fuente:** NYC Taxi and Limousine Commission (TLC)
- **Periodo:** Enero 2022 — Diciembre 2024
- **Volumen:** ~180 millones de registros reales
- **Formato:** Parquet mensual
- **API:** https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

## Hallazgos Principales

- JFK Airport genera el mayor revenue por viaje con $1.28M total
- La hora pico de demanda es las 18hrs con 24,614 viajes
- La hora mas rentable por viaje es las 5am con $35 promedio
- El 80% de los pagos se realizan con tarjeta de credito
- Manhattan concentra el 88% del volumen total de viajes
- Modelo RandomForest predice propinas con R²=0.67 y RMSE=$2.12
- `fare_amount` y `trip_distance` son los predictores mas importantes de propina

## Requisitos

    pip install -r requirements.txt

## Instalacion

    git clone git clone https://github.com/Josss180M/nyc-taxi-analytics.git
    cd nyc-taxi-analytics
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

## Uso

Ejecutar cada etapa en orden:

    # Etapa 01 - Ingesta de datos
    python 01_api_rest/01_api_ingest.py

    # Etapa 03 - EDA y modelo ML
    python 03_python_eda/02_eda_cleaning_ml.py

## Notas

- Los archivos Parquet no se incluyen en el repositorio por su
  tamaño. Ejecutar el script de ingesta para generarlos.
- El archivo Excel requiere Microsoft 365 para las macros VBA.
- Las credenciales de base de datos se configuran en un
  archivo .env (ver .env.example).

## Autor

**Joshue Moreno**
Data Analyst — Python, SQL, Power BI
joshuemoreno612@gmail.com
LinkedIn: linkedin.com/in/joshue-moreno-3279692b3  