from enum import Enum

INV_SRC_FULFILLMENT = 'FulfillmentCodeHook'
INV_SRC_DIALOG = 'DialogCodeHook'


class ChatbotIntent(Enum):
    InitialPositiveIntent = 'InitialPositiveIntent'
    InitialNegativeIntent = 'InitialNegativeIntent'
    PaymentIntent = 'PaymentIntent'
    DetailsIntent = 'DetailsIntent'
    DiscountIntent = 'DiscountIntent'
    FallbackIntent = 'FallbackIntent'
    NotEnoughMoneyIntent = 'NotEnoughMoneyIntent'


class SessionStateDialogAction(Enum):
    close = 'Close'
    confirm_intent = 'ConfirmIntent'
    delegate = 'Delegate'
    elicit_intent = 'ElicitIntent'
    elicit_slot = 'ElicitSlot'


class ChatbotPlaceholder(Enum):
    StartConversation = '_START_CONVERSATION_'
    SorryUtterance = '_SORRY_UTTERANCE_'
    PaymentLink = '_PAYMENT_LINK_'
    DebtDetails = '_DEBT_DETAILS_'
    DebtDiscount = '_DEBT_DISCOUNT_'
    NotEnoughMoney = '_NOT_ENOUGH_MONEY_'


class ChatbotContext(Enum):
    StartConversation = 'StartConversation'
    InitialNegativeIntent_fulfilled = 'InitialNegativeIntent_fulfilled'
    InitialpositiveIntent_fulfilled = 'InitialpositiveIntent_fulfilled'
    DiscountIntent_fulfilled = 'DiscountIntent_fulfilled'