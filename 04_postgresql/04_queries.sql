-- ─────────────────────────────────────────────────────────────────────────────
--  04_queries.sql
--  NYC Taxi Analytics — Queries avanzadas: CTEs + Window Functions
-- ─────────────────────────────────────────────────────────────────────────────


-- ── 1. REVENUE TOTAL POR AÑO Y MES ───────────────────────────────────────────
SELECT
    year,
    month,
    COUNT(*)                        AS total_trips,
    ROUND(SUM(fare_amount)::NUMERIC, 2)  AS revenue,
    ROUND(AVG(fare_amount)::NUMERIC, 2)  AS avg_fare,
    ROUND(AVG(tip_amount)::NUMERIC,  2)  AS avg_tip,
    ROUND(AVG(duration_min)::NUMERIC, 2) AS avg_duration_min
FROM fact_trips
GROUP BY year, month
ORDER BY year, month;


-- ── 2. TOP 10 ZONAS POR REVENUE (con nombre de zona) ─────────────────────────
SELECT
    z.zone,
    z.borough,
    COUNT(*)                             AS total_trips,
    ROUND(SUM(f.fare_amount)::NUMERIC, 2) AS total_revenue,
    ROUND(AVG(f.fare_amount)::NUMERIC, 2) AS avg_fare,
    ROUND(AVG(f.tip_pct)::NUMERIC, 2)     AS avg_tip_pct
FROM fact_trips f
JOIN dim_zone z ON f.pu_location_id = z.zone_id
GROUP BY z.zone, z.borough
ORDER BY total_revenue DESC
LIMIT 10;


-- ── 3. WINDOW FUNCTION — RANKING DE ZONAS POR REVENUE DENTRO DE CADA BOROUGH ──
WITH zone_revenue AS (
    SELECT
        z.borough,
        z.zone,
        ROUND(SUM(f.fare_amount)::NUMERIC, 2) AS revenue
    FROM fact_trips f
    JOIN dim_zone z ON f.pu_location_id = z.zone_id
    GROUP BY z.borough, z.zone
)
SELECT
    borough,
    zone,
    revenue,
    RANK() OVER (PARTITION BY borough ORDER BY revenue DESC) AS rank_in_borough
FROM zone_revenue
ORDER BY borough, rank_in_borough;


-- ── 4. WINDOW FUNCTION — REVENUE ACUMULADO MENSUAL POR AÑO ───────────────────
WITH monthly AS (
    SELECT
        year,
        month,
        ROUND(SUM(fare_amount)::NUMERIC, 2) AS monthly_revenue
    FROM fact_trips
    GROUP BY year, month
)
SELECT
    year,
    month,
    monthly_revenue,
    ROUND(SUM(monthly_revenue) OVER (
        PARTITION BY year
        ORDER BY month
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )::NUMERIC, 2) AS cumulative_revenue
FROM monthly
ORDER BY year, month;


-- ── 5. WINDOW FUNCTION — VARIACIÓN MES A MES (MoM) ───────────────────────────
WITH monthly AS (
    SELECT
        year,
        month,
        ROUND(SUM(fare_amount)::NUMERIC, 2) AS revenue
    FROM fact_trips
    GROUP BY year, month
)
SELECT
    year,
    month,
    revenue,
    LAG(revenue) OVER (ORDER BY year, month) AS prev_month_revenue,
    ROUND((revenue - LAG(revenue) OVER (ORDER BY year, month))
        / NULLIF(LAG(revenue) OVER (ORDER BY year, month), 0) * 100, 2) AS mom_pct_change
FROM monthly
ORDER BY year, month;


-- ── 6. PERCENTILES DE PROPINA POR ZONA (TOP 10 ZONAS) ────────────────────────
WITH top_zones AS (
    SELECT pu_location_id
    FROM fact_trips
    GROUP BY pu_location_id
    ORDER BY SUM(fare_amount) DESC
    LIMIT 10
)
SELECT
    z.zone,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY f.tip_amount)::NUMERIC, 2) AS p25,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY f.tip_amount)::NUMERIC, 2) AS p50,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY f.tip_amount)::NUMERIC, 2) AS p75,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY f.tip_amount)::NUMERIC, 2) AS p90,
    ROUND(AVG(f.tip_amount)::NUMERIC, 2)                                           AS avg_tip
FROM fact_trips f
JOIN dim_zone z ON f.pu_location_id = z.zone_id
WHERE f.pu_location_id IN (SELECT pu_location_id FROM top_zones)
GROUP BY z.zone
ORDER BY p50 DESC;


-- ── 7. HORA MÁS RENTABLE POR DÍA DE SEMANA ───────────────────────────────────
WITH hour_stats AS (
    SELECT
        day_of_week,
        hour,
        COUNT(*)                              AS trips,
        ROUND(AVG(fare_amount)::NUMERIC, 2)   AS avg_fare,
        ROUND(AVG(tip_amount)::NUMERIC, 2)    AS avg_tip
    FROM fact_trips
    GROUP BY day_of_week, hour
)
SELECT
    CASE day_of_week
        WHEN 0 THEN 'Lunes'    WHEN 1 THEN 'Martes'
        WHEN 2 THEN 'Miércoles' WHEN 3 THEN 'Jueves'
        WHEN 4 THEN 'Viernes'  WHEN 5 THEN 'Sábado'
        WHEN 6 THEN 'Domingo'
    END AS dia,
    hour,
    trips,
    avg_fare,
    avg_tip,
    RANK() OVER (PARTITION BY day_of_week ORDER BY avg_fare DESC) AS rank_by_fare
FROM hour_stats
ORDER BY day_of_week, rank_by_fare;


-- ── 8. CTE RECURSIVA — SEGMENTACIÓN DE VIAJES POR DISTANCIA ──────────────────
WITH segments AS (
    SELECT
        CASE
            WHEN trip_distance < 1    THEN '0-1 milla'
            WHEN trip_distance < 3    THEN '1-3 millas'
            WHEN trip_distance < 5    THEN '3-5 millas'
            WHEN trip_distance < 10   THEN '5-10 millas'
            ELSE '10+ millas'
        END AS segmento,
        fare_amount,
        tip_amount,
        tip_pct,
        duration_min
    FROM fact_trips
)
SELECT
    segmento,
    COUNT(*)                                AS total_trips,
    ROUND(AVG(fare_amount)::NUMERIC, 2)     AS avg_fare,
    ROUND(AVG(tip_amount)::NUMERIC, 2)      AS avg_tip,
    ROUND(AVG(tip_pct)::NUMERIC, 2)         AS avg_tip_pct,
    ROUND(AVG(duration_min)::NUMERIC, 2)    AS avg_duration_min
FROM segments
GROUP BY segmento
ORDER BY MIN(
    CASE segmento
        WHEN '0-1 milla'   THEN 1 WHEN '1-3 millas' THEN 2
        WHEN '3-5 millas'  THEN 3 WHEN '5-10 millas' THEN 4
        ELSE 5
    END
);


-- ── 9. COMPARATIVO AÑO A AÑO POR BOROUGH ─────────────────────────────────────
SELECT
    z.borough,
    f.year,
    COUNT(*)                              AS trips,
    ROUND(SUM(f.fare_amount)::NUMERIC, 2) AS revenue,
    ROUND(AVG(f.tip_pct)::NUMERIC, 2)     AS avg_tip_pct,
    ROUND(AVG(f.duration_min)::NUMERIC, 2) AS avg_duration
FROM fact_trips f
JOIN dim_zone z ON f.pu_location_id = z.zone_id
GROUP BY z.borough, f.year
ORDER BY z.borough, f.year;


-- ── 10. DETECCIÓN DE VIAJES ATÍPICOS (outliers con Z-score) ──────────────────
WITH stats AS (
    SELECT
        AVG(fare_amount)   AS mean_fare,
        STDDEV(fare_amount) AS std_fare
    FROM fact_trips
)
SELECT
    trip_id,
    pickup_datetime,
    pu_location_id,
    do_location_id,
    trip_distance,
    fare_amount,
    ROUND(((fare_amount - mean_fare) / NULLIF(std_fare, 0))::NUMERIC, 2) AS z_score
FROM fact_trips, stats
WHERE ABS((fare_amount - mean_fare) / NULLIF(std_fare, 0)) > 3
ORDER BY z_score DESC
LIMIT 50;
