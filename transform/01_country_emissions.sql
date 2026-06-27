-- Clean country-year emissions table.
--  * Only REAL countries (3-letter iso_code) — aggregates like "World"/"Asia" are dropped
--  * PARTITION BY year  → queries scan only the relevant years (lower cost)
--  * CLUSTER BY country → country-filtered queries run faster
-- These BigQuery-specific optimizations drive cost/performance on large tables.

CREATE OR REPLACE TABLE `${PROJECT}.${ANALYTICS}.country_emissions`
PARTITION BY RANGE_BUCKET(year, GENERATE_ARRAY(1750, 2050, 1))
CLUSTER BY country
AS
SELECT
    country,
    iso_code,
    year,
    population,
    gdp,
    co2,                                    -- total CO₂ (million tonnes)
    co2_per_capita,                         -- per-capita CO₂ (tonnes)
    co2_growth_prct,                        -- year-over-year % change
    share_global_co2,                       -- share of global emissions (%)
    SAFE_DIVIDE(gdp, population) AS gdp_per_capita
FROM `${PROJECT}.${RAW}.owid_co2`
WHERE iso_code IS NOT NULL
  AND LENGTH(iso_code) = 3                  -- real country code (drops OWID_WRL etc.)
  AND year IS NOT NULL;
