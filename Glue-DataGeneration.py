from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *
import random
from datetime import datetime, timedelta
import string

def create_spark_session():
    return (SparkSession.builder
            .appName("Transaction Data Generator")
            .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain")
            .getOrCreate())

def random_string(length, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(length))

def random_date(start_year=2020):
    start = datetime(start_year, 1, 1)
    end = datetime.now()
    return start + timedelta(days=random.randint(0, (end - start).days))

def generate_transaction_data(spark, num_records=100):
    # Define schema
    schema = StructType([
        StructField("SRC_STRT_DT", DateType(), True),
        StructField("DET_AMOUNT", StringType(), True),  # Changed to StringType initially
        StructField("DET_FUNC_CODE", StringType(), True),
        StructField("DET_PROD_CODE", StringType(), True),
        StructField("DET_SUB_PROD_CODE", StringType(), True),
        StructField("DET_ACC_NBR_ORIG", StringType(), True),
        StructField("BRR_MRCH_NBR", StringType(), True),
        StructField("ROW_CHKSUM", StringType(), True),
        StructField("BRR_MRCH_NBR1", StringType(), True),
        StructField("DET_DATE_CAPTURE", DateType(), True),
        StructField("DET_TRAN_CLASS", StringType(), True),
        StructField("DET_SOURCE_ID", StringType(), True),
        StructField("DET_ODS_END_POINT", StringType(), True),
        StructField("CURR_CODE", StringType(), True),
        StructField("DET_CHANNEL_CODE", StringType(), True),
        StructField("DET_REC_TYPE", StringType(), True),
        StructField("TAND_WALLET_ID", StringType(), True),
        StructField("MCC", StringType(), True),
        StructField("CRX_MCC_CODE", StringType(), True),
        StructField("PMT_AUXDOM", StringType(), True),
        StructField("AUX_DOM", StringType(), True),
        StructField("EX_AUX_DOM", StringType(), True),
        StructField("AF_TYPE", StringType(), True),
        StructField("TRACK_2", StringType(), True),
        StructField("DET_BANK_ORIGIN", StringType(), True),
        StructField("DET_BANK_ORIGIN_1", StringType(), True),
        StructField("STATEMENT_DETAILS", StringType(), True),
        StructField("DET_TRAN_CODE", StringType(), True),
        StructField("DUP_SQNC_NBR", StringType(), True),
        StructField("DET_BSB", StringType(), True),
        StructField("DET_TRACE_ID", StringType(), True),
        StructField("BRR_NUMBER_OF_ITEMS", StringType(), True),  # Changed to StringType initially
        StructField("RECEIPT_NUMBER", StringType(), True),
        StructField("FROM_ACCOUNT", StringType(), True),
        StructField("TO_ACCOUNT", StringType(), True),
        StructField("DET_APP_GROUP_CODE", StringType(), True),
        StructField("SOURCE1", StringType(), True),
        StructField("DET_SEQ_NBR", StringType(), True),
        StructField("DET_APP_DELV_CODE", StringType(), True),
        StructField("BPAY_PAYER_INITR_CODE", StringType(), True),
        StructField("DET_DATE_EFFECTIVE", DateType(), True),
        StructField("CSL_REFUND_REASON", StringType(), True),
        StructField("DET_VALUE_NONVAL", StringType(), True),  # Changed to StringType initially
        StructField("DET_FLOAT_3_DAYS", StringType(), True),  # Changed to StringType initially
        StructField("CASH_AMT", StringType(), True),  # Changed to StringType initially
        StructField("DET_TIME_CAPTURE", TimestampType(), True),
        StructField("BILLER_NUMBER", StringType(), True),
        StructField("DET_MISC_FIELD", StringType(), True),
        StructField("BRR_ITEM_CHEQUE_NBR", StringType(), True),
        StructField("SRC_DELT_FLAG", StringType(), True)
    ])

    # Generate data
    data = []
    for _ in range(num_records):
        row = [
            random_date(),  # SRC_STRT_DT
            f"{random.uniform(1, 10000):.3f}",  # DET_AMOUNT
            random.choice(['CB','CC']),  # DET_FUNC_CODE
            random_string(4),  # DET_PROD_CODE
            random_string(4),  # DET_SUB_PROD_CODE
            str(random.randint(1000000000, 9999999999)),  # DET_ACC_NBR_ORIG
            random_string(10),  # BRR_MRCH_NBR
            random_string(32),  # ROW_CHKSUM
            random_string(10),  # BRR_MRCH_NBR1
            random_date(),  # DET_DATE_CAPTURE
            random.choice(['BL','CL']),  # DET_TRAN_CLASS
            random.choice(['CSL', 'CMO', 'ILS', 'PCB', 'IVR', 'MPB', 'AX1', 'EDIB', 'EDOB', 'APY', 'BDO', 'BLO', 'DDA', 'ESAN', 'MEL', 'MTS', 'NOM', 'POSS', 'PTP', 'SWFT', 'VIP', 'VPLD', 'BPS', 'BLN', 'LIQ', 'TAL', 'GPP', 'PEG', 'MTSX', 'BCH', 'REM', 'XCG', 'TLG', 'VLPD', 'EDIA', 'EDOA']),  # DET_SOURCE_ID
            random.choice(['999','121','967','184','963','121','965','967','184']),  # DET_ODS_END_POINT
            random.choice(['USD', 'EUR', 'GBP', 'AUD']),  # CURR_CODE
            random.choice(['119', '202', '400', '405', '406', '407', '529', '538', '540', '541', '545', '552', '615', '620', '621', '622', '623', '710', '711', '800', '801', '855', '856', '861', '270', '450', '870', '871']),  # DET_CHANNEL_CODE
            random.choice(['D','C','E','F']),  # DET_REC_TYPE
            random_string(16),  # TAND_WALLET_ID
            str(random.randint(1000, 9999)),  # MCC
            str(random.randint(1000, 9999)),  # CRX_MCC_CODE
            random_string(8),  # PMT_AUXDOM
            random.choice(['Y', 'N']),  # AUX_DOM
            random.choice(['Y', 'N']),  # EX_AUX_DOM
            random_string(2),  # AF_TYPE
            random_string(40),  # TRACK_2
            random_string(6),  # DET_BANK_ORIGIN
            random_string(6),  # DET_BANK_ORIGIN_1
            random.choice(['Payment	500	paid	McDonalda', '800	paid	for	school	fee', '9004	TO 0984572829', 'NETFLIX.COM	INDIA	BLR','','-']),  # STATEMENT_DETAILS
            random.choice(['008', '806', '050', '052', '053', '054', '055', '056', '057', '079', '013', '037', '098', '099', '000', '034', '030', '080', '070', '051', '060']), # DET_TRAN_CODE
            random_string(8),  # DUP_SQNC_NBR
            random_string(6),  # DET_BSB
            random_string(16),  # DET_TRACE_ID
            str(random.randint(1, 100)),  # BRR_NUMBER_OF_ITEMS
            random_string(10),  # RECEIPT_NUMBER
            str(random.randint(1000000000, 9999999999)),  # FROM_ACCOUNT
            str(random.randint(1000000000, 9999999999)),  # TO_ACCOUNT
            random.choice(['ZB', 'N3', 'N2', 'N4', 'N1', 'NE', 'ND', 'NG', 'NA']),  # DET_APP_GROUP_CODE
            random_string(8),  # SOURCE1
            str(random.randint(1, 999999)),  # DET_SEQ_NBR
            random_string(6),  # DET_APP_DELV_CODE
            random.choice(['ANZ', 'BNZ']),  # BPAY_PAYER_INITR_CODE
            random_date(),  # DET_DATE_EFFECTIVE
            random_string(8),  # CSL_REFUND_REASON
            f"{random.uniform(1, 10000):.3f}",  # DET_VALUE_NONVAL
            str(random.randint(0, 3)),  # DET_FLOAT_3_DAYS
            f"{random.uniform(1, 10000):.3f}",  # CASH_AMT
            datetime.now(),  # DET_TIME_CAPTURE
            str(random.randint(100000, 999999)),  # BILLER_NUMBER
            random_string(50),  # DET_MISC_FIELD
            random_string(10),  # BRR_ITEM_CHEQUE_NBR
            random.choice(['I', 'U', 'D'])  # SRC_DELT_FLAG
        ]
        data.append(row)

    # Create DataFrame
    df = spark.createDataFrame(data, schema)

    # Cast numeric columns to proper types
    df = df.select(
        col("SRC_STRT_DT"),
        col("DET_AMOUNT").cast(DecimalType(18, 3)),
        col("DET_FUNC_CODE"),
        col("DET_PROD_CODE"),
        col("DET_SUB_PROD_CODE"),
        col("DET_ACC_NBR_ORIG"),
        col("BRR_MRCH_NBR"),
        col("ROW_CHKSUM"),
        col("BRR_MRCH_NBR1"),
        col("DET_DATE_CAPTURE"),
        col("DET_TRAN_CLASS"),
        col("DET_SOURCE_ID"),
        col("DET_ODS_END_POINT"),
        col("CURR_CODE"),
        col("DET_CHANNEL_CODE"),
        col("DET_REC_TYPE"),
        col("TAND_WALLET_ID"),
        col("MCC"),
        col("CRX_MCC_CODE"),
        col("PMT_AUXDOM"),
        col("AUX_DOM"),
        col("EX_AUX_DOM"),
        col("AF_TYPE"),
        col("TRACK_2"),
        col("DET_BANK_ORIGIN"),
        col("DET_BANK_ORIGIN_1"),
        col("STATEMENT_DETAILS"),
        col("DET_TRAN_CODE"),
        col("DUP_SQNC_NBR"),
        col("DET_BSB"),
        col("DET_TRACE_ID"),
        col("BRR_NUMBER_OF_ITEMS").cast(IntegerType()),
        col("RECEIPT_NUMBER"),
        col("FROM_ACCOUNT"),
        col("TO_ACCOUNT"),
        col("DET_APP_GROUP_CODE"),
        col("SOURCE1"),
        col("DET_SEQ_NBR"),
        col("DET_APP_DELV_CODE"),
        col("BPAY_PAYER_INITR_CODE"),
        col("DET_DATE_EFFECTIVE"),
        col("CSL_REFUND_REASON"),
        col("DET_VALUE_NONVAL").cast(DecimalType(18, 3)),
        col("DET_FLOAT_3_DAYS").cast(IntegerType()),
        col("CASH_AMT").cast(DecimalType(18, 3)),
        col("DET_TIME_CAPTURE"),
        col("BILLER_NUMBER"),
        col("DET_MISC_FIELD"),
        col("BRR_ITEM_CHEQUE_NBR"),
        col("SRC_DELT_FLAG")
    )
    
    return df



S3_PATH = "s3a://dbt-athena-vrajabhi-bucket/transaction_data"
NUM_RECORDS = 100000

# Create Spark session
spark = create_spark_session()

# Generate data
print("Generating data...")
df = generate_transaction_data(spark, NUM_RECORDS)

# Add partition column
df = df.withColumn("load_date", date_format(current_date(), "yyyyMMdd"))

# Write to S3
print(f"Writing data to {S3_PATH}...")
(df.
 coalesce(10)
 .write
 .mode("append")
 .partitionBy("load_date")
 .format("parquet")
 .save(S3_PATH))






from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import AwsGlueJobOperator
from airflow.providers.amazon.aws.sensors.glue import AwsGlueJobSensor
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import boto3

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 5, 28),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'glue_job_pipeline',
    default_args=default_args,
    schedule_interval=timedelta(days=1),
)

def get_glue_job_outputs(**context):
    glue_client = boto3.client('glue')
    
    # Get the job run ID from the previous task
    job_run_id = context['task_instance'].xcom_pull(task_ids='glue_job_1', key='return_value')
    job_name = 'your_first_glue_job_name'
    
    # Get job run details
    response = glue_client.get_job_run(
        JobName=job_name,
        RunId=job_run_id
    )
    
    # Extract the output locations from job arguments
    job_run = response['JobRun']
    
    # Get the output directory from job parameters or arguments
    output_files = []
    
    # If you have configured job metrics
    if 'Statistics' in job_run:
        written_files = job_run['Statistics'].get('WrittenFiles', [])
        output_files.extend(written_files)
    
    # You can also get from job parameters if you've explicitly set them
    if 'Arguments' in job_run:
        output_location = job_run['Arguments'].get('--output_location', '')
        if output_location:
            output_files.append(output_location)
    
    context['task_instance'].xcom_push(key='output_files', value=output_files)
    return output_files

# First Glue job
glue_job_1 = AwsGlueJobOperator(
    task_id='glue_job_1',
    job_name='your_first_glue_job_name',
    script_location='s3://your-bucket/scripts/first_job_script.py',
    iam_role_name='your-glue-role',
    dag=dag,
)

# Sensor to wait for the first Glue job to complete
glue_job_1_sensor = AwsGlueJobSensor(
    task_id='glue_job_1_sensor',
    job_name='your_first_glue_job_name',
    run_id="{{ task_instance.xcom_pull(task_ids='glue_job_1', key='return_value') }}",
    dag=dag,
)

# Task to get Glue job outputs
get_outputs_task = PythonOperator(
    task_id='get_glue_outputs',
    python_callable=get_glue_job_outputs,
    provide_context=True,
    dag=dag,
)

# Second Glue job
glue_job_2 = AwsGlueJobOperator(
    task_id='glue_job_2',
    job_name='your_second_glue_job_name',
    script_location='s3://your-bucket/scripts/second_job_script.py',
    iam_role_name='your-glue-role',
    script_args={
        '--input_files': "{{ task_instance.xcom_pull(task_ids='get_glue_outputs', key='output_files') }}"
    },
    dag=dag,
)

glue_job_1 >> glue_job_1_sensor >> get_outputs_task >> glue_job_2
