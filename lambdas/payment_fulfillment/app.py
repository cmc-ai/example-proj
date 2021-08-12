import json

# TODO: move to Layer
###
from enum import Enum

INV_SRC_FULFILLMENT = 'FulfillmentCodeHook'
INV_SRC_DIALOG = 'DialogCodeHook'

class SessionStateDialogAction(Enum):
    close = 'Close'
    confirm_intent = 'ConfirmIntent'
    delegate = 'Delegate'
    elicit_intent = 'ElicitIntent'
    elicit_slot = 'ElicitSlot'


###

def process_fulfillment(event: dict):
    print('Process Fulfillment')

    session_state = event.get('sessionState')
    session_state['dialogAction'] = session_state.get('dialogAction', {})
    session_state['dialogAction']['type'] = SessionStateDialogAction.close.value
    session_state['intent']['state'] = 'Fulfilled'

    messages = [{'contentType': 'PlainText', 'content': 'PaymentLink'}]

    response = {
        'sessionState': session_state,
        'messages': messages
    }

    return response


def process_dialog(event: dict):
    # TODO
    return None


def lambda_handler(event, context):

    print(event)
    '''
    {'sessionId': '630063752049475', 
    'inputTranscript': 'I want to pay', 
    'interpretations': [{'intent': {'slots': {}, 'confirmationState': 'None', 'name': 'PaymentIntent', 'state': 'ReadyForFulfillment'}, 'nluConfidence': 1.0}, 
                        {'intent': {'slots': {}, 'confirmationState': 'None', 'name': 'FallbackIntent', 'state': 'ReadyForFulfillment'}}
                        ], 
    'responseContentType': 'text/plain; charset=utf-8', 
    'invocationSource': 'FulfillmentCodeHook', 
    'messageVersion': '1.0', 
    'sessionState': {'intent': {'slots': {}, 'confirmationState': 'None', 'name': 'PaymentIntent', 'state': 'ReadyForFulfillment'}, 'originatingRequestId': 'be6e8d61-fad4-45b5-9c27-3cabd0f1ab1f'}, 
    'inputMode': 'Text', 
    'bot': {'aliasId': 'TSTALIASID', 'aliasName': 'TestBotAlias', 'name': 'TestBot', 'version': 'DRAFT', 'localeId': 'en_US', 'id': 'A9ENAISYXZ'}
    }
    '''

    inv_src = event.get('invocationSource')
    if inv_src == INV_SRC_FULFILLMENT:
        response = process_fulfillment(event)
    elif inv_src == INV_SRC_DIALOG:
        response = process_dialog(event)
    else:
        response = None

    return response
