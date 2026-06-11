# Etapa 04 — PostgreSQL: Modelado Relacional y Analítica SQL

Carga de 26.7 millones de registros de NYC Yellow Taxi (2022-2024) en un
esquema estrella dentro de PostgreSQL, con queries avanzadas usando CTEs
y Window Functions, listo para conectarse a Power BI.

---

## Por que PostgreSQL

Despues de procesar los datos en Python (Etapa 03), necesitamos un motor
que soporte consultas relacionales complejas a escala. PostgreSQL permite:

- Hacer JOINs entre 26M filas y tablas de catalogo en milisegundos
- Definir relaciones (Foreign Keys) que garantizan integridad de datos
- Crear vistas precalculadas que Power BI consume sin escribir SQL
- Correr queries analiticas avanzadas (CTEs, Window Functions, percentiles)

---

## Modelo de Datos — Esquema Estrella

```
                    dim_vendor
                    (vendor_id PK)
                         |
   dim_ratecode ─── fact_trips ─── dim_payment
 (ratecode_id PK)  (trip_id PK)  (payment_type_id PK)
                    pu_location_id ──┐
                    do_location_id ──┴── dim_zone
                                        (zone_id PK)
```

### Tablas

| Tabla | Filas | Descripcion |
|---|---|---|
| `fact_trips` | 26,718,285 | Cada viaje: tiempos, distancia, tarifa, propina, zona |
| `dim_vendor` | 2 | Creative Mobile Technologies / VeriFone Inc. |
| `dim_payment` | 6 | Credit card, Cash, No charge, Dispute, Unknown, Voided |
| `dim_ratecode` | 6 | Standard, JFK, Newark, Nassau, Negotiated, Group |
| `dim_zone` | 265 | Zonas NYC con borough y service zone |

### Columnas de fact_trips

| Columna | Tipo | Descripcion |
|---|---|---|
| `trip_id` | BIGSERIAL | PK autogenerada |
| `vendor_id` | SMALLINT FK | Proveedor del viaje |
| `pickup_datetime` | TIMESTAMP | Fecha y hora de recogida |
| `dropoff_datetime` | TIMESTAMP | Fecha y hora de llegada |
| `duration_min` | NUMERIC | Duracion del viaje en minutos |
| `passenger_count` | SMALLINT | Numero de pasajeros |
| `trip_distance` | NUMERIC | Distancia en millas |
| `pu_location_id` | SMALLINT FK | Zona de recogida |
| `do_location_id` | SMALLINT FK | Zona de destino |
| `ratecode_id` | SMALLINT FK | Tipo de tarifa |
| `payment_type_id` | SMALLINT FK | Metodo de pago |
| `fare_amount` | NUMERIC | Tarifa base |
| `tip_amount` | NUMERIC | Propina |
| `tip_pct` | NUMERIC | Propina como % de la tarifa |
| `total_amount` | NUMERIC | Total cobrado |
| `price_per_mile` | NUMERIC | Precio por milla |
| `hour` | SMALLINT | Hora de recogida (0-23) |
| `day_of_week` | SMALLINT | Dia de la semana (0=Lunes) |
| `month` | SMALLINT | Mes (1-12) |
| `year` | SMALLINT | Ano (2022-2024) |

---

## Archivos

```
04_postgresql/
├── 03_db_load.py    <- ETL: crea schema y carga datos desde CSV
└── 04_queries.sql   <- 10 queries avanzadas de analisis
```

---

## ETL — 03_db_load.py

El script ejecuta 4 etapas:

**1. Schema** — DROP + CREATE de las 5 tablas con Foreign Keys e indices

**2. Dimension tables** — Insercion directa de datos hardcodeados para
vendors, payments y ratecodes. Las zonas se leen desde
`data/taxi_zone_lookup.csv` (265 zonas NYC)

**3. Fact table** — Carga de `data/processed/fact_trips.csv` en chunks
de 100,000 filas usando `COPY FROM STDIN` (psycopg2), el metodo nativo
de PostgreSQL para carga masiva. Incluye:
- Rename de columnas segun mapeo definido
- Cast de columnas float a int (SMALLINT es estricto)
- Clip de valores extremos en tip_pct y price_per_mile
- Filtrado de FKs invalidas antes de insertar

**4. Indices** — 6 indices creados al final para acelerar queries en Power BI:

```sql
pickup_datetime    -- queries de rango temporal
pu_location_id     -- JOINs con dim_zone (pickup)
do_location_id     -- JOINs con dim_zone (dropoff)
payment_type_id    -- filtros por tipo de pago
(year, month)      -- agregaciones mensuales
hour               -- analisis por hora del dia
```

### Rendimiento de carga

| Metodo | Velocidad aprox |
|---|---|
| INSERT fila por fila | ~5,000 filas/seg |
| method="multi" | ~50,000 filas/seg |
| **COPY FROM STDIN** | **~300,000 filas/seg** |

---

## Queries Avanzadas — 04_queries.sql

10 queries que cubren los patrones mas demandados en entrevistas de datos:

| # | Query | Tecnica |
|---|---|---|
| 1 | Revenue total por ano y mes | GROUP BY, agregaciones |
| 2 | Top 10 zonas por revenue | JOIN, ORDER BY |
| 3 | Ranking de zonas por borough | CTE + RANK() OVER PARTITION BY |
| 4 | Revenue acumulado mensual | CTE + SUM() OVER ROWS |
| 5 | Variacion mes a mes (MoM) | CTE + LAG() OVER |
| 6 | Percentiles de propina por zona | PERCENTILE_CONT, CTE |
| 7 | Hora mas rentable por dia | CTE + RANK() OVER PARTITION BY |
| 8 | Segmentacion por distancia | CTE con CASE WHEN |
| 9 | Comparativo ano a ano por borough | JOIN, GROUP BY multi-dimension |
| 10 | Deteccion de outliers con Z-score | CTE + formula estadistica |

---

## Configuracion

### Requisitos

```
postgresql >= 14
psycopg2-binary
sqlalchemy
python-dotenv
pandas
```

### Variables de entorno (.env)

```env
DB_USER=postgres
DB_PASS=tu_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nyc_taxi
```

### Ejecucion

```bash
# Desde la raiz del proyecto
python 04_postgresql/03_db_load.py
```

El script hace DROP + CREATE al inicio, por lo que es re-ejecutable
de forma segura si se necesita recargar datos.

### Ver datos en pgAdmin

1. Abrir pgAdmin → click derecho en **Servers** → **Register > Server**
2. Conexion: `localhost:5432`, usuario `postgres`
3. Navegar: `nyc_taxi → Schemas → public → Tables`
4. Click derecho sobre cualquier tabla → **View/Edit Data → First 100 Rows**

---

## Resultados

```
Schema creado.
dim_vendor, dim_payment, dim_ratecode cargadas.
dim_zone cargada: 265 zonas.
Cargando data\processed\fact_trips.csv...
  ...
fact_trips cargada: 26,718,285 filas.
Indices creados.

Etapa 04 completada.
```
