import os
from datetime import datetime

from botocore.exceptions import ClientError
from dynamo_models import BorrowerMessageModel


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
