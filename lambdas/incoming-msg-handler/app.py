import json
import os

import boto3

sqs_resource = boto3.resource('sqs')

MAX_BATCH_SIZE = 10


def write_batch_sqs(messages: list, queue):
    batches = [messages[x:x + MAX_BATCH_SIZE] for x in range(0, len(messages), MAX_BATCH_SIZE)]
    print(f'NUM OF BATCHES: {len(batches)}')

    for batch in batches:
        entries = []
        for message in batch:
            entries.append({
                'Id': str(len(entries) + 1),
                'MessageBody': json.dumps(message)
            })

        response = queue.send_messages(Entries=entries)
        print(f'PUSH-TO-QUEUE RESPONSE: {response}')


def lambda_handler(event, context):
    print(event['Records'])

    sqs_queue_name = os.getenv('SQS_QUEUE_NAME')
    messages = []

    for record in event['Records']:
        if record.get('Sns'):
            response_msg = json.loads(record['Sns']['Message'])
            originationNumber = response_msg['originationNumber']
            destinationNumber = response_msg['destinationNumber']
            messageKeyword = response_msg['messageKeyword']
            messageBody = response_msg['messageBody']
            print(f"Response message from {destinationNumber}: {messageKeyword} {messageBody}")

            # TODO: extract state from DynamoDB by originationNumber,destinationNumber

            messages.append({
                'originationNumber': originationNumber,
                'destinationNumber': destinationNumber,
                'messageKeyword': messageKeyword,
                'messageBody': messageBody
                # some DynamoDB data
            })

    print(f'Downstream SQS queue: {sqs_queue_name}')
    queue = sqs_resource.get_queue_by_name(QueueName=sqs_queue_name)
    write_batch_sqs(messages, queue)
