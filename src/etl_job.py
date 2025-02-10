import boto3
import pandas as pd
import psycopg2
from io import StringIO
import os

def get_s3_data(bucket_name, file_key):
    """Read data from S3 bucket"""
    s3_client = boto3.client('s3')
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        # Simple CSV read as our test file is basic
        data = pd.read_csv(StringIO(response['Body'].read().decode('utf-8')))
        return data
    except Exception as e:
        print(f"Error reading from S3: {str(e)}")
        return None

def write_to_rds(data, db_params):
    """Write data to RDS PostgreSQL"""
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # Create table matching our test_data.csv structure
        create_table_query = """
        CREATE TABLE IF NOT EXISTS data_table (
            id SERIAL PRIMARY KEY,
            column1 VARCHAR(100),
            column2 VARCHAR(100)
        )
        """
        cursor.execute(create_table_query)

        # Insert data using our CSV column names
        for _, row in data.iterrows():
            insert_query = "INSERT INTO data_table (column1, column2) VALUES (%s, %s)"
            cursor.execute(insert_query, (row['column1'], row['column2']))

        conn.commit()
        return True
    except Exception as e:
        print(f"Error writing to RDS: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def write_to_glue_catalog(data, database_name, table_name):
    """Write data to AWS Glue Data Catalog"""
    try:
        glue_client = boto3.client('glue')

        # Convert DataFrame to Parquet and save to S3
        bucket = os.environ['GLUE_BUCKET']
        key = f"data/{table_name}.parquet"

        parquet_buffer = StringIO()
        data.to_parquet(parquet_buffer)

        s3_client = boto3.client('s3')
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=parquet_buffer.getvalue()
        )

        # Create or update Glue table with our test data structure
        glue_client.create_table(
            DatabaseName=database_name,
            TableInput={
                'Name': table_name,
                'StorageDescriptor': {
                    'Columns': [
                        # Columns matching our test_data.csv
                        {'Name': 'column1', 'Type': 'string'},
                        {'Name': 'column2', 'Type': 'string'}
                    ],
                    'Location': f's3://{bucket}/{key}',
                    'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
                    'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
                    'SerdeInfo': {
                        'SerializationLibrary': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
                    }
                }
            }
        )
        return True
    except Exception as e:
        print(f"Error writing to Glue: {str(e)}")
        return False

def lambda_handler(event, context):
    """AWS Lambda handler function"""
    try:
        # Get environment variables
        bucket_name = os.environ['SOURCE_BUCKET']
        file_key = os.environ['SOURCE_KEY']
        database_name = os.environ['DATABASE_NAME']
        table_name = os.environ['TABLE_NAME']

        # Read data from S3
        data = get_s3_data(bucket_name, file_key)
        if data is None:
            return {
                'statusCode': 500,
                'body': 'Failed to read data from S3'
            }

        # Try to write to RDS first
        db_params = {
            'host': os.environ['DB_HOST'],
            'database': os.environ['DB_NAME'],
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASSWORD']
        }

        if write_to_rds(data, db_params):
            return {
                'statusCode': 200,
                'body': 'Successfully wrote data to RDS'
            }

        # If RDS fails, write to Glue
        if write_to_glue_catalog(data, database_name, table_name):
            return {
                'statusCode': 200,
                'body': 'Successfully wrote data to Glue Catalog'
            }

        return {
            'statusCode': 500,
            'body': 'Failed to write data to both RDS and Glue'
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }