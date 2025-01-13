from confluent_kafka import Producer
from confluent_kafka.serialization import StringSerializer
import fastavro
import io
import json
import uuid
import time
import random
import os
import boto3
from botocore.exceptions import ClientError
import io
from faker import Faker
import logging
from datetime import datetime, timedelta
import string

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


parse_flag=False
local_file_path='/Users/vrajabhi/Documents/flink-ecommerse/Schema_Folder/transaction_schema.json'
# s3_prefix='schema_dir/transaction_schema.json'
# s3_bucket='aws-glue-assets-767397672884-us-east-1'
s3_prefix=None
s3_bucket=None
KAFKA_CONFIG = {'bootstrap.servers': 'localhost:9092','client.id': 'avro-order-data-1-new-1'}
#Kafka topic
TOPIC = 'banking-transaction-topic-11111'
#Batch size limit (2 MB)clea
MAX_BATCH_SIZE = 2 * 1024 * 1024
#Checkpointing configuration
CHECKPOINT_FILE = 'bank_transaction_checkpoint.json'


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


def generate_sample_data():
    fake = Faker()
    # return {
    #     "header": {
    #         "eventUUID": str(uuid.uuid4()),
    #         "subject": {
    #             "subjectType": "CONTACT_PERSON",
    #             "subjectId": str(uuid.uuid4())
    #         },
    #         "occurrenceDateTime": int(time.time() * 1000),
    #         "traceId": str(uuid.uuid4()),
    #         "spanId": str(uuid.uuid4()),
    #         "source": "SAMPLE_SOURCE",
    #         "hierarchy": "SAMPLE_HIERARCHY"
    #     },
    #     "contactPerson": {
    #         "globalID": str(uuid.uuid4()),
    #         "eventType": "CREATE",
    #         "firstName": random.choice(["John", "Jane", "Alice", "Bob"]),
    #         "lastName": random.choice(["Doe", "Smith", "Johnson", "Brown"]),
    #         "middleInitials": random.choice(["A", "B", "C", "D", None]),
    #         "title": random.choice(["Mr.", "Mrs.", "Ms.", "Dr.", None]),
    #         "honorificTitle": random.choice(["PhD", "MBA", None]),
    #         "language": random.choice(["English", "Spanish", "French", None]),
    #         "position": random.choice(["Manager", "Director", "Analyst", None]),
    #         "notes": "Sample notes for contact person",
    #         "communications": {
    #         "email": [
    #             {
    #                 "description": random.choice(["Work", "Personal"]),
    #                 "address": fake.email()
    #             } for _ in range(random.randint(1, 2))
    #         ],
    #         "phoneNumber": [
    #             {
    #                 "description": random.choice(["Mobile", "Office", "Home"]),
    #                 "country": fake.country_code(),
    #                 "number": fake.phone_number(),
    #                 "extension": str(random.randint(100, 999))
    #             } for _ in range(random.randint(1, 2))
    #         ],
    #         "website": [
    #             {
    #                 "description": random.choice(["Company", "Personal"]),
    #                 "address": fake.url()
    #             } for _ in range(random.randint(1, 2))
    #         ]
    #         }
    #     }
    # }

    # return {
    #         "orderId": "ORD-12345",
    #         "customerId": "CUST-6789",
    #         "orderDate": 1704844800000,
    #         "shippingAddress": {
    #             "street": "123 Main St",
    #             "city": "Springfield",
    #             "state": "IL",
    #             "zipCode": "62701"
    #         },
    #         "items": [
    #             {
    #             "productId": "PROD-001",
    #             "productName": "Smartphone X",
    #             "quantity": 1,
    #             "unitPrice": "799.99"
    #             },
    #             {
    #             "productId": "PROD-002",
    #             "productName": "Wireless Earbuds",
    #             "quantity": 2,
    #             "unitPrice": "129.99"
    #             }
    #         ],
    #         "totalAmount": "1059.97",
    #         "paymentInfo": {
    #             "paymentMethod": "CREDIT_CARD",
    #             "transactionId": "TXN-98765"
    #         },
    #         "status": "PROCESSING"
    #         }

    return {
            "account_number": str(uuid.uuid4()),
            "account_type": random.choice(["CHECKING", "SAVINGS", "MONEY_MARKET", "CERTIFICATE_OF_DEPOSIT"]),
            "customer": {
                "customer_id": "CUST-"+str(uuid.uuid4()),
                "first_name": random.choice(["John", "Jane", "Alice", "Bob"]),
                "last_name": random.choice(["Doe", "Smith", "Johnson", "Brown"]),
                "date_of_birth": "1985-07-15",
                "ssn": str(random.randint(100, 999))+"-"+str(random.randint(200, 599))+"-"+str(random.randint(900, 999)),
                "contact": {
                "email": fake.email(),
                "phone": fake.phone_number(),
                "address": {
                    "street": fake.url(),
                    "city": "Metropolis",
                    "state": "NY",
                    "zip": "10001",
                    "country": fake.country_code()
                }
                }
            },
            "balance": "5432.10",
            "currency": "USD",
            "open_date": int(time.time() * 1000),
            "last_activity_date": int(time.time() * 1000),
            "status": random.choice(["ACTIVE", "INACTIVE", "FROZEN", "CLOSED"]),
            "transactions": [
                {
                "transaction_id": "TRX-"+str(uuid.uuid4()),
                "date": int(time.time() * 1000),
                "type": "DEPOSIT",
                "amount": "1000.00",
                "description": "Payroll deposit",
                "balance_after": "5432.10"
                },
                {
                "transaction_id": "TRX-"+str(uuid.uuid4()),
                "date": int(time.time() * 1000),
                "type": "WITHDRAWAL",
                "amount": "200.00",
                "description": "ATM withdrawal",
                "balance_after": "5232.10"
                }
            ],
            "interest_rate": "0.01",
            "overdraft_limit": "500.00",
            "linked_accounts": ["9876543210", "5678901234"],
            "tags": ["preferred customer", "paperless", "mobile banking"]
            }










def serialize_to_avro(data, schema):
    bytes_writer = io.BytesIO()
    fastavro.schemaless_writer(bytes_writer, schema, data)
    return bytes_writer.getvalue()



def delivery_report(err, msg):
    if err is not None:
        print(f'Message delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}')

def send_batch_to_kafka(producer, topic, batch):
    for avro_bytes in batch:
        producer.produce(
            topic,
            value=avro_bytes
            #on_delivery=delivery_report
        )
    producer.flush()


def save_checkpoint(last_processed_id,CHECKPOINT_FILE):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({'last_processed_id': last_processed_id}, f)


def load_checkpoint(CHECKPOINT_FILE):
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)['last_processed_id']
    return 0




# s3_bucket = 'aws-glue-assets-767397672884-us-east-1'
# s3_prefix = 'order_schema.json'
# avro_schema = read_json_file(local_file_path=None,s3_prefix=s3_prefix, s3_bucket=s3_bucket)
# parsed_schema = fastavro.parse_schema(avro_schema)
# ample_order = generate_order_data()
# sample_order = calculate_total(sample_order)
# print(sample_order)
# print("##################################################")
# avro_bytes = serialize_to_avro(sample_order, parsed_schema)
# print(avro_bytes)
# print("##################Avro Bytes#########################")
# bytes_reader = io.BytesIO(avro_bytes)
# aa=fastavro.schemaless_reader(bytes_reader, avro_schema)
# print("###################Deserialsise######################")
# print(aa)




def main():
    avro_schema,avro_schema_str = read_json_file(parse_flag=parse_flag,local_file_path=local_file_path,s3_prefix=s3_prefix, s3_bucket=s3_bucket)

    producer = Producer(KAFKA_CONFIG)
    parsed_schema = fastavro.parse_schema(avro_schema)
        
    batch = []
    batch_size = 0
    last_processed_id = load_checkpoint(CHECKPOINT_FILE)
    
    for i in range(last_processed_id + 1, 900000):  # Assuming a large number of records
        sample_order = generate_sample_data()
        avro_bytes = serialize_to_avro(sample_order, parsed_schema)

        if batch_size + len(avro_bytes) > MAX_BATCH_SIZE:
            send_batch_to_kafka(producer, TOPIC, batch)
            save_checkpoint(i - 1,CHECKPOINT_FILE)
            print("Messages processed in the if loop")
            print("Batch size:",batch_size)
            print(f"Sent batch. Last processed ID: {i - 1}")
            batch = []
            batch_size = 0
            time.sleep(2)
        
        batch.append(avro_bytes)
        batch_size += len(avro_bytes)
        
        # Optional: Add a small delay between record generation
        #time.sleep(1)
    
    # Send any remaining data in the batch
    if batch:
        send_batch_to_kafka(producer, TOPIC, batch)
        save_checkpoint(i,CHECKPOINT_FILE)
        print(f"Sent final batch. Last processed ID: {i}")
    
    print("Finished sending messages.")

if __name__ == "__main__":
    main()




