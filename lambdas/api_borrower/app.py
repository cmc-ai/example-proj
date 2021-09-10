import boto3
import json

from constants import HTTPCodes
from controllers import DebtAPIController, ClientAPIController, OtherAPIController
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
    print(event)

    db_conn = get_or_create_pg_connection(pg_conn, rds_client)

    path = event.get('path').rstrip('/')
    http_method = event.get('httpMethod')
    headers = event.get('headers')
    body = json.loads(event.get('body')) if type(event.get('body')) == str else event.get('body')

    request_params = {
        'path': path,
        'headers': headers,
        'params': event.get('queryStringParameters'),
        'body': body
    }
    c_params = {
        'db_conn': db_conn
    }
    c_params.update(request_params)

    response = DEFAULT_RESPONSE
    code = HTTPCodes.OK.value

    # Debts
    if path == '/api/payment':
        controller = (**c_params)
        if http_method == 'GET':
            response = controller.get_debt()
        if http_method == 'POST':
            code, response = controller.post_portfolio()

    return build_response(response, code)
