from constants import INV_SRC_FULFILLMENT, INV_SRC_DIALOG, ChatbotPlaceholder, ChatbotIntent, SessionStateDialogAction


def fill_session_state(session_state: dict):
    session_state['dialogAction'] = session_state.get('dialogAction', {})
    session_state['dialogAction']['type'] = SessionStateDialogAction.close.value
    session_state['intent']['state'] = 'Fulfilled'

    return session_state


def process_payment_intent(event: dict):
    print('Process Payment Fulfillment')
    session_state = fill_session_state(event.get('sessionState').copy())
    messages = [{'contentType': 'PlainText', 'content': ChatbotPlaceholder.PaymentLink.value}]

    response = {
        'sessionState': session_state,
        'messages': messages
    }
    return response


def process_fallback(event: dict):
    print('Process Fallback Fulfillment')
    session_state = fill_session_state(event.get('sessionState').copy())
    messages = [{'contentType': 'PlainText', 'content': 'Cannot recognize your intent. To make a payment, reply PAYMENT. To know more about debt, reply DETAIL'}]

    response = {
        'sessionState': session_state,
        'messages': messages
    }
    return response


def process_details_intent(event: dict):
    print('Process Details Fulfillment')
    session_state = fill_session_state(event.get('sessionState').copy())
    messages = [{'contentType': 'PlainText', 'content': ChatbotPlaceholder.DebtDetails.value}]

    response = {
        'sessionState': session_state,
        'messages': messages
    }
    return response


def lambda_handler(event, context):
    print(event)
    '''
    {'sessionId': '630063752049952', 
    'inputTranscript': 'details', 
    'interpretations': [
        {'intent': {'slots': {},
                    'confirmationState': 'None', 
                    'name': 'DetailsIntent', 
                    'state': 'ReadyForFulfillment'}, 
        'nluConfidence': 1.0}, 
        {'intent': {'slots': {},    
                    'confirmationState': 'None', 
                    'name': 'PaymentIntent', 
                    'state': 'ReadyForFulfillment'}, 
        'nluConfidence': 0.45}, 
        {'intent': {'slots': {}, 
                    'confirmationState': 'None', 
                    'name': 'FallbackIntent', 
                    'state': 'ReadyForFulfillment'}}
    ], 
    'responseContentType': 'text/plain; charset=utf-8', 
    'invocationSource': 'FulfillmentCodeHook', 
    'messageVersion': '1.0', 
    'sessionState': {'intent': {'slots': {}, 
                                'confirmationState': 'None', 
                                'name': 'DetailsIntent', 
                                'state': 'ReadyForFulfillment'}, 
                    'originatingRequestId': '2ba81f3c-78eb-4184-98a6-dedfa248489f'}, 
    'inputMode': 'Text', 
    'bot': {'aliasId': 'TSTALIASID', 'aliasName': 'TestBotAlias', 'name': 'TestBot', 'version': 'DRAFT', 'localeId': 'en_US', 'id': 'A9ENAISYXZ'}}
    '''

    intent = event.get('sessionState').get('intent').get('name')

    if intent == ChatbotIntent.PaymentIntent.value:
        response = process_payment_intent(event)
    elif intent == ChatbotIntent.DetailsIntent.value:
        response = process_details_intent(event)
    else:
        response = process_fallback(event)

    return response
