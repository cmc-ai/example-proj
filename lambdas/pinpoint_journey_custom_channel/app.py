# OS Envs: PINPOINT_ORIGINATION_NUMBER_KEY
# Layers : sms_functions
# Permissions: Dynamo:write, Pinpoint:send_sms, ParamStore:read

import os

import boto3
from sms_functions import send_sms

param_store_client = boto3.client('ssm')
pinoint_client = boto3.client('pinpoint', region_name=os.getenv('AWS_REGION'))


def extract_data(endpoint):
    return {
        'address':      endpoint.get('Address'),
        'first_name':   endpoint.get('User').get('UserAttributes').get('FirstName')[0],
        'last_name':    endpoint.get('User').get('UserAttributes').get('LastName')[0],
        'borrower_id':  endpoint.get('User').get('UserId')
    }


def lambda_handler(event, context):
    print(event)
    ssm_origination_number_key = os.getenv('SSM_PINPOINT_ORIGINATION_NUMBER_KEY',
                                           '/chatbot-dev/dev/pinpoint/origination_number')
    origination_number = param_store_client.get_parameter(Name=ssm_origination_number_key,
                                                          WithDecryption=False)['Parameter']['Value']

    endpoints = [extract_data(event.get('Endpoints', {}).get(e)) for e in event.get('Endpoints')]
    for endpoint in endpoints:
        text = f'''Hello! Am I talking with {endpoint.get('first_name')} {endpoint.get('last_name')}?'''

        send_sms(pinoint_client, text, origination_number, endpoint.get('address'), endpoint.get('borrower_id'))
