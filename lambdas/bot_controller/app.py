# OS ENVS TO BE ADDED:
# AWS_PINPOINT_KEYWORD (The SMS program name that you provided to AWS Support when you requested your dedicated number)

import boto3
import json
import os
import uuid

from datetime import datetime, timedelta


# this dependencies are deployed to /opt/python by Lambda Layers
from constants import ChatbotPlaceholder, ChatbotContext
from dynamo_models import DebtRecordModel
from helper_functions import get_or_create_pg_connection
from sms_functions import send_sms
from payment_controller import DebtPaymentController

pinoint_client = boto3.client('pinpoint', region_name=os.getenv('AWS_REGION'))
lex_client = boto3.client('lexv2-runtime')
param_store_client = boto3.client('ssm')
rds_client = boto3.client('rds')
pg_conn = None

DEFAULT_DISCOUNT_EXPIRATION_HOURS = 24


def find_or_create_debt_state(response_msg_and_session_state):
    debt_id = response_msg_and_session_state.get('debt_id')
    borrower_id = response_msg_and_session_state.get('borrower_id')
    is_initial_message = False  # for simplicity, move to Aurora later

    debt_records = [d for d in DebtRecordModel.query(debt_id)]

    if debt_records:
        print(f'Debt Id {debt_id} is found')
        debt_record = debt_records[0]
    else:
        print(f'Debt Id {debt_id} is not found')
        debt_record = DebtRecordModel(debt_id=debt_id,
                                      borrower_id=borrower_id,
                                      aws_lex_session_id=str(uuid.uuid4()))  # generate uuid for a new session
        is_initial_message = True
        print(f'Add Debt {debt_record.attribute_values} to Table')
        debt_record.save()

    state = debt_record.attribute_values  # convert to dict
    state.update({'is_initial_message': is_initial_message})
    return state


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

    if float(outstanding_balance) > 0:
        new_msg = f'''{organization.strip()} has a balance in collections for ${outstanding_balance}. To make a payment, reply PAYMENT. To know more about debt, reply DETAIL.'''
    else:
        new_msg = f'''{organization.strip()} has no balance in collection to you. Have a nice day!'''
    print(f'New Message: {new_msg}')
    return new_msg


def say_sorry(response_msg_and_session_state):
    new_msg = f'''Sorry. Have a nice day!'''
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


def get_payment_link(response_msg_and_session_state):
    global pg_conn
    global rds_client
    conn = get_or_create_pg_connection(pg_conn, rds_client)

    print(f'Generating Payment Link')
    p_controller = DebtPaymentController(response_msg_and_session_state.get('debt_id'))
    payment_link, exp_minutes = p_controller.get_or_create_payment_link(pg_conn=conn, ssm_client=param_store_client)

    return f'Link will be expired in {exp_minutes} minutes: {payment_link}'


def get_discount_proposal(response_msg_and_session_state):
    global pg_conn
    global rds_client
    conn = get_or_create_pg_connection(pg_conn, rds_client)

    # save new discount_expiration_dt
    discount_exp_dt = datetime.now() + timedelta(hours=DEFAULT_DISCOUNT_EXPIRATION_HOURS)
    query = f"""
        UPDATE Debt SET
        discountExpirationDateTime = TO_TIMESTAMP('{discount_exp_dt.strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS'),
        lastUpdateDate = CURRENT_TIMESTAMP
        WHERE id = {response_msg_and_session_state.get('debt_id')}
    """
    print(f'QUERY: {query}')
    conn.run(query)
    conn.commit()

    # get discount amount
    query = f"""
                    SELECT d.discount, d.outstandingBalance
                    FROM Debt d
                    WHERE d.id = {response_msg_and_session_state.get('debt_id')}
                    """
    cursor = conn.cursor()
    rows = cursor.execute(query).fetchall()
    cursor.close()

    discount, outstanding_balance = rows[0] if rows else ('', '')
    msg = f'We can offer you a ${discount} discount, which reduces your balance to ${float(outstanding_balance) - float(discount)}. This offer expires in 24 hours. To make a payment, reply PAYMENT'
    return msg


def redirect_on_agent(response_msg_and_session_state):
    # TODO: remove debt record from Dynamo ???
    # TODO:  close Journey(Entry)ExeActivity in Aurora ???

    msg = f'OK, our agent will contact you shortly'
    return msg


def process_placeholders(msg: str, response_msg_and_session_state: dict) -> str:
    if ChatbotPlaceholder.StartConversation.value in msg:
        return start_conversation(response_msg_and_session_state)
    elif ChatbotPlaceholder.SorryUtterance.value in msg:
        return say_sorry(response_msg_and_session_state)
    elif ChatbotPlaceholder.PaymentLink.value in msg:
        return get_payment_link(response_msg_and_session_state)
    elif ChatbotPlaceholder.DebtDiscount.value in msg:
        return get_discount_proposal(response_msg_and_session_state)
    elif ChatbotPlaceholder.DebtDetails.value in msg:
        return get_more_debt_details(response_msg_and_session_state)
    elif ChatbotPlaceholder.NotEnoughMoney.value in msg:
        return redirect_on_agent(response_msg_and_session_state)
    else:
        return msg


def call_chatbot(response_msg_and_session_state):
    bot_id = os.getenv('AWS_LEX_BOT_ID')
    bot_alias_id = os.getenv('AWS_LEX_BOT_ALIAS_ID')
    locale_id = os.getenv('AWS_LEX_LOCALE_ID')
    message = response_msg_and_session_state.get('messageBody')
    aws_lex_session_id = response_msg_and_session_state.get('aws_lex_session_id')

    session_state = {}
    if response_msg_and_session_state.get('is_initial_message', True):
        # add one-time StartConversation context
        session_state = {
            'activeContexts': [{'name': ChatbotContext.StartConversation.value,
                                'timeToLive': {'turnsToLive': 1, 'timeToLiveInSeconds': 86400},
                                'contextAttributes': {}}
                               ]
        }

    print(f'Calling the chatbot bot_id {bot_id} bot_alias_id {bot_alias_id} locale_id {locale_id}')
    chatbot_response = lex_client.recognize_text(
        botId=bot_id,
        botAliasId=bot_alias_id,
        localeId=locale_id,
        sessionId=aws_lex_session_id,
        text=message,
        sessionState=session_state,
        requestAttributes={}
    )
    print(f'Chatbot response: {chatbot_response}')
    message = chatbot_response.get('messages')[0].get('content')

    return process_placeholders(message, response_msg_and_session_state)


def lambda_handler(event, context):
    for record in event['Records']:
        response_msg_and_session_state = json.loads(record['body'])

        debt_record = find_or_create_debt_state(response_msg_and_session_state)
        response_msg_and_session_state.update(debt_record)

        print(f'Incoming message and session state: {response_msg_and_session_state}')

        # process the msg+state with Lex
        new_msg = call_chatbot(response_msg_and_session_state)

        # send and log the new message TO originationNumber FROM destinationNumber
        new_destinationNumber = response_msg_and_session_state.get('originationNumber')
        new_originationNumber = response_msg_and_session_state.get('destinationNumber')

        send_sms(pinoint_client, new_msg, new_originationNumber, new_destinationNumber,
                 response_msg_and_session_state.get('borrower_id'))

