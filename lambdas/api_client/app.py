import boto3
import json
from jose import jwt

from constants import HTTPCodes
from api_controller_client import DebtAPIController, ClientAPIController, OtherAPIController
from api_payment_controller import PaymentAPIController
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

    path = event.get('path').rstrip('/')
    http_method = event.get('httpMethod')
    headers = event.get('headers')
    body = event.get('body')
    # print(f"Received body: {body}")
    if type(body) == str:
        try:
            body = json.loads(body)
        except Exception as e:
            print("Can not parse JSON body: {}")

    if not headers or not headers.get('Authorization'):
        return build_response({'message': 'No auth header found'}, HTTPCodes.UNAUTHORIZED.value)
    token = headers.get('Authorization')

    client_username = jwt.get_unverified_claims(token).get('cognito:username')
    request_params = {
        'path': path,
        'headers': headers,
        'params': event.get('queryStringParameters'),
        'body': body
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
        if http_method == 'POST':
            response = controller.validate_and_upload()
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
    elif path == '/api/portfolio':
        controller = ClientAPIController(**c_params)
        if http_method == 'GET':
            code, response = controller.get_portfolio()
        if http_method == 'POST':
            code, response = controller.post_portfolio()
        if http_method == 'PUT':
            code, response = controller.put_portfolio()
        if http_method == 'DELETE':
            code, response = controller.delete_portfolio()
    elif path == '/api/collection':
        controller = ClientAPIController(**c_params)
        if http_method == 'GET':
            code, response = controller.get_collection()
        if http_method == 'POST':
            code, response = controller.post_collection()
        if http_method == 'PUT':
            code, response = controller.put_collection()
        if http_method == 'DELETE':
            code, response = controller.delete_collection()

    # Other
    elif path == '/api/report':
        controller = OtherAPIController(**c_params)
        if http_method == 'GET':
            response = controller.get_report()

    elif path == '/api/payment-link':
        controller = PaymentAPIController(**c_params)
        if http_method == 'GET':
            code, response = controller.get_or_create_payment_link()

    return build_response(response, code)
