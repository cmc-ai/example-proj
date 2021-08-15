import os

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute


class DebtRecordModel(Model):
    class Meta:
        table_name = os.getenv('DYNAMODB_TABLE', 'chatbot-dev-sessions')  #
        region = os.getenv('AWS_REGION', 'ca-central-1')  #

    debt_id = NumberAttribute(hash_key=True)
    borrower_id = NumberAttribute()
    journey_id = NumberAttribute()
    aws_lex_session_id = UnicodeAttribute()