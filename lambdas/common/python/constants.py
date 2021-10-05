from enum import Enum

INV_SRC_FULFILLMENT = 'FulfillmentCodeHook'
INV_SRC_DIALOG = 'DialogCodeHook'

PAYMENT_LINK_HASH_PATTERN = 'debt_id:amount:expiration_utc_ts'

LEX_MAX_TTL_SECONDS = 86400
LEX_MAX_TTL_TIMES = 20


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


class HTTPCodes(Enum):
    OK = 200
    CREATED = 201
    ERROR = 400
    UNAUTHORIZED = 401


class FundingType(Enum):
    cc = 'cc'
    ach = 'ach'


class DBDebtStatus(Enum):
    waiting_journey_assignment = 'waiting-journey-assignment'
    in_journey = 'in-journey'
    journey_quit = 'journey-quit'


class DBJourneyDebtStatus(Enum):
    is_responded = 'is_responded'
    agree_to_pay = 'agree_to_pay'
    paid = 'paid'
    redirected_on_agent = 'redirected_on_agent'


class DBBorrowerChannelType(Enum):
    SMS = 'SMS'


class JourneyProcessStatus(Enum):
    success = 'success'
    failed = 'failed'
    in_progress = 'in_progress'


class PaymentProccessorPaymentStatus(Enum):
    OK = 'OK'