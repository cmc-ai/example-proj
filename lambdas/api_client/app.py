import json

import boto3

from controllers import DebtAPIController, ClientAPIController, OtherAPIController

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
    print(event)
    """
    {'resource': '/api/debts', 
    'path': '/api/debts', 
    'httpMethod': 'GET', 
    'headers': None, 
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
    request_params = {
        'path': path,
        'headers': event.get('headers'),
        'params': event.get('queryStringParameters'),
        'body': event.get('body')
    }
    params = {
        'db_conn': pg_conn
    }
    params.update(request_params)

    response = DEFAULT_RESPONSE

    # Debts
    if path == '/api/debts':
        controller = DebtAPIController(**params)
        if http_method == 'GET':
            response = controller.get_debt()
    elif path == '/api/debts/upload':
        controller = DebtAPIController(**params)
        if http_method == 'GET':
            response = controller.upload()
    elif path == '/api/debts/download':
        controller = DebtAPIController(**params)
        if http_method == 'GET':
            response = controller.download()
    elif path.startswith('/api/chat-history/'):
        controller = DebtAPIController(**params)
        if http_method == 'GET':
            response = controller.get_chat_history()
    elif path.startswith('/api/payment-history/'):
        controller = DebtAPIController(**params)
        if http_method == 'GET':
            response = controller.get_payment_history()

    # Clients
    elif path == '/api/account':
        controller = ClientAPIController(**params)
        if http_method == 'GET':
            response = controller.get_account()
        if http_method == 'PATCH':
            response = controller.patch_account()
    elif path == '/api/account/refresh-api-token':
        controller = ClientAPIController(**params)
        if http_method == 'POST':
            response = controller.post_api_token()
    elif path.startswith('/api/portfolio/'):
        controller = ClientAPIController(**params)
        if http_method == 'GET':
            response = controller.get_portfolio()
        if http_method == 'POST':
            response = controller.post_portfolio()
    elif path.startswith('/api/collection/'):
        controller = ClientAPIController(**params)
        if http_method == 'GET':
            response = controller.get_collection()
        if http_method == 'POST':
            response = controller.post_collection()

    # Other
    elif path == '/api/report':
        controller = OtherAPIController(**params)
        if http_method == 'GET':
            response = controller.get_report()

    return build_response(response)
