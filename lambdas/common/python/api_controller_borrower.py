import os
import boto3
from datetime import datetime
from typing import Dict

from api_controller_base import APIController
from constants import HTTPCodes, FundingType, PaymentProccessorPaymentStatus, DBDebtStatus, DBJourneyDebtStatus
from dynamo_models import DebtRecordModel
from payment_controller import decrypt_payment_link
from payment_processor.swervepay import SwervePay
from sms_functions import send_sms
from payment_controller import DebtPaymentController

LAST_INDEX = -1  # use these indexes to avoid magic numbers in code
THE_ONLY_INDEX = 0
PAYMENT_PROCESSOR_NAME = 'SwervePay'

pinoint_client = boto3.client('pinpoint', region_name=os.getenv('AWS_REGION'))
param_store_client = boto3.client('ssm')


class PaymentAPIController(APIController):

    def __init__(self, **kwargs):
        super(PaymentAPIController, self).__init__(**kwargs)
        self._sp_proc = None

    def _create_and_send_new_payment_link(self, borrower_id: int, borrower_phone_number: str, debt_id: int):
        payment_link, exp_minutes = DebtPaymentController(debt_id=debt_id).get_or_create_payment_link(
            pg_conn=self.db_conn, ssm_client=param_store_client)
        if not payment_link and exp_minutes:
            return HTTPCodes.ERROR.value, {'message': 'Can not to get payment link'}

        ssm_origination_number_key = os.getenv('SSM_PINPOINT_ORIGINATION_NUMBER_KEY',
                                               '/chatbot/dev/pinpoint/origination_number')
        origination_number = param_store_client.get_parameter(Name=ssm_origination_number_key,
                                                              WithDecryption=False)['Parameter']['Value']

        send_sms(pinoint_client=pinoint_client, message=payment_link, originationNumber=origination_number,
                 destinationNumber=borrower_phone_number, borrower_id=borrower_id)

    def _create_sp_proc(self, debt_id):
        query = f"SELECT id, clientId FROM Debt WHERE id = {debt_id}"
        cols, rows = self._execute_select(query)
        debt_id, client_id = rows[0]

        sp_key_prefix = os.getenv('SWERVE_PAY_KEY_PREFIX').rstrip('/')
        acc_sid_key = f'{sp_key_prefix}/{client_id}/account_sid'
        username_key = f'{sp_key_prefix}/{client_id}/username'
        apikey_key = f'{sp_key_prefix}/{client_id}/apikey'
        ssm_client = boto3.client('ssm')

        print(f"sp_key_prefix: {sp_key_prefix}")
        print(f"acc_sid_key: {acc_sid_key}")
        print(f"username_key: {username_key}")
        print(f"apikey_key: {apikey_key}")
        print(f"ssm_client: {ssm_client}")
        acc_sid = ssm_client.get_parameter(Name=acc_sid_key, WithDecryption=False)['Parameter']['Value']
        username = ssm_client.get_parameter(Name=username_key, WithDecryption=False)['Parameter']['Value']
        apikey = ssm_client.get_parameter(Name=apikey_key, WithDecryption=True)['Parameter']['Value']
        self._sp_proc = SwervePay(accountSid=acc_sid, username=username, apikey=apikey)

    def _verify_hash(self):
        hash = self.params.get('hash') or self.body.get('hash')
        crc = self.params.get('crc') or self.body.get('crc')
        if not hash or not crc:
            return '', False
        ssm_payment_link_encryption_key = os.getenv('SSM_PAYMENT_LINK_ENCRYPTION_KEY')
        print(f'Fetching param: {ssm_payment_link_encryption_key}')
        encryption_key = boto3.client('ssm').get_parameter(Name=ssm_payment_link_encryption_key,
                                                           WithDecryption=True)['Parameter']['Value']
        return decrypt_payment_link(hash, encryption_key, crc)

    def _update_debt_data(self, debt_id, debt_amount, err_code, err_code_description, data_dict, funding_account):
        debt_id = int(debt_id)
        fund_acc_summary = funding_account.get('id')
        fund_acc_type = funding_account.get('accountType')
        payment_proc = funding_account.get('payment_proc')
        sp_transaction_id = data_dict.get('data')
        sp_transaction_reason = data_dict.get('reason')

        # insert into DebtPayment
        query = f"""
        INSERT INTO DebtPayment
        (debtId, paymentDateTimeUTC, amount,
        paymentStatus, fundingAccSummary, paymentProcessor,
        vendorTransId, statusReason, accountType,
        createDate, lastUpdateDate)
        VALUES 
        ({debt_id}, CURRENT_TIMESTAMP, {debt_amount}, 
        '{err_code_description}', cast({fund_acc_summary} as varchar), '{payment_proc}',
        '{sp_transaction_id}', '{sp_transaction_reason}', '{fund_acc_type}', 
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        """
        self._execute_insert(query)

        # if err_code_description == PaymentProccessorPaymentStatus.OK.value:
        if err_code == 0:  # payment succeed

            # 1. update Debt
            query = f"""
                UPDATE Debt SET
                status = '{DBDebtStatus.journey_quit.value}',
                lastUpdateDate = CURRENT_TIMESTAMP
                WHERE id = {debt_id}
            """
            self._execute_update(query)

            # 2. add JourneyDebtStatus 'paid'
            query = f"""
                INSERT INTO JourneyDebtStatus(journeyEntryActivityId, journeyDebtStatusDefinitionId, 
                                                createDate, lastUpdateDate)
                SELECT jea_id, jdsd_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                FROM (
                    SELECT jea.id as jea_id, jdsd.id as jdsd_id
                    FROM JourneyEntryActivity jea, JourneyDebtStatusDefinition jdsd
                    WHERE jea.debtId = {debt_id} AND jea.exitDateTimeUTC IS NULL
                    AND jdsd.statusName = '{DBJourneyDebtStatus.paid.value}'
                    LIMIT 1
                ) j
            """
            self._execute_insert(query)

            # 3. add JourneyEntryActivity.exitDateTimeUTC
            query = f"""
                UPDATE JourneyEntryActivity SET
                exitDateTimeUTC = CURRENT_TIMESTAMP,
                lastUpdateDate = CURRENT_TIMESTAMP
                WHERE debtId = {debt_id}
            """
            self._execute_update(query)

            # 4.  remove debt session from Dynamo
            debt_records = [d for d in DebtRecordModel.query(debt_id)]
            print(f"Found debt records: {debt_records}")
            for record in debt_records:
                record.delete()

    def get_payment(self):
        decrypted_link, verified = self._verify_hash()
        if not verified:
            return HTTPCodes.ERROR.value, {'message': 'Verification Failed'}

        debt_id, debt_amount, expiration_utc_ts = decrypted_link.split(':')
        print(f'Processing payment (debt_id, debt_amount, expiration_utc_ts) {debt_id, debt_amount, expiration_utc_ts}')

        # add borrower's data
        query = f"""
                    SELECT b.id, b.firstName, b.lastName, b.phonenum, c.organization, d.outstandingBalance
                    FROM Debt d JOIN Client c on d.clientId = c.id JOIN Borrower b on b.debtId = d.id
                    WHERE d.id = {debt_id}
                """
        borrower = self._map_cols_rows(*self._execute_select(query))

        if int(expiration_utc_ts) < datetime.utcnow().timestamp():
            return HTTPCodes.OK.value, {'message': 'Link Expired', 'borrower': borrower}

        # get borrower's funding accounts
        query = f"""
            SELECT bfa.* 
            FROM Borrower b JOIN BorrowerFundingAccount bfa ON b.id = bfa.borrowerId
            WHERE b.debtId = {debt_id}
        """
        funding_accounts = self._map_cols_rows(*self._execute_select(query))

        return HTTPCodes.OK.value, {'funding_accounts': funding_accounts, 'borrower': borrower}

    def post_payment_account(self):
        """
        0. Check if debt hasn't been paid
        1. If new payment method:
            1.a. get or create new user in Swerve Pay
            1.b. add new funding account
        2. commit payment
        """

        decrypted_link, verified = self._verify_hash()
        if not verified:
            return HTTPCodes.ERROR.value, {'message': 'Verification Failed'}

        if 'cardHolder' not in self.body:
            return HTTPCodes.ERROR.value, {'message': f'Missing card holder'}

        if 'cardNumber' not in self.body:
            return HTTPCodes.ERROR.value, {'message': f'Missing card number'}

        if 'expMonYear' not in self.body:
            return HTTPCodes.ERROR.value, {'message': f'Missing card expire date'}

        if 'cvc' not in self.body:
            return HTTPCodes.ERROR.value, {'message': f'Missing card CVC code'}

        debt_id, debt_amount, expiration_utc_ts = decrypted_link.split(':')
        print(f'Processing payment (debt_id, debt_amount, expiration_utc_ts) {debt_id, debt_amount, expiration_utc_ts}')

        # check if debt hasn't been paid already
        query = f"""SELECT count(*) FROM DebtPayment WHERE debtid = {debt_id};"""
        print(f"Query: {query}")
        cols, rows = self._execute_select(query)

        debt_payment_cnt = rows[THE_ONLY_INDEX][THE_ONLY_INDEX]
        print(f'DebtPayment count: {debt_payment_cnt}')
        if int(debt_payment_cnt) > 0:
            return HTTPCodes.ERROR.value, {'message': f'Debt {debt_id} is already paid'}

        self._create_sp_proc(debt_id)

        # get payment params
        borrower_funding_account_id = self.body.get('id')

        if not borrower_funding_account_id:
            print(f'Funding account is not found, will be created')

            cardHolder = self.body.get('cardHolder')
            firstName = cardHolder.split()[0]
            lastName = '' if len(cardHolder.split()) < 2 else cardHolder.split()[1]

            # check if user_id is already created by debt_id
            query = f"""
                SELECT DISTINCT(bfa.paymentProcessorUserId) as user_id
                FROM BorrowerFundingAccount bfa JOIN Borrower b ON bfa.borrowerId = b.id
                WHERE b.debtId = {debt_id}
            """
            cols, rows = self._execute_select(query)
            user_id = ''
            if rows and rows[0] and rows[0][0]:
                user_id = rows[0][0].rstrip(' ')

            if not user_id:
                # create user in Swerve
                error_code, error_code_description, data_dict = self._sp_proc.create_user(firstName, lastName)
                print(f'create_user {firstName},{lastName}: {[error_code, error_code_description, data_dict]}')
                user_id = '' if not data_dict else data_dict.get('data', {})
                if not user_id:
                    return HTTPCodes.ERROR.value, {'message': f'Failed to create new payment user {cardHolder}'}

            query = f"SELECT id FROM Borrower WHERE debtId = {debt_id}"
            cols, rows = self._execute_select(query)
            borrowerId = rows[0][0]

            print(f'borrowerId, user_id {borrowerId, user_id}')

            # add funding account
            cardNumber = self.body.get('cardNumber')
            cardNumber_last_4_digits = str(cardNumber)[-4:]
            expMonYear = self.body.get('expMonYear')
            cvc = self.body.get('cvc')
            accountType = FundingType.cc.value

            err_code, err_code_description, data_dict = self._sp_proc.add_funding_account(
                fundingType=accountType,
                billFirstName=firstName,
                billLastName=lastName,
                accountNumber=cardNumber,
                userid=user_id,
                cardExpirationDate=expMonYear.replace('/', ''),
                routingNumber=''
            )
            print(f'add_funding_account {cardNumber, expMonYear}: {[err_code, err_code_description, data_dict]}')
            if err_code != 0:
                return HTTPCodes.ERROR.value, {
                    'error_code': err_code,
                    'error_code_description': err_code_description,
                    'data_dict': data_dict
                }

            tokenized_id = '' if not data_dict else data_dict.get('data')
            if not tokenized_id:
                return HTTPCodes.ERROR.value, {'message': f'Failed to create new funding account {cardHolder}'}

            # save new funding account into Aurora
            try:
                query = f"""
                    INSERT INTO BorrowerFundingAccount
                    (borrowerId, accountType, cardNumber, cardHolder,
                    paymentProcessor, paymentProcessorUserId, token, 
                    createDate, lastUpdateDate)
                    VALUES 
                    ({borrowerId},'{accountType}','{cardNumber_last_4_digits}','{cardHolder}',
                    '{PAYMENT_PROCESSOR_NAME}', '{user_id}', '{tokenized_id}',
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
                self._execute_insert(query)
            except Exception as e:
                print(f'Can not insert into borrower funding account')
                print(f'Error: {e}')
                return HTTPCodes.ERROR.value, {'message': f'Failed to create borrower funding account'}

            # get id of the new account
            query = f"""
                SELECT id FROM BorrowerFundingAccount 
                WHERE borrowerId = {borrowerId} AND paymentProcessorUserId = '{user_id}'
                AND cardNumber = '{cardNumber_last_4_digits}' AND token = '{tokenized_id}'
                """
            cols, rows = self._execute_select(query)
            borrower_funding_account_id = rows[THE_ONLY_INDEX][THE_ONLY_INDEX]

            if not borrower_funding_account_id:
                return HTTPCodes.ERROR.value, {'message': f'Failed to create borrower funding account'}

        return HTTPCodes.OK.value, {
            'data_dict': {
                "borrowerFundingAccountId": borrower_funding_account_id
            }
        }

    def delete_payment_account(self):
        print("Delete payment account")
        borrower_funding_account_id = self.params.get("borrowerFundingAccountId")
        print(f"Received borrowerFundingAccountId: {borrower_funding_account_id}")

        if not borrower_funding_account_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing borrowerFundingAccountId'}

        try:
            query = f"""
                    DELETE FROM BorrowerFundingAccount
                    WHERE id={borrower_funding_account_id};
                    """
            self._execute_delete(query)
        except Exception as e:
            print(f"Can not to delete funding account with id {borrower_funding_account_id}")
            print(e)

            return HTTPCodes.ERROR.value, {
                'message': f'{e}'
            }
        return HTTPCodes.OK.value, {}

    def post_payment(self):
        decrypted_link, verified = self._verify_hash()
        if not verified:
            return HTTPCodes.ERROR.value, {'message': 'Verification Failed'}

        borrower_funding_account_id = self.body.get("borrowerFundingAccountId")
        if not borrower_funding_account_id:
            return HTTPCodes.ERROR.value, {'message': 'No borrowerFundingAccountId found'}
        print(f"Received borrowerFundingAccountId: {borrower_funding_account_id}")

        debt_amount = self.body.get("debtAmount")
        if not debt_amount:
            return HTTPCodes.ERROR.value, {'message': 'No debtAmount found'}

        print(f"Received debtAmount: {debt_amount}")

        debt_id, debt_amount_extracted, expiration_utc_ts = decrypted_link.split(':')
        print(
            f'Processing payment (debt_id, debt_amount, expiration_utc_ts) {debt_id, debt_amount_extracted, expiration_utc_ts}')

        # check if debt hasn't been paid already
        query = f"""SELECT count(*) FROM DebtPayment WHERE debtid = {debt_id};"""
        print(f"Query: {query}")
        cols, rows = self._execute_select(query)

        debt_payment_cnt = rows[THE_ONLY_INDEX][THE_ONLY_INDEX]
        print(f'DebtPayment count: {debt_payment_cnt}')
        if int(debt_payment_cnt) > 0:
            return HTTPCodes.ERROR.value, {'message': f'Debt {debt_id} is already paid'}

        self._create_sp_proc(debt_id)

        query = f"""
            SELECT bfa.* 
            FROM BorrowerFundingAccount bfa JOIN Borrower b ON bfa.borrowerId = b.id
            WHERE b.debtId = {debt_id} AND bfa.id = {borrower_funding_account_id}
        """

        print(f"Query: {query}")
        query_results = self._map_cols_rows(*self._execute_select(query))
        print(f"Query result: {query_results}")

        if not query_results:
            return HTTPCodes.ERROR.value, {
                'message': f'Borrower funding account {borrower_funding_account_id} doesnt belong to Debt {debt_id}'
            }
        print("Extract funding account")
        funding_account = query_results[0]
        print(f'funding_account {funding_account}')
        err_code, err_code_description, data_dict = self._sp_proc.make_payment(funding_account.get('accounttype'),
                                                                               funding_account.get('token'),
                                                                               amount=debt_amount)

        self._update_debt_data(debt_id, debt_amount, err_code, err_code_description, data_dict, funding_account)

        return HTTPCodes.OK.value, {
            'error_code': err_code,
            'error_code_description': err_code_description,
            'data_dict': data_dict
        }

    def resend_payment_link(self):
        decrypted_link, verified = self._verify_hash()
        if not verified:
            return HTTPCodes.ERROR.value, {'message': 'Verification Failed'}

        debt_id, debt_amount, expiration_utc_ts = decrypted_link.split(':')
        print(f'Processing payment (debt_id, debt_amount, expiration_utc_ts) {debt_id, debt_amount, expiration_utc_ts}')

        query = f"""
                    SELECT id, phonenum
                    FROM Borrower WHERE debtId = {debt_id}
                """
        borrower = self._map_cols_rows(*self._execute_select(query))

        self._create_and_send_new_payment_link(borrower_id=int(borrower[0]['id']),
                                               borrower_phone_number=borrower[0]['phonenum'],
                                               debt_id=int(debt_id))

        return HTTPCodes.OK.value, {}
