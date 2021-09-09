def lambda_handler(event, context):
    print(event)

    event['response']['autoConfirmUser'] = 'True'

    return event
