from datetime import datetime
from decimal import Decimal

from dynamo_models import BorrowerMessageModel

LAST_INDEX = -1


class APIController(object):
    def __init__(self, path, headers, params, body, db_conn):
        self.path = path
        self.headers = headers or {}
        self.params = params or {}
        self.body = body or {}
        self.db_conn = db_conn

    def _build_filter_string(self):
        offset = self.params.get('offset', 0)
        limit = self.params.get('limit', 50)
        params = [p for p in self.params if p not in ['limit', 'offset']]

        param_strings = []
        for param in params:
            if type(param) == str:
                param_string = f" {param} = '{self.params.get(param)}' "
            else:
                param_string = f" {param} = {self.params.get(param)} "
            param_strings.append(param_string)

        result = ''
        if param_strings:
            result = result + ' WHERE ' + ' AND '.join(param_strings)
        result = result + f' LIMIT {limit} OFFSET {offset}'

        return result

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
            debt = {field[2:]: item[field] for field in item if field.startswith('d_')}  # [2:] removes prefix
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
        borrower_id = int(self.path.rstrip('/').split('/')[LAST_INDEX])
        message_records = [d for d in BorrowerMessageModel.query(borrower_id)]

        return message_records

    def get_payment_history(self):
        return {}


class ClientAPIController(APIController):
    def get_account(self):
        return {}

    def patch_account(self):
        return {}

    def post_api_token(self):
        return {}

    def get_portfolio(self):
        return {}

    def post_portfolio(self):
        return {}

    def get_collection(self):
        return {}

    def post_collection(self):
        return {}


class OtherAPIController(APIController):
    def get_report(self):
        return {}


# -----------------
# import pynamodb
#
# controller = DebtAPIController('/api/chat-history/1', {}, {}, {}, None)
# print(controller.get_chat_history())