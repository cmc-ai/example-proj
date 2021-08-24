import os

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, BooleanAttribute


class DebtRecordModel(Model):
    class Meta:
        table_name = os.getenv('DYNAMODB_SESSION_TABLE')
        region = os.getenv('AWS_REGION')

    debt_id = NumberAttribute(hash_key=True)
    borrower_id = NumberAttribute()
    aws_lex_session_id = UnicodeAttribute()


class BorrowerMessageModel(Model):
    class Meta:
        table_name = os.getenv('DYNAMODB_MESSAGE_TABLE')
        region = os.getenv('AWS_REGION')

    borrower_id = NumberAttribute(hash_key=True)
    event_ts = NumberAttribute(range_key=True)
    origination_number = UnicodeAttribute()
    destination_number = UnicodeAttribute()
    text = UnicodeAttribute()