from datetime import datetime
from decimal import Decimal

LAST_INDEX = -1  # use these indexes to avoid magic numbers in code
THE_ONLY_INDEX = 0


class APIController(object):

    def __init__(self, path, headers, params, body, db_conn, client_username=None):
        self.path = path
        self.headers = headers or {}
        self.params = params or {}
        self.body = body or {}
        self.db_conn = db_conn
        self._client_id = None
        self._client_portfolio_id = params.get('clientPortfolioId', 0)

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

    def _map_cols_rows(self, cols, rows) -> list:
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
