# Etapa 03 — Python EDA, Limpieza y Modelo ML

Analisis exploratorio, limpieza de datos y modelo predictivo de propinas
sobre el dataset NYC Yellow Taxi 2022-2024 (~119M registros reales).

## Descripcion

Esta etapa procesa los archivos Parquet descargados en la Etapa 01 para
generar insights visuales, un dataset limpio y un modelo de machine learning
que predice el monto de propina por viaje.

## Archivo

    03_python_eda/
    └── 02_eda_cleaning_ml.py

## Pipeline

    Parquet (raw) --> EDA / Figuras --> Limpieza --> fact_trips.csv
                                                         |
                                                    Modelo ML (RF)
                                                         |
                                               fact_predictions.csv + .pkl

## Parametros Configurables

| Variable         | Valor | Descripcion                                      |
|------------------|-------|--------------------------------------------------|
| `EDA_SAMPLE_FRAC`| 0.25  | % de filas por archivo para EDA (~30M filas)     |
| `ML_SAMPLE_FRAC` | 0.10  | % adicional para entrenamiento (~2.2M filas)     |
| `YEARS`          | lista | Anos a procesar                                  |

> Ajustar `EDA_SAMPLE_FRAC` segun RAM disponible. Con 10 GB libres, 0.25 es seguro.

## Figuras Generadas

| Figura | Descripcion |
|--------|-------------|
| `01_distribuciones.png` | Histogramas de fare, tip y distancia con mediana |
| `02_heatmap_hora_dia.png` | Volumen de viajes por hora y dia de semana |
| `03_tendencia_mensual_revenue.png` | Revenue mensual 2022-2024 por ano |
| `05_correlacion.png` | Matriz de correlacion de variables numericas |
| `06_feature_importance.png` | Importancia de variables en el modelo RF |
| `07_predicciones_vs_real.png` | Scatter predicho vs real del test set |

## Limpieza Aplicada

| Filtro | Criterio |
|--------|----------|
| Tarifa | 0 < fare_amount <= 500 |
| Pasajeros | passenger_count > 0, sin nulos |
| Distancia | 0 < trip_distance <= 200 millas |
| Duracion | 1 <= duration_min <= 300 |
| Periodo | Anos 2022-2024 |
| Nulos | dropna en columnas criticas |

**Retencion:** 90.3% de los registros tras limpieza

## Modelo ML

| Parametro | Valor |
|-----------|-------|
| Algoritmo | RandomForestRegressor |
| Target | `tip_amount` (USD) |
| n_estimators | 150 |
| max_depth | 15 |
| Train/Test split | 80/20 |
| **RMSE** | **2.12** |
| **R²** | **0.67** |

**Features:** hour, dayofweek, PULocationID, DOLocationID, trip_distance,
passenger_count, fare_amount, RatecodeID, duration_min

## Salidas

| Archivo | Descripcion | Tamano aprox |
|---------|-------------|--------------|
| `data/processed/fact_trips.csv` | Dataset limpio completo | ~5 GB |
| `data/processed/fact_predictions.csv` | Test set con predicciones | ~60 MB |
| `models/rf_tip_predictor.pkl` | Modelo serializado | ~140 MB |
| `models/model_metadata.csv` | Metricas y parametros del modelo | < 1 KB |
| `figures/*.png` | 6 visualizaciones EDA | < 1 MB c/u |

> Los archivos CSV y .pkl no se versionan en git por su tamano.
> Son regenerables ejecutando el script.

## Uso

    # Desde la raiz del proyecto
    python 03_python_eda/02_eda_cleaning_ml.py

## Dependencias

    pandas>=2.0
    pyarrow>=14.0
    scikit-learn>=1.4
    matplotlib>=3.8
    seaborn>=0.13
