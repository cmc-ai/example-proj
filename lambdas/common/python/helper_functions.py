import os
import pg8000
from botocore.exceptions import ClientError
from datetime import datetime

from dynamo_models import BorrowerMessageModel


def get_or_create_pg_connection(pg_conn, rds_client):
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
        print(f"While connecting failed due to :{str(e)}")
        return None


def send_sms(pinoint_client, message, originationNumber, destinationNumber, borrower_id=None):
    print(f'SENDING MESSAGE: {message} FROM {originationNumber} TO {destinationNumber}')

    applicationId = os.getenv('AWS_PINPOINT_PROJECT_ID')
    registeredKeyword = os.getenv('AWS_PINPOINT_KEYWORD', '')
    messageType = os.getenv('AWS_PINPOINT_MESSAGE_TYPE', 'PROMOTIONAL')

    try:
        response = pinoint_client.send_messages(
            ApplicationId=applicationId,
            MessageRequest={
                'Addresses': {
                    destinationNumber: {
                        'ChannelType': 'SMS'
                    }
                },
                'MessageConfiguration': {
                    'SMSMessage': {
                        'Body': message,
                        'Keyword': registeredKeyword,
                        'MessageType': messageType,
                        'OriginationNumber': originationNumber
                    }
                }
            }
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Message sent: " + response['MessageResponse']['Result'][destinationNumber]['MessageId'])
        if borrower_id:
            log_sms(borrower_id, int(datetime.now().timestamp()), originationNumber, destinationNumber, message)


def log_sms(borrower_id, event_ts, origination_number, destination_number, text):
    print(f'Logging message to Dynamo: borrower_id {borrower_id} event_ts {event_ts}')
    item = BorrowerMessageModel(borrower_id=borrower_id,
                                event_ts=event_ts,
                                origination_number=origination_number,
                                destination_number=destination_number,
                                text=text)
    item.save()


def dt_to_ts(str_dt: str):
    # '2021-08-18T11:41:55.285Z'
    dt = datetime.strptime(str_dt, '%Y-%m-%dT%H:%M:%S.%fZ')
    return int(dt.timestamp())
