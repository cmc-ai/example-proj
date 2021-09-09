def lambda_handler(event, context):
    print(event)

    event['autoConfirmUser'] = event\
        .get('response', {})\
        .get('autoConfirmUser', {})
    event['autoConfirmUser'] = True

    return event
