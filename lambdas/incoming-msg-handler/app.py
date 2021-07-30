import json
import os

import boto3

MAX_BATCH_SIZE = 10
SQS_QUEUE_NAME = os.getenv('SQS_QUEUE_NAME')
sqs_resource = boto3.resource('sqs')


def write_batch_sqs(messages: list):
    queue = sqs_resource.get_queue_by_name(QueueName=SQS_QUEUE_NAME)
    batches = [messages[x:x + MAX_BATCH_SIZE] for x in range(0, len(messages), MAX_BATCH_SIZE)]

    for batch in batches:
        entries = []
        for message in batch:
            entries.append({
                'Id': str(len(entries) + 1),
                'MessageBody': json.dumps(message)
            })

        response = queue.send_messages(Entries=entries)
        print(f'PUSH_TO_QUEUE RESPONSE: {response}')


def lambda_handler(event, context):
    print(event['Records'])
    """
    [{'EventSource': 'aws:sns', 
    'EventVersion': '1.0', 
    'EventSubscriptionArn': 'arn:aws:sns:ca-central-1:630063752049:test-incoming-msg-topic:60affe38-2824-4f9d-a9a6-c00c186debf5', 
    'Sns': {'Type': 'Notification', 
            'MessageId': '166f4ff5-7d3e-56fc-9a03-1681d53578f2', 
            'TopicArn': 'arn:aws:sns:ca-central-1:630063752049:test-incoming-msg-topic', 
            'Subject': None, 
            
            'Message': '{\n  "originationNumber":"+14255550182",\n  "destinationNumber":"+12125550101",\n  "messageKeyword":"JOIN",\n  "messageBody":"EXAMPLE",\n  "inboundMessageId":"cae173d2-66b9-564c-8309-21f858e9fb84",\n  "previousPublishedMessageId":"wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n}', 
            
            'Timestamp': '2021-07-23T11:19:39.334Z', 
            'SignatureVersion': '1', 
            'Signature': 'O+lemvM4TsYUQv+anEkYVt7ag82YwdAMudrSX8bq+MbSSuPeQp+aTSTCR0g3iUDCjwMtiLkUfP24hQxKzMNZD/YcP/Z9lXRGLrTdj2R9w70Le9AW9FOnQlPQ60VdcipOaSuzReU4SsW5prvhT4Jao2qctuSN6pHOILMSrVdmRAJdtwS/LDLVAZdMQFye3mSvLtPBzpz5z55XeCb8JfCoBvEsaZkflw2MIYE2FZ4gM+n+qXxKzWe4vmFzzBsrUJTQgdCUjxnnggqYQDzDTXhiVnqQ72WXRjJq9AwKTVwitPNbnG60AZIsmTfuT+703nTQ/ysVaT5o3jwQCPCc4sIYIA==', 
            'SigningCertUrl': 'https://sns.ca-central-1.amazonaws.com/SimpleNotificationService-010a507c1833636cd94bdb98bd93083a.pem', 
            'UnsubscribeUrl': 'https://sns.ca-central-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:ca-central-1:630063752049:test-incoming-msg-topic:60affe38-2824-4f9d-a9a6-c00c186debf5', 
            'MessageAttributes': {}
            }
    }]
    """
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

    write_batch_sqs(messages)
