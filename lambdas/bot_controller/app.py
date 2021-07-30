import json


def lambda_handler(event, context):

    print(event['Records'])

    for record in event['Records']:
        response_msg_and_state = json.loads(record['body'])
        print(f'MESSAGE: {response_msg_and_state}')

            # process the msg+state with Lex

            # send new message to originationNumber from destinationNumber
