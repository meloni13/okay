import boto3
import os
import sys
import subprocess
import requests

# AWS S3 and SQS clients
s3 = boto3.client('s3', region_name="us-east-1")
sqs = boto3.client('sqs', region_name="us-east-1")
ec2 = boto3.client('ec2', region_name="us-east-1")

# Bucket and queue names
INPUT_BUCKET = f"1233521057-in-bucket"
OUTPUT_BUCKET = f"1233521057-out-bucket"
REQUEST_QUEUE = f"1233521057-req-queue"
RESPONSE_QUEUE = f"1233521057-resp-queue"
TOKEN_URL = "http://169.254.169.254/latest/api/token"
INSTANCE_ID_URL = "http://169.254.169.254/latest/meta-data/instance-id"

def get_imds_token():
    headers = {"X-aws-ec2-metadata-token-ttl-seconds": "21600"}
    response = requests.put(TOKEN_URL, headers=headers, timeout=5)
    TOKEN = response.text 
    headers = {"X-aws-ec2-metadata-token": TOKEN}
    response = requests.get(INSTANCE_ID_URL, headers=headers, timeout=5)
    INSTANCE_ID = response.text
    return INSTANCE_ID

def process_request():
    while True:
        response = sqs.receive_message(QueueUrl=REQUEST_QUEUE, MaxNumberOfMessages=1)
        if 'Messages' in response:
            message = response['Messages'][0]
            file_name = message['Body']
            receipt_handle = message['ReceiptHandle']
            local_image_path = f"/tmp/{file_name}"
            s3.download_file(INPUT_BUCKET, file_name, local_image_path)
            try:
                result = subprocess.run(
                    ['python3', 'face_recognition.py', local_image_path],
                    capture_output=True, text=True
                )
                prediction = result.stdout.strip() 
            except Exception as e:
                prediction = "Unknown"
            s3.put_object(Bucket=OUTPUT_BUCKET, Key=file_name, Body=prediction)
            sqs.send_message(QueueUrl=RESPONSE_QUEUE, MessageBody=f"{file_name}:{prediction}")
            sqs.delete_message(QueueUrl=REQUEST_QUEUE, ReceiptHandle=receipt_handle)
            os.remove(local_image_path)
        else:
            instance_id=get_imds_token()
            ec2.stop_instances(InstanceIds=[instance_id])

if __name__ == '__main__':
    process_request()