import json
import os
import uuid

import boto3
# import pg8000

# this dependency is deployed to /opt/python by Lambda Layers
from debt_record_model import DebtRecordModel
from helper_functions import get_or_create_pg_connection

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


def find_or_create_debt_state(debt_id, borrower_id, journey_id):
    is_first_entrance = False  # for simplicity, move to Aurora later

    debt_records = [d for d in DebtRecordModel.query(debt_id)]

    if debt_records:
        print(f'Debt Id {debt_id} is found')
        debt_record = debt_records[0]  # what if several?
    else:
        print(f'Debt Id {debt_id} is not found')
        debt_record = DebtRecordModel(debt_id=debt_id,
                                      borrower_id=borrower_id,
                                      journey_id=journey_id,
                                      aws_lex_session_id=str(uuid.uuid4()))  # generate uuid for a new session
        is_first_entrance = True
        print(f'Add Debt {debt_record.attribute_values} to Table')
        debt_record.save()

    state = debt_record.attribute_values  # convert to dict
    state.update({'is_first_entrance': is_first_entrance})
    return state


def lambda_handler(event, context):
    print(event['Records'])

    messages = []
    for record in event['Records']:
        if record.get('Sns'):
            response_msg = json.loads(record['Sns']['Message'])
            originationNumber = response_msg['originationNumber']
            destinationNumber = response_msg['destinationNumber']
            messageKeyword = response_msg['messageKeyword']
            messageBody = response_msg['messageBody']
            print(f"Response message from {originationNumber}: {messageKeyword} {messageBody}")
            msg = {
                'originationNumber': originationNumber,
                'destinationNumber': destinationNumber,
                'messageKeyword': messageKeyword,
                'messageBody': messageBody
            }

            debt_id, borrower_id, journey_id = find_debt_by_number(originationNumber)
            print(f'DebtId, JourneyId found: {debt_id} {journey_id}')

            debt_record = find_or_create_debt_state(debt_id, borrower_id, journey_id)
            print(f'Debt state found: {debt_record}')
            msg.update(debt_record)

            messages.append(msg.copy())

    sqs_queue_name = os.getenv('SQS_QUEUE_NAME')
    print(f'Downstream SQS queue: {sqs_queue_name}')
    queue = sqs_resource.get_queue_by_name(QueueName=sqs_queue_name)
    write_batch_sqs(messages, queue)
