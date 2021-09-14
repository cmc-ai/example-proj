import os
import boto3
from datetime import datetime

from api_controller_base import APIController
from constants import HTTPCodes
from payment_controller import decrypt_payment_link
from payment_processor.swervepay import SwervePay

LAST_INDEX = -1  # use these indexes to avoid magic numbers in code
THE_ONLY_INDEX = 0


class PaymentAPIController(APIController):

    def __init__(self, **kwargs):
        super(PaymentAPIController, self).__init__(**kwargs)
        self._sp_proc = None

    def _create_sp_proc(self, debt_id):
        query = f"SELECT id, clientId FROM Debt WHERE id = {debt_id}"
        debt_id, client_id = self._execute_select(query)[LAST_INDEX]

        sp_key_prefix = os.getenv('SWERVE_PAY_KEY_PREFIX')
        acc_sid_key = f'{sp_key_prefix}/{client_id}/account_sid'
        username_key = f'{sp_key_prefix}/{client_id}/username'
        apikey_key = f'{sp_key_prefix}/{client_id}/apikey'
        ssm_client = boto3.client('ssm')
        acc_sid = ssm_client.get_parameter(Name=acc_sid_key, WithDecryption=False)['Parameter']['Value']
        username = ssm_client.get_parameter(Name=username_key, WithDecryption=False)['Parameter']['Value']
        apikey = ssm_client.get_parameter(Name=apikey_key, WithDecryption=True)['Parameter']['Value']

        self._sp_proc = SwervePay(accountSid=acc_sid, username=username, apikey=apikey)

    def get_payment(self):
        hash = self.params.get('hash')
        crc = self.params.get('crc')
        ssm_payment_link_encryption_key = os.getenv('SSM_PAYMENT_LINK_ENCRYPTION_KEY')
        encryption_key = boto3.client('ssm').get_parameter(Name=ssm_payment_link_encryption_key,
                                                           WithDecryption=True)['Parameter']['Value']

        decrypted_link, verified = decrypt_payment_link(hash, encryption_key, crc)
        if not verified:
            return HTTPCodes.ERROR.value, {'message': 'Link Verification Failed'}

        debt_id, debt_amount, expiration_utc_ts = decrypted_link.split(':')
        print(f'Processing payment (debt_id, debt_amount, expiration_utc_ts) {debt_id, debt_amount, expiration_utc_ts}')

        if int(expiration_utc_ts) < datetime.utcnow().timestamp():
            return HTTPCodes.OK.value, {'message': 'Link Expired'}

        # get borrower's funding accounts
        query = f"""
            SELECT bfa.* 
            FROM Borrower b JOIN BorrowerFundingAccount bfa ON b.id = bfa.borrowerId
            WHERE b.debtId = {debt_id}
        """
        mapped_items = self._map_cols_rows(*self._execute_select(query))

        return HTTPCodes.OK.value, mapped_items

    def post_payment(self):
        # {'id': 1, 'borrowerid': 1, 'accounttype': 'cc', 'summary': 'idk some summary', 'paymentprocessor': 'Swerve',
        # 'token': 'dasfdasd3fDF', 'clientidexternal': '124132'}

        account_type = self.body.get('accountType', '')
        summary = self.body.get('summary', '')
        token = self.body.get('token', '')


        return HTTPCodes.OK.value, {}

# ----
# from helper_functions import get_or_create_pg_connection
# db_conn = get_or_create_pg_connection(None, boto3.client('rds'))
# c = PaymentAPIController(path='/api/payment',headers={},
#                          params={'hash': 'MTo0LjU6MTYzMDUwMjQ0Ng==', 'crc': '0x8af86f69'},
#                          body={},db_conn=db_conn) # ,client_username='test_ilnur'
# print(c.get_payment())