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
        

        
class FlattenFunction(MapFunction):
    def __init__(self):
        self.delimiter = "_"
        self.max_recursion_depth = 100  # Add recursion depth limit
        
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

    def map(self, value: Union[Dict, None]) -> Union[List[Dict[str, str]], None]:
        """
        Map function to flatten the input value and create multiple rows for arrays.
        """
        if value is None:
            return None
            
        # First flatten the nested structures
        flattened = self.flatten_dict(value)
        
        # Process arrays and create combinations with recursive flattening
        result_rows = self.process_arrays(flattened)
        
        # Convert all values to strings and add timestamp
        timestamp = datetime.now().isoformat()
        final_rows = []
        for row in result_rows:
            stringified_row = self.stringify_values(row)
            stringified_row['timestamp'] = timestamp
            final_rows.append(stringified_row)
            
        return final_rows



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



















def __init__(self, batch_size=100, batch_interval=60):
        self.delimiter = "_"
        self.max_recursion_depth = 100
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.current_batch = []
        self.last_batch_time = time.time()
        
    # ... [keep all other methods as they are] ...

    def process_batch(self):
        # Process the current batch (e.g., send to Kafka)
        print(f"Processing batch of {len(self.current_batch)} items")
        # Here you would typically send the batch to Kafka or perform other processing
        self.current_batch = []
        self.last_batch_time = time.time()

    def add_to_batch(self, item):
        self.current_batch.append(item)
        if len(self.current_batch) >= self.batch_size or (time.time() - self.last_batch_time) >= self.batch_interval:
            self.process_batch()

    def map(self, value: Union[Dict, None]) -> None:
        """
        Map function to flatten the input value, create multiple rows for arrays,
        and add to the current batch.
        """
        if value is None:
            return
            
        # First flatten the nested structures
        flattened = self.flatten_dict(value)
        
        # Process arrays and create combinations with recursive flattening
        result_rows = self.process_arrays(flattened)
        
        # Convert all values to strings and add timestamp
        timestamp = datetime.now().isoformat()
        for row in result_rows:
            stringified_row = self.stringify_values(row)
            stringified_row['timestamp'] = timestamp
            self.add_to_batch(stringified_row)

    def close(self):
        """
        Process any remaining items in the batch when closing the function.
        """
        if self.current_batch:
            self.process_batch()











import boto3

def get_contract_lists_from_s3(bucket_name, prefix):
    s3_client = boto3.client('s3')
    source_contracts = []
    consumer_contracts = []
    
    # List objects in the bucket with the given prefix
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    
    for obj in response.get('Contents', []):
        file_name = obj['Key'].split('/')[-1]  # Get just the filename
        parts = file_name.split('-')
        
        if 'source' in file_name:
            source_contracts.append(parts[1])
        elif 'consumer' in file_name:
            consumer_contracts.append(parts[1])
            
    return source_contracts, consumer_contracts

# Example usage:
bucket_name = 'adap-apse2-tbi-metadata-dev'
prefix = 'data-contract'

source_list, consumer_list = get_contract_lists_from_s3(bucket_name, prefix)
print("Source contracts:", source_list)
print("Consumer contracts:", consumer_list)
