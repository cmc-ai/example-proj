import os

import boto3
from boto3.dynamodb.conditions import Key

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute

dynamodb_resource = boto3.resource('dynamodb')


# def find_or_create_debt_state(debt_id, journey_id):
#     table_name = os.getenv('DYNAMODB_TABLE', 'chatbot-dev-sessions')
#     table = dynamodb_resource.Table(table_name)
#
#     items = table.query(KeyConditionExpression=Key('debt_id').eq(debt_id))
#
#     if items['Count'] > 0:
#         item = items['Items'][0]
#
#     else:
#         print(f'Debt Id {debt_id} is not found')
#         debt = {'debt_id': debt_id, 'journey_id': journey_id}
#
#         print(f'Add Debt {debt} to Table')
#         response = table.put_item(Item=debt)
#
#         if response.get('ResponseMetadata', {}).get('HTTPStatusCode', {}) == 200:
#             item = debt
#         else:
#             item = None
#
#     return item


###
# https://pynamodb.readthedocs.io/en/latest/

class DebtRecordModel(Model):
    class Meta:
        table_name = os.getenv('DYNAMODB_TABLE', 'chatbot-dev-sessions')
        region = os.getenv('AWS_REGION', 'ca-central-1')

    debt_id = NumberAttribute(hash_key=True)
    journey_id = NumberAttribute()


def find_or_create_debt_state(debt_id, journey_id):
    debt_records = [d for d in DebtRecordModel.query(debt_id)]

    if debt_records:
        debt_record = debt_records[0]  # TODO: what if several?
    else:
        print(f'Debt Id {debt_id} is not found')
        debt_record = DebtRecordModel(debt_id=debt_id, journey_id=journey_id)
        print(f'Add Debt {debt_record.attribute_values} to Table')
        debt_record.save()

    return debt_record.attribute_values  # convert to dict


###

print(find_or_create_debt_state(1, 1))
