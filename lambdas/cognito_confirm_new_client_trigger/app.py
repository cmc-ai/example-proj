import boto3
from payment_processor.swervepay import SwervePay
from constants import FundingType

cognito_client = boto3.client('cognito-idp')

def create_swerve_proc(acc_sid, username, apikey):
    return SwervePay(accountSid=acc_sid, username=username, apikey=apikey)


def lambda_handler(event, context):
    print(event)
    """
    {'version': '1', 
    'region': 'ca-central-1', 
    'userPoolId': 'ca-central-1_eznPYLov2', 
    'userName': '9db0023c-1ae8-467f-ac45-ea8dcf9bc96d', 
    'callerContext': {'awsSdkVersion': 'aws-sdk-unknown-unknown', 
                        'clientId': '6jfs3gnjcjl2qv8fap4tjjigma'}, 
    'triggerSource': 'PreSignUp_SignUp', 
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
                                    'custom:swerve_apikey': ''
                                    }, 
                'validationData': None}, 
    'response': {'autoConfirmUser': False, 'autoVerifyEmail': False, 'autoVerifyPhone': False}}
    """
    user_attrs = event['request']['userAttributes']
    event['response']['autoConfirmUser'] = False

    # create new payment account
    cardHolder = user_attrs.get('name')
    firstName = cardHolder.split()[0]
    lastName = '' if len(cardHolder.split()) < 2 else cardHolder.split()[1]
    swerve_acc_sid = user_attrs.get('custom:swerve_account_sid')
    swerve_username = user_attrs.get('custom:swerve_username')
    swerve_apikey = user_attrs.get('custom:swerve_apikey')
    cardNumber = user_attrs.get('custom:funding_account')
    expMonYear = user_attrs.get('custom:exp')
    cvc = user_attrs.get('custom:cvc')
    accountType = FundingType.cc.value

    print(f'Getting SP processor')
    sp_proc = create_swerve_proc(swerve_acc_sid, swerve_username, swerve_apikey)
    if not sp_proc:
        raise Exception(f'Failed to get SP processor for {swerve_acc_sid, swerve_username, swerve_apikey}')
        # return event

    print(f'Creating SP user')
    error_code, error_code_description, data_dict = sp_proc.create_user(firstName, lastName)
    print(f'create_user {firstName},{lastName}: {[error_code, error_code_description, data_dict]}')
    user_id = '' if not data_dict else data_dict.get('data', {})
    if not user_id:
        raise Exception(f'Failed to create SP user {firstName, lastName}')
        # return event

    print(f'Adding funding account')
    err_code, err_code_description, data_dict = sp_proc.add_funding_account(
        fundingType=accountType,
        billFirstName=firstName,
        billLastName=lastName,
        accountNumber=cardNumber.replace(' ',''),
        userid=user_id,
        cardExpirationDate=expMonYear.replace('/', ''),
        routingNumber=''
    )
    if err_code != 0:
        # raise Exception(f'Failed to add funding account {firstName, lastName, cardNumber, expMonYear, accountType}: {err_code, err_code_description, data_dict}')
        raise Exception(f'Failed to add funding account: {data_dict.get("reason")}')
        # return event

    tokenized_id = data_dict.get('data')

    # set custom:swerve_tokenized_id
    cognito_client.admin_update_user_attributes(
        UserPoolId=event.get('userPoolId'),
        Username=event.get('userName'),
        UserAttributes=[
            {
                'Name': 'custom:swerve_tokenized_id',
                'Value': str(tokenized_id)
            },
        ]
    )

    # other

    event['response']['autoConfirmUser'] = 'True'

    if 'email' in event['request']['userAttributes']:
        event['response']['autoVerifyEmail'] = True

    if 'phone_number' in event['request']['userAttributes']:
        event['response']['autoVerifyPhone'] = True

    return event
