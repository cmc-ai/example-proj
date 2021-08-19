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


def process_discount_intent(event: dict):
    print('Process Discount Fulfillment')
    session_state = fill_session_state(event.get('sessionState').copy())
    messages = [{'contentType': 'PlainText', 'content': ChatbotPlaceholder.DebtDiscount.value}]

    response = {
        'sessionState': session_state,
        'messages': messages
    }
    return response


def process_not_enough_money_intent(event: dict):
    print('Process Not Enough Money Fulfillment')
    session_state = fill_session_state(event.get('sessionState').copy())
    messages = [{'contentType': 'PlainText', 'content': ChatbotPlaceholder.NotEnoughMoney.value}]

    response = {
        'sessionState': session_state,
        'messages': messages
    }
    return response


def lambda_handler(event, context):
    print(event)
    '''
    {'sessionId': '630063752049475', 
    'inputTranscript': 'detail', 
    'interpretations': [{'intent': {'slots': {}, 'confirmationState': 'None', 'name': 'DetailsIntent', 'state': 'ReadyForFulfillment'}, 'nluConfidence': 1.0}, 
                        {'intent': {'slots': {}, 'confirmationState': 'None', 'name': 'FallbackIntent', 'state': 'ReadyForFulfillment'}}, 
                        {'intent': {'slots': {}, 'confirmationState': 'None', 'name': 'PaymentIntent', 'state': 'ReadyForFulfillment'}, 'nluConfidence': 0.44}, 
                        {'intent': {'slots': {}, 'confirmationState': 'None', 'name': 'DiscountIntent', 'state': 'ReadyForFulfillment'}, 'nluConfidence': 0.36}], 
    'responseContentType': 'text/plain; charset=utf-8', 
    'invocationSource': 'FulfillmentCodeHook', 
    'messageVersion': '1.0', 
    'sessionState': {'intent': {'slots': {}, 
                                'confirmationState': 'None', 
                                'name': 'DetailsIntent', 
                                'state': 'ReadyForFulfillment'}, 
                    'originatingRequestId': '8f0a1ced-3592-48df-abaf-1634bcf0c279'}, 
    'inputMode': 'Text', 
    'bot': {'aliasId': 'TSTALIASID', 'aliasName': 'TestBotAlias', 'name': 'TestBot', 'version': 'DRAFT', 'localeId': 'en_US', 'id': 'A9ENAISYXZ'}}
    '''

    intent = event.get('sessionState').get('intent').get('name')

    if intent == ChatbotIntent.PaymentIntent.value:
        response = process_payment_intent(event)
    elif intent == ChatbotIntent.DetailsIntent.value:
        response = process_details_intent(event)
    elif intent == ChatbotIntent.DiscountIntent.value:
        response = process_discount_intent(event)
    elif intent == ChatbotIntent.NotEnoughMoneyIntent.value:
        response = process_not_enough_money_intent(event)
    else:
        response = process_fallback(event)

    return response
