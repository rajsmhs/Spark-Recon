import os
import json
import logging
from datetime import datetime
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
import fastavro
from fastavro import writer, parse_schema
import avro.schema
from avro.io import BinaryDecoder, DatumReader
import pickle

from pyflink.datastream import StreamExecutionEnvironment, CheckpointingMode
from pyflink.common import Configuration, Time
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream.connectors import FlinkKafkaConsumer
from pyflink.common import Types
from pyflink.datastream.functions import MapFunction, ProcessWindowFunction
from pyflink.datastream.window import TumblingProcessingTimeWindows
from pyflink.datastream import FileSystemCheckpointStorage
from avro.datafile import DataFileWriter
from avro.io import DatumWriter
import uuid
import io
from typing import Dict, List, Any, Union
from itertools import product
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

parse_flag=True
#local_file_path='/Users/vrajabhi/Documents/flink-ecommerse/Schema_Folder/transaction_schema.json'
local_file_path=None
s3_prefix='schema_dir/schema_new.json'
s3_bucket='aws-glue-assets-767397672884-us-east-1'
# s3_prefix=None
# s3_bucket=None

# Configuration
CONFIG = { 
    'kafka': {
        'bootstrap_servers': 'localhost:9092',
        'group_id': 'banking-transaction-group-new-25th-jan-2025-01-00',
        'auto_offset_reset': 'earliest',
        'topic': 'Event-Mesh-topic-11111-25th-jan-night'
    },
    's3': {
        'bucket_name': 'aws-glue-assets-767397672884-us-east-1',
        'raw_prefix': 'Event_raw_avro_array_flatten/',
        'flattened_prefix': 'Event_flatten_avro_array_flatten/'
    },
    'checkpoint': {
        'interval': 60000,
        'dir': 'file:///Users/vrajabhi/Documents/flink-ecommerse/event_mesh'
    },
    'window': {
        'size': Time.seconds(10)
    },
    'jar_path' : {
        'flink_kafka_connector_jar': 'file:///Users/vrajabhi/Documents/flink-ecommerse/flink-sql-connector-kafka-3.3.0-1.20.jar'
    }
}


def read_json_file(parse_flag,local_file_path, s3_prefix=None, s3_bucket=None):
    try:
        if s3_bucket:
            s3 = boto3.client('s3')
            try:
                response = s3.get_object(Bucket=s3_bucket, Key=s3_prefix)
                file_content = response['Body'].read().decode('utf-8')
                data = json.loads(file_content)
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.error(f"File not found in S3 bucket {s3_bucket}, key {s3_prefix}")
                    raise FileNotFoundError(f"S3 object not found: s3://{s3_bucket}/{s3_prefix}")
                else:
                    logger.error(f"Error accessing S3: {str(e)}")
                    raise
        else:
            if local_file_path is None:
                print("Error: local_file_path is None")
                return None
    
            if not os.path.exists(local_file_path):
                print(f"Error: File does not exist at {local_file_path}")
                return None
            
            with open(local_file_path, 'r') as file:
                data = json.load(file)
        
        if parse_flag:
            field_list = []
            for item in data:
                field_list.append (item)

            new_data_dict = {"type": "record", "name": "Root", "fields": field_list}
            new_data_str = json.dumps(new_data_dict)
        else:
            new_data_dict = data
            new_data_str = json.dumps(new_data_dict)
            
        
        return new_data_dict , new_data_str

    except FileNotFoundError:
        logger.error(f"File not found at {local_file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {local_file_path}: {str(e)}")
        raise
    except boto3.exceptions.Boto3Error as e:
        logger.error(f"Error with AWS operations: {str(e)}")
        raise

# Read Avro schema
avro_schema,avro_schema_str = read_json_file(parse_flag=parse_flag,local_file_path=local_file_path,s3_prefix=s3_prefix, s3_bucket=s3_bucket)





def deserialize_from_avro(avro_bytes, schema):
    """
    Deserialize Avro bytes back into a Python dictionary.
    
    Args:
        avro_bytes: The serialized Avro bytes
        schema: The Avro schema used for serialization
        
    Returns:
        dict: The deserialized data as a Python dictionary
    """
    bytes_reader = io.BytesIO(avro_bytes)
    try:
        return fastavro.schemaless_reader(bytes_reader, schema)
    except Exception as e:
        logger.error(f"Failed to deserialize Avro data: {str(e)}")
        return None


    




class AvroDeserializer(MapFunction):
    def __init__(self, schema):
        self.schema = schema

    def map(self, value):
        try:
            return deserialize_from_avro(value, self.schema)
        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            return None




class BatchFlattenFunction(MapFunction):
    def __init__(self, batch_size=1000):
        self.delimiter = "_"
        self.max_recursion_depth = 100
        self.batch_size = batch_size
        self.current_batch = []

    def flatten_dict(self, data: Any, parent_key: str = '') -> Dict[str, Any]:
        """
        Flatten nested dictionaries while preserving arrays for later processing.
        """
        items = {}
        
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{parent_key}{self.delimiter}{key}" if parent_key else key
                
                if isinstance(value, dict):
                    items.update(self.flatten_dict(value, new_key))
                else:
                    items[new_key] = value
        else:
            items[parent_key] = data
            
        return items

    def is_nested(self, data: Dict[str, Any]) -> bool:
        """
        Check if dictionary contains any nested structures (dicts or lists).
        """
        if not isinstance(data, dict):
            return False
        return any(isinstance(v, (dict, list)) for v in data.values())

    def process_arrays_recursive(self, data: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """
        Recursively flatten nested structures until no nested structures remain.
        Added depth parameter to prevent infinite recursion.
        """
        if depth >= self.max_recursion_depth:
            return data
            
        if not self.is_nested(data):
            return data
            
        flattened = self.flatten_dict(data)
        
        # Check if flattening actually changed anything
        if flattened == data:
            return data
            
        return self.process_arrays_recursive(flattened, depth + 1)

    def process_arrays(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process arrays and create combinations while avoiding infinite recursion.
        """
        try:
            # Initial flattening with depth control
            data = self.process_arrays_recursive(data, 0)
            
            # Separate array and non-array fields
            array_fields = {}
            non_array_fields = {}
            
            for key, value in data.items():
                if isinstance(value, list):
                    if not value:  # Empty array
                        non_array_fields[key] = value
                    else:
                        processed_array = []
                        for item in value:
                            if isinstance(item, dict):
                                flattened_item = self.flatten_dict(item, key)
                                if self.is_nested(flattened_item):
                                    sub_rows = self.process_arrays(flattened_item)
                                    processed_array.extend(sub_rows)
                                else:
                                    processed_array.append(flattened_item)
                            else:
                                processed_array.append({key: item})
                        array_fields[key] = processed_array
                else:
                    non_array_fields[key] = value

            # If no arrays, return the original dict in a list
            if not array_fields:
                return [non_array_fields]

            # Generate combinations
            array_combinations = [array_fields[field] for field in array_fields]
            result_rows = []
            
            for combination in product(*array_combinations):
                new_row = non_array_fields.copy()
                for item in combination:
                    new_row.update(item)
                if self.is_nested(new_row):
                    sub_rows = self.process_arrays(new_row)
                    result_rows.extend(sub_rows)
                else:
                    result_rows.append(new_row)

            return result_rows
            
        except RecursionError:
            # Fallback handling in case of recursion error
            return [self.flatten_dict(data)]

    def stringify_values(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Convert all values in the dictionary to strings.
        """
        return {k: str(v) for k, v in data.items()}

    def process_batch(self, batch):
        """
        Process a batch of records and return flattened dictionaries
        """
        flattened_records = []
        for record in batch:
            if record is None:
                continue
            
            # First flatten the nested structures
            flattened = self.flatten_dict(record)
            
            # Process arrays and create combinations
            result_rows = self.process_arrays(flattened)
            
            # Convert all values to strings and add timestamp
            timestamp = datetime.now().isoformat()
            for row in result_rows:
                stringified_row = self.stringify_values(row)
                stringified_row['timestamp'] = timestamp
                flattened_records.append(stringified_row)
                
        return flattened_records

    def map(self, value: Union[Dict, None]) -> Union[List[Dict[str, str]], None]:
        """
        Map function that implements batch processing
        """
        if value is None:
            return None
            
        self.current_batch.append(value)
        
        # Process batch when it reaches the specified size
        if len(self.current_batch) >= self.batch_size:
            result = self.process_batch(self.current_batch)
            self.current_batch = []  # Reset batch
            return result
            
        return None  # Return None for incomplete batches



class BatchedFlattenedAvroS3SinkFunction(ProcessWindowFunction):
    def __init__(self, bucket_name, prefix,batch_size=1000):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.batch_size = batch_size
 

    def write_batch_to_s3(self, records, schema, batch_id):
        """
        Write a batch of records to S3
        """
        if not records:
            return

        buffer = BytesIO()
        try:
            fastavro.writer(buffer, schema, records)
            file_identifier = datetime.now().strftime("%Y%m%d%H%M%S%f")
            s3_key = f'{self.prefix}flatten_data_batch_{file_identifier}.avro'.strip("()'")
            s3 = boto3.client('s3')
            s3.put_object(
                Bucket=self.bucket_name,
                Key= s3_key,
                Body=buffer.getvalue()
            )
            logger.info(f"Successfully wrote batch {batch_id} with {len(records)} records to S3")
        except Exception as e:
            logger.error(f"Failed to write batch {batch_id} to S3: {str(e)}")

    def process(self, key, context, elements,batch_id):
        s3 = boto3.client('s3')
        batch_timestamp = datetime.now().isoformat()
        records = []
        schemas = []

        for element in elements:
            if element is not None:
                # Handle nested batches from the flatten function
                if isinstance(element, list):
                    for batch in element:
                        # Check if batch is a list (nested batch)
                        if isinstance(batch, list):
                            for record in batch:
                                if isinstance(record, dict):
                                    record['batch_timestamp'] = batch_timestamp
                                    records.append(record)
                                    schemas.append(self.infer_schema(record))
                        # Handle single record
                        elif isinstance(batch, dict):
                            batch['batch_timestamp'] = batch_timestamp
                            records.append(batch)
                            schemas.append(self.infer_schema(batch))
                # Handle single record
                elif isinstance(element, dict):
                    element['batch_timestamp'] = batch_timestamp
                    records.append(element)
                    schemas.append(self.infer_schema(element))

        if not records:
            logger.warning("No valid flattened records to process")
            return

        # Create a union schema that can accommodate all record types
        union_schema = self.create_union_schema(schemas)

        buffer = BytesIO()
        file_identifier = datetime.now().strftime("%Y%m%d%H%M%S%f")

        try:
            fastavro.writer(buffer, union_schema, records)
            file_identifier = datetime.now().strftime("%Y%m%d%H%M%S%f")
            s3_key = f'{self.prefix}flatten_data_batch_{file_identifier}.avro'.strip("()'")
            s3.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=buffer.getvalue()
            )
            logger.info(f"Successfully wrote {len(records)} flattened records to S3")
        except Exception as e:
            logger.error(f"Failed to write flattened data to S3: {str(e)}")

        yield len(records)

    def infer_schema(self, record):
        fields = []
        for key, value in record.items():
            if isinstance(value, list):
                # Handle array type with variable length
                item_type = self.infer_type(value[0]) if value else 'null'
                fields.append({'name': key, 'type': ['null', {'type': 'array', 'items': ['null', item_type]}]})
            else:
                fields.append({'name': key, 'type': ['null', self.infer_type(value)]})
        
        return {'type': 'record', 'name': 'Record', 'fields': fields}

    def infer_type(self, value):
        if isinstance(value, str):
            return 'string'
        elif isinstance(value, int):
            return 'long'  # Using long instead of int for wider range
        elif isinstance(value, float):
            return 'double'  # Using double instead of float for higher precision
        elif isinstance(value, bool):
            return 'boolean'
        elif value is None:
            return 'null'
        else:
            return 'string'  # Default to string for complex types

    def create_union_schema(self, schemas):
        all_fields = set()
        for schema in schemas:
            all_fields.update(field['name'] for field in schema['fields'])
        
        union_fields = []
        for field_name in all_fields:
            field_types = set()
            for schema in schemas:
                field = next((f for f in schema['fields'] if f['name'] == field_name), None)
                if field:
                    if isinstance(field['type'], list):
                        field_types.update(field['type'])
                    else:
                        field_types.add(field['type'])
            
            union_fields.append({
                'name': field_name,
                'type': list(field_types) if len(field_types) > 1 else list(field_types)[0]
            })

        return parse_schema({
            'type': 'record',
            'name': 'UnionRecord',
            'fields': union_fields
        })
    


    def process(self, key, context, elements):
        current_batch = []
        batch_count = 0
        
        for element in elements:
            if element is None:
                continue
                
            # Handle nested batches from the flatten function
            if isinstance(element, list):
                current_batch.extend(element)
            else:
                current_batch.append(element)
                
            # Write batch when it reaches the specified size
            if len(current_batch) >= self.batch_size:
                schema = self.create_union_schema([self.infer_schema(record) for record in current_batch])
                self.write_batch_to_s3(current_batch, schema, batch_count)
                current_batch = []
                batch_count += 1
        
        # Write remaining records
        if current_batch:
            schema = self.create_union_schema([self.infer_schema(record) for record in current_batch])
            self.write_batch_to_s3(current_batch, schema, batch_count)
            
        yield batch_count + 1


from pyflink.datastream import ProcessWindowFunction
from io import BytesIO
import boto3
import fastavro
from datetime import datetime
import logging
from botocore.config import Config

logger = logging.getLogger(__name__)

class RawAvroS3SinkFunction(ProcessWindowFunction):
    def __init__(self,bucket_name, prefix,batch_size=1000, max_retries=3):
        self.bucket_name = str(bucket_name).strip("()'")
        self.prefix = str(prefix).strip("()'")
        if not self.prefix.endswith('/'):
            self.prefix += '/'
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.batch_count = 0


    def write_batch_to_s3(self, records,avro_schema,batch_id):
        """
        Write a batch of records to S3 with retry logic
        """
        if not records:
            return

        buffer = BytesIO()
        file_identifier = datetime.now().strftime("%Y%m%d%H%M%S%f")
        s3_key = f'{self.prefix}raw_data_batch_{file_identifier}.avro'.strip("()'")
    

        try:
            fastavro.writer(buffer, avro_schema, records)
            s3 = boto3.client('s3')
            s3.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=buffer.getvalue()
            )
            logger.info(f"Successfully wrote batch {batch_id} with {len(records)} records to S3")
        except Exception as e:
            logger.error(f"Failed to write batch {batch_id} to S3: {str(e)}")
            raise

    def process(self, key, context, elements):
        batch_timestamp = datetime.now().isoformat()
        records = []
        total_records = 0
        buffer = BytesIO()
        s3 = boto3.client('s3')

        try:
            # Process all elements
            for element in elements:
                if element is not None:
                    records.append(element)
                    
                    # When batch size is reached, write to S3
                    if len(records) >= self.batch_size:
                        if not records:
                            continue

                        schema = fastavro.parse_schema(avro_schema)
                        fastavro.writer(buffer, schema, records)
                        batch_id = f"{batch_timestamp}_{self.batch_count}"
                        self.write_batch_to_s3(records, schema, batch_id)
                        
                        total_records += len(records)
                        records = []  # Clear the batch
                        self.batch_count += 1

            # Write any remaining records
            if records:
                schema = fastavro.parse_schema(avro_schema)
                fastavro.writer(buffer, schema, records)
                batch_id = f"{batch_timestamp}_{self.batch_count}"
                self.write_batch_to_s3(records, schema, batch_id)
                total_records += len(records)
                self.batch_count += 1

            if total_records == 0:
                logger.warning("No valid raw records to process")
                return

            logger.info(f"Successfully processed total of {total_records} records in {self.batch_count} batches")
            yield total_records

        except Exception as e:
            logger.error(f"Error in process method: {str(e)}")
            raise

    # def close(self):
    #     """
    #     Cleanup method to write any remaining records when the window closes
    #     """
    #     try:
    #         if hasattr(self, 'current_batch') and self.current_batch:
    #             schema = fastavro.parse_schema(avro_schema)
    #             batch_id = f"{datetime.now().isoformat()}_{self.batch_count}"
    #             self.write_batch_to_s3(self.current_batch, schema, batch_id)
    #             self.current_batch = []
    #             self.batch_count += 1
    #     except Exception as e:
    #         logger.error(f"Error in close method: {str(e)}")
    #         raise



def print_stream_type(stream, stream_name):
    type_info = stream.get_type()
    print(f"Type of {stream_name}: {type_info}")



def main():


# Create a Configuration object
    config = Configuration()

    # Create the StreamExecutionEnvironment
    env = StreamExecutionEnvironment.get_execution_environment(config)
    env.add_jars(CONFIG['jar_path']['flink_kafka_connector_jar'])

    # Set up checkpointing
    checkpoint_dir = CONFIG['checkpoint']['dir']
    os.makedirs(checkpoint_dir.replace('file://', ''), exist_ok=True)

    # Enable checkpointing
    env.enable_checkpointing(CONFIG['checkpoint']['interval'])
    
    checkpoint_config = env.get_checkpoint_config()
    checkpoint_config.set_checkpointing_mode(CheckpointingMode.EXACTLY_ONCE)
    checkpoint_config.set_min_pause_between_checkpoints(30000)
    checkpoint_config.set_checkpoint_timeout(300000)
    checkpoint_config.set_max_concurrent_checkpoints(1)
    
    checkpoint_storage = FileSystemCheckpointStorage(checkpoint_dir)
    checkpoint_config.set_checkpoint_storage(checkpoint_storage)

    # Kafka consumer configuration
    kafka_props = {
        'bootstrap.servers': CONFIG['kafka']['bootstrap_servers'],
        'group.id': CONFIG['kafka']['group_id'],
        'auto.offset.reset': CONFIG['kafka']['auto_offset_reset'],
        'enable.auto.commit': 'false',
        'max.poll.records': str(5),
        'max.request.size': '2097152',  # 2MB
        'message.max.bytes': '2097152'
    }

    kafka_consumer = FlinkKafkaConsumer(
        topics=CONFIG['kafka']['topic'],
        deserialization_schema=SimpleStringSchema(),
        properties=kafka_props
    )



    # Create the data stream from Kafka
    stream = env.add_source(kafka_consumer)

    deserialized_stream = stream \
        .map(lambda x: bytearray(x.encode('utf-8')), output_type=Types.PRIMITIVE_ARRAY(Types.BYTE())) \
        .map(AvroDeserializer(avro_schema)) \
        .filter(lambda x: x is not None)
    
    deserialized_stream \
        .key_by(lambda x: 1) \
        .window(TumblingProcessingTimeWindows.of(CONFIG['window']['size'])) \
        .process(RawAvroS3SinkFunction
        (
            bucket_name=CONFIG['s3']['bucket_name'],
            prefix=CONFIG['s3']['raw_prefix'],
            batch_size=8000
        ))


    # Use batch processing for flattening
    flattened_stream = deserialized_stream.map(BatchFlattenFunction(batch_size=1000))

    # # flattened_stream.print()


    # # Process batches with windowing
    flattened_stream \
        .key_by(lambda x: 1) \
        .window(TumblingProcessingTimeWindows.of(CONFIG['window']['size'])) \
        .process(BatchedFlattenedAvroS3SinkFunction(
            CONFIG['s3']['bucket_name'], 
            CONFIG['s3']['flattened_prefix'],
            batch_size=1000
        ))
    
    


    # Write raw data to S3
    #raw_stream.map(lambda x: raw_writer.write_to_s3(x, 'raw'))

    # Execute the job
    try:
        job_result = env.execute("Avro Deserialization and Dual S3 Sink Job")
        
        # Log job results
        logger.info(f"Job executed successfully. Job ID: {job_result.get_job_id()}")
        logger.info(f"Job runtime: {job_result.get_net_runtime()} ms")
        
    except Exception as e:
        logger.error(f"Job execution failed: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        # Initialize any required resources
        
        # Run the main job
        main()
        
    except Exception as e:
        logger.error(f"Application failed: {str(e)}")
        sys.exit(1)
    finally:
        # Cleanup resources if needed
        pass
