
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

    return