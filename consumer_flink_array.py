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
        'group_id': 'banking-transaction-group-new-1211121-new-0980-09-009-00',
        'auto_offset_reset': 'earliest',
        'topic': 'Event-Mesh-topic-11111-21st-jan'
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


    
# def deserialize_from_avro(avro_bytes, schema):
#     """
#     Deserialize Avro bytes back into a Python dictionary.
    
#     Args:
#         avro_bytes: The serialized Avro bytes
#         schema: The Avro schema used for serialization
        
#     Returns:
#         dict: The deserialized data as a Python dictionary
#     """
#     bytes_reader = io.BytesIO(avro_bytes)
#     try:
#         return fastavro.schemaless_reader(bytes_reader, schema)
#     except fastavro.schema.SchemaParseException as e:
#         logger.error(f"Schema parsing error: {str(e)}")
#     except fastavro.read.ReadError as e:
#         logger.error(f"Avro read error: {str(e)}")
#     except ValueError as e:
#         logger.error(f"Value error during deserialization: {str(e)}")
#     except Exception as e:
#         logger.error(f"Unexpected error during deserialization: {str(e)}")
#     return None



class AvroDeserializer(MapFunction):
    def __init__(self, schema):
        self.schema = schema

    def map(self, value):
        try:
            return deserialize_from_avro(value, self.schema)
        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            return None
        

        
from datetime import datetime
from typing import List, Dict, Any
import itertools

class FlattenFunction(MapFunction):
    def __init__(self, batch_size: int = 1000):
        self.delimiter = "_"
        self.batch_size = batch_size

    def explode_arrays(self, data: Dict[str, Any], parent_key: str = '') -> List[Dict[str, Any]]:
        """
        Explode arrays in the data structure and return a list of dictionaries.
        
        Args:
            data: The input dictionary containing possible arrays
            parent_key: The parent key for nested elements
            
        Returns:
            List of dictionaries with exploded arrays
        """
        result = [{}]
        
        for key, value in data.items():
            current_key = f"{parent_key}{self.delimiter}{key}" if parent_key else key
            
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                nested_results = self.explode_arrays(value, current_key)
                result = [
                    {**existing, **new} 
                    for existing, new in itertools.product(result, nested_results)
                ]
                
            elif isinstance(value, list):
                if not value:  # Empty array
                    for d in result:
                        d[current_key] = None
                else:
                    temp_result = []
                    for item in value:
                        if isinstance(item, (dict, list)):
                            # Handle nested structures within arrays
                            nested_results = self.explode_arrays({f"item": item}, current_key)
                            temp_result.extend([
                                {**existing, **new}
                                for existing in result
                                for new in nested_results
                            ])
                        else:
                            # Handle primitive values in arrays
                            temp_result.extend([
                                {**existing, current_key: str(item)}
                                for existing in result
                            ])
                    result = temp_result
                    
            else:
                # Handle non-array values
                for d in result:
                    d[current_key] = str(value)
                    
        return result

    def batch_results(self, results: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Split results into batches.
        
        Args:
            results: List of flattened dictionaries
            
        Returns:
            List of batches of dictionaries
        """
        return [
            results[i:i + self.batch_size] 
            for i in range(0, len(results), self.batch_size)
        ]

    def map(self, value):
        if value is None:
            return None
            
        # Explode arrays and flatten the structure
        exploded_results = self.explode_arrays(value)
        
        # Add timestamp to each record
        current_timestamp = datetime.now().isoformat()
        for result in exploded_results:
            result['timestamp'] = current_timestamp
            
        # Batch the results
        return self.batch_results(exploded_results)



class FlattenedAvroS3SinkFunction(ProcessWindowFunction):
    def __init__(self, bucket_name, prefix):
        self.bucket_name = bucket_name
        self.prefix = prefix

    def process(self, key, context, elements):
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
            s3.put_object(
                Bucket=self.bucket_name,
                Key=f'{self.prefix}flattened_data_{file_identifier}.avro',
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



class RawAvroS3SinkFunction(ProcessWindowFunction):
    def __init__(self, bucket_name, prefix):
        self.bucket_name = bucket_name
        self.prefix = prefix

    def process(self, key, context, elements):
        s3 = boto3.client('s3')
        buffer = BytesIO()
        
        batch_timestamp = datetime.now().isoformat()
        records = []
        for element in elements:
            if element is not None:
                records.append(element)

        if not records:
            logger.warning("No valid raw records to process")
            return

        schema = fastavro.parse_schema(avro_schema)
        #schema = infer_schema(records[0])
        fastavro.writer(buffer, schema, records)
        file_identifier = datetime.now().strftime("%Y%m%d%H%M%S%f")
        
        try:
            s3.put_object(
                Bucket=self.bucket_name,
                Key=f'{self.prefix}raw_data_{file_identifier}.avro',
                Body=buffer.getvalue()
            )
            logger.info(f"Successfully wrote {len(records)} raw records to S3")
        except Exception as e:
            logger.error(f"Failed to write raw data to S3: {str(e)}")
        
        yield len(records)



def print_stream_type(stream, stream_name):
    type_info = stream.get_type()
    print(f"Type of {stream_name}: {type_info}")


class NewAvroDeserializer(MapFunction):
    def __init__(self, schema):
        self.schema = schema

    def map(self, value):
        try:
            logger.info(f"Received value: {value[:20]}...")  # Log the first 20 bytes
            
            # Ensure value is bytes
            if isinstance(value, bytearray):
                value = bytes(value)
            elif isinstance(value, str):
                value = value.encode('utf-8')
            
            # Deserialize Avro bytes
            bytes_reader = io.BytesIO(value)
            deserialized_data = fastavro.schemaless_reader(bytes_reader, self.schema)
            logger.info(f"Deserialized data: {deserialized_data}")
            return json.dumps(deserialized_data)
        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            return None
        


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
        'auto.offset.reset': CONFIG['kafka']['auto_offset_reset']
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
    
    # print_stream_type(deserialized_stream,"Kafka Source Stream")
    
    # deserialized_stream.print()
    

    deserialized_stream \
        .key_by(lambda x: 1) \
        .window(TumblingProcessingTimeWindows.of(CONFIG['window']['size'])) \
        .process(RawAvroS3SinkFunction(CONFIG['s3']['bucket_name'], CONFIG['s3']['raw_prefix']))



    # # Process and sink for flattened data
    flattened_stream = deserialized_stream.map(FlattenFunction())
    # print_stream_type(flattened_stream,"Kafka Source Stream")
    # flattened_stream.print()


    flattened_stream \
        .key_by(lambda x: 1) \
        .window(TumblingProcessingTimeWindows.of(CONFIG['window']['size'])) \
        .process(FlattenedAvroS3SinkFunction(CONFIG['s3']['bucket_name'], CONFIG['s3']['flattened_prefix']))

    # Execute the job
    try:
        env.execute("Avro Deserialization and Dual New S3 Sink Job")
    except Exception as e:
        logger.error(f"Job execution failed: {str(e)}")

if __name__ == "__main__":
    main()









class FlattenFunction(MapFunction):
    def __init__(self, batch_size: int = 1000):
        self.delimiter = "_"
        self.batch_size = batch_size

    def flatten_and_explode(self, data: Any, parent_key: str = '') -> List[Dict[str, str]]:
        """
        Recursively flatten and explode nested structures.
        
        Args:
            data: The input data (dict, list, or primitive)
            parent_key: The parent key for nested elements
            
        Returns:
            List of flattened dictionaries
        """
        if data is None:
            return [{}]

        if isinstance(data, dict):
            return self.flatten_dict(data, parent_key)
        elif isinstance(data, list):
            return self.flatten_list(data, parent_key)
        else:
            return [{parent_key: str(data)}] if parent_key else [{}]

    def flatten_dict(self, data: Dict, parent_key: str = '') -> List[Dict[str, str]]:
        """
        Flatten a dictionary and its nested structures.
        """
        results = [{}]
        
        for key, value in data.items():
            current_key = f"{parent_key}{self.delimiter}{key}" if parent_key else key
            
            if isinstance(value, dict):
                nested_results = self.flatten_and_explode(value, current_key)
                results = [
                    {**existing, **new}
                    for existing in results
                    for new in nested_results
                ]
            elif isinstance(value, list):
                nested_results = self.flatten_list(value, current_key)
                if nested_results:
                    results = [
                        {**existing, **new}
                        for existing in results
                        for new in nested_results
                    ]
                else:
                    for d in results:
                        d[current_key] = None
            else:
                for d in results:
                    d[current_key] = str(value)
                    
        return results

    def flatten_list(self, data: List, parent_key: str) -> List[Dict[str, str]]:
        """
        Flatten a list and its nested structures.
        """
        if not data:
            return [{}]
            
        results = []
        for i, item in enumerate(data):
            if isinstance(item, dict):
                # For nested objects in array
                nested_results = self.flatten_dict(item, f"{parent_key}")
                results.extend(nested_results)
            elif isinstance(item, list):
                # For nested arrays
                nested_results = self.flatten_list(item, f"{parent_key}")
                results.extend(nested_results)
            else:
                # For primitive values
                results.append({parent_key: str(item)})
                
        return results

    def batch_results(self, results: List[Dict[str, str]]) -> List[List[Dict[str, str]]]:
        """
        Split results into batches.
        """
        return [
            results[i:i + self.batch_size] 
            for i in range(0, len(results), self.batch_size)
        ]

    def map(self, value):
        if value is None:
            return None
            
        # Flatten and explode the structure
        flattened_results = self.flatten_and_explode(value)
        
        # Add timestamp to each record
        current_timestamp = datetime.now().isoformat()
        for result in flattened_results:
            result['timestamp'] = current_timestamp
            
        # Batch the results
        return self.batch_results(flattened_results)









=============


class FlattenFunction(MapFunction):
    def __init__(self, batch_size: int = 1000):
        self.delimiter = "_"
        self.batch_size = batch_size

    def is_nested(self, value: Any) -> bool:
        """Check if a value contains nested structures."""
        return isinstance(value, (dict, list))

    def has_nested_structures(self, data: Dict[str, Any]) -> bool:
        """Check if dictionary contains any nested structures."""
        return any(self.is_nested(value) for value in data.values())

    def flatten_one_level(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten one level of nesting in the dictionary.
        
        Args:
            data: Dictionary that may contain nested structures
            
        Returns:
            Partially flattened dictionary
        """
        flattened = {}

        for key, value in data.items():
            if isinstance(value, dict):
                # Flatten one level of dictionary
                for sub_key, sub_value in value.items():
                    new_key = f"{key}{self.delimiter}{sub_key}"
                    flattened[new_key] = sub_value
            elif isinstance(value, list):
                # Handle arrays
                if value and all(isinstance(item, dict) for item in value):
                    # List of dictionaries - flatten each dict in the list
                    for item in value:
                        for sub_key, sub_value in item.items():
                            new_key = f"{key}{self.delimiter}{sub_key}"
                            if new_key in flattened:
                                # If key exists, append as comma-separated value
                                if isinstance(flattened[new_key], list):
                                    flattened[new_key].append(sub_value)
                                else:
                                    flattened[new_key] = [flattened[new_key], sub_value]
                            else:
                                flattened[new_key] = sub_value
                else:
                    # List of primitive values or mixed content
                    flattened[key] = value
            else:
                # Keep non-nested values as is
                flattened[key] = value

        return flattened

    def flatten_completely(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Iteratively flatten all nested structures until no nesting remains.
        
        Args:
            data: Dictionary with nested structures
            
        Returns:
            Completely flattened dictionary
        """
        flattened = dict(data)
        iteration = 0
        max_iterations = 100  # Safety limit to prevent infinite loops

        while self.has_nested_structures(flattened) and iteration < max_iterations:
            flattened = self.flatten_one_level(flattened)
            iteration += 1

        # Convert all values to strings and handle any remaining lists
        final_result = {}
        for key, value in flattened.items():
            if isinstance(value, list):
                # Convert list to comma-separated string
                final_result[key] = ','.join(str(item) for item in value)
            else:
                final_result[key] = str(value)

        return final_result

    def explode_arrays(self, flattened_dict: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Explode any comma-separated values into separate records.
        
        Args:
            flattened_dict: Dictionary with flattened structure
            
        Returns:
            List of dictionaries with exploded arrays
        """
        # Find keys with comma-separated values
        array_keys = {k: v.split(',') for k, v in flattened_dict.items() 
                     if isinstance(v, str) and ',' in v}
        
        if not array_keys:
            return [flattened_dict]

        # Generate all combinations of array values
        keys = list(array_keys.keys())
        value_combinations = itertools.product(*[array_keys[k] for k in keys])
        
        # Create new records for each combination
        result = []
        non_array_items = {k: v for k, v in flattened_dict.items() if k not in array_keys}
        
        for values in value_combinations:
            new_dict = non_array_items.copy()
            for k, v in zip(keys, values):
                new_dict[k] = v
            result.append(new_dict)
            
        return result

    def batch_results(self, results: List[Dict[str, str]]) -> List[List[Dict[str, str]]]:
        """Split results into batches."""
        return [
            results[i:i + self.batch_size] 
            for i in range(0, len(results), self.batch_size)
        ]

    def map(self, value):
        if value is None:
            return None

        try:
            # First, completely flatten the structure
            flattened = self.flatten_completely(value)
            
            # Then explode any remaining arrays (comma-separated values)
            exploded_results = self.explode_arrays(flattened)
            
            # Add timestamp to each record
            current_timestamp = datetime.now().isoformat()
            for result in exploded_results:
                result['timestamp'] = current_timestamp
            
            # Batch the results
            return self.batch_results(exploded_results)
            
        except Exception as e:
            logger.error(f"Error in flattening: {str(e)}")
            return None

