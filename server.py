from flask import Flask, request, Response
import boto3
import threading
import time

app = Flask(__name__)

S3 = "1233521057-in-bucket"
REQUEST_QUEUE = f"1233521057-req-queue"
RESPONSE_QUEUE = f"1233521057-resp-queue"

s3_client = boto3.client("s3", region_name="us-east-1")
sqs_client = boto3.client("sqs", region_name="us-east-1")

request_queue_url = sqs_client.get_queue_url(QueueName=REQUEST_QUEUE)["QueueUrl"]
response_queue_url = sqs_client.get_queue_url(QueueName=RESPONSE_QUEUE)["QueueUrl"]

image_results = {}

def process_response_queue():
    while True:
        response = sqs_client.receive_message(QueueUrl=response_queue_url, MaxNumberOfMessages=1)
        if 'Messages' in response:
            for message in response['Messages']:
                result = message['Body']
                if ":" in result:
                    file_name, prediction = result.split(":", 1)
                    image_results[file_name] = prediction.strip()
                sqs_client.delete_message(QueueUrl=response_queue_url, ReceiptHandle=message['ReceiptHandle'])

@app.route('/', methods=['POST'])
def handle_request():
    if 'inputFile' not in request.files:
        return "No file uploaded", 400

    file = request.files['inputFile']
    file_name = file.filename
    s3_client.upload_fileobj(file, S3, file_name)
    sqs_client.send_message(QueueUrl=request_queue_url, MessageBody=file_name)
    while True:
        if file_name in image_results:
            result = image_results.pop(file_name)
            return f"{file_name}:{result}"

response_thread = threading.Thread(target=process_response_queue, daemon=True)
response_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
