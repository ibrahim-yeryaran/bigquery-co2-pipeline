-- Ranks countries by total and per-capita emissions for each year.
-- Answers "who emitted the most in a given year, and who leads per capita".

CREATE OR REPLACE TABLE `${PROJECT}.${ANALYTICS}.top_emitters`
CLUSTER BY year
AS
SELECT
    year,
    country,
    iso_code,
    co2,
    co2_per_capita,
    share_global_co2,
    RANK() OVER (PARTITION BY year ORDER BY co2 DESC)            AS rank_total_co2,
    RANK() OVER (PARTITION BY year ORDER BY co2_per_capita DESC) AS rank_per_capita
FROM `${PROJECT}.${ANALYTICS}.country_emissions`
WHERE co2 IS NOT NULL;
