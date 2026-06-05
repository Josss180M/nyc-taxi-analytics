# Etapa 02 — Validacion y Analisis en Excel + Power Query

Profiling, validacion, analisis exploratorio y documentacion del dataset
NYC Yellow Taxi Trips utilizando Excel avanzado con Power Query, formulas
complejas, tablas dinamicas, visualizaciones y automatizacion con macros VBA.

## Descripcion

Esta etapa toma las muestras CSV generadas en la Etapa 01 y las procesa
en Excel para validar la calidad del dato, documentar el dataset y generar
los primeros insights de negocio antes de pasar al procesamiento en Python.

## Archivo

    02_excel_power_query/
    └── nyc_taxi_profiling.xlsm

## Estructura del Archivo Excel

| Hoja | Descripcion |
|---|---|
| Muestra | 360,000 filas combinadas de 36 archivos via Power Query |
| Estadisticas | Metricas clave del dataset con formulas avanzadas |
| Diccionario | Documentacion de las 26 columnas del dataset |
| Zonas | Catalogo oficial de 265 zonas NYC (taxi_zone_lookup.csv) |
| Analisis_Operativo | Revenue por borough, viajes por hora, rutas origen-destino |
| Dashboard | 4 KPIs y 4 graficos ejecutivos |
| Graficos | Distribucion por tipo de pago y Top 10 zonas por revenue |
| Tabla_Dinamica | Tabla dinamica interactiva con 3 segmentadores |
| Busquedas | Buscador de zonas con desplegable y filtro de fechas |

## Tecnicas y Formulas Aplicadas

### Power Query
- Combinacion de 36 archivos CSV desde carpeta en una sola tabla
- Deteccion automatica de tipos de dato
- Perfil de columnas con calidad, distribucion y estadisticas
- Analisis sobre 360,000 filas completas

### Formulas Avanzadas
| Formula | Aplicacion |
|---|---|
| BUSCARV | Cruce de LocationID con nombres de zonas NYC |
| BUSCARX | Version moderna del cruce de zonas |
| INDICE + COINCIDIR | Busqueda flexible en cualquier direccion |
| SUMAPRODUCTO | Conteo y suma con multiples condiciones simultaneas |
| SUMAR.SI | Revenue total por borough y zona |
| PROMEDIO.SI | Propina promedio por borough |
| CONTAR.SI | Total de viajes por tipo de pago y zona |
| SI anidados | Conversion de codigos numericos a descripciones |
| HORA | Extraccion de hora desde timestamps |

### Columnas Calculadas
| Columna | Formula | Descripcion |
|---|---|---|
| trip_duration_min | (dropoff - pickup) * 1440 | Duracion del viaje en minutos |
| tip_percentage | (tip / fare) * 100 | Porcentaje de propina sobre tarifa |
| price_per_mile | fare / distance | Precio por milla recorrida |
| Payment_Desc | SI anidados | Descripcion del tipo de pago |
| Pickup_Zone | BUSCARV | Nombre de zona de recogida |
| Pickup_Borough | BUSCARV | Borough de recogida |
| Dropoff_Zone | BUSCARV | Nombre de zona de destino |
| Dropoff_Borough | BUSCARV | Borough de destino |

## Hallazgos de Calidad del Dato

| Problema | Cantidad | Accion |
|---|---|---|
| Tarifas negativas (fare_amount < 0) | 4,119 | Eliminar en Etapa 03 |
| Viajes sin pasajeros (passenger_count = 0) | 5,378 | Eliminar en Etapa 03 |
| Nulos en passenger_count | 708,471 | Imputar en Etapa 03 |
| Minimo fare_amount | -667.3 | Outlier a limpiar |
| Maximo fare_amount | 768.1 | Verificar en Etapa 03 |

## Hallazgos de Negocio

- Manhattan concentra 318,748 viajes y $240,574 de revenue
- Queens tiene el precio por milla mas alto ($33.88) por los aeropuertos
- La hora pico de demanda es las 18hrs con 24,614 viajes
- La hora mas rentable por viaje es las 5am con $35 promedio
- JFK Airport genera $1,288,979 de revenue total
- El 80% de los pagos se realizan con tarjeta de credito
- La ruta Manhattan-Manhattan domina con $5.7M de revenue

## Automatizacion con Macros VBA

| Macro | Descripcion |
|---|---|
| ActualizarTodo | Refresca todas las conexiones Power Query y tablas dinamicas |
| ExportarDashboardPDF | Exporta el dashboard como PDF con fecha en el nombre |
| ExportarBuscadorPDF | Exporta el reporte de la zona seleccionada como PDF |

## Buscador de Zonas

Herramienta interactiva que permite seleccionar cualquiera de las 265 zonas
de NYC desde un desplegable y filtrar por rango de años para obtener:

- LocationID y Borough de la zona
- Revenue total del periodo seleccionado
- Total de viajes
- Propina promedio
- Duracion promedio del viaje
- Precio promedio por milla
- Porcentaje del revenue total que representa la zona

## Dependencias

- Microsoft 365 con Excel (para macros VBA y Power Query completo)