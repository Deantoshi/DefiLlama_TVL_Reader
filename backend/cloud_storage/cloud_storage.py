from flask import Flask, request, jsonify
from web3 import Web3
from web3.middleware import geth_poa_middleware
import pandas as pd
import json
# from functools import cache
import threading 
import queue
import time
import datetime
from concurrent.futures import ThreadPoolExecutor
# import gcs_updater
from google.cloud import storage
import google.cloud.storage
import os
import sys
import io
from io import BytesIO
import zipfile

# PATH = os.path.join(os.getcwd(), 'fast-web-419215-35d284e06546.json')

# STORAGE_CLIENT = storage.Client(PATH)

# Assuming the key file is in your user's home directory
HOME_DIR = os.path.expanduser('~')
PATH = os.path.join(HOME_DIR, 'fast-web-419215-35d284e06546.json')
STORAGE_CLIENT = storage.Client.from_service_account_json(PATH)

# @cache
def read_from_cloud_storage(filename, bucketname):
    # storage_client = storage.Client(PATH)
    bucket = STORAGE_CLIENT.get_bucket(bucketname)

    df = pd.read_csv(
    io.BytesIO(
                 bucket.blob(blob_name = filename).download_as_string()
              ) ,
                 encoding='UTF-8',
                 sep=',',
                 dtype=str)

    return df

# # writes our dataframe to our desired filename
def df_write_to_cloud_storage(df, filename, bucketname):

    # storage_client = storage.Client(PATH)
    bucket = STORAGE_CLIENT.get_bucket(bucketname)

    csv_string = df.to_csv(index=False)  # Omit index for cleaner output
    blob = bucket.blob(filename)
    blob.upload_from_string(csv_string)

    return


def read_zip_csv_from_cloud_storage(filename, bucketname):
    # storage_client = storage.Client(PATH)
    bucket = STORAGE_CLIENT.get_bucket(bucketname)
    
    # Download the zip file content
    zip_content = bucket.blob(blob_name=filename).download_as_bytes()
    
    # Create a BytesIO object from the zip content
    zip_buffer = io.BytesIO(zip_content)
    
    # Open the zip file
    with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
        # Assume there's only one CSV file in the zip
        csv_filename = zip_ref.namelist()[0]
        
        # Read the CSV file from the zip
        with zip_ref.open(csv_filename) as csv_file:
            df = pd.read_csv(
                csv_file,
                encoding='UTF-8',
                sep=',',
                dtype=str
            )
    
    df = df.dropna()

    return df

def df_write_to_cloud_storage_as_zip(df, filename, bucketname):
    
    df = df.dropna()

    # Create a CSV string from the dataframe
    csv_string = df.to_csv(index=False)

    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        temp_filename = filename.split('.')
        temp_filename = temp_filename[0]
        zip_file.writestr(f"{temp_filename}.csv", csv_string)
    
    # Move the buffer's pointer to the beginning
    zip_buffer.seek(0)

    # Get the bucket
    bucket = STORAGE_CLIENT.get_bucket(bucketname)

    # Create a new blob and upload the zip file's content
    zip_filename = f"{filename}"
    blob = bucket.blob(zip_filename)
    blob.upload_from_file(zip_buffer, content_type='application/zip')

    return f"Uploaded {zip_filename} to {bucketname}"

# # will return a list of all the files with 'revenue' in their name from our GCP bucket
def get_all_revenue_files(bucket_name):
    """Lists all the blobs in the bucket that begin with the prefix."""
    bucket = STORAGE_CLIENT.get_bucket(bucket_name)

    # List blobs with the given prefix
    blobs = bucket.list_blobs()

    file_list = []
    for blob in blobs:
        if 'revenue' in blob.name.lower():
            file_list.append(blob.name)

    return file_list

# # will return a list of all the files with 'revenue' in their name from our GCP bucket
def get_all_prefix_files(bucket_name, prefix):
    """Lists all the blobs in the bucket that begin with the prefix."""
    bucket = STORAGE_CLIENT.get_bucket(bucket_name)

    # List blobs with the given prefix
    blobs = bucket.list_blobs()

    file_list = []
    for blob in blobs:
        if prefix in blob.name.lower():
            file_list.append(blob.name)

    return file_list