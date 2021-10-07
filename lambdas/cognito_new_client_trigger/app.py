import os

import boto3
from helper_functions import get_or_create_pg_connection

ssm_client = boto3.client('ssm')
rds_client = boto3.client('rds')
pg_conn = None


def lambda_handler(event, context):
    print(event)
    """
    {'version': '1', 
    'region': 'ca-central-1', 
    'userPoolId': 'ca-central-1_uUYSvAsUz', 
    'userName': 'test-demo', 
    'callerContext': {'awsSdkVersion': 'aws-sdk-unknown-unknown', 
                        'clientId': None
                        }, 
    'triggerSource': 'PostConfirmation_ConfirmSignUp', 
    'request': {'userAttributes': {'custom:organization': 'ert', 
                                    'name': 'card holder', 
                                    'custom:funding_account': '99992222 2333 3333', 
                                    'custom:exp': '11/25', 
                                    'phone_number': '+12342345756', 
                                    'custom:cvc': '000', 
                                    'custom:payment': 'swerepay', 
                                    'email': 'delete@it.pls',
                                    'custom:swerve_account_sid': '',
                                    'custom:swerve_username': '',
                                    'custom:swerve_apikey': '',
                                    'custom:swerve_tokenized_id': ''
                                    }
                }, 
    'response': {}
    }
    """

    udata = event.get('request', {}).get('userAttributes', {})
    user_name = event.get('userName')
    if not udata or not user_name:
        print(f'No User Data found, return')
        return event
    cardHolder = udata.get('name')
    firstName = cardHolder.split()[0]
    lastName = '' if len(cardHolder.split()) < 2 else cardHolder.split()[1]
    cardNumber = udata.get('custom:funding_account')
    cardNumber_last_4_digits = int(str(cardNumber)[-4:])

    # TODO: SP stuff

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
        print(f'Failed to insert Funding Account, No Сlinet.id found, return')
        return event

    print(f'Inserting into ClientFundingAccount')
    insert_funding_acc_query = f"""
        INSERT INTO ClientFundingAccount
            (clientId, paymentProcessor, 
            cardNumber, cardHolder, paymentProcessorUserId
            createDate, lastUpdateDate)
        VALUES
            ({client_id}, '{udata.get('custom:payment')}',
            {cardNumber_last_4_digits}, {cardHolder}, {udata.get('custom:swerve_tokenized_id')},
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """
    conn.run(insert_funding_acc_query)
    conn.commit()

    # write swervepay creds to ParamStore
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
