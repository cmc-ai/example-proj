# OS ENVS TO BE ADDED
# AWS_PINPOINT_PROJECT_ID, AWS_PINPOINT_MESSAGE_TYPE,
# AWS_PINPOINT_KEYWORD (The SMS program name that you provided to AWS Support when you requested your dedicated number)

# Permissions
# mobiletargeting:SendMessages

import json
import os

import boto3


# this dependencies are deployed to /opt/python by Lambda Layers
from helper_functions import get_or_create_pg_connection, send_sms
from constants import ChatbotPlaceholder

pipoint_client = boto3.client('pinpoint', region_name=os.getenv('AWS_REGION'))
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
                FROM Debt d JOIN Client c on d.clientId = c.id
                WHERE d.id = {response_msg_and_session_state.get('debt_id')}
            """
    cursor = conn.cursor()
    rows = cursor.execute(query).fetchall()
    cursor.close()
    organization, outstanding_balance = rows[0] if rows else ('', '')

    new_msg = f'''{organization.strip()} has a balance in collections for ${outstanding_balance}. To make a payment, reply PAYMENT. To know more about debt, reply DETAIL.'''
    print(f'New Message: {new_msg}')
    return new_msg


def get_more_debt_details(response_msg_and_session_state):
    global pg_conn
    global rds_client
    conn = get_or_create_pg_connection(pg_conn, rds_client)

    query = f"""
                SELECT b.firstName, b.lastName, c.organization, d.outstandingBalance
                FROM Debt d JOIN Client c on d.clientId = c.id JOIN Borrower b on b.debtId = d.id
                WHERE d.id = {response_msg_and_session_state.get('debt_id')}
                AND b.phoneNum = '{response_msg_and_session_state.get('originationNumber')}'
                """
    cursor = conn.cursor()
    rows = cursor.execute(query).fetchall()
    cursor.close()
    firstName, lastName, organization, outstanding_balance = rows[0] if rows else ('', '', '', '')

    msg = f'Name: {firstName.strip()} {lastName.strip()}; OriginalCreditor: {organization.strip()}; Amount Due: ${outstanding_balance};  To make a payment, reply PAYMENT'
    return msg


def replace_placeholders(msg: str, response_msg_and_session_state: dict):
    msg = msg.replace(ChatbotPlaceholder.PaymentLink.value, 'www.make_payment.com')
    msg = msg.replace(ChatbotPlaceholder.DebtDetails.value, get_more_debt_details(response_msg_and_session_state))
    return msg


def lambda_handler(event, context):
    for record in event['Records']:
        response_msg_and_session_state = json.loads(record['body'])
        print(f'Incoming message and session state: {response_msg_and_session_state}')

        # process the msg+state with Lex
        if response_msg_and_session_state.get('is_first_entrance', True):
            new_msg = start_conversation(response_msg_and_session_state)
        else:
            raw_new_msg = call_chatbot(response_msg_and_session_state)
            new_msg = replace_placeholders(raw_new_msg, response_msg_and_session_state)

        # send the new message TO originationNumber FROM destinationNumber
        new_destinationNumber = response_msg_and_session_state.get('originationNumber')
        new_originationNumber = response_msg_and_session_state.get('destinationNumber')
        send_sms(pipoint_client, new_msg, new_originationNumber, new_destinationNumber)
