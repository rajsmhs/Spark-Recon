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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

parse_flag=False
local_file_path='/Users/vrajabhi/Documents/flink-ecommerse/Schema_Folder/transaction_schema.json'
#local_file_path=None
# s3_prefix='schema_dir/transaction_schema.json'
# s3_bucket='aws-glue-assets-767397672884-us-east-1'
s3_prefix=None
s3_bucket=None

# Configuration
CONFIG = { 
    'kafka': {
        'bootstrap_servers': 'localhost:9092',
        'group_id': 'banking-transaction-group-new-1211121-new',
        'auto_offset_reset': 'earliest',
        'topic': 'banking-transaction-topic-11111'
    },
    's3': {
        'bucket_name': 'aws-glue-assets-767397672884-us-east-1',
        'raw_prefix': 'bank_transaction_raw_avro/',
        'flattened_prefix': 'bank_transaction_flatten_avro/'
    },
    'checkpoint': {
        'interval': 60000,
        'dir': 'file:///Users/vrajabhi/Documents/flink-ecommerse/bank_transaction_cp'
    },
    'window': {
        'size': Time.minutes(2)
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

    def flatten_dict(self,data, parent_key=''):
        """
        Flatten a nested dictionary/list structure into a single level dictionary.
        
        Args:
            data: The nested dictionary/list to flatten
            parent_key: The parent key for nested elements (used in recursion)
            sep: Separator for nested keys
        
        Returns:
            A flattened dictionary with compound keys
        """
        items = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{parent_key}{self.delimiter}{key}" if parent_key else key
                
                if isinstance(value, (dict, list)):
                    items.extend(self.flatten_dict(value, new_key).items())
                else:
                    items.append((new_key, str(value)))  # Convert all values to strings
                    
        elif isinstance(data, list):
            for i, value in enumerate(data):
                new_key = f"{parent_key}{self.delimiter}{i}"
                
                if isinstance(value, (dict, list)):
                    items.extend(self.flatten_dict(value, new_key).items())
                else:
                    items.append((new_key, str(value)))  # Convert all values to strings
        else:
            items.append((parent_key, str(data)))  # Convert all values to strings
            
        return dict(items)

    def map(self, value):
        if value is None:
            return None
        flattened = self.flatten_dict(value)
        flattened['timestamp'] = datetime.now().isoformat()
        return flattened



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
    
    print_stream_type(deserialized_stream,"Kafka Source Stream")
    
    # deserialized_stream.print()
    

    deserialized_stream \
        .key_by(lambda x: 1) \
        .window(TumblingProcessingTimeWindows.of(CONFIG['window']['size'])) \
        .process(RawAvroS3SinkFunction(CONFIG['s3']['bucket_name'], CONFIG['s3']['raw_prefix']))



    # # Process and sink for flattened data
    flattened_stream = deserialized_stream.map(FlattenFunction())
    # flattened_stream.print()
    #print_stream_type(deserialized_stream,"Kafka Source Stream")

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
