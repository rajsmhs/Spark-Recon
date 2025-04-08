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





