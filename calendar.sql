WITH cte_1900 AS (
  SELECT n 
  FROM UNNEST(SEQUENCE(0, CAST(DATE_DIFF('day', DATE '1900-01-01', DATE '2000-12-31') AS INTEGER))) AS t(n)
),

cte_2001 AS (
  SELECT n 
  FROM UNNEST(SEQUENCE(0, CAST(DATE_DIFF('day', DATE '2001-01-01', DATE '2100-12-31') AS INTEGER))) AS t(n)
)

select generated_date,ROW_NUMBER() OVER (ORDER BY generated_date) as id from 
(
SELECT 
DATE_ADD('day', n, DATE '1900-01-01') as generated_date
FROM cte_1900
union all 
SELECT 
 DATE_ADD('day', n, DATE '2001-01-01') as generated_date
FROM cte_2001
)
order by generated_date desc







======================
CASE
    WHEN STRPOS(COLUMN_70, REGEXP_EXTRACT(COLUMN_70, '(:[0-9]{2})')) > 1 
         AND STRPOS(COLUMN_70, REGEXP_EXTRACT(COLUMN_70, '(:[0-9]{2})')) < STRPOS(COLUMN_70, '-') THEN
        SUBSTRING(COLUMN_70, 1, STRPOS(COLUMN_70, REGEXP_EXTRACT(COLUMN_70, '(:[0-9]{2})')) - 1)

    WHEN STRPOS(COLUMN_70, REGEXP_EXTRACT(COLUMN_70, '(:[0-9]{2})')) > 1 
         AND STRPOS(COLUMN_70, '-') < STRPOS(COLUMN_70, REGEXP_EXTRACT(COLUMN_70, '(:[0-9]{2})')) THEN
        SUBSTRING(COLUMN_70, 1, STRPOS(COLUMN_70, '-') - 1)

    WHEN STRPOS(COLUMN_70, REGEXP_EXTRACT(COLUMN_70, '(:[0-9]{2})')) > 1 THEN
        SUBSTRING(COLUMN_70, 1, STRPOS(COLUMN_70, REGEXP_EXTRACT(COLUMN_70, '(:[0-9]{2})')) - 1)

    WHEN STRPOS(COLUMN_70, '-') > 1 THEN
        SUBSTRING(COLUMN_70, 1, STRPOS(COLUMN_70, '-') - 1)

    ELSE COLUMN_70
END AS COLUMN_70_TRIMED


==========================

The CURRENCY_CONVERSION table is a critical component in our financial data infrastructure that maintains foreign exchange (FX) rate information for currency conversions across business operations. The table structure comprises four essential elements: CALENDAR_DATE for recording the validity date, FROM_CUR representing the source currency, TO_CUR indicating the target currency, and FX_RATE storing the actual conversion rate. Data is sourced from the FX_RATES view, with built-in quality control that excludes null exchange rates.

The table supports both direct and inverse currency conversions, optimizing data storage while maintaining full functionality. It enables various financial operations including reporting, cross-border transactions, historical analysis, and regulatory compliance. Regular daily updates ensure current market rates are available for business operations, making it a reliable source for all currency-related calculations. Due to its critical role in financial accuracy, access to this table is carefully managed through appropriate security protocols.


