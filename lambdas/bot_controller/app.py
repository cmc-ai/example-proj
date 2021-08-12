import json
import os

import boto3

# this dependency is deployed to /opt/python by Lambda Layers
from helper_functions import get_or_create_pg_connection

lex_client = boto3.client('lexv2-runtime')
rds_client = boto3.client('rds')
pg_conn = None


def call_chatbot(response_msg_and_session_state):
    bot_id = os.getenv('AWS_LEX_BOT_ID', 'A9ENAISYXZ')
    bot_alias_id = os.getenv('AWS_LEX_BOT_ALIAS_ID', 'TSTALIASID')
    locale_id = os.getenv('AWS_LEX_LOCALE_ID', 'en_US')
    message = response_msg_and_session_state.get('messageBody')
    aws_lex_session_id = response_msg_and_session_state.get('aws_lex_session_id')

    print(f'Calling the chatbot bot_id {bot_id} bot_alias_id {bot_alias_id} locale_id {locale_id}')
    chatbot_response = lex_client.recognize_text(
        botId=bot_id,
        botAliasId=bot_alias_id,
        localeId=locale_id,
        sessionId=aws_lex_session_id,
        text=message,
        sessionState={},
        requestAttributes={}
    )
    print(f'Chatbot response: {chatbot_response}')

    return chatbot_response.get('messages')[0].get('content')


def start_conversation(response_msg_and_session_state):
    global pg_conn
    global rds_client
    conn = get_or_create_pg_connection(pg_conn, rds_client)

    # find debt details in Aurora
    query = f"""
                SELECT c.organization, d.outstandingBalance
                FROM Debt d JOIN Client c on d.client_id = c.id
                WHERE d.id = {response_msg_and_session_state.get('debt_id')}
            """
    cursor = conn.cursor()
    rows = cursor.execute(query).fetchall()
    cursor.close()
    organization, outstanding_balance = rows[0] if rows else (None, None)
    print(f'organization, outstanding_balance {organization, outstanding_balance}')

    new_msg = f'''
    {organization} has a balance in collections for ${outstanding_balance}. To make a payment, reply PAYMENT. To know more about debt, reply DETAIL.
    '''
    return new_msg


def lambda_handler(event, context):
    for record in event['Records']:
        response_msg_and_session_state = json.loads(record['body'])
        print(f'MESSAGE: {response_msg_and_session_state}')

        # process the msg+state with Lex
        if response_msg_and_session_state.get('is_first_entrance', True):
            new_msg = start_conversation(response_msg_and_session_state)
        else:
            new_msg = call_chatbot(response_msg_and_session_state)

        # send new message to originationNumber from destinationNumber
        print(f'New Message: {new_msg}')
