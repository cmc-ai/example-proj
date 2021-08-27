import json
import os

import boto3

# this dependency is deployed to /opt/python by Lambda Layers
from helper_functions import get_or_create_pg_connection, dt_to_ts
from sms_functions import log_sms

sqs_resource = boto3.resource('sqs')
rds_client = boto3.client('rds')
pg_conn = None

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


def find_debt_by_number(origination_number: str):
    global pg_conn
    global rds_client
    conn = get_or_create_pg_connection(pg_conn, rds_client)

    query = f"""
            SELECT b.debtId, b.id, jea.journeyId
            FROM Debt d JOIN Borrower b on d.id = b.debtId
            JOIN JourneyEntryActivity jea on d.id = jea.debtId
            where b.phoneNum = '{origination_number}'
            and jea.exitDateTime IS NULL
        """
    cursor = conn.cursor()
    rows = cursor.execute(query).fetchall()
    # colnames = [desc[0] for desc in cursor.description]
    cursor.close()

    debt_id, borrower_id, journey_id = rows[0] if rows else (None, None, None)
    return debt_id, borrower_id, journey_id


def lambda_handler(event, context):
    print(event['Records'])

    messages = []
    for record in event['Records']:
        if record.get('Sns'):
            response_msg = json.loads(record['Sns']['Message'])
            response_ts = dt_to_ts(record['Sns']['Timestamp'])
            originationNumber = response_msg['originationNumber']
            destinationNumber = response_msg['destinationNumber']
            messageBody = response_msg['messageBody']
            print(f"Response message: {response_msg}")

            debt_id, borrower_id, journey_id = find_debt_by_number(originationNumber)
            print(f'debt_id, borrower_id, journey_id: {debt_id} {borrower_id} {journey_id}')

            log_sms(borrower_id, response_ts, originationNumber, destinationNumber, messageBody)

            msg = {
                'originationNumber': originationNumber,
                'destinationNumber': destinationNumber,
                'messageKeyword': response_msg['messageKeyword'],
                'messageBody': messageBody,
                'debt_id': debt_id,
                'borrower_id': borrower_id,
                'journey_id': journey_id
            }
            messages.append(msg.copy())

    sqs_queue_name = os.getenv('SQS_QUEUE_NAME')
    print(f'Downstream SQS queue: {sqs_queue_name}')
    queue = sqs_resource.get_queue_by_name(QueueName=sqs_queue_name)
    write_batch_sqs(messages, queue)
