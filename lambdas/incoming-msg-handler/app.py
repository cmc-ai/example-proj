import json
import os

import boto3
import pg8000

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


def get_pg_connection():
    global pg_conn

    if pg_conn:
        return pg_conn

    try:
        print("Connecting to database")

        DBEndPoint = os.environ.get("DBEndPoint")
        DatabaseName = os.environ.get("DatabaseName")
        DBUserName = os.environ.get("DBUserName")
        password = rds_client.generate_db_auth_token(DBHostname=DBEndPoint, Port=5432, DBUsername=DBUserName)

        # Establishes the connection with the server using the token generated as password
        pg_conn = pg8000.connect(
            host=DBEndPoint,
            user=DBUserName,
            database=DatabaseName,
            password=password,
            ssl_context=True
        )

        print("Connected to database")
        return pg_conn

    except Exception as e:
        print("While connecting failed due to :{0}".format(str(e)))
        return None


def find_debt_by_number(origination_number: str):
    conn = get_pg_connection()
    query = f"""
            SELECT b.debtId, jea.journeyId
            FROM Debt d JOIN Borrower b on d.id = b.debtId
            JOIN JourneyEntryActivity jea on d.id = jea.debtId
            where b.phoneNum = '{origination_number}'
            and jea.exitDateTime IS NULL
        """
    cursor = conn.cursor()
    rows = cursor.execute(query).fetchall()
    # colnames = [desc[0] for desc in cursor.description]
    cursor.close()

    debt_id, journey_id = rows[0] if rows else (None, None)
    return debt_id, journey_id


def find_or_create_debt_state(debt_id, journey_id):
    item = None
    # get data by debt_id

    # if no data, create item and get it

    return item


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

            debt_id, journey_id = find_debt_by_number(originationNumber)
            debt_state = find_or_create_debt_state(debt_id, journey_id)

            messages.append({
                'originationNumber': originationNumber,
                'destinationNumber': destinationNumber,
                'messageKeyword': messageKeyword,
                'messageBody': messageBody
                # some DynamoDB data
            })

    sqs_queue_name = os.getenv('SQS_QUEUE_NAME')
    print(f'Downstream SQS queue: {sqs_queue_name}')
    queue = sqs_resource.get_queue_by_name(QueueName=sqs_queue_name)
    write_batch_sqs(messages, queue)
