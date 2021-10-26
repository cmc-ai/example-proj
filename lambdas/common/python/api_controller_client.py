import boto3
import os
from datetime import datetime, timedelta

from api_controller_base import APIController
import validate_and_upload_depts
from constants import HTTPCodes
from dynamo_models import BorrowerMessageModel
from helper_functions import ts_to_utc_dt
from contextlib import closing

S3_PRESIGNED_URL_EXPIRATION_SEC = 3600
LAST_INDEX = -1  # use these indexes to avoid magic numbers in code
THE_ONLY_INDEX = 0


class DebtAPIController(APIController):

    def get_debt(self):
        if self._client_id:
            self.params['d.clientId'] = self._client_id

        print(f"Received params: {self.params}")
        if "clientPortfolioId" in self.params:
            self.params["d.clientportfolioid"] = int(self.params["clientPortfolioId"])
            del self.params["clientPortfolioId"]

        print(f"Updated params: {self.params}")

        query = f"""
            SELECT db.*, 
            cp.portfolioName as d_clientPortfolioName,
            jdsd.statusName as s_statusName,
            jds.statusValue as s_statusValue 
            FROM
            (
                SELECT 
                d.id as d_id, 
                d.clientid as d_clientId,
                d.clientportfolioid as d_clientPortfolioId, 
                d.originalbalance as d_originalBalance, 
                d.outstandingbalance as d_outstandingBalance, 
                d.totalpayment as d_totalPayment, 
                d.discount as d_discount, 
                d.description as d_description, 
                d.discountexpirationdatetimeutc as d_discountExpirationDateTimeUTC,
                d.createdate as d_createDate, 
                d.lastupdatedate as d_lastUpdateDate,
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
                {self._build_filter_string()} 
            ) db
            LEFT JOIN ClientPortfolio cp ON cp.id = db.d_clientPortfolioId
            LEFT JOIN JourneyEntryActivity jea ON jea.debtId = db.d_id
            LEFT JOIN JourneyDebtStatus jds ON jds.journeyEntryActivityId = jea.id
            LEFT JOIN JourneyDebtStatusDefinition jdsd ON jdsd.id = jds.journeyDebtStatusDefinitionId
            ;
        """
        mapped_items = self._map_cols_rows(*self._execute_select(query))

        groupped_debts = {}
        for item in mapped_items:
            debt = {field[2:]: item[field] for field in item if field.startswith('d_')}  # [2:] removes prefix d_
            debt_id = debt.get('id')
            borrower = {field[2:]: item[field] for field in item if field.startswith('b_')}
            status = {field[2:]: item[field] for field in item if field.startswith('s_') and item[field]}

            if not groupped_debts.get(debt_id):  # check if debt already exists
                groupped_debts[debt_id] = debt.copy()
                groupped_debts[debt_id]['borrowers'] = []
                groupped_debts[debt_id]['statuses'] = []
            if borrower not in groupped_debts[debt_id]['borrowers']:
                groupped_debts[debt_id]['borrowers'].append(borrower.copy())
            if status and status not in groupped_debts[debt_id]['statuses']:
                groupped_debts[debt_id]['statuses'].append(status.copy())

        # select count
        query = f"""
            SELECT COUNT(DISTINCT(d.id)) 
            FROM Debt d JOIN Borrower b ON d.id = b.debtId
            {self._build_filter_string(limit_offset=False)};
        """
        columns, rows = self._execute_select(query)
        total_count = int(rows[0][0])

        return {
            'data': [groupped_debts[debt_id] for debt_id in groupped_debts],
            'pagination': {'totalCount': total_count}
        }

    def validate_and_upload(self):
        print("Validate and upload CSV file")
        s3_bucket = os.getenv('CLIENTS_S3_BUCKET_NAME')
        upload_file_key = f"debts/{self._client_id}/{self._client_portfolio_id}/{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}.csv"
        code, rsp = validate_and_upload_depts.upload(body=self.body,
                                                     upload_s3_path=os.path.join("s3://", s3_bucket, upload_file_key))
        print(f"Response code: {code}. Response: {rsp}")
        return code, rsp

    def upload(self):
        if not self._client_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing ClientId'}

        s3_bucket = os.getenv('CLIENTS_S3_BUCKET_NAME')
        upload_file_key = f"debts/{self._client_id}/{self._client_portfolio_id}/{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}.csv"

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
        example_file_key = 'debts-upload-example.csv'

        url = boto3.client('s3').generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': s3_bucket, 'Key': example_file_key},
            ExpiresIn=S3_PRESIGNED_URL_EXPIRATION_SEC,
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

        cognito_response = {}

        cognito_client = boto3.client('cognito-idp')
        cognito_client_app_id = os.getenv('COGNITO_CLIENT_APP_ID')

        # cognito_response = cognito_client.initiate_auth(
        #     AuthFlow='REFRESH_TOKEN_AUTH',
        #     AuthParameters=self.body.get('AuthParameters', {}),
        #     ClientMetadata=self.body.get('ClientMetadata', {}),
        #     ClientId=cognito_client_app_id,
        #     AnalyticsMetadata=self.body.get('AnalyticsMetadata', {}),
        #     UserContextData=self.body.get('UserContextData', {})
        # )
        # if cognito_response and cognito_response.get('AuthenticationResult', {}).get('AccessToken'):
        #     new_token = cognito_response.get('AuthenticationResult', {}).get('IdToken')
        #     query = f"UPDATE Client SET token = '{new_token}' WHERE id = {self._client_id}"
        #     self._execute_insert(query)

        # 1. revoke
        cognito_client.revoke_token(
            Token=self.body.get('RefreshToken'),
            ClientId=cognito_client_app_id
        )
        # 2. sign out
        cognito_client.global_sign_out(
            AccessToken=self.body.get('AccessToken')
        )

        return cognito_response

    def get_portfolio(self):
        client_id = self._client_id or -1
        use_limit_offset = True if 'limit' in self.params or 'offset' in self.params else False
        query = f"SELECT * FROM ClientPortfolio WHERE clientId = {client_id} {self._build_filter_string(limit_offset=use_limit_offset)}"
        columns, rows = self._execute_select(query)
        mapped_items = self._map_cols_rows(columns, rows)

        if use_limit_offset:
            query = f"""
                SELECT COUNT(DISTINCT(id)) 
                FROM ClientPortfolio WHERE clientId = {client_id}
                {self._build_filter_string(limit_offset=False)};
            """
            columns, rows = self._execute_select(query)
            total_count = int(rows[0][0])

            return HTTPCodes.OK.value, {
                'data': mapped_items,
                'pagination': {
                    'totalCount': total_count,
                    'perPage': self.params.get('limit', 0),
                    'page': self.params.get('offset', 0),
                },
            }

        return HTTPCodes.OK.value, mapped_items

    def post_portfolio(self):
        if not self._client_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing ClientId'}

        portfolio_name = self.body.get('portfolioName')
        if not portfolio_name:
            return HTTPCodes.ERROR.value, {'message': 'Missing portfolioName'}

        query = f"""
            INSERT INTO ClientPortfolio (clientId, portfolioName, createDate, lastUpdateDate )
            VALUES ({self._client_id}, '{portfolio_name}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id;
        """
        # self._execute_insert(query)

        print(f"Query: {query}")

        client_portfolio_id = None
        with closing(self.db_conn.cursor()) as cursor:
            row = cursor.execute(query).fetchone()
            self.db_conn.commit()
            client_portfolio_id = row[0]
            print(f"Created client portfolio entry with id: {client_portfolio_id}")

        if not client_portfolio_id:
            print("No client portfolio id")
            return HTTPCodes.ERROR.value, {'message': "Could not create client portfolio"}

        query = f"""
            INSERT INTO Clientconfiguration(
            clientportfolioid, createdate, lastupdatedate)
            VALUES ({client_portfolio_id}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
        """
        print(f"Query: {query}")
        self._execute_insert(query)

        return HTTPCodes.CREATED.value, {}

    def put_portfolio(self):
        if not self._client_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing ClientId'}

        portfolio_name = self.body.get('portfolioName')
        if not portfolio_name:
            return HTTPCodes.ERROR.value, {'message': 'Missing portfolioName'}

        portfolio_id = self.params.get('portfolioId')
        if not portfolio_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing portfolioId'}

        print(f"Update client portfolio with id {portfolio_id}")
        query = f"""
            UPDATE clientportfolio
            SET portfolioname='{portfolio_name}', lastupdatedate=CURRENT_TIMESTAMP
            WHERE id={portfolio_id};
        """
        self._execute_update(query)

        return HTTPCodes.OK.value, {}

    def delete_portfolio(self):
        if not self._client_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing ClientId'}

        portfolio_id = self.params.get('portfolioId')
        if not portfolio_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing portfolioId'}

        print(f"Delete client portfolio with id {portfolio_id}")
        query = f"""
                    DELETE FROM clientportfolio
                    WHERE id={portfolio_id};
                """
        self._execute_delete(query)

        return HTTPCodes.OK.value, {}
        pass

    def get_collection(self):
        client_id = self._client_id or -1

        use_limit_offset = True if 'limit' in self.params or 'offset' in self.params else False

        query = f"""
            SELECT cc.* FROM ClientConfiguration cc JOIN ClientPortfolio cp ON cc.clientPortfolioId = cp.id
            WHERE cp.clientId = {client_id}
            {self._build_filter_string(limit_offset=use_limit_offset)};
        """

        print(f"Get collection query: {query}")
        columns, rows = self._execute_select(query)
        mapped_items = self._map_cols_rows(columns, rows)

        if use_limit_offset:
            query = f"""
                SELECT COUNT(DISTINCT(cc.id)) FROM ClientConfiguration cc JOIN ClientPortfolio cp ON cc.clientPortfolioId = cp.id
                WHERE cp.clientId = {client_id}
                {self._build_filter_string(limit_offset=False)};
            """
            columns, rows = self._execute_select(query)
            total_count = int(rows[0][0])

            return HTTPCodes.OK.value, {
                'data': mapped_items,
                'pagination': {
                    'totalCount': total_count,
                    'perPage': self.params.get('limit', 0),
                    'page': self.params.get('offset', 0),
                }
            }

        return HTTPCodes.OK.value, mapped_items

    def post_collection(self):
        if not self._client_id:
            return HTTPCodes.ERROR.value, {'message': 'No ClientId provided'}

        client_portfolio_id = self.body.get('clientPortfolioId')
        if not client_portfolio_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing client portfolio ID'}

        link_exp_minutes = self.body.get('linkExpMinutes')
        if not link_exp_minutes:
            return HTTPCodes.ERROR.value, {'message': 'Missing link expiration minutes'}

        gap_btw_journeys_days = self.body.get('gapBetweenJourneysDays')
        if not link_exp_minutes:
            return HTTPCodes.ERROR.value, {'message': 'Missing gap between journey days'}

        update_segment_interval = self.body.get('updateSegmentInterval')
        if not update_segment_interval:
            return HTTPCodes.ERROR.value, {'message': 'Missing update segment interval'}

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
            (clientPortfolioId, linkExpMinutes, gapBetweenJourneysDays, createDate, lastUpdateDate, updatesegmentinterval )
            VALUES 
            ({client_portfolio_id}, {link_exp_minutes}, {gap_btw_journeys_days}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 
            {update_segment_interval});
            """
        self._execute_insert(query)

        return HTTPCodes.CREATED.value, {}

    def put_collection(self):
        if not self._client_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing ClientId'}

        collection_id = self.params.get('collectionId')
        if not collection_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing collectionId'}

        print("Get collection fields")
        client_portfolio_id = self.body.get('clientPortfolioId')
        if not client_portfolio_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing client portfolio ID'}

        link_exp_minutes = self.body.get('linkExpMinutes')
        if not link_exp_minutes:
            return HTTPCodes.ERROR.value, {'message': 'Missing link expiration minutes'}

        gap_btw_journeys_days = self.body.get('gapBetweenJourneysDays')
        if not link_exp_minutes:
            return HTTPCodes.ERROR.value, {'message': 'Missing gap between journey days'}

        update_segment_interval = self.body.get('updateSegmentInterval')
        if not update_segment_interval:
            return HTTPCodes.ERROR.value, {'message': 'Missing update segment interval'}

        print(f"Update client collection with id {collection_id}")
        query = f"""
            UPDATE ClientConfiguration
            SET clientPortfolioId={client_portfolio_id}, linkExpMinutes={link_exp_minutes}, 
            gapBetweenJourneysDays={gap_btw_journeys_days}, lastupdatedate=CURRENT_TIMESTAMP,
            updatesegmentinterval={update_segment_interval}
            WHERE id={collection_id};
        """
        print(f"Update query: {query}")
        self._execute_update(query)

        return HTTPCodes.OK.value, {}

    def delete_collection(self):
        if not self._client_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing ClientId'}

        collection_id = self.params.get('collectionId')
        if not collection_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing collectionId'}

        print(f"Delete client configuration with id {collection_id}")
        query = f"""
                    DELETE FROM ClientConfiguration
                    WHERE id={collection_id};
                """
        self._execute_delete(query)

        return HTTPCodes.OK.value, {}


class OtherAPIController(APIController):
    def get_report(self):
        start_data = self.params.get('startDate') or datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
        end_date = self.params.get('endDate') or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        portfolio_id = int(self.params.get('portfolioId')) if self.params.get('portfolioId') else None
        print(f"Selected portfolio id: {portfolio_id}")

        if portfolio_id:
            query = f"""
                        SELECT status, COUNT(*) AS num, SUM(originalbalance) as originalbalance FROM debt
                        WHERE createdate >= '{start_data}' and createdate <= '{end_date}' and clientportfolioid={portfolio_id} 
                        and clientid={self._client_id} 
                        GROUP BY status
                    """
        else:
            query = f"""
                    SELECT status, COUNT(*) AS num, SUM(originalbalance) as originalbalance FROM debt
                    WHERE createdate >= '{start_data}' and createdate <= '{end_date}' and clientid={self._client_id} 
                    GROUP BY status
                    """

        newly_added_items = self._map_cols_rows(*self._execute_select(query))
        print(f"newly_added_items: {newly_added_items}")

        query = f"""
                    SELECT COUNT(*) AS num FROM debt
                    WHERE lastupdatedate >= '{start_data}' and lastupdatedate <= '{end_date}' and clientid={self._client_id} 
                """
        if portfolio_id:
            query += f" and clientportfolioid={portfolio_id}"

        completes_items = self._map_cols_rows(*self._execute_select(query))
        print(f"completes_items: {completes_items}")
        completes_count = completes_items[0]['num'] or 0 if completes_items else 0

        query = f"""
                    SELECT COUNT(*) AS num FROM debt
                    WHERE lastupdatedate >= '{start_data}' and lastupdatedate <= '{end_date}' and status = 'inactive' 
                    and clientid={self._client_id} 
                """
        if portfolio_id:
            query += f" and clientportfolioid={portfolio_id}"

        inactive_items = self._map_cols_rows(*self._execute_select(query))
        print(f"inactive_items: {inactive_items}")
        inactive_count = inactive_items[0]['num'] or 0 if inactive_items else 0

        if portfolio_id:
            query = f"""
                    SELECT SUM(amount) AS amount FROM debtpayment AS dp INNER JOIN debt as d on dp.debtid=d.id
                    WHERE dp.paymentDateTimeUTC >= '{start_data}' and dp.paymentDateTimeUTC <= '{end_date}' and
                    d.clientportfolioid={portfolio_id} and d.clientid={self._client_id} 
                    """
        else:
            query = f"""
                    SELECT SUM(amount) AS amount FROM debtpayment AS dp INNER JOIN debt as d on dp.debtid=d.id
                    WHERE dp.paymentDateTimeUTC >= '{start_data}' and dp.paymentDateTimeUTC <= '{end_date}' 
                    and d.clientid={self._client_id}
                    """
        collected_amounts = self._map_cols_rows(*self._execute_select(query))
        print(f"collected_amounts: {collected_amounts}")
        collected_amount = collected_amounts[0]['amount'] or 0 if collected_amounts else 0

        query = f"""
                    SELECT SUM(outstandingBalance) AS amount FROM debt
                    WHERE lastupdatedate >= '{start_data}' and lastupdatedate <= '{end_date}' and clientid={self._client_id}
                """
        if portfolio_id:
            query += f" and clientportfolioid={portfolio_id}"

        original_balances = self._map_cols_rows(*self._execute_select(query))
        print(f"original_balances: {original_balances}")
        original_balance = original_balances[0]['amount'] or 0 if original_balances else 0

        return {
            "newly_added_items": newly_added_items,
            "completes_count": completes_count,
            "inactive_count": inactive_count,
            "collected_amount": collected_amount,
            "original_balance": original_balance,
        }
