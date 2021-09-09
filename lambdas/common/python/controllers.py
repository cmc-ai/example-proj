from datetime import datetime
from decimal import Decimal

from dynamo_models import BorrowerMessageModel
from constants import HTTPCodes
from helper_functions import ts_to_utc_dt

LAST_INDEX = -1


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
                self._client_id = int(rows[0][0])
                print(f'Found ClientId {self._client_id}')

    def _build_filter_string(self):
        offset = self.params.get('offset', 0)
        limit = self.params.get('limit', 50)
        params = [p for p in self.params if p not in ['limit', 'offset']]

        param_strings = []
        for param in params:
            val = self.params.get(param)
            if type(val) == str:
                param_string = f"{param} = '{val}'"
            else:
                param_string = f"{param} = {val}"
            param_strings.append(param_string)

        result = ''
        if param_strings:
            result = result + 'WHERE ' + ' AND '.join(param_strings)
        result = result + f' LIMIT {limit} OFFSET {offset}'

        return result

    def _execute_insert(self, query):
        print(f'Executing {query}')
        self.db_conn.run(query)
        self.db_conn.commit()
        return

    def _execute_select(self, query):
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
            self.params['clientId'] = self._client_id
        query = f"""
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
            FROM Debt d join Borrower b on d.id = b.debtId
            {self._build_filter_string()} ;
        """
        columns, rows = self._execute_select(query)
        mapped_items = self._map_cols_rows(columns, rows)

        groupped_debts = {}
        for item in mapped_items:
            debt = {field[2:]: item[field] for field in item if field.startswith('d_')}  # [2:] removes prefix d_
            debt_id = debt.get('id')
            borrower = {field[2:]: item[field] for field in item if field.startswith('b_')}

            if not groupped_debts.get(debt_id):  # check if debt already exists
                groupped_debts[debt_id] = debt.copy()
                groupped_debts[debt_id]['borrowers'] = []
            groupped_debts[debt_id]['borrowers'].append(borrower.copy())

        return [groupped_debts[debt_id] for debt_id in groupped_debts]

    def upload(self):
        return {}

    def download(self):
        return {}

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
        return {}

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
            return HTTPCodes.ERROR.value, {'message': 'Missing clientPortfolioId, linkExpMinutes, or gapBetweenJourneysDays'}

        # check
        query = f"""
            SELECT cp.id from ClientPortfolio cp JOIN Client c on cp.clientId = c.id
            WHERE cp.id = {client_portfolio_id} AND c.id = {self._client_id}
        """
        cols, rows = self._execute_select(query)
        if not rows:
            return HTTPCodes.ERROR.value, {'message': f'ClientPortfolio {client_portfolio_id} doesnt belong to the Client {self._client_id}'}

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
