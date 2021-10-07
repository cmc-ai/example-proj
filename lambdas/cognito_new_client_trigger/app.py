import os

import boto3

from payment_processor.swervepay import SwervePay
from helper_functions import get_or_create_pg_connection
from constants import FundingType

ssm_client = boto3.client('ssm')
rds_client = boto3.client('rds')
pg_conn = None
cognito_client = boto3.client('cognito-idp')


def create_swerve_proc(acc_sid, username, apikey):
    return SwervePay(accountSid=acc_sid, username=username, apikey=apikey)


def delete_cognito_user(user_pool_id, user_name):
    cognito_client.admin_delete_user(
        UserPoolId=user_pool_id,
        Username=user_name
    )


def lambda_handler(event, context):
    print(event)

    udata = event.get('request', {}).get('userAttributes', {})
    user_name = event.get('userName')
    user_pool_id = event.get('userPoolId')

    cardHolder = udata.get('name')
    firstName = cardHolder.split()[0]
    lastName = '' if len(cardHolder.split()) < 2 else cardHolder.split()[1]
    cardNumber = udata.get('custom:funding_account').replace(' ', '')
    cardNumber_last_4_digits = int(str(cardNumber)[-4:])
    swerve_acc_sid = udata.get('custom:swerve_account_sid')
    swerve_username = udata.get('custom:swerve_username')
    swerve_apikey = udata.get('custom:swerve_apikey')
    expMonYear = udata.get('custom:exp')
    accountType = FundingType.cc.value

    # SwervePay Validation

    print(f'Getting SP processor')
    sp_proc = create_swerve_proc(swerve_acc_sid, swerve_username, swerve_apikey)
    if not sp_proc:
        delete_cognito_user(user_pool_id, user_name)
        raise Exception(f'Failed to get SP processor for {swerve_acc_sid, swerve_username, swerve_apikey}')

    print(f'Creating SP user')
    error_code, error_code_description, data_dict = sp_proc.create_user(firstName, lastName)
    print(f'create_user {firstName},{lastName}: {[error_code, error_code_description, data_dict]}')
    user_id = '' if not data_dict else data_dict.get('data', {})
    if not user_id:
        delete_cognito_user(user_pool_id, user_name)
        raise Exception(f'Failed to create SP user {firstName, lastName}, reason: {data_dict.get("reason")}')

    print(f'Adding funding account')
    err_code, err_code_description, data_dict = sp_proc.add_funding_account(
        fundingType=accountType,
        billFirstName=firstName,
        billLastName=lastName,
        accountNumber=cardNumber,
        userid=user_id,
        cardExpirationDate=expMonYear.replace('/', ''),
        routingNumber=''
    )
    if err_code != 0:
        delete_cognito_user(user_pool_id, user_name)
        raise Exception(f'Failed to add funding account: {data_dict.get("reason")}')

    tokenized_id = data_dict.get('data')

    # Write to Database

    global pg_conn
    global rds_client
    conn = get_or_create_pg_connection(pg_conn, rds_client)

    print(f'Inserting into Client')
    insert_client_query = f"""
        INSERT INTO Client
            (username, firstName, lastName, phoneNum, email, organization, createDate, lastUpdateDate)
        VALUES
            (   '{user_name}',
                '{firstName}',
                '{lastName}',
                '{udata.get('phone_number')}',
                '{udata.get('email')}',
                '{udata.get('custom:organization')}',
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
    """
    conn.run(insert_client_query)
    conn.commit()

    print(f'Selecting id from Client')
    select_id_query = f"""
        SELECT id, username FROM Client
        WHERE username = '{user_name}'
        AND createDate = (SELECT MAX(createDate) FROM Client WHERE username = '{user_name}')
    """
    cursor = conn.cursor()
    rows = cursor.execute(select_id_query).fetchall()
    cursor.close()
    client_id, client_username = rows[0] if rows else (None, '')

    if not client_id:
        raise Exception(f'client_id not found')

    print(f'Inserting into ClientFundingAccount')
    insert_funding_acc_query = f"""
        INSERT INTO ClientFundingAccount
            (clientId, paymentProcessor, 
            cardNumber, cardHolder, paymentProcessorUserId
            createDate, lastUpdateDate)
        VALUES
            ({client_id}, '{udata.get('custom:payment')}',
            {cardNumber_last_4_digits}, {cardHolder}, {tokenized_id},
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """
    conn.run(insert_funding_acc_query)
    conn.commit()

    # Write SwervePay creds to ParamStore

    print(f'Adding swervepay creds to ParamStore')
    sp_key_prefix = os.getenv('SWERVE_PAY_KEY_PREFIX').rstrip('/')
    acc_sid_key = f'{sp_key_prefix}/{client_id}/account_sid'
    username_key = f'{sp_key_prefix}/{client_id}/username'
    apikey_key = f'{sp_key_prefix}/{client_id}/apikey'
    ssm_client.put_parameter(Name=acc_sid_key, Value=udata.get('custom:swerve_account_sid'), Type='String',
                             Overwrite=False, DataType='text')
    ssm_client.put_parameter(Name=username_key, Value=udata.get('custom:swerve_username'), Type='String',
                             Overwrite=False, DataType='text')
    ssm_client.put_parameter(Name=apikey_key, Value=udata.get('custom:swerve_apikey'), Type='SecureString',
                             Overwrite=False, DataType='text')

    return event
