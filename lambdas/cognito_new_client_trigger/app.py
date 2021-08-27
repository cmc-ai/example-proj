import boto3
from helper_functions import get_or_create_pg_connection


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
    'request': {'userAttributes': {'sub': '6c0b24cf-ee02-46f9-ae11-1cdee9a2c8ad', 
                                    'custom:organization': 'Provectus', 
                                    'email_verified': 'false', 
                                    'cognito:user_status': 'CONFIRMED', 
                                    'name': 'Demo', 
                                    'custom:funding_account': '123132132311122', 
                                    'phone_number_verified': 'false', 
                                    'phone_number': '+5555111221', 
                                    'custom:payment': 'swerepay', 
                                    'email': 'RN@AAAAAAAAA.COM'
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

    global pg_conn
    global rds_client
    conn = get_or_create_pg_connection(pg_conn, rds_client)

    print(f'Inserting into Client')
    insert_client_query = f"""
        INSERT INTO Client
            (username, phoneNum, email, organization, createDate, lastUpdateDate)
        VALUES
            (   {user_name},
                {udata.get('phone_number')},
                {udata.get('email')},
                {udata.get('custom:organization')},
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
    clinet_id, client_username = rows[0] if rows else (None, '')

    if not clinet_id:
        print(f'No clinet.id found, return')
        return event

    print(f'Inserting into ClientFundingAccount')
    insert_funding_acc_query = f"""
        INSERT INTO ClientFundingAccount
            (clientId, paymentProcessor, createDate, lastUpdateDate)
        VALUES
            (   {clinet_id},
                {udata.get('custom:payment')},
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
    """
    conn.run(insert_funding_acc_query)
    conn.commit()

    return event