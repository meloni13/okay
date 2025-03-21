import boto3
import time

# AWS SQS and EC2 clients
sqs = boto3.client('sqs', region_name="us-east-1")
ec2 = boto3.client('ec2', region_name="us-east-1")

REQUEST_QUEUE = "1233521057-req-queue"
APP_TIER_INSTANCE_PREFIX = "app-tier-instance"

def get_pending_requests():
    response = sqs.get_queue_attributes(
        QueueUrl=REQUEST_QUEUE, 
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(response['Attributes'].get('ApproximateNumberOfMessages', 0))

def get_stopped_instances():
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:Name', 'Values': [APP_TIER_INSTANCE_PREFIX + '*']},
            {'Name': 'instance-state-name', 'Values': ['stopped']} 
        ]
    )
    stopped_instances = [
        instance['InstanceId']
        for reservation in response.get('Reservations', [])
        for instance in reservation.get('Instances', [])
    ]
    return stopped_instances

def scale_app_tier():
    while True:
        pending_requests = get_pending_requests()
        stopped_instances = get_stopped_instances()   
        inst = 15-len(stopped_instances)
        count=0
        if inst<pending_requests:
            count=pending_requests-inst
        if count > 0:
            if stopped_instances:
                instances_to_start = min(count, len(stopped_instances))
                instances_to_start_list = stopped_instances[:instances_to_start]
                ec2.start_instances(InstanceIds=instances_to_start_list)
if __name__ == '__main__':
    scale_app_tier()
