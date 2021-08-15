import os
import pg8000
from botocore.exceptions import ClientError


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


def send_sms(pipoint_client, message, originationNumber, destinationNumber):
    print(f'SENDING MESSAGE: {message} FROM {originationNumber} TO {destinationNumber}')

    applicationId = os.getenv('AWS_PINPOINT_PROJECT_ID')
    registeredKeyword = os.getenv('AWS_PINPOINT_KEYWORD', '')
    messageType = os.getenv('AWS_PINPOINT_MESSAGE_TYPE', 'PROMOTIONAL')

    try:
        response = pipoint_client.send_messages(
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
        print("Message sent! Message ID: "
              + response['MessageResponse']['Result'][destinationNumber]['MessageId'])
