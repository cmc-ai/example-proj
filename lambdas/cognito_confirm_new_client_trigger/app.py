def lambda_handler(event, context):
    print(event)

    event['response']['autoConfirmUser'] = 'True'

    if 'email' in event['request']['userAttributes']:
        event['response']['autoVerifyEmail'] = True

    if 'phone_number' in event['request']['userAttributes']:
        event['response']['autoVerifyPhone'] = True

    return event
