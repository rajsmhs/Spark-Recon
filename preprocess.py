from pyspark.sql import SparkSession
from pyspark.sql.functions import input_file_name, lit, udf
from pyspark.sql.types import StringType
from datetime import datetime
import boto3
import os

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
            
            # Show results
            print("\nResulting DataFrame:")
            df.select("input_file", "src_strt_trans").show(10, truncate=False)
            
        except Exception as e:
            print(f"Error processing batch starting at index {i}: {str(e)}")

