import boto3
import os
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()

# Konfiguracja połączenia z DigitalOcean Spaces
session = boto3.session.Session()
client = session.client(
    's3',
    region_name=os.getenv('DO_SPACES_REGION'),
    endpoint_url=os.getenv('DO_SPACES_ENDPOINT'),
    aws_access_key_id=os.getenv('DO_SPACES_KEY'),
    aws_secret_access_key=os.getenv('DO_SPACES_SECRET')
)

BUCKET_NAME = os.getenv('DO_SPACES_BUCKET')

# Upload plików
print("Uploading halfmarathon_2023.csv...")
client.upload_file(
    'data/raw/halfmarathon_2023.csv',
    BUCKET_NAME,
    'data/raw/halfmarathon_2023.csv'
)

print("Uploading halfmarathon_2024.csv...")
client.upload_file(
    'data/raw/halfmarathon_2024.csv',
    BUCKET_NAME,
    'data/raw/halfmarathon_2024.csv'
)

print("Upload completed!")
