import boto3
import json
from jose import jwt

from controllers import DebtAPIController, ClientAPIController, OtherAPIController
from constants import HTTPCodes
from helper_functions import get_or_create_pg_connection

DEFAULT_RESPONSE = {"message": "Path is not recognized"}

rds_client = boto3.client('rds')
pg_conn = None


def build_response(body: dict, code: int = 200):
    return {
        "statusCode": code,
        "body": json.dumps(body),
        "headers": {
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Requested-With',
            'Access-Control-Allow-Methods': 'GET,OPTIONS,POST,PUT',
            'Access-Control-Allow-Origin': '*'
        }
    }


def lambda_handler(event, context):
    db_conn = get_or_create_pg_connection(pg_conn, rds_client)

    print(event)
    """
    {'resource': '/api/debts', 
    'path': '/api/debts', 
    'httpMethod': 'GET', 
    'headers': {'authorization': 'eyJraWQiOiJUZGJOUVwvKzlyTG5pb1NPU2U2VGVQeEMzUzUyWGFJcmJaUTQ1dXN4R2RSOD0iLCJhbGciOiJSUzI1NiJ9.eyJjdXN0b206b3JnYW5pemF0aW9uIjoiUHJvdmVjdHVzIiwic3ViIjoiMDMxMGE0NDItMmExNy00OTFjLWI4OTgtYTZiOWVhODIzMTA1IiwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJjdXN0b206ZnVuZGluZ19hY2NvdW50IjoiOTA5MDkwOTAgOTA5MCA5MDkwIiwiaXNzIjoiaHR0cHM6XC9cL2NvZ25pdG8taWRwLmNhLWNlbnRyYWwtMS5hbWF6b25hd3MuY29tXC9jYS1jZW50cmFsLTFfbU91enpoemNTIiwicGhvbmVfbnVtYmVyX3ZlcmlmaWVkIjpmYWxzZSwiY3VzdG9tOmN2YyI6IjA5OCIsImNvZ25pdG86dXNlcm5hbWUiOiJtdGVyZXNoaW4iLCJjdXN0b206cGF5bWVudCI6InN3ZXJlcGF5Iiwib3JpZ2luX2p0aSI6ImM4YjViNzFhLTgwMTktNDA5ZS05MDI2LWEwNzJmZjk4Y2JhNyIsImF1ZCI6IjY3dW5sYmtkMDEwa3JncnZ1ZmJ1OTYxdXNzIiwiZXZlbnRfaWQiOiI0YjY2NGRlZS1kZjBkLTQwYWUtOTMzNC02MWU2NTFiOTRkMDkiLCJ0b2tlbl91c2UiOiJpZCIsImF1dGhfdGltZSI6MTYzMTA5MzE3MSwibmFtZSI6Ik1heGltIiwiY3VzdG9tOmV4cCI6IjEwXC8yOCIsInBob25lX251bWJlciI6Iis3OTE3OTM5NDI0MiIsImV4cCI6MTYzMTA5Njc3MSwiaWF0IjoxNjMxMDkzMTcxLCJqdGkiOiI5ZTRiZWFkYi1hYzljLTQ2YTMtYjgwYi0wNzliOGU2ODZmZjQiLCJlbWFpbCI6InRlcmVzaGluOTNAZ21haWwuY29tIn0.oeOTOtvf1Z7fwHucIc3fq7nSz538GtkP4E0dFWysrXvelL5Z1wTIdZnPS9CrN130LHV6nlPQ5yQ0gcWoWryUMir_QuB8jDeLnrMtxuz3bYeJt5fB-Gh1U0HIBKCC_v_2bd9w9bxnBAjnmZwf4G9pE2MnUKMHnTb2Dz7iT2OXLdybJH3KqE5dv2nFBk2RQTFhcBOJQON0Ks8AAVLiJBxhgMkFh1QF1kQXRHspl00xBUYTaXc01Ypoi9f5c89TOon9IPBx3DbogZcK3jCUqckXjJw2pcoIcbz_kT0s_XEcrsyRwhLBIC5T3wzqyUWlmgGKvMuPtWexuKXmCfK4O1zZbg'}, 
    'multiValueHeaders': None, 
    'queryStringParameters': {'firstName': 'Stan'}, 
    'multiValueQueryStringParameters': {'firstName': ['Stan']}, 
    'pathParameters': None, 
    'stageVariables': None, 
    'requestContext': {'resourceId': 'yokon5', 
                        'resourcePath': '/api/debts', 
                        'httpMethod': 'GET', 
                        'extendedRequestId': 'FFBNWEg44osF6hg=', 
                        'requestTime': '03/Sep/2021:08:52:37 +0000', 
                        'path': '/api/debts', 
                        'accountId': '630063752049', 
                        'protocol': 'HTTP/1.1', 
                        'stage': 'test-invoke-stage', 
                        'domainPrefix': 'testPrefix', 
                        'requestTimeEpoch': 1630659157293, 
                        'requestId': '53e9aaa7-c844-43cd-8987-e83be960e34a', 
                        'identity': {'cognitoIdentityPoolId': None, 
                                    'cognitoIdentityId': None, 
                                    'apiKey': 'test-invoke-api-key', 
                                    'principalOrgId': None, 
                                    'cognitoAuthenticationType': None, 
                                    'userArn': 'arn:aws:iam::630063752049:user/stanislav.nikitin', 
                                    'apiKeyId': 'test-invoke-api-key-id', 
                                    'userAgent': 'aws-internal/3 aws-sdk-java/1.11.1030 Linux/5.4.129-72.229.amzn2int.x86_64 OpenJDK_64-Bit_Server_VM/25.302-b08 java/1.8.0_302 vendor/Oracle_Corporation cfg/retry-mode/legacy', 
                                    'accountId': '630063752049', 
                                    'caller': 'AIDAZFMVZ4NYTIMFAHJM3', 
                                    'sourceIp': 'test-invoke-source-ip', 
                                    'accessKey': 'ASIAZFMVZ4NYTEAUBJPJ', 
                                    'cognitoAuthenticationProvider': None, 
                                    'user': 'AIDAZFMVZ4NYTIMFAHJM3'
                                    }, 
                        'domainName': 'testPrefix.testDomainName', 
                        'apiId': 'vm2fjqgdle'
                        }, 
    'body': None, 
    'isBase64Encoded': False
    }
    """

    path = event.get('path')
    http_method = event.get('httpMethod')
    headers = event.get('headers')

    token = headers.get('Authorization')
    if not token:
        return build_response({'message': 'No auth header found'}, HTTPCodes.UNAUTHORIZED.value)

    client_username = jwt.get_unverified_claims(token).get('cognito:username')
    request_params = {
        'path': path,
        'headers': headers,
        'params': event.get('queryStringParameters'),
        'body': event.get('body')
    }
    c_params = {
        'db_conn': db_conn,
        'client_username': client_username
    }
    c_params.update(request_params)

    response = DEFAULT_RESPONSE
    code = HTTPCodes.OK.value

    # Debts
    if path == '/api/debts':
        controller = DebtAPIController(**c_params)
        if http_method == 'GET':
            response = controller.get_debt()
    elif path == '/api/debts/upload':
        controller = DebtAPIController(**c_params)
        if http_method == 'GET':
            response = controller.upload()
    elif path == '/api/debts/download':
        controller = DebtAPIController(**c_params)
        if http_method == 'GET':
            response = controller.download()
    elif path.startswith('/api/chat-history/'):
        controller = DebtAPIController(**c_params)
        if http_method == 'GET':
            response = controller.get_chat_history()
    elif path.startswith('/api/payment-history/'):
        controller = DebtAPIController(**c_params)
        if http_method == 'GET':
            response = controller.get_payment_history()

    # Clients
    elif path == '/api/account':
        controller = ClientAPIController(**c_params)
        if http_method == 'GET':
            response = controller.get_account()
        if http_method == 'PATCH':
            code, response = controller.patch_account()
    elif path == '/api/account/refresh-api-token':
        controller = ClientAPIController(**c_params)
        if http_method == 'POST':
            response = controller.post_api_token()
    elif path.startswith('/api/portfolio/'):
        controller = ClientAPIController(**c_params)
        if http_method == 'GET':
            response = controller.get_portfolio()
        if http_method == 'POST':
            code, response = controller.post_portfolio()
    elif path.startswith('/api/collection/'):
        controller = ClientAPIController(**c_params)
        if http_method == 'GET':
            response = controller.get_collection()
        if http_method == 'POST':
            response = controller.post_collection()

    # Other
    elif path == '/api/report':
        controller = OtherAPIController(**c_params)
        if http_method == 'GET':
            response = controller.get_report()

    return build_response(response, code)
