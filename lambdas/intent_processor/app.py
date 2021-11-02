from constants import INV_SRC_FULFILLMENT, INV_SRC_DIALOG, ChatbotPlaceholder, ChatbotIntent, SessionStateDialogAction


def fill_session_state(session_state: dict):
    session_state['dialogAction'] = session_state.get('dialogAction', {})
    session_state['dialogAction']['type'] = SessionStateDialogAction.close.value
    session_state['intent']['state'] = 'Fulfilled'

    return session_state


def process_initial_positive_intent(event: dict):
    print('Process Initial Positive Fulfillment')
    session_state = fill_session_state(event.get('sessionState').copy())
    messages = [{'contentType': 'PlainText', 'content': ChatbotPlaceholder.StartConversation.value}]

    response = {
        'sessionState': session_state,
        'messages': messages
    }
    return response


def process_initial_negative_intent(event: dict):
    print('Process Initial Negative Fulfillment')
    session_state = fill_session_state(event.get('sessionState').copy())
    messages = [{'contentType': 'PlainText', 'content': ChatbotPlaceholder.SorryUtterance.value}]

    response = {
        'sessionState': session_state,
        'messages': messages
    }
    return response


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
    messages = [{'contentType': 'PlainText',
                 'content': 'Cannot recognize your intent. Please answer more precisely.'}]

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
    {'sessionId': '630063752049469', 
    'inputTranscript': 'yes', 
    'interpretations': [{'intent': {'slots': {}, 'confirmationState': 'None', 'name': 'InitialPositiveIntent', 'state': 'ReadyForFulfillment'}, 'nluConfidence': 1.0}, 
                        {'intent': {'slots': {}, 'confirmationState': 'None', 'name': 'DiscountIntent', 'state': 'ReadyForFulfillment'}, 'nluConfidence': 0.25}, 
                        {'intent': {'slots': {}, 'confirmationState': 'None', 'name': 'PaymentIntent', 'state': 'ReadyForFulfillment'}, 'nluConfidence': 0.16}, 
                        {'intent': {'slots': {}, 'confirmationState': 'None', 'name': 'FallbackIntent', 'state': 'ReadyForFulfillment'}}, 
                        {'intent': {'slots': {}, 'confirmationState': 'None', 'name': 'InitialNegativeIntent', 'state': 'ReadyForFulfillment'}, 'nluConfidence': 0.09}
                        ], 
    'responseContentType': 'text/plain; charset=utf-8', 
    'invocationSource': 'FulfillmentCodeHook', 
    'messageVersion': '1.0', 
    'sessionState': {'activeContexts': [{'timeToLive': {'turnsToLive': 3, 'timeToLiveInSeconds': 86391}, 'name': 'InitialpositiveIntent_fulfilled', 'contextAttributes': {}}, 
                                        {'timeToLive': {'turnsToLive': 4, 'timeToLiveInSeconds': 86399}, 'name': 'InitialNegativeIntent_fulfilled', 'contextAttributes': {}}
                                        ], 
                    'intent': {'slots': {}, 'confirmationState': 'None', 'name': 'InitialPositiveIntent', 'state': 'ReadyForFulfillment'}, 
                    'originatingRequestId': 'de28f4cc-db5e-41d2-8bca-8af325b77880'
                    }, 
    'bot': {'aliasId': 'TSTALIASID', 'aliasName': 'TestBotAlias', 'name': 'TestBot', 'version': 'DRAFT', 'localeId': 'en_US', 'id': 'A9ENAISYXZ'}, 
    'inputMode': 'Text'
    }
    '''

    intent = event.get('sessionState').get('intent').get('name')

    if intent == ChatbotIntent.InitialPositiveIntent.value:
        response = process_initial_positive_intent(event)
    elif intent == ChatbotIntent.InitialNegativeIntent.value:
        response = process_initial_negative_intent(event)
    elif intent == ChatbotIntent.PaymentIntent.value:
        response = process_payment_intent(event)
    elif intent == ChatbotIntent.DetailsIntent.value:
        response = process_details_intent(event)
    elif intent == ChatbotIntent.DiscountIntent.value:
        response = process_discount_intent(event)
    elif intent == ChatbotIntent.NotEnoughMoneyIntent.value:
        response = process_not_enough_money_intent(event)
    else:
        response = process_fallback(event)

    print(f'Intent Processor response: {response}')
    """
    {'sessionState': {'activeContexts': [{'timeToLive': {'turnsToLive': 0, 
                                                        'timeToLiveInSeconds': 86400
                                                        }, 
                                            'name': 'StartConversation', 
                                            'contextAttributes': {}
                                            }
                                        ], 
                        'intent': {'slots': {}, 
                                    'confirmationState': 'None', 
                                    'name': 'InitialPositiveIntent', 
                                    'state': 'Fulfilled'
                                    }, 
                        'originatingRequestId': 'f7e9ca1c-995b-4be0-bbfd-e5319157470c', 
                        'dialogAction': {'type': 'Close'}
                        }, 
    'messages': [{'contentType': 'PlainText', 
                    'content': '_START_CONVERSATION_'
                    }
                ]
    }
    """
    if response.get('sessionState'):
        old_active_contexts = response.get('sessionState', {}).get('activeContexts', [])
        active_contexts = [ctx for ctx in old_active_contexts if ctx.get('timeToLive', {}).get('turnsToLive', 0) > 0]
        response['activeContexts'] = active_contexts

    print(f'UPD Intent Processor response: {response}')
    return response
