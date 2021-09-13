import os

import boto3

from datetime import datetime
from decimal import Decimal

from dynamo_models import BorrowerMessageModel
from constants import HTTPCodes
from helper_functions import ts_to_utc_dt
from payment_controller import decrypt_payment_link
# from payment_processor import SwervePay

LAST_INDEX = -1  # use these indexes to avoid magic numbers in code
THE_ONLY_INDEX = 0
S3_PRESIGNED_URL_EXPIRATION_SEC = 3600


class APIController(object):

    def __init__(self, path, headers, params, body, db_conn, client_username=None):
        self.path = path
        self.headers = headers or {}
        self.params = params or {}
        self.body = body or {}
        self.db_conn = db_conn
        self._client_id = None

        # Client API section
        if client_username:
            query = f"SELECT id FROM Client WHERE username = '{client_username}'"
            cols, rows = self._execute_select(query)
            if not rows:
                print(f'ClientId is not found for client_username {client_username}')
            else:
                self._client_id = int(rows[THE_ONLY_INDEX][THE_ONLY_INDEX])
                print(f'Found ClientId {self._client_id}')

    def _build_filter_string(self, limit_offset=True):
        offset = self.params.get('offset', 0)
        limit = self.params.get('limit', 10)
        params = [p for p in self.params if p not in ['limit', 'offset']]

        param_strings = []
        for param in params:
            val = self.params.get(param)
            if type(val) == str:
                param_string = f"LOWER({param}) = '{val.lower()}'"
            else:
                param_string = f"{param} = {val}"
            param_strings.append(param_string)

        result = ''
        if param_strings:
            result = result + 'WHERE ' + ' AND '.join(param_strings)
        if limit_offset:
            result = result + f' LIMIT {limit} OFFSET {offset}'

        return result

    def _execute_insert(self, query):
        print(f'Executing {query}')
        self.db_conn.run(query)
        self.db_conn.commit()
        return

    def _execute_select(self, query) -> (list, list):
        print(f'Executing {query}')
        cursor = self.db_conn.cursor()
        rows = cursor.execute(query).fetchall()
        cols = [desc[0] for desc in cursor.description]
        cursor.close()
        return cols, rows

    def _map_cols_rows(self, cols, rows):
        result = []
        for row in rows:
            mapped_row = {}
            for i in range(len(cols)):
                mapped_row[cols[i]] = self._clear_value(row[i])
            result.append(mapped_row)
        return result

    def _clear_value(self, val):
        if type(val) == str:
            return val.rstrip()
        if type(val) == Decimal:
            return float(val)
        if type(val) == datetime:
            return val.strftime('%Y-%m-%d %H:%M:%S')
        return val


class DebtAPIController(APIController):

    def get_debt(self):
        if self._client_id:
            self.params['d.clientId'] = self._client_id
        query = f"""
            SELECT 
            d.id as d_id, 
            d.clientid as d_clientId,
            d.clientportfolioid as d_clientPortfolioId, 
            cp.portfolioName as d_clientPortfolioName,
            d.originalbalance as d_originalBalance, 
            d.outstandingbalance as d_outstandingBalance, 
            d.totalpayment as d_totalPayment, 
            d.discount as d_discount, 
            d.description as d_description, 
            d.discountexpirationdatetimeutc as d_discountExpirationDateTimeUTC,
            d.createdate as d_createDate, 
            d.lastupdatedate as d_lastUpdateDate,
            jdsd.statusName as s_statusName,
            jds.statusValue as s_statusValue,
            b.id as b_id,
            b.debtId as b_debtId,
            b.firstName as b_firstName,
            b.lastName as b_lastName,
            b.isPrimary as b_isPrimary,
            b.channelType as b_channelType,
            b.phoneNum as b_phoneNum,
            b.email as b_email,
            b.timezone as b_timezone,
            b.country as b_country,
            b.createDate as b_createDate,
            b.lastUpdateDate as b_lastUpdateDate
            FROM Debt d JOIN Borrower b ON d.id = b.debtId
            JOIN ClientPortfolio cp ON cp.id = d.clientPortfolioId
            JOIN JourneyEntryActivity jea ON jea.debtId = d.id
            JOIN JourneyDebtStatus jds ON jds.journeyEntryActivityId = jea.id
            JOIN JourneyDebtStatusDefinition jdsd ON jdsd.id = jds.journeyDebtStatusDefinitionId
            {self._build_filter_string()} ;
        """
        mapped_items = self._map_cols_rows(*self._execute_select(query))

        groupped_debts = {}
        for item in mapped_items:
            debt = {field[2:]: item[field] for field in item if field.startswith('d_')}  # [2:] removes prefix d_
            debt_id = debt.get('id')
            borrower = {field[2:]: item[field] for field in item if field.startswith('b_')}
            status = {field[2:]: item[field] for field in item if field.startswith('s_')}

            if not groupped_debts.get(debt_id):  # check if debt already exists
                groupped_debts[debt_id] = debt.copy()
                groupped_debts[debt_id]['borrowers'] = []
                groupped_debts[debt_id]['statuses'] = []
            if borrower not in groupped_debts[debt_id]['borrowers']:
                groupped_debts[debt_id]['borrowers'].append(borrower.copy())
            if status not in groupped_debts[debt_id]['statuses']:
                groupped_debts[debt_id]['statuses'].append(status.copy())

        # select count
        query = f"""
            SELECT COUNT(*) FROM Debt d join Borrower b on d.id = b.debtId 
            {self._build_filter_string(limit_offset=False)};
        """
        columns, rows = self._execute_select(query)
        total_count = int(rows[0][0])

        return {
            'data': [groupped_debts[debt_id] for debt_id in groupped_debts],
            'pagination': {'totalCount': total_count}
        }

    def upload(self):
        if not self._client_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing ClientId'}

        s3_bucket = os.getenv('CLIENTS_S3_BUCKET_NAME')
        upload_file_key = f"{self._client_id}/debts/{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}.json"

        url = boto3.client('s3').generate_presigned_url(
            ClientMethod='put_object',
            Params={'Bucket': s3_bucket, 'Key': upload_file_key},
            ExpiresIn=S3_PRESIGNED_URL_EXPIRATION_SEC
        )
        print(f'Presigned URL {S3_PRESIGNED_URL_EXPIRATION_SEC} sec {url}')
        return url

    def download(self):
        if not self._client_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing ClientId'}

        s3_bucket = os.getenv('CLIENTS_S3_BUCKET_NAME')
        example_file_key = 'debts-upload-example.json'

        url = boto3.client('s3').generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': s3_bucket, 'Key': example_file_key},
            ExpiresIn=S3_PRESIGNED_URL_EXPIRATION_SEC
        )
        print(f'Presigned URL {S3_PRESIGNED_URL_EXPIRATION_SEC} sec {url}')
        return url

    def get_chat_history(self):
        debt_id = int(self.path.rstrip('/').split('/')[LAST_INDEX])
        query = f"""
            SELECT b.id FROM Borrower b JOIN Debt d on b.debtId = d.id
            WHERE b.debtId = {debt_id} 
        """
        if self._client_id:
            query += f" AND d.clientId = {self._client_id}"
        columns, rows = self._execute_select(query)
        if not rows:
            print(f'borrower_id is not found for debt_id {debt_id}')
            return []

        borrower_id = rows[0][0]
        print(f'Found borrower_id {borrower_id}')
        message_records = BorrowerMessageModel.query(borrower_id)

        messages = [r.attribute_values for r in message_records]
        for message in messages:
            message['event_utc_dt'] = ts_to_utc_dt(message.get('event_utc_ts', 0))

        return messages

    def get_payment_history(self):
        debt_id = int(self.path.rstrip('/').split('/')[LAST_INDEX])
        query = f"""
            SELECT * FROM DebtPayment WHERE debtId = {debt_id}
        """
        if self._client_id:
            query += f" AND EXISTS (SELECT * FROM Debt where id = {debt_id} and clientId = {self._client_id})"
        columns, rows = self._execute_select(query)
        mapped_items = self._map_cols_rows(columns, rows)

        return mapped_items


class ClientAPIController(APIController):

    def get_account(self):
        client_id = self._client_id or -1
        query = f"SELECT * FROM Client WHERE id = {client_id}"
        columns, rows = self._execute_select(query)
        mapped_items = self._map_cols_rows(columns, rows)
        return {} if not mapped_items else mapped_items[0]

    def patch_account(self):
        if not self._client_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing ClientId'}

        client_fields = ['firstName', 'lastName', 'phoneNum', 'email', 'organization']
        set_strings = []
        for f in client_fields:
            new_value = self.body.get(f)
            if new_value:
                if type(new_value) == str:
                    set_strings.append(f" {f} = '{new_value}'")
                else:
                    set_strings.append(f" {f} = {new_value}")
        if not set_strings:
            return HTTPCodes.ERROR.value, {'message': f'No new values provided for {client_fields}'}

        query = f"""
            UPDATE Client SET
            {','.join(set_strings)},
            lastUpdateDate = CURRENT_TIMESTAMP
            WHERE id = {self._client_id}
        """
        self._execute_insert(query)

        return HTTPCodes.OK.value, {}

    def post_api_token(self):
        if not self._client_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing ClientId'}

        cognito_client = boto3.client('cognito-idp')
        cognito_response = cognito_client.initiate_auth(
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters=self.body.get('AuthParameters', {}),
            ClientMetadata=self.body.get('ClientMetadata', {}),
            ClientId=self.body.get('ClientId'),
            AnalyticsMetadata=self.body.get('AnalyticsMetadata', {}),
            UserContextData=self.body.get('UserContextData', {})
        )

        if cognito_response and cognito_response.get('AuthenticationResult', {}).get('AccessToken'):
            new_token = cognito_response.get('AuthenticationResult', {}).get('AccessToken')
            query = f"UPDATE Client SET token = '{new_token}' WHERE id = {self._client_id}"
            self._execute_insert(query)

        return cognito_response

    def get_portfolio(self):
        client_id = self._client_id or -1
        query = f"SELECT * FROM ClientPortfolio WHERE clientId = {client_id}"
        columns, rows = self._execute_select(query)
        mapped_items = self._map_cols_rows(columns, rows)
        return mapped_items

    def post_portfolio(self):
        if not self._client_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing ClientId'}

        portfolio_name = self.body.get('portfolioName')
        if not portfolio_name:
            return HTTPCodes.ERROR.value, {'message': 'Missing portfolioName'}

        query = f"""
            INSERT INTO ClientPortfolio (clientId, portfolioName, createDate, lastUpdateDate )
            VALUES ({self._client_id}, '{portfolio_name}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        """
        self._execute_insert(query)

        return HTTPCodes.CREATED.value, {}

    def get_collection(self):
        client_id = self._client_id or -1
        query = f"""
            SELECT cc.* FROM ClientConfiguration cc JOIN ClientPortfolio cp ON cc.clientPortfolioId = cp.id
            WHERE cp.clientId = {client_id}
        """
        columns, rows = self._execute_select(query)
        mapped_items = self._map_cols_rows(columns, rows)
        return mapped_items

    def post_collection(self):
        if not self._client_id:
            return HTTPCodes.ERROR.value, {'message': 'No ClientId provided'}

        client_portfolio_id = self.body.get('clientPortfolioId')
        link_exp_minutes = self.body.get('linkExpMinutes')
        gap_btw_journeys_days = self.body.get('gapBetweenJourneysDays')
        if not client_portfolio_id or not link_exp_minutes or not gap_btw_journeys_days:
            return HTTPCodes.ERROR.value, {
                'message': 'Missing clientPortfolioId, linkExpMinutes, or gapBetweenJourneysDays'}

        # check
        query = f"""
            SELECT cp.id from ClientPortfolio cp JOIN Client c on cp.clientId = c.id
            WHERE cp.id = {client_portfolio_id} AND c.id = {self._client_id}
        """
        cols, rows = self._execute_select(query)
        if not rows:
            return HTTPCodes.ERROR.value, {
                'message': f'ClientPortfolio {client_portfolio_id} doesnt belong to the Client {self._client_id}'}

        query = f"""
            INSERT INTO ClientConfiguration 
            (clientPortfolioId, linkExpMinutes, gapBetweenJourneysDays, createDate, lastUpdateDate )
            VALUES 
            ({client_portfolio_id}, {link_exp_minutes}, {gap_btw_journeys_days}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
            """
        self._execute_insert(query)

        return HTTPCodes.CREATED.value, {}


class OtherAPIController(APIController):
    def get_report(self):
        return {}


class PaymentAPIController(APIController):

    def __init__(self, **kwargs):
        super(PaymentAPIController, self).__init__(**kwargs)
        self._sp_proc = None

    def _create_sp_proc(self, debt_id):
        query = f"SELECT id, clientId FROM Debt WHERE id = {debt_id}"
        debt_id, client_id = self._execute_select(query)[LAST_INDEX]

        # sp_key_prefix = os.getenv('SWERVE_PAY_KEY_PREFIX')
        # acc_sid_key = f'{sp_key_prefix}/{client_id}/account_sid'
        # username_key = f'{sp_key_prefix}/{client_id}/username'
        # apikey_key = f'{sp_key_prefix}/{client_id}/apikey'
        # ssm_client = boto3.client('ssm')
        # acc_sid = ssm_client.get_parameter(Name=acc_sid_key, WithDecryption=False)['Parameter']['Value']
        # username = ssm_client.get_parameter(Name=username_key, WithDecryption=False)['Parameter']['Value']
        # apikey = ssm_client.get_parameter(Name=apikey_key, WithDecryption=True)['Parameter']['Value']
        #
        # self._sp_proc = SwervePay(accountSid=acc_sid, username=username, apikey=apikey)

    def get_payment(self):
        hash = self.params.get('hash')
        crc = self.params.get('crc')
        ssm_payment_link_encryption_key = os.getenv('SSM_PAYMENT_LINK_ENCRYPTION_KEY')
        encryption_key = boto3.client('ssm') \
            .get_parameter(Name=ssm_payment_link_encryption_key, WithDecryption=True)['Parameter']['Value']

        decrypted_link, verified = decrypt_payment_link(hash, encryption_key, crc)
        if not verified:
            return HTTPCodes.ERROR.value, {'message': 'Link Verification Failed'}

        debt_id, debt_amount, expiration_utc_ts = decrypted_link.split(':')
        print(f'Processing payment (debt_id, debt_amount, expiration_utc_ts) {debt_id, debt_amount, expiration_utc_ts}')

        if int(expiration_utc_ts) < datetime.utcnow().timestamp():
            return HTTPCodes.OK.value, {'message': 'Link Expired'}

        # get borrower's data
        query = f"""
            SELECT id, firstName, lastName 
            FROM Borrower WHERE debtId = {debt_id}
        """
        b_id, b_first_name, b_last_name = self._execute_select(query)[LAST_INDEX]


        return {}

    def post_payment(self):
        return {}
