-- Temiz ülke-yıl emisyon tablosu.
--  * Sadece GERÇEK ülkeler (3 harfli iso_code) — "World", "Asia" gibi agregalar elenir
--  * PARTITION BY year  → sorgular sadece ilgili yılları tarar (maliyet ↓)
--  * CLUSTER BY country → ülke filtreli sorgular hızlanır
-- BigQuery'ye özgü bu optimizasyonlar büyük tablolarda maliyeti/performansı belirler.

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
    co2,                                    -- toplam CO₂ (milyon ton)
    co2_per_capita,                         -- kişi başı CO₂ (ton)
    co2_growth_prct,                        -- yıllık % değişim
    share_global_co2,                       -- küresel emisyondaki pay (%)
    SAFE_DIVIDE(gdp, population) AS gdp_per_capita
FROM `${PROJECT}.${RAW}.owid_co2`
WHERE iso_code IS NOT NULL
  AND LENGTH(iso_code) = 3                  -- gerçek ülke kodu (OWID_WRL vb. elenir)
  AND year IS NOT NULL;
