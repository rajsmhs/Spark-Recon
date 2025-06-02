from pyspark.sql import SparkSession
from pyspark.sql.functions import input_file_name, lit, udf
from pyspark.sql.types import StringType
from datetime import datetime
import boto3
import os

def estimate_partitions_sampling(df, target_size_mb=125, sample_ratio=0.01):
    """
    Estimate partitions using sampling
    """
    # Take sample
    sample_df = df.sample(withReplacement=False, fraction=sample_ratio)
    
    # Calculate average row size from sample
    sample_count = sample_df.count()
    if sample_count > 0:
        sample_size = sample_df.rdd.mapPartitions(
            lambda x: [sum(len(str(row)) for row in x)]
        ).sum()
        avg_row_size = sample_size / sample_count
        
        # Extrapolate to full dataset
        total_count = df.count()
        estimated_size = total_count * avg_row_size
        
        # Calculate partitions
        num_partitions = max(1, int(estimated_size // (target_size_mb * 1024 * 1024)))
        return num_partitions
    return 1


def separate_and_map_files(file_list):
    csv_files = []
    file_dict = {}
    
    for file_path in file_list:
        if file_path.endswith('.csv.bz2'):  # Changed this line to check for complete extension
            csv_files.append(file_path)
            # Remove .csv.bz2 and add .tag
            tag_file = file_path.replace('.csv.bz2', '.tag')
            if tag_file in file_list:
                file_dict[file_path] = tag_file
    
    return csv_files, file_dict



def create_date_mapping(tag_mapping):
    """
    Creates mapping between CSV files and their dates from tag files
    """
    file_date_mapping = {}
    s3_client = boto3.client('s3')
    
    for csv_file, tag_file in tag_mapping.items():
        try:
            bucket = tag_file.split('s3://')[1].split('/')[0]
            print(bucket)
            key = '/'.join(tag_file.split('s3://')[1].split('/')[1:])
            print(key)
            response = s3_client.get_object(Bucket=bucket, Key=key)
            date_value = response['Body'].read().decode('utf-8').split(',')[0].strip()
            formatted_date = datetime.strptime(date_value, '%Y%m%d').strftime('%Y-%m-%d')
            print(formatted_date)
            
            # Store date mapping for all path variants
            original_path = csv_file
            s3_path = f"s3://{csv_file}" if not csv_file.startswith('s3://') else csv_file
            non_s3_path = csv_file.replace('s3://', '')
            
            file_date_mapping[original_path] = formatted_date
            file_date_mapping[s3_path] = formatted_date
            file_date_mapping[non_s3_path] = formatted_date
            
        except Exception as e:
            print(f"Error processing tag file {tag_file}: {str(e)}")
            
    return file_date_mapping


def process_csv_files(spark, file_list, output_path, batch_size=100):
    """
    Main function to process CSV files and add src_strt_trans column
    """
    s3_client = boto3.client('s3')
    
    # Separate files and create mappings
    csv_files, tag_mapping = separate_and_map_files(file_list)
    print("##################################")
    print(csv_files)
    print("##################################")
    print(tag_mapping)
    print("##################################")
    file_date_mapping = create_date_mapping(tag_mapping)
    print(file_date_mapping)
    print("##################################")
    
    
    # Print mappings for debugging
    print("File Date Mapping:")
    for k, v in file_date_mapping.items():
        print(f"{k}: {v}")
    
    # Broadcast the mapping
    mapping_broadcast = spark.sparkContext.broadcast(file_date_mapping)
    
    def get_date_from_file(file_path):
        # Try different path formats
        result = mapping_broadcast.value.get(file_path)
        if result is None:
            # Try with s3:// prefix
            result = mapping_broadcast.value.get(f"s3://{file_path}")
        if result is None:
            # Try without s3:// prefix
            result = mapping_broadcast.value.get(file_path.replace('s3://', ''))
            
        print(f"Processing file_path: {file_path}, Result: {result}")
        return result
    
    date_udf = udf(get_date_from_file, StringType())
    
    # Process CSV files in batches
    for i in range(0, len(csv_files), batch_size):
        batch_files = csv_files[i:i + batch_size]
        
        try:
            # Read and process batch
            df = (spark.read
                  .option("header", "true")
                  .csv(batch_files)
                  .withColumn("input_file", input_file_name())
                  .withColumn("src_strt_trans", date_udf(input_file_name()))
                 )
            print(df.count())
            num_part = estimate_partitions_sampling(df)
            print(num_part)
            # Show results
            # print("\nResulting DataFrame:")
            # df.select("input_file", "src_strt_trans").show(10, truncate=False)
            # output_data = "s3://adap-apse2-tbi-metadata-dev/output_data/runid4/"
            # df.coalesce(num_part).write.format('csv').mode("overwrite").option("compression", "bzip2").save(output_data)
            
        except Exception as e:
            print(f"Error processing batch starting at index {i}: {str(e)}")



==============================================================================================================================================
from pyspark.sql import SparkSession
from pyspark.sql.functions import input_file_name, lit, udf
from pyspark.sql.types import StringType
from datetime import datetime
import boto3
import os

file_options = {}
file_options["sep"] = ","
file_options["header"] = True
file_options["nullValue"] = None
file_options["format"] = "csv"
file_options["compression"] = "bzip2"

# spark_df = spark.read.options(**file_options).csv(source_file)

print(file_options)


def separate_and_map_files(file_list):
    csv_files = []
    file_dict = {}
    
    for file_path in file_list:
        if file_path.endswith('.csv.bz2'):  # Changed this line to check for complete extension
            csv_files.append(file_path)
            # Remove .csv.bz2 and add .tag
            tag_file = file_path.replace('.csv.bz2', '.tag')
            if tag_file in file_list:
                file_dict[file_path] = tag_file
    
    return csv_files, file_dict



import boto3
def create_date_and_count_mapping(tag_mapping):
    """
    Creates mapping between CSV files and their dates and counts from tag files
    """
    file_mapping = {}
    s3_client = boto3.client('s3')
    
    for csv_file, tag_file in tag_mapping.items():
        try:
            bucket = tag_file.split('s3://')[1].split('/')[0]
            key = '/'.join(tag_file.split('s3://')[1].split('/')[1:])
            response = s3_client.get_object(Bucket=bucket, Key=key)
            tag_content = response['Body'].read().decode('utf-8').split(',')
            
            date_value = tag_content[0].strip()
            count_value = int(tag_content[3].strip())
            formatted_date = datetime.strptime(date_value, '%Y%m%d').strftime('%Y-%m-%d')
            
            # Store both date and count mapping for all path variants
            original_path = csv_file
            s3_path = f"s3://{csv_file}" if not csv_file.startswith('s3://') else csv_file
            non_s3_path = csv_file.replace('s3://', '')
            
            file_mapping[original_path] = {'date': formatted_date, 'count': count_value}
            # file_mapping[s3_path] = {'date': formatted_date, 'count': count_value}
            # file_mapping[non_s3_path] = {'date': formatted_date, 'count': count_value}
            
        except Exception as e:
            print(f"Error processing tag file {tag_file}: {str(e)}")
            raise
            
    return file_mapping





def validate_counts(df, file_mapping):
    """
    Validates counts for all files in the DataFrame
    Returns a dictionary of validation results
    """
    validation_results = {}
    error_messages = []
    
    # Group by input file and count rows
    file_counts = df.groupBy("input_file").count().collect()
    
    for row in file_counts:
        file_path = row["input_file"]
        df_count = row["count"]
        
        # Try different path variants
        mapping_info = None
        for path_variant in [file_path, f"s3://{file_path}", file_path.replace('s3://', '')]:
            if path_variant in file_mapping:
                mapping_info = file_mapping[path_variant]
                break
        
        if mapping_info:
            tag_count = mapping_info['count']
            if df_count != tag_count:
                error_message = (
                    f"Count mismatch for {file_path} DataFrame count: {df_count} Tag file count: {tag_count}"
                )
                error_messages.append(error_message)
        else:
            error_message = f"No count information found for {file_path}"
            error_messages.append(error_message) 
    return error_messages





def write_df_to_s3(df, output_path, format='csv', file_options):
    """
    Writes a DataFrame to S3 with optional partitioning
    """
    df.write.format('csv').mode("overwrite").option("compression", "bzip2").save(output_path))



def process_csv_files(spark, file_list, output_path):
    """
    Main function to process CSV files and add src_strt_trans column
    Processes all files together but validates counts before writing
    """
    try:
        # Separate files and create mappings
        csv_files, tag_mapping = separate_and_map_files(file_list)
        print(csv_files)
        print(tag_mapping)
        if not csv_files:
            raise ValueError("No CSV files found in the input list")
            
        print(f"Found {len(csv_files)} CSV files to process")
        
        # Create file mapping with dates and counts
        file_mapping = create_date_and_count_mapping(tag_mapping)
        print("Created file mapping successfully")
        print(file_mapping)
        
#         # Broadcast the mapping
        mapping_broadcast = spark.sparkContext.broadcast(file_mapping)
        
        def get_date_from_file(file_path):
            mapping_info = None
            for path_variant in [file_path, f"s3://{file_path}", file_path.replace('s3://', '')]:
                if path_variant in mapping_broadcast.value:
                    mapping_info = mapping_broadcast.value[path_variant]
                    break
            return mapping_info['date'] if mapping_info else None
        
        date_udf = udf(get_date_from_file, StringType())
        print("Reading all CSV files...")
        df = (spark.read
              .option("header", "true")
              .csv(csv_files)
              .withColumn("input_file", input_file_name())
              .withColumn("src_strt_trans", date_udf(input_file_name()))
             )
        df.show(10, truncate=False)
        print("Validating counts for all files...")
        err = validate_counts(df, file_mapping)
        print(err)

#         print("Count validation passed for all files")
        
    except Exception as e:
        print(f"ERROR: Unexpected error during processing:\n{str(e)}")



process_csv_files(spark, file_list_out, "hhh")




import re

def check_data_source(string, data_source):
    pattern = r'\b' + re.escape(data_source) + r'\b'
    return bool(re.search(pattern, string, re.IGNORECASE))

# Usage
string1 = "The data source is Fulcrum"
string2 = "The data source is fulcrumsens"
data_source = "fulcrum"

print(check_data_source(string1, data_source))  # True
print(check_data_source(string2, data_source))  # False

