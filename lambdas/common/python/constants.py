from enum import Enum

INV_SRC_FULFILLMENT = 'FulfillmentCodeHook'
INV_SRC_DIALOG = 'DialogCodeHook'


class ChatbotIntent(Enum):
    PaymentIntent = 'PaymentIntent'
    DetailsIntent = 'DetailsIntent'
    FallbackIntent = 'FallbackIntent'


class SessionStateDialogAction(Enum):
    close = 'Close'
    confirm_intent = 'ConfirmIntent'
    delegate = 'Delegate'
    elicit_intent = 'ElicitIntent'
    elicit_slot = 'ElicitSlot'


class ChatbotPlaceholder(Enum):
    PaymentLink = '_PAYMENT_LINK_'
    DebtDetails = '_DEBT_DETAILS_'
