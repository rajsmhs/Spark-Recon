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


  ==========================
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.context import SparkContext
from pyspark.sql.functions import *

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

# Define the existing table details
DATABASE = "fulcrum"
TABLE_NAME = "calendar_dim"
S3_PATH = "s3://anzbank-testing/calendar_dim"  # Make sure this matches your actual path

# Create the calendar data
df = spark.sql("""
    WITH dates_1900 AS (
        SELECT explode(sequence(0, 
            datediff(cast('2000-12-31' as date), cast('1900-01-01' as date)))) as n
    ),
    dates_2001 AS (
        SELECT explode(sequence(0, 
            datediff(cast('2100-12-31' as date), cast('2001-01-01' as date)))) as n
    ),
    all_dates AS (
        SELECT date_add(cast('1900-01-01' as date), n) as generated_date
        FROM dates_1900
        UNION ALL
        SELECT date_add(cast('2001-01-01' as date), n) as generated_date
        FROM dates_2001
    )
    SELECT 
        generated_date as CALENDAR_DT,
        (cast(year(generated_date) as bigint) * 1000000) +
        (cast(month(generated_date) as bigint) * 10000) +
        (cast(day(generated_date) as bigint) * 100) +
        (cast(extract(dow from generated_date) as bigint) + 11111) as SURROGATE_KEY,
        CASE extract(dow from generated_date)
            WHEN 0 THEN 'Sunday'
            WHEN 1 THEN 'Monday'
            WHEN 2 THEN 'Tuesday'
            WHEN 3 THEN 'Wednesday'
            WHEN 4 THEN 'Thursday'
            WHEN 5 THEN 'Friday'
            WHEN 6 THEN 'Saturday'
        END as DAY_OF_WEEK_NM
    FROM all_dates
    ORDER BY CALENDAR_DT
""")

# Write directly using DataFrame API
df.write \
    .mode("overwrite") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save(S3_PATH)
    
job.commit()

