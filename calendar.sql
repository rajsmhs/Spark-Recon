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
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql.functions import *
import sys

# Get job parameters
args = getResolvedOptions(
    sys.argv,
    [
        'calendar_start_date',
        'calendar_end_date',
        'database_name',
        'table_name',
        'warehouse_dir'  # Add this parameter
    ]
)

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

# Define table identifier and location
table_identifier = f"{args['database_name']}.{args['table_name']}"
table_location = f"{args['warehouse_dir']}/{args['table_name']}"

# Drop existing table if exists
spark.sql(f"DROP TABLE IF EXISTS {table_identifier}")

# Create table with Iceberg format
create_table_sql = f"""
    CREATE TABLE {table_identifier} (
        CALENDAR_DT DATE,
        SURROGATE_KEY BIGINT,
        DAY_OF_WEEK_NM STRING
    )
    USING iceberg
    TBLPROPERTIES (
        'write.format.default' = 'parquet',
        'write.parquet.compression-codec' = 'snappy'
    )
    LOCATION '{table_location}'
"""

spark.sql(create_table_sql)

# Create the calendar data
df = spark.sql(f"""
    WITH dates_part1 AS (
        SELECT explode(sequence(0, 
            datediff(cast('2000-12-31' as date), cast('{args['calendar_start_date']}' as date)))) as n
    ),
    dates_part2 AS (
        SELECT explode(sequence(0, 
            datediff(cast('{args['calendar_end_date']}' as date), cast('2001-01-01' as date)))) as n
    ),
    all_dates AS (
        SELECT date_add(cast('{args['calendar_start_date']}' as date), n) as generated_date
        FROM dates_part1
        UNION ALL
        SELECT date_add(cast('2001-01-01' as date), n) as generated_date
        FROM dates_part2
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

# Write to table
df.write \
    .format("iceberg") \
    .mode("append") \
    .saveAsTable(table_identifier)

job.commit()
